from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class InjuryStatus(str, Enum):
    HEALTHY = "HEALTHY"
    QUESTIONABLE = "QUESTIONABLE"
    DOUBTFUL = "DOUBTFUL"
    OUT = "OUT"
    IR = "IR"
    UNKNOWN = "UNKNOWN"


class Player(BaseModel):
    name: str
    position: str  # NFL position (QB, RB, WR, TE, etc.)
    roster_slot: Optional[str] = None  # Fantasy roster slot (QB, RB, WR, TE, OP, FLEX, BE, IR, etc.)
    team: str
    projected_score: float
    actual_score: float
    is_starter: bool
    should_have_started: Optional[bool] = None  # Whether this player should have been in optimal lineup
    injury_status: InjuryStatus = InjuryStatus.UNKNOWN


class Team(BaseModel):
    id: int
    name: str
    abbreviation: str
    owner: str
    division: str
    wins: int
    losses: int
    ties: int = 0
    points_for: float
    points_against: float
    overall_rank: int  # Overall league ranking from ESPN
    division_rank: int  # Rank within division (derived from overall_rank)
    logo: Optional[str] = None  # Team logo URL


class Matchup(BaseModel):
    week: int
    home_team: Team
    away_team: Team
    home_score: float
    away_score: float
    home_projected_score: Optional[float] = None  # Projected score of all starters
    away_projected_score: Optional[float] = None  # Projected score of all starters
    home_optimal_score: Optional[float] = None  # Optimal score if best lineup was used
    away_optimal_score: Optional[float] = None  # Optimal score if best lineup was used
    winner_id: Optional[int] = None
    loser_id: Optional[int] = None
    is_complete: bool
    players: List[Player]


class Division(BaseModel):
    name: str
    teams: List[Team]


class InjuredStarter(BaseModel):
    player_name: str
    team_name: str
    position: str
    injury_status: InjuryStatus


class WeeklyReport(BaseModel):
    league_id: int
    league_name: str
    season: int
    week: int
    report_date: datetime
    divisions: List[Division]
    matchups: List[Matchup]
    injured_starters: List[InjuredStarter]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }