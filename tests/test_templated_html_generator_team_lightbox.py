"""Tests for team lightbox functionality in TemplatedFantasyHTMLGenerator."""

import pytest
from unittest.mock import Mock, patch
from src.generators.templated_html_generator import TemplatedFantasyHTMLGenerator


class TestTeamLightboxDataPreparation:
    """Test team lightbox data preparation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TemplatedFantasyHTMLGenerator()

        # Sample enhanced data structure with team standings
        self.sample_enhanced_data = {
            'current_week_data': {
                'divisions': [
                    {
                        'name': 'Division A',
                        'teams': [
                            {
                                'id': '1',
                                'name': 'Team Alpha',
                                'owner': 'Owner A',
                                'division': 'Division A',
                                'logo': 'https://example.com/alpha.png'
                            },
                            {
                                'id': '2',
                                'name': 'Team Beta',
                                'owner': 'Owner B',
                                'division': 'Division A',
                                'logo': 'https://example.com/beta.png'
                            }
                        ]
                    }
                ]
            },
            'season_context': {
                'team_standings': {
                    '1': {
                        'wins': 3,
                        'losses': 1,
                        'ties': 0,
                        'points_for': 450.5,
                        'points_against': 380.2,
                        'overall_rank': 1,
                        'division_rank': 1
                    },
                    '2': {
                        'wins': 2,
                        'losses': 2,
                        'ties': 0,
                        'points_for': 420.8,
                        'points_against': 410.5,
                        'overall_rank': 2,
                        'division_rank': 2
                    }
                }
            }
        }

    def test_prepare_team_lightbox_data_basic_structure(self):
        """Test basic structure and content of team lightbox data."""
        # Mock the weekly results calculation method
        team_logos = {'Team Alpha': 'https://example.com/alpha.png', 'Team Beta': 'https://example.com/beta.png'}
        with patch.object(self.generator, '_calculate_team_weekly_results', return_value={'1': [], '2': []}):
            result = self.generator._prepare_team_lightbox_data(self.sample_enhanced_data, team_logos)

        # Verify basic structure
        assert isinstance(result, dict)
        assert '1' in result
        assert '2' in result

        # Verify team 1 data structure
        team1_data = result['1']
        assert team1_data['name'] == 'Team Alpha'
        assert team1_data['owner'] == 'Owner A'
        assert team1_data['division'] == 'Division A'
        assert team1_data['logo'] == 'https://example.com/alpha.png'

        # Verify theme colors are included
        assert 'themeColors' in team1_data
        assert isinstance(team1_data['themeColors'], (list, tuple))
        assert len(team1_data['themeColors']) == 2

        # Verify season stats structure
        season_stats = team1_data['seasonStats']
        assert season_stats['wins'] == 3
        assert season_stats['losses'] == 1
        assert season_stats['ties'] == 0
        assert season_stats['rank'] == 1
        assert season_stats['pointsFor'] == 450.5
        assert season_stats['pointsAgainst'] == 380.2

    def test_prepare_team_lightbox_data_missing_standings(self):
        """Test lightbox data preparation when team standings are missing."""
        # Remove season context to simulate missing standings
        data_without_standings = {
            'current_week_data': {
                'divisions': [
                    {
                        'name': 'Division A',
                        'teams': [
                            {
                                'id': '1',
                                'name': 'Team Alpha',
                                'owner': 'Owner A',
                                'division': 'Division A',
                                'logo': 'https://example.com/alpha.png'
                            }
                        ]
                    }
                ]
            }
        }

        # Mock the weekly results calculation method
        team_logos = {'Team Alpha': 'https://example.com/alpha.png'}
        with patch.object(self.generator, '_calculate_team_weekly_results', return_value={'1': []}):
            result = self.generator._prepare_team_lightbox_data(data_without_standings, team_logos)

        # Verify team data exists but with default stats
        assert '1' in result
        team1_data = result['1']
        assert team1_data['name'] == 'Team Alpha'

        # Verify default season stats when standings missing
        season_stats = team1_data['seasonStats']
        assert season_stats['wins'] == 0
        assert season_stats['losses'] == 0
        assert season_stats['ties'] == 0
        assert season_stats['rank'] == 0
        assert season_stats['pointsFor'] == 0
        assert season_stats['pointsAgainst'] == 0


class TestTeamWeeklyResultsCalculation:
    """Test team weekly results calculation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TemplatedFantasyHTMLGenerator()

        # Sample teams data
        self.sample_teams = {
            '1': {
                'id': '1',
                'name': 'Team Alpha',
                'owner': 'Owner A',
                'division': 'Division A',
                'logo': 'https://example.com/alpha.png'
            },
            '2': {
                'id': '2',
                'name': 'Team Beta',
                'owner': 'Owner B',
                'division': 'Division B',
                'logo': 'https://example.com/beta.png'
            }
        }

        # Sample enhanced data with historical matchups (new format)
        self.sample_enhanced_data = {
            'season_context': {
                'matchup_history': {
                    'weekly_results': {
                        1: [
                            {
                                'home_team': {'id': '1', 'name': 'Team Alpha'},
                                'away_team': {'id': '2', 'name': 'Team Beta'},
                                'home_score': 125.5,
                                'away_score': 118.3,
                                'home_projected_score': 120.0,
                                'away_projected_score': 115.0,
                                'home_optimal_score': 135.0,
                                'away_optimal_score': 130.0,
                                'winner_id': '1',
                                'loser_id': '2'
                            }
                        ],
                        2: [
                            {
                                'home_team': {'id': '2', 'name': 'Team Beta'},
                                'away_team': {'id': '1', 'name': 'Team Alpha'},
                                'home_score': 142.8,
                                'away_score': 135.2,
                                'home_projected_score': 130.0,
                                'away_projected_score': 125.0,
                                'home_optimal_score': 148.5,
                                'away_optimal_score': 142.0,
                                'winner_id': '2',
                                'loser_id': '1'
                            }
                        ]
                    }
                }
            }
        }

    def test_calculate_team_weekly_results_basic_functionality(self):
        """Test basic weekly results calculation with multiple weeks."""
        result = self.generator._calculate_team_weekly_results(self.sample_enhanced_data, self.sample_teams)

        # Verify structure
        assert isinstance(result, dict)
        assert '1' in result
        assert '2' in result

        # Verify Team Alpha results (2 weeks)
        team1_results = result['1']
        assert len(team1_results) == 2

        # Week 1 - Team Alpha won at home
        week1_result = team1_results[0]
        assert week1_result['week'] == 1
        assert week1_result['opponent'] == 'Team Beta'
        assert week1_result['opponentDivision'] == 'Division B'
        assert week1_result['homeAway'] == 'vs'
        assert week1_result['teamScore'] == 125.5
        assert week1_result['opponentScore'] == 118.3
        assert week1_result['result'] == 'Win'
        assert week1_result['recordAfter'] == '1-0'

        # Week 2 - Team Alpha lost away
        week2_result = team1_results[1]
        assert week2_result['week'] == 2
        assert week2_result['opponent'] == 'Team Beta'
        assert week2_result['homeAway'] == '@'
        assert week2_result['result'] == 'Loss'
        assert week2_result['recordAfter'] == '1-1'

    def test_calculate_team_weekly_results_no_matchup_history(self):
        """Test weekly results calculation when no historical data is available."""
        data_no_history = {}

        result = self.generator._calculate_team_weekly_results(data_no_history, self.sample_teams)

        # Should return empty results for all teams
        assert isinstance(result, dict)
        assert '1' in result
        assert '2' in result
        assert len(result['1']) == 0
        assert len(result['2']) == 0


class TestTeamLightboxHelperMethods:
    """Test helper methods for team lightbox functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TemplatedFantasyHTMLGenerator()

    def test_determine_match_result_team_wins(self):
        """Test match result determination when team wins."""
        result = self.generator._determine_match_result('1', '1', None)
        assert result == 'Win'

    def test_determine_match_result_team_loses(self):
        """Test match result determination when team loses."""
        result = self.generator._determine_match_result('1', '2', '1')
        assert result == 'Loss'

    def test_determine_match_result_tie_game(self):
        """Test match result determination for tie games."""
        result = self.generator._determine_match_result('1', None, None)
        assert result == 'Tie'

        # Also test with explicit None winner
        result = self.generator._determine_match_result('2', None, None)
        assert result == 'Tie'

    def test_calculate_record_after_week_win_sequence(self):
        """Test record calculation after a series of wins."""
        results = [
            {'result': 'Win'},
            {'result': 'Win'},
            {'result': 'Win'}
        ]
        record = self.generator._calculate_record_after_week(results, 'Win')
        assert record == '4-0'

    def test_calculate_record_after_week_mixed_results(self):
        """Test record calculation with wins, losses, and ties."""
        results = [
            {'result': 'Win'},
            {'result': 'Loss'},
            {'result': 'Tie'},
            {'result': 'Win'}
        ]
        record = self.generator._calculate_record_after_week(results, 'Loss')
        assert record == '2-2-1'

    def test_calculate_record_after_week_empty_history(self):
        """Test record calculation with no previous results."""
        results = []
        record = self.generator._calculate_record_after_week(results, 'Win')
        assert record == '1-0'

        record = self.generator._calculate_record_after_week(results, 'Loss')
        assert record == '0-1'

        record = self.generator._calculate_record_after_week(results, 'Tie')
        assert record == '0-0-1'

    def test_determine_match_result_from_scores_win(self):
        """Test fallback method for determining match result from scores - win."""
        result = self.generator._determine_match_result_from_scores(125.5, 118.3)
        assert result == 'Win'

    def test_determine_match_result_from_scores_loss(self):
        """Test fallback method for determining match result from scores - loss."""
        result = self.generator._determine_match_result_from_scores(118.3, 125.5)
        assert result == 'Loss'

    def test_determine_match_result_from_scores_tie(self):
        """Test fallback method for determining match result from scores - tie."""
        result = self.generator._determine_match_result_from_scores(125.0, 125.0)
        assert result == 'Tie'


class TestTeamLightboxIntegration:
    """Test integration scenarios for team lightbox functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TemplatedFantasyHTMLGenerator()

        # Comprehensive test data
        self.comprehensive_data = {
            'current_week_data': {
                'week': 4,
                'report_date': '2024-01-15T10:30:00Z',
                'league_name': 'Test League',
                'divisions': [
                    {
                        'name': 'Division A',
                        'teams': [
                            {
                                'id': '1',
                                'name': 'Team Alpha',
                                'owner': 'John Smith',
                                'division': 'Division A',
                                'logo': 'https://example.com/alpha.png'
                            }
                        ]
                    }
                ]
            },
            'season_context': {
                'team_standings': {
                    '1': {
                        'wins': 2,
                        'losses': 1,
                        'ties': 1,
                        'points_for': 450.75,
                        'points_against': 425.25,
                        'overall_rank': 3,
                        'division_rank': 2
                    }
                },
                'matchup_history': {
                    'weekly_results': {
                        1: [
                            {
                                'home_team': {'id': '1', 'name': 'Team Alpha'},
                                'away_team': {'id': '2', 'name': 'Team Beta'},
                                'home_score': 125.5,
                                'away_score': 125.5,
                                'home_projected_score': 120.0,
                                'away_projected_score': 115.0,
                                'home_optimal_score': 135.0,
                                'away_optimal_score': 130.0,
                                'winner_id': None,  # Tie game
                                'loser_id': None
                            }
                        ]
                    }
                }
            }
        }

    def test_integration_complete_lightbox_data_structure(self):
        """Test complete integration with realistic data structure."""
        team_logos = {'Team Alpha': 'https://example.com/alpha.png', 'Team Beta': 'https://example.com/beta.png'}
        result = self.generator._prepare_team_lightbox_data(self.comprehensive_data, team_logos)

        # Verify complete structure
        assert '1' in result
        team_data = result['1']

        # Basic team info
        assert team_data['name'] == 'Team Alpha'
        assert team_data['owner'] == 'John Smith'
        assert team_data['division'] == 'Division A'
        assert team_data['logo'] == 'https://example.com/alpha.png'

        # Season statistics
        stats = team_data['seasonStats']
        assert stats['wins'] == 2
        assert stats['losses'] == 1
        assert stats['ties'] == 1
        assert stats['rank'] == 3
        assert stats['pointsFor'] == 450.8  # Rounded
        assert stats['pointsAgainst'] == 425.2  # Rounded

        # Weekly results
        weekly = team_data['weeklyResults']
        assert len(weekly) == 1
        assert weekly[0]['week'] == 1
        assert weekly[0]['result'] == 'Tie'
        assert weekly[0]['recordAfter'] == '0-0-1'


    def test_error_handling_malformed_data(self):
        """Test error handling with malformed or missing data."""
        # Test with completely empty data
        empty_data = {}
        team_logos = {}
        result = self.generator._prepare_team_lightbox_data(empty_data, team_logos)
        assert isinstance(result, dict)
        assert len(result) == 0

        # Test with missing team ID
        malformed_data = {
            'current_week_data': {
                'divisions': [
                    {
                        'name': 'Division A',
                        'teams': [
                            {
                                'name': 'Team Alpha',  # Missing 'id' field
                                'owner': 'Owner A'
                            }
                        ]
                    }
                ]
            }
        }

        result = self.generator._prepare_team_lightbox_data(malformed_data, team_logos)
        # Should handle gracefully and return empty result
        assert isinstance(result, dict)

    def test_full_season_history_in_lightbox(self):
        """Test that team lightbox shows full season history instead of just current week."""
        # Enhanced data with multiple weeks of history
        multi_week_data = {
            'current_week_data': {
                'divisions': [
                    {
                        'name': 'Division A',
                        'teams': [
                            {
                                'id': '1',
                                'name': 'Team Alpha',
                                'owner': 'Owner A',
                                'division': 'Division A',
                                'logo': 'https://example.com/alpha.png'
                            },
                            {
                                'id': '2',
                                'name': 'Team Beta',
                                'owner': 'Owner B',
                                'division': 'Division B',
                                'logo': 'https://example.com/beta.png'
                            }
                        ]
                    }
                ]
            },
            'season_context': {
                'team_standings': {
                    '1': {
                        'wins': 2,
                        'losses': 1,
                        'ties': 0,
                        'points_for': 390.5,
                        'points_against': 380.2,
                        'overall_rank': 1,
                        'division_rank': 1
                    }
                },
                'matchup_history': {
                    'weekly_results': {
                        1: [
                            {
                                'home_team': {'id': '1', 'name': 'Team Alpha'},
                                'away_team': {'id': '2', 'name': 'Team Beta'},
                                'home_score': 125.5,
                                'away_score': 118.3,
                                'winner_id': '1',
                                'loser_id': '2'
                            }
                        ],
                        2: [
                            {
                                'home_team': {'id': '2', 'name': 'Team Beta'},
                                'away_team': {'id': '1', 'name': 'Team Alpha'},
                                'home_score': 135.2,
                                'away_score': 142.8,
                                'winner_id': '1',  # Away team won
                                'loser_id': '2'
                            }
                        ],
                        3: [
                            {
                                'home_team': {'id': '1', 'name': 'Team Alpha'},
                                'away_team': {'id': '2', 'name': 'Team Beta'},
                                'home_score': 122.2,
                                'away_score': 126.7,
                                'winner_id': '2',
                                'loser_id': '1'
                            }
                        ]
                    }
                }
            }
        }

        team_logos = {'Team Alpha': 'https://example.com/alpha.png', 'Team Beta': 'https://example.com/beta.png'}
        result = self.generator._prepare_team_lightbox_data(multi_week_data, team_logos)

        # Verify Team Alpha has results from all 3 weeks
        team1_weekly = result['1']['weeklyResults']
        assert len(team1_weekly) == 3

        # Verify correct week ordering and data
        assert team1_weekly[0]['week'] == 1
        assert team1_weekly[0]['result'] == 'Win'
        assert team1_weekly[0]['homeAway'] == 'vs'
        assert team1_weekly[0]['recordAfter'] == '1-0'

        assert team1_weekly[1]['week'] == 2
        assert team1_weekly[1]['result'] == 'Win'
        assert team1_weekly[1]['homeAway'] == '@'
        assert team1_weekly[1]['recordAfter'] == '2-0'

        assert team1_weekly[2]['week'] == 3
        assert team1_weekly[2]['result'] == 'Loss'
        assert team1_weekly[2]['homeAway'] == 'vs'
        assert team1_weekly[2]['recordAfter'] == '2-1'