"""
One-off backfill: re-render past weekly reports with the current templates
WITHOUT re-extracting or re-aggregating their data.

For each requested week it reads the enhanced JSON that the upload stage stored
in DynamoDB (READ-ONLY get_item), restores the Decimal values, and regenerates
the weekly report HTML locally. Nothing is uploaded: review the files, then
deploy each one with the HTML-only deploy command the script prints.

HTML-only deploy matters: passing enhanced JSON to the deploy stage would also
rebuild the season overview / hub / survivor pages from that (stale) week,
because every past week was stored with metadata.is_latest_week = True.

Run from the repo root:
    python scripts/backfill_restyle.py --season 2026 --weeks 1-4
    python scripts/backfill_restyle.py --season 2026 --weeks 2 --check-only
"""
import argparse
import json
import os
import sys
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

import boto3  # noqa: E402

from generators.templated_html_generator import (  # noqa: E402
    TemplatedFantasyHTMLGenerator,
    theme_for_season,
)
from utils.config import get_config  # noqa: E402

DATA_TYPE_ID = "weekly_report"


def parse_weeks(spec: str) -> List[int]:
    """Parse '1-4', '1,3,5' or '2' into a sorted list of week numbers."""
    weeks = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            weeks.update(range(int(start), int(end) + 1))
        elif part:
            weeks.add(int(part))
    return sorted(weeks)


def restore_decimals(obj: Any) -> Any:
    """Undo the upload stage's float->Decimal conversion (whole numbers -> int)."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, dict):
        return {k: restore_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [restore_decimals(v) for v in obj]
    return obj


def fetch_week(table, season: int, week: int) -> Optional[Dict[str, Any]]:
    """Read one stored weekly report (read-only). Returns the item or None."""
    response = table.get_item(Key={"season_week": f"{season}-{week:02d}", "data_type_id": DATA_TYPE_ID})
    item = response.get("Item")
    return restore_decimals(item) if item else None


def validate(item: Dict[str, Any], season: int, week: int, league_id: Any) -> List[str]:
    """Return a list of problems that make a stored record unsafe to re-render."""
    problems = []
    data = item.get("data")
    if not isinstance(data, dict):
        return ["record has no 'data' document"]
    if str(item.get("league_id")) != str(league_id):
        problems.append(f"league_id {item.get('league_id')} != configured {league_id}")
    if "current_week" not in data or "season_context" not in data:
        problems.append("stored data is not an enhanced report (missing current_week/season_context)")
    meta = data.get("metadata", {})
    if meta.get("error"):
        problems.append(f"stored enhanced data was a fallback after an error: {meta.get('error')}")
    stored_week = data.get("current_week", {}).get("week", item.get("week"))
    if stored_week is not None and int(stored_week) != week:
        problems.append(f"stored week {stored_week} != requested week {week}")
    stored_season = meta.get("season", item.get("season"))
    if stored_season is not None and int(stored_season) != season:
        problems.append(f"stored season {stored_season} != requested season {season}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--season", type=int, required=True, help="Season year, e.g. 2026")
    parser.add_argument("--weeks", required=True, help="Weeks to re-render: '1-4', '1,3' or '2'")
    parser.add_argument("--output-dir", default=os.path.join(REPO_ROOT, "output", "backfill"),
                        help="Where to write recovered JSON and re-rendered HTML (default: output/backfill)")
    parser.add_argument("--profile", help="AWS profile override (default: pipeline.aws.profile from config)")
    parser.add_argument("--check-only", action="store_true",
                        help="Only fetch + validate the stored records; don't render")
    args = parser.parse_args()

    config = get_config()
    aws = config.pipeline.aws
    league_id = config.league.league_id
    profile = args.profile or aws.profile
    session = boto3.Session(profile_name=profile, region_name=aws.region) if profile \
        else boto3.Session(region_name=aws.region)
    table = session.resource("dynamodb").Table(aws.dynamodb_table)  # type: ignore[attr-defined]

    # The deploy stage derives the S3 season from the HTML filename's timestamp,
    # so HTML generated in a different calendar year would deploy to the wrong key.
    if args.season != datetime.now().year:
        print(f"WARNING: season {args.season} != current year {datetime.now().year}; "
              "`pipeline deploy` would map these files to the current year's S3 keys. Do not deploy them as-is.")

    os.makedirs(args.output_dir, exist_ok=True)
    generator = TemplatedFantasyHTMLGenerator()
    rendered, failed = [], []

    print(f"Table {aws.dynamodb_table} ({aws.region}), league {league_id}, season {args.season}, "
          f"theme '{theme_for_season(args.season, 'weekly')}'")
    for week in parse_weeks(args.weeks):
        item = fetch_week(table, args.season, week)
        if item is None:
            print(f"  week {week}: NOT FOUND in DynamoDB")
            failed.append(week)
            continue

        problems = validate(item, args.season, week, league_id)
        data = item.get("data", {})
        meta = data.get("metadata", {}) if isinstance(data, dict) else {}
        summary = (f"stored {item.get('timestamp', '?')}, "
                   f"historical_weeks_included={meta.get('historical_weeks_included', '?')}")
        if problems:
            print(f"  week {week}: SKIPPED ({summary})")
            for problem in problems:
                print(f"      - {problem}")
            failed.append(week)
            continue
        if args.check_only:
            print(f"  week {week}: OK ({summary})")
            continue

        json_path = os.path.join(args.output_dir, f"enhanced_week_{week}_from_dynamodb.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Same naming as the generate stage so `pipeline deploy` parses the week correctly
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_path = os.path.join(args.output_dir, f"fantasy_report_week_{week}_{stamp}.html")
        generator.generate_html(data, html_path)
        rendered.append(html_path)
        print(f"  week {week}: rendered -> {os.path.relpath(html_path, REPO_ROOT)} ({summary})")

    if rendered:
        print("\nReview the files, then deploy each one HTML-only (uploads that week's page + invalidates it):")
        for path in rendered:
            print(f"  ./fantasy-extractor pipeline deploy {os.path.relpath(path, REPO_ROOT)} --dry-run")
        print("  (drop --dry-run to upload)")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
