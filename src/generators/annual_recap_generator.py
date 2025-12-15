"""
Annual Recap Generator

Generates an interactive "Wrapped"-style annual recap website that transforms
season fantasy football results into an animated narrative experience.
"""

from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import json
from pathlib import Path


class AnnualRecapGenerator:
    """
    Generates annual recap HTML with:
    - Horse-race leaderboard animation
    - Season awards recap
    - Weekly highlights
    """

    def __init__(self, logger=None):
        self.logger = logger

    def generate(self, weekly_reports: List[Dict[str, Any]], output_path: str) -> str:
        """
        Generate annual recap HTML from weekly report data.

        Args:
            weekly_reports: List of weekly report data (from DynamoDB or JSON files)
            output_path: Path to save the generated HTML file

        Returns:
            Path to generated HTML file
        """
        if self.logger:
            self.logger.info(f"Generating annual recap from {len(weekly_reports)} weekly reports")

        # Extract league metadata from first report
        league_metadata = self._extract_league_metadata(weekly_reports)

        # Aggregate data across all weeks
        teams_data = self._aggregate_team_data(weekly_reports)
        awards_data = self._aggregate_awards_data(weekly_reports)
        weekly_highlights = self._aggregate_weekly_highlights(weekly_reports)

        # Generate HTML
        html_content = self._generate_html(teams_data, awards_data, weekly_highlights, league_metadata)

        # Save to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            f.write(html_content)

        if self.logger:
            self.logger.info(f"Annual recap saved to {output_file}")

        return str(output_file)

    def _extract_league_metadata(self, weekly_reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract league metadata (name, season, logo) from weekly reports."""
        # Default league logo URL
        default_logo_url = "https://will.moore.fyi/duke-football-invitational/static/duke-football-invitational-logo-v2.png"

        if not weekly_reports:
            return {'league_name': 'Fantasy League', 'season': 2024, 'league_logo_url': default_logo_url}

        first_report = weekly_reports[0]

        # Extract from report
        league_name = first_report.get('league_name', 'Fantasy League')
        season = int(first_report.get('season', 2024))  # Ensure integer
        league_logo_url = first_report.get('league_logo_url') or default_logo_url

        return {
            'league_name': league_name,
            'season': season,
            'league_logo_url': league_logo_url
        }

    def _aggregate_team_data(self, weekly_reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate team standings data across all weeks for horse-race animation.

        Returns:
            {
                'teams': [list of team info],
                'weekly_standings': [list of weekly rankings],
                'weekly_records': [list of weekly win/loss/points records]
            }
        """
        if not weekly_reports:
            return {'teams': [], 'weeklyStandings': [], 'weeklyRecords': []}

        # Extract teams from first report
        first_report = weekly_reports[0]
        teams = []
        team_id_to_info = {}

        # Build team list
        for division in first_report.get('divisions', []):
            for team in division.get('teams', []):
                team_info = {
                    'id': team['id'],
                    'name': team['name'],
                    'logo': team.get('logo', ''),
                    'owner': team.get('owner', '')
                }
                teams.append(team_info)
                team_id_to_info[team['id']] = team_info

        # Sort teams by ID for consistency
        teams.sort(key=lambda t: t['id'])

        # Calculate cumulative standings from matchup results
        weekly_standings = []
        weekly_records = []

        # Initialize running totals for each team
        team_stats = {team_id: {'wins': 0, 'losses': 0, 'points_for': 0.0, 'points_against': 0.0}
                     for team_id in range(1, len(teams) + 1)}

        for report in weekly_reports:
            matchups = report.get('matchups', [])

            # Update stats based on matchup results
            for matchup in matchups:
                home_team = matchup.get('home_team', {})
                away_team = matchup.get('away_team', {})
                home_score = float(matchup.get('home_score', 0.0))
                away_score = float(matchup.get('away_score', 0.0))
                winner_id = matchup.get('winner_id')

                home_id = home_team.get('id')
                away_id = away_team.get('id')

                if home_id and away_id:
                    # Update points for/against
                    team_stats[home_id]['points_for'] += home_score
                    team_stats[home_id]['points_against'] += away_score
                    team_stats[away_id]['points_for'] += away_score
                    team_stats[away_id]['points_against'] += home_score

                    # Update wins/losses
                    if winner_id == home_id:
                        team_stats[home_id]['wins'] += 1
                        team_stats[away_id]['losses'] += 1
                    elif winner_id == away_id:
                        team_stats[away_id]['wins'] += 1
                        team_stats[home_id]['losses'] += 1
                    # Ties: no win/loss update

            # Build rankings for this week based on cumulative stats
            team_standings = []
            for team_id in range(1, len(teams) + 1):
                stats = team_stats[team_id]
                team_standings.append({
                    'id': team_id,
                    'wins': stats['wins'],
                    'losses': stats['losses'],
                    'points_for': stats['points_for'],
                    'points_against': stats['points_against']
                })

            # Sort by standings (wins desc, losses asc, points_for desc, points_against asc)
            team_standings.sort(key=lambda t: (
                -t['wins'],
                t['losses'],
                -t['points_for'],
                t['points_against']
            ))

            # Extract team IDs in ranking order
            week_ranking = [t['id'] for t in team_standings]
            weekly_standings.append(week_ranking)

            # Extract records for display
            week_records = []
            for team_id in range(1, len(teams) + 1):
                stats = team_stats[team_id]
                week_records.append({
                    'wins': stats['wins'],
                    'losses': stats['losses'],
                    'points': stats['points_for']
                })

            weekly_records.append(week_records)

        return {
            'teams': teams,
            'weeklyStandings': weekly_standings,
            'weeklyRecords': weekly_records
        }

    def _aggregate_awards_data(self, weekly_reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate awards data across all weeks to find which teams won each award most.

        Returns:
            {
                'awards': [
                    {
                        'id': 'mvp',
                        'title': 'Most Valuable Player',
                        'icon': '🏆',
                        'winners': [
                            {
                                'teamName': 'Y',
                                'logo': 'Z',
                                'count': N,
                                'details': [{'week': W, 'stat': '...'}]
                            },
                            ...  # Multiple winners if tied
                        ]
                    },
                    ...
                ]
            }
        """
        # Track which team won each award in each week
        award_tracker = defaultdict(lambda: defaultdict(list))  # award_type -> team_name -> [weeks]

        award_definitions = {
            'mvp': {'title': 'Most Valuable Player', 'icon': '🏆'},
            'mwp': {'title': 'Most Wasted Player', 'icon': '😤'},
            'hsl': {'title': 'Highest Scoring Loser', 'icon': '💔'},
            'lsw': {'title': 'Lowest Scoring Winner', 'icon': '🍀'},
            'mup': {'title': 'Most Useless Player', 'icon': '🤦'},
            'mdp': {'title': 'Most Disrespected Player', 'icon': '🪑'},
            'ssl': {'title': 'Smartest Starting Lineup', 'icon': '🧠'},
            'ifm': {'title': 'I Fucked Myself', 'icon': '🤡'},
            'accidental_genius': {'title': 'Accidental Genius', 'icon': '🎲'},
            'mccollapse': {'title': 'Mike McCoy "McCollapse" Award', 'icon': '💀'},
            'clapper_collapse': {'title': 'Jason Garrett "The Clapper" Award', 'icon': '👏'},
        }

        # Collect award winners by week
        for report in weekly_reports:
            week = report.get('week')
            awards = report.get('awards', {})

            # Process each award type
            for award_id, award_def in award_definitions.items():
                award_data = awards.get(award_id)
                if award_data:
                    team_name = award_data.get('team_name')
                    if team_name:
                        # Build stat description based on award type
                        stat_desc = self._build_award_stat_description(award_id, award_data)
                        award_tracker[award_id][team_name].append({
                            'week': week,
                            'stat': stat_desc,
                            'raw_data': award_data
                        })

        # Determine winner for each award (team that won it most times)
        awards_list = []

        for award_id, award_def in award_definitions.items():
            if award_id not in award_tracker:
                continue

            team_counts = {team: len(weeks) for team, weeks in award_tracker[award_id].items()}
            if not team_counts:
                continue

            # Find team(s) with most wins (handle ties)
            max_count = max(team_counts.values())
            winner_teams = [team for team, count in team_counts.items() if count == max_count]

            # Build winners list (one or more teams if tied)
            winners = []
            for winner_team in winner_teams:
                winner_details = award_tracker[award_id][winner_team]
                team_logo = self._get_team_logo(weekly_reports, winner_team)

                winners.append({
                    'teamName': winner_team,
                    'logo': team_logo,
                    'count': max_count,
                    'details': [{'week': d['week'], 'stat': d['stat']} for d in winner_details]
                })

            awards_list.append({
                'id': award_id,
                'title': award_def['title'],
                'icon': award_def['icon'],
                'winners': winners  # Changed from 'winner' to 'winners' (list)
            })

        return {'awards': awards_list}

    def _build_award_stat_description(self, award_id: str, award_data: Dict[str, Any]) -> str:
        """Build a human-readable stat description for an award."""
        if award_id in ['mvp', 'mwp', 'mup', 'mdp']:
            # Player awards
            player_name = award_data.get('player_name', 'Unknown')
            score = award_data.get('score', 0.0)
            return f"{player_name} - {score:.1f} pts"
        elif award_id in ['hsl', 'lsw']:
            # Team score awards
            score = award_data.get('score', 0.0)
            additional_info = award_data.get('additional_info', '')
            if additional_info:
                return f"{score:.1f} pts - {additional_info}"
            return f"{score:.1f} pts"
        elif award_id in ['ssl', 'ifm', 'accidental_genius']:
            # Lineup efficiency awards
            actual_score = award_data.get('actual_score', 0.0)
            optimal_score = award_data.get('optimal_score', 0.0)
            efficiency_pct = award_data.get('efficiency_percentage', 0.0)
            return f"{actual_score:.1f} pts (optimal: {optimal_score:.1f}, {efficiency_pct:.1f}% efficiency)"
        elif award_id == 'mccollapse':
            # McCollapse award - would have won with optimal lineup
            actual_score = award_data.get('actual_score', 0.0)
            optimal_score = award_data.get('optimal_score', 0.0)
            opponent_score = award_data.get('opponent_score', 0.0)
            points_diff = award_data.get('points_difference', 0.0)
            return f"Scored {actual_score:.1f} (optimal: {optimal_score:.1f}) vs {opponent_score:.1f} - {points_diff:.1f} pt swing"
        elif award_id == 'clapper_collapse':
            # Clapper award - projected to win but lost
            projected_score = award_data.get('projected_score', 0.0)
            actual_score = award_data.get('actual_score', 0.0)
            opponent_actual = award_data.get('opponent_actual_score', 0.0)
            return f"Projected {projected_score:.1f}, scored {actual_score:.1f} vs {opponent_actual:.1f}"
        else:
            # Generic fallback
            return str(award_data)

    def _get_team_logo(self, weekly_reports: List[Dict[str, Any]], team_name: str) -> str:
        """Find a team's logo from weekly reports."""
        for report in weekly_reports:
            for division in report.get('divisions', []):
                for team in division.get('teams', []):
                    if team.get('name') == team_name:
                        return team.get('logo', '')
        return ''

    def _aggregate_weekly_highlights(self, weekly_reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate weekly highlights: highest scorer, lowest scorer, and winners.

        Returns:
            {
                'weeks': [
                    {
                        'week': 1,
                        'highestScorer': {...},
                        'lowestScorer': {...},
                        'winners': [...]
                    },
                    ...
                ]
            }
        """
        weeks_list = []

        for report in weekly_reports:
            week = report.get('week')
            matchups = report.get('matchups', [])

            # Find highest and lowest scorers
            all_scores = []
            for matchup in matchups:
                home_team = matchup.get('home_team', {})
                away_team = matchup.get('away_team', {})
                home_score = matchup.get('home_score', 0.0)
                away_score = matchup.get('away_score', 0.0)

                all_scores.append({
                    'team': home_team,
                    'score': home_score
                })
                all_scores.append({
                    'team': away_team,
                    'score': away_score
                })

            if not all_scores:
                continue

            # Sort by score
            all_scores.sort(key=lambda x: x['score'])
            lowest = all_scores[0]
            highest = all_scores[-1]

            # Find winners
            winners = []
            for matchup in matchups:
                winner_id = matchup.get('winner_id')
                if winner_id:
                    home_team = matchup.get('home_team', {})
                    away_team = matchup.get('away_team', {})

                    winner_team = home_team if home_team.get('id') == winner_id else away_team
                    winners.append({
                        'teamId': winner_team.get('id'),
                        'name': winner_team.get('name'),
                        'logo': winner_team.get('logo', '')
                    })

            weeks_list.append({
                'week': week,
                'highestScorer': {
                    'teamId': highest['team'].get('id'),
                    'teamName': highest['team'].get('name'),
                    'logo': highest['team'].get('logo', ''),
                    'score': highest['score']
                },
                'lowestScorer': {
                    'teamId': lowest['team'].get('id'),
                    'teamName': lowest['team'].get('name'),
                    'logo': lowest['team'].get('logo', ''),
                    'score': lowest['score']
                },
                'winners': winners
            })

        return {'weeks': weeks_list}

    def _convert_decimals(self, obj: Any) -> Any:
        """Recursively convert Decimal objects to float/int for JSON serialization."""
        from decimal import Decimal

        if isinstance(obj, Decimal):
            # Convert to int if it's a whole number, otherwise float
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        else:
            return obj

    def _generate_html(self, teams_data: Dict[str, Any],
                      awards_data: Dict[str, Any],
                      weekly_highlights: Dict[str, Any],
                      league_metadata: Dict[str, Any]) -> str:
        """Generate the complete HTML content with embedded data."""

        # Read the template HTML from templates directory
        template_path = Path(__file__).parent / 'templates' / 'annual-recap-template.html'

        if not template_path.exists():
            raise FileNotFoundError(f"Template not found at {template_path}")

        with open(template_path, 'r') as f:
            html_content = f.read()

        # Convert Decimal objects to float before JSON serialization
        teams_data = self._convert_decimals(teams_data)
        awards_data = self._convert_decimals(awards_data)
        weekly_highlights = self._convert_decimals(weekly_highlights)
        league_metadata = self._convert_decimals(league_metadata)

        # Convert data to JSON strings for embedding
        teams_json = json.dumps(teams_data, indent=4)
        awards_json = json.dumps(awards_data, indent=4)
        weekly_json = json.dumps(weekly_highlights, indent=4)

        # Replace league metadata in HTML
        league_name = league_metadata.get('league_name', 'Fantasy League')
        season = league_metadata.get('season', 2024)
        league_logo_url = league_metadata.get('league_logo_url')

        # Replace title
        html_content = html_content.replace(
            '<title>Duke Football Invitational - 2024 Wrapped</title>',
            f'<title>{league_name} - {season} Wrapped</title>'
        )

        # Replace intro slide content with logo (no text since logo includes it)
        if league_logo_url:
            # Replace h1 with logo image (logo already has league name text)
            html_content = html_content.replace(
                '<h1>Duke Football<br>Invitational</h1>',
                f'<img src="{league_logo_url}" alt="{league_name}" style="max-height: 390px; width: auto; margin-bottom: 2rem;">'
            )
            if self.logger:
                self.logger.info(f"Added league logo: {league_logo_url}")
        else:
            # No logo available, just update the text
            html_content = html_content.replace(
                '<h1>Duke Football<br>Invitational</h1>',
                f'<h1>{league_name}</h1>'
            )

        # Update season year
        html_content = html_content.replace(
            '<p>2024 Season Wrapped</p>',
            f'<p>{season} Season Wrapped</p>'
        )

        # Replace the dummy data in the template
        # Replace teamData
        html_content = html_content.replace(
            '// Sample data structure (replace with real data)\n        const teamData = {',
            '// Real data from generator\n        const teamData = {'
        )

        # Find and replace the data objects
        import re

        # Replace teamData (using a lambda to avoid escape sequence issues)
        team_data_pattern = r'const teamData = \{[\s\S]*?\};'
        html_content = re.sub(team_data_pattern,
                             lambda m: f'const teamData = {teams_json};',
                             html_content, count=1)

        # Replace awardsData
        awards_data_pattern = r'const awardsData = \{[\s\S]*?\n\};'
        html_content = re.sub(awards_data_pattern,
                             lambda m: f'const awardsData = {awards_json};',
                             html_content, count=1)

        # Replace weeklyRecapData
        weekly_data_pattern = r'const weeklyRecapData = \{[\s\S]*?\n\};'
        html_content = re.sub(weekly_data_pattern,
                             lambda m: f'const weeklyRecapData = {weekly_json};',
                             html_content, count=1)

        return html_content
