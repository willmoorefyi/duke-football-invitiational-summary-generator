"""
Tests for Position Power Rankings functionality.

Tests cover:
- Heatmap color generation (blue-white-red gradient)
- Text color contrast calculation
- Weekly position rankings data preparation
- Season position rankings data preparation
- League share percentage calculations
"""

import pytest
from src.generators.templated_html_generator import TemplatedFantasyHTMLGenerator


class TestHeatmapColorCalculation:
    """Tests for heatmap color generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TemplatedFantasyHTMLGenerator()

    def test_heatmap_color_negative_value_returns_blue(self):
        """Negative values should return blue-ish colors."""
        color = self.generator._calculate_heatmap_color(-20)
        # At min value (-20), should be full blue: rgb(59, 130, 246)
        assert color == "rgb(59, 130, 246)"

    def test_heatmap_color_zero_returns_white(self):
        """Zero value should return white."""
        color = self.generator._calculate_heatmap_color(0)
        assert color == "rgb(255, 255, 255)"

    def test_heatmap_color_positive_value_returns_red(self):
        """Positive values should return red-ish colors."""
        color = self.generator._calculate_heatmap_color(20)
        # At max value (20), should be full red: rgb(239, 68, 68)
        assert color == "rgb(239, 68, 68)"

    def test_heatmap_color_clamped_below_min(self):
        """Values below min should be clamped."""
        color = self.generator._calculate_heatmap_color(-50)
        # Should be same as -20 (clamped)
        assert color == "rgb(59, 130, 246)"

    def test_heatmap_color_clamped_above_max(self):
        """Values above max should be clamped."""
        color = self.generator._calculate_heatmap_color(50)
        # Should be same as 20 (clamped)
        assert color == "rgb(239, 68, 68)"


class TestHeatmapTextColor:
    """Tests for text color contrast calculation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TemplatedFantasyHTMLGenerator()

    def test_text_color_on_light_background_is_black(self):
        """Light backgrounds should get black text."""
        text_color = self.generator._calculate_heatmap_text_color("rgb(255, 255, 255)")
        assert text_color == "rgb(0, 0, 0)"

    def test_text_color_on_dark_background_is_white(self):
        """Dark backgrounds should get white text."""
        text_color = self.generator._calculate_heatmap_text_color("rgb(59, 130, 246)")
        assert text_color == "rgb(255, 255, 255)"

    def test_text_color_invalid_format_returns_black(self):
        """Invalid color format should return black as default."""
        text_color = self.generator._calculate_heatmap_text_color("invalid")
        assert text_color == "rgb(0, 0, 0)"


class TestPositionRankingsDataPreparation:
    """Tests for position rankings data preparation methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TemplatedFantasyHTMLGenerator()
        self.team_logos = {"Team A": "http://logo.png"}

    def test_prepare_position_rankings_empty_data(self):
        """Empty data should return empty list."""
        data = {"season_context": {}}
        result = self.generator._prepare_position_rankings(data, 1, self.team_logos)
        assert result == []

    def test_prepare_position_rankings_with_data(self):
        """Should prepare rankings with colors."""
        data = {
            "season_context": {
                "position_stats": {
                    "weekly_stats": {
                        "1": {
                            "team_stats": {
                                "1": {
                                    "team_name": "Team A",
                                    "team_logo": "http://logo.png",
                                    "positions": {
                                        "QB": {"points": 25.0, "starters": 1, "vs_median": 5.0},
                                        "RB": {"points": 30.0, "starters": 2, "vs_median": -2.0},
                                        "WR": {"points": 0, "starters": 0, "vs_median": 0},
                                        "TE": {"points": 0, "starters": 0, "vs_median": 0},
                                        "K": {"points": 0, "starters": 0, "vs_median": 0},
                                        "D/ST": {"points": 0, "starters": 0, "vs_median": 0},
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        result = self.generator._prepare_position_rankings(data, 1, self.team_logos)

        assert len(result) == 1
        assert result[0]["name"] == "Team A"
        assert result[0]["positions"]["QB"]["vs_median"] == 5.0
        assert result[0]["positions"]["QB"]["points"] == 25.0
        assert "color" in result[0]["positions"]["QB"]
        assert "text_color" in result[0]["positions"]["QB"]

    def test_prepare_season_position_rankings_empty_data(self):
        """Empty data should return empty list."""
        data = {"season_context": {}}
        result = self.generator._prepare_season_position_rankings(data, self.team_logos)
        assert result == []

    def test_prepare_season_strength_percentages_empty_data(self):
        """Empty data should return empty list."""
        data = {"season_context": {}}
        result = self.generator._prepare_season_strength_percentages(data, self.team_logos)
        assert result == []
