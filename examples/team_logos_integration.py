#!/usr/bin/env python3
"""
Example: Team Logo Integration

Shows how to integrate the new team logos configuration into existing code.
"""

import json
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.team_logos import get_team_logo_url, update_team_data_with_logos


def example_html_generation_with_logos():
    """Example of how to use team logos in HTML generation."""

    # Simulate loading JSON data (like from extract stage)
    sample_data = {
        "league_name": "Duke Football Invitational",
        "divisions": [
            {
                "name": "Adams",
                "teams": [
                    {"id": 3, "name": "They Stole Danny's Dimes", "wins": 1, "losses": 0},
                    {"id": 9, "name": "The Williams Football Team", "wins": 1, "losses": 0}
                ]
            },
            {
                "name": "Smythe",
                "teams": [
                    {"id": 10, "name": "Atlanta Faldone", "wins": 1, "losses": 0},
                    {"id": 2, "name": "Moore's Law", "wins": 1, "losses": 0}
                ]
            }
        ]
    }

    # Add logos to all teams
    for division in sample_data["divisions"]:
        division["teams"] = update_team_data_with_logos(division["teams"])

    # Now generate HTML with logos
    html_output = generate_division_html(sample_data["divisions"])
    print("Generated HTML:")
    print(html_output)


def generate_division_html(divisions):
    """Generate HTML for divisions with team logos."""
    html_parts = ["<div class='divisions'>"]

    for division in divisions:
        html_parts.append(f"<h2>{division['name']} Division</h2>")
        html_parts.append("<div class='teams'>")

        for team in division["teams"]:
            team_name = team["name"]
            wins = team.get("wins", 0)
            losses = team.get("losses", 0)
            logo_url = team.get("logo_url", "")

            team_html = f"""
            <div class='team'>
                <img src='{logo_url}' alt='{team_name} logo' class='team-logo'
                     onerror="this.src='https://via.placeholder.com/100x100?text=No+Logo'" />
                <h3>{team_name}</h3>
                <p>Record: {wins}-{losses}</p>
            </div>"""

            html_parts.append(team_html)

        html_parts.append("</div>")

    html_parts.append("</div>")
    return "\n".join(html_parts)


def example_individual_logo_lookup():
    """Example of looking up individual team logos."""

    team_names = [
        "All About That Bass",
        "Atlanta Faldone",
        "Bad JuJu",
        "Non-existent Team"
    ]

    print("Individual logo lookups:")
    for team_name in team_names:
        logo_url = get_team_logo_url(team_name)
        if logo_url:
            print(f"✅ {team_name}: {logo_url}")
        else:
            print(f"❌ {team_name}: No logo found")


if __name__ == "__main__":
    print("=== Team Logo Integration Examples ===\n")

    print("1. Individual Logo Lookups:")
    example_individual_logo_lookup()

    print("\n" + "="*50 + "\n")

    print("2. HTML Generation with Logos:")
    example_html_generation_with_logos()