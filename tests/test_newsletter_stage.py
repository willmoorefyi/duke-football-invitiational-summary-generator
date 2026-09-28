import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.pipeline.newsletter_stage import SECTIONS, NewsletterStage
from src.utils.config import (
    AWSConfig,
    Config,
    NewsletterConfig,
    PipelineConfig,
)


def _condensed(**overrides):
    """Minimal but realistically-shaped condensed payload (post-refactor fields)."""
    data = {
        "league_name": "Duke Football Invitational",
        "week": 1,
        "season": 2025,
        "team_standings": [
            {"name": "Bad JuJu", "division": "East", "wins": 1, "losses": 0,
             "overall_rank": 1, "division_rank": 1},
            {"name": "Team Team", "division": "East", "wins": 0, "losses": 1,
             "overall_rank": 2, "division_rank": 2},
        ],
        "matchups": [{
            "home_team": {
                "name": "Bad JuJu", "points_scored": 150.0,
                "players": [{"name": "Caleb Williams", "player_id": 1, "position": "QB",
                             "roster_slot": "QB", "actual_score": 39.26,
                             "injury_status": "HEALTHY"}],
            },
            "away_team": {
                "name": "Team Team", "points_scored": 90.0,
                "players": [{"name": "Hurt Guy", "player_id": 2, "position": "WR",
                             "roster_slot": "WR", "actual_score": 3.0,
                             "injury_status": "OUT"}],
            },
            "winning_team": "Bad JuJu",
        }],
        "awards": {"mvp": {"player_name": "Caleb Williams", "score": 39.26}},
        "position_strength": {
            "positions": ["QB"],
            "teams": {"Bad JuJu": {"QB": {"points": 39.3, "vs_median": 10.0}}},
        },
        "draft_board": [
            {"player_id": 1, "name": "Caleb Williams", "bid_amount": 5.0,
             "drafting_team_name": "Bad JuJu"},
        ],
        "standings_insights": {
            "draft_value_extremes": {"highest_priced": [], "lowest_priced": []},
            "season_top_scorers": {"league_wide": [], "team_leaders": {}},
            "positional_outliers": {"over_performers": [], "under_performers": []},
        },
        "team_week_by_week": {
            "Bad JuJu": [{"week": 1, "opponent_name": "Team Team", "result": "W",
                          "team_score": 150.0, "opponent_score": 90.0}],
        },
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
                    prompt_version="v2",
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

    # --- prompt versioning ------------------------------------------------

    def test_v2_is_default_and_prompts_load(self):
        assert NewsletterConfig().prompt_version == "v2"
        system_prompt, task_prompt, prompt_hash = self.stage._load_prompts("v2")
        assert system_prompt.strip()
        assert task_prompt.strip()
        # v2 restructures into five sections; the standings section is now its own.
        assert "Standings & divisional analysis" in task_prompt
        assert len(prompt_hash) == 64

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

    # --- per-section payload isolation ------------------------------------

    def test_section_payload_isolation(self):
        condensed = _condensed()

        standings = self.stage._section_payload("standings", condensed)
        assert "standings_insights" in standings
        assert "team_week_by_week" in standings
        assert "team_standings" in standings
        assert "position_strength" in standings
        # The standings section must NOT re-receive the current-week matchup detail.
        assert "matchups" not in standings

        matchups = self.stage._section_payload("matchups", condensed)
        assert "matchups" in matchups
        # Matchups section carries no season-anchored draft/insights data.
        assert "draft_board" not in matchups
        assert "standings_insights" not in matchups
        assert "team_week_by_week" not in matchups

        intro = self.stage._section_payload("intro", condensed)
        assert set(intro).issuperset({"league_name", "week", "season"})
        assert intro["standings_framing"]["division_leaders"]["East"] == "Bad JuJu"
        assert "matchups" not in intro

        awards = self.stage._section_payload("awards", condensed)
        assert "awards" in awards
        assert awards["players"]  # flattened referenced players present
        assert "matchups" not in awards

        recap = self.stage._section_payload("recap", condensed)
        assert "team_standings" in recap and "awards" in recap
        assert recap["week_results"][0]["winning_team"] == "Bad JuJu"
        # Recap gets only a minimal results slice, not the full matchups/players.
        assert "matchups" not in recap
        assert "players" not in recap["week_results"][0]

    def test_section_payload_degrades_without_new_fields(self):
        """Old condensed files lacking the new fields must not raise KeyError."""
        legacy = {
            "league_name": "Old League",
            "week": 3,
            "season": 2024,
            "team_standings": [{"name": "A", "division": "East", "overall_rank": 1}],
            "matchups": [],
            "awards": {},
        }
        for key, _ in SECTIONS:
            payload = self.stage._section_payload(key, legacy)  # must not raise
            assert isinstance(payload, dict)
        standings = self.stage._section_payload("standings", legacy)
        assert "standings_insights" not in standings
        assert "team_week_by_week" not in standings
        assert "position_strength" not in standings
        assert standings["team_standings"] == legacy["team_standings"]

    # --- design normalization pass ----------------------------------------

    def test_normalize_html_replaces_garish_fonts_and_softens_white(self):
        raw = (
            '<h2 style="font-family: Impact, \'Arial Black\', sans-serif; color: #ffffff;">HELLO</h2>'
            '<p style="color: white; background-color: #1a1a1a;">body</p>'
            '<div style="font-family: \'Comic Sans MS\', cursive; color:#FFF;">x</div>'
        )
        out = self.stage._normalize_html(raw)
        assert "Impact" not in out
        assert "Arial Black" not in out
        assert "Comic Sans" not in out
        assert out.count("-apple-system") == 2
        assert "#ffffff" not in out
        assert "color: white" not in out
        assert "#e8e8e8" in out
        assert "background-color: #1a1a1a" in out

    def test_normalize_html_leaves_good_styling_untouched(self):
        raw = '<p style="font-family: Arial, sans-serif; color: #e8e8e8;">clean</p>'
        assert self.stage._normalize_html(raw) == raw

    # --- happy path -------------------------------------------------------

    @patch("src.pipeline.newsletter_stage.boto3")
    def test_full_generation_assembles_and_audits(self, mock_boto3):
        def converse(**kwargs):
            # Route on the unique parenthetical text in each per-section DIRECTIVE.
            user_text = kwargs["messages"][0]["content"][0]["text"]
            if "(the matchup summaries)" in user_text:
                return _converse_response("<div>MATCHUPS</div>")
            if "(the awards)" in user_text:
                return _converse_response("<div>AWARDS</div>")
            if "(the standings & divisional analysis)" in user_text:
                return _converse_response("<div>STANDINGS</div>")
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

        # Five section calls made (one per SECTIONS entry).
        assert bedrock.converse.call_count == 5

        # Assembled HTML contains every section and a wrapper.
        for marker in ("INTRO", "MATCHUPS", "AWARDS", "STANDINGS", "RECAP"):
            assert marker in html
        assert "<!DOCTYPE html>" in html

        # Assembly ORDER matches the new SECTIONS order.
        order = [html.index(m) for m in ("INTRO", "MATCHUPS", "AWARDS", "STANDINGS", "RECAP")]
        assert order == sorted(order)

        # Static preamble links present above the AI content.
        expected_url = (
            "https://will.moore.fyi/duke-football-invitational/weekly-reports/"
            "newsletters/newsletter_2025_week_1.html"
        )
        assert "Weekly Rundown:" in html
        assert "Survivor Pool Results:" in html
        assert "fantasy_report_2025_week_1.html" in html
        assert "survivor.html" in html

        # Metadata.
        assert meta["subject"] == "Week 1 Mayhem"
        assert meta["model_id"] == "mistral.mistral-large-3-675b-instruct"
        assert meta["input_tokens"] == 500  # 100 * 5
        assert meta["output_tokens"] == 250  # 50 * 5
        assert meta["audit_key"]["pk"] == "NEWSLETTER#380491"
        assert meta["season"] == 2025
        assert meta["newsletter_url"] == expected_url
        assert meta["delivery_result"] == "deployed"

        # Audit record written with expected shape (incl. ordered section keys).
        table.put_item.assert_called_once()
        item = table.put_item.call_args.kwargs["Item"]
        assert item["season_week"] == "NEWSLETTER#380491"
        assert item["data_type_id"].startswith("SEASON#2025#WEEK#1#")
        assert item["prompt_version"] == "v2"
        assert item["season"] == 2025
        assert item["sections"] == ["intro", "matchups", "awards", "standings", "recap"]
        assert item["delivery_result"] == "deployed"
        assert item["output_html_ref"] == expected_url
        assert item["local_html_ref"].endswith(".html")
        assert item["subject"] == "Week 1 Mayhem"
        assert "prompt_content_hash" in item
        assert "condensed_input_hash" in item

    # --- S3 upload failure is non-blocking and audited --------------------

    @patch("src.pipeline.newsletter_stage.boto3")
    def test_s3_upload_failure_records_not_sent(self, mock_boto3):
        """If the S3 upload raises, the stage still finishes, writing a not_sent audit."""
        bedrock = MagicMock()
        bedrock.converse.side_effect = lambda **kw: _converse_response(
            "SUBJECT: Wk1\n<div>x</div>"
            if "SUBJECT: " in kw["messages"][0]["content"][0]["text"]
            else "<div>x</div>"
        )
        s3 = MagicMock()
        s3.put_object.side_effect = RuntimeError("access denied")
        table = MagicMock()

        def client(service, **kwargs):
            return bedrock if service == "bedrock-runtime" else s3

        session = MagicMock()
        session.client.side_effect = client
        session.resource.return_value.Table.return_value = table
        mock_boto3.Session.return_value = session

        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_condensed(tmp)
            out, meta = self.stage.execute(condensed_file=path, output_dir=tmp)

        # Stage still produced the local file and did not crash.
        assert out is not None
        assert meta["delivery_result"] == "not_sent"

        # Audit records the local path and not_sent (upload failed).
        item = table.put_item.call_args.kwargs["Item"]
        assert item["delivery_result"] == "not_sent"
        assert item["output_html_ref"].endswith(".html")
        assert item["output_html_ref"] == item["local_html_ref"]

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
