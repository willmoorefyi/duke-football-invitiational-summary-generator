"""Tests for playoff view functionality."""

import pytest
from unittest.mock import Mock, patch
from src.pipeline.aggregate_stage import AggregateStage
from src.generators.templated_html_generator import TemplatedFantasyHTMLGenerator


class TestPlayoffDetection:
    """Tests for playoff week detection."""

    def test_is_playoff_week_true_for_week_15(self):
        """Week 15 should be detected as playoff (14 regular season weeks)."""
        generator = TemplatedFantasyHTMLGenerator()
        data = {
            'season_context': {
                'playoff_context': {
                    'is_playoff_week': True,
                    'playoff_week_number': 1
                }
            }
        }
        assert generator._is_playoff_week(data) is True

    def test_is_playoff_week_false_for_week_14(self):
        """Week 14 should not be detected as playoff."""
        generator = TemplatedFantasyHTMLGenerator()
        data = {
            'season_context': {
                'playoff_context': {
                    'is_playoff_week': False,
                    'playoff_week_number': 0
                }
            }
        }
        assert generator._is_playoff_week(data) is False

    def test_is_playoff_week_fallback_to_week_number(self):
        """Should fallback to week number if no playoff_context."""
        generator = TemplatedFantasyHTMLGenerator()

        # Week 15 should be playoff
        data_playoff = {'current_week': {'week': 15}}
        assert generator._is_playoff_week(data_playoff) is True

        # Week 14 should not be playoff
        data_regular = {'current_week': {'week': 14}}
        assert generator._is_playoff_week(data_regular) is False


class TestPlayoffContext:
    """Tests for playoff context creation."""

    @pytest.fixture
    def stage(self):
        """Create AggregateStage with mocked config."""
        with patch('src.pipeline.base.get_config') as mock_get_config:
            mock_config = Mock()
            mock_config.pipeline.aws.dynamodb_table = 'test-table'
            mock_config.pipeline.aws.region = 'us-east-1'
            mock_config.pipeline.aws.profile = None
            mock_get_config.return_value = mock_config
            return AggregateStage(league_id=123456, dry_run=True)

    def test_create_playoff_context_regular_season(self, stage):
        """Regular season should have is_playoff_week=False."""
        current_data = {'week': 10, 'matchups': []}
        league_settings = {'regular_season_weeks': 14, 'playoff_team_count': 6}

        context = stage._create_playoff_context(current_data, league_settings)

        assert context['is_playoff_week'] is False
        assert context['playoff_week_number'] == 0
        assert context['championship_bracket'] == []
        assert context['consolation_bracket'] == []

    def test_create_playoff_context_playoff_week(self, stage):
        """Playoff week should have is_playoff_week=True."""
        current_data = {
            'week': 15,
            'matchups': [
                {
                    'home_team': {'id': 1, 'name': 'Team A', 'standing': 3, 'logo': ''},
                    'away_team': {'id': 2, 'name': 'Team B', 'standing': 6, 'logo': ''},
                    'home_score': 100, 'away_score': 90,
                    'is_complete': True, 'winner_id': 1
                },
                {
                    'home_team': {'id': 3, 'name': 'Team C', 'standing': 7, 'logo': ''},
                    'away_team': {'id': 4, 'name': 'Team D', 'standing': 8, 'logo': ''},
                    'home_score': 80, 'away_score': 95,
                    'is_complete': True, 'winner_id': 4
                }
            ]
        }
        league_settings = {'regular_season_weeks': 14, 'playoff_team_count': 6}

        context = stage._create_playoff_context(current_data, league_settings)

        assert context['is_playoff_week'] is True
        assert context['playoff_week_number'] == 1
        assert len(context['championship_bracket']) == 1
        assert len(context['consolation_bracket']) == 1

    def test_matchup_categorization_championship_vs_consolation(self, stage):
        """Championship bracket should only include teams with standing <= playoff_team_count."""

        current_data = {
            'week': 15,
            'matchups': [
                # Championship: both teams in top 6
                {
                    'home_team': {'id': 1, 'name': 'Seed 1', 'standing': 1, 'logo': ''},
                    'away_team': {'id': 2, 'name': 'Seed 5', 'standing': 5, 'logo': ''},
                    'home_score': 120, 'away_score': 100,
                    'is_complete': True, 'winner_id': 1
                },
                # Consolation: both teams outside top 6
                {
                    'home_team': {'id': 3, 'name': 'Seed 7', 'standing': 7, 'logo': ''},
                    'away_team': {'id': 4, 'name': 'Seed 10', 'standing': 10, 'logo': ''},
                    'home_score': 90, 'away_score': 85,
                    'is_complete': True, 'winner_id': 3
                },
                # Mixed: should go to consolation (not both in top 6)
                {
                    'home_team': {'id': 5, 'name': 'Seed 6', 'standing': 6, 'logo': ''},
                    'away_team': {'id': 6, 'name': 'Seed 8', 'standing': 8, 'logo': ''},
                    'home_score': 95, 'away_score': 88,
                    'is_complete': True, 'winner_id': 5
                }
            ]
        }
        league_settings = {'regular_season_weeks': 14, 'playoff_team_count': 6}

        context = stage._create_playoff_context(current_data, league_settings)

        # Only the first matchup should be championship
        assert len(context['championship_bracket']) == 1
        assert context['championship_bracket'][0]['home_team']['seed'] == 1

        # Two matchups should be consolation
        assert len(context['consolation_bracket']) == 2


class TestPlayoffMatchupFiltering:
    """Tests for filtering matchups to championship bracket."""

    def test_filter_playoff_matchups(self):
        """Should filter matchups to only championship bracket teams."""
        generator = TemplatedFantasyHTMLGenerator()

        matchups_sorted = [
            {'home_team': {'id': 1}, 'away_team': {'id': 5}},
            {'home_team': {'id': 7}, 'away_team': {'id': 8}},
            {'home_team': {'id': 2}, 'away_team': {'id': 3}},
        ]

        championship_bracket = [
            {'home_team': {'id': 1}, 'away_team': {'id': 5}},
            {'home_team': {'id': 2}, 'away_team': {'id': 3}},
        ]

        filtered = generator._filter_playoff_matchups(matchups_sorted, championship_bracket)

        assert len(filtered) == 2
        assert filtered[0]['home_team']['id'] == 1
        assert filtered[1]['home_team']['id'] == 2

    def test_filter_playoff_matchups_returns_all_if_no_match(self):
        """Should return all matchups if no championship bracket matches."""
        generator = TemplatedFantasyHTMLGenerator()

        matchups_sorted = [
            {'home_team': {'id': 7}, 'away_team': {'id': 8}},
        ]

        championship_bracket = [
            {'home_team': {'id': 1}, 'away_team': {'id': 5}},
        ]

        filtered = generator._filter_playoff_matchups(matchups_sorted, championship_bracket)

        # Should return original matchups as fallback
        assert len(filtered) == 1
        assert filtered[0]['home_team']['id'] == 7
