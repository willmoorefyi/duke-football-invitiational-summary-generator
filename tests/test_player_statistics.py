import pytest
from unittest.mock import Mock, MagicMock
from src.models.data_models import Player, PlayerStatistics, InjuryStatus
from src.extractors.player_extractor import PlayerExtractor
from src.generators.templated_html_generator import TemplatedFantasyHTMLGenerator


class TestPlayerStatistics:
    """Test suite for PlayerStatistics model."""

    def test_player_statistics_creation_with_all_fields(self):
        """Test PlayerStatistics creation with all fields populated."""
        stats = PlayerStatistics(
            passing_completions=15,
            passing_attempts=25,
            passing_yards=250.0,
            passing_touchdowns=2,
            passing_interceptions=1,
            rushing_attempts=5,
            rushing_yards=25.5,
            rushing_touchdowns=1,
            receiving_receptions=3,
            receiving_yards=45.0,
            receiving_touchdowns=1,
            receiving_targets=4,
            field_goals_made=2,
            field_goals_attempted=3,
            extra_points_made=1,
            extra_points_attempted=1,
            defensive_touchdowns=1,
            defensive_interceptions=2,
            defensive_fumbles_recovered=1,
            defensive_safeties=0,
            defensive_sacks=3.0,
            points_allowed=14,
            yards_allowed=300
        )

        assert stats.passing_completions == 15
        assert stats.passing_attempts == 25
        assert stats.passing_yards == 250.0
        assert stats.passing_touchdowns == 2
        assert stats.passing_interceptions == 1
        assert stats.rushing_attempts == 5
        assert stats.rushing_yards == 25.5
        assert stats.rushing_touchdowns == 1
        assert stats.receiving_receptions == 3
        assert stats.receiving_yards == 45.0
        assert stats.receiving_touchdowns == 1
        assert stats.receiving_targets == 4
        assert stats.field_goals_made == 2
        assert stats.field_goals_attempted == 3
        assert stats.extra_points_made == 1
        assert stats.extra_points_attempted == 1
        assert stats.defensive_touchdowns == 1
        assert stats.defensive_interceptions == 2
        assert stats.defensive_fumbles_recovered == 1
        assert stats.defensive_safeties == 0
        assert stats.defensive_sacks == 3.0
        assert stats.points_allowed == 14
        assert stats.yards_allowed == 300

    def test_player_statistics_creation_with_partial_fields(self):
        """Test PlayerStatistics creation with only some fields populated."""
        stats = PlayerStatistics(
            passing_completions=10,
            passing_attempts=15,
            passing_yards=150.0,
            rushing_attempts=3
        )

        # Populated fields
        assert stats.passing_completions == 10
        assert stats.passing_attempts == 15
        assert stats.passing_yards == 150.0
        assert stats.rushing_attempts == 3

        # Unpopulated fields should be None
        assert stats.passing_touchdowns is None
        assert stats.passing_interceptions is None
        assert stats.rushing_yards is None
        assert stats.rushing_touchdowns is None
        assert stats.receiving_receptions is None
        assert stats.receiving_yards is None
        assert stats.receiving_touchdowns is None
        assert stats.receiving_targets is None
        assert stats.field_goals_made is None
        assert stats.field_goals_attempted is None
        assert stats.extra_points_made is None
        assert stats.extra_points_attempted is None
        assert stats.defensive_touchdowns is None
        assert stats.defensive_interceptions is None
        assert stats.defensive_fumbles_recovered is None
        assert stats.defensive_safeties is None
        assert stats.defensive_sacks is None
        assert stats.points_allowed is None
        assert stats.yards_allowed is None


class TestPlayerWithStatistics:
    """Test suite for Player model with statistics integration."""

    def test_player_creation_with_statistics(self):
        """Test Player creation with detailed statistics."""
        stats = PlayerStatistics(
            passing_completions=20,
            passing_attempts=30,
            passing_yards=275.0,
            passing_touchdowns=2,
            rushing_attempts=3,
            rushing_yards=15.0
        )

        player = Player(
            name="Josh Allen",
            position="QB",
            roster_slot="QB",
            team="Team Alpha",
            projected_score=18.5,
            actual_score=22.3,
            is_starter=True,
            should_have_started=True,
            injury_status=InjuryStatus.HEALTHY,
            statistics=stats
        )

        assert player.name == "Josh Allen"
        assert player.position == "QB"
        assert player.roster_slot == "QB"
        assert player.team == "Team Alpha"
        assert player.projected_score == 18.5
        assert player.actual_score == 22.3
        assert player.is_starter is True
        assert player.should_have_started is True
        assert player.injury_status == InjuryStatus.HEALTHY
        assert player.statistics is not None
        assert player.statistics.passing_completions == 20
        assert player.statistics.passing_attempts == 30
        assert player.statistics.passing_yards == 275.0
        assert player.statistics.passing_touchdowns == 2
        assert player.statistics.rushing_attempts == 3
        assert player.statistics.rushing_yards == 15.0

    def test_player_creation_without_statistics(self):
        """Test Player creation without statistics (backward compatibility)."""
        player = Player(
            name="Backup Player",
            position="RB",
            roster_slot="BE",
            team="Team Beta",
            projected_score=8.2,
            actual_score=5.1,
            is_starter=False,
            injury_status=InjuryStatus.QUESTIONABLE
        )

        assert player.name == "Backup Player"
        assert player.position == "RB"
        assert player.roster_slot == "BE"
        assert player.team == "Team Beta"
        assert player.projected_score == 8.2
        assert player.actual_score == 5.1
        assert player.is_starter is False
        assert player.should_have_started is None  # Default value
        assert player.injury_status == InjuryStatus.QUESTIONABLE
        assert player.statistics is None  # Should be None by default


class TestPlayerExtractorStatistics:
    """Test suite for PlayerExtractor statistics extraction."""

    def setup_method(self):
        """Set up test fixtures."""
        mock_espn_client = Mock()
        self.extractor = PlayerExtractor(mock_espn_client)

    def test_extract_player_statistics_with_valid_stats(self):
        """Test statistics extraction with valid ESPN player stats data."""
        # Mock ESPN player with stats data
        mock_espn_player = Mock()
        mock_espn_player.name = "Josh Allen"
        mock_espn_player.stats = {
            2: {  # Week 2 stats
                'breakdown': {
                    'passingCompletions': 15,
                    'passingAttempts': 25,
                    'passingYards': 250.0,
                    'passingTouchdowns': 2,
                    'passingInterceptions': 1,
                    'rushingAttempts': 5,
                    'rushingYards': 25.0,
                    'rushingTouchdowns': 1,
                    'receivingReceptions': 0,
                    'receivingYards': 0.0,
                    'receivingTouchdowns': 0
                }
            }
        }

        # Mock the get_target_week method to return week 2
        self.extractor.get_target_week = Mock(return_value=2)

        # Call the method
        stats = self.extractor._extract_player_statistics(mock_espn_player)

        # Assertions
        assert stats is not None
        assert isinstance(stats, PlayerStatistics)
        assert stats.passing_completions == 15
        assert stats.passing_attempts == 25
        assert stats.passing_yards == 250.0
        assert stats.passing_touchdowns == 2
        assert stats.passing_interceptions == 1
        assert stats.rushing_attempts == 5
        assert stats.rushing_yards == 25.0
        assert stats.rushing_touchdowns == 1
        assert stats.receiving_receptions == 0
        assert stats.receiving_yards == 0.0
        assert stats.receiving_touchdowns == 0

    def test_extract_player_statistics_no_stats_data(self):
        """Test statistics extraction when ESPN player has no stats data."""
        # Mock ESPN player without stats
        mock_espn_player = Mock()
        mock_espn_player.name = "Backup Player"
        mock_espn_player.stats = {}

        # Mock the get_target_week method
        self.extractor.get_target_week = Mock(return_value=2)

        # Call the method
        stats = self.extractor._extract_player_statistics(mock_espn_player)

        # Should return None when no stats available
        assert stats is None


class TestHTMLGeneratorStatisticsDisplay:
    """Test suite for HTML generator statistics display functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TemplatedFantasyHTMLGenerator()

    def test_get_player_stats_display_qb_with_stats(self):
        """Test QB statistics display with detailed stats."""
        player_data = {
            'name': 'Josh Allen',
            'position': 'QB',
            'actual_score': 25.4,
            'projected_score': 18.2,
            'statistics': {
                'passing_completions': 18,
                'passing_attempts': 28,
                'passing_yards': 285.0,
                'passing_touchdowns': 3,
                'rushing_attempts': 6,
                'rushing_yards': 35.0
            }
        }

        result = self.generator._get_player_stats_display(player_data)

        # Should only show statistics, no points/projection (that's in player name)
        expected_result = "18/28 pass; 285 pass yds; 3 pass TD; 6 rush; 35 rush yds"
        assert result == expected_result

    def test_get_player_stats_display_rb_with_stats(self):
        """Test RB statistics display with detailed stats."""
        player_data = {
            'name': 'Saquon Barkley',
            'position': 'RB',
            'actual_score': 18.7,
            'projected_score': 15.3,
            'statistics': {
                'rushing_attempts': 15,
                'rushing_yards': 95.0,
                'rushing_touchdowns': 1,
                'receiving_receptions': 4,
                'receiving_yards': 32.0
            }
        }

        result = self.generator._get_player_stats_display(player_data)

        # Should only show statistics, no points/projection (that's in player name)
        expected_result = "15 rush; 95 rush yds; 1 rush TD; 4 rec; 32 rec yds"
        assert result == expected_result

    def test_get_player_stats_display_no_stats_backward_compatibility(self):
        """Test statistics display falls back gracefully when no stats available."""
        player_data = {
            'name': 'Unknown Player',
            'position': 'WR',
            'actual_score': 12.1,
            'projected_score': 14.5,
            'statistics': None  # No statistics available
        }

        result = self.generator._get_player_stats_display(player_data)

        # Should show stats not available message when no statistics
        assert result == "Stats not available"