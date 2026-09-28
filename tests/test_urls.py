"""Tests for the shared URL/S3-key helpers and cross-stage key agreement."""

from src.utils.urls import (
    DEFAULT_BUCKET,
    newsletter_public_url,
    newsletter_s3_key,
    survivor_public_url,
    weekly_report_public_url,
    weekly_report_s3_key,
)


class TestUrlHelpers:
    """Determinism of the URL/key builders (part H item 4)."""

    def test_newsletter_key_and_url(self):
        assert (
            newsletter_s3_key(2025, 7)
            == "duke-football-invitational/weekly-reports/newsletters/newsletter_2025_week_7.html"
        )
        assert (
            newsletter_public_url(2025, 7)
            == "https://will.moore.fyi/duke-football-invitational/weekly-reports/"
               "newsletters/newsletter_2025_week_7.html"
        )

    def test_weekly_report_key_and_url(self):
        assert (
            weekly_report_s3_key(2025, 7)
            == "duke-football-invitational/weekly-reports/fantasy_report_2025_week_7.html"
        )
        assert (
            weekly_report_public_url(2025, 7)
            == "https://will.moore.fyi/duke-football-invitational/weekly-reports/"
               "fantasy_report_2025_week_7.html"
        )

    def test_survivor_url(self):
        assert survivor_public_url() == "https://will.moore.fyi/duke-football-invitational/survivor.html"

    def test_bucket_override_flows_into_url(self):
        assert newsletter_public_url(2025, 1, "other.example.com").startswith(
            "https://other.example.com/"
        )
        assert weekly_report_public_url(2025, 1, "other.example.com").startswith(
            "https://other.example.com/"
        )

    def test_default_bucket_constant(self):
        assert DEFAULT_BUCKET == "will.moore.fyi"


class TestCrossStageAgreement:
    """Newsletter and weekly-report keys share the same season/folder (part H item 1)."""

    def test_same_season_week_share_folder(self):
        season, week = 2025, 9
        nl = newsletter_s3_key(season, week)
        wr = weekly_report_s3_key(season, week)
        # Both live under the same season-scoped weekly-reports prefix.
        assert nl.startswith("duke-football-invitational/weekly-reports/")
        assert wr.startswith("duke-football-invitational/weekly-reports/")
        # Both encode the identical season and week tokens.
        assert f"_{season}_week_{week}.html" in nl
        assert f"_{season}_week_{week}.html" in wr

    def test_past_season_keys_use_that_season(self):
        # A 2024 regen must key on 2024 regardless of the current year (part H item 2).
        assert "2024" in newsletter_s3_key(2024, 3)
        assert "2024" in weekly_report_s3_key(2024, 3)
        assert "2024" in newsletter_public_url(2024, 3)
