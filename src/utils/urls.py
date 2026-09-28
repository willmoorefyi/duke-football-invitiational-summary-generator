"""
Shared URL and S3-key builders for the fantasy pipeline.

These helpers are the single source of truth for the S3 keys and public URLs of
the weekly report (Stage 5, deploy) and the roast newsletter (Stage 6). Both are
keyed on ``(season, week)`` so the deploy and newsletter stages agree on where a
given edition lives without any cross-stage coordination or ordering dependency.

The public base domain defaults to the ``will.moore.fyi`` bucket to match the
project's CloudFront distribution. Callers that read the bucket from AWSConfig
should pass it through the optional ``bucket`` argument so the URLs stay
consistent with configuration.
"""

# Default S3 web bucket / CloudFront domain (matches AWSConfig.s3_bucket default).
DEFAULT_BUCKET = "will.moore.fyi"

# Common prefix under which weekly reports (and, nested below, newsletters) live.
_WEEKLY_REPORTS_PREFIX = "duke-football-invitational/weekly-reports"


def _base_url(bucket: str = DEFAULT_BUCKET) -> str:
    """Return the public ``https://`` base for ``bucket`` (served via CloudFront)."""
    return f"https://{bucket}"


def newsletter_s3_key(season, week) -> str:
    """S3 key for the roast newsletter HTML for a given season and week."""
    return f"{_WEEKLY_REPORTS_PREFIX}/newsletters/newsletter_{season}_week_{week}.html"


def newsletter_public_url(season, week, bucket: str = DEFAULT_BUCKET) -> str:
    """Public URL for the roast newsletter HTML for a given season and week."""
    return f"{_base_url(bucket)}/{newsletter_s3_key(season, week)}"


def weekly_report_s3_key(season, week) -> str:
    """S3 key for the weekly report HTML for a given season and week."""
    return f"{_WEEKLY_REPORTS_PREFIX}/fantasy_report_{season}_week_{week}.html"


def weekly_report_public_url(season, week, bucket: str = DEFAULT_BUCKET) -> str:
    """Public URL for the weekly report HTML for a given season and week."""
    return f"{_base_url(bucket)}/{weekly_report_s3_key(season, week)}"


def survivor_public_url(bucket: str = DEFAULT_BUCKET) -> str:
    """Public URL for the season-long Survivor pool page."""
    return f"{_base_url(bucket)}/duke-football-invitational/survivor.html"
