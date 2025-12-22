import pytest
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock, call
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

    def test_calculate_matchup_history_basic_functionality(self):
        """Test basic matchup history calculation with weekly results."""
        # Sample historical weeks data
        all_weeks_data = [
            {
                'week': 1,
                'matchups': [
                    {
                        'home_team': {'id': '1', 'name': 'Team Alpha', 'abbreviation': 'ALP'},
                        'away_team': {'id': '2', 'name': 'Team Beta', 'abbreviation': 'BET'},
                        'home_score': 125.5,
                        'away_score': 118.3,
                        'home_projected_score': 120.0,
                        'away_projected_score': 115.0,
                        'home_optimal_score': 135.2,
                        'away_optimal_score': 128.7
                    }
                ]
            },
            {
                'week': 2,
                'matchups': [
                    {
                        'home_team': {'id': '2', 'name': 'Team Beta', 'abbreviation': 'BET'},
                        'away_team': {'id': '1', 'name': 'Team Alpha', 'abbreviation': 'ALP'},
                        'home_score': 142.8,
                        'away_score': 135.2,
                        'home_projected_score': 130.0,
                        'away_projected_score': 125.0,
                        'home_optimal_score': 148.5,
                        'away_optimal_score': 142.1
                    }
                ]
            }
        ]

        result = self.aggregate_stage._calculate_matchup_history(all_weeks_data)

        # Verify structure
        assert 'weekly_results' in result
        weekly_results = result['weekly_results']

        # Should have data for weeks 1 and 2
        assert 1 in weekly_results
        assert 2 in weekly_results
        assert len(weekly_results[1]) == 1  # One matchup in week 1
        assert len(weekly_results[2]) == 1  # One matchup in week 2

        # Verify week 1 matchup data
        week1_matchup = weekly_results[1][0]
        assert week1_matchup['home_team']['id'] == '1'
        assert week1_matchup['away_team']['id'] == '2'
        assert week1_matchup['home_score'] == 125.5
        assert week1_matchup['away_score'] == 118.3
        assert week1_matchup['winner_id'] == '1'  # Home team won
        assert week1_matchup['loser_id'] == '2'

        # Verify week 2 matchup data
        week2_matchup = weekly_results[2][0]
        assert week2_matchup['home_team']['id'] == '2'
        assert week2_matchup['away_team']['id'] == '1'
        assert week2_matchup['winner_id'] == '2'  # Home team won
        assert week2_matchup['loser_id'] == '1'

    def test_calculate_matchup_history_tie_game(self):
        """Test matchup history calculation with tie game."""
        all_weeks_data = [
            {
                'week': 1,
                'matchups': [
                    {
                        'home_team': {'id': '1', 'name': 'Team Alpha'},
                        'away_team': {'id': '2', 'name': 'Team Beta'},
                        'home_score': 125.0,
                        'away_score': 125.0,
                        'home_projected_score': 120.0,
                        'away_projected_score': 115.0,
                        'home_optimal_score': 135.0,
                        'away_optimal_score': 130.0
                    }
                ]
            }
        ]

        result = self.aggregate_stage._calculate_matchup_history(all_weeks_data)

        weekly_results = result['weekly_results']
        matchup = weekly_results[1][0]

        # Verify tie game handling
        assert matchup['winner_id'] is None
        assert matchup['loser_id'] is None
        assert matchup['home_score'] == matchup['away_score']

    def test_calculate_matchup_history_no_data(self):
        """Test matchup history calculation with no data."""
        result = self.aggregate_stage._calculate_matchup_history([])

        assert 'weekly_results' in result
        assert len(result['weekly_results']) == 0

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
        result = self.aggregate_stage._create_enhanced_data(self.sample_raw_data, "test_record_id", [], is_latest_week=True)

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

        result, is_latest = self.aggregate_stage._fetch_historical_data(current_data)

        # Verify correct DynamoDB calls
        mock_boto3_resource.assert_called_once_with('dynamodb', region_name='us-east-1')
        mock_dynamodb.Table.assert_called_once_with('test-table')

        # Should have called get_item for week 1 (historical) and week 3 (future check for is_latest)
        # Since we return {'Item': historical_item} for all calls, it thinks week 3 exists
        assert mock_table.get_item.call_count >= 1  # At least week 1 historical fetch

        # Should return converted data (Decimal -> float)
        assert len(result) == 1
        historical_week = result[0]
        assert historical_week['week'] == 1.0  # Converted from Decimal
        assert historical_week['season'] == 2025.0  # Converted from Decimal
        assert historical_week['matchups'][0]['home_score'] == 105.5  # Converted from Decimal

        # is_latest should be False since we're returning data for week 3 (future)
        assert is_latest is False  # Week 3 exists, so week 2 is not latest

    def test_fetch_historical_data_no_league_id(self):
        """Test fetch_historical_data with missing league_id."""
        current_data = {'season': 2025, 'week': 2}  # No league_id

        result, is_latest = self.aggregate_stage._fetch_historical_data(current_data)

        assert result == []
        assert is_latest is True  # Assumes latest when no league_id

    @patch('boto3.resource')
    def test_fetch_historical_data_boto3_import_error(self, mock_boto3_resource):
        """Test fetch_historical_data when boto3 is not available."""
        # Simulate ImportError for boto3
        mock_boto3_resource.side_effect = ImportError("No module named 'boto3'")

        # We need to patch the import inside the method
        with patch('builtins.__import__', side_effect=ImportError("boto3 not available")):
            result, is_latest = self.aggregate_stage._fetch_historical_data(self.sample_raw_data)

        assert result == []
        assert is_latest is True  # Assumes latest when boto3 not available

    @patch('boto3.resource')
    def test_fetch_historical_data_no_credentials(self, mock_boto3_resource):
        """Test fetch_historical_data with no AWS credentials."""
        from botocore.exceptions import NoCredentialsError

        mock_boto3_resource.side_effect = NoCredentialsError()

        result, is_latest = self.aggregate_stage._fetch_historical_data(self.sample_raw_data)

        assert result == []
        assert is_latest is True  # Assumes latest when no credentials

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

        result, is_latest = self.aggregate_stage._fetch_historical_data(self.sample_raw_data)

        assert result == []
        assert is_latest is True  # Assumes latest when table not found

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

        result, is_latest = self.aggregate_stage._fetch_historical_data(current_data)

        # Should return empty list due to league_id mismatch
        assert result == []
        assert is_latest is True  # Should check for future weeks even if mismatch

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
        # Create sample data for week 2 (current week)
        current_week_data = {
            "league_id": 380491,
            "league_name": "Duke Football Invitational",
            "season": 2025,
            "week": 2,
            "report_date": "2025-09-24 15:32:03.569584",
            "divisions": [
                {
                    "name": "Adams",
                    "teams": [
                        {
                            "id": 3,
                            "name": "They Stole Danny's Dimes",
                            "abbreviation": "MPB",
                            "owner": "dukefb26",
                            "division": "Adams"
                        },
                        {
                            "id": 1,
                            "name": "O'ahu State Warriors",
                            "abbreviation": "RW",
                            "owner": "RWRW3939",
                            "division": "Adams"
                        }
                    ]
                }
            ],
            "matchups": [
                {
                    "week": 2,
                    "home_team": {"id": 1, "name": "O'ahu State Warriors"},
                    "away_team": {"id": 3, "name": "They Stole Danny's Dimes"},
                    "home_score": 105.5,
                    "away_score": 92.3
                }
            ]
        }

        # Create historical data for week 1 with matching team structure
        historical_data = [
            {
                'week': 1,
                'season': 2025,
                'league_id': '380491',
                'divisions': [
                    {
                        'name': 'Adams',
                        'teams': [
                            {'id': 3, 'name': "They Stole Danny's Dimes", 'division': 'Adams'},
                            {'id': 1, 'name': "O'ahu State Warriors", 'division': 'Adams'}
                        ]
                    }
                ],
                'matchups': [
                    {
                        'home_team': {'id': 3, 'name': "They Stole Danny's Dimes"},
                        'away_team': {'id': 1, 'name': "O'ahu State Warriors"},
                        'home_score': 139.7,
                        'away_score': 132.58
                    }
                ]
            }
        ]

        result = self.aggregate_stage._create_enhanced_data(
            current_week_data, "test_record_id", historical_data, is_latest_week=True
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

        # Verify standings are computed from matchups
        team_standings = season_context["team_standings"]
        # Team 3: Won week 1 (139.7-132.58), Lost week 2 (92.3-105.5) = 1-1
        assert team_standings[3]['wins'] == 1
        assert team_standings[3]['losses'] == 1
        # Team 1: Lost week 1 (132.58-139.7), Won week 2 (105.5-92.3) = 1-1
        assert team_standings[1]['wins'] == 1
        assert team_standings[1]['losses'] == 1

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

    def test_calculate_team_standings_multi_week_accumulation(self):
        """Test team standings calculation accumulates correctly across multiple weeks."""
        # Create test data for 3 weeks with known results
        # Teams: Team A (id=1), Team B (id=2), Team C (id=3), Team D (id=4)

        week1_data = {
            'week': 1,
            'divisions': [
                {
                    'name': 'Division 1',
                    'teams': [
                        {'id': 1, 'name': 'Team A', 'abbreviation': 'TA', 'owner': 'Owner A', 'division': 'Division 1', 'logo': 'logo_a.png',
                         'wins': 1, 'losses': 0, 'points_for': 120.5, 'points_against': 110.2},
                        {'id': 2, 'name': 'Team B', 'abbreviation': 'TB', 'owner': 'Owner B', 'division': 'Division 1', 'logo': 'logo_b.png',
                         'wins': 0, 'losses': 1, 'points_for': 110.2, 'points_against': 120.5},
                        {'id': 3, 'name': 'Team C', 'abbreviation': 'TC', 'owner': 'Owner C', 'division': 'Division 1', 'logo': 'logo_c.png',
                         'wins': 1, 'losses': 0, 'points_for': 95.8, 'points_against': 88.1},
                        {'id': 4, 'name': 'Team D', 'abbreviation': 'TD', 'owner': 'Owner D', 'division': 'Division 1', 'logo': 'logo_d.png',
                         'wins': 0, 'losses': 1, 'points_for': 88.1, 'points_against': 95.8}
                    ]
                }
            ],
            'matchups': [
                {  # Team A beats Team B
                    'home_team': {'id': 1, 'name': 'Team A'},
                    'away_team': {'id': 2, 'name': 'Team B'},
                    'home_score': 120.5,
                    'away_score': 110.2
                },
                {  # Team C beats Team D
                    'home_team': {'id': 3, 'name': 'Team C'},
                    'away_team': {'id': 4, 'name': 'Team D'},
                    'home_score': 95.8,
                    'away_score': 88.1
                }
            ]
        }

        week2_data = {
            'week': 2,
            'divisions': [
                {
                    'name': 'Division 1',
                    'teams': [
                        {'id': 1, 'name': 'Team A', 'abbreviation': 'TA', 'owner': 'Owner A', 'division': 'Division 1', 'logo': 'logo_a.png',
                         'wins': 1, 'losses': 1, 'points_for': 229.2, 'points_against': 225.5},
                        {'id': 2, 'name': 'Team B', 'abbreviation': 'TB', 'owner': 'Owner B', 'division': 'Division 1', 'logo': 'logo_b.png',
                         'wins': 1, 'losses': 1, 'points_for': 225.5, 'points_against': 229.2},
                        {'id': 3, 'name': 'Team C', 'abbreviation': 'TC', 'owner': 'Owner C', 'division': 'Division 1', 'logo': 'logo_c.png',
                         'wins': 1, 'losses': 1, 'points_for': 194.9, 'points_against': 190.5},
                        {'id': 4, 'name': 'Team D', 'abbreviation': 'TD', 'owner': 'Owner D', 'division': 'Division 1', 'logo': 'logo_d.png',
                         'wins': 1, 'losses': 1, 'points_for': 190.5, 'points_against': 194.9}
                    ]
                }
            ],
            'matchups': [
                {  # Team B beats Team A (revenge game)
                    'home_team': {'id': 2, 'name': 'Team B'},
                    'away_team': {'id': 1, 'name': 'Team A'},
                    'home_score': 115.3,
                    'away_score': 108.7
                },
                {  # Team D beats Team C (revenge game)
                    'home_team': {'id': 4, 'name': 'Team D'},
                    'away_team': {'id': 3, 'name': 'Team C'},
                    'home_score': 102.4,
                    'away_score': 99.1
                }
            ]
        }

        week3_data = {
            'week': 3,
            'divisions': [
                {
                    'name': 'Division 1',
                    'teams': [
                        {'id': 1, 'name': 'Team A', 'abbreviation': 'TA', 'owner': 'Owner A', 'division': 'Division 1', 'logo': 'logo_a.png',
                         'wins': 2, 'losses': 1, 'points_for': 354.2, 'points_against': 344.0},
                        {'id': 2, 'name': 'Team B', 'abbreviation': 'TB', 'owner': 'Owner B', 'division': 'Division 1', 'logo': 'logo_b.png',
                         'wins': 2, 'losses': 1, 'points_for': 337.3, 'points_against': 334.4},
                        {'id': 3, 'name': 'Team C', 'abbreviation': 'TC', 'owner': 'Owner C', 'division': 'Division 1', 'logo': 'logo_c.png',
                         'wins': 1, 'losses': 2, 'points_for': 313.4, 'points_against': 315.5},
                        {'id': 4, 'name': 'Team D', 'abbreviation': 'TD', 'owner': 'Owner D', 'division': 'Division 1', 'logo': 'logo_d.png',
                         'wins': 1, 'losses': 2, 'points_for': 295.7, 'points_against': 306.7}
                    ]
                }
            ],
            'matchups': [
                {  # Team A beats Team C
                    'home_team': {'id': 1, 'name': 'Team A'},
                    'away_team': {'id': 3, 'name': 'Team C'},
                    'home_score': 125.0,
                    'away_score': 118.5
                },
                {  # Team B beats Team D
                    'home_team': {'id': 2, 'name': 'Team B'},
                    'away_team': {'id': 4, 'name': 'Team D'},
                    'home_score': 111.8,
                    'away_score': 105.2
                }
            ]
        }

        all_weeks_data = [week1_data, week2_data, week3_data]

        # Calculate standings through week 3
        result = self.aggregate_stage._calculate_team_standings(all_weeks_data, 3)

        # Expected cumulative records after 3 weeks:
        # Team A: 2-1 (W vs B, L vs B, W vs C), 354.2 PF, 344.0 PA
        # Team B: 2-1 (L vs A, W vs A, W vs D), 337.3 PF, 334.4 PA
        # Team C: 1-2 (W vs D, L vs D, L vs A), 313.4 PF, 315.5 PA
        # Team D: 1-2 (L vs C, W vs C, L vs B), 295.7 PF, 306.7 PA

        # Verify Team A's cumulative record
        assert result[1]['wins'] == 2
        assert result[1]['losses'] == 1
        assert result[1]['ties'] == 0
        assert abs(result[1]['points_for'] - 354.2) < 0.01  # 120.5 + 108.7 + 125.0
        assert abs(result[1]['points_against'] - 344.0) < 0.01  # 110.2 + 115.3 + 118.5

        # Verify Team B's cumulative record
        assert result[2]['wins'] == 2
        assert result[2]['losses'] == 1
        assert result[2]['ties'] == 0
        assert abs(result[2]['points_for'] - 337.3) < 0.01  # 110.2 + 115.3 + 111.8
        assert abs(result[2]['points_against'] - 334.4) < 0.01  # 120.5 + 108.7 + 105.2

        # Verify Team C's cumulative record
        assert result[3]['wins'] == 1
        assert result[3]['losses'] == 2
        assert result[3]['ties'] == 0
        assert abs(result[3]['points_for'] - 313.4) < 0.01  # 95.8 + 99.1 + 118.5
        assert abs(result[3]['points_against'] - 315.5) < 0.01  # 88.1 + 102.4 + 125.0

        # Verify Team D's cumulative record
        assert result[4]['wins'] == 1
        assert result[4]['losses'] == 2
        assert result[4]['ties'] == 0
        assert abs(result[4]['points_for'] - 295.7) < 0.01  # 88.1 + 102.4 + 105.2
        assert abs(result[4]['points_against'] - 306.7) < 0.01  # 95.8 + 99.1 + 111.8

    def test_calculate_team_standings_mid_season_accumulation(self):
        """Test team standings calculation for mid-season scenario (week 10)."""
        # Create sample teams with varied performance through 10 weeks
        # Team A: Strong start, recent struggles (6-4 record)
        # Team B: Consistent performer (7-3 record)

        # Build 10 weeks of data with known outcomes
        all_weeks_data = []

        # Weeks 1-6: Team A wins, Team B loses (A starts strong)
        team_a_wins = 0
        team_b_wins = 0
        team_a_points_for = 0.0
        team_a_points_against = 0.0
        team_b_points_for = 0.0
        team_b_points_against = 0.0

        for week in range(1, 11):
            if week <= 6:  # Team A wins weeks 1-6
                home_score = 120.0 + week
                away_score = 110.0 + week
                winner_home = True
                team_a_wins += 1
            else:  # Team B wins weeks 7-10
                home_score = 115.0 + week
                away_score = 125.0 + week
                winner_home = False
                team_b_wins += 1

            # Track cumulative totals
            team_a_points_for += home_score
            team_a_points_against += away_score
            team_b_points_for += away_score
            team_b_points_against += home_score

            # Build teams data with cumulative standings for this week
            teams_data = [
                {'id': 1, 'name': 'Team A', 'abbreviation': 'TA', 'owner': 'Owner A', 'division': 'Division 1', 'logo': 'logo_a.png',
                 'wins': team_a_wins, 'losses': week - team_a_wins, 'points_for': team_a_points_for, 'points_against': team_a_points_against},
                {'id': 2, 'name': 'Team B', 'abbreviation': 'TB', 'owner': 'Owner B', 'division': 'Division 1', 'logo': 'logo_b.png',
                 'wins': team_b_wins, 'losses': week - team_b_wins, 'points_for': team_b_points_for, 'points_against': team_b_points_against}
            ]

            # Always Team A home, Team B away for simplicity
            week_data = {
                'week': week,
                'divisions': [{'name': 'Division 1', 'teams': teams_data}],
                'matchups': [{
                    'home_team': {'id': 1, 'name': 'Team A'},
                    'away_team': {'id': 2, 'name': 'Team B'},
                    'home_score': home_score,
                    'away_score': away_score
                }]
            }
            all_weeks_data.append(week_data)

        # Calculate standings through week 10
        result = self.aggregate_stage._calculate_team_standings(all_weeks_data, 10)

        # Verify Team A's cumulative record (6 wins, 4 losses)
        assert result[1]['wins'] == team_a_wins
        assert result[1]['losses'] == 10 - team_a_wins
        assert result[1]['ties'] == 0
        assert abs(result[1]['points_for'] - team_a_points_for) < 0.01
        assert abs(result[1]['points_against'] - team_a_points_against) < 0.01

        # Verify Team B's cumulative record (4 wins, 6 losses)
        assert result[2]['wins'] == team_b_wins
        assert result[2]['losses'] == 10 - team_b_wins
        assert result[2]['ties'] == 0
        assert abs(result[2]['points_for'] - team_b_points_for) < 0.01
        assert abs(result[2]['points_against'] - team_b_points_against) < 0.01

        # Verify standings structure includes all required fields
        for team_id in [1, 2]:
            assert 'name' in result[team_id]
            assert 'division' in result[team_id]
            assert 'owner' in result[team_id]
            assert 'abbreviation' in result[team_id]
            assert 'logo' in result[team_id]
            assert 'overall_rank' in result[team_id]
            assert 'division_rank' in result[team_id]

    def test_calculate_team_standings_with_tie_games(self):
        """Test team standings calculation handles tie games correctly."""
        # Create test data with tie games to validate tie handling
        # Team A: 2 wins, 1 tie, 1 loss
        # Team B: 1 win, 1 tie, 2 losses

        week1_data = {
            'week': 1,
            'divisions': [{'name': 'Division 1', 'teams': [
                {'id': 1, 'name': 'Team A', 'abbreviation': 'TA', 'owner': 'Owner A', 'division': 'Division 1', 'logo': 'logo_a.png',
                 'wins': 1, 'losses': 0, 'ties': 0, 'points_for': 115.5, 'points_against': 110.2},
                {'id': 2, 'name': 'Team B', 'abbreviation': 'TB', 'owner': 'Owner B', 'division': 'Division 1', 'logo': 'logo_b.png',
                 'wins': 0, 'losses': 1, 'ties': 0, 'points_for': 110.2, 'points_against': 115.5}
            ]}],
            'matchups': [{
                'home_team': {'id': 1, 'name': 'Team A'},
                'away_team': {'id': 2, 'name': 'Team B'},
                'home_score': 115.5,  # Team A wins
                'away_score': 110.2
            }]
        }

        week2_data = {
            'week': 2,
            'divisions': [{'name': 'Division 1', 'teams': [
                {'id': 1, 'name': 'Team A', 'abbreviation': 'TA', 'owner': 'Owner A', 'division': 'Division 1', 'logo': 'logo_a.png',
                 'wins': 1, 'losses': 0, 'ties': 1, 'points_for': 234.25, 'points_against': 228.95},
                {'id': 2, 'name': 'Team B', 'abbreviation': 'TB', 'owner': 'Owner B', 'division': 'Division 1', 'logo': 'logo_b.png',
                 'wins': 0, 'losses': 1, 'ties': 1, 'points_for': 228.95, 'points_against': 234.25}
            ]}],
            'matchups': [{
                'home_team': {'id': 2, 'name': 'Team B'},
                'away_team': {'id': 1, 'name': 'Team A'},
                'home_score': 118.75,  # Exact tie game
                'away_score': 118.75
            }]
        }

        week3_data = {
            'week': 3,
            'divisions': [{'name': 'Division 1', 'teams': [
                {'id': 1, 'name': 'Team A', 'abbreviation': 'TA', 'owner': 'Owner A', 'division': 'Division 1', 'logo': 'logo_a.png',
                 'wins': 2, 'losses': 0, 'ties': 1, 'points_for': 356.25, 'points_against': 348.45},
                {'id': 2, 'name': 'Team B', 'abbreviation': 'TB', 'owner': 'Owner B', 'division': 'Division 1', 'logo': 'logo_b.png',
                 'wins': 0, 'losses': 2, 'ties': 1, 'points_for': 348.45, 'points_against': 356.25}
            ]}],
            'matchups': [{
                'home_team': {'id': 1, 'name': 'Team A'},
                'away_team': {'id': 2, 'name': 'Team B'},
                'home_score': 122.0,  # Team A wins again
                'away_score': 119.5
            }]
        }

        week4_data = {
            'week': 4,
            'divisions': [{'name': 'Division 1', 'teams': [
                {'id': 1, 'name': 'Team A', 'abbreviation': 'TA', 'owner': 'Owner A', 'division': 'Division 1', 'logo': 'logo_a.png',
                 'wins': 2, 'losses': 1, 'ties': 1, 'points_for': 476.55, 'points_against': 474.25},
                {'id': 2, 'name': 'Team B', 'abbreviation': 'TB', 'owner': 'Owner B', 'division': 'Division 1', 'logo': 'logo_b.png',
                 'wins': 1, 'losses': 2, 'ties': 1, 'points_for': 474.25, 'points_against': 476.55}
            ]}],
            'matchups': [{
                'home_team': {'id': 2, 'name': 'Team B'},
                'away_team': {'id': 1, 'name': 'Team A'},
                'home_score': 125.8,  # Team B wins
                'away_score': 120.3
            }]
        }

        all_weeks_data = [week1_data, week2_data, week3_data, week4_data]

        # Calculate standings through week 4
        result = self.aggregate_stage._calculate_team_standings(all_weeks_data, 4)

        # Expected cumulative records after 4 weeks:
        # Team A: 2 wins, 1 loss, 1 tie - points: 476.55 PF, 474.25 PA
        # Team B: 1 win, 2 losses, 1 tie - points: 474.25 PF, 476.55 PA

        # Verify Team A's cumulative record
        assert result[1]['wins'] == 2
        assert result[1]['losses'] == 1
        assert result[1]['ties'] == 1
        assert abs(result[1]['points_for'] - 476.55) < 0.01  # 115.5 + 118.75 + 122.0 + 120.3
        assert abs(result[1]['points_against'] - 474.25) < 0.01  # 110.2 + 118.75 + 119.5 + 125.8

        # Verify Team B's cumulative record
        assert result[2]['wins'] == 1
        assert result[2]['losses'] == 2
        assert result[2]['ties'] == 1
        assert abs(result[2]['points_for'] - 474.25) < 0.01  # 110.2 + 118.75 + 119.5 + 125.8
        assert abs(result[2]['points_against'] - 476.55) < 0.01  # 115.5 + 118.75 + 122.0 + 120.3

        # Verify both teams have the same points totals (sum should match)
        total_points = result[1]['points_for'] + result[2]['points_for']
        assert abs(total_points - 950.8) < 0.01

    def test_calculate_team_standings_full_season_accumulation(self):
        """Test team standings calculation for full 14-week regular season."""
        # Create a comprehensive test for full regular season with realistic win/loss distribution
        # Team A: Strong team (10-4 record)
        # Team B: Playoff contender (8-6 record)
        # Team C: Mediocre team (7-7 record)
        # Team D: Struggling team (3-11 record)

        teams_data = [
            {'id': 1, 'name': 'Team A', 'abbreviation': 'TA', 'owner': 'Owner A', 'division': 'Division 1', 'logo': 'logo_a.png'},
            {'id': 2, 'name': 'Team B', 'abbreviation': 'TB', 'owner': 'Owner B', 'division': 'Division 1', 'logo': 'logo_b.png'},
            {'id': 3, 'name': 'Team C', 'abbreviation': 'TC', 'owner': 'Owner C', 'division': 'Division 1', 'logo': 'logo_c.png'},
            {'id': 4, 'name': 'Team D', 'abbreviation': 'TD', 'owner': 'Owner D', 'division': 'Division 1', 'logo': 'logo_d.png'}
        ]

        # Define win patterns for each team to create realistic 14-week records
        # 1=win, 0=loss based on realistic NFL performance curves
        team_a_results = [1,1,1,0,1,1,1,1,0,1,1,1,1,0]  # 10-4
        team_b_results = [1,0,1,1,1,0,1,1,1,0,1,0,1,0]  # 8-6
        team_c_results = [0,1,1,0,1,0,0,1,1,0,1,0,0,1]  # 7-7
        team_d_results = [0,0,0,1,0,0,0,0,0,1,0,0,0,1]  # 3-11

        all_weeks_data = []

        # Track cumulative stats
        team_stats = {
            1: {'wins': 0, 'losses': 0, 'points_for': 0.0, 'points_against': 0.0},
            2: {'wins': 0, 'losses': 0, 'points_for': 0.0, 'points_against': 0.0},
            3: {'wins': 0, 'losses': 0, 'points_for': 0.0, 'points_against': 0.0},
            4: {'wins': 0, 'losses': 0, 'points_for': 0.0, 'points_against': 0.0}
        }

        for week in range(1, 15):  # Weeks 1-14 (regular season only)
            week_idx = week - 1

            # Cycle through matchups: A vs B, C vs D for even distribution
            if week % 2 == 1:  # Odd weeks: A vs B, C vs D
                matchups = [
                    {
                        'home_team': {'id': 1, 'name': 'Team A'},
                        'away_team': {'id': 2, 'name': 'Team B'},
                        'home_score': 125.0 + week if team_a_results[week_idx] else 105.0 + week,
                        'away_score': 105.0 + week if team_a_results[week_idx] else 125.0 + week
                    },
                    {
                        'home_team': {'id': 3, 'name': 'Team C'},
                        'away_team': {'id': 4, 'name': 'Team D'},
                        'home_score': 115.0 + week if team_c_results[week_idx] else 95.0 + week,
                        'away_score': 95.0 + week if team_c_results[week_idx] else 115.0 + week
                    }
                ]
            else:  # Even weeks: A vs C, B vs D
                matchups = [
                    {
                        'home_team': {'id': 1, 'name': 'Team A'},
                        'away_team': {'id': 3, 'name': 'Team C'},
                        'home_score': 125.0 + week if team_a_results[week_idx] else 105.0 + week,
                        'away_score': 105.0 + week if team_a_results[week_idx] else 125.0 + week
                    },
                    {
                        'home_team': {'id': 2, 'name': 'Team B'},
                        'away_team': {'id': 4, 'name': 'Team D'},
                        'home_score': 115.0 + week if team_b_results[week_idx] else 95.0 + week,
                        'away_score': 95.0 + week if team_b_results[week_idx] else 115.0 + week
                    }
                ]

            # Update tracking stats BEFORE creating week data
            for matchup in matchups:
                home_id = matchup['home_team']['id']
                away_id = matchup['away_team']['id']
                home_score = matchup['home_score']
                away_score = matchup['away_score']

                team_stats[home_id]['points_for'] += home_score
                team_stats[home_id]['points_against'] += away_score
                team_stats[away_id]['points_for'] += away_score
                team_stats[away_id]['points_against'] += home_score

                if home_score > away_score:
                    team_stats[home_id]['wins'] += 1
                    team_stats[away_id]['losses'] += 1
                else:
                    team_stats[away_id]['wins'] += 1
                    team_stats[home_id]['losses'] += 1

            # Build teams_data with cumulative standings for this week
            teams_data_with_standings = [
                {'id': 1, 'name': 'Team A', 'abbreviation': 'TA', 'owner': 'Owner A', 'division': 'Division 1', 'logo': 'logo_a.png',
                 'wins': team_stats[1]['wins'], 'losses': team_stats[1]['losses'],
                 'points_for': team_stats[1]['points_for'], 'points_against': team_stats[1]['points_against']},
                {'id': 2, 'name': 'Team B', 'abbreviation': 'TB', 'owner': 'Owner B', 'division': 'Division 1', 'logo': 'logo_b.png',
                 'wins': team_stats[2]['wins'], 'losses': team_stats[2]['losses'],
                 'points_for': team_stats[2]['points_for'], 'points_against': team_stats[2]['points_against']},
                {'id': 3, 'name': 'Team C', 'abbreviation': 'TC', 'owner': 'Owner C', 'division': 'Division 1', 'logo': 'logo_c.png',
                 'wins': team_stats[3]['wins'], 'losses': team_stats[3]['losses'],
                 'points_for': team_stats[3]['points_for'], 'points_against': team_stats[3]['points_against']},
                {'id': 4, 'name': 'Team D', 'abbreviation': 'TD', 'owner': 'Owner D', 'division': 'Division 1', 'logo': 'logo_d.png',
                 'wins': team_stats[4]['wins'], 'losses': team_stats[4]['losses'],
                 'points_for': team_stats[4]['points_for'], 'points_against': team_stats[4]['points_against']}
            ]

            week_data = {
                'week': week,
                'divisions': [{'name': 'Division 1', 'teams': teams_data_with_standings}],
                'matchups': matchups
            }
            all_weeks_data.append(week_data)

        # Calculate standings through week 14 (regular season)
        result = self.aggregate_stage._calculate_team_standings(all_weeks_data, 14)

        # Verify final standings match expected records
        for team_id in [1, 2, 3, 4]:
            expected_wins = team_stats[team_id]['wins']
            expected_losses = team_stats[team_id]['losses']
            expected_pf = team_stats[team_id]['points_for']
            expected_pa = team_stats[team_id]['points_against']

            assert result[team_id]['wins'] == expected_wins, f"Team {team_id} wins mismatch"
            assert result[team_id]['losses'] == expected_losses, f"Team {team_id} losses mismatch"
            assert result[team_id]['ties'] == 0, f"Team {team_id} should have no ties"
            assert abs(result[team_id]['points_for'] - expected_pf) < 0.01, f"Team {team_id} PF mismatch"
            assert abs(result[team_id]['points_against'] - expected_pa) < 0.01, f"Team {team_id} PA mismatch"

        # Verify total games played (each team plays 14 games in regular season)
        for team_id in [1, 2, 3, 4]:
            total_games = result[team_id]['wins'] + result[team_id]['losses'] + result[team_id]['ties']
            assert total_games == 14, f"Team {team_id} should have played 14 games, got {total_games}"

        # Verify league-wide points balance (total points scored = total points allowed)
        total_pf = sum(result[team_id]['points_for'] for team_id in [1, 2, 3, 4])
        total_pa = sum(result[team_id]['points_against'] for team_id in [1, 2, 3, 4])
        assert abs(total_pf - total_pa) < 0.01, "League points for/against should balance"

    def test_calculate_team_standings_win_loss_priority(self):
        """Test that win/loss record takes priority over point totals in rankings."""
        # Create scenario with 4 teams where all teams play each week
        # Team A: 2-0 (best record)
        # Team B: 1-1 (middle record)
        # Team C: 1-1 (middle record)
        # Team D: 0-2 (worst record)
        # Expected ranking: Team A first, then B/C by tiebreaker, then D

        # Week 1: Team A beats Team D, Team B beats Team C
        week1_data = {
            'week': 1,
            'divisions': [{'name': 'Division 1', 'teams': [
                {'id': 1, 'name': 'Team A', 'abbreviation': 'TA', 'owner': 'Owner A', 'division': 'Division 1', 'logo': 'logo_a.png'},
                {'id': 2, 'name': 'Team B', 'abbreviation': 'TB', 'owner': 'Owner B', 'division': 'Division 1', 'logo': 'logo_b.png'},
                {'id': 3, 'name': 'Team C', 'abbreviation': 'TC', 'owner': 'Owner C', 'division': 'Division 1', 'logo': 'logo_c.png'},
                {'id': 4, 'name': 'Team D', 'abbreviation': 'TD', 'owner': 'Owner D', 'division': 'Division 1', 'logo': 'logo_d.png'}
            ]}],
            'matchups': [
                {
                    'home_team': {'id': 1, 'name': 'Team A'},
                    'away_team': {'id': 4, 'name': 'Team D'},
                    'home_score': 150.0,
                    'away_score': 90.0
                },
                {
                    'home_team': {'id': 2, 'name': 'Team B'},
                    'away_team': {'id': 3, 'name': 'Team C'},
                    'home_score': 120.0,
                    'away_score': 100.0
                }
            ]
        }

        # Week 2: Team A beats Team C, Team C beats Team D (wait, that's wrong - C should beat D)
        # Let me restructure: Team A beats Team B, Team C beats Team D
        week2_data = {
            'week': 2,
            'divisions': [{'name': 'Division 1', 'teams': [
                {'id': 1, 'name': 'Team A', 'abbreviation': 'TA', 'owner': 'Owner A', 'division': 'Division 1', 'logo': 'logo_a.png'},
                {'id': 2, 'name': 'Team B', 'abbreviation': 'TB', 'owner': 'Owner B', 'division': 'Division 1', 'logo': 'logo_b.png'},
                {'id': 3, 'name': 'Team C', 'abbreviation': 'TC', 'owner': 'Owner C', 'division': 'Division 1', 'logo': 'logo_c.png'},
                {'id': 4, 'name': 'Team D', 'abbreviation': 'TD', 'owner': 'Owner D', 'division': 'Division 1', 'logo': 'logo_d.png'}
            ]}],
            'matchups': [
                {
                    'home_team': {'id': 1, 'name': 'Team A'},
                    'away_team': {'id': 2, 'name': 'Team B'},
                    'home_score': 140.0,
                    'away_score': 110.0
                },
                {
                    'home_team': {'id': 3, 'name': 'Team C'},
                    'away_team': {'id': 4, 'name': 'Team D'},
                    'home_score': 115.0,
                    'away_score': 95.0
                }
            ]
        }

        all_weeks_data = [week1_data, week2_data]

        # Calculate standings through week 2
        result = self.aggregate_stage._calculate_team_standings(all_weeks_data, 2)

        # Verify records computed from matchups:
        # Team A: 2-0 (beat D 150-90, beat B 140-110) = 290 PF, 200 PA
        # Team B: 1-1 (beat C 120-100, lost to A 110-140) = 230 PF, 240 PA
        # Team C: 1-1 (lost to B 100-120, beat D 115-95) = 215 PF, 215 PA
        # Team D: 0-2 (lost to A 90-150, lost to C 95-115) = 185 PF, 265 PA

        assert result[1]['wins'] == 2 and result[1]['losses'] == 0  # Team A: 2-0
        assert result[2]['wins'] == 1 and result[2]['losses'] == 1  # Team B: 1-1
        assert result[3]['wins'] == 1 and result[3]['losses'] == 1  # Team C: 1-1
        assert result[4]['wins'] == 0 and result[4]['losses'] == 2  # Team D: 0-2

        # Verify ranking: Team A (2-0) > Team B (1-1, 230 PF) > Team C (1-1, 215 PF) > Team D (0-2)
        assert result[1]['overall_rank'] == 1  # Team A: best record
        assert result[2]['overall_rank'] == 2  # Team B: tied record with C, but more points for
        assert result[3]['overall_rank'] == 3  # Team C: tied record with B, but fewer points for
        assert result[4]['overall_rank'] == 4  # Team D: worst record

    def test_calculate_team_standings_points_for_tiebreaker(self):
        """Test that points for is used as tiebreaker when teams have identical records."""
        # Create scenario with 4 teams where 3 teams end up with identical 1-1 records
        # but different point totals. Use 4 teams to ensure all teams have matchups each week.

        # Week 1: A beats B (high scoring), C beats D (low scoring)
        week1_data = {
            'week': 1,
            'divisions': [{'name': 'Division 1', 'teams': [
                {'id': 1, 'name': 'Team A', 'abbreviation': 'TA', 'owner': 'Owner A', 'division': 'Division 1', 'logo': 'logo_a.png'},
                {'id': 2, 'name': 'Team B', 'abbreviation': 'TB', 'owner': 'Owner B', 'division': 'Division 1', 'logo': 'logo_b.png'},
                {'id': 3, 'name': 'Team C', 'abbreviation': 'TC', 'owner': 'Owner C', 'division': 'Division 1', 'logo': 'logo_c.png'},
                {'id': 4, 'name': 'Team D', 'abbreviation': 'TD', 'owner': 'Owner D', 'division': 'Division 1', 'logo': 'logo_d.png'}
            ]}],
            'matchups': [
                {
                    'home_team': {'id': 1, 'name': 'Team A'},
                    'away_team': {'id': 2, 'name': 'Team B'},
                    'home_score': 150.0,  # Team A high scoring win
                    'away_score': 120.0
                },
                {
                    'home_team': {'id': 3, 'name': 'Team C'},
                    'away_team': {'id': 4, 'name': 'Team D'},
                    'home_score': 95.0,   # Team C low scoring win
                    'away_score': 80.0
                }
            ]
        }

        # Week 2: B beats C (medium scoring), D beats A (medium scoring)
        # This creates: A(1-1, 240 PF), B(1-1, 230 PF), C(1-1, 180 PF), D(1-1, 170 PF)
        week2_data = {
            'week': 2,
            'divisions': [{'name': 'Division 1', 'teams': [
                {'id': 1, 'name': 'Team A', 'abbreviation': 'TA', 'owner': 'Owner A', 'division': 'Division 1', 'logo': 'logo_a.png'},
                {'id': 2, 'name': 'Team B', 'abbreviation': 'TB', 'owner': 'Owner B', 'division': 'Division 1', 'logo': 'logo_b.png'},
                {'id': 3, 'name': 'Team C', 'abbreviation': 'TC', 'owner': 'Owner C', 'division': 'Division 1', 'logo': 'logo_c.png'},
                {'id': 4, 'name': 'Team D', 'abbreviation': 'TD', 'owner': 'Owner D', 'division': 'Division 1', 'logo': 'logo_d.png'}
            ]}],
            'matchups': [
                {
                    'home_team': {'id': 2, 'name': 'Team B'},
                    'away_team': {'id': 3, 'name': 'Team C'},
                    'home_score': 110.0,  # Team B medium scoring win
                    'away_score': 85.0
                },
                {
                    'home_team': {'id': 4, 'name': 'Team D'},
                    'away_team': {'id': 1, 'name': 'Team A'},
                    'home_score': 90.0,   # Team D low scoring win over A
                    'away_score': 90.0    # This is actually a tie, let me fix
                }
            ]
        }

        # Fix: Make D beat A clearly
        week2_data['matchups'][1]['home_score'] = 100.0
        week2_data['matchups'][1]['away_score'] = 90.0

        all_weeks_data = [week1_data, week2_data]

        # Calculate standings through week 2
        result = self.aggregate_stage._calculate_team_standings(all_weeks_data, 2)

        # All teams should have identical 1-1 records
        # Team A: beat B (150-120), lost to D (90-100) = 1-1, 240 PF
        # Team B: lost to A (120-150), beat C (110-85) = 1-1, 230 PF
        # Team C: beat D (95-80), lost to B (85-110) = 1-1, 180 PF
        # Team D: lost to C (80-95), beat A (100-90) = 1-1, 180 PF
        assert result[1]['wins'] == 1 and result[1]['losses'] == 1  # Team A: 1-1
        assert result[2]['wins'] == 1 and result[2]['losses'] == 1  # Team B: 1-1
        assert result[3]['wins'] == 1 and result[3]['losses'] == 1  # Team C: 1-1
        assert result[4]['wins'] == 1 and result[4]['losses'] == 1  # Team D: 1-1

        # Verify points for totals (determine tiebreaker ranking)
        assert result[1]['points_for'] == 240.0  # Team A: 150 + 90
        assert result[2]['points_for'] == 230.0  # Team B: 120 + 110
        assert result[3]['points_for'] == 180.0  # Team C: 95 + 85
        assert result[4]['points_for'] == 180.0  # Team D: 80 + 100

        # Verify tiebreaker ranking by points for: A > B > C/D
        # A (1-1, 240 PF) > B (1-1, 230 PF) > C (1-1, 180 PF, 195 PA) > D (1-1, 180 PF, 185 PA)
        # C and D have same PF, so use PA as tiebreaker: D (185 PA) > C (195 PA)
        assert result[1]['overall_rank'] == 1  # Team A: highest points for
        assert result[2]['overall_rank'] == 2  # Team B: second highest points for
        # C and D tie on PF, D has fewer PA so should rank higher
        assert result[4]['overall_rank'] == 3  # Team D: 180 PF, 185 PA
        assert result[3]['overall_rank'] == 4  # Team C: 180 PF, 195 PA

    def test_calculate_team_standings_points_against_tiebreaker(self):
        """Test that points against is used as final tiebreaker when teams have identical records and points for."""
        # Create scenario where teams have identical records and points for, but different points against
        # This tests the complete tiebreaker hierarchy

        # Week 1: Team A plays twice (beats B, loses to C), Team B plays once, Team C plays once
        # After Week 1: A (1-1, 195 PF, 190 PA), B (0-1, 90 PF, 100 PA), C (1-0, 100 PF, 95 PA)
        week1_data = {
            'week': 1,
            'divisions': [{'name': 'Division 1', 'teams': [
                {'id': 1, 'name': 'Team A', 'abbreviation': 'TA', 'owner': 'Owner A', 'division': 'Division 1', 'logo': 'logo_a.png',
                 'wins': 1, 'losses': 1, 'points_for': 195.0, 'points_against': 190.0},
                {'id': 2, 'name': 'Team B', 'abbreviation': 'TB', 'owner': 'Owner B', 'division': 'Division 1', 'logo': 'logo_b.png',
                 'wins': 0, 'losses': 1, 'points_for': 90.0, 'points_against': 100.0},
                {'id': 3, 'name': 'Team C', 'abbreviation': 'TC', 'owner': 'Owner C', 'division': 'Division 1', 'logo': 'logo_c.png',
                 'wins': 1, 'losses': 0, 'points_for': 100.0, 'points_against': 95.0}
            ]}],
            'matchups': [
                {
                    'home_team': {'id': 1, 'name': 'Team A'},
                    'away_team': {'id': 2, 'name': 'Team B'},
                    'home_score': 100.0,  # Team A wins with 100
                    'away_score': 90.0    # Team B loses with 90
                },
                {
                    'home_team': {'id': 3, 'name': 'Team C'},
                    'away_team': {'id': 1, 'name': 'Team A'},  # A plays twice this week
                    'home_score': 100.0,  # Team C wins with 100
                    'away_score': 95.0    # Team A loses with 95
                }
            ]
        }

        # Week 2: Team B plays twice (beats C, beats A), Team A plays once, Team C plays once
        # After Week 2: A (1-2, 295 PF, 295 PA), B (2-1, 295 PF, 285 PA), C (1-1, 185 PF, 195 PA)
        week2_data = {
            'week': 2,
            'divisions': [{'name': 'Division 1', 'teams': [
                {'id': 1, 'name': 'Team A', 'abbreviation': 'TA', 'owner': 'Owner A', 'division': 'Division 1', 'logo': 'logo_a.png',
                 'wins': 1, 'losses': 2, 'points_for': 295.0, 'points_against': 295.0, 'standing': 3},
                {'id': 2, 'name': 'Team B', 'abbreviation': 'TB', 'owner': 'Owner B', 'division': 'Division 1', 'logo': 'logo_b.png',
                 'wins': 2, 'losses': 1, 'points_for': 295.0, 'points_against': 285.0, 'standing': 1},
                {'id': 3, 'name': 'Team C', 'abbreviation': 'TC', 'owner': 'Owner C', 'division': 'Division 1', 'logo': 'logo_c.png',
                 'wins': 1, 'losses': 1, 'points_for': 185.0, 'points_against': 195.0, 'standing': 2}
            ]}],
            'matchups': [
                {
                    'home_team': {'id': 2, 'name': 'Team B'},
                    'away_team': {'id': 3, 'name': 'Team C'},
                    'home_score': 100.0,  # Team B wins with 100
                    'away_score': 85.0    # Team C loses with 85
                },
                {
                    'home_team': {'id': 1, 'name': 'Team A'},
                    'away_team': {'id': 2, 'name': 'Team B'},
                    'home_score': 100.0,  # Team A
                    'away_score': 105.0   # Team B wins (B has two games this week)
                }
            ]
        }

        all_weeks_data = [week1_data, week2_data]

        # Calculate standings through week 2
        result = self.aggregate_stage._calculate_team_standings(all_weeks_data, 2)

        # Calculate expected records:
        # Team A: Beat B (week 1), Lost to C (week 1), Lost to B (week 2) → 1-2
        # Team B: Lost to A (week 1), Beat C (week 2), Beat A (week 2) → 2-1
        # Team C: Beat A (week 1), Lost to B (week 2) → 1-1

        # Verify win/loss records
        assert result[1]['wins'] == 1 and result[1]['losses'] == 2  # Team A: 1-2
        assert result[2]['wins'] == 2 and result[2]['losses'] == 1  # Team B: 2-1
        assert result[3]['wins'] == 1 and result[3]['losses'] == 1  # Team C: 1-1

        # Calculate points for/against:
        # Team A: 100 + 95 + 100 = 295 PF, 90 + 100 + 105 = 295 PA
        # Team B: 90 + 100 + 105 = 295 PF, 100 + 85 + 100 = 285 PA
        # Team C: 100 + 85 = 185 PF, 95 + 100 = 195 PA (corrected)
        assert result[1]['points_for'] == 295.0  # Team A
        assert result[2]['points_for'] == 295.0  # Team B (same as A)
        assert result[3]['points_for'] == 185.0  # Team C

        # Verify points against (lower is better)
        assert result[1]['points_against'] == 295.0  # Team A: worse defense
        assert result[2]['points_against'] == 285.0  # Team B: better defense
        assert result[3]['points_against'] == 195.0  # Team C: best defense

        # Verify final ranking: B (2-1) > C (1-1) > A (1-2)
        # Even though A and B have same points for, B has better record and better points against
        assert result[2]['overall_rank'] == 1  # Team B: best record
        assert result[3]['overall_rank'] == 2  # Team C: middle record
        assert result[1]['overall_rank'] == 3  # Team A: worst record

    @patch('boto3.resource')
    def test_fetch_historical_data_multiple_weeks_success(self, mock_boto3_resource):
        """Test successful fetching of multiple weeks of historical data from DynamoDB."""
        from decimal import Decimal

        # Mock DynamoDB table and responses
        mock_table = MagicMock()
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        # Create historical data for weeks 1-5 (current week is 6)
        historical_items = {}
        for week in range(1, 6):
            historical_items[f'2025-{week:02d}'] = {
                'season_week': f'2025-{week:02d}',
                'data_type_id': 'weekly_report',
                'league_id': Decimal('380491'),
                'data': {
                    'week': Decimal(str(week)),
                    'season': Decimal('2025'),
                    'league_id': Decimal('380491'),
                    'matchups': [{
                        'home_team': {'name': f'Team A Week {week}'},
                        'away_team': {'name': f'Team B Week {week}'},
                        'home_score': Decimal(str(100 + week * 5)),  # Increasing scores each week
                        'away_score': Decimal(str(95 + week * 3))
                    }]
                }
            }

        # Mock get_item to return appropriate historical data based on season_week
        def mock_get_item(Key):
            season_week = Key['season_week']
            if season_week in historical_items:
                return {'Item': historical_items[season_week]}
            else:
                return {}  # No item found

        mock_table.get_item.side_effect = mock_get_item

        # Test data for current week 6
        current_data = {
            'season': 2025,
            'week': 6,
            'league_id': '380491'
        }

        # Mock config
        self.aggregate_stage.config.pipeline.aws.dynamodb_table = 'test-table'
        self.aggregate_stage.config.pipeline.aws.region = 'us-east-1'

        result, is_latest = self.aggregate_stage._fetch_historical_data(current_data)

        # Verify correct number of DynamoDB calls (weeks 1-5 for historical, plus future week checks)
        expected_calls = [
            call(Key={'season_week': '2025-01', 'data_type_id': 'weekly_report'}),
            call(Key={'season_week': '2025-02', 'data_type_id': 'weekly_report'}),
            call(Key={'season_week': '2025-03', 'data_type_id': 'weekly_report'}),
            call(Key={'season_week': '2025-04', 'data_type_id': 'weekly_report'}),
            call(Key={'season_week': '2025-05', 'data_type_id': 'weekly_report'})
        ]
        mock_table.get_item.assert_has_calls(expected_calls, any_order=False)

        # Verify all 5 weeks of historical data returned
        assert len(result) == 5

        # is_latest should be True since no future weeks exist (mock returns empty for week 7+)
        assert is_latest is True

        # Verify data is properly converted from Decimal and ordered correctly
        for i, week_data in enumerate(result):
            expected_week = i + 1
            assert week_data['week'] == expected_week
            assert week_data['season'] == 2025
            assert isinstance(week_data['week'], (int, float))  # Converted from Decimal
            assert isinstance(week_data['season'], (int, float))  # Converted from Decimal

            # Verify matchup data is correctly converted
            matchup = week_data['matchups'][0]
            assert isinstance(matchup['home_score'], (int, float))  # Converted from Decimal
            assert isinstance(matchup['away_score'], (int, float))  # Converted from Decimal
            assert matchup['home_score'] == 100 + expected_week * 5
            assert matchup['away_score'] == 95 + expected_week * 3

    @patch('boto3.resource')
    def test_fetch_historical_data_missing_weeks(self, mock_boto3_resource):
        """Test fetching historical data when some weeks are missing from DynamoDB."""
        from decimal import Decimal

        # Mock DynamoDB table and responses
        mock_table = MagicMock()
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamodb

        # Create historical data for only weeks 1, 3, and 5 (weeks 2 and 4 missing)
        available_weeks = [1, 3, 5]
        historical_items = {}
        for week in available_weeks:
            historical_items[f'2025-{week:02d}'] = {
                'season_week': f'2025-{week:02d}',
                'data_type_id': 'weekly_report',
                'league_id': Decimal('380491'),
                'data': {
                    'week': Decimal(str(week)),
                    'season': Decimal('2025'),
                    'league_id': Decimal('380491'),
                    'matchups': [{
                        'home_team': {'name': f'Team A Week {week}'},
                        'away_team': {'name': f'Team B Week {week}'},
                        'home_score': Decimal(str(100 + week * 5)),
                        'away_score': Decimal(str(95 + week * 3))
                    }]
                }
            }

        # Mock get_item to return data only for available weeks
        def mock_get_item(Key):
            season_week = Key['season_week']
            if season_week in historical_items:
                return {'Item': historical_items[season_week]}
            else:
                return {}  # No item found for missing weeks

        mock_table.get_item.side_effect = mock_get_item

        # Test data for current week 6 (should try to fetch weeks 1-5)
        current_data = {
            'season': 2025,
            'week': 6,
            'league_id': '380491'
        }

        # Mock config
        self.aggregate_stage.config.pipeline.aws.dynamodb_table = 'test-table'
        self.aggregate_stage.config.pipeline.aws.region = 'us-east-1'

        result, is_latest = self.aggregate_stage._fetch_historical_data(current_data)

        # Verify it still tries to fetch all weeks 1-5
        expected_calls = [
            call(Key={'season_week': '2025-01', 'data_type_id': 'weekly_report'}),
            call(Key={'season_week': '2025-02', 'data_type_id': 'weekly_report'}),
            call(Key={'season_week': '2025-03', 'data_type_id': 'weekly_report'}),
            call(Key={'season_week': '2025-04', 'data_type_id': 'weekly_report'}),
            call(Key={'season_week': '2025-05', 'data_type_id': 'weekly_report'})
        ]
        mock_table.get_item.assert_has_calls(expected_calls, any_order=False)

        # Verify only available weeks (1, 3, 5) are returned
        assert len(result) == 3

        # is_latest should be True since no future weeks exist
        assert is_latest is True

        # Verify the correct weeks are present and in order
        returned_weeks = [week_data['week'] for week_data in result]
        assert returned_weeks == [1, 3, 5]

        # Verify data integrity for returned weeks
        for i, week_data in enumerate(result):
            expected_week = available_weeks[i]
            assert week_data['week'] == expected_week
            assert week_data['season'] == 2025
            assert isinstance(week_data['week'], (int, float))

            matchup = week_data['matchups'][0]
            assert matchup['home_score'] == 100 + expected_week * 5
            assert matchup['away_score'] == 95 + expected_week * 3

    def test_calculate_division_strength_basic(self):
        """Test basic division strength calculation with inter-division matchups."""
        # Create sample data with 3 divisions and inter-division games
        all_weeks_data = [
            {
                "divisions": [
                    {"name": "Adams", "teams": [{"id": 1, "name": "Team A"}, {"id": 2, "name": "Team B"}]},
                    {"name": "Smythe", "teams": [{"id": 3, "name": "Team C"}, {"id": 4, "name": "Team D"}]},
                    {"name": "Jones", "teams": [{"id": 5, "name": "Team E"}, {"id": 6, "name": "Team F"}]}
                ],
                "matchups": [
                    # Inter-division games - Adams vs Smythe
                    {"home_team": {"id": 1, "name": "Team A"}, "away_team": {"id": 3, "name": "Team C"},
                     "home_score": 100, "away_score": 90},  # Adams wins
                    {"home_team": {"id": 2, "name": "Team B"}, "away_team": {"id": 4, "name": "Team D"},
                     "home_score": 85, "away_score": 95},   # Smythe wins

                    # Inter-division games - Adams vs Jones
                    {"home_team": {"id": 1, "name": "Team A"}, "away_team": {"id": 5, "name": "Team E"},
                     "home_score": 110, "away_score": 80},  # Adams wins

                    # Inter-division games - Smythe vs Jones
                    {"home_team": {"id": 3, "name": "Team C"}, "away_team": {"id": 6, "name": "Team F"},
                     "home_score": 95, "away_score": 85},   # Smythe wins

                    # Intra-division games (should not count for wins/losses)
                    {"home_team": {"id": 1, "name": "Team A"}, "away_team": {"id": 2, "name": "Team B"},
                     "home_score": 120, "away_score": 100}, # Adams intra-division
                    {"home_team": {"id": 3, "name": "Team C"}, "away_team": {"id": 4, "name": "Team D"},
                     "home_score": 90, "away_score": 80}    # Smythe intra-division
                ]
            }
        ]

        result = self.aggregate_stage._calculate_division_strength(all_weeks_data)

        assert 'divisions' in result
        assert 'ranking_criteria' in result
        assert len(result['divisions']) == 3

        # Verify division data structure
        divisions = {div['name']: div for div in result['divisions']}

        # Adams: 2 wins (vs Team C, vs Team E), 1 loss (Team B vs Team D)
        assert divisions['Adams']['wins'] == 2
        assert divisions['Adams']['losses'] == 1

        # Smythe: 2 wins (Team D vs Team B, Team C vs Team F), 1 loss (Team C vs Team A)
        assert divisions['Smythe']['wins'] == 2
        assert divisions['Smythe']['losses'] == 1

        # Jones: 0 wins, 2 losses (Team E vs Team A, Team F vs Team C)
        assert divisions['Jones']['wins'] == 0
        assert divisions['Jones']['losses'] == 2

        # Verify points calculations (including intra-division games)
        # Adams: 100(A vs C) + 85(B vs D) + 110(A vs E) + 120(A vs B) + 100(B vs A) = 515 points for
        # Adams: 90(C vs A) + 95(D vs B) + 80(E vs A) + 100(B vs A) + 120(A vs B) = 485 points against
        assert abs(divisions['Adams']['points_for'] - 515.0) < 0.01
        assert abs(divisions['Adams']['points_against'] - 485.0) < 0.01

        # Verify ranking (should be sorted by wins desc, losses asc)
        assert result['divisions'][0]['name'] in ['Adams', 'Smythe']  # Both have 2 wins, 1 loss
        assert result['divisions'][2]['name'] == 'Jones'  # Should be last with 0 wins

    def test_calculate_division_strength_with_ties(self):
        """Test division strength calculation excludes tie games."""
        all_weeks_data = [
            {
                "divisions": [
                    {"name": "Adams", "teams": [{"id": 1, "name": "Team A"}]},
                    {"name": "Smythe", "teams": [{"id": 2, "name": "Team B"}]}
                ],
                "matchups": [
                    # Tie game - should be ignored for wins/losses
                    {"home_team": {"id": 1, "name": "Team A"}, "away_team": {"id": 2, "name": "Team B"},
                     "home_score": 100, "away_score": 100},
                    # Regular win
                    {"home_team": {"id": 1, "name": "Team A"}, "away_team": {"id": 2, "name": "Team B"},
                     "home_score": 110, "away_score": 90}
                ]
            }
        ]

        result = self.aggregate_stage._calculate_division_strength(all_weeks_data)
        divisions = {div['name']: div for div in result['divisions']}

        # Adams should have 1 win, 0 losses (tie ignored)
        assert divisions['Adams']['wins'] == 1
        assert divisions['Adams']['losses'] == 0

        # Smythe should have 0 wins, 1 loss (tie ignored)
        assert divisions['Smythe']['wins'] == 0
        assert divisions['Smythe']['losses'] == 1

        # Points should still include tie game
        assert abs(divisions['Adams']['points_for'] - 210.0) < 0.01  # 100 + 110
        assert abs(divisions['Smythe']['points_for'] - 190.0) < 0.01  # 100 + 90

    def test_calculate_division_strength_intra_division_only(self):
        """Test division strength when only intra-division games exist."""
        all_weeks_data = [
            {
                "divisions": [
                    {"name": "Adams", "teams": [{"id": 1, "name": "Team A"}, {"id": 2, "name": "Team B"}]},
                    {"name": "Smythe", "teams": [{"id": 3, "name": "Team C"}, {"id": 4, "name": "Team D"}]}
                ],
                "matchups": [
                    # Only intra-division games
                    {"home_team": {"id": 1, "name": "Team A"}, "away_team": {"id": 2, "name": "Team B"},
                     "home_score": 100, "away_score": 90},
                    {"home_team": {"id": 3, "name": "Team C"}, "away_team": {"id": 4, "name": "Team D"},
                     "home_score": 80, "away_score": 85}
                ]
            }
        ]

        result = self.aggregate_stage._calculate_division_strength(all_weeks_data)
        divisions = {div['name']: div for div in result['divisions']}

        # No inter-division games, so wins/losses should be 0
        for division in divisions.values():
            assert division['wins'] == 0
            assert division['losses'] == 0

        # Points should still be calculated from all games
        assert abs(divisions['Adams']['points_for'] - 190.0) < 0.01  # 100 + 90
        assert abs(divisions['Smythe']['points_for'] - 165.0) < 0.01  # 80 + 85

    def test_calculate_division_strength_ranking_criteria(self):
        """Test division strength ranking with all criteria."""
        all_weeks_data = [
            {
                "divisions": [
                    {"name": "Division A", "teams": [{"id": 1, "name": "Team 1"}, {"id": 2, "name": "Team 2"}]},
                    {"name": "Division B", "teams": [{"id": 3, "name": "Team 3"}, {"id": 4, "name": "Team 4"}]},
                    {"name": "Division C", "teams": [{"id": 5, "name": "Team 5"}, {"id": 6, "name": "Team 6"}]},
                    {"name": "Division D", "teams": [{"id": 7, "name": "Team 7"}, {"id": 8, "name": "Team 8"}]}
                ],
                "matchups": [
                    # Division A: 3 wins, 1 loss, high scoring
                    {"home_team": {"id": 1}, "away_team": {"id": 3}, "home_score": 120, "away_score": 80},  # A wins vs B
                    {"home_team": {"id": 2}, "away_team": {"id": 5}, "home_score": 115, "away_score": 85},  # A wins vs C
                    {"home_team": {"id": 1}, "away_team": {"id": 7}, "home_score": 110, "away_score": 90},  # A wins vs D
                    {"home_team": {"id": 3}, "away_team": {"id": 2}, "home_score": 100, "away_score": 95},  # B wins vs A

                    # Division B: 2 wins, 2 losses, medium scoring
                    {"home_team": {"id": 4}, "away_team": {"id": 5}, "home_score": 95, "away_score": 85},   # B wins vs C
                    {"home_team": {"id": 3}, "away_team": {"id": 7}, "home_score": 90, "away_score": 80},   # B wins vs D
                    {"home_team": {"id": 6}, "away_team": {"id": 4}, "home_score": 85, "away_score": 80},   # C wins vs B

                    # Division C: 1 win, 3 losses, low scoring
                    {"home_team": {"id": 8}, "away_team": {"id": 5}, "home_score": 75, "away_score": 70},   # D wins vs C

                    # Division D: 1 win, 2 losses, but good points against
                    # (Already covered above)
                ]
            }
        ]

        result = self.aggregate_stage._calculate_division_strength(all_weeks_data)
        divisions = result['divisions']

        # Should be ranked by: wins (desc), losses (asc), points for (desc), points against (desc)
        # Division A: 3 wins, 1 loss (best record)
        assert divisions[0]['name'] == 'Division A'
        assert divisions[0]['rank'] == 1
        assert divisions[0]['wins'] == 3
        assert divisions[0]['losses'] == 1

        # Rankings should be 1-4
        ranks = [div['rank'] for div in divisions]
        assert ranks == [1, 2, 3, 4]

    def test_calculate_division_strength_no_data(self):
        """Test division strength calculation with no data."""
        result = self.aggregate_stage._calculate_division_strength([])

        assert result['divisions'] == []
        assert 'error' not in result

    def test_calculate_division_strength_missing_division_info(self):
        """Test division strength calculation when division info is missing."""
        all_weeks_data = [
            {
                "matchups": [
                    {"home_team": {"id": 1, "name": "Team A"}, "away_team": {"id": 2, "name": "Team B"},
                     "home_score": 100, "away_score": 90}
                ]
                # Missing 'divisions' key
            }
        ]

        result = self.aggregate_stage._calculate_division_strength(all_weeks_data)

        assert result['divisions'] == []
        assert 'ranking_criteria' in result

    def test_fetch_league_history_success(self):
        """Test successful league history fetch from DynamoDB."""
        league_id = "380491"

        # Mock league history data
        mock_history = {
            'metadata': {
                'league_id': '380491',
                'league_name': 'Test League',
                'total_seasons': 3,
                'year_range': '2022-2024'
            },
            'seasons': [
                {
                    'year': 2024,
                    'champion': {
                        'team_id': 1,
                        'team_name': 'Team A',
                        'owner_name': 'Owner A',
                        'wins': 12,
                        'losses': 2,
                        'points_for': 1500.50
                    }
                }
            ]
        }

        with patch('src.uploaders.history_uploader.HistoryUploader') as mock_uploader_class:
            mock_uploader = Mock()
            mock_uploader.fetch_league_history.return_value = mock_history
            mock_uploader_class.return_value = mock_uploader

            result = self.aggregate_stage._fetch_league_history(league_id)

            assert result is not None
            assert result['metadata']['league_id'] == '380491'
            assert result['metadata']['total_seasons'] == 3
            assert len(result['seasons']) == 1
            assert result['seasons'][0]['year'] == 2024
            mock_uploader.fetch_league_history.assert_called_once_with(league_id)

    def test_fetch_league_history_not_found(self):
        """Test league history fetch when no data exists."""
        league_id = "999999"

        with patch('src.uploaders.history_uploader.HistoryUploader') as mock_uploader_class:
            mock_uploader = Mock()
            mock_uploader.fetch_league_history.return_value = None
            mock_uploader_class.return_value = mock_uploader

            result = self.aggregate_stage._fetch_league_history(league_id)

            assert result is None

    def test_fetch_league_history_boto3_not_available(self):
        """Test league history fetch when boto3 is not available."""
        league_id = "380491"

        # Mock the import to raise ImportError
        def mock_import(name, *args, **kwargs):
            if name == 'boto3' or (args and 'boto3' in str(args)):
                raise ImportError("boto3 not available")
            return __import__(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            result = self.aggregate_stage._fetch_league_history(league_id)

            assert result is None

    def test_fetch_league_history_no_credentials(self):
        """Test league history fetch with no AWS credentials."""
        from botocore.exceptions import NoCredentialsError
        league_id = "380491"

        with patch('src.uploaders.history_uploader.HistoryUploader') as mock_uploader_class:
            mock_uploader = Mock()
            mock_uploader.fetch_league_history.side_effect = NoCredentialsError()
            mock_uploader_class.return_value = mock_uploader

            result = self.aggregate_stage._fetch_league_history(league_id)

            assert result is None

    def test_fetch_league_history_exception(self):
        """Test league history fetch with unexpected exception."""
        league_id = "380491"

        with patch('src.uploaders.history_uploader.HistoryUploader') as mock_uploader_class:
            mock_uploader = Mock()
            mock_uploader.fetch_league_history.side_effect = Exception("Unexpected error")
            mock_uploader_class.return_value = mock_uploader

            result = self.aggregate_stage._fetch_league_history(league_id)

            assert result is None

    def test_create_enhanced_data_with_league_history(self):
        """Test enhanced data creation includes league history."""
        # Mock league history
        league_history = {
            'metadata': {
                'league_id': '380491',
                'total_seasons': 2,
                'year_range': '2023-2024'
            },
            'seasons': [
                {
                    'year': 2024,
                    'champion': {
                        'team_name': 'Team A',
                        'owner_name': 'Owner A',
                        'wins': 11,
                        'losses': 3
                    }
                }
            ]
        }

        # Create enhanced data with league history
        enhanced_data = self.aggregate_stage._create_enhanced_data(
            self.sample_raw_data,
            "test_record_id",
            [],
            True,
            league_history
        )

        # Verify league history is included
        assert 'league_history' in enhanced_data
        assert enhanced_data['league_history'] == league_history
        assert enhanced_data['metadata']['league_history_available'] is True

    def test_create_enhanced_data_without_league_history(self):
        """Test enhanced data creation when league history is not available."""
        # Create enhanced data without league history
        enhanced_data = self.aggregate_stage._create_enhanced_data(
            self.sample_raw_data,
            "test_record_id",
            [],
            True,
            None
        )

        # Verify league history is None
        assert 'league_history' in enhanced_data
        assert enhanced_data['league_history'] is None
        assert enhanced_data['metadata']['league_history_available'] is False