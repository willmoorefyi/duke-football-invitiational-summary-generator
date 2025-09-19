import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from src.fantasy_extractor import FantasyFootballExtractor
from src.models.data_models import (
    Team, Player, Matchup, WeeklyAwards, InjuryStatus,
    PlayerAward, TeamAward, LineupEfficiencyAward, CollapseAward, ProjectionFailAward, HonorableMention
)


class TestAwardCalculations:
    """Test suite for award calculation negative cases and edge scenarios."""
    
    def setup_method(self):
        """Set up test fixtures for each test method."""
        # Mock the ESPN client creation to avoid actual API calls
        with patch('src.fantasy_extractor.create_espn_client') as mock_client:
            mock_espn_client = Mock()
            mock_client.return_value = mock_espn_client
            
            # Create extractor with mocked ESPN client
            self.extractor = FantasyFootballExtractor(league_id=12345, year=2024)
            self.extractor.logger = Mock()  # Mock the logger to avoid logging during tests
    
    def create_sample_team(self, team_id: int, name: str, division: str = "East") -> Team:
        """Helper method to create a sample team."""
        return Team(
            id=team_id,
            name=name,
            abbreviation=name[:4].upper(),
            owner=f"{name} Owner",
            division=division,
            wins=5,
            losses=3,
            ties=0,
            points_for=850.5,
            points_against=780.2,
            overall_rank=team_id,
            division_rank=team_id
        )
    
    def create_sample_player(self, name: str, team_name: str, position: str = "QB", 
                           is_starter: bool = True, actual_score: float = 15.0,
                           projected_score: float = 18.0, 
                           injury_status: InjuryStatus = InjuryStatus.HEALTHY) -> Player:
        """Helper method to create a sample player."""
        return Player(
            name=name,
            position=position,
            team=team_name,
            projected_score=projected_score,
            actual_score=actual_score,
            is_starter=is_starter,
            injury_status=injury_status
        )
    
    def test_no_winning_teams_mvp_case(self):
        """Test MVP award when there are no winning teams (all ties or incomplete matchups)."""
        team1 = self.create_sample_team(1, "Team One")
        team2 = self.create_sample_team(2, "Team Two")
        
        # Create matchup with no winner (tie or incomplete)
        matchup = Matchup(
            week=1,
            home_team=team1,
            away_team=team2,
            home_score=100.0,
            away_score=100.0,  # Tie score
            winner_id=None,  # No winner
            loser_id=None,
            is_complete=True,
            players=[
                self.create_sample_player("Player 1", "Team One", actual_score=25.0),
                self.create_sample_player("Player 2", "Team Two", actual_score=20.0)
            ]
        )
        
        awards = self.extractor._calculate_weekly_awards([matchup])
        
        # No MVP should be awarded since there are no winning teams
        assert awards.mvp is None
    
    def test_no_losing_teams_mwp_case(self):
        """Test MWP award when there are no losing teams (all ties)."""
        team1 = self.create_sample_team(1, "Team One")
        team2 = self.create_sample_team(2, "Team Two")
        
        matchup = Matchup(
            week=1,
            home_team=team1,
            away_team=team2,
            home_score=100.0,
            away_score=100.0,  # Tie
            winner_id=None,
            loser_id=None,
            is_complete=True,
            players=[
                self.create_sample_player("Player 1", "Team One", actual_score=25.0),
                self.create_sample_player("Player 2", "Team Two", actual_score=20.0)
            ]
        )
        
        awards = self.extractor._calculate_weekly_awards([matchup])
        
        # No MWP should be awarded since there are no losing teams
        assert awards.mwp is None
    
    def test_no_healthy_starters_mup_case(self):
        """Test MUP award when all starters are injured."""
        team1 = self.create_sample_team(1, "Team One")
        team2 = self.create_sample_team(2, "Team Two")
        
        matchup = Matchup(
            week=1,
            home_team=team1,
            away_team=team2,
            home_score=110.0,
            away_score=95.0,
            winner_id=1,
            loser_id=2,
            is_complete=True,
            players=[
                # All starters are injured
                self.create_sample_player("Injured QB", "Team One", actual_score=5.0, 
                                        injury_status=InjuryStatus.OUT),
                self.create_sample_player("Injured RB", "Team Two", actual_score=3.0,
                                        injury_status=InjuryStatus.QUESTIONABLE),
                # Bench players are healthy but not starters
                self.create_sample_player("Bench Player", "Team One", actual_score=15.0,
                                        is_starter=False, injury_status=InjuryStatus.HEALTHY)
            ]
        )
        
        awards = self.extractor._calculate_weekly_awards([matchup])
        
        # No MUP should be awarded since there are no healthy starters
        assert awards.mup is None
    
    def test_no_bench_players_mdp_case(self):
        """Test MDP award when there are no bench players (all players are starters)."""
        team1 = self.create_sample_team(1, "Team One")
        team2 = self.create_sample_team(2, "Team Two")
        
        matchup = Matchup(
            week=1,
            home_team=team1,
            away_team=team2,
            home_score=110.0,
            away_score=95.0,
            winner_id=1,
            loser_id=2,
            is_complete=True,
            players=[
                # All players are starters, no bench players
                self.create_sample_player("Starter 1", "Team One", actual_score=25.0, is_starter=True),
                self.create_sample_player("Starter 2", "Team One", actual_score=20.0, is_starter=True),
                self.create_sample_player("Starter 3", "Team Two", actual_score=15.0, is_starter=True),
                self.create_sample_player("Starter 4", "Team Two", actual_score=10.0, is_starter=True)
            ]
        )
        
        awards = self.extractor._calculate_weekly_awards([matchup])
        
        # No MDP should be awarded since there are no bench players
        assert awards.mdp is None
    
    def test_no_losing_teams_hsl_case(self):
        """Test HSL award when there are no losing teams."""
        team1 = self.create_sample_team(1, "Team One")
        team2 = self.create_sample_team(2, "Team Two")
        
        matchup = Matchup(
            week=1,
            home_team=team1,
            away_team=team2,
            home_score=100.0,
            away_score=100.0,  # Tie
            winner_id=None,
            loser_id=None,
            is_complete=True,
            players=[]
        )
        
        awards = self.extractor._calculate_weekly_awards([matchup])
        
        # No HSL should be awarded since there are no losing teams
        assert awards.hsl is None
    
    def test_no_winning_teams_lsw_case(self):
        """Test LSW award when there are no winning teams."""
        team1 = self.create_sample_team(1, "Team One")
        team2 = self.create_sample_team(2, "Team Two")
        
        matchup = Matchup(
            week=1,
            home_team=team1,
            away_team=team2,
            home_score=100.0,
            away_score=100.0,  # Tie
            winner_id=None,
            loser_id=None,
            is_complete=True,
            players=[]
        )
        
        awards = self.extractor._calculate_weekly_awards([matchup])
        
        # No LSW should be awarded since there are no winning teams
        assert awards.lsw is None
    
    def test_no_optimal_scores_ssl_case(self):
        """Test SSL award when no teams have optimal scores calculated."""
        team1 = self.create_sample_team(1, "Team One")
        team2 = self.create_sample_team(2, "Team Two")
        
        matchup = Matchup(
            week=1,
            home_team=team1,
            away_team=team2,
            home_score=110.0,
            away_score=95.0,
            home_optimal_score=None,  # No optimal scores
            away_optimal_score=None,
            winner_id=1,
            loser_id=2,
            is_complete=True,
            players=[]
        )
        
        awards = self.extractor._calculate_weekly_awards([matchup])
        
        # No SSL should be awarded since there are no optimal scores
        assert awards.ssl is None
    
    def test_no_losing_teams_with_optimal_scores_ifm_case(self):
        """Test IFM award when no losing teams have optimal scores."""
        team1 = self.create_sample_team(1, "Team One")
        team2 = self.create_sample_team(2, "Team Two")
        
        matchup = Matchup(
            week=1,
            home_team=team1,
            away_team=team2,
            home_score=110.0,
            away_score=95.0,
            home_optimal_score=115.0,  # Winner has optimal score
            away_optimal_score=None,   # Loser has no optimal score
            winner_id=1,
            loser_id=2,
            is_complete=True,
            players=[]
        )
        
        awards = self.extractor._calculate_weekly_awards([matchup])
        
        # No IFM should be awarded since losing team has no optimal score
        assert awards.ifm is None
    
    def test_no_winning_teams_with_optimal_scores_accidental_genius_case(self):
        """Test Accidental Genius award when winning teams have no optimal scores."""
        team1 = self.create_sample_team(1, "Team One")
        team2 = self.create_sample_team(2, "Team Two")
        
        matchup = Matchup(
            week=1,
            home_team=team1,
            away_team=team2,
            home_score=110.0,
            away_score=95.0,
            home_optimal_score=None,   # Winner has no optimal score
            away_optimal_score=120.0,  # Loser has optimal score
            winner_id=1,
            loser_id=2,
            is_complete=True,
            players=[]
        )
        
        awards = self.extractor._calculate_weekly_awards([matchup])
        
        # No Accidental Genius should be awarded since winning team has no optimal score
        assert awards.accidental_genius is None
    
    def test_no_mccollapse_scenarios(self):
        """Test McCollapse award when no teams would have won with optimal lineup."""
        team1 = self.create_sample_team(1, "Team One")
        team2 = self.create_sample_team(2, "Team Two")
        
        # Scenario 1: Losing team's optimal score still wouldn't beat winner
        matchup1 = Matchup(
            week=1,
            home_team=team1,
            away_team=team2,
            home_score=110.0,
            away_score=95.0,
            home_optimal_score=115.0,
            away_optimal_score=105.0,  # Still less than home_score
            winner_id=1,
            loser_id=2,
            is_complete=True,
            players=[]
        )
        
        # Scenario 2: No optimal scores available
        team3 = self.create_sample_team(3, "Team Three")
        team4 = self.create_sample_team(4, "Team Four")
        
        matchup2 = Matchup(
            week=1,
            home_team=team3,
            away_team=team4,
            home_score=100.0,
            away_score=85.0,
            home_optimal_score=None,
            away_optimal_score=None,
            winner_id=3,
            loser_id=4,
            is_complete=True,
            players=[]
        )
        
        awards = self.extractor._calculate_weekly_awards([matchup1, matchup2])
        
        # No McCollapse awards should be given
        assert awards.mccollapse is None
    
    def test_no_clapper_collapse_scenarios(self):
        """Test Clapper Collapse award when no teams were projected to win but lost."""
        team1 = self.create_sample_team(1, "Team One")
        team2 = self.create_sample_team(2, "Team Two")
        
        # Scenario 1: Winner was correctly projected to win
        matchup1 = Matchup(
            week=1,
            home_team=team1,
            away_team=team2,
            home_score=110.0,
            away_score=95.0,
            home_projected_score=115.0,  # Higher projection
            away_projected_score=100.0,  # Lower projection
            winner_id=1,  # Home team won as projected
            loser_id=2,
            is_complete=True,
            players=[]
        )
        
        # Scenario 2: No projected scores available
        team3 = self.create_sample_team(3, "Team Three")
        team4 = self.create_sample_team(4, "Team Four")
        
        matchup2 = Matchup(
            week=1,
            home_team=team3,
            away_team=team4,
            home_score=100.0,
            away_score=85.0,
            home_projected_score=None,
            away_projected_score=None,
            winner_id=3,
            loser_id=4,
            is_complete=True,
            players=[]
        )
        
        awards = self.extractor._calculate_weekly_awards([matchup1, matchup2])
        
        # No Clapper Collapse awards should be given
        assert awards.clapper_collapse is None
    
    def test_empty_matchups_list(self):
        """Test award calculations with an empty matchups list."""
        awards = self.extractor._calculate_weekly_awards([])
        
        # All awards should be None or empty lists
        assert awards.mvp is None
        assert awards.mwp is None
        assert awards.mup is None
        assert awards.mdp is None
        assert awards.hsl is None
        assert awards.lsw is None
        assert awards.ssl is None
        assert awards.ifm is None
        assert awards.accidental_genius is None
        assert awards.mccollapse is None
        assert awards.clapper_collapse is None
    
    def test_matchups_with_no_players(self):
        """Test award calculations when matchups have no player data."""
        team1 = self.create_sample_team(1, "Team One")
        team2 = self.create_sample_team(2, "Team Two")
        
        matchup = Matchup(
            week=1,
            home_team=team1,
            away_team=team2,
            home_score=110.0,
            away_score=95.0,
            winner_id=1,
            loser_id=2,
            is_complete=True,
            players=[]  # No players
        )
        
        awards = self.extractor._calculate_weekly_awards([matchup])
        
        # Player-based awards should be None
        assert awards.mvp is None
        assert awards.mwp is None
        assert awards.mup is None
        assert awards.mdp is None
        
        # Team-based awards should still work
        assert awards.hsl is not None  # Highest scoring loser
        assert awards.lsw is not None  # Lowest scoring winner
    
    def test_zero_optimal_scores_edge_case(self):
        """Test award calculations when optimal scores are zero."""
        team1 = self.create_sample_team(1, "Team One")
        team2 = self.create_sample_team(2, "Team Two")
        
        matchup = Matchup(
            week=1,
            home_team=team1,
            away_team=team2,
            home_score=110.0,
            away_score=95.0,
            home_optimal_score=0.0,  # Zero optimal score
            away_optimal_score=0.0,  # Zero optimal score
            winner_id=1,
            loser_id=2,
            is_complete=True,
            players=[]
        )
        
        awards = self.extractor._calculate_weekly_awards([matchup])
        
        # SSL and IFM should be None since optimal scores are zero (division by zero)
        assert awards.ssl is None
        assert awards.ifm is None
        assert awards.accidental_genius is None

    def test_mccollapse_honorable_mentions_single_team(self):
        """Test McCollapse with only one eligible team - no honorable mentions."""
        team1 = self.create_sample_team(1, "Team One")
        team2 = self.create_sample_team(2, "Team Two")

        matchup = Matchup(
            week=1,
            home_team=team1,
            away_team=team2,
            home_score=85.0,
            away_score=110.0,
            home_optimal_score=120.0,  # Would have won with optimal
            away_optimal_score=95.0,
            winner_id=2,
            loser_id=1,
            is_complete=True,
            players=[]
        )

        awards = self.extractor._calculate_weekly_awards([matchup])

        # Should have one McCollapse award and no honorable mentions
        assert awards.mccollapse is not None
        assert awards.mccollapse.team_name == "Team One"
        assert len(awards.honorable_mentions) == 0

    def test_mccollapse_honorable_mentions_multiple_teams(self):
        """Test McCollapse with multiple eligible teams - creates honorable mentions."""
        team1 = self.create_sample_team(1, "Team One")
        team2 = self.create_sample_team(2, "Team Two")
        team3 = self.create_sample_team(3, "Team Three")
        team4 = self.create_sample_team(4, "Team Four")

        # Two matchups where losing teams would have won with optimal
        matchup1 = Matchup(
            week=1,
            home_team=team1,
            away_team=team2,
            home_score=85.0,  # Lost by 25
            away_score=110.0,
            home_optimal_score=140.0,  # Optimal - actual = 55 (highest difference)
            away_optimal_score=95.0,
            winner_id=2,
            loser_id=1,
            is_complete=True,
            players=[]
        )

        matchup2 = Matchup(
            week=1,
            home_team=team3,
            away_team=team4,
            home_score=90.0,
            away_score=95.0,  # Lost by 5
            home_optimal_score=120.0,  # Optimal - actual = 30 (lower difference)
            away_optimal_score=85.0,
            winner_id=4,
            loser_id=3,
            is_complete=True,
            players=[]
        )

        awards = self.extractor._calculate_weekly_awards([matchup1, matchup2])

        # Should have one main award (team with highest difference) and one honorable mention
        assert awards.mccollapse is not None
        assert awards.mccollapse.team_name == "Team One"  # Highest difference (55)

        # Should have one honorable mention for the second team
        assert len(awards.honorable_mentions) == 1
        mention = awards.honorable_mentions[0]
        assert mention.award_type == "mccollapse"
        assert mention.award_name == 'Mike McCoy "McCollapse" Award'
        assert mention.team_name == "Team Three"
        assert mention.opponent_name == "Team Four"
        assert mention.opponent_score == 95.0
        assert mention.primary_stat == 90.0  # actual_score
        assert mention.secondary_stat == 120.0  # optimal_score
        assert mention.stat_difference == 30.0  # optimal - actual
        assert mention.description == "Actual: 90.00, vs. Optimal: 120.00"

    def test_clapper_collapse_honorable_mentions_single_team(self):
        """Test Clapper Collapse with only one eligible team - no honorable mentions."""
        team1 = self.create_sample_team(1, "Team One")
        team2 = self.create_sample_team(2, "Team Two")

        matchup = Matchup(
            week=1,
            home_team=team1,
            away_team=team2,
            home_score=85.0,
            away_score=110.0,
            home_projected_score=120.0,  # Projected to win but lost
            away_projected_score=95.0,
            winner_id=2,
            loser_id=1,
            is_complete=True,
            players=[]
        )

        awards = self.extractor._calculate_weekly_awards([matchup])

        # Should have one Clapper award and no honorable mentions
        assert awards.clapper_collapse is not None
        assert awards.clapper_collapse.team_name == "Team One"
        assert len(awards.honorable_mentions) == 0

    def test_clapper_collapse_honorable_mentions_multiple_teams(self):
        """Test Clapper Collapse with multiple eligible teams - creates honorable mentions."""
        team1 = self.create_sample_team(1, "Team One")
        team2 = self.create_sample_team(2, "Team Two")
        team3 = self.create_sample_team(3, "Team Three")
        team4 = self.create_sample_team(4, "Team Four")

        # Two matchups where teams projected to win but lost
        matchup1 = Matchup(
            week=1,
            home_team=team1,
            away_team=team2,
            home_score=75.0,
            away_score=110.0,
            home_projected_score=125.0,  # Projected - actual = 50 (highest difference)
            away_projected_score=95.0,
            winner_id=2,
            loser_id=1,
            is_complete=True,
            players=[]
        )

        matchup2 = Matchup(
            week=1,
            home_team=team3,
            away_team=team4,
            home_score=85.0,
            away_score=95.0,
            home_projected_score=105.0,  # Projected - actual = 20 (lower difference)
            away_projected_score=80.0,
            winner_id=4,
            loser_id=3,
            is_complete=True,
            players=[]
        )

        awards = self.extractor._calculate_weekly_awards([matchup1, matchup2])

        # Should have one main award (team with highest difference) and one honorable mention
        assert awards.clapper_collapse is not None
        assert awards.clapper_collapse.team_name == "Team One"  # Highest difference (50)

        # Should have one honorable mention for the second team
        assert len(awards.honorable_mentions) == 1
        mention = awards.honorable_mentions[0]
        assert mention.award_type == "clapper_collapse"
        assert mention.award_name == 'Jason Garrett "Applauding Failure" Award'
        assert mention.team_name == "Team Three"
        assert mention.opponent_name == "Team Four"
        assert mention.opponent_score == 95.0
        assert mention.primary_stat == 105.0  # projected_score
        assert mention.secondary_stat == 85.0  # actual_score
        assert mention.stat_difference == 20.0  # projected - actual
        assert mention.description == "Projected: 105.00, vs. Actual: 85.00"

    def test_mixed_honorable_mentions(self):
        """Test scenario with both McCollapse and Clapper honorable mentions."""
        team1 = self.create_sample_team(1, "Team One")
        team2 = self.create_sample_team(2, "Team Two")
        team3 = self.create_sample_team(3, "Team Three")
        team4 = self.create_sample_team(4, "Team Four")
        team5 = self.create_sample_team(5, "Team Five")
        team6 = self.create_sample_team(6, "Team Six")

        # McCollapse scenarios (2 teams)
        matchup1 = Matchup(
            week=1,
            home_team=team1,
            away_team=team2,
            home_score=80.0,
            away_score=100.0,
            home_optimal_score=150.0,  # Difference: 70 (highest)
            away_optimal_score=85.0,
            winner_id=2,
            loser_id=1,
            is_complete=True,
            players=[]
        )

        matchup2 = Matchup(
            week=1,
            home_team=team3,
            away_team=team4,
            home_score=90.0,
            away_score=95.0,
            home_optimal_score=130.0,  # Difference: 40
            away_optimal_score=85.0,
            winner_id=4,
            loser_id=3,
            is_complete=True,
            players=[]
        )

        # Clapper scenarios (2 teams)
        matchup3 = Matchup(
            week=1,
            home_team=team5,
            away_team=team6,
            home_score=70.0,
            away_score=105.0,
            home_projected_score=140.0,  # Difference: 70 (highest)
            away_projected_score=90.0,
            winner_id=6,
            loser_id=5,
            is_complete=True,
            players=[]
        )

        matchup4 = Matchup(
            week=1,
            home_team=team1,  # Reuse team1 in different matchup for clapper
            away_team=team3,
            home_score=85.0,
            away_score=90.0,
            home_projected_score=110.0,  # Difference: 25
            away_projected_score=80.0,
            winner_id=3,
            loser_id=1,
            is_complete=True,
            players=[]
        )

        awards = self.extractor._calculate_weekly_awards([matchup1, matchup2, matchup3, matchup4])

        # Should have one of each main award
        assert awards.mccollapse is not None
        assert awards.mccollapse.team_name == "Team One"  # Highest McCollapse difference

        assert awards.clapper_collapse is not None
        assert awards.clapper_collapse.team_name == "Team Five"  # Highest Clapper difference

        # Should have 2 honorable mentions (1 for each award type)
        assert len(awards.honorable_mentions) == 2

        # Find the mentions by award type
        mccollapse_mention = next(m for m in awards.honorable_mentions if m.award_type == "mccollapse")
        clapper_mention = next(m for m in awards.honorable_mentions if m.award_type == "clapper_collapse")

        # Verify McCollapse honorable mention
        assert mccollapse_mention.team_name == "Team Three"
        assert mccollapse_mention.opponent_name == "Team Four"
        assert mccollapse_mention.stat_difference == 40.0

        # Verify Clapper honorable mention
        assert clapper_mention.team_name == "Team One"  # Same team can have different award types
        assert clapper_mention.opponent_name == "Team Three"
        assert clapper_mention.stat_difference == 25.0


if __name__ == "__main__":
    pytest.main([__file__])