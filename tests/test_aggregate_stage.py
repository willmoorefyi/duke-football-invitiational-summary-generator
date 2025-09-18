import pytest
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path

from src.pipeline.aggregate_stage import AggregateStage
from src.utils.config import Config


class TestAggregateStage:
    """Test suite for data aggregation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.league_id = 380491
        self.aggregate_stage = AggregateStage(league_id=self.league_id)

        # Mock config
        self.aggregate_stage.config = Config()

        # Sample raw data matching the expected structure from extract stage
        self.sample_raw_data = {
            "league_id": 380491,
            "league_name": "Duke Football Invitational",
            "season": 2025,
            "week": 1,
            "report_date": "2025-09-17 15:32:03.569584",
            "divisions": [
                {
                    "name": "Adams",
                    "teams": [
                        {
                            "id": 3,
                            "name": "They Stole Danny's Dimes",
                            "abbreviation": "MPB",
                            "owner": "dukefb26",
                            "division": "Adams",
                            "wins": 2,
                            "losses": 0,
                            "ties": 0,
                            "points_for": 251.52,
                            "points_against": 235.64,
                            "overall_rank": 1,
                            "division_rank": 1,
                            "logo": "https://will.moore.fyi/duke-football-invitational/static/TheyStoleDannysDimesAll.png"
                        },
                        {
                            "id": 1,
                            "name": "O'ahu State Warriors",
                            "abbreviation": "RW",
                            "owner": "RWRW3939",
                            "division": "Adams",
                            "wins": 1,
                            "losses": 1,
                            "ties": 0,
                            "points_for": 232.90,
                            "points_against": 238.52,
                            "overall_rank": 4,
                            "division_rank": 2,
                            "logo": "https://will.moore.fyi/duke-football-invitational/static/OahuStateWarriorsAll.png"
                        }
                    ]
                }
            ],
            "matchups": [
                {
                    "week": 1,
                    "home_team": {
                        "id": 3,
                        "name": "They Stole Danny's Dimes"
                    },
                    "away_team": {
                        "id": 1,
                        "name": "O'ahu State Warriors"
                    },
                    "home_score": 139.7,
                    "away_score": 132.58,
                    "home_projected_score": 115.69,
                    "away_projected_score": 121.23,
                    "home_optimal_score": 159.3,
                    "away_optimal_score": 132.58,
                    "winner_id": 3,
                    "loser_id": 1
                }
            ]
        }

    def test_calculate_running_totals_success(self):
        """Test successful calculation of running totals."""
        result = self.aggregate_stage._calculate_running_totals(self.sample_raw_data)

        # Should return dict with team data
        assert isinstance(result, dict)
        assert len(result) == 2  # Two teams in sample data

        # Check team 3 (They Stole Danny's Dimes) data
        team_3_data = result[3]
        assert team_3_data['name'] == "They Stole Danny's Dimes"
        assert team_3_data['logo'] == "https://will.moore.fyi/duke-football-invitational/static/TheyStoleDannysDimesAll.png"
        assert team_3_data['division'] == "Adams"
        assert team_3_data['actual'] == 139.7
        assert team_3_data['projected'] == 115.69
        assert team_3_data['optimal'] == 159.3
        # Efficiency should be (139.7 / 159.3) * 100 ≈ 87.7%
        assert abs(team_3_data['efficiency'] - 87.69617074701819) < 0.01

        # Check team 1 (O'ahu State Warriors) data
        team_1_data = result[1]
        assert team_1_data['name'] == "O'ahu State Warriors"
        assert team_1_data['actual'] == 132.58
        assert team_1_data['projected'] == 121.23
        assert team_1_data['optimal'] == 132.58
        # Efficiency should be (132.58 / 132.58) * 100 = 100%
        assert team_1_data['efficiency'] == 100.0

    def test_calculate_running_totals_zero_optimal(self):
        """Test running totals calculation when optimal score is zero."""
        # Modify sample data to have zero optimal score
        modified_data = self.sample_raw_data.copy()
        modified_data['matchups'][0]['home_optimal_score'] = 0
        modified_data['matchups'][0]['away_optimal_score'] = 0

        result = self.aggregate_stage._calculate_running_totals(modified_data)

        # Should handle zero optimal scores gracefully
        assert result[3]['efficiency'] == 0.0
        assert result[1]['efficiency'] == 0.0

    def test_calculate_running_totals_no_matchups(self):
        """Test running totals calculation with no matchups."""
        modified_data = self.sample_raw_data.copy()
        modified_data['matchups'] = []

        result = self.aggregate_stage._calculate_running_totals(modified_data)

        # Should still return team data with zero scores
        assert len(result) == 2
        assert result[3]['actual'] == 0.0
        assert result[1]['actual'] == 0.0
        assert result[3]['efficiency'] == 0.0

    def test_calculate_running_totals_missing_team_data(self):
        """Test running totals calculation with missing team info."""
        modified_data = {
            "divisions": [
                {
                    "name": "Adams",
                    "teams": [
                        {
                            "id": 99,
                            # Missing name and logo
                            "division": "Adams"
                        }
                    ]
                }
            ],
            "matchups": [
                {
                    "home_team": {"id": 99},
                    "away_team": {"id": 100},  # Team not in divisions
                    "home_score": 100.0,
                    "away_score": 90.0,
                    "home_projected_score": 95.0,
                    "away_projected_score": 85.0,
                    "home_optimal_score": 105.0,
                    "away_optimal_score": 95.0
                }
            ]
        }

        result = self.aggregate_stage._calculate_running_totals(modified_data)

        # Should handle missing team gracefully
        assert 99 in result
        assert result[99]['name'] == ""  # Default for missing name
        assert result[99]['logo'] == ""  # Default for missing logo
        # Team 100 not in divisions, so not included
        assert 100 not in result

    def test_calculate_running_totals_exception_handling(self):
        """Test running totals calculation with malformed data."""
        # Pass invalid data structure that will cause an exception during processing
        invalid_data = {
            "divisions": [
                {
                    "teams": [
                        {
                            "id": "not_a_number",  # This will cause issues in dictionary access
                            "name": None  # This will cause issues with string operations
                        }
                    ]
                }
            ],
            "matchups": [
                {
                    "home_team": {"id": "not_a_number"},
                    "away_team": {"id": None},
                    "home_score": "not_a_number",  # String instead of number
                    "away_score": None
                }
            ]
        }

        result = self.aggregate_stage._calculate_running_totals(invalid_data)

        # Should handle the malformed data gracefully and return empty dict
        # or return an error dict if an exception occurs
        assert isinstance(result, dict)
        # Either empty dict (graceful handling) or error dict (exception occurred)
        assert len(result) == 0 or "error" in result

    def test_create_enhanced_data_structure(self):
        """Test creation of enhanced data structure with running totals."""
        result = self.aggregate_stage._create_enhanced_data(self.sample_raw_data, "test_record_id")

        # Should have proper structure
        assert "current_week" in result
        assert "season_context" in result
        assert "running_totals" in result["season_context"]
        assert "metadata" in result

        # Current week data should be preserved
        assert result["current_week"] == self.sample_raw_data

        # Running totals should be calculated
        running_totals = result["season_context"]["running_totals"]
        assert len(running_totals) == 2
        assert 3 in running_totals  # Team IDs as keys
        assert 1 in running_totals

        # Metadata should be populated
        metadata = result["metadata"]
        assert metadata["dynamodb_record_id"] == "test_record_id"
        assert metadata["league_id"] == 380491
        assert metadata["current_week"] == 1
        assert metadata["data_source"] == "current_week_only"

    def test_aggregate_execute_dry_run(self):
        """Test aggregate stage execution in dry-run mode."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_raw_data, f)
            temp_file = f.name

        try:
            # Test dry run
            self.aggregate_stage.dry_run = True
            output_path, metadata = self.aggregate_stage.execute(
                current_week_file=temp_file,
                dynamodb_record_id="test_record"
            )

            assert output_path is None
            assert metadata["dry_run"] is True
        finally:
            Path(temp_file).unlink()

    def test_aggregate_execute_success(self):
        """Test successful aggregate stage execution."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_raw_data, f)
            temp_file = f.name

        try:
            output_path, metadata = self.aggregate_stage.execute(
                current_week_file=temp_file,
                dynamodb_record_id="test_record"
            )

            # Should return valid output path and metadata
            assert output_path is not None
            assert Path(output_path).exists()
            assert metadata["week"] == 1
            assert "enhanced_file" in metadata

            # Verify output file contents
            with open(output_path, 'r') as f:
                enhanced_data = json.load(f)

            assert "current_week" in enhanced_data
            assert "season_context" in enhanced_data
            assert "running_totals" in enhanced_data["season_context"]

            # Cleanup
            Path(output_path).unlink()
        finally:
            Path(temp_file).unlink()

    def test_aggregate_execute_invalid_file(self):
        """Test aggregate stage execution with invalid input file."""
        with pytest.raises(FileNotFoundError):
            self.aggregate_stage.execute(
                current_week_file="nonexistent_file.json",
                dynamodb_record_id="test_record"
            )

    def test_aggregate_execute_invalid_json(self):
        """Test aggregate stage execution with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_file = f.name

        try:
            with pytest.raises(json.JSONDecodeError):
                self.aggregate_stage.execute(
                    current_week_file=temp_file,
                    dynamodb_record_id="test_record"
                )
        finally:
            Path(temp_file).unlink()