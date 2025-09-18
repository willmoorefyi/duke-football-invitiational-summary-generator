import pytest
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.generators.templated_html_generator import TemplatedFantasyHTMLGenerator


class TestTemplatedHTMLGeneratorWeeklySummary:
    """Test suite for weekly summary functionality in HTML generator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TemplatedFantasyHTMLGenerator()

        # Sample matchup data for testing weekly summary
        self.sample_matchup_data = {
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
                            "overall_rank": 1,
                            "wins": 1,
                            "losses": 0,
                            "ties": 0,
                            "points_for": 139.7,
                            "points_against": 132.58,
                            "division": "Adams"
                        },
                        {
                            "id": 1,
                            "name": "O'ahu State Warriors",
                            "logo": "https://example.com/team1.png",
                            "overall_rank": 2,
                            "wins": 0,
                            "losses": 1,
                            "ties": 0,
                            "points_for": 132.58,
                            "points_against": 139.7,
                            "division": "Adams"
                        }
                    ]
                }
            ],
            "matchups": [
                {
                    "home_team": {"id": 3, "name": "They Stole Danny's Dimes"},
                    "away_team": {"id": 1, "name": "O'ahu State Warriors"},
                    "home_score": 139.7,
                    "away_score": 132.58,
                    "home_projected_score": 115.69,
                    "away_projected_score": 121.23,
                    "home_optimal_score": 159.3,
                    "away_optimal_score": 132.58,
                    "winner_id": 3,
                    "loser_id": 1,
                    "players": []
                },
                {
                    "home_team": {"id": 5, "name": "Team Alpha"},
                    "away_team": {"id": 6, "name": "Team Beta"},
                    "home_score": 145.2,
                    "away_score": 120.8,
                    "home_projected_score": 130.0,
                    "away_projected_score": 125.0,
                    "home_optimal_score": 150.0,
                    "away_optimal_score": 125.0,
                    "winner_id": 5,
                    "loser_id": 6,
                    "players": []
                }
            ],
            "awards": {},
            "injured_starters": []
        }

        self.team_logos = {
            "They Stole Danny's Dimes": "https://example.com/team3.png",
            "O'ahu State Warriors": "https://example.com/team1.png",
            "Team Alpha": "https://example.com/alpha.png",
            "Team Beta": "https://example.com/beta.png"
        }

    def test_prepare_weekly_summary_data_success(self):
        """Test successful preparation of weekly summary data."""
        result = self.generator._prepare_weekly_summary_data(
            self.sample_matchup_data,
            self.team_logos
        )

        # Should return correct structure
        assert 'team_scores' in result
        assert 'median_score' in result

        # Should have 4 teams total (2 matchups = 4 teams)
        team_scores = result['team_scores']
        assert len(team_scores) == 4

        # Should be sorted by score (highest first)
        scores = [team['score'] for team in team_scores]
        assert scores == sorted(scores, reverse=True)
        assert scores == [145.2, 139.7, 132.58, 120.8]

        # Check first team (highest scorer)
        top_team = team_scores[0]
        assert top_team['team_name'] == "Team Alpha"
        assert top_team['score'] == 145.2
        assert top_team['result'] == "Win"
        assert top_team['margin_display'] == "+24.40"

        # Check second team
        second_team = team_scores[1]
        assert second_team['team_name'] == "They Stole Danny's Dimes"
        assert second_team['score'] == 139.7
        assert second_team['result'] == "Win"
        assert second_team['margin_display'] == "+7.12"

        # Check losing teams
        third_team = team_scores[2]
        assert third_team['team_name'] == "O'ahu State Warriors"
        assert third_team['result'] == "Loss"
        assert third_team['margin_display'] == "-7.12"

        fourth_team = team_scores[3]
        assert fourth_team['team_name'] == "Team Beta"
        assert fourth_team['result'] == "Loss"
        assert fourth_team['margin_display'] == "-24.40"

    def test_prepare_weekly_summary_median_calculation(self):
        """Test median score calculation."""
        result = self.generator._prepare_weekly_summary_data(
            self.sample_matchup_data,
            self.team_logos
        )

        # Median of [145.2, 139.7, 132.58, 120.8] should be (139.7 + 132.58) / 2 = 136.14
        expected_median = (139.7 + 132.58) / 2
        assert abs(result['median_score'] - expected_median) < 0.01

    def test_prepare_weekly_summary_tie_game(self):
        """Test handling of tie games."""
        tie_data = {
            "matchups": [
                {
                    "home_team": {"id": 1, "name": "Team A"},
                    "away_team": {"id": 2, "name": "Team B"},
                    "home_score": 125.5,
                    "away_score": 125.5
                }
            ]
        }

        result = self.generator._prepare_weekly_summary_data(tie_data, {})

        team_scores = result['team_scores']
        assert len(team_scores) == 2

        # Both teams should have "Tie" result and "0.00" margin
        for team in team_scores:
            assert team['result'] == "Tie"
            assert team['margin_display'] == "0.00"
            assert team['score'] == 125.5

    def test_prepare_weekly_summary_no_matchups(self):
        """Test handling of data with no matchups."""
        empty_data = {"matchups": []}

        result = self.generator._prepare_weekly_summary_data(empty_data, {})

        assert result['team_scores'] == []
        assert result['median_score'] == 0.0

    def test_prepare_weekly_summary_single_matchup(self):
        """Test handling of single matchup."""
        single_matchup_data = {
            "matchups": [
                {
                    "home_team": {"id": 1, "name": "Winner"},
                    "away_team": {"id": 2, "name": "Loser"},
                    "home_score": 150.0,
                    "away_score": 100.0
                }
            ]
        }

        result = self.generator._prepare_weekly_summary_data(single_matchup_data, {})

        team_scores = result['team_scores']
        assert len(team_scores) == 2

        # Winner should be first (higher score)
        winner = team_scores[0]
        assert winner['team_name'] == "Winner"
        assert winner['result'] == "Win"
        assert winner['margin_display'] == "+50.00"

        loser = team_scores[1]
        assert loser['team_name'] == "Loser"
        assert loser['result'] == "Loss"
        assert loser['margin_display'] == "-50.00"

        # Median of [150.0, 100.0] should be 125.0
        assert result['median_score'] == 125.0

    def test_prepare_weekly_summary_margin_formatting(self):
        """Test proper formatting of margin values."""
        margin_test_data = {
            "matchups": [
                {
                    "home_team": {"id": 1, "name": "High Scorer"},
                    "away_team": {"id": 2, "name": "Low Scorer"},
                    "home_score": 200.123,
                    "away_score": 75.456
                }
            ]
        }

        result = self.generator._prepare_weekly_summary_data(margin_test_data, {})

        team_scores = result['team_scores']

        # Check margin formatting (should be 2 decimal places)
        winner = team_scores[0]
        loser = team_scores[1]

        assert winner['margin_display'] == "+124.67"  # 200.123 - 75.456 = 124.667
        assert loser['margin_display'] == "-124.67"

    def test_prepare_weekly_summary_integration_with_template_vars(self):
        """Test that weekly summary data integrates correctly with template variables."""
        # Test that _prepare_template_variables includes the weekly summary data
        result = self.generator._prepare_template_variables(self.sample_matchup_data)

        # Should have scoring_leaders_data and median_score in template vars
        assert 'scoring_leaders_data' in result
        assert 'median_score' in result

        # Check the data matches our expected format
        scoring_data = result['scoring_leaders_data']
        assert len(scoring_data) == 4
        assert all('team_name' in team for team in scoring_data)
        assert all('score' in team for team in scoring_data)
        assert all('result' in team for team in scoring_data)
        assert all('margin_display' in team for team in scoring_data)

        # Check median score is a number
        assert isinstance(result['median_score'], (int, float))

    def test_prepare_weekly_summary_odd_number_median(self):
        """Test median calculation with odd number of teams."""
        odd_data = {
            "matchups": [
                {
                    "home_team": {"id": 1, "name": "Team A"},
                    "away_team": {"id": 2, "name": "Team B"},
                    "home_score": 130.0,
                    "away_score": 120.0
                },
                {
                    "home_team": {"id": 3, "name": "Team C"},
                    "away_team": {"id": 4, "name": "Team D"},
                    "home_score": 140.0,
                    "away_score": 110.0
                },
                {
                    "home_team": {"id": 5, "name": "Team E"},
                    "away_team": {"id": 6, "name": "Team F"},
                    "home_score": 125.0,
                    "away_score": 135.0
                }
            ]
        }

        result = self.generator._prepare_weekly_summary_data(odd_data, {})

        # Scores: [140.0, 135.0, 130.0, 125.0, 120.0, 110.0]
        # Median of 6 values should be average of 3rd and 4th: (130.0 + 125.0) / 2 = 127.5
        expected_median = 127.5
        assert result['median_score'] == expected_median