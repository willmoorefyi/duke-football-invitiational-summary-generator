import pytest
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.generators.templated_html_generator import TemplatedFantasyHTMLGenerator


class TestTemplatedHTMLGeneratorDivisionStrength:
    """Test suite for division strength functionality in HTML generator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TemplatedFantasyHTMLGenerator()

    def test_prepare_division_strength_data_success(self):
        """Test successful preparation of division strength data."""
        # Enhanced data structure with division strength information
        data = {
            'season_context': {
                'division_strength': {
                    'divisions': [
                        {
                            'name': 'Adams',
                            'rank': 1,
                            'wins': 8,
                            'losses': 2,
                            'points_for': 1250.5,
                            'points_against': 1100.2
                        },
                        {
                            'name': 'Smythe',
                            'rank': 2,
                            'wins': 6,
                            'losses': 4,
                            'points_for': 1180.8,
                            'points_against': 1120.5
                        },
                        {
                            'name': 'Jones',
                            'rank': 3,
                            'wins': 3,
                            'losses': 7,
                            'points_for': 1050.0,
                            'points_against': 1200.3
                        }
                    ],
                    'ranking_criteria': 'Wins (desc), Losses (asc), Points For (desc), Points Against (desc)'
                }
            }
        }

        team_logos = {}

        result = self.generator._prepare_division_strength_data(data, team_logos)

        assert 'divisions' in result
        assert 'ranking_criteria' in result
        assert len(result['divisions']) == 3

        # Verify first division (Adams)
        adams = result['divisions'][0]
        assert adams['name'] == 'Adams'
        assert adams['rank'] == 1
        assert adams['wins'] == 8
        assert adams['losses'] == 2
        assert adams['points_for'] == 1250.5
        assert adams['points_against'] == 1100.2

        # Verify ranking criteria is passed through
        assert result['ranking_criteria'] == 'Wins (desc), Losses (asc), Points For (desc), Points Against (desc)'

    def test_prepare_division_strength_data_no_season_context(self):
        """Test division strength preparation when season_context is missing."""
        data = {
            'current_week': {
                'week': 5,
                'league_name': 'Test League'
            }
        }

        team_logos = {}

        result = self.generator._prepare_division_strength_data(data, team_logos)

        assert result['divisions'] == []
        assert result['ranking_criteria'] == 'No data available'

    def test_prepare_division_strength_data_no_division_strength(self):
        """Test division strength preparation when division_strength is missing."""
        data = {
            'season_context': {
                'team_standings': {},
                'running_totals': {}
                # Missing division_strength
            }
        }

        team_logos = {}

        result = self.generator._prepare_division_strength_data(data, team_logos)

        assert result['divisions'] == []
        assert result['ranking_criteria'] == 'No data available'

    def test_prepare_division_strength_data_empty_divisions(self):
        """Test division strength preparation with empty divisions list."""
        data = {
            'season_context': {
                'division_strength': {
                    'divisions': [],
                    'ranking_criteria': 'Wins (desc), Losses (asc), Points For (desc), Points Against (desc)'
                }
            }
        }

        team_logos = {}

        result = self.generator._prepare_division_strength_data(data, team_logos)

        assert result['divisions'] == []
        assert result['ranking_criteria'] == 'No data available'

    def test_prepare_division_strength_data_point_rounding(self):
        """Test that points are properly rounded to 1 decimal place."""
        data = {
            'season_context': {
                'division_strength': {
                    'divisions': [
                        {
                            'name': 'Test Division',
                            'rank': 1,
                            'wins': 5,
                            'losses': 1,
                            'points_for': 1234.567,  # Should round to 1234.6
                            'points_against': 987.123  # Should round to 987.1
                        }
                    ],
                    'ranking_criteria': 'Test criteria'
                }
            }
        }

        team_logos = {}

        result = self.generator._prepare_division_strength_data(data, team_logos)

        division = result['divisions'][0]
        assert division['points_for'] == 1234.6
        assert division['points_against'] == 987.1

    def test_prepare_division_strength_data_exception_handling(self):
        """Test division strength preparation handles exceptions gracefully."""
        # Create data that will cause an exception
        data = None  # This will cause an exception

        team_logos = {}

        result = self.generator._prepare_division_strength_data(data, team_logos)

        assert result['divisions'] == []
        assert 'Error:' in result['ranking_criteria']

    def test_prepare_division_strength_data_complete_structure(self):
        """Test that all expected fields are present in the result."""
        data = {
            'season_context': {
                'division_strength': {
                    'divisions': [
                        {
                            'name': 'Division Alpha',
                            'rank': 2,
                            'wins': 7,
                            'losses': 3,
                            'points_for': 1345.89,
                            'points_against': 1123.45,
                            'teams': ['Team A', 'Team B']
                        }
                    ],
                    'ranking_criteria': 'Custom ranking criteria'
                }
            }
        }

        team_logos = {
            'Team A': 'https://example.com/team_a.png',
            'Team B': 'https://example.com/team_b.png'
        }

        result = self.generator._prepare_division_strength_data(data, team_logos)

        # Verify result structure
        assert isinstance(result, dict)
        assert 'divisions' in result
        assert 'ranking_criteria' in result

        # Verify division structure
        division = result['divisions'][0]
        required_fields = ['name', 'rank', 'wins', 'losses', 'points_for', 'points_against', 'teams']
        for field in required_fields:
            assert field in division

        # Verify data types
        assert isinstance(division['name'], str)
        assert isinstance(division['rank'], (int, float))
        assert isinstance(division['wins'], (int, float))
        assert isinstance(division['losses'], (int, float))
        assert isinstance(division['points_for'], (int, float))
        assert isinstance(division['points_against'], (int, float))
        assert isinstance(division['teams'], list)

        # Verify team structure with logos
        assert len(division['teams']) == 2
        team_a = division['teams'][0]
        assert team_a['name'] == 'Team A'
        assert team_a['logo'] == 'https://example.com/team_a.png'

        team_b = division['teams'][1]
        assert team_b['name'] == 'Team B'
        assert team_b['logo'] == 'https://example.com/team_b.png'

    def test_prepare_template_variables_includes_division_strength(self):
        """Test that division strength data is included in template variables."""
        # Create enhanced data structure
        data = {
            'current_week': {
                'league_name': 'Test League',
                'week': 5,
                'season': 2025,
                'report_date': '2025-09-17T15:32:03.569584',
                'divisions': [
                    {
                        'name': 'Adams',
                        'teams': [
                            {
                                'id': 1,
                                'name': 'Test Team',
                                'abbreviation': 'TT',
                                'owner': 'Test Owner',
                                'division': 'Adams'
                            }
                        ]
                    }
                ],
                'matchups': [],
                'weekly_awards': {}
            },
            'season_context': {
                'team_standings': {},
                'division_strength': {
                    'divisions': [
                        {
                            'name': 'Adams',
                            'rank': 1,
                            'wins': 5,
                            'losses': 2,
                            'points_for': 1200.0,
                            'points_against': 1000.0
                        }
                    ],
                    'ranking_criteria': 'Test criteria'
                }
            }
        }

        # Mock the _get_team_standings_from_data method to avoid issues
        with patch.object(self.generator, '_get_team_standings_from_data', return_value={}):
            template_vars = self.generator._prepare_template_variables(data)

        # Verify division strength data is included
        assert 'division_strength_divisions' in template_vars
        assert 'division_strength_criteria' in template_vars

        # Verify the data structure
        assert len(template_vars['division_strength_divisions']) == 1
        division = template_vars['division_strength_divisions'][0]
        assert division['name'] == 'Adams'
        assert division['rank'] == 1
        assert division['wins'] == 5
        assert division['losses'] == 2

        assert template_vars['division_strength_criteria'] == 'Test criteria'

    def test_prepare_template_variables_division_strength_fallback(self):
        """Test template variables when division strength data is not available."""
        # Create data structure without division strength
        data = {
            'current_week': {
                'league_name': 'Test League',
                'week': 5,
                'season': 2025,
                'report_date': '2025-09-17T15:32:03.569584',
                'divisions': [
                    {
                        'name': 'Adams',
                        'teams': [
                            {
                                'id': 1,
                                'name': 'Test Team',
                                'abbreviation': 'TT',
                                'owner': 'Test Owner',
                                'division': 'Adams'
                            }
                        ]
                    }
                ],
                'matchups': [],
                'weekly_awards': {}
            }
            # No season_context
        }

        # Mock the _get_team_standings_from_data method
        with patch.object(self.generator, '_get_team_standings_from_data', return_value={}):
            template_vars = self.generator._prepare_template_variables(data)

        # Verify division strength data defaults are present
        assert 'division_strength_divisions' in template_vars
        assert 'division_strength_criteria' in template_vars

        # Should be empty/default values
        assert template_vars['division_strength_divisions'] == []
        assert template_vars['division_strength_criteria'] == 'No data available'