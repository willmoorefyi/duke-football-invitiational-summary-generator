"""
Verification harness for the 2026 look & feel refresh.

Generates reviewable HTML artifacts on disk from local data only (no AWS / ESPN):
  - output/html/hub.html       season hub (from real stored league history)
  - output/html/overview.html  per-season overview (restyled standings + weekly totals)

Run: python scripts/verify_2026_look.py
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from generators.templated_html_generator import TemplatedFantasyHTMLGenerator  # noqa: E402

HTML_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "html")
os.makedirs(HTML_DIR, exist_ok=True)

LOGO = "https://will.moore.fyi/duke-football-invitational/static/duke-football-invitational-logo-v2.png"


def latest_history():
    files = sorted(glob.glob(os.path.join(HTML_DIR, "..", "history", "league_history_380491_2007-2024_*.json")))
    return json.load(open(files[-1])) if files else None


# Real division / team layout pulled from the 2024 season in stored history.
DIVISIONS = {
    "Adams": ["Bad JuJu", "They Stole Danny's Dimes", "O'ahu State Warriors", "The Williams Football Team"],
    "Patrick": ["Team Team", "Topless Fondue", "All About That Bass", "Weak(ly) Showing"],
    "Smythe": ["Darnold Schwarzenegger", "Atlanta Faldone", "Moore's Law", "Honolulu Corpse Reviver"],
}

# Real team logo assets (from the league's static bucket) so the preview shows the
# logo treatment intact. Unmatched teams fall back to placeholder.png.
STATIC = "https://will.moore.fyi/duke-football-invitational/static"
LOGOS = {
    "Bad JuJu": f"{STATIC}/BadJujuAll2.png",
    "They Stole Danny's Dimes": f"{STATIC}/TheyStoleDannysDimesAll.png",
    "O'ahu State Warriors": f"{STATIC}/OahuStateWarriorsAll.png",
    "The Williams Football Team": f"{STATIC}/WilliamsFootballTeamAll.png",
    "Team Team": f"{STATIC}/TeamTeamAll2.png",
    "Topless Fondue": f"{STATIC}/ToplessFondueAll.png",
    "Weak(ly) Showing": f"{STATIC}/WeaklyShowingAll.png",
    "Darnold Schwarzenegger": f"{STATIC}/DarnoldSchwarzeneggerAll.png",
    "Atlanta Faldone": f"{STATIC}/AtlantaFaldoneAll2.png",
    "Moore's Law": f"{STATIC}/MooresLawAll2.png",
    "Honolulu Corpse Reviver": f"{STATIC}/HonoluluCorpseReviverAll2.png",
}


def logo_for(name):
    return LOGOS.get(name, f"{STATIC}/placeholder.png")


def build_enhanced():
    """A representative 12-team, multi-week enhanced dataset for the overview page."""
    teams, standings = [], {}
    tid = 1
    # Deterministic-but-varied records so standings sort meaningfully.
    for div, names in DIVISIONS.items():
        div_teams = []
        for i, name in enumerate(names):
            div_teams.append({"id": tid, "name": name, "logo": logo_for(name), "division": div})
            wins = (13 - tid) // 2
            standings[str(tid)] = {
                "team_name": name,
                "wins": wins,
                "losses": 4 - (wins if wins <= 4 else 4),
                "ties": 0,
                "points_for": 520.0 - tid * 7.5,
                "points_against": 460.0 + tid * 3.2,
                "overall_rank": tid,
                "division_rank": i + 1,
            }
            tid += 1
        teams.append({"name": div, "teams": div_teams})

    weeks = []
    for w in range(1, 5):
        weeks.append({
            "week": w,
            "median": 100.0 + w,
            "average": 104.0 + w,
            "max": 150.0 - w,
            "min": 70.0 + w,
            "std_dev": 18.0 - w * 0.4,
            "average_efficiency": 88.0 + w * 0.5,
            "max_team_name": "Bad JuJu",
            "min_team_name": "Weak(ly) Showing",
        })

    return {
        "current_week": {
            "league_id": 380491,
            "league_name": "Duke Football Invitational",
            "season": 2026,
            "week": 4,
            "report_date": "2026-09-29T10:34:03.569584",
            "divisions": teams,
            "matchups": [],
        },
        "season_context": {
            "team_standings": standings,
            "weekly_statistics": {"weeks": weeks},
        },
        "metadata": {"is_latest_week": True, "current_week": 4},
    }


def main():
    g = TemplatedFantasyHTMLGenerator()

    # Hub. available_*_years are illustrative here so the preview shows every link
    # state (active Overview, active Wrapped, and disabled "No overview"); in
    # production the deploy stage discovers these from S3 so links never 404.
    hub = g.build_hub_data(
        current_season=2026, current_week=4, leader_name="Bad JuJu",
        league_history=latest_history(), league_logo_url=LOGO,
        available_overview_years={2025},
        available_recap_years={2023, 2024},
        team_logos=LOGOS,
    )
    hub_path = os.path.join(HTML_DIR, "hub.html")
    g.generate_hub_page(hub, hub_path)
    print("hub.html      ->", os.path.abspath(hub_path), f"({os.path.getsize(hub_path)} bytes)")

    # Overview
    ov_path = os.path.join(HTML_DIR, "overview.html")
    g.generate_overview_page(build_enhanced(), ov_path)
    print("overview.html ->", os.path.abspath(ov_path), f"({os.path.getsize(ov_path)} bytes)")


if __name__ == "__main__":
    main()
