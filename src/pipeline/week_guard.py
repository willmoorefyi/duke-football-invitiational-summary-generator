"""
Guard against publishing a fantasy week that hasn't been played yet.

Running the pipeline for a future week (e.g. ``--week 8`` before any week 8 games)
extracts an all-zero week and, because every stored week is treated as the latest,
overwrites the season overview, hub and survivor pages with it. These checks stop the
run before anything is written to DynamoDB or S3.
"""

from typing import Any, Dict, List, Optional


class UnplayedWeekError(RuntimeError):
    """Raised when a week's data shows it hasn't been (fully) played."""


def _matchups(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Matchups from either raw JSON (top-level) or enhanced JSON (``current_week``)."""
    source = data.get("current_week", data)
    matchups = source.get("matchups") if isinstance(source, dict) else None
    return matchups if isinstance(matchups, list) else []


def unplayed_week_reason(data: Dict[str, Any], allow_incomplete: bool = False) -> Optional[str]:
    """
    Return why a week must not be published, or None if it's safe.

    - Every team scored 0 (or there are no matchups): the week hasn't started. Never
      overridable — no real week ends with every score at zero.
    - Any matchup ESPN reports as ``is_complete: False``: the week is still in progress
      (or stats aren't final). Overridable with ``allow_incomplete``. Matchups without
      the flag (older files) don't count as incomplete.
    """
    source = data.get("current_week", data)
    week = source.get("week") if isinstance(source, dict) else None
    label = f"Week {week}" if week is not None else "This week"
    matchups = _matchups(data)

    if not matchups:
        return f"{label} has no matchups."

    scores = [m.get(k) or 0 for m in matchups for k in ("home_score", "away_score")]
    if all(score == 0 for score in scores):
        return f"{label} hasn't been played yet: every team scored 0."

    incomplete = sum(1 for m in matchups if m.get("is_complete") is False)
    if incomplete and not allow_incomplete:
        return (
            f"{label} isn't finished: ESPN reports {incomplete} of {len(matchups)} matchups "
            f"as incomplete. Re-run once the week is final, or pass --allow-incomplete-week "
            f"to publish anyway."
        )
    return None


def ensure_week_played(data: Dict[str, Any], allow_incomplete: bool = False) -> None:
    """Raise :class:`UnplayedWeekError` if the week must not be published."""
    reason = unplayed_week_reason(data, allow_incomplete=allow_incomplete)
    if reason:
        raise UnplayedWeekError(reason)
