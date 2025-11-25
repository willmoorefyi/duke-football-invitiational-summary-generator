import pytest
from src.models.data_models import Team, Division


class TestTeamModelRefactor:
    """Test the refactored Team model without ESPN-derived standings fields."""

    def test_team_model_basic_fields_only(self):
        """Test Team model with only the basic fields (no ESPN standings)."""
        team = Team(
            id=1,
            name="Test Team",
            abbreviation="TT",
            owner="Team Owner",
            division="East",
            logo="https://example.com/logo.png"
        )

        assert team.id == 1
        assert team.name == "Test Team"
        assert team.abbreviation == "TT"
        assert team.owner == "Team Owner"
        assert team.division == "East"
        assert team.logo == "https://example.com/logo.png"

    def test_team_model_without_logo(self):
        """Test Team model without optional logo field."""
        team = Team(
            id=2,
            name="Another Team",
            abbreviation="AT",
            owner="Another Owner",
            division="West"
        )

        assert team.id == 2
        assert team.name == "Another Team"
        assert team.logo is None

    def test_team_model_json_serialization(self):
        """Test that Team model can be serialized to JSON with ESPN standings fields."""
        team = Team(
            id=3,
            name="JSON Team",
            abbreviation="JT",
            owner="JSON Owner",
            division="North",
            logo="logo.jpg"
        )

        json_data = team.model_dump()

        # Team model now includes ESPN standings fields (fetched from ESPN API)
        expected_fields = {
            'id', 'name', 'abbreviation', 'owner', 'division', 'logo',
            'wins', 'losses', 'ties', 'points_for', 'points_against',
            'standing', 'playoff_pct', 'division_rank'
        }
        actual_fields = set(json_data.keys())

        assert actual_fields == expected_fields

        # Verify default values for standings fields
        assert json_data['wins'] == 0
        assert json_data['losses'] == 0
        assert json_data['ties'] == 0
        assert json_data['points_for'] == 0.0
        assert json_data['points_against'] == 0.0
        assert json_data['standing'] == 0
        assert json_data['playoff_pct'] == 0.0
        assert json_data['division_rank'] is None

    def test_division_with_refactored_teams(self):
        """Test Division model works with refactored Team models that include ESPN standings."""
        team1 = Team(
            id=1, name="Team 1", abbreviation="T1",
            owner="Owner 1", division="East"
        )
        team2 = Team(
            id=2, name="Team 2", abbreviation="T2",
            owner="Owner 2", division="East"
        )

        division = Division(
            name="East",
            teams=[team1, team2]
        )

        assert division.name == "East"
        assert len(division.teams) == 2
        assert division.teams[0].name == "Team 1"
        assert division.teams[1].name == "Team 2"

        # Verify teams have standings fields with default values
        for team in division.teams:
            team_dict = team.model_dump()
            espn_fields = {'wins', 'losses', 'ties', 'points_for', 'points_against', 'standing', 'playoff_pct', 'division_rank'}
            # All ESPN fields should be present
            assert all(field in team_dict for field in espn_fields)


if __name__ == "__main__":
    pytest.main([__file__])