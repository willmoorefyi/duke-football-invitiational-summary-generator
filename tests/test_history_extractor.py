"""
Tests for history extractor.
"""

import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.extractors.history_extractor import HistoryExtractor
from src.models.history_models import (
    SeasonHistory, LeagueHistory, ChampionSummary,
    DivisionInfo, LeagueHistoryMetadata
)


class TestHistoryExtractor:
    """Test HistoryExtractor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = HistoryExtractor(
            league_id=123456,
            espn_s2="test_espn_s2",
            swid="test_swid"
        )

    def _create_mock_team(self, team_id, team_name, team_abbrev, division_id, division_name,
                          wins, losses, ties, points_for, points_against, final_standing, standing):
        """Helper to create a mock team object."""
        team = Mock()
        team.team_id = team_id
        team.team_name = team_name
        team.team_abbrev = team_abbrev
        team.division_id = division_id
        team.division_name = division_name
        team.wins = wins
        team.losses = losses
        team.ties = ties
        team.points_for = points_for
        team.points_against = points_against
        team.final_standing = final_standing
        team.standing = standing
        team.owners = [{'firstName': 'John', 'lastName': 'Doe', 'id': 'owner123'}]
        return team

    def _create_mock_league(self, standings):
        """Helper to create a mock league object."""
        league = Mock()
        league.standings = Mock(return_value=standings)
        league.settings = Mock()
        league.settings.name = "Test League"
        league.settings.reg_season_count = 14
        league.settings.playoff_team_count = 6
        return league

    def test_get_owner_name_with_owners(self):
        """Test getting owner name from owner list."""
        owners = [{'firstName': 'John', 'lastName': 'Doe', 'id': 'owner123'}]
        result = self.extractor._get_owner_name(owners)
        assert result == "John Doe"

    def test_get_owner_name_empty_list(self):
        """Test getting owner name with empty list."""
        result = self.extractor._get_owner_name([])
        assert result == "Unknown Owner"

    def test_get_owner_name_missing_fields(self):
        """Test getting owner name with missing fields."""
        owners = [{'id': 'owner123'}]
        result = self.extractor._get_owner_name(owners)
        assert result == "Unknown Owner"

    def test_extract_owner_info(self):
        """Test extracting owner information."""
        owners = [
            {'firstName': 'John', 'lastName': 'Doe', 'id': 'owner123'},
            {'firstName': 'Jane', 'lastName': 'Smith', 'id': 'owner456'}
        ]
        result = self.extractor._extract_owner_info(owners)
        assert len(result) == 2
        assert result[0].first_name == 'John'
        assert result[0].last_name == 'Doe'
        assert result[1].first_name == 'Jane'

    def test_get_championship_title_champion(self):
        """Test getting championship title for champion."""
        result = self.extractor._get_championship_title(1)
        assert result == "Champion"

    def test_get_championship_title_runner_up(self):
        """Test getting championship title for runner-up."""
        result = self.extractor._get_championship_title(2)
        assert result == "Runner-up"

    def test_get_championship_title_third_place(self):
        """Test getting championship title for third place."""
        result = self.extractor._get_championship_title(3)
        assert result == "Third Place"

    def test_get_championship_title_other(self):
        """Test getting championship title for other positions."""
        result = self.extractor._get_championship_title(4)
        assert result is None

    @patch('src.extractors.history_extractor.League')
    def test_extract_season_success(self, mock_league_class):
        """Test successful season extraction."""
        # Create mock teams
        team1 = self._create_mock_team(
            1, "Team Alpha", "ALPH", 0, "North",
            12, 2, 0, 1543.50, 1287.25, 1, 1
        )
        team2 = self._create_mock_team(
            2, "Team Beta", "BETA", 1, "South",
            11, 3, 0, 1487.25, 1312.50, 2, 2
        )
        team3 = self._create_mock_team(
            3, "Team Gamma", "GAMM", 0, "North",
            10, 4, 0, 1421.75, 1350.00, 3, 3
        )

        # Setup mock league
        mock_league = self._create_mock_league([team1, team2, team3])
        mock_league_class.return_value = mock_league

        # Extract season
        result = self.extractor.extract_season(2024)

        # Verify results
        assert result is not None
        assert isinstance(result, SeasonHistory)
        assert result.year == 2024
        assert result.total_teams == 3
        assert len(result.final_standings) == 3
        assert result.champion.team_name == "Team Alpha"
        assert result.runner_up.team_name == "Team Beta"
        assert result.third_place.team_name == "Team Gamma"

    @patch('src.extractors.history_extractor.League')
    def test_extract_season_no_standings(self, mock_league_class):
        """Test season extraction with no standings."""
        mock_league = self._create_mock_league([])
        mock_league_class.return_value = mock_league

        result = self.extractor.extract_season(2024)
        assert result is None

    @patch('src.extractors.history_extractor.League')
    def test_extract_season_with_exception(self, mock_league_class):
        """Test season extraction with exception."""
        mock_league_class.side_effect = Exception("API Error")

        result = self.extractor.extract_season(2024)
        assert result is None

    @patch('src.extractors.history_extractor.League')
    def test_extract_season_only_champion(self, mock_league_class):
        """Test season extraction with only champion (single team)."""
        team1 = self._create_mock_team(
            1, "Team Alpha", "ALPH", 0, "Main",
            14, 0, 0, 1600.00, 1100.00, 1, 1
        )

        mock_league = self._create_mock_league([team1])
        mock_league_class.return_value = mock_league

        result = self.extractor.extract_season(2024)

        assert result is not None
        assert result.champion.team_name == "Team Alpha"
        assert result.runner_up is None
        assert result.third_place is None

    @patch('src.extractors.history_extractor.League')
    def test_extract_season_two_teams(self, mock_league_class):
        """Test season extraction with two teams (no third place)."""
        team1 = self._create_mock_team(
            1, "Team Alpha", "ALPH", 0, "Main",
            12, 2, 0, 1543.50, 1287.25, 1, 1
        )
        team2 = self._create_mock_team(
            2, "Team Beta", "BETA", 0, "Main",
            11, 3, 0, 1487.25, 1312.50, 2, 2
        )

        mock_league = self._create_mock_league([team1, team2])
        mock_league_class.return_value = mock_league

        result = self.extractor.extract_season(2024)

        assert result is not None
        assert result.champion.team_name == "Team Alpha"
        assert result.runner_up.team_name == "Team Beta"
        assert result.third_place is None

    @patch('src.extractors.history_extractor.League')
    def test_extract_season_divisions(self, mock_league_class):
        """Test division extraction in season."""
        team1 = self._create_mock_team(
            1, "Team Alpha", "ALPH", 0, "North",
            12, 2, 0, 1543.50, 1287.25, 1, 1
        )
        team2 = self._create_mock_team(
            2, "Team Beta", "BETA", 1, "South",
            11, 3, 0, 1487.25, 1312.50, 2, 2
        )
        team3 = self._create_mock_team(
            3, "Team Gamma", "GAMM", 0, "North",
            10, 4, 0, 1421.75, 1350.00, 3, 3
        )

        mock_league = self._create_mock_league([team1, team2, team3])
        mock_league_class.return_value = mock_league

        result = self.extractor.extract_season(2024)

        assert result is not None
        assert len(result.divisions) == 2

        # Find North and South divisions
        north_div = next((d for d in result.divisions if d.division_name == "North"), None)
        south_div = next((d for d in result.divisions if d.division_name == "South"), None)

        assert north_div is not None
        assert len(north_div.teams) == 2
        assert "Team Alpha" in north_div.teams
        assert "Team Gamma" in north_div.teams

        assert south_div is not None
        assert len(south_div.teams) == 1
        assert "Team Beta" in south_div.teams

    @patch('src.extractors.history_extractor.League')
    def test_extract_history_multiple_years(self, mock_league_class):
        """Test extracting history for multiple years."""
        # Mock different teams for different years
        def create_league_for_year(year):
            team1 = self._create_mock_team(
                1, f"Champion {year}", "CHMP", 0, "Main",
                12, 2, 0, 1500.00, 1200.00, 1, 1
            )
            team2 = self._create_mock_team(
                2, f"Runner-up {year}", "RNUP", 0, "Main",
                10, 4, 0, 1400.00, 1300.00, 2, 2
            )
            return self._create_mock_league([team1, team2])

        # Setup mock to return different leagues for different years
        mock_league_class.side_effect = [
            create_league_for_year(2022),
            create_league_for_year(2022),  # Called twice (standings + league name)
            create_league_for_year(2023),
            create_league_for_year(2024),
        ]

        result = self.extractor.extract_history(2022, 2024)

        assert isinstance(result, LeagueHistory)
        assert len(result.seasons) == 3
        assert result.seasons[0].year == 2022
        assert result.seasons[1].year == 2023
        assert result.seasons[2].year == 2024
        assert result.metadata.total_seasons == 3
        assert result.metadata.year_range == "2022-2024"

    @patch('src.extractors.history_extractor.League')
    def test_extract_history_with_league_name(self, mock_league_class):
        """Test extracting history with provided league name."""
        team1 = self._create_mock_team(
            1, "Team Alpha", "ALPH", 0, "Main",
            12, 2, 0, 1543.50, 1287.25, 1, 1
        )
        mock_league = self._create_mock_league([team1])
        mock_league_class.return_value = mock_league

        result = self.extractor.extract_history(2024, 2024, league_name="Custom League Name")

        assert result.league_name == "Custom League Name"
        assert len(result.seasons) == 1

    @patch('src.extractors.history_extractor.League')
    def test_extract_history_no_successful_seasons(self, mock_league_class):
        """Test extracting history when all seasons fail."""
        mock_league_class.side_effect = Exception("API Error")

        result = self.extractor.extract_history(2022, 2024)

        assert isinstance(result, LeagueHistory)
        assert len(result.seasons) == 0
        assert result.metadata.total_seasons == 0

    def test_save_to_json_success(self):
        """Test saving league history to JSON file."""
        # Create a simple league history object
        league_history = LeagueHistory(
            league_id="123456",
            league_name="Test League",
            seasons=[
                SeasonHistory(
                    year=2024,
                    regular_season_weeks=14,
                    playoff_weeks=3,
                    total_teams=2,
                    divisions=[DivisionInfo(division_id=0, division_name="Main", teams=["Team A", "Team B"])],
                    final_standings=[],
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

        # Use temporary directory for test
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = self.extractor.save_to_json(league_history, output_dir=tmpdir)

            # Verify file was created
            assert os.path.exists(filepath)
            assert filepath.startswith(tmpdir)
            assert "league_history_123456_2024-2024" in filepath
            assert filepath.endswith(".json")

            # Verify file contents
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            assert data["league_id"] == "123456"
            assert data["league_name"] == "Test League"
            assert len(data["seasons"]) == 1
            assert data["seasons"][0]["year"] == 2024

    def test_save_to_json_creates_directory(self):
        """Test that save_to_json creates output directory if it doesn't exist."""
        league_history = LeagueHistory(
            league_id="123456",
            league_name="Test League",
            seasons=[],
            metadata=LeagueHistoryMetadata(
                extracted_at="2025-01-15T10:30:00Z",
                total_seasons=0,
                year_range="N/A"
            )
        )

        # Use temporary directory with nested path
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = os.path.join(tmpdir, "nested", "path", "history")
            filepath = self.extractor.save_to_json(league_history, output_dir=nested_dir)

            # Verify directory was created
            assert os.path.exists(nested_dir)
            assert os.path.exists(filepath)

    def test_save_to_json_preserves_data(self):
        """Test that JSON serialization preserves all data correctly."""
        league_history = LeagueHistory(
            league_id="123456",
            league_name="Test League",
            seasons=[
                SeasonHistory(
                    year=2024,
                    regular_season_weeks=14,
                    playoff_weeks=3,
                    total_teams=3,
                    divisions=[
                        DivisionInfo(division_id=0, division_name="North", teams=["Team A", "Team B"]),
                        DivisionInfo(division_id=1, division_name="South", teams=["Team C"])
                    ],
                    final_standings=[],
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
            ],
            metadata=LeagueHistoryMetadata(
                extracted_at="2025-01-15T10:30:00Z",
                total_seasons=1,
                year_range="2024-2024"
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = self.extractor.save_to_json(league_history, output_dir=tmpdir)

            # Load and verify all data is preserved
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Verify divisions
            assert len(data["seasons"][0]["divisions"]) == 2
            assert data["seasons"][0]["divisions"][0]["division_name"] == "North"
            assert len(data["seasons"][0]["divisions"][0]["teams"]) == 2

            # Verify champion data
            champion = data["seasons"][0]["champion"]
            assert champion["team_name"] == "Team A"
            assert champion["wins"] == 12
            assert champion["points_for"] == 1543.50

            # Verify third place exists
            third_place = data["seasons"][0]["third_place"]
            assert third_place is not None
            assert third_place["team_name"] == "Team C"
