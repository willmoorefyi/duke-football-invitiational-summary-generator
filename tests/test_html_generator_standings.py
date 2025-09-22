import pytest
from src.generators.templated_html_generator import TemplatedFantasyHTMLGenerator


class TestHTMLGeneratorStandings:
    """Test HTML generator's integration with computed standings."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TemplatedFantasyHTMLGenerator()

    def test_get_team_standings_from_enhanced_data(self):
        """Test extraction of team standings from enhanced data structure."""
        # Enhanced data structure with computed standings
        enhanced_data = {
            'current_week': {
                'week': 2,
                'season': 2024,
                'divisions': [
                    {
                        'name': 'East',
                        'teams': [
                            {'id': 1, 'name': 'Team A', 'owner': 'Owner A'},
                            {'id': 2, 'name': 'Team B', 'owner': 'Owner B'}
                        ]
                    }
                ]
            },
            'season_context': {
                'team_standings': {
                    '1': {
                        'id': 1, 'name': 'Team A', 'wins': 2, 'losses': 0,
                        'points_for': 250.5, 'points_against': 180.0,
                        'overall_rank': 1, 'division_rank': 1
                    },
                    '2': {
                        'id': 2, 'name': 'Team B', 'wins': 1, 'losses': 1,
                        'points_for': 200.0, 'points_against': 220.5,
                        'overall_rank': 2, 'division_rank': 2
                    }
                }
            }
        }

        standings = self.generator._get_team_standings_from_data(enhanced_data)

        assert '1' in standings
        assert standings['1']['wins'] == 2
        assert standings['1']['overall_rank'] == 1

        assert '2' in standings
        assert standings['2']['wins'] == 1
        assert standings['2']['overall_rank'] == 2

    def test_get_team_standings_from_raw_data(self):
        """Test fallback behavior with raw data (no computed standings)."""
        # Raw data structure without season_context
        raw_data = {
            'week': 1,
            'season': 2024,
            'divisions': [
                {
                    'name': 'East',
                    'teams': [
                        {'id': 1, 'name': 'Team A', 'owner': 'Owner A'},
                        {'id': 2, 'name': 'Team B', 'owner': 'Owner B'}
                    ]
                }
            ]
        }

        standings = self.generator._get_team_standings_from_data(raw_data)

        # Should return empty dict for raw data
        assert len(standings) == 0

    def test_prepare_template_variables_with_computed_standings(self):
        """Test that template variables include computed standings merged with team data."""
        # Enhanced data structure
        data = {
            'current_week': {
                'week': 2,
                'season': 2024,
                'league_name': 'Test League',
                'league_id': 12345,
                'report_date': '2024-09-15T12:00:00Z',
                'divisions': [
                    {
                        'name': 'East',
                        'teams': [
                            {
                                'id': 1, 'name': 'Team A', 'owner': 'Owner A',
                                'abbreviation': 'TA', 'logo': 'logo1.png'
                            },
                            {
                                'id': 2, 'name': 'Team B', 'owner': 'Owner B',
                                'abbreviation': 'TB', 'logo': 'logo2.png'
                            }
                        ]
                    }
                ],
                'matchups': []
            },
            'season_context': {
                'team_standings': {
                    '1': {
                        'id': 1, 'wins': 2, 'losses': 0, 'ties': 0,
                        'points_for': 250.5, 'points_against': 180.0,
                        'overall_rank': 1, 'division_rank': 1
                    },
                    '2': {
                        'id': 2, 'wins': 0, 'losses': 2, 'ties': 0,
                        'points_for': 180.0, 'points_against': 250.5,
                        'overall_rank': 2, 'division_rank': 2
                    }
                },
                'weekly_statistics': {
                    'weeks': [
                        {
                            'week': 2, 'median': 100.0, 'average': 105.0,
                            'max': 125.0, 'min': 85.0, 'std_dev': 15.0,
                            'average_efficiency': 85.0
                        }
                    ]
                },
                'running_totals': {}
            }
        }

        template_vars = self.generator._prepare_template_variables(data)

        # Check that all teams have computed standings merged in
        all_teams = template_vars['all_teams_sorted']
        assert len(all_teams) == 2

        # Team A (should be first due to rank 1)
        team_a = all_teams[0]
        assert team_a['name'] == 'Team A'
        assert team_a['wins'] == 2
        assert team_a['losses'] == 0
        assert team_a['points_for'] == 250.5
        assert team_a['overall_rank'] == 1

        # Team B (should be second due to rank 2)
        team_b = all_teams[1]
        assert team_b['name'] == 'Team B'
        assert team_b['wins'] == 0
        assert team_b['losses'] == 2
        assert team_b['points_for'] == 180.0
        assert team_b['overall_rank'] == 2


if __name__ == "__main__":
    pytest.main([__file__])