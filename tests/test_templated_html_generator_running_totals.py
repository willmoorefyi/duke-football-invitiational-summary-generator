import pytest
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.generators.templated_html_generator import TemplatedFantasyHTMLGenerator


class TestTemplatedHTMLGeneratorRunningTotals:
    """Test suite for running totals functionality in HTML generator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TemplatedFantasyHTMLGenerator()

        # Sample enhanced data with running totals
        self.sample_enhanced_data = {
            "current_week": {
                "league_id": 380491,
                "league_name": "Duke Football Invitational",
                "season": 2025,
                "week": 1,
                "report_date": "2025-09-17T15:32:03.569584",
                "divisions": [
                    {
                        "name": "Adams",
                        "teams": [
                            {
                                "id": 3,
                                "name": "They Stole Danny's Dimes",
                                "logo": "https://example.com/team3.png"
                            },
                            {
                                "id": 1,
                                "name": "O'ahu State Warriors",
                                "logo": "https://example.com/team1.png"
                            }
                        ]
                    }
                ],
                "matchups": [
                    {
                        "home_team": {"id": 3},
                        "away_team": {"id": 1},
                        "home_score": 139.7,
                        "away_score": 132.58,
                        "home_projected_score": 115.69,
                        "away_projected_score": 121.23,
                        "home_optimal_score": 159.3,
                        "away_optimal_score": 132.58
                    }
                ]
            },
            "season_context": {
                "running_totals": {
                    "3": {
                        "name": "They Stole Danny's Dimes",
                        "logo": "https://example.com/team3.png",
                        "division": "Adams",
                        "actual": 139.7,
                        "projected": 115.69,
                        "optimal": 159.3,
                        "efficiency": 87.7
                    },
                    "1": {
                        "name": "O'ahu State Warriors",
                        "logo": "https://example.com/team1.png",
                        "division": "Adams",
                        "actual": 132.58,
                        "projected": 121.23,
                        "optimal": 132.58,
                        "efficiency": 100.0
                    }
                }
            }
        }

        # Sample raw data without running totals
        self.sample_raw_data = {
            "league_id": 380491,
            "league_name": "Duke Football Invitational",
            "season": 2025,
            "week": 1,
            "report_date": "2025-09-17T15:32:03.569584",
            "divisions": [
                {
                    "name": "Adams",
                    "teams": [
                        {
                            "id": 3,
                            "name": "They Stole Danny's Dimes",
                            "logo": "https://example.com/team3.png",
                            "division": "Adams"
                        },
                        {
                            "id": 1,
                            "name": "O'ahu State Warriors",
                            "logo": "https://example.com/team1.png",
                            "division": "Adams"
                        }
                    ]
                }
            ],
            "matchups": [
                {
                    "home_team": {"id": 3},
                    "away_team": {"id": 1},
                    "home_score": 139.7,
                    "away_score": 132.58,
                    "home_projected_score": 115.69,
                    "away_projected_score": 121.23,
                    "home_optimal_score": 159.3,
                    "away_optimal_score": 132.58
                }
            ]
        }

        # Sample team logos dict
        self.team_logos = {
            "They Stole Danny's Dimes": "https://example.com/team3.png",
            "O'ahu State Warriors": "https://example.com/team1.png"
        }

    def test_prepare_running_totals_data_enhanced(self):
        """Test prepare running totals data with enhanced data structure."""
        result = self.generator._prepare_running_totals_data(
            self.sample_enhanced_data,
            self.team_logos
        )

        # Should return list of tuples (team_id, team_data)
        assert isinstance(result, list)
        assert len(result) == 2

        # Should be sorted by efficiency (highest first)
        assert result[0][1]['efficiency'] == 100.0  # O'ahu State Warriors
        assert result[1][1]['efficiency'] == 87.7   # They Stole Danny's Dimes

        # Check first team data structure
        team_id, team_data = result[0]
        assert team_id == "1"
        assert team_data['name'] == "O'ahu State Warriors"
        assert team_data['actual'] == 132.58
        assert team_data['projected'] == 121.23
        assert team_data['optimal'] == 132.58
        assert team_data['efficiency'] == 100.0

    def test_prepare_running_totals_data_raw_fallback(self):
        """Test prepare running totals data falls back to calculation for raw data."""
        result = self.generator._prepare_running_totals_data(
            self.sample_raw_data,
            self.team_logos
        )

        # Should return calculated data
        assert isinstance(result, list)
        assert len(result) == 2

        # Should still be sorted by efficiency
        efficiencies = [item[1]['efficiency'] for item in result]
        assert efficiencies == sorted(efficiencies, reverse=True)

    def test_calculate_current_week_totals_success(self):
        """Test calculation of current week totals from raw data."""
        result = self.generator._calculate_current_week_totals(self.sample_raw_data)

        # Should return list of tuples
        assert isinstance(result, list)
        assert len(result) == 2

        # Convert to dict for easier testing
        result_dict = {item[0]: item[1] for item in result}

        # Check team 3 calculations
        team_3_data = result_dict[3]
        assert team_3_data['name'] == "They Stole Danny's Dimes"
        assert team_3_data['logo'] == "https://example.com/team3.png"
        assert team_3_data['actual'] == 139.7
        assert team_3_data['projected'] == 115.69
        assert team_3_data['optimal'] == 159.3
        # Efficiency: (139.7 / 159.3) * 100 ≈ 87.7%
        assert abs(team_3_data['efficiency'] - 87.69617074701819) < 0.01

        # Check team 1 calculations
        team_1_data = result_dict[1]
        assert team_1_data['name'] == "O'ahu State Warriors"
        assert team_1_data['actual'] == 132.58
        assert team_1_data['optimal'] == 132.58
        assert team_1_data['efficiency'] == 100.0

    def test_calculate_current_week_totals_zero_optimal(self):
        """Test calculation handles zero optimal scores."""
        modified_data = self.sample_raw_data.copy()
        modified_data['matchups'][0]['home_optimal_score'] = 0
        modified_data['matchups'][0]['away_optimal_score'] = 0

        result = self.generator._calculate_current_week_totals(modified_data)
        result_dict = {item[0]: item[1] for item in result}

        # Should handle zero optimal gracefully
        assert result_dict[3]['efficiency'] == 0.0
        assert result_dict[1]['efficiency'] == 0.0

    def test_calculate_current_week_totals_no_matchups(self):
        """Test calculation with no matchups."""
        modified_data = self.sample_raw_data.copy()
        modified_data['matchups'] = []

        result = self.generator._calculate_current_week_totals(modified_data)

        # Should return teams with zero scores
        assert len(result) == 2
        result_dict = {item[0]: item[1] for item in result}
        assert result_dict[3]['actual'] == 0.0
        assert result_dict[1]['actual'] == 0.0

    def test_calculate_current_week_totals_missing_team_in_matchup(self):
        """Test calculation with team in matchup but not in divisions."""
        modified_data = self.sample_raw_data.copy()
        # Add matchup with team not in divisions
        modified_data['matchups'].append({
            "home_team": {"id": 99},  # Team not in divisions
            "away_team": {"id": 3},
            "home_score": 100.0,
            "away_score": 90.0,
            "home_projected_score": 95.0,
            "away_projected_score": 85.0,
            "home_optimal_score": 105.0,
            "away_optimal_score": 95.0
        })

        result = self.generator._calculate_current_week_totals(modified_data)

        # Should only include teams from divisions
        team_ids = [item[0] for item in result]
        assert 99 not in team_ids
        assert 3 in team_ids
        assert 1 in team_ids

    def test_prepare_running_totals_data_sorting(self):
        """Test that running totals are sorted by efficiency (highest to lowest)."""
        # Create data with multiple teams with different efficiencies
        enhanced_data_multi_teams = {
            "season_context": {
                "running_totals": {
                    "1": {"name": "Team A", "efficiency": 95.0},
                    "2": {"name": "Team B", "efficiency": 85.0},
                    "3": {"name": "Team C", "efficiency": 100.0},
                    "4": {"name": "Team D", "efficiency": 90.0}
                }
            }
        }

        result = self.generator._prepare_running_totals_data(
            enhanced_data_multi_teams,
            {}
        )

        # Should be sorted by efficiency descending
        efficiencies = [item[1]['efficiency'] for item in result]
        assert efficiencies == [100.0, 95.0, 90.0, 85.0]

        # Verify team order
        team_names = [item[1]['name'] for item in result]
        assert team_names == ["Team C", "Team A", "Team D", "Team B"]

    def test_prepare_running_totals_data_error_handling(self):
        """Test error handling in running totals preparation."""
        # Test with data that has error in running totals
        error_data = {
            "season_context": {
                "running_totals": {
                    "error": "Some calculation error",
                    "1": {"name": "Valid Team", "efficiency": 85.0}
                }
            }
        }

        result = self.generator._prepare_running_totals_data(error_data, {})

        # Should skip error entries and include valid ones
        assert len(result) == 1
        assert result[0][1]['name'] == "Valid Team"

    def test_prepare_running_totals_data_empty_season_context(self):
        """Test handling of empty or missing season context."""
        empty_data = {"some_other_data": "value"}

        result = self.generator._prepare_running_totals_data(empty_data, self.team_logos)

        # Should fall back to calculation (which will return empty list for no valid data)
        assert isinstance(result, list)

    @patch('src.generators.templated_html_generator.TemplatedFantasyHTMLGenerator._calculate_current_week_totals')
    def test_prepare_running_totals_fallback_called(self, mock_calculate):
        """Test that fallback calculation is called when no running totals in enhanced data."""
        mock_calculate.return_value = [("1", {"efficiency": 100.0})]

        # Data without season_context
        raw_data = {"no_season_context": True}

        result = self.generator._prepare_running_totals_data(raw_data, {})

        # Should call the fallback method
        mock_calculate.assert_called_once_with(raw_data)
        assert len(result) == 1