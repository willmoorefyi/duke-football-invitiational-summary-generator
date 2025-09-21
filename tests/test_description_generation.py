import pytest
from src.generators.templated_html_generator import TemplatedFantasyHTMLGenerator


class TestDescriptionGeneration:
    """Test suite for description generation during HTML rendering."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TemplatedFantasyHTMLGenerator()

    def test_mccollapse_description_generation(self):
        """Test that McCollapse descriptions are generated correctly during HTML rendering."""
        # Sample data with honorable mention (no description field in JSON)
        data = {
            "matchups": [],
            "awards": {
                "mvp": None,
                "honorable_mentions": [
                    {
                        "award_type": "mccollapse",
                        "award_name": "Mike McCoy \"McCollapse\" Award",
                        "team_name": "Test Team",
                        "opponent_name": "Opponent Team",
                        "opponent_score": 105.5,
                        "primary_stat": 90.0,  # actual_score
                        "secondary_stat": 125.0,  # optimal_score
                        "stat_difference": 35.0
                    }
                ]
            }
        }

        team_logos = {}

        # Call the method that prepares awards data
        awards_data = self.generator._prepare_awards_data(data, team_logos)

        # Verify description is generated correctly
        assert 'honorable_mentions' in awards_data
        assert len(awards_data['honorable_mentions']) == 1

        mention = awards_data['honorable_mentions'][0]
        assert mention['description'] == "scored 90.00 (vs. Optimal 125.00) against Opponent Team (105.50)"

    def test_clapper_collapse_description_generation(self):
        """Test that Clapper Collapse descriptions are generated correctly during HTML rendering."""
        # Sample data with honorable mention (no description field in JSON)
        data = {
            "matchups": [],
            "awards": {
                "mvp": None,
                "honorable_mentions": [
                    {
                        "award_type": "clapper_collapse",
                        "award_name": "Jason Garrett \"Applauding Failure\" Award",
                        "team_name": "Test Team",
                        "opponent_name": "Opponent Team",
                        "opponent_score": 88.0,
                        "primary_stat": 110.0,  # projected_score
                        "secondary_stat": 85.0,  # actual_score
                        "stat_difference": 25.0
                    }
                ]
            }
        }

        team_logos = {}

        # Call the method that prepares awards data
        awards_data = self.generator._prepare_awards_data(data, team_logos)

        # Verify description is generated correctly
        assert 'honorable_mentions' in awards_data
        assert len(awards_data['honorable_mentions']) == 1

        mention = awards_data['honorable_mentions'][0]
        assert mention['description'] == "scored 85.00 (vs. Projected 110.00) against Opponent Team (88.00)"

    def test_unknown_award_type_description_generation(self):
        """Test fallback description for unknown award types."""
        # Sample data with unknown award type
        data = {
            "matchups": [],
            "awards": {
                "mvp": None,
                "honorable_mentions": [
                    {
                        "award_type": "unknown_type",
                        "award_name": "Unknown Award",
                        "team_name": "Test Team",
                        "opponent_name": "Opponent Team",
                        "opponent_score": 88.0,
                        "primary_stat": 90.0,
                        "secondary_stat": 110.0,
                        "stat_difference": 20.0
                    }
                ]
            }
        }

        team_logos = {}

        # Call the method that prepares awards data
        awards_data = self.generator._prepare_awards_data(data, team_logos)

        # Verify fallback description is generated
        assert 'honorable_mentions' in awards_data
        assert len(awards_data['honorable_mentions']) == 1

        mention = awards_data['honorable_mentions'][0]
        assert mention['description'] == "vs. Opponent Team (88.00)"


if __name__ == "__main__":
    pytest.main([__file__])