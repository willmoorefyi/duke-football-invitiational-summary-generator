import pytest
from datetime import datetime
from src.models.data_models import (
    Team, Player, Matchup, Division, InjuredStarter, 
    WeeklyReport, InjuryStatus
)


class TestDataModels:
    """Test suite for data model validation and serialization."""
    
    def test_team_model(self):
        """Test Team model creation and validation."""
        team = Team(
            id=1,
            name="Test Team",
            abbreviation="TEST",
            owner="Test Owner",
            division="East",
            wins=5,
            losses=3,
            ties=0,
            points_for=850.5,
            points_against=780.2,
            division_rank=1
        )
        
        assert team.id == 1
        assert team.name == "Test Team"
        assert team.division_rank == 1
    
    def test_player_model(self):
        """Test Player model creation and validation."""
        player = Player(
            name="Test Player",
            position="QB",
            team="Test Team",
            projected_score=18.5,
            actual_score=22.3,
            is_starter=True,
            injury_status=InjuryStatus.HEALTHY
        )
        
        assert player.name == "Test Player"
        assert player.position == "QB"
        assert player.is_starter is True
        assert player.injury_status == InjuryStatus.HEALTHY
    
    def test_matchup_model(self):
        """Test Matchup model creation and validation."""
        home_team = Team(
            id=1, name="Home Team", abbreviation="HOME", owner="Owner1",
            division="East", wins=5, losses=3, ties=0, points_for=850.5,
            points_against=780.2, division_rank=1
        )
        
        away_team = Team(
            id=2, name="Away Team", abbreviation="AWAY", owner="Owner2",
            division="West", wins=4, losses=4, ties=0, points_for=800.0,
            points_against=820.0, division_rank=2
        )
        
        matchup = Matchup(
            week=5,
            home_team=home_team,
            away_team=away_team,
            home_score=120.5,
            away_score=115.2,
            winner_id=1,
            loser_id=2,
            is_complete=True,
            players=[]
        )
        
        assert matchup.week == 5
        assert matchup.home_score == 120.5
        assert matchup.winner_id == 1
        assert matchup.is_complete is True
    
    def test_weekly_report_model(self):
        """Test WeeklyReport model creation and serialization."""
        # Create sample data
        team = Team(
            id=1, name="Test Team", abbreviation="TEST", owner="Owner",
            division="East", wins=5, losses=3, ties=0, points_for=850.5,
            points_against=780.2, division_rank=1
        )
        
        division = Division(name="East", teams=[team])
        
        matchup = Matchup(
            week=5, home_team=team, away_team=team, home_score=120.5,
            away_score=115.2, winner_id=1, loser_id=None, is_complete=True,
            players=[]
        )
        
        injured_starter = InjuredStarter(
            player_name="Injured Player",
            team_name="Test Team",
            position="RB",
            injury_status=InjuryStatus.QUESTIONABLE
        )
        
        report = WeeklyReport(
            league_id=123456,
            league_name="Test League",
            season=2024,
            week=5,
            report_date=datetime(2024, 10, 15),
            divisions=[division],
            matchups=[matchup],
            injured_starters=[injured_starter]
        )
        
        assert report.league_id == 123456
        assert report.week == 5
        assert len(report.divisions) == 1
        assert len(report.matchups) == 1
        assert len(report.injured_starters) == 1
    
    def test_injury_status_enum(self):
        """Test InjuryStatus enum values."""
        assert InjuryStatus.HEALTHY == "HEALTHY"
        assert InjuryStatus.QUESTIONABLE == "QUESTIONABLE"
        assert InjuryStatus.OUT == "OUT"
        assert InjuryStatus.IR == "IR"
    
    def test_model_json_serialization(self):
        """Test that models can be serialized to JSON."""
        team = Team(
            id=1, name="Test Team", abbreviation="TEST", owner="Owner",
            division="East", wins=5, losses=3, ties=0, points_for=850.5,
            points_against=780.2, division_rank=1
        )
        
        # Test JSON serialization
        json_data = team.model_dump(mode='json')
        assert isinstance(json_data, dict)
        assert json_data['id'] == 1
        assert json_data['name'] == "Test Team"
        
        # Test deserialization
        new_team = Team.model_validate(json_data)
        assert new_team.id == team.id
        assert new_team.name == team.name


if __name__ == "__main__":
    pytest.main([__file__])