"""
Tests for history uploader.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch
from src.uploaders.history_uploader import HistoryUploader
from src.models.history_models import (
    LeagueHistory, SeasonHistory, ChampionSummary,
    DivisionInfo, LeagueHistoryMetadata
)


class TestHistoryUploader:
    """Test HistoryUploader class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock DynamoDB resource and table
        self.mock_dynamodb = Mock()
        self.mock_table = Mock()
        self.mock_dynamodb.Table.return_value = self.mock_table

        self.uploader = HistoryUploader(
            dynamodb_resource=self.mock_dynamodb,
            table_name="test-table"
        )

    def _create_test_league_history(self):
        """Create a test LeagueHistory object."""
        return LeagueHistory(
            league_id="123456",
            league_name="Test League",
            seasons=[
                SeasonHistory(
                    year=2024,
                    regular_season_weeks=14,
                    playoff_weeks=3,
                    total_teams=12,
                    divisions=[
                        DivisionInfo(division_id=0, division_name="North", teams=["Team A", "Team B"]),
                        DivisionInfo(division_id=1, division_name="South", teams=["Team C", "Team D"])
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
                ),
                SeasonHistory(
                    year=2023,
                    regular_season_weeks=14,
                    playoff_weeks=3,
                    total_teams=12,
                    divisions=[
                        DivisionInfo(division_id=0, division_name="North", teams=["Team A", "Team B"])
                    ],
                    final_standings=[],
                    champion=ChampionSummary(
                        team_id=2, team_name="Team B", owner_name="Jane Smith",
                        wins=13, losses=1, points_for=1612.00
                    ),
                    runner_up=ChampionSummary(
                        team_id=1, team_name="Team A", owner_name="John Doe",
                        wins=11, losses=3, points_for=1523.50
                    )
                )
            ],
            metadata=LeagueHistoryMetadata(
                extracted_at="2025-01-15T10:30:00Z",
                total_seasons=2,
                year_range="2023-2024"
            )
        )

    def test_convert_floats_to_decimal(self):
        """Test float to Decimal conversion."""
        obj = {
            "float_val": 123.45,
            "int_val": 100,
            "string_val": "test",
            "list_val": [1.5, 2.5, 3.5],
            "nested": {
                "inner_float": 99.99,
                "inner_list": [1.1, 2.2]
            }
        }

        result = self.uploader._convert_floats_to_decimal(obj)

        assert isinstance(result["float_val"], Decimal)
        assert result["float_val"] == Decimal("123.45")
        assert isinstance(result["int_val"], int)
        assert isinstance(result["list_val"][0], Decimal)
        assert isinstance(result["nested"]["inner_float"], Decimal)
        assert result["string_val"] == "test"

    def test_create_metadata_record(self):
        """Test metadata record creation."""
        league_history = self._create_test_league_history()
        record = self.uploader._create_metadata_record(league_history)

        assert record["season_week"] == "HISTORY#123456"
        assert record["data_type_id"] == "METADATA"
        assert record["league_id"] == "123456"
        assert record["league_name"] == "Test League"
        assert record["total_seasons"] == 2
        assert record["year_range"] == "2023-2024"
        assert record["seasons_list"] == [2024, 2023]
        assert "extracted_at" in record
        assert "last_updated" in record

    def test_create_season_record(self):
        """Test season record creation."""
        league_history = self._create_test_league_history()
        season = league_history.seasons[0]

        record = self.uploader._create_season_record("123456", season)

        assert record["season_week"] == "HISTORY#123456"
        assert record["data_type_id"] == "SEASON#2024"
        assert record["league_id"] == "123456"
        assert record["year"] == 2024
        assert record["regular_season_weeks"] == 14
        assert record["playoff_weeks"] == 3
        assert record["total_teams"] == 12
        assert len(record["divisions"]) == 2
        assert record["champion"]["team_name"] == "Team A"
        assert record["runner_up"]["team_name"] == "Team B"
        assert record["third_place"]["team_name"] == "Team C"
        assert "extracted_at" in record

    def test_create_season_record_float_conversion(self):
        """Test that floats are converted to Decimal in season records."""
        league_history = self._create_test_league_history()
        season = league_history.seasons[0]

        record = self.uploader._create_season_record("123456", season)

        # Check that points_for is converted to Decimal
        assert isinstance(record["champion"]["points_for"], Decimal)
        assert record["champion"]["points_for"] == Decimal("1543.50")

    def test_upload_league_history_success(self):
        """Test successful league history upload."""
        league_history = self._create_test_league_history()

        result = self.uploader.upload_league_history(league_history, dry_run=False)

        # Verify results
        assert result["league_id"] == "123456"
        assert result["records_created"] == 3  # 1 metadata + 2 seasons
        assert result["metadata_record"] is not None
        assert len(result["season_records"]) == 2
        assert result["dry_run"] is False

        # Verify DynamoDB calls
        assert self.mock_table.put_item.call_count == 3

    def test_upload_league_history_dry_run(self):
        """Test league history upload with dry_run=True."""
        league_history = self._create_test_league_history()

        result = self.uploader.upload_league_history(league_history, dry_run=True)

        # Verify results
        assert result["league_id"] == "123456"
        assert result["records_created"] == 3
        assert result["dry_run"] is True

        # Verify no DynamoDB calls were made
        assert self.mock_table.put_item.call_count == 0

    def test_upload_league_history_single_season(self):
        """Test uploading league history with single season."""
        league_history = LeagueHistory(
            league_id="123456",
            league_name="Test League",
            seasons=[
                SeasonHistory(
                    year=2024,
                    regular_season_weeks=14,
                    playoff_weeks=3,
                    total_teams=12,
                    divisions=[],
                    final_standings=[],
                    champion=ChampionSummary(
                        team_id=1, team_name="Team A", owner_name="John Doe",
                        wins=12, losses=2, points_for=1543.50
                    )
                )
            ],
            metadata=LeagueHistoryMetadata(
                extracted_at="2025-01-15T10:30:00Z",
                total_seasons=1,
                year_range="2024-2024"
            )
        )

        result = self.uploader.upload_league_history(league_history, dry_run=False)

        assert result["records_created"] == 2  # 1 metadata + 1 season
        assert self.mock_table.put_item.call_count == 2

    def test_upload_league_history_exception_handling(self):
        """Test upload with DynamoDB exception."""
        league_history = self._create_test_league_history()
        self.mock_table.put_item.side_effect = Exception("DynamoDB Error")

        with pytest.raises(Exception) as exc_info:
            self.uploader.upload_league_history(league_history, dry_run=False)

        assert "DynamoDB Error" in str(exc_info.value)

    def test_upload_season_success(self):
        """Test successful single season upload."""
        season = SeasonHistory(
            year=2024,
            regular_season_weeks=14,
            playoff_weeks=3,
            total_teams=12,
            divisions=[],
            final_standings=[],
            champion=ChampionSummary(
                team_id=1, team_name="Team A", owner_name="John Doe",
                wins=12, losses=2, points_for=1543.50
            )
        )

        result = self.uploader.upload_season("123456", season, dry_run=False)

        assert result["league_id"] == "123456"
        assert result["year"] == 2024
        assert result["season_record"] is not None
        assert result["dry_run"] is False
        assert self.mock_table.put_item.call_count == 1

    def test_upload_season_dry_run(self):
        """Test single season upload with dry_run=True."""
        season = SeasonHistory(
            year=2024,
            regular_season_weeks=14,
            playoff_weeks=3,
            total_teams=12,
            divisions=[],
            final_standings=[],
            champion=ChampionSummary(
                team_id=1, team_name="Team A", owner_name="John Doe",
                wins=12, losses=2, points_for=1543.50
            )
        )

        result = self.uploader.upload_season("123456", season, dry_run=True)

        assert result["dry_run"] is True
        assert self.mock_table.put_item.call_count == 0

    def test_fetch_league_history_success(self):
        """Test successful league history fetch."""
        # Mock DynamoDB query response
        self.mock_table.query.return_value = {
            'Items': [
                {
                    'season_week': 'HISTORY#123456',
                    'data_type_id': 'METADATA',
                    'league_name': 'Test League',
                    'total_seasons': 2
                },
                {
                    'season_week': 'HISTORY#123456',
                    'data_type_id': 'SEASON#2024',
                    'year': 2024,
                    'champion': {'team_name': 'Team A'}
                },
                {
                    'season_week': 'HISTORY#123456',
                    'data_type_id': 'SEASON#2023',
                    'year': 2023,
                    'champion': {'team_name': 'Team B'}
                }
            ]
        }

        result = self.uploader.fetch_league_history("123456")

        assert result is not None
        assert result["metadata"]["league_name"] == "Test League"
        assert len(result["seasons"]) == 2
        assert result["seasons"][0]["year"] == 2023  # Sorted by year
        assert result["seasons"][1]["year"] == 2024

    def test_fetch_league_history_not_found(self):
        """Test fetch when no history exists."""
        self.mock_table.query.return_value = {'Items': []}

        result = self.uploader.fetch_league_history("999999")

        assert result is None

    def test_fetch_league_history_no_metadata(self):
        """Test fetch when metadata record is missing."""
        self.mock_table.query.return_value = {
            'Items': [
                {
                    'season_week': 'HISTORY#123456',
                    'data_type_id': 'SEASON#2024',
                    'year': 2024
                }
            ]
        }

        result = self.uploader.fetch_league_history("123456")

        assert result is None

    def test_fetch_season_success(self):
        """Test successful season fetch."""
        self.mock_table.get_item.return_value = {
            'Item': {
                'season_week': 'HISTORY#123456',
                'data_type_id': 'SEASON#2024',
                'year': 2024,
                'champion': {'team_name': 'Team A'}
            }
        }

        result = self.uploader.fetch_season("123456", 2024)

        assert result is not None
        assert result["year"] == 2024
        assert result["champion"]["team_name"] == "Team A"

    def test_fetch_season_not_found(self):
        """Test fetch when season doesn't exist."""
        self.mock_table.get_item.return_value = {}

        result = self.uploader.fetch_season("123456", 2020)

        assert result is None

    def test_fetch_season_exception_handling(self):
        """Test fetch with DynamoDB exception."""
        self.mock_table.get_item.side_effect = Exception("DynamoDB Error")

        with pytest.raises(Exception) as exc_info:
            self.uploader.fetch_season("123456", 2024)

        assert "DynamoDB Error" in str(exc_info.value)

    def test_uploader_with_provided_resource(self):
        """Test uploader initialization with provided DynamoDB resource."""
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table

        uploader = HistoryUploader(dynamodb_resource=mock_dynamodb, table_name="test-table")

        assert uploader.dynamodb is not None
        assert uploader.table is not None
        assert uploader.table == mock_table
