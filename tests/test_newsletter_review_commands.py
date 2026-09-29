"""
Tests for the newsletter review-loop CLI commands:

- ``pipeline newsletter-regenerate`` — LOCAL-ONLY preview (Bedrock generation, no
  S3 / CloudFront / DynamoDB), used to iterate on the copy before deploying.
- ``pipeline newsletter-upload`` — deploys a reviewed HTML file to S3, invalidates
  CloudFront, and writes a fresh 'deployed' audit row.

These follow the mocking patterns in tests/test_newsletter_stage.py (boto3/Bedrock
mocked) but drive the commands through Click's CliRunner. They run inside an isolated
filesystem so the stage's relative output dirs (output/condensed, output/newsletters)
are contained in a temp directory.
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from src.cli import newsletter_regenerate, newsletter_upload
from src.pipeline.newsletter_stage import SECTIONS
from src.utils.urls import newsletter_public_url, newsletter_s3_key


def _condensed(week=3, season=2025):
    """Minimal but valid condensed payload (mirrors test_newsletter_stage)."""
    return {
        "league_name": "Duke Football Invitational",
        "week": week,
        "season": season,
        "team_standings": [
            {"name": "Bad JuJu", "division": "East", "wins": 1, "losses": 0,
             "overall_rank": 1, "division_rank": 1},
        ],
        "matchups": [{
            "home_team": {"name": "Bad JuJu", "points_scored": 150.0, "players": []},
            "away_team": {"name": "Team Team", "points_scored": 90.0, "players": []},
            "winning_team": "Bad JuJu",
        }],
        "awards": {"mvp": {"player_name": "Caleb Williams", "score": 39.26}},
    }


def _converse_response(text, stop_reason="end_turn", in_tok=100, out_tok=50):
    return {
        "output": {"message": {"content": [{"text": text}]}},
        "usage": {"inputTokens": in_tok, "outputTokens": out_tok},
        "stopReason": stop_reason,
    }


def _bedrock_converse(**kwargs):
    """Route the intro directive (asks for a SUBJECT line) vs. everything else."""
    user_text = kwargs["messages"][0]["content"][0]["text"]
    if "SUBJECT: " in user_text:
        return _converse_response("SUBJECT: Week 3 Mayhem\n<div>INTRO</div>")
    return _converse_response("<div>SECTION</div>")


class TestNewsletterRegenerate:
    def setup_method(self):
        self.runner = CliRunner()

    def _write_condensed(self, name="condensed_week_3_20260929_100000.json", **kw):
        cond_dir = Path("output/condensed")
        cond_dir.mkdir(parents=True, exist_ok=True)
        path = cond_dir / name
        path.write_text(json.dumps(_condensed(**kw)))
        return path

    @patch("src.pipeline.newsletter_stage.boto3")
    def test_regenerate_local_only_no_deploy_or_audit(self, mock_boto3):
        """Generates a local HTML file and makes NO S3/CloudFront/DynamoDB calls."""
        bedrock = MagicMock()
        bedrock.converse.side_effect = _bedrock_converse
        session = MagicMock()
        session.client.return_value = bedrock
        mock_boto3.Session.return_value = session

        with self.runner.isolated_filesystem():
            self._write_condensed(week=3, season=2025)
            result = self.runner.invoke(newsletter_regenerate, [])
            assert result.exit_code == 0, result.output

            # Local HTML written to output/newsletters/.
            html_files = list(Path("output/newsletters").glob("*.html"))
            assert len(html_files) == 1
            html = html_files[0].read_text()
            assert "INTRO" in html and "SECTION" in html

        # Bedrock was invoked once per section, but NO deploy/audit clients created.
        assert bedrock.converse.call_count == len(SECTIONS)
        session.resource.assert_not_called()  # no DynamoDB audit resource (session path)
        # _write_audit uses boto3.resource(...) directly when no profile is set, so a
        # missing audit also means the module-level resource factory was never touched.
        mock_boto3.resource.assert_not_called()
        services = [c.args[0] for c in session.client.call_args_list]
        assert services == ["bedrock-runtime"] * len(services)
        assert "s3" not in services and "cloudfront" not in services

    @patch("src.pipeline.newsletter_stage.boto3")
    def test_regenerate_uses_given_condensed_file(self, mock_boto3):
        """An explicit CONDENSED_FILE argument is honored over the latest-file default."""
        bedrock = MagicMock()
        bedrock.converse.side_effect = _bedrock_converse
        session = MagicMock()
        session.client.return_value = bedrock
        mock_boto3.Session.return_value = session

        with self.runner.isolated_filesystem():
            # A newer, unrelated file exists; the explicitly-passed one must win.
            self._write_condensed(name="condensed_week_9_newer.json", week=9, season=2025)
            chosen = self._write_condensed(name="condensed_week_2_chosen.json", week=2, season=2025)
            result = self.runner.invoke(newsletter_regenerate, [str(chosen)])
            assert result.exit_code == 0, result.output
            assert "Week: 2" in result.output

    def test_regenerate_dry_run_makes_no_bedrock_call(self):
        with patch("src.pipeline.newsletter_stage.boto3") as mock_boto3:
            with self.runner.isolated_filesystem():
                self._write_condensed(week=7, season=2024)
                result = self.runner.invoke(newsletter_regenerate, ["--dry-run"])
                assert result.exit_code == 0, result.output
                assert "dry-run" in result.output.lower()
                assert "Week: 7" in result.output
                assert "2024" in result.output
                # No HTML written and no AWS session opened.
                assert not list(Path("output/newsletters").glob("*.html"))
            mock_boto3.Session.assert_not_called()

    def test_regenerate_errors_when_no_condensed(self):
        with self.runner.isolated_filesystem():
            Path("output/condensed").mkdir(parents=True, exist_ok=True)
            result = self.runner.invoke(newsletter_regenerate, [])
            assert result.exit_code == 1
            assert "no condensed JSON found" in result.output


class TestNewsletterUpload:
    def setup_method(self):
        self.runner = CliRunner()

    def _write_newsletter(self, name, mtime=None):
        out_dir = Path("output/newsletters")
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / name
        path.write_text("<html><body>reviewed newsletter</body></html>")
        if mtime is not None:
            import os
            os.utime(path, (mtime, mtime))
        return path

    def _mock_boto3(self, mock_boto3):
        s3 = MagicMock()
        cf = MagicMock()
        table = MagicMock()

        def client(service, **kwargs):
            return {"s3": s3, "cloudfront": cf}[service]

        session = MagicMock()
        session.client.side_effect = client
        session.resource.return_value.Table.return_value = table
        mock_boto3.Session.return_value = session
        return s3, cf, table

    @patch("src.pipeline.newsletter_stage.boto3")
    def test_upload_latest_deploys_and_audits(self, mock_boto3):
        """Resolves the latest HTML by mtime, uploads, invalidates, and audits 'deployed'."""
        s3, cf, table = self._mock_boto3(mock_boto3)

        with self.runner.isolated_filesystem():
            # Two files; the week-5 one is newest and must be chosen.
            self._write_newsletter("newsletter_week_2_old.html", mtime=1000)
            self._write_newsletter("newsletter_week_5_new.html", mtime=2000)
            result = self.runner.invoke(newsletter_upload, ["--season", "2025"])
            assert result.exit_code == 0, result.output

        expected_key = newsletter_s3_key(2025, 5)
        expected_url = newsletter_public_url(2025, 5, "will.moore.fyi")

        # Uploaded to the computed key + bucket.
        s3.put_object.assert_called_once()
        assert s3.put_object.call_args.kwargs["Key"] == expected_key
        assert s3.put_object.call_args.kwargs["Bucket"] == "will.moore.fyi"

        # CloudFront invalidation issued.
        cf.create_invalidation.assert_called_once()

        # Fresh 'deployed' audit row pointing at the public URL.
        table.put_item.assert_called_once()
        item = table.put_item.call_args.kwargs["Item"]
        assert item["delivery_result"] == "deployed"
        assert item["output_html_ref"] == expected_url
        assert item["week"] == 5
        assert item["season"] == 2025
        assert expected_url in result.output

    @patch("src.pipeline.newsletter_stage.boto3")
    def test_upload_defaults_season_to_current_year(self, mock_boto3):
        s3, cf, table = self._mock_boto3(mock_boto3)
        current_year = datetime.now().year

        with self.runner.isolated_filesystem():
            self._write_newsletter("newsletter_week_4_x.html")
            result = self.runner.invoke(newsletter_upload, [])
            assert result.exit_code == 0, result.output

        assert s3.put_object.call_args.kwargs["Key"] == newsletter_s3_key(current_year, 4)

    def _write_condensed_for_week(self, week, season):
        """Write a matching condensed_week_{week}_*.json used for season inference."""
        cond_dir = Path("output/condensed")
        cond_dir.mkdir(parents=True, exist_ok=True)
        path = cond_dir / f"condensed_week_{week}_20230101_000000.json"
        path.write_text(json.dumps({"week": week, "season": season}))
        return path

    @patch("src.pipeline.newsletter_stage.boto3")
    def test_upload_infers_season_from_condensed(self, mock_boto3):
        """With no --season, the season comes from the matching condensed file."""
        s3, cf, table = self._mock_boto3(mock_boto3)

        with self.runner.isolated_filesystem():
            self._write_newsletter("newsletter_week_5_x.html")
            self._write_condensed_for_week(week=5, season=2023)
            result = self.runner.invoke(newsletter_upload, [])
            assert result.exit_code == 0, result.output
            assert "from condensed file" in result.output

        assert s3.put_object.call_args.kwargs["Key"] == newsletter_s3_key(2023, 5)
        assert table.put_item.call_args.kwargs["Item"]["season"] == 2023

    @patch("src.pipeline.newsletter_stage.boto3")
    def test_upload_season_flag_overrides_condensed(self, mock_boto3):
        """An explicit --season wins over the condensed file's season."""
        s3, cf, table = self._mock_boto3(mock_boto3)

        with self.runner.isolated_filesystem():
            self._write_newsletter("newsletter_week_5_x.html")
            self._write_condensed_for_week(week=5, season=2023)
            result = self.runner.invoke(newsletter_upload, ["--season", "2025"])
            assert result.exit_code == 0, result.output
            assert "(--season)" in result.output

        assert s3.put_object.call_args.kwargs["Key"] == newsletter_s3_key(2025, 5)

    @patch("src.pipeline.newsletter_stage.boto3")
    def test_upload_dry_run_makes_no_aws_calls(self, mock_boto3):
        with self.runner.isolated_filesystem():
            self._write_newsletter("newsletter_week_6_x.html")
            result = self.runner.invoke(newsletter_upload, ["--season", "2025", "--dry-run"])
            assert result.exit_code == 0, result.output
            assert "dry-run" in result.output.lower()
            assert newsletter_s3_key(2025, 6) in result.output
            assert newsletter_public_url(2025, 6, "will.moore.fyi") in result.output
        mock_boto3.Session.assert_not_called()

    @patch("src.pipeline.newsletter_stage.boto3")
    def test_upload_errors_on_unparseable_week(self, mock_boto3):
        self._mock_boto3(mock_boto3)
        with self.runner.isolated_filesystem():
            path = self._write_newsletter("not_a_newsletter.html")
            result = self.runner.invoke(newsletter_upload, [str(path)])
            assert result.exit_code == 1
            assert "could not parse week" in result.output

    def test_upload_errors_when_no_html(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("output/newsletters").mkdir(parents=True, exist_ok=True)
            result = runner.invoke(newsletter_upload, [])
            assert result.exit_code == 1
            assert "no HTML found" in result.output
