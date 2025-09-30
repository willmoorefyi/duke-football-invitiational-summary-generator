import pytest
from src.generators.templated_html_generator import TemplatedFantasyHTMLGenerator


class TestHonorableMentionsThemeColors:
    """Test suite for honorable mentions team theme colors."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TemplatedFantasyHTMLGenerator()

    def test_honorable_mentions_include_team_theme_colors(self):
        """Test that honorable mentions include team theme colors and logos."""
        # Sample data with honorable mentions
        data = {
            "matchups": [
                {
                    "home_team": {"name": "Bad JuJu", "id": 1},
                    "away_team": {"name": "Moore's Law", "id": 2},
                    "home_score": 100.0,
                    "away_score": 105.0
                }
            ],
            "awards": {
                "mvp": None,
                "honorable_mentions": [
                    {
                        "award_type": "mccollapse",
                        "award_name": "Mike McCoy \"McCollapse\" Award",
                        "team_name": "Bad JuJu",
                        "opponent_name": "Moore's Law",
                        "opponent_score": 105.0,
                        "primary_stat": 100.0,  # actual_score
                        "secondary_stat": 130.0,  # optimal_score
                        "stat_difference": 30.0
                    },
                    {
                        "award_type": "clapper_collapse",
                        "award_name": "Jason Garrett \"Applauding Failure\" Award",
                        "team_name": "Moore's Law",
                        "opponent_name": "Bad JuJu",
                        "opponent_score": 100.0,
                        "primary_stat": 120.0,  # projected_score
                        "secondary_stat": 105.0,  # actual_score
                        "stat_difference": 15.0
                    }
                ]
            }
        }

        team_logos = {
            "Bad JuJu": "https://example.com/badjuju.png",
            "Moore's Law": "https://example.com/mooreslaw.png"
        }

        # Call the method that prepares awards data
        awards_data = self.generator._prepare_awards_data(data, team_logos)

        # Verify honorable mentions exist
        assert 'honorable_mentions' in awards_data
        assert len(awards_data['honorable_mentions']) == 2

        # Verify first honorable mention (Bad JuJu)
        mention1 = awards_data['honorable_mentions'][0]
        assert mention1['team_name'] == "Bad JuJu"
        assert 'team_bg_color' in mention1
        assert 'team_font_color' in mention1
        assert 'team_logo' in mention1

        # Verify Bad JuJu has the corrected background color (darkened red)
        assert mention1['team_bg_color'] == "rgb(180, 1, 22)"

        # Verify second honorable mention (Moore's Law)
        mention2 = awards_data['honorable_mentions'][1]
        assert mention2['team_name'] == "Moore's Law"
        assert 'team_bg_color' in mention2
        assert 'team_font_color' in mention2
        assert 'team_logo' in mention2

        # Verify Moore's Law has the corrected background color (darker gold)
        assert mention2['team_bg_color'] == "rgb(184, 134, 11)"

        # Verify descriptions are still generated correctly
        assert mention1['description'] == "scored 100.00 (vs. Optimal 130.00) against Moore's Law (105.00)"
        assert mention2['description'] == "scored 105.00 (vs. Projected 120.00) against Bad JuJu (100.00)"

    def test_honorable_mentions_team_logos_included(self):
        """Test that team logos are properly included in honorable mentions."""
        data = {
            "matchups": [],
            "awards": {
                "honorable_mentions": [
                    {
                        "award_type": "mccollapse",
                        "award_name": "Mike McCoy \"McCollapse\" Award",
                        "team_name": "Test Team",
                        "opponent_name": "Opponent",
                        "opponent_score": 100.0,
                        "primary_stat": 90.0,
                        "secondary_stat": 120.0,
                        "stat_difference": 30.0
                    }
                ]
            }
        }

        team_logos = {"Test Team": "https://example.com/testteam.png"}

        awards_data = self.generator._prepare_awards_data(data, team_logos)

        mention = awards_data['honorable_mentions'][0]
        assert 'team_logo' in mention
        # The logo should be rendered as HTML img tag
        assert '<img src="https://example.com/testteam.png"' in mention['team_logo']
        assert 'class="matchup-team-logo"' in mention['team_logo']


if __name__ == "__main__":
    pytest.main([__file__])