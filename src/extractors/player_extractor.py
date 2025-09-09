from typing import List, Optional, Any, Dict
from datetime import datetime

from .base_extractor import BaseExtractor
from ..models.data_models import Player, InjuryStatus, InjuredStarter


class PlayerExtractor(BaseExtractor):
    """
    Extractor for player data including projected/actual scores and injury status.
    """
    
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
            for slot in lineup:
                espn_player = slot.player
                
                if not espn_player:
                    continue
                
                player = self._convert_espn_player(
                    espn_player, 
                    espn_team.team_name,
                    slot
                )
                
                if player:
                    players.append(player)
        
        except Exception as e:
            self.logger.error(f"Failed to extract players from team {espn_team.team_name}: {e}")
        
        return players
    
    def _convert_espn_player(self, espn_player: Any, team_name: str, slot: Any) -> Optional[Player]:
        """
        Convert an ESPN player to our Player model.
        
        Args:
            espn_player: ESPN player object
            team_name: Fantasy team name
            slot: ESPN roster slot object
            
        Returns:
            Player model instance or None if invalid
        """
        try:
            # Determine if player was a starter
            is_starter = self._is_starter_slot(slot.slot_position)
            
            # Get projected and actual scores
            projected_score = float(getattr(espn_player, 'projected_points', 0))
            actual_score = float(getattr(espn_player, 'points', 0))
            
            # Determine injury status
            injury_status = self._get_injury_status(espn_player)
            
            return Player(
                name=espn_player.name,
                position=espn_player.position,
                team=team_name,
                projected_score=projected_score,
                actual_score=actual_score,
                is_starter=is_starter,
                injury_status=injury_status
            )
            
        except Exception as e:
            self.logger.error(f"Failed to convert ESPN player: {e}")
            return None
    
    def _is_starter_slot(self, slot_position: str) -> bool:
        """
        Determine if a roster slot position indicates a starter.
        
        Args:
            slot_position: ESPN slot position (e.g., 'QB', 'RB', 'BE', 'IR')
            
        Returns:
            True if the slot is a starting position
        """
        # Common starting positions in fantasy football
        starting_positions = {
            'QB', 'RB', 'WR', 'TE', 'FLEX', 'K', 'D/ST', 'DL', 'LB', 'DB'
        }
        
        # Non-starting positions
        non_starting_positions = {
            'BE',  # Bench
            'IR',  # Injured Reserve
            'SUSPEND',  # Suspended
            'NA'   # Not Available
        }
        
        return slot_position in starting_positions
    
    def _get_injury_status(self, espn_player: Any) -> InjuryStatus:
        """
        Determine injury status from ESPN player data.
        
        Args:
            espn_player: ESPN player object
            
        Returns:
            InjuryStatus enum value
        """
        try:
            # ESPN may provide injury status in different attributes
            injury_status = getattr(espn_player, 'injuryStatus', None)
            
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
                'INJURED_RESERVE': InjuryStatus.IR
            }
            
            return injury_mapping.get(injury_status.upper(), InjuryStatus.UNKNOWN)
            
        except Exception:
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