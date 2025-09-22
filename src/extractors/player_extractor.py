from typing import List, Optional, Any, Dict
from datetime import datetime

from .base_extractor import BaseExtractor
from ..models.data_models import Player, InjuryStatus, InjuredStarter, PlayerStatistics


class PlayerExtractor(BaseExtractor):
    """
    Extractor for player data including projected/actual scores and injury status.
    """
    
    def extract(self) -> List[Player]:
        """
        Extract all players from current week matchups.
        This is the abstract method required by BaseExtractor.
        
        Returns:
            List of all Player objects from current week
        """
        week = self.get_target_week()
        matchups = self.espn_client.get_matchups(week)
        
        all_players = []
        for matchup in matchups:
            players = self.extract_players_from_matchup(matchup)
            all_players.extend(players)
        
        return all_players
    
    def extract_players_from_matchup(self, espn_matchup: Any) -> List[Player]:
        """
        Extract all players from a specific ESPN matchup.
        
        Args:
            espn_matchup: ESPN box score object
            
        Returns:
            List of Player objects
        """
        self.log_extraction_start("player data from matchup")
        
        try:
            players = []
            
            # Extract players from home team
            home_players = self._extract_team_players(
                espn_matchup.home_team, 
                espn_matchup.home_lineup, 
                True
            )
            players.extend(home_players)
            
            # Extract players from away team
            away_players = self._extract_team_players(
                espn_matchup.away_team, 
                espn_matchup.away_lineup, 
                False
            )
            players.extend(away_players)
            
            self.log_extraction_complete("player data from matchup", len(players))
            return players
            
        except Exception as e:
            self.handle_extraction_error(e, "player data from matchup")
    
    def _extract_team_players(self, espn_team: Any, lineup: Any, is_home: bool) -> List[Player]:
        """
        Extract players from a team's lineup.
        
        Args:
            espn_team: ESPN team object
            lineup: ESPN lineup object
            is_home: Whether this is the home team
            
        Returns:
            List of Player objects
        """
        players = []
        
        try:
            # ESPN lineups have different slots (starter, bench, IR, etc.)
            for box_player in lineup:
                # BoxPlayer object structure - the player info is directly on the BoxPlayer
                espn_player = box_player
                
                if not espn_player:
                    continue
                
                # Try to get slot position from the BoxPlayer object
                slot_position = getattr(espn_player, 'slot_position', getattr(espn_player, 'lineupSlot', 'UNKNOWN'))
                
                player = self._convert_espn_player(
                    espn_player, 
                    espn_team.team_name,
                    slot_position
                )
                
                if player:
                    players.append(player)
        
        except Exception as e:
            self.logger.error(f"Failed to extract players from team {espn_team.team_name}: {e}")
        
        return players
    
    def _convert_espn_player(self, espn_player: Any, team_name: str, slot_position: str) -> Optional[Player]:
        """
        Convert an ESPN BoxPlayer to our Player model.
        
        Args:
            espn_player: ESPN BoxPlayer object
            team_name: Fantasy team name
            slot_position: Lineup slot position string
            
        Returns:
            Player model instance or None if invalid
        """
        try:
            # Determine if player was a starter
            is_starter = self._is_starter_slot(slot_position)
            
            # Get player name - try different attributes
            player_name = getattr(espn_player, 'name', 
                         getattr(espn_player, 'player_name', 
                         getattr(espn_player, 'fullName', 'Unknown Player')))
            
            # Get player position - try different attributes
            position = getattr(espn_player, 'position', 
                      getattr(espn_player, 'eligible_positions', ['UNKNOWN'])[0] if hasattr(espn_player, 'eligible_positions') else 'UNKNOWN')
            
            # Get projected and actual scores - try different attributes
            projected_score = float(getattr(espn_player, 'projected_points', 
                                   getattr(espn_player, 'projected_total_points', 
                                   getattr(espn_player, 'projected_avg_points', 0))))
            
            actual_score = float(getattr(espn_player, 'points', 
                                getattr(espn_player, 'total_points', 
                                getattr(espn_player, 'avg_points', 0))))
            
            # Determine injury status
            injury_status = self._get_injury_status(espn_player)

            # Extract detailed statistics
            statistics = self._extract_player_statistics(espn_player)

            return Player(
                name=player_name,
                position=str(position),
                roster_slot=slot_position,
                team=team_name,
                projected_score=projected_score,
                actual_score=actual_score,
                is_starter=is_starter,
                should_have_started=None,  # Will be calculated later
                injury_status=injury_status,
                statistics=statistics
            )
            
        except Exception as e:
            self.logger.error(f"Failed to convert ESPN BoxPlayer: {e}")
            return None
    
    def _extract_player_statistics(self, espn_player: Any) -> Optional[PlayerStatistics]:
        """
        Extract detailed statistics from ESPN BoxPlayer object.

        Args:
            espn_player: ESPN BoxPlayer object

        Returns:
            PlayerStatistics object with detailed stats or None if unavailable
        """
        try:
            # Try to access the stats breakdown for the current week
            # ESPN player stats structure: espn_player.stats[week]['breakdown']
            stats_data = getattr(espn_player, 'stats', {})

            # Find the most recent week with data
            if not stats_data:
                self.logger.debug(f"No stats data available for player {getattr(espn_player, 'name', 'unknown')}")
                return None

            # Get the target week or find the most recent week
            target_week = self.get_target_week()

            # Try target week first, then fall back to any available week
            week_stats = None
            if target_week in stats_data:
                week_stats = stats_data[target_week]
            elif stats_data:
                # Get the most recent week with data
                available_weeks = sorted(stats_data.keys(), reverse=True)
                week_stats = stats_data[available_weeks[0]]

            if not week_stats or 'breakdown' not in week_stats:
                return None

            breakdown = week_stats['breakdown']

            # Extract statistics based on available breakdown data
            return PlayerStatistics(
                # QB Statistics
                passing_completions=breakdown.get('passingCompletions'),
                passing_attempts=breakdown.get('passingAttempts'),
                passing_yards=breakdown.get('passingYards'),
                passing_touchdowns=breakdown.get('passingTouchdowns'),
                passing_interceptions=breakdown.get('passingInterceptions'),

                # Rushing Statistics
                rushing_attempts=breakdown.get('rushingAttempts'),
                rushing_yards=breakdown.get('rushingYards'),
                rushing_touchdowns=breakdown.get('rushingTouchdowns'),

                # Receiving Statistics
                receiving_receptions=breakdown.get('receivingReceptions'),
                receiving_yards=breakdown.get('receivingYards'),
                receiving_touchdowns=breakdown.get('receivingTouchdowns'),
                receiving_targets=breakdown.get('receivingTargets'),

                # Kicking Statistics
                field_goals_made=breakdown.get('kickingFieldGoalsMade'),
                field_goals_attempted=breakdown.get('kickingFieldGoalsAttempted'),
                extra_points_made=breakdown.get('kickingExtraPointsMade'),
                extra_points_attempted=breakdown.get('kickingExtraPointsAttempted'),

                # Defense/Special Teams Statistics
                defensive_touchdowns=breakdown.get('defensiveTouchdowns'),
                defensive_interceptions=breakdown.get('defensiveInterceptions'),
                defensive_fumbles_recovered=breakdown.get('defensiveFumblesRecovered'),
                defensive_safeties=breakdown.get('defensiveSafeties'),
                defensive_sacks=breakdown.get('defensiveSacks'),
                points_allowed=breakdown.get('defensivePointsAllowed'),
                yards_allowed=breakdown.get('defensiveYardsAllowed')
            )

        except Exception as e:
            self.logger.debug(f"Could not extract player statistics: {e}")
            return None

    def _is_starter_slot(self, slot_position: str) -> bool:
        """
        Determine if a roster slot position indicates a starter.
        
        Args:
            slot_position: ESPN slot position (e.g., 'QB', 'RB', 'BE', 'IR')
            
        Returns:
            True if the slot is a starting position
        """
        # Always non-starting positions
        non_starting_positions = {
            'BE',  # Bench
            'IR',  # Injured Reserve
            'SUSPEND',  # Suspended
            'NA',   # Not Available
            'ER'    # Emergency/Reserve
        }
        
        # If it's explicitly a non-starting position, return False
        if slot_position in non_starting_positions:
            return False
        
        # Try to get starting positions from league settings
        try:
            league = self.espn_client.get_league()
            if hasattr(league.settings, 'position_slot_counts'):
                position_counts = league.settings.position_slot_counts
                # If this position has a slot count > 0 and it's not in non-starting, it's a starter
                return position_counts.get(slot_position, 0) > 0
        except Exception as e:
            self.logger.debug(f"Could not get league position settings: {e}")
        
        # Fallback: Common starting positions in fantasy football
        starting_positions = {
            'QB', 'RB', 'WR', 'TE', 'FLEX', 'OP', 'K', 'D/ST', 'DL', 'LB', 'DB',
            'RB/WR', 'RB/WR/TE', 'WR/TE', 'TQB'  # Various flex positions
        }
        
        return slot_position in starting_positions
    
    def _get_injury_status(self, espn_player: Any) -> InjuryStatus:
        """
        Determine injury status from ESPN BoxPlayer data.
        
        Args:
            espn_player: ESPN BoxPlayer object
            
        Returns:
            InjuryStatus enum value
        """
        try:
            # ESPN may provide injury status in different attributes
            injury_status = getattr(espn_player, 'injuryStatus', 
                             getattr(espn_player, 'injury_status',
                             getattr(espn_player, 'playerPoolEntry', {}).get('injuryStatus', None)))
            
            if not injury_status:
                return InjuryStatus.UNKNOWN
            
            # Map ESPN injury status to our enum
            injury_mapping = {
                'ACTIVE': InjuryStatus.HEALTHY,
                'QUESTIONABLE': InjuryStatus.QUESTIONABLE,
                'DOUBTFUL': InjuryStatus.DOUBTFUL,
                'OUT': InjuryStatus.OUT,
                'IR': InjuryStatus.IR,
                'INJURY_RESERVE': InjuryStatus.IR,
                'INJURED_RESERVE': InjuryStatus.IR,
                'NORMAL': InjuryStatus.HEALTHY,
                'HEALTHY': InjuryStatus.HEALTHY
            }
            
            status_str = str(injury_status).upper()
            return injury_mapping.get(status_str, InjuryStatus.UNKNOWN)
            
        except Exception as e:
            self.logger.debug(f"Could not determine injury status: {e}")
            return InjuryStatus.UNKNOWN
    
    def extract_injured_starters(self, matchups: List[Any]) -> List[InjuredStarter]:
        """
        Extract list of players who were started but are injured.
        
        Args:
            matchups: List of matchup objects (with player data)
            
        Returns:
            List of InjuredStarter objects
        """
        self.log_extraction_start("injured starters")
        
        try:
            injured_starters = []
            
            for matchup in matchups:
                # Extract all players from this matchup
                players = self.extract_players_from_matchup(matchup)
                
                # Find injured starters
                for player in players:
                    if (player.is_starter and 
                        player.injury_status != InjuryStatus.HEALTHY and
                        player.injury_status != InjuryStatus.UNKNOWN):
                        
                        injured_starter = InjuredStarter(
                            player_name=player.name,
                            team_name=player.team,
                            position=player.position,
                            injury_status=player.injury_status
                        )
                        injured_starters.append(injured_starter)
            
            self.log_extraction_complete("injured starters", len(injured_starters))
            return injured_starters
            
        except Exception as e:
            self.handle_extraction_error(e, "injured starters")
    
    def get_player_performance_summary(self, players: List[Player]) -> Dict[str, Any]:
        """
        Generate a summary of player performance.
        
        Args:
            players: List of Player objects
            
        Returns:
            Dictionary with performance statistics
        """
        if not players:
            return {}
        
        starters = [p for p in players if p.is_starter]
        bench = [p for p in players if not p.is_starter]
        
        total_projected = sum(p.projected_score for p in starters)
        total_actual = sum(p.actual_score for p in starters)
        
        return {
            'total_starters': len(starters),
            'total_bench': len(bench),
            'total_projected_points': total_projected,
            'total_actual_points': total_actual,
            'projection_accuracy': total_actual - total_projected,
            'best_performer': max(starters, key=lambda p: p.actual_score) if starters else None,
            'worst_performer': min(starters, key=lambda p: p.actual_score) if starters else None,
            'injured_starters': len([p for p in starters if p.injury_status != InjuryStatus.HEALTHY])
        }
    
    def find_players_by_position(self, players: List[Player], position: str) -> List[Player]:
        """
        Find all players at a specific position.
        
        Args:
            players: List of Player objects
            position: Position to filter by (e.g., 'QB', 'RB')
            
        Returns:
            List of players at the specified position
        """
        return [p for p in players if p.position == position]
    
    def get_top_performers(self, players: List[Player], count: int = 5) -> List[Player]:
        """
        Get the top performing players by actual score.
        
        Args:
            players: List of Player objects
            count: Number of top performers to return
            
        Returns:
            List of top performing players
        """
        return sorted(players, key=lambda p: p.actual_score, reverse=True)[:count]