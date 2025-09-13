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
        <h2>Week {data['week']} Totals</h2>
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
        
        # Create team lookup for matchup data
        team_scores = {}
        for matchup in data['matchups']:
            team_scores[matchup['home_team']['id']] = {
                'name': matchup['home_team']['name'],
                'logo': matchup['home_team']['logo'],
                'actual': matchup['home_score'],
                'projected': matchup['home_projected_score'],
                'optimal': matchup['home_optimal_score']
            }
            team_scores[matchup['away_team']['id']] = {
                'name': matchup['away_team']['name'],
                'logo': matchup['away_team']['logo'],
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
            logo_html = self._render_logo(team_data["team"].get("logo", ""), team_data["team"]["name"])
            
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
    
    def _build_weekly_awards(self, data: Dict[str, Any]) -> str:
        """Build the weekly awards section."""
        if 'awards' not in data:
            return ""
        
        awards = data['awards']
        html = """
        <h2>Weekly Awards</h2>
        <div class="award-section">
        """
        
        # Individual Player Awards
        html += "<h3>Individual Player Awards</h3>"
        
        if 'mvp' in awards and awards['mvp']:
            award = awards['mvp']
            html += f'<div class="award-item"><strong>MVP:</strong> {award["player_name"]} ({award["team_name"]}) - {award["score"]:.2f} pts</div>'
        
        if 'mwp' in awards and awards['mwp']:
            award = awards['mwp']
            html += f'<div class="award-item"><strong>MWP:</strong> {award["player_name"]} ({award["team_name"]}) - {award["score"]:.2f} pts</div>'
        
        if 'mup' in awards and awards['mup']:
            award = awards['mup']
            html += f'<div class="award-item"><strong>MUP:</strong> {award["player_name"]} ({award["team_name"]}) - {award["score"]:.2f} pts</div>'
        
        if 'mdp' in awards and awards['mdp']:
            award = awards['mdp']
            html += f'<div class="award-item"><strong>MDP:</strong> {award["player_name"]} ({award["team_name"]}) - {award["score"]:.2f} pts</div>'
        
        # Team Awards
        html += "<h3>Team Awards</h3>"
        
        if 'hsl' in awards and awards['hsl']:
            award = awards['hsl']
            html += f'<div class="award-item"><strong>HSL:</strong> {award["team_name"]} - {award["score"]:.2f} pts</div>'
        
        if 'lsw' in awards and awards['lsw']:
            award = awards['lsw']
            html += f'<div class="award-item"><strong>LSW:</strong> {award["team_name"]} - {award["score"]:.2f} pts</div>'
        
        # Lineup Efficiency Awards
        html += "<h3>Lineup Efficiency Awards</h3>"
        
        if 'ssl' in awards and awards['ssl']:
            award = awards['ssl']
            html += f'<div class="award-item"><strong>SSL:</strong> {award["team_name"]} - {award["efficiency_percentage"]:.1f}% efficiency</div>'
        
        if 'ifm' in awards and awards['ifm']:
            award = awards['ifm']
            html += f'<div class="award-item"><strong>IFM:</strong> {award["team_name"]} - {award["efficiency_percentage"]:.1f}% efficiency</div>'
        
        if 'accidental_genius' in awards and awards['accidental_genius']:
            award = awards['accidental_genius']
            html += f'<div class="award-item"><strong>Accidental Genius:</strong> {award["team_name"]} - {award["efficiency_percentage"]:.1f}% efficiency</div>'
        
        # Collapse Awards
        html += "<h3>Collapse Awards</h3>"
        
        if 'mccollapse' in awards and awards['mccollapse']:
            for award in awards['mccollapse']:
                html += f'<div class="award-item"><strong>McCollapse:</strong> {award["team_name"]} - Lost by {award["points_difference"]:.2f} pts with optimal lineup</div>'
        
        if 'clapper_collapse' in awards and awards['clapper_collapse']:
            for award in awards['clapper_collapse']:
                html += f'<div class="award-item"><strong>Clapper Collapse:</strong> {award["team_name"]} - Projected to win but lost</div>'
        
        html += """
        </div>
        <div class="section-divider"></div>
        """
        return html
    
    def _build_game_summaries(self, data: Dict[str, Any]) -> str:
        """Build the game summaries section."""
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
            html += self._build_matchup_summary(matchup)
        
        html += '<div class="section-divider"></div>'
        return html
    
    def _build_matchup_summary(self, matchup: Dict[str, Any]) -> str:
        """Build a single matchup summary."""
        home_team = matchup['home_team']
        away_team = matchup['away_team']
        
        home_logo = self._render_logo(home_team.get("logo", ""), home_team["name"])
        away_logo = self._render_logo(away_team.get("logo", ""), away_team["name"])
        
        html = f"""
        <div class="matchup">
            <div class="matchup-header">
                <span class="team-name">{away_logo}{away_team['name']}</span>
                <span class="vs">@</span>
                <span class="team-name">{home_logo}{home_team['name']}</span>
            </div>
            
            <div class="center">
                <span class="score">{away_team['name']}: {matchup['away_score']:.2f}</span>
                <span class="projected">(proj: {matchup['away_projected_score']:.2f})</span>
                <span class="vs">vs</span>
                <span class="score">{home_team['name']}: {matchup['home_score']:.2f}</span>
                <span class="projected">(proj: {matchup['home_projected_score']:.2f})</span>
            </div>
            
            <div class="teams-side-by-side">
                <div class="team-column">
                    <h3>{away_team['name']}</h3>
                    {self._build_team_player_table(matchup['players'], away_team['name'])}
                </div>
                <div class="team-column">
                    <h3>{home_team['name']}</h3>
                    {self._build_team_player_table(matchup['players'], home_team['name'])}
                </div>
            </div>
        </div>
        """
        
        return html
    
    def _build_team_player_table(self, all_players: List[Dict[str, Any]], team_name: str) -> str:
        """Build a table of player performances for a specific team."""
        # Filter players for this team
        team_players = [p for p in all_players if p['team'] == team_name]
        
        # Find MVP (highest scoring starter) and LVPs (starters who shouldn't have started)
        starters = [p for p in team_players if p['is_starter']]
        mvp_player = max(starters, key=lambda p: p['actual_score']) if starters else None
        
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
        
        # Sort players: starters first, then bench
        position_order = ['QB', 'RB', 'WR', 'TE', 'OP', 'RB/WR/TE', 'K', 'D/ST']
        starters_sorted = sorted([p for p in team_players if p['is_starter']], 
                                key=lambda p: position_order.index(p['roster_slot']) if p['roster_slot'] in position_order else 999)
        bench_sorted = sorted([p for p in team_players if not p['is_starter']], 
                             key=lambda p: position_order.index(p['roster_slot']) if p['roster_slot'] in position_order else 999)
        
        # Combine: starters first, then bench
        all_sorted = starters_sorted + bench_sorted
        
        for player in all_sorted:
            # Determine MVP/LVP status
            mvp_lvp = ""
            row_class = ""
            
            if player['is_starter']:
                if player == mvp_player:
                    mvp_lvp = "MVP"
                    row_class = ' class="mvp-row"'
                elif not player['should_have_started']:
                    mvp_lvp = "LVP"
                    row_class = ' class="lvp-row"'
            else:
                # Bench player who should have started
                if player['should_have_started']:
                    row_class = ' class="should-start-row"'
            
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
        
        html += """
            </tbody>
        </table>
        """
        return html
    
    def _build_footer(self, data: Dict[str, Any]) -> str:
        """Build the footer section."""
        return f"""
        <div class="footer">
            <p>Generated by Duke Football Invitational Summary Generator</p>
            <p>Report Date: {data['report_date']}</p>
        </div>
        """