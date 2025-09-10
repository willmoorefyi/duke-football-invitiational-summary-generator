import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from .utils.espn_client import create_espn_client
from .utils.config import get_config
from .utils.date_utils import parse_date_input, get_nfl_week_calculator
from .extractors.team_extractor import TeamExtractor
from .extractors.matchup_extractor import MatchupExtractor
from .extractors.player_extractor import PlayerExtractor
from .models.data_models import WeeklyReport


class FantasyFootballExtractor:
    """
    Main orchestrator class that coordinates all data extraction and output generation.
    """
    
    def __init__(self, league_id: int, year: Optional[int] = None, 
                 espn_s2: Optional[str] = None, swid: Optional[str] = None):
        """
        Initialize the fantasy football extractor.
        
        Args:
            league_id: ESPN fantasy league ID
            year: Fantasy season year (defaults to current year)
            espn_s2: ESPN_S2 cookie value (overrides config)
            swid: SWID cookie value (overrides config)
        """
        self.league_id = league_id
        self.year = year or datetime.now().year
        self.config = get_config()
        
        # Set up logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Create ESPN client
        self.espn_client = create_espn_client(league_id, year, espn_s2, swid)
        
        # Initialize extractors
        self.team_extractor = None
        self.matchup_extractor = None
        self.player_extractor = None
        
        self.logger.info(f"Initialized FantasyFootballExtractor for league {league_id}")
    
    def _setup_logging(self):
        """Set up logging configuration."""
        logging.basicConfig(
            level=getattr(logging, self.config.logging.level),
            format=self.config.logging.format
        )
    
    def _initialize_extractors(self, reference_date: datetime):
        """Initialize all data extractors with the reference date."""
        self.team_extractor = TeamExtractor(self.espn_client, reference_date)
        self.matchup_extractor = MatchupExtractor(self.espn_client, reference_date)
        self.player_extractor = PlayerExtractor(self.espn_client, reference_date)
    
    def extract_weekly_report(self, date: Optional[str] = None, week: Optional[int] = None) -> WeeklyReport:
        """
        Extract a complete weekly fantasy football report.
        
        Args:
            date: Date string for reference (ISO format, defaults to now)
            week: Specific week to extract (overrides date-based calculation)
            
        Returns:
            WeeklyReport object with all extracted data
        """
        # Parse reference date
        reference_date = parse_date_input(date)
        
        # Initialize extractors with reference date
        self._initialize_extractors(reference_date)
        
        # Determine target week
        if week is not None:
            target_week = week
        else:
            week_calculator = get_nfl_week_calculator()
            target_week = week_calculator.get_previous_complete_week(reference_date)
        
        self.logger.info(f"Extracting weekly report for week {target_week}")
        
        try:
            # Get league info
            league_info = self.espn_client.get_league_info()
            
            # Extract team data (divisions and standings)
            divisions = self.team_extractor.extract()
            
            # Extract matchup data
            matchups = self.matchup_extractor.extract(target_week)
            
            # Extract player data for each matchup
            for matchup in matchups:
                espn_matchup = self._get_espn_matchup(target_week, matchup)
                if espn_matchup:
                    matchup.players = self.player_extractor.extract_players_from_matchup(espn_matchup)
                    # Calculate projected scores for starters
                    self._calculate_projected_scores(matchup)
                    # Calculate optimal lineups and scores
                    self._calculate_optimal_lineups(matchup)
            
            # Extract injured starters
            espn_matchups = self.espn_client.get_matchups(target_week)
            injured_starters = self.player_extractor.extract_injured_starters(espn_matchups)
            
            # Create the weekly report
            report = WeeklyReport(
                league_id=self.league_id,
                league_name=league_info['name'],
                season=self.year,
                week=target_week,
                report_date=reference_date,
                divisions=divisions,
                matchups=matchups,
                injured_starters=injured_starters
            )
            
            self.logger.info(f"Successfully generated weekly report for week {target_week}")
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to extract weekly report: {e}")
            raise
    
    def _get_espn_matchup(self, week: int, matchup) -> Optional[Any]:
        """
        Find the corresponding ESPN matchup object for our matchup.
        This is needed to extract player data.
        """
        try:
            espn_matchups = self.espn_client.get_matchups(week)
            
            for espn_matchup in espn_matchups:
                if (espn_matchup.home_team.team_id == matchup.home_team.id and
                    espn_matchup.away_team.team_id == matchup.away_team.id):
                    return espn_matchup
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to find ESPN matchup: {e}")
            return None
    
    def _calculate_projected_scores(self, matchup):
        """
        Calculate projected scores for both teams in a matchup.
        This is the sum of projected scores for all starting players.

        Args:
            matchup: Matchup object containing player data
        """
        try:
            # Separate players by team
            home_players = [p for p in matchup.players if p.team == matchup.home_team.name]
            away_players = [p for p in matchup.players if p.team == matchup.away_team.name]
            
            # Calculate projected scores for starters only
            home_projected_score = sum(p.projected_score for p in home_players if p.is_starter)
            away_projected_score = sum(p.projected_score for p in away_players if p.is_starter)
            
            # Update matchup with projected scores
            matchup.home_projected_score = home_projected_score
            matchup.away_projected_score = away_projected_score
            
        except Exception as e:
            self.logger.error(f"Failed to calculate projected scores: {e}")
            # Set defaults if calculation fails
            matchup.home_projected_score = None
            matchup.away_projected_score = None
    
    def _calculate_optimal_lineups(self, matchup):
        """
        Calculate optimal lineups and scores for both teams in a matchup.
        Updates the matchup with optimal scores and player should_have_started flags.
        
        Args:
            matchup: Matchup object containing player data
        """
        try:
            # Get league position requirements
            league = self.espn_client.get_league()
            position_counts = getattr(league.settings, 'position_slot_counts', {})
            
            # Separate players by team
            home_players = [p for p in matchup.players if p.team == matchup.home_team.name]
            away_players = [p for p in matchup.players if p.team == matchup.away_team.name]
            
            # Calculate optimal lineups
            home_optimal_lineup, home_optimal_score = self._calculate_team_optimal_lineup(home_players, position_counts)
            away_optimal_lineup, away_optimal_score = self._calculate_team_optimal_lineup(away_players, position_counts)
            
            # Update matchup with optimal scores
            matchup.home_optimal_score = home_optimal_score
            matchup.away_optimal_score = away_optimal_score
            
            # Mark players with should_have_started
            home_optimal_names = {p.name for p in home_optimal_lineup}
            away_optimal_names = {p.name for p in away_optimal_lineup}
            
            for player in matchup.players:
                if player.team == matchup.home_team.name:
                    player.should_have_started = player.name in home_optimal_names
                elif player.team == matchup.away_team.name:
                    player.should_have_started = player.name in away_optimal_names
                    
        except Exception as e:
            self.logger.error(f"Failed to calculate optimal lineups: {e}")
            # Set defaults if calculation fails
            matchup.home_optimal_score = None
            matchup.away_optimal_score = None
            for player in matchup.players:
                player.should_have_started = None
    
    def _calculate_team_optimal_lineup(self, players, position_counts):
        """
        Calculate the optimal starting lineup for a team's players.
        
        Args:
            players: List of Player objects for the team
            position_counts: Dictionary of position slot counts from league settings
            
        Returns:
            Tuple of (optimal_lineup_players, total_optimal_score)
        """
        # Filter out players on IR, suspended, etc. 
        available_players = [p for p in players if p.roster_slot not in {'IR', 'SUSPEND', 'NA'}]
        
        # Sort all players by actual score (descending)
        available_players.sort(key=lambda x: x.actual_score, reverse=True)
        
        optimal_lineup = []
        used_players = set()
        
        # Define position requirements based on common fantasy lineup
        # We'll use a simplified approach based on your league structure
        position_requirements = {
            'QB': position_counts.get('QB', 1),
            'RB': position_counts.get('RB', 2), 
            'WR': position_counts.get('WR', 2),
            'TE': position_counts.get('TE', 1),
            'K': position_counts.get('K', 1),
            'D/ST': position_counts.get('D/ST', 1),
            'RB/WR/TE': position_counts.get('RB/WR/TE', 1),  # Flex position
            'OP': position_counts.get('OP', 1)  # Offensive player (QB/RB/WR/TE)
        }
        
        # Fill dedicated positions first
        for pos, count in position_requirements.items():
            if pos in ['RB/WR/TE', 'OP']:  # Skip flex positions for now
                continue
                
            pos_players = [p for p in available_players 
                          if p.name not in used_players and self._player_eligible_for_position(p, pos)]
            
            for i in range(min(count, len(pos_players))):
                optimal_lineup.append(pos_players[i])
                used_players.add(pos_players[i].name)
        
        # Fill RB/WR/TE flex position
        if position_requirements.get('RB/WR/TE', 0) > 0:
            flex_eligible = [p for p in available_players 
                           if p.name not in used_players and p.position in ['RB', 'WR', 'TE']]
            if flex_eligible:
                optimal_lineup.append(flex_eligible[0])
                used_players.add(flex_eligible[0].name)
        
        # Fill OP (offensive player) position  
        if position_requirements.get('OP', 0) > 0:
            op_eligible = [p for p in available_players 
                         if p.name not in used_players and p.position in ['QB', 'RB', 'WR', 'TE']]
            if op_eligible:
                optimal_lineup.append(op_eligible[0])
                used_players.add(op_eligible[0].name)
        
        # Calculate total optimal score
        total_optimal_score = sum(p.actual_score for p in optimal_lineup)
        
        return optimal_lineup, total_optimal_score
    
    def _player_eligible_for_position(self, player, position):
        """
        Check if a player is eligible for a specific position.
        
        Args:
            player: Player object
            position: Position string (e.g., 'QB', 'RB', 'WR', 'TE', 'K', 'D/ST')
            
        Returns:
            Boolean indicating eligibility
        """
        return player.position == position
    
    def save_report_to_file(self, report: WeeklyReport, output_path: Optional[Path] = None) -> Path:
        """
        Save the weekly report to a JSON file.
        
        Args:
            report: WeeklyReport object to save
            output_path: Custom output path (defaults to configured pattern)
            
        Returns:
            Path to the saved file
        """
        if output_path is None:
            # Generate filename from config pattern
            filename = self.config.output.filename_pattern.format(
                week=report.week,
                date=report.report_date.strftime('%Y-%m-%d')
            )
            output_path = Path(filename)
        
        # Convert to JSON
        json_data = report.model_dump(mode='json')
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to file
        with open(output_path, 'w') as f:
            if self.config.output.pretty_print:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            else:
                json.dump(json_data, f, ensure_ascii=False)
        
        self.logger.info(f"Saved weekly report to {output_path}")
        return output_path
    
    def generate_and_save_report(self, date: Optional[str] = None, 
                               week: Optional[int] = None,
                               output_path: Optional[Path] = None) -> Path:
        """
        Generate a weekly report and save it to a file in one operation.
        
        Args:
            date: Date string for reference (ISO format, defaults to now)
            week: Specific week to extract (overrides date-based calculation)
            output_path: Custom output path (defaults to configured pattern)
            
        Returns:
            Path to the saved file
        """
        report = self.extract_weekly_report(date, week)
        return self.save_report_to_file(report, output_path)
    
    def get_league_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the league information.
        
        Returns:
            Dictionary with league summary data
        """
        try:
            league_info = self.espn_client.get_league_info()
            
            # Initialize extractors with current date
            self._initialize_extractors(datetime.now())
            
            # Get team data
            divisions = self.team_extractor.extract()
            
            return {
                'league_info': league_info,
                'divisions': [
                    {
                        'name': div.name,
                        'team_count': len(div.teams),
                        'teams': [
                            {
                                'name': team.name,
                                'owner': team.owner,
                                'record': f"{team.wins}-{team.losses}",
                                'rank': team.division_rank
                            }
                            for team in div.teams
                        ]
                    }
                    for div in divisions
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get league summary: {e}")
            raise