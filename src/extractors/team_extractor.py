from typing import List, Dict, Any, Optional
from collections import defaultdict

from .base_extractor import BaseExtractor
from ..models.data_models import Team, Division
from ..utils.team_logos import get_team_logo_url


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

        # Extract ESPN standings data
        wins = getattr(espn_team, 'wins', 0)
        losses = getattr(espn_team, 'losses', 0)
        ties = getattr(espn_team, 'ties', 0)
        points_for = float(getattr(espn_team, 'points_for', 0.0))
        points_against = float(getattr(espn_team, 'points_against', 0.0))
        standing = getattr(espn_team, 'standing', 0)
        playoff_pct = float(getattr(espn_team, 'playoff_pct', 0.0))

        return Team(
            id=espn_team.team_id,
            name=espn_team.team_name,
            abbreviation=espn_team.team_abbrev,
            owner=self._extract_owner_name(espn_team),
            division=division,
            logo=self._extract_logo_url(espn_team.team_name, espn_team),
            wins=wins,
            losses=losses,
            ties=ties,
            points_for=points_for,
            points_against=points_against,
            standing=standing,
            playoff_pct=playoff_pct
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

    def _extract_logo_url(self, team_name: str, espn_team: Any) -> Optional[str]:
        """
        Extract logo URL using custom team logo configuration, with ESPN fallback.

        Args:
            team_name: Team name for logo lookup
            espn_team: ESPN team object (used as fallback)

        Returns:
            Logo URL as string or None if not available
        """
        try:
            # First priority: Use custom team logo configuration
            custom_logo_url = get_team_logo_url(team_name)
            if custom_logo_url:
                self.logger.debug(f"Using custom logo for {team_name}: {custom_logo_url}")
                return custom_logo_url

            # Fallback: Try ESPN logo sources
            self.logger.debug(f"No custom logo found for {team_name}, trying ESPN sources")

            # Try to get logo_url directly from team
            if hasattr(espn_team, 'logo_url') and espn_team.logo_url:
                self.logger.debug(f"Using ESPN logo for {team_name}: {espn_team.logo_url}")
                return espn_team.logo_url

            # Try alternative ESPN attribute names
            for attr in ['logoUrl', 'logo', 'avatar_url', 'avatarUrl']:
                if hasattr(espn_team, attr):
                    value = getattr(espn_team, attr)
                    if value:
                        self.logger.debug(f"Using ESPN logo ({attr}) for {team_name}: {value}")
                        return value

            self.logger.info(f"No logo found for {team_name} from custom config or ESPN")
            return None

        except Exception as e:
            self.logger.warning(f"Failed to extract logo URL for {team_name}: {e}")
            return None

    def _determine_team_division(self, espn_team: Any) -> str:
        """
        Determine which division a team belongs to.

        Args:
            espn_team: ESPN team object

        Returns:
            Division name
        """
        # First try to get division name directly from team (most reliable)
        if hasattr(espn_team, 'division_name') and espn_team.division_name:
            return espn_team.division_name

        # Fallback: try to get division mapping from league settings
        if hasattr(espn_team, 'division_id'):
            try:
                league = self.espn_client.get_league()
                if hasattr(league.settings, 'division_map'):
                    division_map = league.settings.division_map
                    return division_map.get(espn_team.division_id, f"Division {espn_team.division_id}")
            except Exception as e:
                self.logger.warning(f"Could not get division mapping from league settings: {e}")

            # Generic fallback if we have division_id but no mapping
            return f"Division {espn_team.division_id}"

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
        Return teams as-is since ranking will be calculated in aggregate stage.

        Args:
            teams: List of teams

        Returns:
            List of teams (no ranking applied)
        """
        # No ranking applied here - will be calculated in aggregate stage
        # based on actual wins/losses/points from matchup data
        return teams

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
        Get all teams (standings will be calculated in aggregate stage).

        Returns:
            List of all teams (no ranking applied)
        """
        divisions = self.extract()

        # Collect all teams
        all_teams = []
        for division in divisions:
            all_teams.extend(division.teams)

        # No ranking applied here - will be calculated in aggregate stage
        return all_teams