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


class PlayerAward(BaseModel):
    """Award for individual players."""
    player_name: str
    team_name: str
    position: str
    score: float


class TeamAward(BaseModel):
    """Award for teams."""
    team_name: str
    score: float
    additional_info: Optional[str] = None


class LineupEfficiencyAward(BaseModel):
    """Award for lineup management efficiency."""
    team_name: str
    actual_score: float
    optimal_score: float
    efficiency_percentage: float
    additional_info: Optional[str] = None


class CollapseAward(BaseModel):
    """Award for teams that collapsed (would have won with optimal lineup)."""
    team_name: str
    actual_score: float
    optimal_score: float
    opponent_score: float
    points_difference: float  # How much they lost by with actual vs would have won by with optimal


class ProjectionFailAward(BaseModel):
    """Award for teams that were projected to win but lost."""
    team_name: str
    projected_score: float
    actual_score: float
    opponent_projected_score: float
    opponent_actual_score: float


class HonorableMention(BaseModel):
    """Honorable mention for awards with multiple eligible teams."""
    award_type: str  # 'mccollapse' or 'clapper_collapse'
    award_name: str  # Full award name (e.g., 'Mike McCoy "McCollapse" Award')
    team_name: str
    primary_stat: float  # actual_score for mccollapse, projected_score for clapper
    secondary_stat: float  # optimal_score for mccollapse, actual_score for clapper
    stat_difference: float  # The difference used for ranking
    description: str  # Formatted description for display


class WeeklyAwards(BaseModel):
    """All awards for a given week."""
    mvp: Optional[PlayerAward] = None  # Most Valuable Player
    mwp: Optional[PlayerAward] = None  # Most Wasted Player
    mup: Optional[PlayerAward] = None  # Most Useless Player
    mdp: Optional[PlayerAward] = None  # Most Disrespected Player
    hsl: Optional[TeamAward] = None    # Highest Scoring Loser
    lsw: Optional[TeamAward] = None    # Lowest Scoring Winner
    ssl: Optional[LineupEfficiencyAward] = None  # Smartest Starting Lineup
    ifm: Optional[LineupEfficiencyAward] = None  # I Fucked Myself (losing team with worst lineup)
    accidental_genius: Optional[LineupEfficiencyAward] = None  # Winning team with worst lineup
    mccollapse: List[CollapseAward] = Field(default_factory=list)  # McCollapse awards
    clapper_collapse: List[ProjectionFailAward] = Field(default_factory=list)  # Clapper Collapse awards
    honorable_mentions: List[HonorableMention] = Field(default_factory=list)  # Honorable mentions for awards with multiple eligible teams


class WeeklyReport(BaseModel):
    league_id: int
    league_name: str
    season: int
    week: int
    report_date: datetime
    divisions: List[Division]
    matchups: List[Matchup]
    injured_starters: List[InjuredStarter]
    awards: WeeklyAwards
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }