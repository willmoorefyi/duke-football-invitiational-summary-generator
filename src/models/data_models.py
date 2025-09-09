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
    position: str
    team: str
    projected_score: float
    actual_score: float
    is_starter: bool
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
    division_rank: int


class Matchup(BaseModel):
    week: int
    home_team: Team
    away_team: Team
    home_score: float
    away_score: float
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