from typing import List, Dict, Any, Optional
from collections import defaultdict

from .base_extractor import BaseExtractor
from ..models.data_models import Team, Division


class TeamExtractor(BaseExtractor):
    """
    Extractor for team data including division standings and rankings.
    """
    
    def extract(self) -> List[Division]:
        """
        Extract all teams organized by divisions with proper rankings.
        
        Returns:
            List of Division objects with ranked teams
        """
        self.log_extraction_start("team data")
        
        try:
            # Get all teams from ESPN
            espn_teams = self.espn_client.get_teams()
            
            # Convert to our Team model
            teams = []
            for espn_team in espn_teams:
                team = self._convert_espn_team(espn_team)
                teams.append(team)
            
            # Organize teams into divisions
            divisions = self._organize_teams_into_divisions(teams)
            
            # Rank teams within each division
            for division in divisions:
                division.teams = self._rank_teams(division.teams)
            
            self.log_extraction_complete("team data", len(teams))
            return divisions
            
        except Exception as e:
            self.handle_extraction_error(e, "team data")
    
    def _convert_espn_team(self, espn_team: Any) -> Team:
        """
        Convert an ESPN team object to our Team model.
        
        Args:
            espn_team: ESPN team object
            
        Returns:
            Team model instance
        """
        # Extract division info - ESPN may or may not provide this
        division = self._determine_team_division(espn_team)
        
        return Team(
            id=espn_team.team_id,
            name=espn_team.team_name,
            abbreviation=espn_team.team_abbrev,
            owner=self._extract_owner_name(espn_team),
            division=division,
            wins=espn_team.wins,
            losses=espn_team.losses,
            ties=getattr(espn_team, 'ties', 0),
            points_for=espn_team.points_for,
            points_against=espn_team.points_against,
            division_rank=0  # Will be calculated later
        )
    
    def _extract_owner_name(self, espn_team: Any) -> str:
        """
        Extract owner name from ESPN team object.
        
        Args:
            espn_team: ESPN team object
            
        Returns:
            Owner display name as string
        """
        try:
            # Try different possible owner attribute structures
            if hasattr(espn_team, 'owner'):
                owner = espn_team.owner
                if isinstance(owner, dict):
                    return owner.get('displayName', owner.get('name', 'Unknown'))
                elif isinstance(owner, str):
                    return owner
                else:
                    return str(owner)
            
            # Try owners list (plural)
            if hasattr(espn_team, 'owners') and espn_team.owners:
                owner = espn_team.owners[0]
                if isinstance(owner, dict):
                    return owner.get('displayName', owner.get('name', 'Unknown'))
                elif isinstance(owner, str):
                    return owner
                else:
                    return str(owner)
            
            return 'Unknown'
            
        except Exception as e:
            self.logger.warning(f"Failed to extract owner name: {e}")
            return 'Unknown'
    
    def _determine_team_division(self, espn_team: Any) -> str:
        """
        Determine which division a team belongs to.
        ESPN may or may not provide division info, so we may need to infer it.
        
        Args:
            espn_team: ESPN team object
            
        Returns:
            Division name
        """
        # Check if ESPN provides division info
        if hasattr(espn_team, 'division_id'):
            division_id = espn_team.division_id
            # Map division ID to name (this is league-specific)
            division_map = {0: "Division 0", 1: "Division 1", 2: "Division 2", 3: "Division 3"}
            return division_map.get(division_id, f"Division {division_id}")
        
        # If no division info from ESPN and no divisions in config, create simple divisions
        if not hasattr(self.config.league, 'divisions') or not self.config.league.divisions:
            # Auto-create divisions based on team count
            return f"Division {espn_team.team_id % 2}"  # Simple 2-division split
        
        # Use config divisions as fallback
        divisions = self.config.league.divisions
        division_index = espn_team.team_id % len(divisions)
        return divisions[division_index]
    
    def _organize_teams_into_divisions(self, teams: List[Team]) -> List[Division]:
        """
        Organize teams into divisions.
        
        Args:
            teams: List of Team objects
            
        Returns:
            List of Division objects
        """
        # Group teams by division
        division_teams = defaultdict(list)
        for team in teams:
            division_teams[team.division].append(team)
        
        # Create Division objects
        divisions = []
        for division_name, division_team_list in division_teams.items():
            division = Division(
                name=division_name,
                teams=division_team_list
            )
            divisions.append(division)
        
        return divisions
    
    def _rank_teams(self, teams: List[Team]) -> List[Team]:
        """
        Rank teams within a division based on league tiebreaking rules.
        
        Args:
            teams: List of teams to rank
            
        Returns:
            List of teams sorted by rank (1st place first)
        """
        # Create a copy to avoid modifying the original
        ranked_teams = teams.copy()
        
        # Sort teams based on configured tiebreakers
        tiebreakers = self.config.league.tiebreakers
        
        def sort_key(team: Team):
            sort_criteria = []
            
            for tiebreaker in tiebreakers:
                if tiebreaker == "wins":
                    sort_criteria.append(-team.wins)  # Negative for descending
                elif tiebreaker == "losses":
                    sort_criteria.append(team.losses)  # Positive for ascending
                elif tiebreaker == "points_for":
                    sort_criteria.append(-team.points_for)
                elif tiebreaker == "points_against":
                    sort_criteria.append(team.points_against)
                elif tiebreaker == "head_to_head":
                    # This would require matchup history - complex implementation
                    # For now, use a placeholder (0)
                    sort_criteria.append(0)
            
            return tuple(sort_criteria)
        
        ranked_teams.sort(key=sort_key)
        
        # Assign division ranks
        for rank, team in enumerate(ranked_teams, 1):
            team.division_rank = rank
        
        return ranked_teams
    
    def get_team_by_id(self, team_id: int) -> Optional[Team]:
        """
        Get a specific team by ID.
        
        Args:
            team_id: ESPN team ID
            
        Returns:
            Team object or None if not found
        """
        cache_key = f"team_{team_id}"
        cached_team = self.get_cached_data(cache_key)
        
        if cached_team is not None:
            return cached_team
        
        try:
            espn_teams = self.espn_client.get_teams()
            
            for espn_team in espn_teams:
                if espn_team.team_id == team_id:
                    team = self._convert_espn_team(espn_team)
                    self.set_cached_data(cache_key, team)
                    return team
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get team {team_id}: {e}")
            return None
    
    def get_standings(self) -> List[Team]:
        """
        Get overall league standings (all teams ranked).
        
        Returns:
            List of all teams sorted by overall rank
        """
        divisions = self.extract()
        
        # Collect all teams
        all_teams = []
        for division in divisions:
            all_teams.extend(division.teams)
        
        # Rank all teams against each other
        return self._rank_teams(all_teams)