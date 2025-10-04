import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.pipeline.aggregate_stage import AggregateStage


class TestAggregateStageCondensed:
    """Test suite for condensed JSON generation in AggregateStage."""

    def setup_method(self):
        """Set up test fixtures."""
        self.aggregate_stage = AggregateStage(league_id=380491)

        # Sample enhanced data structure
        self.sample_enhanced_data = {
            "current_week": {
                "league_name": "Duke Football Invitational",
                "season": 2025,
                "week": 2,
                "report_date": "2025-09-21T21:04:13.720247",
                "matchups": [
                    {
                        "week": 2,
                        "home_team": {"name": "Team Alpha", "id": 1},
                        "away_team": {"name": "Team Beta", "id": 2},
                        "home_score": 120.5,
                        "away_score": 115.2,
                        "home_projected_score": 118.0,
                        "away_projected_score": 112.0,
                        "home_optimal_score": 135.0,
                        "away_optimal_score": 125.0,
                        "players": [
                            {
                                "name": "Josh Allen",
                                "position": "QB",
                                "roster_slot": "QB",
                                "team": "Team Alpha",
                                "projected_score": 18.5,
                                "actual_score": 22.3
                            },
                            {
                                "name": "Saquon Barkley",
                                "position": "RB",
                                "roster_slot": "RB",
                                "team": "Team Beta",
                                "projected_score": 15.3,
                                "actual_score": 18.7
                            }
                        ]
                    }
                ],
                "awards": {
                    "mvp": {
                        "player_name": "Josh Allen",
                        "team_name": "Team Alpha",
                        "position": "QB",
                        "score": 22.3
                    },
                    "mwp": {
                        "player_name": "Saquon Barkley",
                        "team_name": "Team Beta",
                        "position": "RB",
                        "score": 18.7
                    },
                    "mup": None,
                    "mdp": None,
                    "hsl": {
                        "team_name": "Team Beta",
                        "score": 115.2
                    },
                    "lsw": None,
                    "ssl": None,
                    "ifm": None,
                    "accidental_genius": None,
                    "mccollapse": None,
                    "clapper_collapse": None
                }
            },
            "season_context": {
                "team_standings": {
                    "1": {
                        "id": 1,
                        "name": "Team Alpha",
                        "division": "Adams",
                        "wins": 2,
                        "losses": 0,
                        "ties": 0,
                        "points_for": 240.5,
                        "points_against": 180.0,
                        "overall_rank": 1,
                        "division_rank": 1
                    },
                    "2": {
                        "id": 2,
                        "name": "Team Beta",
                        "division": "Smythe",
                        "wins": 1,
                        "losses": 1,
                        "ties": 0,
                        "points_for": 220.8,
                        "points_against": 200.5,
                        "overall_rank": 2,
                        "division_rank": 1
                    }
                }
            }
        }

    def test_create_condensed_data_success(self):
        """Test successful creation of condensed data structure."""
        condensed_data = self.aggregate_stage._create_condensed_data(self.sample_enhanced_data)

        # Verify basic structure
        assert "league_name" in condensed_data
        assert "week" in condensed_data
        assert "team_standings" in condensed_data
        assert "matchups" in condensed_data
        assert "awards" in condensed_data

        # Verify basic league information
        assert condensed_data["league_name"] == "Duke Football Invitational"
        assert condensed_data["week"] == 2

        # Verify team standings structure
        team_standings = condensed_data["team_standings"]
        assert len(team_standings) == 2
        assert isinstance(team_standings, list)

        # Verify team standings are sorted by overall_rank
        assert team_standings[0]["overall_rank"] == 1
        assert team_standings[1]["overall_rank"] == 2

        # Verify team standings fields
        team_alpha = team_standings[0]
        assert team_alpha["name"] == "Team Alpha"
        assert team_alpha["division"] == "Adams"
        assert team_alpha["wins"] == 2
        assert team_alpha["losses"] == 0
        assert team_alpha["ties"] == 0
        assert team_alpha["points_for"] == 240  # Rounded from 240.5
        assert team_alpha["points_against"] == 180  # Rounded from 180.0
        assert team_alpha["overall_rank"] == 1
        assert team_alpha["division_rank"] == 1

    def test_create_condensed_data_matchups(self):
        """Test condensed data matchup structure."""
        condensed_data = self.aggregate_stage._create_condensed_data(self.sample_enhanced_data)

        matchups = condensed_data["matchups"]
        assert len(matchups) == 1

        matchup = matchups[0]

        # Verify home team structure
        home_team = matchup["home_team"]
        assert home_team["name"] == "Team Alpha"
        assert home_team["points_scored"] == 120.5
        assert home_team["projected_score"] == 118.0
        assert home_team["optimal_score"] == 135.0
        assert len(home_team["players"]) == 1

        # Verify away team structure
        away_team = matchup["away_team"]
        assert away_team["name"] == "Team Beta"
        assert away_team["points_scored"] == 115.2
        assert away_team["projected_score"] == 112.0
        assert away_team["optimal_score"] == 125.0
        assert len(away_team["players"]) == 1

        # Verify player data
        josh_allen = home_team["players"][0]
        assert josh_allen["name"] == "Josh Allen"
        assert josh_allen["position"] == "QB"
        assert josh_allen["roster_slot"] == "QB"
        assert josh_allen["projected_score"] == 18.5
        assert josh_allen["actual_score"] == 22.3

        saquon = away_team["players"][0]
        assert saquon["name"] == "Saquon Barkley"
        assert saquon["position"] == "RB"
        assert saquon["roster_slot"] == "RB"
        assert saquon["projected_score"] == 15.3
        assert saquon["actual_score"] == 18.7

        # Verify new matchup fields
        # Team Alpha wins all three categories:
        # Actual: 120.5 > 115.2, Projected: 118.0 > 112.0, Optimal: 135.0 > 125.0
        assert matchup["winning_team"] == "Team Alpha"
        assert matchup["projected_winning_team"] == "Team Alpha"
        assert matchup["optimal_winning_team"] == "Team Alpha"

    def test_create_condensed_data_awards(self):
        """Test condensed data awards structure."""
        condensed_data = self.aggregate_stage._create_condensed_data(self.sample_enhanced_data)

        awards = condensed_data["awards"]

        # Verify individual player awards
        assert awards["mvp"]["player_name"] == "Josh Allen"
        assert awards["mvp"]["team_name"] == "Team Alpha"
        assert awards["mvp"]["position"] == "QB"
        assert awards["mvp"]["score"] == 22.3

        assert awards["mwp"]["player_name"] == "Saquon Barkley"
        assert awards["mwp"]["team_name"] == "Team Beta"

        # Verify None awards are preserved
        assert awards["mup"] is None
        assert awards["mdp"] is None

        # Verify team awards
        assert awards["hsl"]["team_name"] == "Team Beta"
        assert awards["hsl"]["score"] == 115.2

        # Verify other awards are None
        assert awards["lsw"] is None
        assert awards["ssl"] is None
        assert awards["ifm"] is None
        assert awards["accidental_genius"] is None
        assert awards["mccollapse"] is None
        assert awards["clapper_collapse"] is None

    def test_create_condensed_data_empty_structure(self):
        """Test condensed data creation with empty/minimal data."""
        minimal_enhanced_data = {
            "current_week": {
                "league_name": "Test League",
                "week": 1,
                "matchups": [],
                "awards": {}
            },
            "season_context": {
                "team_standings": {}
            }
        }

        condensed_data = self.aggregate_stage._create_condensed_data(minimal_enhanced_data)

        # Verify basic structure is maintained
        assert condensed_data["league_name"] == "Test League"
        assert condensed_data["week"] == 1
        assert condensed_data["team_standings"] == []
        assert condensed_data["matchups"] == []
        assert isinstance(condensed_data["awards"], dict)

        # Verify all award types are None
        expected_awards = ["mvp", "mwp", "mup", "mdp", "hsl", "lsw", "ssl", "ifm", "accidental_genius", "mccollapse", "clapper_collapse"]
        for award_type in expected_awards:
            assert award_type in condensed_data["awards"]
            assert condensed_data["awards"][award_type] is None

    def test_create_condensed_data_error_handling(self):
        """Test condensed data creation with invalid data structure."""
        invalid_data = {
            "invalid_structure": True
        }

        condensed_data = self.aggregate_stage._create_condensed_data(invalid_data)

        # Should return default values when structure is invalid
        assert condensed_data["league_name"] == "Unknown League"
        assert condensed_data["week"] == 1
        assert condensed_data["team_standings"] == []
        assert condensed_data["matchups"] == []

        # Verify awards dict exists with all expected None values
        awards = condensed_data["awards"]
        expected_awards = ["mvp", "mwp", "mup", "mdp", "hsl", "lsw", "ssl", "ifm", "accidental_genius", "mccollapse", "clapper_collapse"]
        for award_type in expected_awards:
            assert award_type in awards
            assert awards[award_type] is None

    @patch('src.pipeline.aggregate_stage.AggregateStage._fetch_historical_data')
    @patch('src.pipeline.aggregate_stage.AggregateStage._create_enhanced_data')
    def test_aggregate_stage_creates_both_files(self, mock_enhanced, mock_historical):
        """Test that aggregate stage creates both enhanced and condensed files."""
        # Setup mocks
        mock_historical.return_value = ([], True)  # Returns tuple (historical_data, is_latest_week)
        mock_enhanced.return_value = self.sample_enhanced_data

        # Create sample current week file
        sample_current_data = {
            "league_name": "Duke Football Invitational",
            "week": 2,
            "matchups": []
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(sample_current_data, temp_file)
            temp_file_path = temp_file.name

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Execute aggregate stage
                enhanced_file, metadata = self.aggregate_stage.execute(
                    current_week_file=temp_file_path,
                    output_dir=f"{temp_dir}/enhanced"
                )

                # Verify both files were created
                assert enhanced_file is not None
                assert "enhanced_file" in metadata
                assert "condensed_file" in metadata

                # Verify enhanced file exists and is valid JSON
                assert os.path.exists(enhanced_file)
                with open(enhanced_file, 'r') as f:
                    enhanced_json = json.load(f)
                assert "current_week" in enhanced_json

                # Verify condensed file exists and is valid JSON
                condensed_file = metadata["condensed_file"]
                assert os.path.exists(condensed_file)
                with open(condensed_file, 'r') as f:
                    condensed_json = json.load(f)

                # Verify condensed file structure
                assert "league_name" in condensed_json
                assert "week" in condensed_json
                assert "team_standings" in condensed_json
                assert "matchups" in condensed_json
                assert "awards" in condensed_json

        finally:
            # Cleanup
            os.unlink(temp_file_path)

    def test_condensed_file_well_formed_json(self):
        """Test that condensed file is well-formed JSON with expected schema."""
        condensed_data = self.aggregate_stage._create_condensed_data(self.sample_enhanced_data)

        # Convert to JSON string and back to verify it's valid JSON
        json_string = json.dumps(condensed_data, indent=2)
        parsed_data = json.loads(json_string)

        # Verify the parsed data matches original
        assert parsed_data["league_name"] == condensed_data["league_name"]
        assert parsed_data["week"] == condensed_data["week"]
        assert len(parsed_data["team_standings"]) == len(condensed_data["team_standings"])

        # Verify team standings schema
        if parsed_data["team_standings"]:
            team = parsed_data["team_standings"][0]
            required_fields = ["name", "division", "wins", "losses", "ties", "points_for", "points_against", "overall_rank", "division_rank"]
            for field in required_fields:
                assert field in team

        # Verify matchups schema
        if parsed_data["matchups"]:
            matchup = parsed_data["matchups"][0]
            assert "home_team" in matchup
            assert "away_team" in matchup

            for team_key in ["home_team", "away_team"]:
                team_data = matchup[team_key]
                required_team_fields = ["name", "points_scored", "projected_score", "optimal_score", "players"]
                for field in required_team_fields:
                    assert field in team_data

                if team_data["players"]:
                    player = team_data["players"][0]
                    required_player_fields = ["name", "position", "roster_slot", "projected_score", "actual_score"]
                    for field in required_player_fields:
                        assert field in player

        # Verify awards schema
        awards = parsed_data["awards"]
        expected_award_types = ["mvp", "mwp", "mup", "mdp", "hsl", "lsw", "ssl", "ifm", "accidental_genius", "mccollapse", "clapper_collapse"]
        for award_type in expected_award_types:
            assert award_type in awards

    def test_create_condensed_data_matchup_edge_cases(self):
        """Test condensed data matchup fields with edge cases including ties."""
        # Create test data with tie games and mixed winners
        tie_game_data = {
            "current_week": {
                "league_name": "Test League",
                "week": 3,
                "matchups": [
                    {
                        "home_team": {"name": "Team Gamma", "id": 3},
                        "away_team": {"name": "Team Delta", "id": 4},
                        # Tie game: same actual scores
                        "home_score": 110.0,
                        "away_score": 110.0,
                        # Team Gamma projected higher
                        "home_projected_score": 115.0,
                        "away_projected_score": 108.0,
                        # Team Delta optimal higher
                        "home_optimal_score": 120.0,
                        "away_optimal_score": 125.0,
                        "players": []
                    },
                    {
                        "home_team": {"name": "Team Echo", "id": 5},
                        "away_team": {"name": "Team Foxtrot", "id": 6},
                        # Team Foxtrot wins actual
                        "home_score": 95.5,
                        "away_score": 102.3,
                        # Tie in projected
                        "home_projected_score": 100.0,
                        "away_projected_score": 100.0,
                        # Team Echo optimal higher
                        "home_optimal_score": 130.0,
                        "away_optimal_score": 115.0,
                        "players": []
                    }
                ],
                "awards": {}
            },
            "season_context": {
                "team_standings": {}
            }
        }

        condensed_data = self.aggregate_stage._create_condensed_data(tie_game_data)
        matchups = condensed_data["matchups"]
        assert len(matchups) == 2

        # Test first matchup: tie game with mixed winners
        matchup1 = matchups[0]
        assert matchup1["winning_team"] is None  # Tie game
        assert matchup1["projected_winning_team"] == "Team Gamma"  # 115.0 > 108.0
        assert matchup1["optimal_winning_team"] == "Team Delta"  # 125.0 > 120.0

        # Test second matchup: different winners in each category
        matchup2 = matchups[1]
        assert matchup2["winning_team"] == "Team Foxtrot"  # 102.3 > 95.5
        assert matchup2["projected_winning_team"] is None  # Tie: 100.0 = 100.0
        assert matchup2["optimal_winning_team"] == "Team Echo"  # 130.0 > 115.0