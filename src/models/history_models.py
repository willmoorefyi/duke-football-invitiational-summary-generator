"""
Pydantic models for league history data.

This module defines the data structures for historical league information,
including season standings, champions, and league metadata.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class OwnerInfo(BaseModel):
    """Owner information for a team."""
    first_name: str
    last_name: str
    id: str

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DivisionInfo(BaseModel):
    """Division information including teams."""
    division_id: int
    division_name: str
    teams: List[str]  # List of team names in this division


class TeamSeasonStanding(BaseModel):
    """Complete team standing information for a season."""
    rank: int
    team_id: int
    team_name: str
    team_abbrev: str
    owners: List[OwnerInfo]
    division_id: int
    division_name: str
    wins: int
    losses: int
    ties: int
    points_for: float
    points_against: float
    playoff_seed: int
    final_standing: int
    championship_title: Optional[str] = None  # "Champion", "Runner-up", "Third Place", etc.


class ChampionSummary(BaseModel):
    """Summary information for top finishers (champion, runner-up, third place)."""
    team_id: int
    team_name: str
    owner_name: str
    wins: int
    losses: int
    points_for: float


class SeasonHistory(BaseModel):
    """Complete history for a single season."""
    year: int
    regular_season_weeks: int
    playoff_weeks: int
    total_teams: int
    divisions: List[DivisionInfo]
    final_standings: List[TeamSeasonStanding]
    champion: ChampionSummary
    runner_up: Optional[ChampionSummary] = None
    third_place: Optional[ChampionSummary] = None


class TeamIdentifierMapping(BaseModel):
    """Track team name changes and owner changes over time."""
    team_id: int
    historical_names: List[str]
    current_name: str
    first_seen_year: int
    last_seen_year: int
    all_owners: List[Dict[str, Any]]  # [{"name": "John Doe", "years": [2020, 2021]}]


class LeagueHistoryMetadata(BaseModel):
    """Metadata about the league history extraction."""
    extracted_at: str
    total_seasons: int
    year_range: str
    extractor_version: str = "1.0.0"


class LeagueHistory(BaseModel):
    """Complete league history across all seasons."""
    league_id: str
    league_name: str
    seasons: List[SeasonHistory]
    metadata: LeagueHistoryMetadata

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
