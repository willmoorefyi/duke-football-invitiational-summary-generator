"""
Test suite for TemplatedFantasyHTMLGenerator multi-week functionality.

Tests the new functionality for handling historical data and rendering
weekly statistics across multiple weeks.
"""

import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal

from src.generators.templated_html_generator import TemplatedFantasyHTMLGenerator


class TestTemplatedHTMLGeneratorMultiWeek(unittest.TestCase):
    """Test multi-week functionality in TemplatedFantasyHTMLGenerator."""

    def setUp(self):
        """Set up test fixtures."""
        self.generator = TemplatedFantasyHTMLGenerator()

        # Sample current week data with all required fields
        self.current_week_data = {
            'week': 2,
            'season': 2025,
            'league_id': '380491',
            'league_name': 'Test Fantasy League',
            'report_date': '2025-09-18T12:00:00Z',
            'divisions': [
                {
                    'name': 'Test Division',
                    'teams': [
                        {
                            'id': 'team1',
                            'name': 'Team A',
                            'logo': 'http://example.com/teamA.png',
                            'overall_rank': 1,
                            'wins': 1,
                            'losses': 1,
                            'points_for': 216.3,
                            'points_against': 207.5
                        },
                        {
                            'id': 'team2',
                            'name': 'Team B',
                            'logo': 'http://example.com/teamB.png',
                            'overall_rank': 2,
                            'wins': 1,
                            'losses': 1,
                            'points_for': 207.5,
                            'points_against': 216.3
                        }
                    ]
                }
            ],
            'matchups': [
                {
                    'home_team': {'id': 'team1', 'name': 'Team A'},
                    'away_team': {'id': 'team2', 'name': 'Team B'},
                    'home_score': 105.8,
                    'away_score': 112.3,
                    'home_projected_score': 108.0,
                    'away_projected_score': 103.0,
                    'home_optimal_score': 120.0,
                    'away_optimal_score': 115.0,
                    'players': []
                }
            ],
            'awards': {}
        }

        # Sample enhanced data with multi-week statistics
        self.enhanced_data_multiweek = {
            'current_week': self.current_week_data,
            'season_context': {
                'weekly_statistics': {
                    'weeks': [
                        {
                            'week': 1,
                            'median': 102.85,
                            'average': 102.85,
                            'max': 110.5,
                            'min': 95.2,
                            'std_dev': 10.82,
                            'max_team_name': 'Team A',
                            'min_team_name': 'Team B',
                            'average_efficiency': 88.5
                        },
                        {
                            'week': 2,
                            'median': 109.05,
                            'average': 109.05,
                            'max': 112.3,
                            'min': 105.8,
                            'std_dev': 4.59,
                            'max_team_name': 'Team B',
                            'min_team_name': 'Team A',
                            'average_efficiency': 92.1
                        }
                    ]
                }
            }
        }

        # Sample raw data (no enhanced season context)
        self.raw_data_single_week = self.current_week_data

    def test_get_week_statistics_data_with_enhanced_data(self):
        """Test _get_week_statistics_data with enhanced multi-week data."""
        result = self.generator._get_week_statistics_data(
            self.enhanced_data_multiweek,
            self.current_week_data
        )

        # Should return current week statistics for backward compatibility
        assert result['median'] == 109.05
        assert result['average'] == 109.05
        assert result['max'] == 112.3
        assert result['min'] == 105.8
        assert result['max_team_name'] == 'Team B'
        assert result['min_team_name'] == 'Team A'
        assert result['average_efficiency'] == 92.1

        # Should include all weeks for template iteration
        assert 'all_weeks' in result
        assert len(result['all_weeks']) == 2

        # Verify week 1 data
        week1 = result['all_weeks'][0]
        assert week1['week'] == 1
        assert week1['max'] == 110.5
        assert week1['max_team_name'] == 'Team A'

        # Verify week 2 data
        week2 = result['all_weeks'][1]
        assert week2['week'] == 2
        assert week2['max'] == 112.3
        assert week2['max_team_name'] == 'Team B'

    def test_get_week_statistics_data_fallback_to_current_week(self):
        """Test _get_week_statistics_data falls back to current week calculation."""
        result = self.generator._get_week_statistics_data(
            self.raw_data_single_week,
            self.current_week_data
        )

        # Should calculate current week statistics
        assert 'median' in result
        assert 'average' in result
        assert 'max' in result
        assert 'min' in result

        # Should wrap single week in all_weeks array
        assert 'all_weeks' in result
        assert len(result['all_weeks']) == 1
        assert result['all_weeks'][0]['median'] == result['median']

    def test_get_week_statistics_data_current_week_not_in_enhanced_data(self):
        """Test when current week is not found in pre-calculated enhanced data."""
        # Create enhanced data that doesn't include current week (week 2)
        enhanced_data_missing_current = {
            'current_week': self.current_week_data,
            'season_context': {
                'weekly_statistics': {
                    'weeks': [
                        {
                            'week': 1,
                            'median': 102.85,
                            'average': 102.85,
                            'max': 110.5,
                            'min': 95.2,
                            'std_dev': 10.82,
                            'max_team_name': 'Team A',
                            'min_team_name': 'Team B',
                            'average_efficiency': 88.5
                        }
                        # Week 2 is missing
                    ]
                }
            }
        }

        result = self.generator._get_week_statistics_data(
            enhanced_data_missing_current,
            self.current_week_data
        )

        # Should fall back to calculating current week statistics
        # and still provide all weeks from enhanced data
        assert 'median' in result
        assert 'all_weeks' in result
        assert len(result['all_weeks']) == 1  # Only week 1 from enhanced data

    def test_get_week_statistics_data_empty_enhanced_context(self):
        """Test _get_week_statistics_data with malformed enhanced data."""
        # Enhanced data with empty weekly_statistics
        enhanced_data_empty = {
            'current_week': self.current_week_data,
            'season_context': {
                'weekly_statistics': {}  # Missing 'weeks' key
            }
        }

        result = self.generator._get_week_statistics_data(
            enhanced_data_empty,
            self.current_week_data
        )

        # Should fall back to current week calculation
        assert 'all_weeks' in result
        assert len(result['all_weeks']) == 1

    def test_calculate_week_statistics_type_conversion(self):
        """Test that _calculate_week_statistics properly converts types."""
        # Create data with potential Decimal/string values
        test_data = {
            'matchups': [
                {
                    'home_team': {'name': 'Team A'},
                    'away_team': {'name': 'Team B'},
                    'home_score': 105.8,  # Could be Decimal from DynamoDB
                    'away_score': 112.3,
                    'home_optimal_score': 120.0,
                    'away_optimal_score': 115.0
                }
            ]
        }

        result = self.generator._calculate_week_statistics(test_data)

        # All numeric values should be float type
        assert isinstance(result['median'], float)
        assert isinstance(result['average'], float)
        assert isinstance(result['max'], float)
        assert isinstance(result['min'], float)
        assert isinstance(result['std_dev'], float)
        assert isinstance(result['average_efficiency'], float)

        # String values should remain strings
        assert isinstance(result['max_team_name'], str)
        assert isinstance(result['min_team_name'], str)

    def test_template_variables_include_all_weeks_stats(self):
        """Test that template variables include all_weeks_stats for multi-week rendering."""
        template_vars = self.generator._prepare_template_variables(self.enhanced_data_multiweek)

        # Should include all_weeks_stats for template iteration
        assert 'all_weeks_stats' in template_vars
        assert len(template_vars['all_weeks_stats']) == 2

        # Verify week data structure
        week1 = template_vars['all_weeks_stats'][0]
        assert week1['week'] == 1
        assert week1['max_team_name'] == 'Team A'

        week2 = template_vars['all_weeks_stats'][1]
        assert week2['week'] == 2
        assert week2['max_team_name'] == 'Team B'

    def test_template_variables_fallback_single_week(self):
        """Test template variables fallback for single week data."""
        template_vars = self.generator._prepare_template_variables(self.raw_data_single_week)

        # Should still include all_weeks_stats with single week
        assert 'all_weeks_stats' in template_vars
        assert len(template_vars['all_weeks_stats']) == 1

    def test_get_week_statistics_data_robust_fallback(self):
        """Test that _get_week_statistics_data is robust to data variations."""
        # Test with minimal data structure
        minimal_data = {
            'matchups': [
                {
                    'home_team': {'name': 'Team A'},
                    'away_team': {'name': 'Team B'},
                    'home_score': 100.0,
                    'away_score': 95.0,
                    'home_optimal_score': 110.0,
                    'away_optimal_score': 105.0
                }
            ]
        }

        result = self.generator._get_week_statistics_data(minimal_data, minimal_data)

        # Should return valid structure even with minimal data
        assert 'all_weeks' in result
        assert len(result['all_weeks']) >= 1

    def test_decimal_to_float_conversion_in_enhanced_data(self):
        """Test that enhanced data with Decimal values is properly handled."""
        # Create enhanced data with Decimal values (as would come from DynamoDB)
        enhanced_data_with_decimals = {
            'current_week': self.current_week_data,
            'season_context': {
                'weekly_statistics': {
                    'weeks': [
                        {
                            'week': 1,
                            'median': Decimal('102.85'),
                            'average': Decimal('102.85'),
                            'max': Decimal('110.5'),
                            'min': Decimal('95.2'),
                            'std_dev': Decimal('10.82'),
                            'max_team_name': 'Team A',
                            'min_team_name': 'Team B',
                            'average_efficiency': Decimal('88.5')
                        }
                    ]
                }
            }
        }

        result = self.generator._get_week_statistics_data(
            enhanced_data_with_decimals,
            self.current_week_data
        )

        # Should convert Decimal values to float for template compatibility
        week1_stats = result['all_weeks'][0]
        assert isinstance(week1_stats['median'], (float, Decimal))
        assert isinstance(week1_stats['average'], (float, Decimal))
        assert isinstance(week1_stats['max'], (float, Decimal))

    def test_empty_matchups_handling_in_statistics_calculation(self):
        """Test handling of empty matchups in week statistics calculation."""
        empty_data = {'matchups': []}

        result = self.generator._calculate_week_statistics(empty_data)

        # Should return proper default structure with all_weeks
        assert result['median'] == 0.0
        assert result['average'] == 0.0
        assert result['max'] == 0.0
        assert result['min'] == 0.0
        assert result['average_efficiency'] == 0.0
        assert 'all_weeks' in result
        assert len(result['all_weeks']) == 1

    def test_integration_prepare_template_variables_multiweek(self):
        """Integration test for complete template variable preparation with multi-week data."""
        # Mock the Jinja2 environment setup
        with patch.object(self.generator, 'env'):
            template_vars = self.generator._prepare_template_variables(self.enhanced_data_multiweek)

            # Verify all required template variables are present
            required_vars = [
                'league_name', 'week', 'season', 'report_date',
                'team_logos', 'all_teams_sorted', 'week_stats',
                'all_weeks_stats', 'week_team_scores', 'scoring_leaders_data',
                'player_awards', 'team_awards', 'collapse_awards',
                'matchups_sorted'
            ]

            for var in required_vars:
                assert var in template_vars, f"Missing template variable: {var}"

            # Verify multi-week specific data
            assert len(template_vars['all_weeks_stats']) == 2
            assert template_vars['all_weeks_stats'][0]['week'] == 1
            assert template_vars['all_weeks_stats'][1]['week'] == 2


if __name__ == '__main__':
    unittest.main()