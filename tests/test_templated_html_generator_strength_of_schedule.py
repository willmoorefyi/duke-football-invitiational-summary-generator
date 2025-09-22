import pytest
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.generators.templated_html_generator import TemplatedFantasyHTMLGenerator


class TestTemplatedHTMLGeneratorStrengthOfSchedule:
    """Test suite for strength of schedule functionality in HTML generator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TemplatedFantasyHTMLGenerator()

        # Sample enhanced data with team standings for strength of schedule
        self.sample_enhanced_data = {
            "current_week": {
                "league_id": 380491,
                "league_name": "Duke Football Invitational",
                "season": 2025,
                "week": 2,
                "report_date": "2025-09-21T21:04:13.720247",
                "divisions": [
                    {
                        "name": "Adams",
                        "teams": [
                            {"id": 1, "name": "Team A", "logo": "logo_a.png", "division": "Adams"},
                            {"id": 2, "name": "Team B", "logo": "logo_b.png", "division": "Adams"}
                        ]
                    }
                ],
                "matchups": []
            },
            "season_context": {
                "team_standings": {
                    "1": {
                        "id": 1,
                        "name": "Team A",
                        "division": "Adams",
                        "logo": "logo_a.png",
                        "wins": 2,
                        "losses": 0,
                        "ties": 0,
                        "points_for": 240.0,
                        "points_against": 180.0
                    },
                    "2": {
                        "id": 2,
                        "name": "Team B",
                        "division": "Adams",
                        "logo": "logo_b.png",
                        "wins": 1,
                        "losses": 1,
                        "ties": 0,
                        "points_for": 220.0,
                        "points_against": 200.0
                    },
                    "3": {
                        "id": 3,
                        "name": "Team C",
                        "division": "Smythe",
                        "logo": "logo_c.png",
                        "wins": 0,
                        "losses": 2,
                        "ties": 0,
                        "points_for": 160.0,
                        "points_against": 240.0
                    }
                }
            },
            "metadata": {
                "total_weeks_processed": 2
            }
        }

    def test_prepare_strength_of_schedule_data_success(self):
        """Test successful preparation of strength of schedule data."""
        team_logos = {"Team A": "logo_a.png", "Team B": "logo_b.png", "Team C": "logo_c.png"}

        result = self.generator._prepare_strength_of_schedule_data(self.sample_enhanced_data, team_logos)

        # Check return structure
        assert 'teams' in result
        assert 'average_points_per_game' in result
        assert 'total_weeks' in result

        # Verify average calculation: (240 + 220 + 160) / (3 teams * 2 weeks) = 620 / 6 = 103.33
        expected_avg = (240.0 + 220.0 + 160.0) / (3 * 2)
        assert abs(result['average_points_per_game'] - expected_avg) < 0.01
        assert result['total_weeks'] == 2

        # Check team data
        teams = result['teams']
        assert len(teams) == 3

        # Teams should be sorted by points_against per game (highest first)
        # Team C: 240/2 = 120 per game (most difficult schedule)
        # Team B: 200/2 = 100 per game
        # Team A: 180/2 = 90 per game (least difficult schedule)
        assert teams[0]['name'] == 'Team C'
        assert teams[0]['sos_rank'] == 1
        assert teams[0]['points_against_per_game'] == 120.0

        assert teams[1]['name'] == 'Team B'
        assert teams[1]['sos_rank'] == 2
        assert teams[1]['points_against_per_game'] == 100.0

        assert teams[2]['name'] == 'Team A'
        assert teams[2]['sos_rank'] == 3
        assert teams[2]['points_against_per_game'] == 90.0

    def test_prepare_strength_of_schedule_data_percentage_calculation(self):
        """Test percentage vs average calculation for strength of schedule."""
        team_logos = {"Team A": "logo_a.png", "Team B": "logo_b.png", "Team C": "logo_c.png"}

        result = self.generator._prepare_strength_of_schedule_data(self.sample_enhanced_data, team_logos)

        # Average = 103.33 points per game
        expected_avg = (240.0 + 220.0 + 160.0) / (3 * 2)  # 103.33

        teams = result['teams']

        # Team C: 120 points against per game vs 103.33 avg = +16.13%
        team_c = next(t for t in teams if t['name'] == 'Team C')
        expected_pct_c = ((120.0 - expected_avg) / expected_avg) * 100
        assert abs(team_c['percentage_vs_average'] - expected_pct_c) < 0.1
        assert team_c['percentage_vs_average'] > 0  # Above average (harder schedule)

        # Team A: 90 points against per game vs 103.33 avg = -12.90%
        team_a = next(t for t in teams if t['name'] == 'Team A')
        expected_pct_a = ((90.0 - expected_avg) / expected_avg) * 100
        assert abs(team_a['percentage_vs_average'] - expected_pct_a) < 0.1
        assert team_a['percentage_vs_average'] < 0  # Below average (easier schedule)

    def test_prepare_strength_of_schedule_data_record_formatting(self):
        """Test head-to-head record formatting including ties."""
        # Add a team with ties
        data_with_ties = self.sample_enhanced_data.copy()
        data_with_ties['season_context']['team_standings']['4'] = {
            "id": 4,
            "name": "Team D",
            "division": "Patrick",
            "logo": "logo_d.png",
            "wins": 1,
            "losses": 1,
            "ties": 1,  # Has a tie game
            "points_for": 200.0,
            "points_against": 200.0
        }

        team_logos = {"Team A": "logo_a.png", "Team B": "logo_b.png", "Team C": "logo_c.png", "Team D": "logo_d.png"}

        result = self.generator._prepare_strength_of_schedule_data(data_with_ties, team_logos)

        teams = result['teams']

        # Find Team D and check its record format includes tie
        team_d = next(t for t in teams if t['name'] == 'Team D')
        assert team_d['record'] == '1-1-1'  # wins-losses-ties format

        # Check other teams still use wins-losses format (no ties)
        team_a = next(t for t in teams if t['name'] == 'Team A')
        assert team_a['record'] == '2-0'  # No ties, so no third number

    def test_prepare_strength_of_schedule_data_edge_cases(self):
        """Test edge cases like missing data and zero values."""
        # Test with minimal/missing data
        minimal_data = {
            "current_week": {"week": 1},
            "season_context": {"team_standings": {}},
            "metadata": {"total_weeks_processed": 1}
        }

        result = self.generator._prepare_strength_of_schedule_data(minimal_data, {})

        # Should handle empty team standings gracefully
        assert result['teams'] == []
        assert result['average_points_per_game'] == 0.0
        assert result['total_weeks'] == 1

    def test_prepare_strength_of_schedule_data_fallback_week_calculation(self):
        """Test fallback week calculation when metadata is missing."""
        # Remove metadata to test fallback
        data_no_metadata = self.sample_enhanced_data.copy()
        del data_no_metadata['metadata']

        team_logos = {"Team A": "logo_a.png", "Team B": "logo_b.png", "Team C": "logo_c.png"}

        result = self.generator._prepare_strength_of_schedule_data(data_no_metadata, team_logos)

        # Should use current_week.week as fallback
        assert result['total_weeks'] == 2  # From current_week.week

        # Average calculation should still work
        expected_avg = (240.0 + 220.0 + 160.0) / (3 * 2)
        assert abs(result['average_points_per_game'] - expected_avg) < 0.01