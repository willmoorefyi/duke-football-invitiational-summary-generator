"""
Tests for league history data models.
"""

import pytest
from datetime import datetime
from src.models.history_models import (
    OwnerInfo,
    DivisionInfo,
    TeamSeasonStanding,
    ChampionSummary,
    SeasonHistory,
    TeamIdentifierMapping,
    LeagueHistoryMetadata,
    LeagueHistory
)


class TestOwnerInfo:
    """Test OwnerInfo model."""

    def test_owner_info_valid(self):
        """Test valid owner info creation."""
        owner = OwnerInfo(
            first_name="John",
            last_name="Doe",
            id="owner123"
        )
        assert owner.first_name == "John"
        assert owner.last_name == "Doe"
        assert owner.id == "owner123"

    def test_owner_info_serialization(self):
        """Test owner info JSON serialization."""
        owner = OwnerInfo(
            first_name="Jane",
            last_name="Smith",
            id="owner456"
        )
        data = owner.model_dump()
        assert data["first_name"] == "Jane"
        assert data["last_name"] == "Smith"
        assert data["id"] == "owner456"


class TestDivisionInfo:
    """Test DivisionInfo model."""

    def test_division_info_valid(self):
        """Test valid division info creation."""
        division = DivisionInfo(
            division_id=0,
            division_name="North",
            teams=["Team A", "Team B", "Team C"]
        )
        assert division.division_id == 0
        assert division.division_name == "North"
        assert len(division.teams) == 3

    def test_division_info_empty_teams(self):
        """Test division with no teams."""
        division = DivisionInfo(
            division_id=1,
            division_name="South",
            teams=[]
        )
        assert len(division.teams) == 0


class TestTeamSeasonStanding:
    """Test TeamSeasonStanding model."""

    def test_team_standing_complete(self):
        """Test complete team standing creation."""
        standing = TeamSeasonStanding(
            rank=1,
            team_id=1,
            team_name="Team Alpha",
            team_abbrev="ALPH",
            owners=[OwnerInfo(first_name="John", last_name="Doe", id="owner123")],
            division_id=0,
            division_name="North",
            wins=12,
            losses=2,
            ties=0,
            points_for=1543.50,
            points_against=1287.25,
            playoff_seed=1,
            final_standing=1,
            championship_title="Champion"
        )
        assert standing.rank == 1
        assert standing.championship_title == "Champion"
        assert standing.wins == 12
        assert standing.points_for == 1543.50

    def test_team_standing_no_championship_title(self):
        """Test team standing without championship title."""
        standing = TeamSeasonStanding(
            rank=5,
            team_id=5,
            team_name="Team Echo",
            team_abbrev="ECHO",
            owners=[OwnerInfo(first_name="Bob", last_name="Jones", id="owner789")],
            division_id=1,
            division_name="South",
            wins=8,
            losses=6,
            ties=0,
            points_for=1200.00,
            points_against=1250.00,
            playoff_seed=5,
            final_standing=5
        )
        assert standing.championship_title is None

    def test_team_standing_with_ties(self):
        """Test team standing with tie games."""
        standing = TeamSeasonStanding(
            rank=3,
            team_id=3,
            team_name="Team Gamma",
            team_abbrev="GAMM",
            owners=[OwnerInfo(first_name="Alice", last_name="Brown", id="owner456")],
            division_id=0,
            division_name="North",
            wins=9,
            losses=3,
            ties=2,
            points_for=1350.75,
            points_against=1300.50,
            playoff_seed=3,
            final_standing=3,
            championship_title="Third Place"
        )
        assert standing.ties == 2
        assert standing.championship_title == "Third Place"


class TestChampionSummary:
    """Test ChampionSummary model."""

    def test_champion_summary_valid(self):
        """Test valid champion summary creation."""
        champion = ChampionSummary(
            team_id=1,
            team_name="Team Alpha",
            owner_name="John Doe",
            wins=12,
            losses=2,
            points_for=1543.50
        )
        assert champion.team_id == 1
        assert champion.owner_name == "John Doe"
        assert champion.wins == 12


class TestSeasonHistory:
    """Test SeasonHistory model."""

    def test_season_history_complete(self):
        """Test complete season history creation."""
        season = SeasonHistory(
            year=2024,
            regular_season_weeks=14,
            playoff_weeks=3,
            total_teams=12,
            divisions=[
                DivisionInfo(division_id=0, division_name="North", teams=["Team A", "Team B"]),
                DivisionInfo(division_id=1, division_name="South", teams=["Team C", "Team D"])
            ],
            final_standings=[
                TeamSeasonStanding(
                    rank=1, team_id=1, team_name="Team A", team_abbrev="TEMA",
                    owners=[OwnerInfo(first_name="John", last_name="Doe", id="owner1")],
                    division_id=0, division_name="North",
                    wins=12, losses=2, ties=0,
                    points_for=1543.50, points_against=1287.25,
                    playoff_seed=1, final_standing=1, championship_title="Champion"
                ),
                TeamSeasonStanding(
                    rank=2, team_id=2, team_name="Team B", team_abbrev="TEMB",
                    owners=[OwnerInfo(first_name="Jane", last_name="Smith", id="owner2")],
                    division_id=1, division_name="South",
                    wins=11, losses=3, ties=0,
                    points_for=1487.25, points_against=1312.50,
                    playoff_seed=2, final_standing=2, championship_title="Runner-up"
                )
            ],
            champion=ChampionSummary(
                team_id=1, team_name="Team A", owner_name="John Doe",
                wins=12, losses=2, points_for=1543.50
            ),
            runner_up=ChampionSummary(
                team_id=2, team_name="Team B", owner_name="Jane Smith",
                wins=11, losses=3, points_for=1487.25
            ),
            third_place=ChampionSummary(
                team_id=3, team_name="Team C", owner_name="Bob Jones",
                wins=10, losses=4, points_for=1421.75
            )
        )
        assert season.year == 2024
        assert season.total_teams == 12
        assert len(season.divisions) == 2
        assert len(season.final_standings) == 2
        assert season.champion.team_name == "Team A"
        assert season.third_place is not None

    def test_season_history_no_third_place(self):
        """Test season history without third place."""
        season = SeasonHistory(
            year=2023,
            regular_season_weeks=14,
            playoff_weeks=3,
            total_teams=8,
            divisions=[DivisionInfo(division_id=0, division_name="Main", teams=["Team A"])],
            final_standings=[
                TeamSeasonStanding(
                    rank=1, team_id=1, team_name="Team A", team_abbrev="TEMA",
                    owners=[OwnerInfo(first_name="John", last_name="Doe", id="owner1")],
                    division_id=0, division_name="Main",
                    wins=11, losses=3, ties=0,
                    points_for=1400.00, points_against=1200.00,
                    playoff_seed=1, final_standing=1, championship_title="Champion"
                )
            ],
            champion=ChampionSummary(
                team_id=1, team_name="Team A", owner_name="John Doe",
                wins=11, losses=3, points_for=1400.00
            ),
            runner_up=ChampionSummary(
                team_id=2, team_name="Team B", owner_name="Jane Smith",
                wins=10, losses=4, points_for=1350.00
            )
        )
        assert season.third_place is None


class TestTeamIdentifierMapping:
    """Test TeamIdentifierMapping model."""

    def test_team_identifier_mapping_valid(self):
        """Test valid team identifier mapping."""
        mapping = TeamIdentifierMapping(
            team_id=1,
            historical_names=["Team Alpha", "Alpha Squad", "The Alphas"],
            current_name="Team Alpha",
            first_seen_year=2020,
            last_seen_year=2024,
            all_owners=[
                {"name": "John Doe", "years": [2020, 2021, 2022]},
                {"name": "Mike Smith", "years": [2023, 2024]}
            ]
        )
        assert mapping.team_id == 1
        assert len(mapping.historical_names) == 3
        assert len(mapping.all_owners) == 2


class TestLeagueHistoryMetadata:
    """Test LeagueHistoryMetadata model."""

    def test_metadata_valid(self):
        """Test valid metadata creation."""
        metadata = LeagueHistoryMetadata(
            extracted_at="2025-01-15T10:30:00Z",
            total_seasons=5,
            year_range="2020-2024"
        )
        assert metadata.total_seasons == 5
        assert metadata.year_range == "2020-2024"
        assert metadata.extractor_version == "1.0.0"

    def test_metadata_custom_version(self):
        """Test metadata with custom version."""
        metadata = LeagueHistoryMetadata(
            extracted_at="2025-01-15T10:30:00Z",
            total_seasons=3,
            year_range="2022-2024",
            extractor_version="2.0.0"
        )
        assert metadata.extractor_version == "2.0.0"


class TestLeagueHistory:
    """Test LeagueHistory model."""

    def test_league_history_complete(self):
        """Test complete league history creation."""
        history = LeagueHistory(
            league_id="123456",
            league_name="Duke Football Invitational",
            seasons=[
                SeasonHistory(
                    year=2024,
                    regular_season_weeks=14,
                    playoff_weeks=3,
                    total_teams=12,
                    divisions=[DivisionInfo(division_id=0, division_name="North", teams=["Team A"])],
                    final_standings=[
                        TeamSeasonStanding(
                            rank=1, team_id=1, team_name="Team A", team_abbrev="TEMA",
                            owners=[OwnerInfo(first_name="John", last_name="Doe", id="owner1")],
                            division_id=0, division_name="North",
                            wins=12, losses=2, ties=0,
                            points_for=1543.50, points_against=1287.25,
                            playoff_seed=1, final_standing=1, championship_title="Champion"
                        )
                    ],
                    champion=ChampionSummary(
                        team_id=1, team_name="Team A", owner_name="John Doe",
                        wins=12, losses=2, points_for=1543.50
                    ),
                    runner_up=ChampionSummary(
                        team_id=2, team_name="Team B", owner_name="Jane Smith",
                        wins=11, losses=3, points_for=1487.25
                    )
                )
            ],
            metadata=LeagueHistoryMetadata(
                extracted_at="2025-01-15T10:30:00Z",
                total_seasons=1,
                year_range="2024-2024"
            )
        )
        assert history.league_id == "123456"
        assert history.league_name == "Duke Football Invitational"
        assert len(history.seasons) == 1
        assert history.seasons[0].year == 2024

    def test_league_history_json_serialization(self):
        """Test league history JSON serialization."""
        history = LeagueHistory(
            league_id="123456",
            league_name="Test League",
            seasons=[],
            metadata=LeagueHistoryMetadata(
                extracted_at="2025-01-15T10:30:00Z",
                total_seasons=0,
                year_range="N/A"
            )
        )
        data = history.model_dump()
        assert data["league_id"] == "123456"
        assert data["league_name"] == "Test League"
        assert isinstance(data["seasons"], list)
        assert isinstance(data["metadata"], dict)
