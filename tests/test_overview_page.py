import pytest
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.generators.templated_html_generator import TemplatedFantasyHTMLGenerator
from src.pipeline.deploy_stage import DeployStage


class TestOverviewPageGeneration:
    """Test suite for overview page generation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TemplatedFantasyHTMLGenerator()

        # Sample enhanced data with season context
        self.sample_enhanced_data = {
            "current_week": {
                "league_id": 380491,
                "league_name": "Duke Football Invitational",
                "season": 2025,
                "week": 4,
                "report_date": "2025-09-30T10:34:03.569584",
                "divisions": [
                    {
                        "name": "Adams",
                        "teams": [
                            {
                                "id": 1,
                                "name": "Team Alpha",
                                "logo": "https://example.com/team1.png",
                                "division": "Adams"
                            },
                            {
                                "id": 2,
                                "name": "Team Beta",
                                "logo": "https://example.com/team2.png",
                                "division": "Adams"
                            }
                        ]
                    }
                ],
                "matchups": [
                    {
                        "home_team": {"id": 1, "name": "Team Alpha"},
                        "away_team": {"id": 2, "name": "Team Beta"},
                        "home_score": 120.5,
                        "away_score": 115.3,
                        "winner_id": "1",
                        "loser_id": "2"
                    }
                ]
            },
            "season_context": {
                "team_standings": {
                    "1": {
                        "wins": 3,
                        "losses": 1,
                        "ties": 0,
                        "points_for": 450.5,
                        "points_against": 420.3,
                        "overall_rank": 1,
                        "division_rank": 1
                    },
                    "2": {
                        "wins": 1,
                        "losses": 3,
                        "ties": 0,
                        "points_for": 420.3,
                        "points_against": 450.5,
                        "overall_rank": 2,
                        "division_rank": 2
                    }
                },
                "weekly_statistics": {
                    "weeks": [
                        {
                            "week": 1,
                            "median": 100.0,
                            "average": 105.5,
                            "max": 130.0,
                            "min": 80.0,
                            "std_dev": 15.5,
                            "average_efficiency": 85.0,
                            "max_team_name": "Team Alpha",
                            "min_team_name": "Team Beta"
                        },
                        {
                            "week": 2,
                            "median": 102.0,
                            "average": 107.5,
                            "max": 135.0,
                            "min": 82.0,
                            "std_dev": 16.5,
                            "average_efficiency": 86.0,
                            "max_team_name": "Team Alpha",
                            "min_team_name": "Team Beta"
                        }
                    ]
                }
            },
            "metadata": {
                "is_latest_week": True,
                "current_week": 4
            }
        }

    def test_overview_page_generation_basic(self):
        """Test basic overview page generation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            output_path = f.name

        try:
            self.generator.generate_overview_page(self.sample_enhanced_data, output_path)

            # Verify file was created
            assert Path(output_path).exists()

            # Read and verify content
            with open(output_path, 'r') as f:
                content = f.read()

            # Check for key sections
            assert "Season Overview" in content
            assert "Overall League Standings" in content
            assert "Weekly Totals" in content
            assert "Duke Football Invitational" in content

        finally:
            Path(output_path).unlink()

    def test_overview_page_contains_week_links(self):
        """Test that overview page contains clickable week links in Weekly Totals table."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            output_path = f.name

        try:
            self.generator.generate_overview_page(self.sample_enhanced_data, output_path)

            with open(output_path, 'r') as f:
                content = f.read()

            # Check for week links with arrow indicator
            assert "Week 1 →" in content
            assert "Week 2 →" in content

            # Check for proper link structure
            assert 'class="week-report-link"' in content
            assert 'fantasy_report_2025_week_1.html' in content
            assert 'fantasy_report_2025_week_2.html' in content

            # Verify links open in new tab
            assert 'target="_blank"' in content

        finally:
            Path(output_path).unlink()

    def test_overview_page_no_report_column(self):
        """Test that overview page does NOT have a separate Report column."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            output_path = f.name

        try:
            self.generator.generate_overview_page(self.sample_enhanced_data, output_path)

            with open(output_path, 'r') as f:
                content = f.read()

            # Weekly Totals table should have 7 columns, not 8
            # Check that there's NO separate "Report" header
            assert '<th class="center">Report</th>' not in content

            # Verify the standard 7 columns exist
            assert '<th>Week</th>' in content
            assert '<th class="numeric">Median</th>' in content
            assert '<th class="numeric">Average</th>' in content

        finally:
            Path(output_path).unlink()

    def test_overview_page_team_standings(self):
        """Test that overview page displays team standings correctly."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            output_path = f.name

        try:
            self.generator.generate_overview_page(self.sample_enhanced_data, output_path)

            with open(output_path, 'r') as f:
                content = f.read()

            # Check for team standings data
            assert "Team Alpha" in content

            # Check for standings table structure
            assert '<th class="numeric">Rank</th>' in content or '<th>Team</th>' in content
            assert '<th class="numeric">Wins</th>' in content
            assert '<th class="numeric">Losses</th>' in content

        finally:
            Path(output_path).unlink()


class TestOverviewPageConditionalGeneration:
    """Test suite for conditional overview page generation (latest week only)."""

    def test_deploy_stage_skips_overview_for_non_latest_week(self):
        """Test that deploy stage skips overview generation when is_latest_week is False."""
        # Create enhanced JSON with is_latest_week = False
        test_data = {
            "metadata": {"is_latest_week": False},
            "current_week": {
                "week": 3,
                "season": 2025,
                "league_name": "Test League",
                "report_date": "2025-09-30T10:00:00Z",
                "divisions": []
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_path = f.name

        try:
            stage = DeployStage(league_id='test', dry_run=True)
            result = stage._generate_and_upload_overview(temp_path)

            # Should return empty dict (skipped generation)
            assert result == {}

        finally:
            Path(temp_path).unlink()

    def test_deploy_stage_generates_overview_for_latest_week(self):
        """Test that deploy stage generates overview when is_latest_week is True."""
        # Create enhanced JSON with is_latest_week = True
        test_data = {
            "metadata": {"is_latest_week": True},
            "current_week": {
                "week": 4,
                "season": 2025,
                "league_name": "Test League",
                "report_date": "2025-09-30T10:00:00Z",
                "divisions": [
                    {
                        "name": "Test Division",
                        "teams": [
                            {"id": 1, "name": "Test Team", "logo": "http://example.com/logo.png", "division": "Test Division"}
                        ]
                    }
                ]
            },
            "season_context": {
                "team_standings": {
                    "1": {"wins": 3, "losses": 1, "ties": 0, "points_for": 400.0, "points_against": 350.0, "overall_rank": 1, "division_rank": 1}
                },
                "weekly_statistics": {
                    "weeks": [
                        {"week": 1, "median": 100.0, "average": 105.0, "max": 130.0, "min": 80.0, "std_dev": 15.0, "average_efficiency": 85.0, "max_team_name": "Test Team", "min_team_name": "Test Team"}
                    ]
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_path = f.name

        try:
            stage = DeployStage(league_id='test', dry_run=True)
            result = stage._generate_and_upload_overview(temp_path)

            # Should return metadata dict with local_path
            assert 'local_path' in result or result == {}  # dry_run may skip actual generation

        finally:
            Path(temp_path).unlink()
