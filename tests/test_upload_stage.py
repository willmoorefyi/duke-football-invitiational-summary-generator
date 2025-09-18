import pytest
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from src.pipeline.upload_stage import UploadStage
from src.utils.config import Config, PipelineConfig, AWSConfig


class TestUploadStage:
    """Test suite for DynamoDB upload functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.league_id = 380491
        self.upload_stage = UploadStage(league_id=self.league_id)

        # Mock the config to return expected values
        self.upload_stage.config = Config(
            pipeline=PipelineConfig(
                aws=AWSConfig(
                    dynamodb_table='fantasy-league-data',
                    region='us-east-1'
                )
            )
        )

        # Sample extract data matching the real format
        self.sample_data = {
            "league_id": 380491,
            "league_name": "Duke Football Invitational",
            "season": 2025,
            "week": 1,
            "report_date": "2025-09-15 23:25:36.701615",
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
                            "wins": 1,
                            "losses": 0,
                            "ties": 0,
                            "points_for": 139.7,
                            "points_against": 132.58,
                            "overall_rank": 1,
                            "division_rank": 1
                        },
                        {
                            "id": 9,
                            "name": "The Williams Football Team",
                            "abbreviation": "TWFT",
                            "owner": "SLW422",
                            "division": "Adams",
                            "wins": 1,
                            "losses": 0,
                            "ties": 0,
                            "points_for": 110.08,
                            "points_against": 78.44,
                            "overall_rank": 4,
                            "division_rank": 2
                        }
                    ]
                }
            ],
            "matchups": [],
            "injured_starters": [],
            "awards": {}
        }

    def test_dry_run_mode(self):
        """Test that dry run mode works correctly."""
        dry_run_stage = UploadStage(league_id=self.league_id, dry_run=True)
        dry_run_stage.config = self.upload_stage.config

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_data, f)
            temp_file = f.name

        try:
            output_path, metadata = dry_run_stage.execute(input_file=temp_file)

            assert output_path is None
            assert metadata["dry_run"] is True
            assert "record_id" in metadata
        finally:
            Path(temp_file).unlink()

    def test_missing_required_data(self):
        """Test handling of missing required data fields."""
        incomplete_data = {"league_id": 380491}  # Missing week and season

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(incomplete_data, f)
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="Missing required data"):
                self.upload_stage.execute(input_file=temp_file)
        finally:
            Path(temp_file).unlink()

    @patch('boto3.resource')
    def test_successful_upload(self, mock_boto3_resource):
        """Test successful DynamoDB upload with all records."""
        # Mock DynamoDB table and responses
        mock_table = Mock()
        mock_boto3_resource.return_value.Table.return_value = mock_table
        mock_table.put_item.return_value = {
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_data, f)
            temp_file = f.name

        try:
            output_path, metadata = self.upload_stage.execute(input_file=temp_file)

            # Verify return values
            assert output_path is None
            assert metadata["table_name"] == "fantasy-league-data"
            assert metadata["season_week"] == "2025-01"
            assert metadata["week"] == 1
            assert metadata["year"] == 2025
            assert metadata["league_id"] == 380491
            assert metadata["league_name"] == "Duke Football Invitational"
            assert metadata["records_uploaded"] == 3  # 1 main + 2 teams
            assert metadata["dynamodb_response"] == 200

            # Verify DynamoDB interactions
            assert mock_table.put_item.call_count == 3  # 1 main + 2 teams

            # Check main record structure
            main_call = mock_table.put_item.call_args_list[0]
            main_item = main_call[1]['Item']
            assert main_item['season_week'] == "2025-01"
            assert main_item['data_type_id'] == "weekly_report"
            assert main_item['league_id'] == "380491"
            assert main_item['week'] == 1
            assert main_item['season'] == 2025
            assert 'data' in main_item
            assert 'timestamp' in main_item
            assert main_item['schema_version'] == "1.0"

            # Check team records structure
            team_calls = mock_table.put_item.call_args_list[1:]
            team_items = [call[1]['Item'] for call in team_calls]

            for i, team_item in enumerate(team_items):
                expected_team_id = [3, 9][i]
                expected_team_name = ["They Stole Danny's Dimes", "The Williams Football Team"][i]

                assert team_item['season_week'] == "2025-01"
                assert team_item['data_type_id'] == f"team_{expected_team_id}"
                assert team_item['team_id'] == str(expected_team_id)
                assert team_item['team_name'] == expected_team_name
                assert team_item['league_id'] == "380491"
                assert 'team_data' in team_item
                assert 'timestamp' in team_item
        finally:
            Path(temp_file).unlink()

    @patch('boto3.resource')
    def test_decimal_conversion(self, mock_boto3_resource):
        """Test that float values are properly converted to Decimal for DynamoDB."""
        mock_table = Mock()
        mock_boto3_resource.return_value.Table.return_value = mock_table
        mock_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_data, f)
            temp_file = f.name

        try:
            self.upload_stage.execute(input_file=temp_file)

            # Check that float values were converted to Decimal
            main_call = mock_table.put_item.call_args_list[0]
            main_item = main_call[1]['Item']

            # Navigate to a float value in the data
            team_data = main_item['data']['divisions'][0]['teams'][0]
            assert isinstance(team_data['points_for'], Decimal)
            assert isinstance(team_data['points_against'], Decimal)
            assert team_data['points_for'] == Decimal('139.7')
            assert team_data['points_against'] == Decimal('132.58')
        finally:
            Path(temp_file).unlink()

    @patch('boto3.resource')
    def test_dynamodb_error_handling(self, mock_boto3_resource):
        """Test handling of DynamoDB errors."""
        mock_table = Mock()
        mock_boto3_resource.return_value.Table.return_value = mock_table
        mock_table.put_item.side_effect = Exception("DynamoDB connection failed")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_data, f)
            temp_file = f.name

        try:
            with pytest.raises(Exception, match="DynamoDB connection failed"):
                self.upload_stage.execute(input_file=temp_file)
        finally:
            Path(temp_file).unlink()

    def test_invalid_json_file(self):
        """Test handling of invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content {")
            temp_file = f.name

        try:
            with pytest.raises(json.JSONDecodeError):
                self.upload_stage.execute(input_file=temp_file)
        finally:
            Path(temp_file).unlink()

    def test_file_not_found(self):
        """Test handling of non-existent file."""
        with pytest.raises(FileNotFoundError):
            self.upload_stage.execute(input_file="/nonexistent/file.json")

    @patch('boto3.resource')
    def test_empty_divisions(self, mock_boto3_resource):
        """Test handling of data with no teams/divisions."""
        mock_table = Mock()
        mock_boto3_resource.return_value.Table.return_value = mock_table
        mock_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}

        data_with_no_teams = {
            "league_id": 380491,
            "league_name": "Empty League",
            "season": 2025,
            "week": 1,
            "divisions": [],
            "matchups": [],
            "injured_starters": [],
            "awards": {}
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data_with_no_teams, f)
            temp_file = f.name

        try:
            output_path, metadata = self.upload_stage.execute(input_file=temp_file)

            # Should only upload the main record, no team records
            assert metadata["records_uploaded"] == 1
            assert mock_table.put_item.call_count == 1
        finally:
            Path(temp_file).unlink()

    @patch('boto3.resource')
    def test_teams_missing_id_or_name(self, mock_boto3_resource):
        """Test handling of teams with missing ID or name."""
        mock_table = Mock()
        mock_boto3_resource.return_value.Table.return_value = mock_table
        mock_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}

        data_with_incomplete_teams = {
            "league_id": 380491,
            "league_name": "Test League",
            "season": 2025,
            "week": 1,
            "divisions": [
                {
                    "name": "Test Division",
                    "teams": [
                        {"id": 1, "name": "Valid Team"},  # Valid team
                        {"name": "Team Without ID"},      # Missing ID
                        {"id": 3}                         # Missing name
                    ]
                }
            ],
            "matchups": [],
            "injured_starters": [],
            "awards": {}
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data_with_incomplete_teams, f)
            temp_file = f.name

        try:
            output_path, metadata = self.upload_stage.execute(input_file=temp_file)

            # Should upload main record + only 1 valid team record
            assert metadata["records_uploaded"] == 2
            assert mock_table.put_item.call_count == 2

            # Verify valid team record
            team_call = mock_table.put_item.call_args_list[1]
            team_item = team_call[1]['Item']
            assert team_item['data_type_id'] == "team_1"
            assert team_item['team_id'] == "1"
            assert team_item['team_name'] == "Valid Team"
        finally:
            Path(temp_file).unlink()

    def test_convert_floats_to_decimal_function(self):
        """Test the float to Decimal conversion utility function."""
        # Access the nested function by creating an instance and calling execute with dry_run
        dry_run_stage = UploadStage(league_id=self.league_id, dry_run=True)
        dry_run_stage.config = self.upload_stage.config

        # Test data with nested floats
        test_data = {
            "simple_float": 123.45,
            "simple_int": 100,
            "simple_string": "test",
            "nested_dict": {
                "inner_float": 67.89,
                "inner_list": [1.1, 2.2, "string", {"deep_float": 3.3}]
            },
            "list_of_floats": [10.1, 20.2, 30.3]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_data = {**self.sample_data, "test_field": test_data}
            json.dump(temp_data, f)
            temp_file = f.name

        try:
            # This will exercise the convert_floats_to_decimal function
            output_path, metadata = dry_run_stage.execute(input_file=temp_file)
            assert metadata["dry_run"] is True
        finally:
            Path(temp_file).unlink()