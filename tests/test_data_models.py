import pytest
from datetime import datetime
from src.models.data_models import (
    Team, Player, Matchup, Division, InjuredStarter,
    WeeklyReport, InjuryStatus, WeeklyAwards, PlayerAward,
    TeamAward, LineupEfficiencyAward, CollapseAward, ProjectionFailAward,
    HonorableMention
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
            logo="https://example.com/logo.png"
        )
        
        assert team.id == 1
        assert team.name == "Test Team"
        assert team.abbreviation == "TEST"
        assert team.owner == "Test Owner"
        assert team.division == "East"
        assert team.logo == "https://example.com/logo.png"
        
        # Test that logo is optional
        team_without_logo = Team(
            id=2,
            name="Team Without Logo",
            abbreviation="TWL",
            owner="Another Owner",
            division="West"
        )
        
        assert team_without_logo.logo is None
    
    def test_player_model(self):
        """Test Player model creation and validation."""
        player = Player(
            name="Test Player",
            position="QB",
            roster_slot="OP",
            team="Test Team",
            projected_score=18.5,
            actual_score=22.3,
            is_starter=True,
            injury_status=InjuryStatus.HEALTHY
        )
        
        assert player.name == "Test Player"
        assert player.position == "QB"
        assert player.roster_slot == "OP"
        assert player.is_starter is True
        assert player.injury_status == InjuryStatus.HEALTHY
        
        # Test that roster_slot and should_have_started are optional
        player_without_slot = Player(
            name="Bench Player",
            position="RB",
            team="Test Team",
            projected_score=10.0,
            actual_score=8.5,
            is_starter=False,
            injury_status=InjuryStatus.HEALTHY
        )
        
        assert player_without_slot.roster_slot is None
        assert player_without_slot.should_have_started is None
    
    def test_matchup_model(self):
        """Test Matchup model creation and validation."""
        home_team = Team(
            id=1, name="Home Team", abbreviation="HOME", owner="Owner1",
            division="East", wins=5, losses=3, ties=0, points_for=850.5,
            points_against=780.2, overall_rank=1, division_rank=1
        )
        
        away_team = Team(
            id=2, name="Away Team", abbreviation="AWAY", owner="Owner2",
            division="West", wins=4, losses=4, ties=0, points_for=800.0,
            points_against=820.0, overall_rank=2, division_rank=2
        )
        
        matchup = Matchup(
            week=5,
            home_team=home_team,
            away_team=away_team,
            home_score=120.5,
            away_score=115.2,
            home_projected_score=118.0,
            away_projected_score=112.5,
            winner_id=1,
            loser_id=2,
            is_complete=True,
            players=[]
        )
        
        assert matchup.week == 5
        assert matchup.home_score == 120.5
        assert matchup.home_projected_score == 118.0
        assert matchup.away_projected_score == 112.5
        assert matchup.winner_id == 1
        assert matchup.is_complete is True
    
    def test_weekly_report_model(self):
        """Test WeeklyReport model creation and serialization."""
        # Create sample data
        team = Team(
            id=1, name="Test Team", abbreviation="TEST", owner="Owner",
            division="East", wins=5, losses=3, ties=0, points_for=850.5,
            points_against=780.2, overall_rank=1, division_rank=1
        )
        
        division = Division(name="East", teams=[team])
        
        matchup = Matchup(
            week=5, home_team=team, away_team=team, home_score=120.5,
            away_score=115.2, home_projected_score=118.0, away_projected_score=112.5,
            winner_id=1, loser_id=None, is_complete=True, players=[]
        )
        
        injured_starter = InjuredStarter(
            player_name="Injured Player",
            team_name="Test Team",
            position="RB",
            injury_status=InjuryStatus.QUESTIONABLE
        )
        
        awards = WeeklyAwards()  # Empty awards for test
        
        report = WeeklyReport(
            league_id=123456,
            league_name="Test League",
            season=2024,
            week=5,
            report_date=datetime(2024, 10, 15),
            divisions=[division],
            matchups=[matchup],
            injured_starters=[injured_starter],
            awards=awards
        )
        
        assert report.league_id == 123456
        assert report.week == 5
        assert len(report.divisions) == 1
        assert len(report.matchups) == 1
        assert len(report.injured_starters) == 1
        assert report.awards is not None
    
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
            points_against=780.2, overall_rank=1, division_rank=1
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


    def test_weekly_awards_negative_cases(self):
        """Test that WeeklyAwards handles negative cases where no teams fit award criteria."""
        
        # Test empty awards object
        empty_awards = WeeklyAwards()
        assert empty_awards.mvp is None
        assert empty_awards.mwp is None
        assert empty_awards.mup is None
        assert empty_awards.mdp is None
        assert empty_awards.hsl is None
        assert empty_awards.lsw is None
        assert empty_awards.ssl is None
        assert empty_awards.ifm is None
        assert empty_awards.accidental_genius is None
        assert empty_awards.mccollapse is None
        assert empty_awards.clapper_collapse is None

        # Test that all award fields are properly optional
        assert isinstance(empty_awards.honorable_mentions, list)
        assert len(empty_awards.honorable_mentions) == 0
    
    def test_weekly_awards_with_all_awards_populated(self):
        """Test WeeklyAwards with all award types populated to ensure the model works correctly."""
        
        # Create sample awards for each type
        mvp_award = PlayerAward(
            player_name="MVP Player",
            team_name="Winning Team",
            position="QB",
            score=25.5
        )
        
        mwp_award = PlayerAward(
            player_name="MWP Player", 
            team_name="Losing Team",
            position="RB",
            score=22.3
        )
        
        mup_award = PlayerAward(
            player_name="MUP Player",
            team_name="Bad Team", 
            position="K",
            score=2.1
        )
        
        mdp_award = PlayerAward(
            player_name="MDP Player",
            team_name="Some Team",
            position="WR", 
            score=18.7
        )
        
        hsl_award = TeamAward(
            team_name="High Scoring Loser",
            score=145.2,
            additional_info="Unlucky loss"
        )
        
        lsw_award = TeamAward(
            team_name="Low Scoring Winner",
            score=87.5,
            additional_info="Lucky win"
        )
        
        ssl_award = LineupEfficiencyAward(
            team_name="Smart Team",
            actual_score=120.5,
            optimal_score=122.1,
            efficiency_percentage=98.7,
            additional_info="Nearly perfect lineup"
        )
        
        ifm_award = LineupEfficiencyAward(  
            team_name="Dumb Team",
            actual_score=85.2,
            optimal_score=145.8,
            efficiency_percentage=58.4,
            additional_info="Would have won with optimal lineup: True"
        )
        
        genius_award = LineupEfficiencyAward(
            team_name="Lucky Team", 
            actual_score=95.3,
            optimal_score=130.2,
            efficiency_percentage=73.2,
            additional_info="Won despite suboptimal lineup"
        )
        
        mccollapse_award = CollapseAward(
            team_name="Collapse Team",
            actual_score=98.5,
            optimal_score=135.7,
            opponent_score=105.2,
            points_difference=30.5
        )
        
        clapper_award = ProjectionFailAward(
            team_name="Projection Fail Team",
            projected_score=118.5,
            actual_score=89.2,
            opponent_projected_score=112.3,
            opponent_actual_score=94.8
        )
        
        # Create awards object with all awards populated
        full_awards = WeeklyAwards(
            mvp=mvp_award,
            mwp=mwp_award, 
            mup=mup_award,
            mdp=mdp_award,
            hsl=hsl_award,
            lsw=lsw_award,
            ssl=ssl_award,
            ifm=ifm_award,
            accidental_genius=genius_award,
            mccollapse=mccollapse_award,
            clapper_collapse=clapper_award
        )
        
        # Verify all awards are properly set
        assert full_awards.mvp == mvp_award
        assert full_awards.mwp == mwp_award
        assert full_awards.mup == mup_award
        assert full_awards.mdp == mdp_award
        assert full_awards.hsl == hsl_award
        assert full_awards.lsw == lsw_award
        assert full_awards.ssl == ssl_award
        assert full_awards.ifm == ifm_award
        assert full_awards.accidental_genius == genius_award
        assert full_awards.mccollapse == mccollapse_award
        assert full_awards.clapper_collapse == clapper_award
    
    def test_weekly_awards_partial_population(self):
        """Test WeeklyAwards with only some awards populated to simulate realistic scenarios."""
        
        # Scenario: Only player awards, no team collapse awards
        partial_awards = WeeklyAwards(
            mvp=PlayerAward(
                player_name="Solo MVP",
                team_name="Winning Team", 
                position="QB",
                score=28.3
            ),
            mup=PlayerAward(
                player_name="Solo MUP",
                team_name="Bad Team",
                position="K", 
                score=1.2
            )
            # Note: No mwp, mdp, hsl, lsw, ssl, ifm, accidental_genius, mccollapse, clapper_collapse
        )
        
        # Verify populated awards
        assert partial_awards.mvp is not None
        assert partial_awards.mvp.player_name == "Solo MVP"
        assert partial_awards.mup is not None
        assert partial_awards.mup.score == 1.2
        
        # Verify unpopulated awards are None or empty
        assert partial_awards.mwp is None
        assert partial_awards.mdp is None
        assert partial_awards.hsl is None
        assert partial_awards.lsw is None
        assert partial_awards.ssl is None
        assert partial_awards.ifm is None
        assert partial_awards.accidental_genius is None
        assert partial_awards.mccollapse is None
        assert partial_awards.clapper_collapse is None
        assert len(partial_awards.honorable_mentions) == 0
    
    def test_collapse_awards_with_honorable_mentions(self):
        """Test that collapse awards work as single objects with honorable mentions for runners-up."""

        mccollapse_award = CollapseAward(
            team_name="Main Collapse Team",
            actual_score=85.2,
            optimal_score=120.5,
            opponent_score=90.1,
            points_difference=30.4
        )

        clapper_award = ProjectionFailAward(
            team_name="Main Clapper Team",
            projected_score=125.0,
            actual_score=95.5,
            opponent_projected_score=118.2,
            opponent_actual_score=99.8
        )

        honorable_mention = HonorableMention(
            award_type="mccollapse",
            award_name='Mike McCoy "McCollapse" Award',
            team_name="Runner Up Team",
            opponent_name="Opponent Team",
            opponent_score=82.1,
            primary_stat=78.9,
            secondary_stat=115.3,
            stat_difference=36.4
        )

        awards_with_mentions = WeeklyAwards(
            mccollapse=mccollapse_award,
            clapper_collapse=clapper_award,
            honorable_mentions=[honorable_mention]
        )

        # Verify single main awards
        assert awards_with_mentions.mccollapse == mccollapse_award
        assert awards_with_mentions.clapper_collapse == clapper_award

        # Verify honorable mentions
        assert len(awards_with_mentions.honorable_mentions) == 1
        assert awards_with_mentions.honorable_mentions[0] == honorable_mention

        # Verify other awards are still None
        assert awards_with_mentions.mvp is None
        assert awards_with_mentions.ssl is None
        assert awards_with_mentions.ifm is None


if __name__ == "__main__":
    pytest.main([__file__])