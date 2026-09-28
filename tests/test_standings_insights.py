"""
Tests for the season-anchored standings insights added to the aggregate stage:
per-player season roll-up, per-team week-by-week, draft board extraction/threading,
draft-value join, and the positional-outlier metric (golden test).
"""
from datetime import datetime
from types import SimpleNamespace

from src.extractors.player_extractor import PlayerExtractor
from src.pipeline.aggregate_stage import AggregateStage


def _matchup(home_name, home_id, away_name, away_id, players):
    return {
        "home_team": {"name": home_name, "id": home_id},
        "away_team": {"name": away_name, "id": away_id},
        "players": players,
    }


def _starter(name, pid, team, position, actual, is_starter=True):
    return {
        "name": name, "player_id": pid, "team": team, "position": position,
        "actual_score": actual, "is_starter": is_starter,
    }


class TestPlayerSeasonRollup:
    def setup_method(self):
        self.stage = AggregateStage(league_id=380491)

    def test_starter_points_accumulate_and_bench_ignored(self):
        all_weeks = [
            _week(1, [_matchup("A", 1, "B", 2, [
                _starter("Ace", 100, "A", "QB", 30.0),
                _starter("Benchy", 101, "A", "RB", 99.0, is_starter=False),  # ignored
                _starter("Dud", 200, "B", "RB", 5.0),
            ])]),
            _week(2, [_matchup("A", 1, "B", 2, [
                _starter("Ace", 100, "A", "QB", 10.0),
                _starter("Dud", 200, "B", "RB", 7.0),
            ])]),
        ]
        rollup = self.stage._calculate_player_season_rollup(all_weeks)
        by_name = {(e["team_name"], e["player_name"]): e for e in rollup["players"]}
        assert by_name[("A", "Ace")]["points"] == 40.0
        assert by_name[("A", "Ace")]["starts"] == 2
        assert ("A", "Benchy") not in by_name  # bench player never counted
        assert by_name[("B", "Dud")]["points"] == 12.0

    def test_traded_player_yields_separate_per_team_entries(self):
        all_weeks = [
            _week(1, [_matchup("A", 1, "B", 2, [_starter("Trav", 300, "A", "TE", 20.0)])]),
            _week(2, [_matchup("A", 1, "B", 2, [_starter("Trav", 300, "B", "TE", 10.0)])]),
        ]
        rollup = self.stage._calculate_player_season_rollup(all_weeks)
        entries = {e["team_name"]: e for e in rollup["players"] if e["player_id"] == 300}
        assert entries["A"]["points"] == 20.0
        assert entries["B"]["points"] == 10.0
        assert entries["A"]["starts"] == 1 and entries["B"]["starts"] == 1


class TestTeamWeekByWeek:
    def setup_method(self):
        self.stage = AggregateStage(league_id=380491)

    def test_actual_scores_result_and_opponent(self):
        matchup_history = {"weekly_results": {
            1: [{"home_team": {"name": "A", "id": "1"}, "away_team": {"name": "B", "id": "2"},
                 "home_score": 100.0, "away_score": 90.0, "winner_id": "1"}],
            2: [{"home_team": {"name": "A", "id": "1"}, "away_team": {"name": "B", "id": "2"},
                 "home_score": 80.0, "away_score": 80.0, "winner_id": None}],  # tie
        }}
        wbw = self.stage._calculate_team_week_by_week(matchup_history)
        assert [r["week"] for r in wbw["A"]] == [1, 2]
        assert wbw["A"][0] == {"week": 1, "opponent_name": "B", "result": "W",
                               "team_score": 100.0, "opponent_score": 90.0}
        assert wbw["B"][0]["result"] == "L"
        assert wbw["A"][1]["result"] == "T" and wbw["B"][1]["result"] == "T"


class TestPositionalOutliersGolden:
    def setup_method(self):
        self.stage = AggregateStage(league_id=380491)
        # Weekly medians: week 2 QB median is 0 -> that week must be excluded.
        self.position_stats = {"weekly_stats": {
            1: {"medians": {"QB": 20.0, "RB": 10.0}},
            2: {"medians": {"QB": 0.0, "RB": 10.0}},
            3: {"medians": {"QB": 20.0, "RB": 10.0}},
        }}
        self.all_weeks = [
            _week(1, [_matchup("A", 1, "B", 2, [
                _starter("Ace", 100, "A", "QB", 30.0),   # (30-20)/20 = 0.5
                _starter("Dud", 200, "B", "RB", 5.0),    # (5-10)/10 = -0.5
            ])]),
            _week(2, [_matchup("A", 1, "B", 2, [
                _starter("Ace", 100, "A", "QB", 100.0),  # median 0 -> EXCLUDED
                _starter("Dud", 200, "B", "RB", 5.0),    # -0.5
            ])]),
            _week(3, [_matchup("A", 1, "B", 2, [
                _starter("Ace", 100, "A", "QB", 40.0),   # (40-20)/20 = 1.0
                _starter("Dud", 200, "B", "RB", 5.0),    # -0.5
            ])]),
        ]

    def test_metric_median_exclusion_and_ordering(self):
        out = self.stage._calculate_positional_outliers(
            self.all_weeks, self.position_stats, n=5, min_starts=2
        )
        over = out["over_performers"]
        under = out["under_performers"]
        # Ace: mean of [0.5, 1.0] = 0.75 over 2 qualifying weeks (week 2 excluded).
        ace = next(r for r in over if r["name"] == "Ace")
        assert ace["metric"] == 0.75
        assert ace["starts"] == 2
        assert ace["position"] == "QB"
        # Dud: mean of three -0.5 samples.
        dud = next(r for r in under if r["name"] == "Dud")
        assert dud["metric"] == -0.5
        assert dud["starts"] == 3
        # Ordering: best over-performer first, worst under-performer first.
        assert over[0]["name"] == "Ace"
        assert under[0]["name"] == "Dud"

    def test_min_starts_filter_excludes_ace(self):
        # With min_starts=3, Ace has only 2 qualifying weeks and drops out.
        out = self.stage._calculate_positional_outliers(
            self.all_weeks, self.position_stats, n=5, min_starts=3
        )
        names = {r["name"] for r in out["over_performers"]} | {r["name"] for r in out["under_performers"]}
        assert "Ace" not in names
        assert "Dud" in names


class TestStandingsInsightsDraftJoin:
    def setup_method(self):
        self.stage = AggregateStage(league_id=380491)

    def test_draft_join_bust_steal_and_free_agent(self):
        rollup = {"players": [
            {"player_id": 100, "player_name": "Ace", "team_id": "1", "team_name": "A",
             "points": 300.0, "starts": 10},
            {"player_id": 200, "player_name": "Cheapo", "team_id": "2", "team_name": "B",
             "points": 250.0, "starts": 10},
        ]}
        draft_board = [
            {"player_id": 100, "name": "Ace", "bid_amount": 50.0, "drafting_team_name": "A"},
            {"player_id": 999, "name": "NeverStarted", "bid_amount": 40.0, "drafting_team_name": "B"},  # bust
            {"player_id": 200, "name": "Cheapo", "bid_amount": 2.0, "drafting_team_name": "B"},         # steal
            {"player_id": 0, "name": "FreeAgent", "bid_amount": 0.0, "drafting_team_name": "A"},        # omitted
        ]
        insights = self.stage._calculate_standings_insights(
            draft_board, rollup, {"weekly_stats": {}}, []
        )
        extremes = insights["draft_value_extremes"]
        names_in = {r["name"] for r in extremes["highest_priced"]}
        assert "FreeAgent" not in names_in  # no bid -> not a draft extreme
        # Drafted-then-never-started surfaces as a 0-point bust joined by player_id.
        bust = next(r for r in extremes["highest_priced"] if r["name"] == "NeverStarted")
        assert bust["season_points"] == 0.0
        # Steal: cheap bid, big season points.
        steal = next(r for r in extremes["lowest_priced"] if r["name"] == "Cheapo")
        assert steal["bid_amount"] == 2.0 and steal["season_points"] == 250.0
        # League-wide top scorer + per-team leader present.
        assert insights["season_top_scorers"]["league_wide"][0]["name"] == "Ace"
        assert insights["season_top_scorers"]["team_leaders"]["A"]["player_name"] == "Ace"


class TestDraftBoardExtraction:
    def test_extract_draft_board_from_league(self):
        pick1 = SimpleNamespace(playerId=100, playerName="Ace", bid_amount=50,
                                team=SimpleNamespace(team_id=1, team_name="A"))
        pick2 = SimpleNamespace(playerId=200, playerName="Cheapo", bid_amount=2,
                                team=SimpleNamespace(team_id=2, team_name="B"))
        espn_client = SimpleNamespace(get_league=lambda: SimpleNamespace(draft=[pick1, pick2]))
        extractor = PlayerExtractor(espn_client, datetime.now())
        board = extractor.extract_draft_board()
        assert len(board) == 2
        assert board[0].player_id == 100 and board[0].name == "Ace"
        assert board[0].bid_amount == 50.0
        assert board[0].drafting_team_id == 1 and board[0].drafting_team_name == "A"

    def test_extract_draft_board_handles_missing_draft(self):
        espn_client = SimpleNamespace(get_league=lambda: SimpleNamespace(draft=[]))
        extractor = PlayerExtractor(espn_client, datetime.now())
        assert extractor.extract_draft_board() == []


class TestCondensedThreading:
    def setup_method(self):
        self.stage = AggregateStage(league_id=380491)

    def test_condensed_threads_player_id_and_omits_draft_board(self):
        enhanced = {
            "current_week": {
                "league_name": "Duke Football Invitational",
                "season": 2025,
                "week": 1,
                "matchups": [_matchup("A", 1, "B", 2, [
                    _starter("Ace", 100, "A", "QB", 30.0),
                    _starter("Dud", 200, "B", "RB", 5.0),
                ])],
                "awards": {},
                "draft_board": [
                    {"player_id": 100, "name": "Ace", "position": "QB",
                     "bid_amount": 50.0, "drafting_team_name": "A"},
                ],
            },
            "season_context": {
                "team_standings": {},
                "standings_insights": {"draft_value_extremes": {}},
                "team_week_by_week": {"A": []},
            },
            "metadata": {"season": 2025},
        }
        condensed = self.stage._create_condensed_data(enhanced)
        # player_id threaded into condensed player entries.
        players = condensed["matchups"][0]["home_team"]["players"]
        assert players[0]["player_id"] == 100
        # The full draft board is deliberately NOT emitted into the condensed JSON
        # (no newsletter section consumes it; standings_insights captures its value).
        assert "draft_board" not in condensed
        # It remains in the enhanced JSON / current_week so _calculate_standings_insights
        # can still compute the draft extremes from it.
        assert enhanced["current_week"]["draft_board"][0]["player_id"] == 100
        # New top-level fields present.
        assert condensed["standings_insights"] == {"draft_value_extremes": {}}
        assert "A" in condensed["team_week_by_week"]


def _week(week_num, matchups):
    return {"week": week_num, "matchups": matchups}
