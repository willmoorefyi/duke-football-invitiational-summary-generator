import logging
from typing import Optional, List, Dict, Any
from espn_api.football import League
from .config import get_config, ESPNConfig
from datetime import datetime


logger = logging.getLogger(__name__)


class ESPNClient:
    """
    Wrapper around the espn-api library to provide standardized access
    to ESPN Fantasy Football league data.
    """
    
    def __init__(self, league_id: int, year: Optional[int] = None, 
                 username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize ESPN client.
        
        Args:
            league_id: ESPN fantasy league ID
            year: Fantasy season year (defaults to current year)
            username: ESPN username (overrides config)
            password: ESPN password (overrides config)
        """
        self.league_id = league_id
        self.year = year or datetime.now().year
        
        # Get credentials from config if not provided
        config = get_config()
        self.username = username or config.espn.username
        self.password = password or config.espn.password
        
        self._league = None
        
        logger.info(f"Initialized ESPN client for league {league_id}, year {self.year}")
    
    def connect(self) -> League:
        """
        Establish connection to ESPN Fantasy League.
        
        Returns:
            ESPN League object
            
        Raises:
            Exception: If connection fails
        """
        if self._league is not None:
            return self._league
        
        try:
            if self.username and self.password:
                logger.info("Connecting to ESPN with credentials")
                self._league = League(
                    league_id=self.league_id,
                    year=self.year,
                    username=self.username,
                    password=self.password
                )
            else:
                logger.info("Connecting to ESPN without credentials (public league)")
                self._league = League(
                    league_id=self.league_id,
                    year=self.year
                )
            
            logger.info(f"Successfully connected to league: {self._league.settings.name}")
            return self._league
            
        except Exception as e:
            logger.error(f"Failed to connect to ESPN league {self.league_id}: {e}")
            raise
    
    def get_league(self) -> League:
        """Get the connected league object."""
        if self._league is None:
            return self.connect()
        return self._league
    
    def get_teams(self) -> List[Any]:
        """Get all teams in the league."""
        league = self.get_league()
        return league.teams
    
    def get_matchups(self, week: Optional[int] = None) -> List[Any]:
        """
        Get matchups for a specific week.
        
        Args:
            week: NFL week number (defaults to current week)
            
        Returns:
            List of matchup objects
        """
        league = self.get_league()
        
        if week is None:
            # Use current week from league
            week = league.current_week
        
        try:
            return league.box_scores(week)
        except Exception as e:
            logger.error(f"Failed to get matchups for week {week}: {e}")
            return []
    
    def get_league_info(self) -> Dict[str, Any]:
        """
        Get basic league information.
        
        Returns:
            Dictionary with league details
        """
        league = self.get_league()
        
        return {
            'id': self.league_id,
            'name': league.settings.name,
            'year': self.year,
            'current_week': league.current_week,
            'team_count': len(league.teams),
            'playoff_team_count': league.settings.playoff_team_count,
            'regular_season_count': league.settings.reg_season_count
        }
    
    def get_player_info(self, player_id: int) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific player.
        
        Args:
            player_id: ESPN player ID
            
        Returns:
            Player information dictionary or None if not found
        """
        try:
            league = self.get_league()
            # This would need to be implemented based on espn-api capabilities
            # The espn-api library may not have direct player lookup by ID
            logger.warning("Player lookup by ID not yet implemented")
            return None
        except Exception as e:
            logger.error(f"Failed to get player info for ID {player_id}: {e}")
            return None
    
    def is_authenticated(self) -> bool:
        """Check if client is using authenticated access."""
        return bool(self.username and self.password)
    
    def get_current_week(self) -> int:
        """Get the current week from the league."""
        league = self.get_league()
        return league.current_week
    
    def get_scoring_period(self, week: int) -> int:
        """
        Convert NFL week to ESPN scoring period.
        In most cases, these are the same, but this provides flexibility.
        
        Args:
            week: NFL week number
            
        Returns:
            ESPN scoring period
        """
        # For now, assume 1:1 mapping
        return week


def create_espn_client(league_id: int, year: Optional[int] = None, 
                      username: Optional[str] = None, password: Optional[str] = None) -> ESPNClient:
    """
    Factory function to create and connect an ESPN client.
    
    Args:
        league_id: ESPN fantasy league ID
        year: Fantasy season year (defaults to current year)
        username: ESPN username (overrides config)
        password: ESPN password (overrides config)
        
    Returns:
        Connected ESPN client
    """
    client = ESPNClient(league_id, year, username, password)
    client.connect()  # Ensure connection is established
    return client