import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from src.fantasy_extractor import FantasyFootballExtractor
from src.models.data_models import (
    Team, Player, Matchup, WeeklyAwards, InjuryStatus,
    PlayerAward, TeamAward, LineupEfficiencyAward, CollapseAward, ProjectionFailAward
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
        assert len(awards.mccollapse) == 0
    
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
        assert len(awards.clapper_collapse) == 0
    
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
        assert len(awards.mccollapse) == 0
        assert len(awards.clapper_collapse) == 0
    
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


if __name__ == "__main__":
    pytest.main([__file__])