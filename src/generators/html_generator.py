"""
HTML Generator for Fantasy Football Reports

This module generates HTML websites from fantasy football JSON data.
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

try:
    from ..utils.logo_validator import get_logo_validator
except ImportError:
    from utils.logo_validator import get_logo_validator


class FantasyHTMLGenerator:
    """Generates HTML websites from fantasy football JSON data."""

    def __init__(self, validate_logos: bool = False):
        """Initialize the HTML generator."""
        # Server-side logo validation disabled - using client-side validation instead
        # self.validate_logos = validate_logos
        # if validate_logos:
        #     self.logo_validator = get_logo_validator()
        self.validate_logos = False

    def generate_html(self, json_data: Dict[str, Any], output_path: str) -> None:
        """
        Generate HTML report from fantasy football JSON data.

        Args:
            json_data: Fantasy football report data
            output_path: Path to save the HTML file
        """
        # Server-side logo validation disabled - using client-side validation instead
        # if self.validate_logos:
        #     json_data = self._validate_team_logos(json_data)

        html_content = self._build_html_template(json_data)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def generate_from_file(self, json_file_path: str, output_path: str) -> None:
        """
        Generate HTML report from JSON file.

        Args:
            json_file_path: Path to JSON report file
            output_path: Path to save the HTML file
        """
        with open(json_file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        self.generate_html(json_data, output_path)

    # Server-side logo validation method (commented out - now using client-side validation)
    # def _validate_team_logos(self, data: Dict[str, Any]) -> Dict[str, Any]:
    #     """
    #     Validate team logos and replace invalid ones with poop emoji.
    #
    #     Args:
    #         data: Fantasy football report data
    #
    #     Returns:
    #         Updated data with validated logos
    #     """
    #     # Make a copy to avoid modifying original data
    #     import copy
    #     validated_data = copy.deepcopy(data)
    #
    #     # Validate logos in divisions/teams
    #     for division in validated_data.get('divisions', []):
    #         for team in division.get('teams', []):
    #             if 'logo' in team and team['logo']:
    #                 team['logo'] = self.logo_validator.get_validated_logo(team['logo'])
    #
    #     # Validate logos in matchups
    #     for matchup in validated_data.get('matchups', []):
    #         # Validate home team logo
    #         if 'home_team' in matchup and 'logo' in matchup['home_team'] and matchup['home_team']['logo']:
    #             matchup['home_team']['logo'] = self.logo_validator.get_validated_logo(matchup['home_team']['logo'])
    #
    #         # Validate away team logo
    #         if 'away_team' in matchup and 'logo' in matchup['away_team'] and matchup['away_team']['logo']:
    #             matchup['away_team']['logo'] = self.logo_validator.get_validated_logo(matchup['away_team']['logo'])
    #
    #     return validated_data

    def _create_team_logo_lookup(self, data: Dict[str, Any]) -> Dict[str, str]:
        """
        Create a comprehensive team logo lookup that prioritizes division data over matchup data.

        Args:
            data: Fantasy football report data

        Returns:
            Dictionary mapping team names to their logo URLs
        """
        team_logo_lookup = {}

        # First, populate from matchup data
        for matchup in data.get('matchups', []):
            team_logo_lookup[matchup['home_team']['name']] = matchup['home_team'].get('logo', '')
            team_logo_lookup[matchup['away_team']['name']] = matchup['away_team'].get('logo', '')

        # Then override with division data (higher priority - these URLs are more reliable)
        for division in data.get('divisions', []):
            for team in division.get('teams', []):
                if team.get('logo'):
                    team_logo_lookup[team['name']] = team['logo']

        return team_logo_lookup

    def _render_logo(self, logo_url: str, team_name: str) -> str:
        """
        Render a team logo with client-side fallback to poop emoji if image fails to load.

        Args:
            logo_url: URL to the logo image
            team_name: Name of the team for alt text

        Returns:
            HTML string for the logo with error handling
        """
        if not logo_url:
            return ""

        # Always render as image with client-side error handling via JavaScript
        return f'<img src="{logo_url}" class="team-logo" alt="{team_name}">'

    def _render_team_logo_with_hover(self, team_info: Dict[str, str]) -> str:
        """
        Render a team logo with hover text showing team name.

        Args:
            team_info: Dictionary containing team information with 'logo', 'name', etc.

        Returns:
            HTML string for the logo with hover text
        """
        if not team_info or not team_info.get('logo'):
            return ""

        logo_url = team_info['logo']
        team_name = team_info['name']

        # Always render as image with client-side error handling and hover text
        return f'<img src="{logo_url}" class="team-logo" alt="{team_name}" title="{team_name}">'

    def _render_score_with_logo(self, score: float, team_info: Optional[Dict[str, str]]) -> str:
        """
        Render a score with team logo inline.

        Args:
            score: The numerical score
            team_info: Dictionary containing team information with 'logo', 'name', etc.

        Returns:
            HTML string combining score and logo
        """
        score_text = f"{score:.2f}"

        if not team_info or not team_info.get('logo'):
            return score_text

        logo_html = self._render_team_logo_with_hover(team_info)
        return f"{score_text} {logo_html}"

    def _build_html_template(self, data: Dict[str, Any]) -> str:
        """Build the complete HTML template with data."""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{data['league_name']} - Week {data['week']} Report</title>
    <style>
{self._get_css_styles()}
    </style>
    <script>
{self._get_javascript()}
    </script>
</head>
<body>
    <div class="container">
        {self._build_header(data)}
        {self._build_season_stats_section(data)}
        {self._build_weekly_stats_section(data)}
        {self._build_game_summaries_section(data)}
        {self._build_footer(data)}
    </div>
</body>
</html>"""
        return html

    def _get_css_styles(self) -> str:
        """Return CSS styles for the HTML template."""
        return """
        @import url('https://fonts.googleapis.com/css2?family=Audiowide:wght@400&display=swap');

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: Arial, Helvetica, sans-serif;
            background-color: #ffffff;
            color: #000000;
            line-height: 1.5;
            font-size: 13px;
            margin: 0;
            padding: 0;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 15px;
        }

        .league-title {
            text-align: center;
            font-size: 28px;
            margin-bottom: 15px;
            font-weight: bold;
            color: #333;
        }

        h1 {
            font-size: 24px;
            margin: 30px 0 20px 0;
            font-weight: bold;
            color: #222;
            border-bottom: 3px solid #333;
            padding-bottom: 8px;
        }

        h2 {
            font-size: 18px;
            margin: 25px 0 12px 0;
            font-weight: bold;
            color: #444;
            border-bottom: 2px solid #ddd;
            padding-bottom: 5px;
        }

        h3 {
            font-size: 16px;
            margin: 18px 0 8px 0;
            font-weight: bold;
            color: #555;
        }

        .section-divider {
            border-bottom: 1px solid #000;
            margin: 15px 0;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            font-size: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        th, td {
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }

        th {
            font-weight: bold;
            background-color: #f8f9fa;
            color: #495057;
            font-size: 13px;
            border-bottom: 2px solid #dee2e6;
        }

        tr:nth-child(even) {
            background-color: #f8f9fa;
        }

        tr:hover {
            background-color: #e9ecef;
        }

        .standings-table th, .standings-table td {
            padding: 6px 10px;
            font-size: 13px;
        }

        .standings-table th {
            background-color: #343a40;
            color: white;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .team-logo {
            width: 20px;
            height: 20px;
            vertical-align: middle;
            margin-right: 5px;
        }

        .emoji-logo {
            display: inline-block;
            font-size: 16px;
            line-height: 20px;
            width: 20px;
            text-align: center;
        }

        .team-name {
            white-space: nowrap;
        }

        .numeric {
            text-align: right;
        }

        .center {
            text-align: center;
        }

        .injury-questionable {
            color: #ff6600;
            font-weight: bold;
        }

        .injury-out {
            color: #ff0000;
            font-weight: bold;
        }

        .injury-ir {
            color: #cc0000;
            font-weight: bold;
        }

        .should-start {
            background-color: #90EE90;
        }

        .should-bench {
            background-color: #FFB6C1;
        }

        .award-section {
            margin: 10px 0;
        }

        .award-item {
            margin: 5px 0;
            padding: 3px;
            border-left: 3px solid #ccc;
            padding-left: 8px;
        }

        .matchup {
            margin: 15px 0;
            padding: 10px;
            border: 1px solid #ddd;
        }

        .matchup-header {
            font-weight: bold;
            margin-bottom: 10px;
            padding: 5px;
            background-color: #f0f0f0;
        }

        .vs {
            font-weight: bold;
            margin: 0 10px;
        }

        .score {
            font-weight: bold;
            font-size: 14px;
        }

        .projected {
            color: #666;
            font-style: italic;
        }

        .footer {
            margin-top: 30px;
            text-align: center;
            color: #666;
            font-size: 10px;
        }

        /* Side-by-side team layout */
        .teams-side-by-side {
            display: flex;
            gap: 20px;
            margin-top: 15px;
        }

        .team-column {
            flex: 1;
        }

        /* MVP/LVP row styling */
        .mvp-row {
            background-color: rgb(255, 215, 64) !important;
        }

        .lvp-row {
            background-color: #FFCDD2 !important;
            color: #B71C1C !important;
        }

        .should-start-row {
            background-color: #C8E6C9 !important;
            color: #1B5E20 !important;
        }

        /* Award Cards Styling */
        .awards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }

        .award-card {
            border: 2px solid #333;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            background: white;
        }

        .award-header {
            padding: 15px;
            text-align: center;
            color: white;
        }

        .award-name {
            font-family: 'Audiowide', sans-serif;
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 8px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }

        .award-description {
            font-size: 14px;
            opacity: 0.9;
            font-style: italic;
        }

        .award-content {
            padding: 15px;
            background: white;
        }

        .award-player {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
        }

        .award-stats {
            font-size: 14px;
            color: #666;
            margin-bottom: 10px;
            font-style: italic;
        }

        .award-team {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 10px 0;
            border-top: 1px solid #eee;
        }

        .award-team-logo {
            width: 24px;
            height: 24px;
            margin-right: 8px;
        }

        .award-winner-logo {
            width: 20px;
            height: 20px;
            margin-right: 6px;
            vertical-align: middle;
        }

        .award-team-name {
            font-weight: bold;
            color: #333;
        }

        .award-winner-logo {
            width: 20px;
            height: 20px;
            margin-right: 6px;
            vertical-align: middle;
        }
        """

    def _get_javascript(self) -> str:
        """Return JavaScript for client-side logo validation."""
        return """
        // Client-side logo validation with fallback to poop emoji
        document.addEventListener('DOMContentLoaded', function() {
            // Function to replace failed logo with poop emoji
            function replaceWithPoop(imgElement) {
                const teamName = imgElement.alt || 'Team';
                const poopSpan = document.createElement('span');
                poopSpan.className = 'team-logo emoji-logo';
                poopSpan.textContent = '💩';
                poopSpan.title = `Logo failed to load for ${teamName}`;
                imgElement.parentNode.replaceChild(poopSpan, imgElement);
            }

            // Find all team logo images and add enhanced error handling
            const logoImages = document.querySelectorAll('img.team-logo');

            logoImages.forEach(function(img) {
                // Set a timeout to handle slow-loading images
                const timeout = setTimeout(function() {
                    replaceWithPoop(img);
                }, 10000); // 10 second timeout

                // Clear timeout if image loads successfully
                img.addEventListener('load', function() {
                    clearTimeout(timeout);
                });

                // Handle immediate errors
                img.addEventListener('error', function() {
                    clearTimeout(timeout);
                    replaceWithPoop(this);
                });

                // Check if image is already broken (in case it loaded before DOM was ready)
                if (img.complete && img.naturalWidth === 0) {
                    clearTimeout(timeout);
                    replaceWithPoop(img);
                }
            });
        });
        """

    def _build_header(self, data: Dict[str, Any]) -> str:
        """Build the header section."""
        report_date = datetime.fromisoformat(data['report_date'].replace('Z', '+00:00'))
        formatted_date = report_date.strftime("%B %d, %Y at %I:%M %p")

        return f"""
        <h1 class="league-title">{data['league_name']}</h1>
        <div class="center">
            <strong>Week {data['week']} - {data['season']}</strong><br>
            Generated: {formatted_date}
        </div>
        <div class="section-divider"></div>
        """

    def _build_season_stats_section(self, data: Dict[str, Any]) -> str:
        """Build the Season Stats section."""
        return f"""
        <h1>Season Stats</h1>
        {self._build_overall_standings(data)}
        {self._build_weekly_totals(data)}
        {self._build_week_specific_totals(data)}
        {self._build_strength_of_schedule(data)}
        {self._build_lineup_accuracy(data)}
        """

    def _build_weekly_stats_section(self, data: Dict[str, Any]) -> str:
        """Build the Weekly Stats section."""
        return f"""
        <h1>Weekly Stats</h1>
        {self._build_scoring_leaders(data)}
        {self._build_weekly_awards(data)}
        """

    def _build_game_summaries_section(self, data: Dict[str, Any]) -> str:
        """Build the Game Summaries section."""
        return f"""
        <h1>Game Summaries</h1>
        {self._build_game_summaries(data)}
        """

    def _build_overall_standings(self, data: Dict[str, Any]) -> str:
        """Build the overall league standings section."""
        html = """
        <h2>Overall League Standings</h2>
        <table class="standings-table">
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Team</th>
                    <th>Division</th>
                    <th class="numeric">W</th>
                    <th class="numeric">L</th>
                    <th class="numeric">T</th>
                    <th class="numeric">PF</th>
                    <th class="numeric">PA</th>
                </tr>
            </thead>
            <tbody>
        """

        # Collect all teams and sort by overall rank
        all_teams = []
        for division in data['divisions']:
            for team in division['teams']:
                all_teams.append(team)

        all_teams.sort(key=lambda x: x['overall_rank'])

        for team in all_teams:
            logo_html = self._render_logo(team.get("logo", ""), team["name"])
            html += f"""
                <tr>
                    <td class="numeric">{team['overall_rank']}</td>
                    <td class="team-name">{logo_html}{team['name']}</td>
                    <td>{team['division']}</td>
                    <td class="numeric">{team['wins']}</td>
                    <td class="numeric">{team['losses']}</td>
                    <td class="numeric">{team['ties']}</td>
                    <td class="numeric">{team['points_for']:.2f}</td>
                    <td class="numeric">{team['points_against']:.2f}</td>
                </tr>
            """

        html += """
            </tbody>
        </table>
        <div class="section-divider"></div>
        """
        return html

    def _build_week_specific_totals(self, data: Dict[str, Any]) -> str:
        """Build the week-specific totals section."""
        html = f"""
        <h2>Week {data['week']} Running Totals</h2>
        <table>
            <thead>
                <tr>
                    <th>Team</th>
                    <th class="numeric">Points</th>
                    <th class="numeric">Projected</th>
                    <th class="numeric">Optimal</th>
                    <th class="numeric">Efficiency %</th>
                </tr>
            </thead>
            <tbody>
        """

        # Create team lookup for matchup data with reliable logos
        team_logo_lookup = self._create_team_logo_lookup(data)

        team_scores = {}
        for matchup in data['matchups']:
            team_scores[matchup['home_team']['id']] = {
                'name': matchup['home_team']['name'],
                'logo': team_logo_lookup.get(matchup['home_team']['name'], ''),
                'actual': matchup['home_score'],
                'projected': matchup['home_projected_score'],
                'optimal': matchup['home_optimal_score']
            }
            team_scores[matchup['away_team']['id']] = {
                'name': matchup['away_team']['name'],
                'logo': team_logo_lookup.get(matchup['away_team']['name'], ''),
                'actual': matchup['away_score'],
                'projected': matchup['away_projected_score'],
                'optimal': matchup['away_optimal_score']
            }

        # Sort teams by points scored this week
        sorted_teams = sorted(team_scores.items(), key=lambda x: x[1]['actual'], reverse=True)

        for team_id, team_data in sorted_teams:
            efficiency = (team_data['actual'] / team_data['optimal'] * 100) if team_data['optimal'] > 0 else 0
            logo_html = self._render_logo(team_data.get("logo", ""), team_data["name"])

            html += f"""
                <tr>
                    <td class="team-name">{logo_html}{team_data['name']}</td>
                    <td class="numeric">{team_data['actual']:.2f}</td>
                    <td class="numeric">{team_data['projected']:.2f}</td>
                    <td class="numeric">{team_data['optimal']:.2f}</td>
                    <td class="numeric">{efficiency:.1f}%</td>
                </tr>
            """

        html += """
            </tbody>
        </table>
        <div class="section-divider"></div>
        """
        return html

    def _build_weekly_totals(self, data: Dict[str, Any]) -> str:
        """Build the weekly totals summary statistics table."""
        html = """
        <h2>Weekly Totals</h2>
        <table class="standings-table">
            <thead>
                <tr>
                    <th>Week</th>
                    <th class="numeric">Median</th>
                    <th class="numeric">Average</th>
                    <th class="numeric">Max</th>
                    <th class="numeric">Min</th>
                    <th class="numeric">Std Dev</th>
                </tr>
            </thead>
            <tbody>
        """

        # Calculate statistics for the current week
        week_stats = self._calculate_week_statistics(data)

        # Render combined score and team logo
        max_content = self._render_score_with_logo(week_stats['max'], week_stats['max_team'])
        min_content = self._render_score_with_logo(week_stats['min'], week_stats['min_team'])

        html += f"""
                <tr>
                    <td>Week {data['week']}</td>
                    <td class="numeric">{week_stats['median']:.2f}</td>
                    <td class="numeric">{week_stats['average']:.2f}</td>
                    <td class="numeric">{max_content}</td>
                    <td class="numeric">{min_content}</td>
                    <td class="numeric">{week_stats['std_dev']:.2f}</td>
                </tr>
        """

        html += """
            </tbody>
        </table>
        <div class="section-divider"></div>
        """
        return html

    def _calculate_week_statistics(self, data: Dict[str, Any]) -> Dict:
        """Calculate summary statistics for the week."""
        import statistics

        # Collect all team scores with team info for the week
        team_scores = []
        for matchup in data['matchups']:
            team_scores.append({
                'score': matchup['home_score'],
                'team': matchup['home_team']
            })
            team_scores.append({
                'score': matchup['away_score'],
                'team': matchup['away_team']
            })

        # Calculate statistics
        if not team_scores:
            return {
                'median': 0.0,
                'average': 0.0,
                'max': 0.0,
                'min': 0.0,
                'std_dev': 0.0,
                'max_team': None,
                'min_team': None
            }

        scores = [ts['score'] for ts in team_scores]
        max_score = max(scores)
        min_score = min(scores)

        # Find teams with max and min scores
        max_team = next(ts['team'] for ts in team_scores if ts['score'] == max_score)
        min_team = next(ts['team'] for ts in team_scores if ts['score'] == min_score)

        return {
            'median': statistics.median(scores),
            'average': statistics.mean(scores),
            'max': max_score,
            'min': min_score,
            'std_dev': statistics.stdev(scores) if len(scores) > 1 else 0.0,
            'max_team': max_team,
            'min_team': min_team
        }

    def _build_strength_of_schedule(self, data: Dict[str, Any]) -> str:
        """Build the strength of schedule section."""
        html = """
        <h2>Strength of Schedule</h2>
        <p><em>TBD - Coming Soon</em></p>
        <div class="section-divider"></div>
        """
        return html

    def _build_lineup_accuracy(self, data: Dict[str, Any]) -> str:
        """Build the lineup accuracy section."""
        # Create reliable team logo lookup
        team_logo_lookup = self._create_team_logo_lookup(data)

        html = """
        <h2>Lineup Accuracy</h2>
        <table class="standings-table">
            <thead>
                <tr>
                    <th>Team</th>
                    <th class="numeric">Actual Score</th>
                    <th class="numeric">Optimal Score</th>
                    <th class="numeric">Efficiency %</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
        """

        # Calculate efficiency for each team
        efficiency_data = []
        for matchup in data['matchups']:
            for team_key in ['home_team', 'away_team']:
                team = matchup[team_key]
                actual_key = f"{team_key.split('_')[0]}_score"
                optimal_key = f"{team_key.split('_')[0]}_optimal_score"

                actual = matchup[actual_key]
                optimal = matchup[optimal_key]
                efficiency = (actual / optimal * 100) if optimal > 0 else 0

                # Determine if they won or lost
                if matchup['winner_id'] == team['id']:
                    status = "Won"
                elif matchup['loser_id'] == team['id']:
                    status = "Lost"
                else:
                    status = "Tied"

                efficiency_data.append({
                    'team': team,
                    'actual': actual,
                    'optimal': optimal,
                    'efficiency': efficiency,
                    'status': status
                })

        # Sort by efficiency
        efficiency_data.sort(key=lambda x: x['efficiency'], reverse=True)

        for team_data in efficiency_data:
            logo_html = self._render_logo(team_logo_lookup.get(team_data["team"]["name"], ""), team_data["team"]["name"])

            html += f"""
                <tr>
                    <td class="team-name">{logo_html}{team_data['team']['name']}</td>
                    <td class="numeric">{team_data['actual']:.2f}</td>
                    <td class="numeric">{team_data['optimal']:.2f}</td>
                    <td class="numeric">{team_data['efficiency']:.1f}%</td>
                    <td>{team_data['status']}</td>
                </tr>
            """

        html += """
            </tbody>
        </table>
        <div class="section-divider"></div>
        """
        return html

    def _build_scoring_leaders(self, data: Dict[str, Any]) -> str:
        """Build the scoring leaders section for this week."""
        import statistics

        # Create reliable team logo lookup
        team_logo_lookup = self._create_team_logo_lookup(data)

        # Collect all team scores for this week with their matchup results
        team_scores = []
        for matchup in data['matchups']:
            # Determine winner/loser for each team
            home_result = "W" if matchup.get('winner_id') == matchup['home_team']['id'] else ("L" if matchup.get('loser_id') == matchup['home_team']['id'] else "T")
            away_result = "W" if matchup.get('winner_id') == matchup['away_team']['id'] else ("L" if matchup.get('loser_id') == matchup['away_team']['id'] else "T")

            # Calculate margin (positive for winners, negative for losers)
            score_diff = abs(matchup['home_score'] - matchup['away_score'])
            home_margin = score_diff if home_result == "W" else (-score_diff if home_result == "L" else 0)
            away_margin = score_diff if away_result == "W" else (-score_diff if away_result == "L" else 0)

            team_scores.append({
                'team': matchup['home_team'],
                'score': matchup['home_score'],
                'result': home_result,
                'margin': home_margin
            })
            team_scores.append({
                'team': matchup['away_team'],
                'score': matchup['away_score'],
                'result': away_result,
                'margin': away_margin
            })

        # Sort teams by score (highest to lowest)
        team_scores.sort(key=lambda x: x['score'], reverse=True)

        # Calculate median
        scores = [ts['score'] for ts in team_scores]
        median_score = statistics.median(scores)

        html = """
        <h2>Scoring Leaders</h2>
        <table class="standings-table">
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Team</th>
                    <th class="numeric">Points</th>
                    <th>Result</th>
                    <th class="numeric">Margin</th>
                </tr>
            </thead>
            <tbody>
        """

        for i, team_data in enumerate(team_scores):
            rank = i + 1
            logo_html = self._render_logo(team_logo_lookup.get(team_data['team']['name'], ""), team_data['team']["name"])

            # Add median row between ranks 6 and 7
            if rank == 7:
                html += f"""
                <tr style="background-color: #f0f0f0; font-style: italic;">
                    <td colspan="5" style="text-align: center; padding: 8px; font-weight: bold;">League Median: {median_score:.2f} pts</td>
                </tr>
                """

            # Format margin with + for positive, - for negative
            margin_display = f"+{team_data['margin']:.2f}" if team_data['margin'] > 0 else f"{team_data['margin']:.2f}"
            if team_data['margin'] == 0:
                margin_display = "0.00"

            html += f"""
                <tr>
                    <td class="numeric">{rank}</td>
                    <td class="team-name">{logo_html}{team_data['team']['name']}</td>
                    <td class="numeric">{team_data['score']:.2f}</td>
                    <td class="center">{team_data['result']}</td>
                    <td class="numeric">{margin_display}</td>
                </tr>
            """

        html += """
            </tbody>
        </table>
        <div class="section-divider"></div>
        """
        return html

    def _build_weekly_awards(self, data: Dict[str, Any]) -> str:
        """Build the weekly awards section with enhanced card layout."""
        if 'awards' not in data:
            return ""

        awards = data['awards']
        html = """
        <h2>Weekly Awards</h2>
        <div class="awards-grid">
        """

        # Define award definitions for descriptions
        award_definitions = {
            'mvp': 'Most Valuable Player',
            'mwp': 'Most Wasted Player',
            'mup': 'Most Useless Player',
            'mdp': 'Most Disrespected Player',
            'hsl': 'Highest Scoring Loser',
            'lsw': 'Lowest Scoring Winner',
            'ssl': 'Smartest Starting Lineup',
            'ifm': 'I Fucked Myself',
            'accidental_genius': 'Jerry Jones "Accidental Genius" Award',
            'mccollapse': 'Mike McCoy "McCollapse" Award',
            'clapper_collapse': 'Jason Garrett “Applauding Failure” Award'
        }

        # Calculate score rankings for HSL/LSW awards
        team_scores = []
        for matchup in data['matchups']:
            team_scores.append({'name': matchup['home_team']['name'], 'score': matchup['home_score']})
            team_scores.append({'name': matchup['away_team']['name'], 'score': matchup['away_score']})
        team_scores.sort(key=lambda x: x['score'], reverse=True)

        def get_score_rank(team_name):
            for i, team_data in enumerate(team_scores):
                if team_data['name'] == team_name:
                    rank = i + 1
                    if rank == 1:
                        return "1st highest"
                    elif rank == 2:
                        return "2nd highest"
                    elif rank == 3:
                        return "3rd highest"
                    else:
                        return f"{rank}th highest"
            return ""

        # Create comprehensive team logo lookup with division data priority
        team_logo_lookup = self._create_team_logo_lookup(data)

        # Individual Player Awards
        player_awards = ['mvp', 'mwp', 'mup', 'mdp']

        for award_key in player_awards:
            if award_key in awards and awards[award_key]:
                award = awards[award_key]
                team_bg_color, team_font_color = self._get_team_theme_colors(award['team_name'])
                team_logo_url = team_logo_lookup.get(award['team_name'], '')
                team_logo = self._render_logo(team_logo_url, award['team_name'])
                winner_logo = self._render_logo(team_logo_url, award['team_name']).replace('class="team-logo"', 'class="award-winner-logo"')

                html += f"""
                <div class="award-card" style="background-color: {team_bg_color};">
                    <div class="award-header" style="background-color: {team_bg_color}; color: {team_font_color};">
                        <div class="award-name">{award_key.upper()}</div>
                        <div class="award-description">{award_definitions[award_key]}</div>
                    </div>
                    <div class="award-content" style="background-color: {team_bg_color};">
                        <div class="award-player" style="font-size: 15px; color: {team_font_color};">{winner_logo}{award['player_name']}</div>
                        <div class="award-stats" style="color: {team_font_color};">Stats TBD</div>
                        <div class="award-team">
                            {team_logo}
                            <span class="award-team-name" style="color: {team_font_color}; font-size: 15px;">{award['team_name']}</span>
                        </div>
                    </div>
                </div>
                """

        # Team Awards
        team_awards = ['hsl', 'lsw', 'ssl', 'ifm', 'accidental_genius']

        for award_key in team_awards:
            if award_key in awards and awards[award_key]:
                award = awards[award_key]
                team_bg_color, team_font_color = self._get_team_theme_colors(award['team_name'])
                team_logo_url = team_logo_lookup.get(award['team_name'], '')
                team_logo = self._render_logo(team_logo_url, award['team_name'])

                # Determine the content based on award type
                if award_key == 'hsl' or award_key == 'lsw':
                    # Add score total and relative rank for HSL/LSW
                    score_rank = get_score_rank(award['team_name'])
                    content = f"{award['score']:.2f} pts ({score_rank})"
                elif award_key == 'ssl':
                    # SSL format: XX% of Optimal Score with note
                    actual_score = award.get('actual_score', 0)
                    optimal_score = award.get('optimal_score', 0)
                    content = f"{award['efficiency_percentage']:.1f}% of Optimal Score"
                    note = f"({actual_score:.2f} of {optimal_score:.2f} points)"
                elif award_key == 'ifm':
                    # IFM format: same as SSL
                    actual_score = award.get('actual_score', 0)
                    optimal_score = award.get('optimal_score', 0)
                    content = f"{award['efficiency_percentage']:.1f}% of Optimal Score"
                    note = f"({actual_score:.2f} of {optimal_score:.2f} points)"
                elif award_key == 'accidental_genius':
                    actual_score = award.get('actual_score', 0)
                    optimal_score = award.get('optimal_score', 0)
                    content = f"{award['efficiency_percentage']:.1f}% of Optimal Score"
                    note = f"({actual_score:.2f} of {optimal_score:.2f} points)"
                else:
                    content = f"{award['score']:.2f} pts"

                # Format award name for display
                award_name = award_key.upper()
                if award_key == 'accidental_genius':
                    award_name = 'ACCIDENTAL GENIUS'

                html += f"""
                <div class="award-card" style="background-color: {team_bg_color};">
                    <div class="award-header" style="background-color: {team_bg_color}; color: {team_font_color};">
                        <div class="award-name">{award_name}</div>
                        <div class="award-description">{award_definitions[award_key]}</div>
                    </div>
                    <div class="award-content" style="background-color: {team_bg_color};">
                        <div class="award-player" style="color: {team_font_color};">{content}</div>"""

                # Add note for SSL, IFM, and Accidental Genius
                if award_key in ['ssl', 'ifm', 'accidental_genius']:
                    html += f"""
                        <div class="award-stats" style="color: {team_font_color};">{note}</div>"""

                html += f"""
                        <div class="award-team">
                            {team_logo}
                            <span class="award-team-name" style="color: {team_font_color}; font-size: 15px;">{award['team_name']}</span>
                        </div>
                    </div>
                </div>
                """

        # Collapse Awards (can have multiple winners)
        if 'mccollapse' in awards and awards['mccollapse']:
            for award in awards['mccollapse']:
                team_bg_color, team_font_color = self._get_team_theme_colors(award['team_name'])
                team_logo_url = team_logo_lookup.get(award['team_name'], '')
                team_logo = self._render_logo(team_logo_url, award['team_name'])

                html += f"""
                <div class="award-card" style="background-color: {team_bg_color};">
                    <div class="award-header" style="background-color: {team_bg_color}; color: {team_font_color};">
                        <div class="award-name">MCCOLLAPSE</div>
                        <div class="award-description">{award_definitions['mccollapse']}</div>
                    </div>
                    <div class="award-content" style="background-color: {team_bg_color};">
                        <div class="award-player" style="color: {team_font_color};">Lost by {award['points_difference']:.2f} pts</div>
                        <div class="award-stats" style="color: {team_font_color};">With optimal lineup</div>
                        <div class="award-team">
                            {team_logo}
                            <span class="award-team-name" style="color: {team_font_color}; font-size: 15px;">{award['team_name']}</span>
                        </div>
                    </div>
                </div>
                """

        if 'clapper_collapse' in awards and awards['clapper_collapse']:
            for award in awards['clapper_collapse']:
                team_bg_color, team_font_color = self._get_team_theme_colors(award['team_name'])
                team_logo_url = team_logo_lookup.get(award['team_name'], '')
                team_logo = self._render_logo(team_logo_url, award['team_name'])

                html += f"""
                <div class="award-card" style="background-color: {team_bg_color};">
                    <div class="award-header" style="background-color: {team_bg_color}; color: {team_font_color};">
                        <div class="award-name">CLAPPER COLLAPSE</div>
                        <div class="award-description">{award_definitions['clapper_collapse']}</div>
                    </div>
                    <div class="award-content" style="background-color: {team_bg_color};">
                        <div class="award-player" style="color: {team_font_color};">Projected to win but lost</div>
                        <div class="award-team">
                            {team_logo}
                            <span class="award-team-name" style="color: {team_font_color}; font-size: 15px;">{award['team_name']}</span>
                        </div>
                    </div>
                </div>
                """

        html += """
        </div>
        <div class="section-divider"></div>
        """
        return html

    def _build_game_summaries(self, data: Dict[str, Any]) -> str:
        """Build the game summaries section."""
        # Create reliable team logo lookup
        team_logo_lookup = self._create_team_logo_lookup(data)

        html = """
        <h2>Game of the Week</h2>
        """

        # Sort matchups by score difference (closest games first)
        def calculate_score_difference(matchup):
            home_score = matchup['home_score']
            away_score = matchup['away_score']
            return abs(home_score - away_score)

        sorted_matchups = sorted(data['matchups'], key=calculate_score_difference)

        for matchup in sorted_matchups:
            html += self._build_matchup_summary(matchup, team_logo_lookup)

        html += '<div class="section-divider"></div>'
        return html

    def _build_matchup_summary(self, matchup: Dict[str, Any], team_logo_lookup: Dict[str, str]) -> str:
        """Build a single matchup summary."""
        home_team = matchup['home_team']
        away_team = matchup['away_team']

        home_logo = self._render_logo(team_logo_lookup.get(home_team["name"], ""), home_team["name"])
        away_logo = self._render_logo(team_logo_lookup.get(away_team["name"], ""), away_team["name"])

        # Get theme colors for both teams
        away_bg_color, away_font_color = self._get_team_theme_colors(away_team['name'])
        home_bg_color, home_font_color = self._get_team_theme_colors(home_team['name'])

        html = f"""
        <div class="matchup">
            <div class="center">
                <span class="score">{away_team['name']}: {matchup['away_score']:.2f}</span>
                <span class="projected">(proj: {matchup['away_projected_score']:.2f})</span>
                <span class="vs">vs</span>
                <span class="score">{home_team['name']}: {matchup['home_score']:.2f}</span>
                <span class="projected">(proj: {matchup['home_projected_score']:.2f})</span>
            </div>

            <div class="teams-side-by-side">
                <div class="team-column">
                    <h3 style="background-color: {away_bg_color}; color: {away_font_color}; padding: 8px 12px; border-radius: 4px; text-align: center;">{away_logo}{away_team['name']}</h3>
                    {self._build_team_player_table(matchup['players'], away_team['name'], matchup)}
                </div>
                <div class="team-column">
                    <h3 style="background-color: {home_bg_color}; color: {home_font_color}; padding: 8px 12px; border-radius: 4px; text-align: center;">{home_logo}{home_team['name']}</h3>
                    {self._build_team_player_table(matchup['players'], home_team['name'], matchup)}
                </div>
            </div>
        </div>
        """

        return html

    def _build_team_player_table(self, all_players: List[Dict[str, Any]], team_name: str, matchup: Dict[str, Any]) -> str:
        """Build a table of player performances for a specific team."""
        # Filter players for this team
        team_players = [p for p in all_players if p['team'] == team_name]

        # Find MVP (highest scoring starter) and LVPs (starters who shouldn't have started)
        starters = [p for p in team_players if p['is_starter']]
        mvp_player = max(starters, key=lambda p: p['actual_score']) if starters else None

        # Calculate total score for starters
        starter_total = sum(p['actual_score'] for p in starters)

        # Get optimal score and calculate accuracy for this team
        if matchup['home_team']['name'] == team_name:
            optimal_score = matchup.get('home_optimal_score', matchup.get('home_score', 0))
            actual_score = matchup.get('home_score', 0)
        else:  # away team
            optimal_score = matchup.get('away_optimal_score', matchup.get('away_score', 0))
            actual_score = matchup.get('away_score', 0)

        accuracy_percentage = (actual_score / optimal_score * 100) if optimal_score > 0 else 0

        # Get team theme colors for the "Should Have Started" row
        team_bg_color, team_font_color = self._get_team_theme_colors(team_name)

        html = """
        <table>
            <thead>
                <tr>
                    <th></th>
                    <th>Position</th>
                    <th>Player</th>
                    <th class="numeric">Points</th>
                </tr>
            </thead>
            <tbody>
        """

        # Sort starters by position
        position_order = ['QB', 'RB', 'WR', 'TE', 'OP', 'RB/WR/TE', 'K', 'D/ST']
        starters_sorted = sorted([p for p in team_players if p['is_starter']],
                                key=lambda p: position_order.index(p['roster_slot']) if p['roster_slot'] in position_order else 999)

        # Add all starters
        for player in starters_sorted:
            # Determine MVP/LVP status
            mvp_lvp = ""
            row_class = ""

            if player == mvp_player:
                mvp_lvp = "MVP"
                row_class = ' class="mvp-row"'
            elif not player['should_have_started']:
                mvp_lvp = "LVP"
                row_class = ' class="lvp-row"'

            # Injury status with mending heart emoji
            injury_indicator = ""
            if player['injury_status'] != 'HEALTHY':
                injury_indicator = " ❤️‍🩹"

            html += f"""
                <tr{row_class}>
                    <td class="center">{mvp_lvp}</td>
                    <td>{player['roster_slot']}</td>
                    <td>{player['name']}{injury_indicator}</td>
                    <td class="numeric">{player['actual_score']:.2f}</td>
                </tr>
            """

        # Add total row
        html += f"""
                <tr style="border-top: 2px solid #333;">
                    <td class="center"></td>
                    <td></td>
                    <td style="text-align: right; font-weight: bold;">Total:</td>
                    <td class="numeric" style="font-weight: bold;">{starter_total:.2f}</td>
                </tr>
        """

        # Add "Should Have Started" header row
        html += f"""
                <tr style="background-color: {team_bg_color}; color: {team_font_color};">
                    <td class="center"></td>
                    <td colspan="3" style="text-align: center; font-weight: bold; padding: 8px;">Should Have Started</td>
                </tr>
        """

        # Sort bench players: should-have-started first, then others, IR last
        bench_players = [p for p in team_players if not p['is_starter']]

        # Separate bench players by categories
        should_start = [p for p in bench_players if p['should_have_started'] and p['roster_slot'] != 'IR']
        regular_bench = [p for p in bench_players if not p['should_have_started'] and p['roster_slot'] != 'IR']
        ir_players = [p for p in bench_players if p['roster_slot'] == 'IR']

        # Sort each category by position
        should_start_sorted = sorted(should_start, key=lambda p: position_order.index(p['roster_slot']) if p['roster_slot'] in position_order else 999)
        regular_bench_sorted = sorted(regular_bench, key=lambda p: position_order.index(p['roster_slot']) if p['roster_slot'] in position_order else 999)
        ir_players_sorted = sorted(ir_players, key=lambda p: position_order.index(p['roster_slot']) if p['roster_slot'] in position_order else 999)

        # Combine bench players: should-start first, then regular bench, then IR
        bench_sorted = should_start_sorted + regular_bench_sorted + ir_players_sorted

        # Add bench players
        for player in bench_sorted:
            row_class = ""
            if player['should_have_started']:
                row_class = ' class="should-start-row"'

            # Injury status with mending heart emoji
            injury_indicator = ""
            if player['injury_status'] != 'HEALTHY':
                injury_indicator = " ❤️‍🩹"

            html += f"""
                <tr{row_class}>
                    <td class="center"></td>
                    <td>{player['roster_slot']}</td>
                    <td>{player['name']}{injury_indicator}</td>
                    <td class="numeric">{player['actual_score']:.2f}</td>
                </tr>
            """

        # Add optimal score and accuracy rows after all players
        html += f"""
                <tr style="background-color: #1B5E20; color: white;">
                    <td class="center"></td>
                    <td></td>
                    <td style="text-align: right; font-weight: bold;">Optimal:</td>
                    <td class="numeric" style="font-weight: bold;">{optimal_score:.2f}</td>
                </tr>
        """

        html += f"""
                <tr style="background-color: #1B5E20; color: white;">
                    <td class="center"></td>
                    <td></td>
                    <td style="text-align: right; font-weight: bold;">Accuracy (%):</td>
                    <td class="numeric" style="font-weight: bold;">{accuracy_percentage:.1f}%</td>
                </tr>
        """

        html += """
            </tbody>
        </table>
        """
        return html

    def _get_team_theme_color(self, team_name: str) -> str:
        """
        Get the theme background color for a specific team.

        Args:
            team_name: The name of the team

        Returns:
            RGB color string for the team's theme color
        """
        team_colors = {
            "They Stole Danny's Dimes": "rgb(189, 142, 156)",
            "All About That Bass": "rgb(179, 0, 21)",
            "Atlanta Faldone": "rgb(123, 0, 19)",
            "The Williams Football Team": "rgb(100, 54, 30)",
            "Moore's Law": "rgb(222, 176, 71)",
            "Topless Fondue": "rgb(35, 50, 98)",
            "O'ahu State Warriors": "rgb(100, 54, 30)",
            "Darnold Schwarzenegger": "rgb(244, 129, 25)",
            "Weak(ly) Showing": "rgb(0, 0, 0)",
            "Team Team": "rgb(27, 120, 51)",
            "Bad JuJu": "rgb(252, 1, 31)",
            "Honolulu Corpse Reviver": "rgb(212, 213, 214)"
        }
        return team_colors.get(team_name, "rgb(255, 255, 255)")  # Default to white

    def _get_team_font_color(self, team_name: str) -> str:
        """
        Get the appropriate font color for a team based on their theme color.

        Args:
            team_name: The name of the team

        Returns:
            RGB color string for the team's font color
        """
        import colorsys
        import math

        # Get the background color
        bg_color = self._get_team_theme_color(team_name)

        # Parse RGB values from "rgb(r, g, b)" format
        rgb_str = bg_color.replace("rgb(", "").replace(")", "")
        r, g, b = map(int, rgb_str.split(", "))

        # Step 1: Convert to relative luminance using W3C formula
        def linearize_srgb(value):
            """Convert sRGB value to linear RGB for luminance calculation"""
            value = value / 255.0
            if value <= 0.03928:
                return value / 12.92
            else:
                return math.pow((value + 0.055) / 1.055, 2.4)

        r_linear = linearize_srgb(r)
        g_linear = linearize_srgb(g)
        b_linear = linearize_srgb(b)

        bg_luminance = 0.2126 * r_linear + 0.7152 * g_linear + 0.0722 * b_linear

        # Step 2: Determine if background is light or dark (threshold 0.5)
        is_dark_bg = bg_luminance < 0.5

        # Convert background RGB to HSL
        r_norm, g_norm, b_norm = r/255.0, g/255.0, b/255.0
        h, l, s = colorsys.rgb_to_hls(r_norm, g_norm, b_norm)

        # Step 3: Check if highly saturated (S > 80% and L between 40%-60%)
        is_highly_saturated = s > 0.8 and 0.4 <= l <= 0.6

        # Apply hue shift for thematic appropriateness (+30° or -30°)
        # Choose direction based on team name hash for consistency
        hue_shift_direction = 1 if hash(team_name) % 2 == 0 else -1
        h_shifted = (h + (30.0 / 360.0) * hue_shift_direction) % 1.0

        # Desaturate if highly saturated
        s_adjusted = s * 0.5 if is_highly_saturated else s

        # Step 4: Adjust lightness to achieve 4.5:1 contrast ratio
        def contrast_ratio(lum1, lum2):
            """Calculate contrast ratio between two luminance values"""
            lighter = max(lum1, lum2)
            darker = min(lum1, lum2)
            return (lighter + 0.05) / (darker + 0.05)

        def luminance_from_lightness(lightness):
            """Approximate luminance from HSL lightness (simplified)"""
            # This is a rough approximation - actual conversion is more complex
            # but sufficient for our contrast calculation
            return lightness

        # Target contrast ratio of :1
        target_contrast = 7

        # Binary search for the right lightness value
        if is_dark_bg:
            # Dark background needs light text
            l_min, l_max = 0.5, 1.0
        else:
            # Light background needs dark text
            l_min, l_max = 0.0, 0.5

        # Find lightness that achieves target contrast
        best_l = l_min
        for _ in range(20):  # Binary search iterations
            test_l = (l_min + l_max) / 2
            test_luminance = luminance_from_lightness(test_l)
            contrast = contrast_ratio(bg_luminance, test_luminance)

            if contrast >= target_contrast:
                best_l = test_l
                if is_dark_bg:
                    l_max = test_l
                else:
                    l_min = test_l
            else:
                if is_dark_bg:
                    l_min = test_l
                else:
                    l_max = test_l

        # Convert back to RGB
        font_r, font_g, font_b = colorsys.hls_to_rgb(h_shifted, best_l, s_adjusted)

        # Convert to 0-255 range and format as RGB string
        font_r = int(round(font_r * 255))
        font_g = int(round(font_g * 255))
        font_b = int(round(font_b * 255))

        return f"rgb({font_r}, {font_g}, {font_b})"

    def _get_team_theme_colors(self, team_name: str) -> tuple:
        """
        Get the complete theme colors for a team (background and font color).

        Args:
            team_name: The name of the team

        Returns:
            Tuple of (background_color, font_color) as RGB color strings
        """
        background_color = self._get_team_theme_color(team_name)
        font_color = self._get_team_font_color(team_name)
        return (background_color, font_color)

    def _build_footer(self, data: Dict[str, Any]) -> str:
        """Build the footer section."""
        return f"""
        <div class="footer">
            <p>Generated by Duke Football Invitational Summary Generator</p>
            <p>Report Date: {data['report_date']}</p>
        </div>
        """