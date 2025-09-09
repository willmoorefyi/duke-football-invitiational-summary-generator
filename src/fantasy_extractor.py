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
                 username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize the fantasy football extractor.
        
        Args:
            league_id: ESPN fantasy league ID
            year: Fantasy season year (defaults to current year)
            username: ESPN username (overrides config)
            password: ESPN password (overrides config)
        """
        self.league_id = league_id
        self.year = year or datetime.now().year
        self.config = get_config()
        
        # Set up logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Create ESPN client
        self.espn_client = create_espn_client(league_id, year, username, password)
        
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