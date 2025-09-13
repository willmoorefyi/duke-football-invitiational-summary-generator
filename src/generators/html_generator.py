"""
HTML Generator for Fantasy Football Reports

This module generates HTML websites from fantasy football JSON data.
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class FantasyHTMLGenerator:
    """Generates HTML websites from fantasy football JSON data."""
    
    def __init__(self):
        """Initialize the HTML generator."""
        pass
    
    def generate_html(self, json_data: Dict[str, Any], output_path: str) -> None:
        """
        Generate HTML report from fantasy football JSON data.
        
        Args:
            json_data: Fantasy football report data
            output_path: Path to save the HTML file
        """
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
</head>
<body>
    <div class="container">
        {self._build_header(data)}
        {self._build_overall_standings(data)}
        {self._build_weekly_totals(data)}
        {self._build_strength_of_schedule(data)}
        {self._build_lineup_accuracy(data)}
        {self._build_weekly_awards(data)}
        {self._build_game_summaries(data)}
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
            font-family: 'Courier New', monospace;
            background-color: #ffffff;
            color: #000000;
            line-height: 1.4;
            font-size: 12px;
        }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
        }
        
        h1 {
            text-align: center;
            font-size: 24px;
            margin-bottom: 10px;
            font-weight: bold;
        }
        
        h2 {
            font-size: 16px;
            margin: 20px 0 10px 0;
            font-weight: bold;
        }
        
        h3 {
            font-size: 14px;
            margin: 15px 0 5px 0;
            font-weight: bold;
        }
        
        .section-divider {
            border-bottom: 1px solid #000;
            margin: 15px 0;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 15px;
            font-size: 11px;
        }
        
        th, td {
            padding: 3px 5px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        th {
            font-weight: bold;
            background-color: #f5f5f5;
        }
        
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        
        .team-logo {
            width: 20px;
            height: 20px;
            vertical-align: middle;
            margin-right: 5px;
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
        """
    
    def _build_header(self, data: Dict[str, Any]) -> str:
        """Build the header section."""
        report_date = datetime.fromisoformat(data['report_date'].replace('Z', '+00:00'))
        formatted_date = report_date.strftime("%B %d, %Y at %I:%M %p")
        
        return f"""
        <h1>{data['league_name']}</h1>
        <div class="center">
            <strong>Week {data['week']} - {data['season']}</strong><br>
            Generated: {formatted_date}
        </div>
        <div class="section-divider"></div>
        """
    
    def _build_overall_standings(self, data: Dict[str, Any]) -> str:
        """Build the overall league standings section."""
        html = """
        <h2>Overall League Standings</h2>
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Team</th>
                    <th>Owner</th>
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
            logo_img = f'<img src="{team["logo"]}" class="team-logo" alt="{team["name"]}">' if team.get("logo") else ""
            html += f"""
                <tr>
                    <td class="numeric">{team['overall_rank']}</td>
                    <td class="team-name">{logo_img}{team['name']}</td>
                    <td>{team['owner']}</td>
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
    
    def _build_weekly_totals(self, data: Dict[str, Any]) -> str:
        """Build the weekly totals section."""
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
            logo_img = f'<img src="{team_data["logo"]}" class="team-logo" alt="{team_data["name"]}">' if team_data.get("logo") else ""
            
            html += f"""
                <tr>
                    <td class="team-name">{logo_img}{team_data['name']}</td>
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
        <table>
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
            logo_img = f'<img src="{team_data["team"]["logo"]}" class="team-logo" alt="{team_data["team"]["name"]}">' if team_data["team"].get("logo") else ""
            
            html += f"""
                <tr>
                    <td class="team-name">{logo_img}{team_data['team']['name']}</td>
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
        <h2>Game Summaries</h2>
        """
        
        for matchup in data['matchups']:
            html += self._build_matchup_summary(matchup)
        
        html += '<div class="section-divider"></div>'
        return html
    
    def _build_matchup_summary(self, matchup: Dict[str, Any]) -> str:
        """Build a single matchup summary."""
        home_team = matchup['home_team']
        away_team = matchup['away_team']
        
        home_logo = f'<img src="{home_team["logo"]}" class="team-logo" alt="{home_team["name"]}">' if home_team.get("logo") else ""
        away_logo = f'<img src="{away_team["logo"]}" class="team-logo" alt="{away_team["name"]}">' if away_team.get("logo") else ""
        
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
        """
        
        # Build player performance tables
        home_players = [p for p in matchup['players'] if p['team'] == home_team['name'] and p['is_starter']]
        away_players = [p for p in matchup['players'] if p['team'] == away_team['name'] and p['is_starter']]
        
        html += f"""
            <h3>{away_team['name']} Starters</h3>
            {self._build_player_table(away_players)}
            
            <h3>{home_team['name']} Starters</h3>
            {self._build_player_table(home_players)}
        </div>
        """
        
        return html
    
    def _build_player_table(self, players: List[Dict[str, Any]]) -> str:
        """Build a table of player performances."""
        html = """
        <table>
            <thead>
                <tr>
                    <th>Position</th>
                    <th>Player</th>
                    <th class="numeric">Projected</th>
                    <th class="numeric">Actual</th>
                    <th class="numeric">Diff</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
        """
        
        # Sort players by roster slot for consistent display
        position_order = ['QB', 'RB', 'WR', 'TE', 'OP', 'RB/WR/TE', 'K', 'D/ST']
        players_sorted = sorted(players, key=lambda p: position_order.index(p['roster_slot']) if p['roster_slot'] in position_order else 999)
        
        for player in players_sorted:
            diff = player['actual_score'] - player['projected_score']
            
            # Determine row class based on optimal lineup
            row_class = ""
            if not player['should_have_started']:
                row_class = ' class="should-bench"'
            
            # Injury status
            injury_class = ""
            injury_indicator = ""
            if player['injury_status'] != 'HEALTHY':
                if player['injury_status'] == 'QUESTIONABLE':
                    injury_class = "injury-questionable"
                    injury_indicator = " (Q)"
                elif player['injury_status'] in ['OUT', 'IR']:
                    injury_class = "injury-out" if player['injury_status'] == 'OUT' else "injury-ir"
                    injury_indicator = f" ({player['injury_status']})"
            
            html += f"""
                <tr{row_class}>
                    <td>{player['roster_slot']}</td>
                    <td class="{injury_class}">{player['name']}{injury_indicator}</td>
                    <td class="numeric">{player['projected_score']:.2f}</td>
                    <td class="numeric">{player['actual_score']:.2f}</td>
                    <td class="numeric">{diff:+.2f}</td>
                    <td>{'Bench' if not player['should_have_started'] else 'Start'}</td>
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