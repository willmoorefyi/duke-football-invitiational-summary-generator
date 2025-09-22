import pytest
from unittest.mock import Mock, patch
from src.pipeline.aggregate_stage import AggregateStage


class TestStandingsCalculation:
    """Test suite for the new standings calculation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.aggregate_stage = AggregateStage(league_id=12345, dry_run=True)
        self.aggregate_stage.logger = Mock()  # Mock logger to avoid logging during tests

    def test_rank_teams_by_performance_basic_sorting(self):
        """Test basic team ranking by wins, losses, points."""
        teams = [
            {
                'id': 1, 'name': 'Team A', 'wins': 2, 'losses': 1,
                'points_for': 200.0, 'points_against': 150.0
            },
            {
                'id': 2, 'name': 'Team B', 'wins': 3, 'losses': 0,
                'points_for': 180.0, 'points_against': 120.0
            },
            {
                'id': 3, 'name': 'Team C', 'wins': 1, 'losses': 2,
                'points_for': 160.0, 'points_against': 180.0
            }
        ]

        ranked_teams = self.aggregate_stage._rank_teams_by_performance(teams)

        # Team B should be first (3 wins, 0 losses)
        assert ranked_teams[0]['name'] == 'Team B'
        assert ranked_teams[0]['wins'] == 3

        # Team A should be second (2 wins, 1 loss)
        assert ranked_teams[1]['name'] == 'Team A'
        assert ranked_teams[1]['wins'] == 2

        # Team C should be third (1 win, 2 losses)
        assert ranked_teams[2]['name'] == 'Team C'
        assert ranked_teams[2]['wins'] == 1

    def test_rank_teams_by_performance_tiebreaker_rules(self):
        """Test tiebreaker rules: wins > losses > points_for > points_against."""
        teams = [
            {
                'id': 1, 'name': 'Team A', 'wins': 2, 'losses': 1,
                'points_for': 200.0, 'points_against': 150.0
            },
            {
                'id': 2, 'name': 'Team B', 'wins': 2, 'losses': 1,
                'points_for': 220.0, 'points_against': 160.0  # More points for
            },
            {
                'id': 3, 'name': 'Team C', 'wins': 2, 'losses': 1,
                'points_for': 200.0, 'points_against': 140.0  # Fewer points against
            }
        ]

        ranked_teams = self.aggregate_stage._rank_teams_by_performance(teams)

        # Team B should be first (same record, but more points for)
        assert ranked_teams[0]['name'] == 'Team B'
        assert ranked_teams[0]['points_for'] == 220.0

        # Team C should be second (same record and points for as A, but fewer points against)
        assert ranked_teams[1]['name'] == 'Team C'
        assert ranked_teams[1]['points_against'] == 140.0

        # Team A should be third
        assert ranked_teams[2]['name'] == 'Team A'

    def test_calculate_team_standings_single_week(self):
        """Test calculating team standings from a single week of matchups."""
        week_data = [{
            'week': 1,
            'season': 2024,
            'divisions': [
                {
                    'name': 'East',
                    'teams': [
                        {'id': 1, 'name': 'Team A', 'division': 'East', 'owner': 'Owner A', 'abbreviation': 'TA', 'logo': ''},
                        {'id': 2, 'name': 'Team B', 'division': 'East', 'owner': 'Owner B', 'abbreviation': 'TB', 'logo': ''}
                    ]
                }
            ],
            'matchups': [
                {
                    'home_team': {'id': 1}, 'away_team': {'id': 2},
                    'home_score': 120.5, 'away_score': 95.0
                }
            ]
        }]

        standings = self.aggregate_stage._calculate_team_standings(week_data, 1)

        # Team 1 should have 1 win, 0 losses
        team_1 = standings[1]
        assert team_1['wins'] == 1
        assert team_1['losses'] == 0
        assert team_1['points_for'] == 120.5
        assert team_1['points_against'] == 95.0
        assert team_1['overall_rank'] == 1

        # Team 2 should have 0 wins, 1 loss
        team_2 = standings[2]
        assert team_2['wins'] == 0
        assert team_2['losses'] == 1
        assert team_2['points_for'] == 95.0
        assert team_2['points_against'] == 120.5
        assert team_2['overall_rank'] == 2

    def test_calculate_team_standings_multi_week(self):
        """Test calculating team standings across multiple weeks."""
        week_data = [
            # Week 1 data
            {
                'week': 1,
                'divisions': [
                    {
                        'name': 'East',
                        'teams': [
                            {'id': 1, 'name': 'Team A', 'division': 'East', 'owner': 'Owner A', 'abbreviation': 'TA', 'logo': ''},
                            {'id': 2, 'name': 'Team B', 'division': 'East', 'owner': 'Owner B', 'abbreviation': 'TB', 'logo': ''}
                        ]
                    }
                ],
                'matchups': [
                    {
                        'home_team': {'id': 1}, 'away_team': {'id': 2},
                        'home_score': 120.0, 'away_score': 95.0
                    }
                ]
            },
            # Week 2 data (current week)
            {
                'week': 2,
                'divisions': [
                    {
                        'name': 'East',
                        'teams': [
                            {'id': 1, 'name': 'Team A', 'division': 'East', 'owner': 'Owner A', 'abbreviation': 'TA', 'logo': ''},
                            {'id': 2, 'name': 'Team B', 'division': 'East', 'owner': 'Owner B', 'abbreviation': 'TB', 'logo': ''}
                        ]
                    }
                ],
                'matchups': [
                    {
                        'home_team': {'id': 2}, 'away_team': {'id': 1},
                        'home_score': 130.0, 'away_score': 105.0
                    }
                ]
            }
        ]

        standings = self.aggregate_stage._calculate_team_standings(week_data, 2)

        # After 2 weeks, both teams should have 1-1 records
        team_1 = standings[1]
        assert team_1['wins'] == 1
        assert team_1['losses'] == 1
        assert team_1['points_for'] == 225.0  # 120 + 105
        assert team_1['points_against'] == 225.0  # 95 + 130

        team_2 = standings[2]
        assert team_2['wins'] == 1
        assert team_2['losses'] == 1
        assert team_2['points_for'] == 225.0  # 95 + 130
        assert team_2['points_against'] == 225.0  # 120 + 105

        # Team 2 should rank higher due to better points differential (same record)
        # Team 2: +0 differential, Team 1: +0 differential, so it goes to points_for tiebreaker
        # Both have same points_for, so it goes to points_against (lower is better)
        # Both have same points_against, so original order maintained

    def test_calculate_team_standings_with_ties(self):
        """Test calculating team standings with tie games."""
        week_data = [{
            'week': 1,
            'divisions': [
                {
                    'name': 'East',
                    'teams': [
                        {'id': 1, 'name': 'Team A', 'division': 'East', 'owner': 'Owner A', 'abbreviation': 'TA', 'logo': ''},
                        {'id': 2, 'name': 'Team B', 'division': 'East', 'owner': 'Owner B', 'abbreviation': 'TB', 'logo': ''}
                    ]
                }
            ],
            'matchups': [
                {
                    'home_team': {'id': 1}, 'away_team': {'id': 2},
                    'home_score': 100.0, 'away_score': 100.0  # Tie game
                }
            ]
        }]

        standings = self.aggregate_stage._calculate_team_standings(week_data, 1)

        # Both teams should have 0 wins, 0 losses, 1 tie
        team_1 = standings[1]
        assert team_1['wins'] == 0
        assert team_1['losses'] == 0
        assert team_1['ties'] == 1
        assert team_1['points_for'] == 100.0
        assert team_1['points_against'] == 100.0

        team_2 = standings[2]
        assert team_2['wins'] == 0
        assert team_2['losses'] == 0
        assert team_2['ties'] == 1
        assert team_2['points_for'] == 100.0
        assert team_2['points_against'] == 100.0


if __name__ == "__main__":
    pytest.main([__file__])