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
        result = self.aggregate_stage._create_enhanced_data(self.sample_raw_data, "test_record_id", [])

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

        # Weekly statistics should be included
        assert "weekly_statistics" in result["season_context"]

    def test_convert_decimal_to_float(self):
        """Test conversion of DynamoDB Decimal objects to float."""
        from decimal import Decimal

        # Test various data structures with Decimal values
        test_data = {
            'number': Decimal('123.45'),
            'nested': {
                'score': Decimal('89.2'),
                'string_val': 'test'
            },
            'list_data': [Decimal('1.1'), Decimal('2.2'), 'string'],
            'regular_float': 3.14,
            'integer': 42
        }

        result = self.aggregate_stage._convert_decimal_to_float(test_data)

        # Check conversions
        assert result['number'] == 123.45
        assert isinstance(result['number'], float)
        assert result['nested']['score'] == 89.2
        assert isinstance(result['nested']['score'], float)
        assert result['nested']['string_val'] == 'test'  # Unchanged
        assert result['list_data'][0] == 1.1
        assert isinstance(result['list_data'][0], float)
        assert result['list_data'][2] == 'string'  # Unchanged
        assert result['regular_float'] == 3.14  # Unchanged
        assert result['integer'] == 42  # Unchanged

    @patch('boto3.resource')
    def test_fetch_historical_data_success(self, mock_boto3_resource):
        """Test successful fetching of historical data from DynamoDB."""
        from decimal import Decimal

        # Mock DynamoDB table and responses
        mock_table = MagicMock()
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        # Create sample historical data with Decimal values (as DynamoDB returns)
        historical_item = {
            'season_week': '2025-01',
            'data_type_id': 'weekly_report',
            'league_id': Decimal('380491'),
            'data': {
                'week': Decimal('1'),
                'season': Decimal('2025'),
                'league_id': Decimal('380491'),
                'matchups': [{
                    'home_team': {'name': 'Test Team A'},
                    'away_team': {'name': 'Test Team B'},
                    'home_score': Decimal('105.5'),
                    'away_score': Decimal('92.3')
                }]
            }
        }

        # Setup mock responses - week 1 exists
        mock_table.get_item.return_value = {'Item': historical_item}

        # Test data for current week 2
        current_data = {
            'season': 2025,
            'week': 2,
            'league_id': '380491'
        }

        # Mock config
        self.aggregate_stage.config.pipeline.aws.dynamodb_table = 'test-table'
        self.aggregate_stage.config.pipeline.aws.region = 'us-east-1'

        result = self.aggregate_stage._fetch_historical_data(current_data)

        # Verify correct DynamoDB calls
        mock_boto3_resource.assert_called_once_with('dynamodb', region_name='us-east-1')
        mock_dynamodb.Table.assert_called_once_with('test-table')

        # Should have called get_item for week 1 only (current week is 2)
        mock_table.get_item.assert_called_once_with(
            Key={'season_week': '2025-01', 'data_type_id': 'weekly_report'}
        )

        # Should return converted data (Decimal -> float)
        assert len(result) == 1
        historical_week = result[0]
        assert historical_week['week'] == 1.0  # Converted from Decimal
        assert historical_week['season'] == 2025.0  # Converted from Decimal
        assert historical_week['matchups'][0]['home_score'] == 105.5  # Converted from Decimal

    def test_fetch_historical_data_no_league_id(self):
        """Test fetch_historical_data with missing league_id."""
        current_data = {'season': 2025, 'week': 2}  # No league_id

        result = self.aggregate_stage._fetch_historical_data(current_data)

        assert result == []

    @patch('boto3.resource')
    def test_fetch_historical_data_boto3_import_error(self, mock_boto3_resource):
        """Test fetch_historical_data when boto3 is not available."""
        # Simulate ImportError for boto3
        mock_boto3_resource.side_effect = ImportError("No module named 'boto3'")

        # We need to patch the import inside the method
        with patch('builtins.__import__', side_effect=ImportError("boto3 not available")):
            result = self.aggregate_stage._fetch_historical_data(self.sample_raw_data)

        assert result == []

    @patch('boto3.resource')
    def test_fetch_historical_data_no_credentials(self, mock_boto3_resource):
        """Test fetch_historical_data with no AWS credentials."""
        from botocore.exceptions import NoCredentialsError

        mock_boto3_resource.side_effect = NoCredentialsError()

        result = self.aggregate_stage._fetch_historical_data(self.sample_raw_data)

        assert result == []

    @patch('boto3.resource')
    def test_fetch_historical_data_table_not_found(self, mock_boto3_resource):
        """Test fetch_historical_data when DynamoDB table doesn't exist."""
        from botocore.exceptions import ClientError

        mock_table = MagicMock()
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        # Mock table not found error
        error_response = {'Error': {'Code': 'ResourceNotFoundException'}}
        mock_table.get_item.side_effect = ClientError(error_response, 'GetItem')

        # Mock config
        self.aggregate_stage.config.pipeline.aws.dynamodb_table = 'nonexistent-table'
        self.aggregate_stage.config.pipeline.aws.region = 'us-east-1'

        result = self.aggregate_stage._fetch_historical_data(self.sample_raw_data)

        assert result == []

    @patch('boto3.resource')
    def test_fetch_historical_data_league_id_mismatch(self, mock_boto3_resource):
        """Test fetch_historical_data with wrong league_id in historical data."""
        from decimal import Decimal

        mock_table = MagicMock()
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        # Historical item with different league_id
        historical_item = {
            'season_week': '2025-01',
            'data_type_id': 'weekly_report',
            'league_id': Decimal('999999'),  # Different league
            'data': {'week': Decimal('1')}
        }

        mock_table.get_item.return_value = {'Item': historical_item}

        # Mock config
        self.aggregate_stage.config.pipeline.aws.dynamodb_table = 'test-table'
        self.aggregate_stage.config.pipeline.aws.region = 'us-east-1'

        # Test data expects league_id 380491
        current_data = {
            'season': 2025,
            'week': 2,
            'league_id': '380491'
        }

        result = self.aggregate_stage._fetch_historical_data(current_data)

        # Should return empty list due to league_id mismatch
        assert result == []

    def test_calculate_multi_week_team_performance(self):
        """Test calculation of team performance across multiple weeks."""
        # Create sample multi-week data
        week1_data = {
            'week': 1,
            'matchups': [
                {
                    'home_team': {'name': 'Team A'},
                    'away_team': {'name': 'Team B'},
                    'home_score': 110.5,
                    'away_score': 95.2
                }
            ]
        }

        week2_data = {
            'week': 2,
            'matchups': [
                {
                    'home_team': {'name': 'Team A'},
                    'away_team': {'name': 'Team B'},
                    'home_score': 105.8,
                    'away_score': 112.3
                }
            ]
        }

        all_weeks_data = [week1_data, week2_data]

        result = self.aggregate_stage._calculate_multi_week_team_performance(all_weeks_data)

        # Verify structure
        assert 'average_scores' in result
        assert 'league_average' in result
        assert 'highest_score' in result
        assert 'lowest_score' in result
        assert 'total_points' in result
        assert 'total_weeks' in result

        # Check team averages (Team A: (110.5 + 105.8) / 2 = 108.15)
        assert result['average_scores']['Team A'] == (110.5 + 105.8) / 2
        assert result['average_scores']['Team B'] == (95.2 + 112.3) / 2

        # Check overall statistics
        assert result['highest_score'] == 112.3
        assert result['lowest_score'] == 95.2
        assert result['total_weeks'] == 2
        assert result['total_points'] == 110.5 + 95.2 + 105.8 + 112.3

    def test_calculate_multi_week_team_performance_empty_data(self):
        """Test multi-week team performance calculation with empty data."""
        result = self.aggregate_stage._calculate_multi_week_team_performance([])

        assert result['average_scores'] == {}
        assert result['league_average'] == 0
        assert result['highest_score'] == 0
        assert result['lowest_score'] == 0
        assert result['total_points'] == 0
        assert result['total_weeks'] == 0

    def test_calculate_multi_week_running_totals(self):
        """Test calculation of running totals across multiple weeks."""
        # Create sample multi-week data with team info
        week1_data = {
            'week': 1,
            'divisions': [
                {
                    'teams': [
                        {'id': 'team1', 'name': 'Team A', 'logo': 'logo1.png'},
                        {'id': 'team2', 'name': 'Team B', 'logo': 'logo2.png'}
                    ]
                }
            ],
            'matchups': [
                {
                    'home_team': {'id': 'team1'},
                    'away_team': {'id': 'team2'},
                    'home_score': 110.5,
                    'away_score': 95.2,
                    'home_projected_score': 105.0,
                    'away_projected_score': 100.0,
                    'home_optimal_score': 125.0,
                    'away_optimal_score': 110.0
                }
            ]
        }

        week2_data = {
            'week': 2,
            'divisions': [
                {
                    'teams': [
                        {'id': 'team1', 'name': 'Team A', 'logo': 'logo1.png'},
                        {'id': 'team2', 'name': 'Team B', 'logo': 'logo2.png'}
                    ]
                }
            ],
            'matchups': [
                {
                    'home_team': {'id': 'team1'},
                    'away_team': {'id': 'team2'},
                    'home_score': 105.8,
                    'away_score': 112.3,
                    'home_projected_score': 108.0,
                    'away_projected_score': 103.0,
                    'home_optimal_score': 120.0,
                    'away_optimal_score': 115.0
                }
            ]
        }

        all_weeks_data = [week1_data, week2_data]

        result = self.aggregate_stage._calculate_multi_week_running_totals(all_weeks_data)

        # Verify team1 totals
        team1_data = result['team1']
        assert team1_data['name'] == 'Team A'
        assert team1_data['actual'] == 110.5 + 105.8  # Sum across weeks
        assert team1_data['projected'] == 105.0 + 108.0
        assert team1_data['optimal'] == 125.0 + 120.0
        # Efficiency = (216.3 / 245.0) * 100
        expected_efficiency = ((110.5 + 105.8) / (125.0 + 120.0)) * 100
        assert abs(team1_data['efficiency'] - expected_efficiency) < 0.1

        # Verify team2 totals
        team2_data = result['team2']
        assert team2_data['name'] == 'Team B'
        assert team2_data['actual'] == 95.2 + 112.3
        assert team2_data['projected'] == 100.0 + 103.0
        assert team2_data['optimal'] == 110.0 + 115.0

    def test_calculate_all_weeks_statistics(self):
        """Test calculation of statistics for each individual week."""
        # Create sample multi-week data
        week1_data = {
            'week': 1,
            'matchups': [
                {
                    'home_team': {'name': 'Team A'},
                    'away_team': {'name': 'Team B'},
                    'home_score': 110.5,
                    'away_score': 95.2,
                    'home_optimal_score': 125.0,
                    'away_optimal_score': 110.0
                }
            ]
        }

        week2_data = {
            'week': 2,
            'matchups': [
                {
                    'home_team': {'name': 'Team A'},
                    'away_team': {'name': 'Team B'},
                    'home_score': 105.8,
                    'away_score': 112.3,
                    'home_optimal_score': 120.0,
                    'away_optimal_score': 115.0
                }
            ]
        }

        all_weeks_data = [week1_data, week2_data]

        result = self.aggregate_stage._calculate_all_weeks_statistics(all_weeks_data)

        # Should have weeks array
        assert 'weeks' in result
        weekly_stats = result['weeks']
        assert len(weekly_stats) == 2

        # Check week 1 stats
        week1_stats = weekly_stats[0]
        assert week1_stats['week'] == 1
        assert week1_stats['max'] == 110.5
        assert week1_stats['min'] == 95.2
        assert week1_stats['max_team_name'] == 'Team A'
        assert week1_stats['min_team_name'] == 'Team B'

        # Check week 2 stats
        week2_stats = weekly_stats[1]
        assert week2_stats['week'] == 2
        assert week2_stats['max'] == 112.3
        assert week2_stats['min'] == 105.8
        assert week2_stats['max_team_name'] == 'Team B'
        assert week2_stats['min_team_name'] == 'Team A'

    def test_create_enhanced_data_with_historical_data(self):
        """Test enhanced data creation with historical data included."""
        # Create historical data
        historical_data = [
            {
                'week': 1,
                'season': 2025,
                'league_id': '380491',
                'matchups': [
                    {
                        'home_team': {'name': 'Team A'},
                        'away_team': {'name': 'Team B'},
                        'home_score': 105.5,
                        'away_score': 92.3
                    }
                ]
            }
        ]

        result = self.aggregate_stage._create_enhanced_data(
            self.sample_raw_data, "test_record_id", historical_data
        )

        # Should have proper structure with historical context
        assert "current_week" in result
        assert "season_context" in result
        assert "metadata" in result

        # Check metadata shows multi-week data
        metadata = result["metadata"]
        assert metadata["historical_weeks_included"] == 1
        assert metadata["total_weeks_processed"] == 2  # 1 historical + 1 current
        assert metadata["data_source"] == "multi_week"

        # Check season context includes historical analysis
        season_context = result["season_context"]
        assert "weekly_statistics" in season_context
        assert "performance_trends" in season_context
        assert "running_totals" in season_context

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