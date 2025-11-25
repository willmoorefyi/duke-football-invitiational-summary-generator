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
        """Test extracting team standings from ESPN data."""
        week_data = [{
            'week': 1,
            'season': 2024,
            'divisions': [
                {
                    'name': 'East',
                    'teams': [
                        {
                            'id': 1, 'name': 'Team A', 'division': 'East', 'owner': 'Owner A',
                            'abbreviation': 'TA', 'logo': '',
                            # ESPN standings data
                            'wins': 1, 'losses': 0, 'ties': 0,
                            'points_for': 120.5, 'points_against': 95.0,
                            'standing': 1, 'playoff_pct': 100.0
                        },
                        {
                            'id': 2, 'name': 'Team B', 'division': 'East', 'owner': 'Owner B',
                            'abbreviation': 'TB', 'logo': '',
                            # ESPN standings data
                            'wins': 0, 'losses': 1, 'ties': 0,
                            'points_for': 95.0, 'points_against': 120.5,
                            'standing': 2, 'playoff_pct': 0.0
                        }
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

        # Team 1 standings extracted from ESPN data
        team_1 = standings[1]
        assert team_1['wins'] == 1
        assert team_1['losses'] == 0
        assert team_1['points_for'] == 120.5
        assert team_1['points_against'] == 95.0
        assert team_1['overall_rank'] == 1  # ESPN's standing

        # Team 2 standings extracted from ESPN data
        team_2 = standings[2]
        assert team_2['wins'] == 0
        assert team_2['losses'] == 1
        assert team_2['points_for'] == 95.0
        assert team_2['points_against'] == 120.5
        assert team_2['overall_rank'] == 2  # ESPN's standing

    def test_calculate_team_standings_multi_week(self):
        """Test extracting team standings from ESPN data (current week contains cumulative standings)."""
        week_data = [
            # Week 1 data (historical)
            {
                'week': 1,
                'divisions': [
                    {
                        'name': 'East',
                        'teams': [
                            {
                                'id': 1, 'name': 'Team A', 'division': 'East', 'owner': 'Owner A',
                                'abbreviation': 'TA', 'logo': '',
                                'wins': 1, 'losses': 0, 'ties': 0,
                                'points_for': 120.0, 'points_against': 95.0,
                                'standing': 1, 'playoff_pct': 100.0
                            },
                            {
                                'id': 2, 'name': 'Team B', 'division': 'East', 'owner': 'Owner B',
                                'abbreviation': 'TB', 'logo': '',
                                'wins': 0, 'losses': 1, 'ties': 0,
                                'points_for': 95.0, 'points_against': 120.0,
                                'standing': 2, 'playoff_pct': 0.0
                            }
                        ]
                    }
                ],
                'matchups': []
            },
            # Week 2 data (current week with cumulative ESPN standings)
            {
                'week': 2,
                'divisions': [
                    {
                        'name': 'East',
                        'teams': [
                            {
                                'id': 1, 'name': 'Team A', 'division': 'East', 'owner': 'Owner A',
                                'abbreviation': 'TA', 'logo': '',
                                # ESPN's cumulative standings after 2 weeks
                                'wins': 1, 'losses': 1, 'ties': 0,
                                'points_for': 225.0, 'points_against': 225.0,
                                'standing': 1, 'playoff_pct': 50.0
                            },
                            {
                                'id': 2, 'name': 'Team B', 'division': 'East', 'owner': 'Owner B',
                                'abbreviation': 'TB', 'logo': '',
                                # ESPN's cumulative standings after 2 weeks
                                'wins': 1, 'losses': 1, 'ties': 0,
                                'points_for': 225.0, 'points_against': 225.0,
                                'standing': 2, 'playoff_pct': 50.0
                            }
                        ]
                    }
                ],
                'matchups': []
            }
        ]

        standings = self.aggregate_stage._calculate_team_standings(week_data, 2)

        # Standings extracted from current week's ESPN data (which is cumulative)
        team_1 = standings[1]
        assert team_1['wins'] == 1
        assert team_1['losses'] == 1
        assert team_1['points_for'] == 225.0
        assert team_1['points_against'] == 225.0
        assert team_1['overall_rank'] == 1  # ESPN's standing

        team_2 = standings[2]
        assert team_2['wins'] == 1
        assert team_2['losses'] == 1
        assert team_2['points_for'] == 225.0
        assert team_2['points_against'] == 225.0
        assert team_2['overall_rank'] == 2  # ESPN's standing
        # Both have same points_for, so it goes to points_against (lower is better)
        # Both have same points_against, so original order maintained

    def test_calculate_team_standings_with_ties(self):
        """Test extracting team standings with tie games from ESPN data."""
        week_data = [{
            'week': 1,
            'divisions': [
                {
                    'name': 'East',
                    'teams': [
                        {
                            'id': 1, 'name': 'Team A', 'division': 'East', 'owner': 'Owner A',
                            'abbreviation': 'TA', 'logo': '',
                            # ESPN standings with tie
                            'wins': 0, 'losses': 0, 'ties': 1,
                            'points_for': 100.0, 'points_against': 100.0,
                            'standing': 1, 'playoff_pct': 50.0
                        },
                        {
                            'id': 2, 'name': 'Team B', 'division': 'East', 'owner': 'Owner B',
                            'abbreviation': 'TB', 'logo': '',
                            # ESPN standings with tie
                            'wins': 0, 'losses': 0, 'ties': 1,
                            'points_for': 100.0, 'points_against': 100.0,
                            'standing': 2, 'playoff_pct': 50.0
                        }
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

        # Standings extracted from ESPN data showing ties
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