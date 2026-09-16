import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.pipeline.newsletter_stage import NewsletterStage
from src.utils.config import (
    AWSConfig,
    Config,
    NewsletterConfig,
    PipelineConfig,
)


def _condensed(**overrides):
    """Minimal valid condensed payload."""
    data = {
        "league_name": "Duke Football Invitational",
        "week": 1,
        "team_standings": [{"team_name": "Bad JuJu", "wins": 1, "losses": 0}],
        "matchups": [{"home_team": "Bad JuJu", "away_team": "Team Team"}],
        "awards": {"mvp": {"player": "Caleb Williams", "points": 39.26}},
    }
    data.update(overrides)
    return data


def _converse_response(text, stop_reason="end_turn", in_tok=100, out_tok=50):
    return {
        "output": {"message": {"content": [{"text": text}]}},
        "usage": {"inputTokens": in_tok, "outputTokens": out_tok},
        "stopReason": stop_reason,
    }


class TestNewsletterStage:
    def setup_method(self):
        self.stage = NewsletterStage(league_id=380491)
        self.stage.config = Config(
            pipeline=PipelineConfig(
                aws=AWSConfig(region="us-east-1", dynamodb_table="test-table", profile="test-profile"),
                newsletter=NewsletterConfig(
                    bedrock_model_id="mistral.mistral-large-3-675b-instruct",
                    temperature=0.9,
                    max_tokens=4000,
                    prompt_version="v1",
                ),
            )
        )

    def _write_condensed(self, tmpdir, **overrides):
        path = Path(tmpdir) / "condensed.json"
        path.write_text(json.dumps(_condensed(**overrides)))
        return str(path)

    # --- validation -------------------------------------------------------

    def test_missing_keys_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text(json.dumps({"league_name": "x", "week": 1}))
            with pytest.raises(ValueError, match="missing required keys"):
                self.stage.execute(condensed_file=str(path))

    # --- dry run ----------------------------------------------------------

    @patch("src.pipeline.newsletter_stage.boto3")
    def test_dry_run_makes_no_aws_calls(self, mock_boto3):
        self.stage.dry_run = True
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_condensed(tmp)
            out, meta = self.stage.execute(condensed_file=path, output_dir=tmp)
        assert out is None
        assert meta["dry_run"] is True
        assert meta["week"] == 1
        mock_boto3.Session.assert_not_called()

    # --- extraction helper ------------------------------------------------

    def test_extract_strips_fence_and_preamble_and_subject(self):
        raw = (
            "SUBJECT: Week 1 Chaos\n"
            "Here's your newsletter:\n"
            "```html\n"
            "<div>hello <b>world</b></div>\n"
            "```\n"
            "Hope you enjoy!"
        )
        subject, fragment = self.stage._extract_fragment(raw, want_subject=True)
        assert subject == "Week 1 Chaos"
        assert fragment == "<div>hello <b>world</b></div>"
        assert "```" not in fragment
        assert "Here's your newsletter" not in fragment
        assert "Hope you enjoy" not in fragment

    def test_extract_no_subject_when_not_wanted(self):
        subject, fragment = self.stage._extract_fragment("<p>hi</p>", want_subject=False)
        assert subject is None
        assert fragment == "<p>hi</p>"

    # --- happy path -------------------------------------------------------

    @patch("src.pipeline.newsletter_stage.boto3")
    def test_full_generation_assembles_and_audits(self, mock_boto3):
        def converse(**kwargs):
            # Match the per-section directive text (task_v1.md itself contains the bare
            # strings "Section 1/2/3", so match the directive's unique descriptions).
            user_text = kwargs["messages"][0]["content"][0]["text"]
            if "(the matchup summaries)" in user_text:
                return _converse_response("<div>MATCHUPS</div>")
            if "(the awards)" in user_text:
                return _converse_response("<div>AWARDS</div>")
            if "(the final recap)" in user_text:
                return _converse_response("<div>RECAP</div>")
            return _converse_response("SUBJECT: Week 1 Mayhem\n<div>INTRO</div>")

        bedrock = MagicMock()
        bedrock.converse.side_effect = converse
        table = MagicMock()
        session = MagicMock()
        session.client.return_value = bedrock
        session.resource.return_value.Table.return_value = table
        mock_boto3.Session.return_value = session

        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_condensed(tmp)
            out, meta = self.stage.execute(condensed_file=path, output_dir=tmp)
            assert out is not None
            html = Path(out).read_text()

        # Four section calls made.
        assert bedrock.converse.call_count == 4

        # Assembled HTML contains every section and a wrapper.
        for marker in ("INTRO", "MATCHUPS", "AWARDS", "RECAP"):
            assert marker in html
        assert "<!DOCTYPE html>" in html

        # Metadata.
        assert meta["subject"] == "Week 1 Mayhem"
        assert meta["model_id"] == "mistral.mistral-large-3-675b-instruct"
        assert meta["input_tokens"] == 400  # 100 * 4
        assert meta["output_tokens"] == 200  # 50 * 4
        assert meta["audit_key"]["pk"] == "NEWSLETTER#380491"

        # Audit record written with expected shape.
        table.put_item.assert_called_once()
        item = table.put_item.call_args.kwargs["Item"]
        assert item["season_week"] == "NEWSLETTER#380491"
        assert item["data_type_id"].startswith("SEASON#")
        assert item["prompt_version"] == "v1"
        assert item["delivery_result"] == "not_sent"
        assert item["subject"] == "Week 1 Mayhem"
        assert "prompt_content_hash" in item
        assert "condensed_input_hash" in item

    # --- truncation is a hard failure -------------------------------------

    @patch("src.pipeline.newsletter_stage.boto3")
    def test_max_tokens_stop_raises(self, mock_boto3):
        bedrock = MagicMock()
        bedrock.converse.return_value = _converse_response("<div>x</div>", stop_reason="max_tokens")
        session = MagicMock()
        session.client.return_value = bedrock
        mock_boto3.Session.return_value = session

        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_condensed(tmp)
            with pytest.raises(RuntimeError, match="max_tokens"):
                self.stage.execute(condensed_file=path, output_dir=tmp)
