"""
Team Logo Utility Functions

Provides easy access to team logo URLs for use throughout the application.
"""

from typing import Optional
from .config import get_config


def get_team_logo_url(team_name: str) -> Optional[str]:
    """
    Get the full logo URL for a team name.

    Args:
        team_name: The exact team name as it appears in ESPN data

    Returns:
        Full URL to the team's logo, or None if not found

    Example:
        >>> get_team_logo_url("All About That Bass")
        'https://will.moore.fyi/duke-football-invitational/static/AllAboutThatBassAll2.png'
    """
    config = get_config()
    return config.team_logos.get_logo_url(team_name)


def get_all_team_logos() -> dict[str, str]:
    """
    Get all team logo mappings.

    Returns:
        Dictionary mapping team names to their full logo URLs
    """
    config = get_config()
    return {
        team_name: config.team_logos.get_logo_url(team_name)
        for team_name in config.team_logos.teams.keys()
    }


def update_team_data_with_logos(teams_data: list) -> list:
    """
    Update a list of team dictionaries with their logo URLs.

    Args:
        teams_data: List of team dictionaries (from ESPN extract)

    Returns:
        Updated list with 'logo_url' field added to each team

    Example:
        >>> teams = [{"name": "All About That Bass", "wins": 5}]
        >>> updated_teams = update_team_data_with_logos(teams)
        >>> print(updated_teams[0]["logo_url"])
        'https://will.moore.fyi/duke-football-invitational/static/AllAboutThatBassAll2.png'
    """
    config = get_config()

    for team in teams_data:
        if isinstance(team, dict) and 'name' in team:
            logo_url = config.team_logos.get_logo_url(team['name'])
            if logo_url:
                team['logo_url'] = logo_url

    return teams_data