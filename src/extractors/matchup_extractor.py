from typing import List, Optional, Any
from datetime import datetime

from .base_extractor import BaseExtractor
from .team_extractor import TeamExtractor
from ..models.data_models import Matchup, Team


class MatchupExtractor(BaseExtractor):
    """
    Extractor for matchup data including scores and results.
    """
    
    def __init__(self, espn_client, reference_date: Optional[datetime] = None):
        super().__init__(espn_client, reference_date)
        self.team_extractor = TeamExtractor(espn_client, reference_date)
    
    def extract(self, week: Optional[int] = None) -> List[Matchup]:
        """
        Extract matchups for a specific week.
        
        Args:
            week: NFL week number (defaults to target week)
            
        Returns:
            List of Matchup objects
        """
        if week is None:
            week = self.get_target_week()
        
        if not self.validate_week(week):
            raise ValueError(f"Invalid week number: {week}")
        
        self.log_extraction_start("matchup data", week)
        
        try:
            # Get matchups from ESPN
            espn_matchups = self.espn_client.get_matchups(week)
            
            # Convert to our Matchup model
            matchups = []
            for espn_matchup in espn_matchups:
                matchup = self._convert_espn_matchup(espn_matchup, week)
                if matchup:  # Only add valid matchups
                    matchups.append(matchup)
            
            self.log_extraction_complete("matchup data", len(matchups), week)
            return matchups
            
        except Exception as e:
            self.handle_extraction_error(e, "matchup data", week)
    
    def _convert_espn_matchup(self, espn_matchup: Any, week: int) -> Optional[Matchup]:
        """
        Convert an ESPN matchup/box score to our Matchup model.
        
        Args:
            espn_matchup: ESPN box score object
            week: NFL week number
            
        Returns:
            Matchup model instance or None if invalid
        """
        try:
            # ESPN box scores have home/away team structure
            home_team_data = espn_matchup.home_team
            away_team_data = espn_matchup.away_team
            
            # Convert teams
            home_team = self._convert_team_from_matchup(home_team_data)
            away_team = self._convert_team_from_matchup(away_team_data)
            
            if not home_team or not away_team:
                self.logger.warning(f"Invalid team data in matchup for week {week}")
                return None
            
            # Get scores
            home_score = float(espn_matchup.home_score or 0)
            away_score = float(espn_matchup.away_score or 0)
            
            # Determine winner/loser
            winner_id = None
            loser_id = None
            is_complete = home_score > 0 or away_score > 0  # Basic completion check
            
            if is_complete and home_score != away_score:
                if home_score > away_score:
                    winner_id = home_team.id
                    loser_id = away_team.id
                else:
                    winner_id = away_team.id
                    loser_id = home_team.id
            
            # Extract player data (will be populated by player extractor)
            players = []
            
            return Matchup(
                week=week,
                home_team=home_team,
                away_team=away_team,
                home_score=home_score,
                away_score=away_score,
                winner_id=winner_id,
                loser_id=loser_id,
                is_complete=is_complete,
                players=players
            )
            
        except Exception as e:
            self.logger.error(f"Failed to convert ESPN matchup: {e}")
            return None
    
    def _convert_team_from_matchup(self, team_data: Any) -> Optional[Team]:
        """
        Convert team data from a matchup to our Team model.
        This is a simplified version for matchup context.
        
        Args:
            team_data: ESPN team data from matchup
            
        Returns:
            Team model instance or None if invalid
        """
        try:
            # Use the team extractor to get full team data
            full_team = self.team_extractor.get_team_by_id(team_data.team_id)
            
            if full_team:
                return full_team
            
            # Fallback: create minimal team data from matchup context
            return Team(
                id=team_data.team_id,
                name=team_data.team_name,
                abbreviation=team_data.team_abbrev,
                owner=getattr(team_data, 'owner', 'Unknown'),
                division='Unknown',
                wins=0,
                losses=0,
                ties=0,
                points_for=0.0,
                points_against=0.0,
                division_rank=0
            )
            
        except Exception as e:
            self.logger.error(f"Failed to convert team data: {e}")
            return None
    
    def get_current_week_matchups(self) -> List[Matchup]:
        """
        Get matchups for the current NFL week.
        
        Returns:
            List of current week matchups
        """
        current_week = self.get_current_week()
        return self.extract(current_week)
    
    def get_completed_matchups(self, week: Optional[int] = None) -> List[Matchup]:
        """
        Get only completed matchups for a week.
        
        Args:
            week: NFL week number (defaults to target week)
            
        Returns:
            List of completed matchups
        """
        matchups = self.extract(week)
        return [m for m in matchups if m.is_complete]
    
    def get_matchup_by_teams(self, team1_id: int, team2_id: int, week: Optional[int] = None) -> Optional[Matchup]:
        """
        Get a specific matchup between two teams.
        
        Args:
            team1_id: First team ID
            team2_id: Second team ID
            week: NFL week number (defaults to target week)
            
        Returns:
            Matchup object or None if not found
        """
        matchups = self.extract(week)
        
        for matchup in matchups:
            home_id = matchup.home_team.id
            away_id = matchup.away_team.id
            
            if ((home_id == team1_id and away_id == team2_id) or 
                (home_id == team2_id and away_id == team1_id)):
                return matchup
        
        return None
    
    def get_team_matchup(self, team_id: int, week: Optional[int] = None) -> Optional[Matchup]:
        """
        Get the matchup for a specific team in a given week.
        
        Args:
            team_id: Team ID
            week: NFL week number (defaults to target week)
            
        Returns:
            Matchup object or None if not found
        """
        matchups = self.extract(week)
        
        for matchup in matchups:
            if matchup.home_team.id == team_id or matchup.away_team.id == team_id:
                return matchup
        
        return None