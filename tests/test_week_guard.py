"""Refusing to publish a fantasy week that hasn't been played (or isn't finished)."""

import json
from unittest.mock import MagicMock

import pytest

from src.pipeline.week_guard import UnplayedWeekError, ensure_week_played, unplayed_week_reason


def _week(scores, complete=True, week=8, enhanced=False):
    matchups = [
        {"home_score": h, "away_score": a, **({} if complete is None else {"is_complete": complete})}
        for h, a in scores
    ]
    data = {"week": week, "matchups": matchups}
    return {"current_week": data} if enhanced else data


class TestUnplayedWeekReason:
    def test_played_week_is_allowed(self):
        assert unplayed_week_reason(_week([(104.2, 127.1), (85.9, 90.3)])) is None

    def test_all_zero_week_is_refused_even_with_override(self):
        data = _week([(0.0, 0.0), (0.0, 0.0)], complete=False)
        assert "hasn't been played" in unplayed_week_reason(data)
        assert "hasn't been played" in unplayed_week_reason(data, allow_incomplete=True)

    def test_in_progress_week_is_refused_unless_overridden(self):
        data = _week([(104.2, 27.1), (0.0, 0.0)], complete=False)
        reason = unplayed_week_reason(data)
        assert "isn't finished" in reason and "2 of 2" in reason
        assert unplayed_week_reason(data, allow_incomplete=True) is None

    def test_missing_completion_flag_is_not_treated_as_incomplete(self):
        assert unplayed_week_reason(_week([(104.2, 127.1)], complete=None)) is None

    def test_reads_enhanced_json_shape(self):
        data = _week([(0.0, 0.0)], complete=False, enhanced=True)
        with pytest.raises(UnplayedWeekError, match="Week 8"):
            ensure_week_played(data)

    def test_no_matchups_is_refused(self):
        assert "no matchups" in unplayed_week_reason({"week": 8, "matchups": []})


class TestPipelineRefusesUnplayedWeek:
    def test_full_run_stops_after_extract_before_any_writes(self, tmp_path):
        from src.pipeline.orchestrator import PipelineOrchestrator
        from src.pipeline.orchestrator import PipelineResult, PipelineStatus

        raw = tmp_path / "raw_week_8.json"
        raw.write_text(json.dumps(_week([(0.0, 0.0)], complete=False)))

        orch = PipelineOrchestrator.__new__(PipelineOrchestrator)
        orch.logger = MagicMock()
        orch.execution_id = "test"
        orch.results = {}
        calls = []

        def run_stage(name, **kwargs):
            calls.append(name)
            return PipelineResult(stage_name=name, status=PipelineStatus.SUCCESS,
                                  output_path=str(raw), metadata={})

        orch.run_stage = run_stage
        orch._save_pipeline_log = MagicMock()
        with pytest.raises(UnplayedWeekError):
            orch.run_full_pipeline(week=8)
        assert calls == ["extract"]

    def test_upload_stage_refuses_before_touching_dynamodb(self, tmp_path):
        from src.pipeline.upload_stage import UploadStage

        enhanced = tmp_path / "enhanced_week_8.json"
        data = _week([(0.0, 0.0)], complete=False, enhanced=True)
        data["current_week"].update({"season": 2026, "league_id": 380491})
        enhanced.write_text(json.dumps(data))
        stage = UploadStage.__new__(UploadStage)
        stage.logger = MagicMock()
        stage.dry_run = False
        with pytest.raises(UnplayedWeekError):
            stage.execute(str(enhanced))
