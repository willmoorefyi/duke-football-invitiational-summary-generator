"""
Templated HTML Generator for Fantasy Football Reports

This module generates HTML websites from fantasy football JSON data using Jinja2 templates.
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import statistics
import colorsys
import math

from jinja2 import Environment, FileSystemLoader, select_autoescape
try:
    from jinja2 import Markup
except ImportError:
    from markupsafe import Markup



class TemplatedFantasyHTMLGenerator:
    """Generates HTML websites from fantasy football JSON data using Jinja2 templates."""

    def __init__(self):
        """Initialize the templated HTML generator."""

        # Setup Jinja2 environment
        templates_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )

        # Add custom filters
        self.env.filters['render_logo'] = self._render_logo_filter

    def generate_html(self, json_data: Dict[str, Any], output_path: str) -> None:
        """
        Generate HTML report from fantasy football JSON data.

        Args:
            json_data: Fantasy football report data
            output_path: Path to save the HTML file
        """
        # Prepare all template variables
        template_vars = self._prepare_template_variables(json_data)

        # Render the main template
        template = self.env.get_template('main.html')
        html_content = template.render(**template_vars)

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

    def _prepare_template_variables(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare all variables needed for template rendering."""
        # Extract current week data for template processing
        if 'current_week' in data:
            # Enhanced data structure
            current_week_data = data['current_week']
            self.full_data = data  # Store full data for access to season_context
        else:
            # Raw data structure
            current_week_data = data
            self.full_data = data

        # Create centralized team logo lookup
        team_logos = self._create_team_logo_lookup(current_week_data)

        # Format date
        report_date = datetime.fromisoformat(current_week_data['report_date'].replace('Z', '+00:00'))
        formatted_date = report_date.strftime("%B %d, %Y at %I:%M %p")

        # Prepare all team data with computed standings merged in
        all_teams_sorted = []
        team_standings = self._get_team_standings_from_data(self.full_data)

        for division in current_week_data['divisions']:
            for team in division['teams']:
                # Merge team base data with computed standings
                team_with_standings = dict(team)  # Copy base team data

                # Add standings data if available
                team_id = team.get('id')
                if team_id and str(team_id) in team_standings:
                    standings_data = team_standings[str(team_id)]
                    team_with_standings.update({
                        'wins': standings_data.get('wins', 0),
                        'losses': standings_data.get('losses', 0),
                        'ties': standings_data.get('ties', 0),
                        'points_for': standings_data.get('points_for', 0.0),
                        'points_against': standings_data.get('points_against', 0.0),
                        'overall_rank': standings_data.get('overall_rank', 999),
                        'division_rank': standings_data.get('division_rank', 999)
                    })
                else:
                    # Fallback values if standings not available
                    team_with_standings.update({
                        'wins': 0, 'losses': 0, 'ties': 0,
                        'points_for': 0.0, 'points_against': 0.0,
                        'overall_rank': 999, 'division_rank': 999
                    })

                all_teams_sorted.append(team_with_standings)

        all_teams_sorted.sort(key=lambda x: x['overall_rank'])

        # Calculate week statistics (use pre-calculated from enhanced data if available)
        week_stats = self._get_week_statistics_data(self.full_data, current_week_data)

        # Prepare weekly awards data
        awards_data = self._prepare_awards_data(current_week_data, team_logos)

        # Prepare matchup data for game summaries
        matchups_data = self._prepare_matchups_data(current_week_data, team_logos)

        # Prepare running totals data (uses full data to access season_context)
        week_team_scores = self._prepare_running_totals_data(self.full_data, team_logos)

        # Prepare weekly summary data (scoring leaders for current week)
        weekly_summary_data = self._prepare_weekly_summary_data(current_week_data, team_logos)

        # Prepare strength of schedule data (uses full data to access season_context)
        strength_of_schedule_data = self._prepare_strength_of_schedule_data(self.full_data, team_logos)

        # Prepare division strength data (uses full data to access season_context)
        division_strength_data = self._prepare_division_strength_data(self.full_data, team_logos)

        # Prepare team lightbox data for interactive popover functionality
        team_lightbox_data = self._prepare_team_lightbox_data(self.full_data, team_logos)

        return {
            # Basic info
            'league_name': current_week_data['league_name'],
            'week': current_week_data['week'],
            'season': current_week_data['season'],
            'report_date': current_week_data['report_date'],
            'formatted_date': formatted_date,

            # Team data
            'team_logos': team_logos,
            'all_teams_sorted': all_teams_sorted,

            # Statistics
            'week_stats': week_stats,
            'all_weeks_stats': week_stats.get('all_weeks', []),
            'week_team_scores': week_team_scores,

            # Weekly Summary (scoring leaders for current week)
            'scoring_leaders_data': weekly_summary_data['team_scores'],
            'median_score': weekly_summary_data['median_score'],

            # Strength of Schedule
            'strength_of_schedule_teams': strength_of_schedule_data['teams'],
            'average_points_per_game': strength_of_schedule_data['average_points_per_game'],
            'sos_total_weeks': strength_of_schedule_data['total_weeks'],

            # Division Strength
            'division_strength_divisions': division_strength_data['divisions'],
            'division_strength_criteria': division_strength_data['ranking_criteria'],

            # Awards
            'player_awards': awards_data['player_awards'],
            'team_awards': awards_data['team_awards'],
            'collapse_awards': awards_data['collapse_awards'],
            'honorable_mentions': awards_data['honorable_mentions'],

            # Team lightbox data
            'team_lightbox_data': team_lightbox_data,

            # Game summaries
            'matchups_sorted': matchups_data,

            # Helper functions
            'render_logo': self._render_logo_helper,
            'get_team_theme_colors': self._get_team_theme_colors,
            'get_team_color_data': self._get_team_color_data,
            'lighten_color': self._lighten_color,
            'get_background_css': self._get_background_css,
            'get_combined_background': self._get_combined_background,
        }

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

    def _render_logo_filter(self, logo_url: str, team_name: str) -> Markup:
        """Jinja2 filter for rendering team logos."""
        return self._render_logo_helper(logo_url, team_name)

    def _get_team_standings_from_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract team standings from enhanced data structure.

        Args:
            data: Full data structure (enhanced or raw)

        Returns:
            Dictionary mapping team_id to standings data
        """
        # Check if this is enhanced data with computed standings
        if ('season_context' in data and 'team_standings' in data['season_context']):
            return data['season_context']['team_standings']

        # Fallback: return empty dict (will use fallback values)
        return {}

    def _render_logo_helper(self, logo_url: str, team_name: str, logo_class: str = "matchup-team-logo") -> Markup:
        """
        Render a team logo directly without fallback behavior.

        Args:
            logo_url: URL to the logo image
            team_name: Name of the team for alt text
            logo_class: CSS class for the logo (default: matchup-team-logo)

        Returns:
            HTML string for the logo (marked as safe for Jinja2)
        """
        if not logo_url:
            return Markup("")

        # Render as image without fallback logic
        return Markup(f'<img src="{logo_url}" class="{logo_class}" alt="{team_name}" title="{team_name}">')

    def _calculate_week_statistics(self, data: Dict[str, Any]) -> Dict:
        """Calculate summary statistics for the week."""
        # Collect all team scores with team info and efficiency data for the week
        team_scores = []
        team_efficiencies = []

        for matchup in data['matchups']:
            # Home team data - ensure proper type conversion
            home_score = float(matchup['home_score'])
            home_optimal = float(matchup.get('home_optimal_score', home_score))  # Fallback to actual if no optimal
            home_efficiency = (home_score / home_optimal * 100) if home_optimal > 0 else 0.0

            team_scores.append({
                'score': home_score,
                'team': matchup['home_team']
            })
            team_efficiencies.append(home_efficiency)

            # Away team data - ensure proper type conversion
            away_score = float(matchup['away_score'])
            away_optimal = float(matchup.get('away_optimal_score', away_score))  # Fallback to actual if no optimal
            away_efficiency = (away_score / away_optimal * 100) if away_optimal > 0 else 0.0

            team_scores.append({
                'score': away_score,
                'team': matchup['away_team']
            })
            team_efficiencies.append(away_efficiency)

        # Calculate statistics
        if not team_scores:
            return {
                'median': 0.0,
                'average': 0.0,
                'max': 0.0,
                'min': 0.0,
                'std_dev': 0.0,
                'average_efficiency': 0.0,
                'max_team_name': '',
                'max_logo_url': '',
                'min_team_name': '',
                'min_logo_url': '',
                'max_content': '0.00',
                'min_content': '0.00',
                'all_weeks': [{'week': 1, 'median': 0.0, 'average': 0.0, 'max': 0.0, 'min': 0.0, 'std_dev': 0.0, 'average_efficiency': 0.0, 'max_team_name': '', 'min_team_name': ''}]
            }

        scores = [ts['score'] for ts in team_scores]
        max_score = max(scores)
        min_score = min(scores)

        # Find teams with max and min scores
        max_team = next(ts['team'] for ts in team_scores if ts['score'] == max_score)
        min_team = next(ts['team'] for ts in team_scores if ts['score'] == min_score)

        # Calculate average efficiency
        average_efficiency = statistics.mean(team_efficiencies) if team_efficiencies else 0.0

        # Get team logos and prepare data for background styling
        team_logos = self._create_team_logo_lookup(data)
        max_logo_url = team_logos.get(max_team['name'], '')
        min_logo_url = team_logos.get(min_team['name'], '')

        return {
            'median': float(statistics.median(scores)),
            'average': float(statistics.mean(scores)),
            'max': float(max_score),
            'min': float(min_score),
            'std_dev': float(statistics.stdev(scores) if len(scores) > 1 else 0.0),
            'average_efficiency': float(average_efficiency),
            'max_team_name': str(max_team['name']),
            'max_logo_url': str(max_logo_url),
            'min_team_name': str(min_team['name']),
            'min_logo_url': str(min_logo_url),
            # Keep legacy fields for backward compatibility
            'max_content': f"{max_score:.2f}",
            'min_content': f"{min_score:.2f}"
        }

    def _get_week_statistics_data(self, full_data: Dict[str, Any], current_week_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get week statistics data - use pre-calculated from enhanced data if available,
        otherwise calculate from current week data.

        Args:
            full_data: Full data structure (may include season_context)
            current_week_data: Current week data for fallback calculation

        Returns:
            Dictionary with week statistics including current week and all weeks if available
        """
        # Check if we have enhanced data with pre-calculated weekly statistics
        if ('season_context' in full_data and
            'weekly_statistics' in full_data['season_context'] and
            'weeks' in full_data['season_context']['weekly_statistics']):

            # Use pre-calculated weekly statistics
            all_weeks_stats = full_data['season_context']['weekly_statistics']['weeks']

            # Find current week stats from the pre-calculated data
            current_week_num = current_week_data.get('week', 1)
            current_week_stats = None

            for week_stat in all_weeks_stats:
                if week_stat.get('week') == current_week_num:
                    current_week_stats = week_stat
                    break

            # If we didn't find current week in pre-calculated data, calculate it
            if not current_week_stats:
                current_week_stats = self._calculate_week_statistics(current_week_data)

            # Return structure with both current week and all weeks data
            return {
                **current_week_stats,  # Current week stats for backward compatibility
                'all_weeks': all_weeks_stats  # All weeks for template iteration
            }
        else:
            # Fall back to calculating current week only
            current_stats = self._calculate_week_statistics(current_week_data)
            return {
                **current_stats,
                'all_weeks': [current_stats]  # Single week wrapped in list
            }

    def _prepare_awards_data(self, data: Dict[str, Any], team_logos: Dict[str, str]) -> Dict[str, List]:
        """Prepare awards data for template rendering."""
        if 'awards' not in data:
            return {'player_awards': [], 'team_awards': [], 'collapse_awards': [], 'honorable_mentions': []}

        awards = data['awards']

        # Create player lookup for statistics
        player_lookup = self._create_player_lookup(data)

        # Award definitions for descriptions
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
            'clapper_collapse': 'Jason Garrett "Applauding Failure" Award'
        }

        # Calculate score rankings and create opponent lookup
        team_scores = []
        opponent_lookup = {}  # team_name -> opponent info

        for matchup in data['matchups']:
            home_team = matchup['home_team']['name']
            away_team = matchup['away_team']['name']
            home_score = matchup['home_score']
            away_score = matchup['away_score']

            team_scores.append({'name': home_team, 'score': home_score})
            team_scores.append({'name': away_team, 'score': away_score})

            # Create opponent lookup
            opponent_lookup[home_team] = {
                'name': away_team,
                'score': away_score
            }
            opponent_lookup[away_team] = {
                'name': home_team,
                'score': home_score
            }

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

        # Prepare player awards
        player_awards = []
        for award_key in ['mvp', 'mwp', 'mup', 'mdp']:
            if award_key in awards and awards[award_key]:
                award = awards[award_key]
                team_bg_color, team_font_color = self._get_team_theme_colors(award['team_name'])
                team_logo_url = team_logos.get(award['team_name'], '')
                team_logo = self._render_logo_helper(team_logo_url, award['team_name'], 'award-team-logo')
                winner_logo = self._render_logo_helper(team_logo_url, award['team_name'], 'award-winner-logo')

                # Look up player statistics
                player_key = (award.get('player_name'), award.get('team_name'))
                player_data = player_lookup.get(player_key)
                player_stats = self._get_player_stats_display(player_data)

                player_awards.append({
                    'name': award_key,
                    'description': award_definitions[award_key],
                    'data': award,
                    'player_stats': player_stats,
                    'team_bg_color': team_bg_color,
                    'team_font_color': team_font_color,
                    'team_logo': team_logo,
                    'winner_logo': winner_logo
                })

        # Prepare team awards
        team_awards = []
        for award_key in ['hsl', 'lsw', 'ssl', 'ifm', 'accidental_genius']:
            if award_key in awards and awards[award_key]:
                award = awards[award_key]
                team_bg_color, team_font_color = self._get_team_theme_colors(award['team_name'])
                team_logo_url = team_logos.get(award['team_name'], '')
                team_logo = self._render_logo_helper(team_logo_url, award['team_name'])

                # Determine content based on award type
                content = ""
                note = None
                display_name = award_key.upper()

                if award_key == 'hsl' or award_key == 'lsw':
                    score_rank = get_score_rank(award['team_name'])
                    content = f"{award['score']:.2f} pts ({score_rank})"
                    # Add opponent information
                    opponent_info = opponent_lookup.get(award['team_name'])
                    if opponent_info:
                        opponent_rank = get_score_rank(opponent_info['name'])
                        note = f"vs. {opponent_info['name']} - {opponent_info['score']:.2f} ({opponent_rank})"
                elif award_key == 'ssl':
                    actual_score = award.get('actual_score', 0)
                    optimal_score = award.get('optimal_score', 0)
                    content = f"{award['efficiency_percentage']:.1f}% of Optimal Score"
                    note = f"({actual_score:.2f} of {optimal_score:.2f} points)"
                elif award_key == 'ifm':
                    actual_score = award.get('actual_score', 0)
                    optimal_score = award.get('optimal_score', 0)
                    content = f"{award['efficiency_percentage']:.1f}% of Optimal Score"
                    note = f"({actual_score:.2f} of {optimal_score:.2f} points)"
                elif award_key == 'accidental_genius':
                    actual_score = award.get('actual_score', 0)
                    optimal_score = award.get('optimal_score', 0)
                    content = f"{award['efficiency_percentage']:.1f}% of Optimal Score"
                    note = f"({actual_score:.2f} of {optimal_score:.2f} points)"
                    display_name = 'ACCIDENTAL GENIUS'

                team_awards.append({
                    'key': award_key,
                    'display_name': display_name,
                    'description': award_definitions[award_key],
                    'data': award,
                    'content': content,
                    'note': note,
                    'team_bg_color': team_bg_color,
                    'team_font_color': team_font_color,
                    'team_logo': team_logo
                })

        # Prepare collapse awards
        collapse_awards = []
        for award_type in ['mccollapse', 'clapper_collapse']:
            if award_type in awards and awards[award_type]:
                award_list = awards[award_type] if isinstance(awards[award_type], list) else [awards[award_type]]
                for award in award_list:
                    team_bg_color, team_font_color = self._get_team_theme_colors(award['team_name'])
                    team_logo_url = team_logos.get(award['team_name'], '')
                    team_logo = self._render_logo_helper(team_logo_url, award['team_name'])

                    content = ""
                    note = None
                    if award_type == 'mccollapse':
                        # Change content to show actual vs optimal
                        actual_score = award.get('actual_score', 0)
                        optimal_score = award.get('optimal_score', 0)
                        content = f"Actual: {actual_score:.2f}, vs. Optimal: {optimal_score:.2f}"
                        # Change note to show opponent information
                        opponent_score = award.get('opponent_score', 0)
                        opponent_info = opponent_lookup.get(award['team_name'])
                        if opponent_info:
                            opponent_rank = get_score_rank(opponent_info['name'])
                            note = f"vs. {opponent_info['name']} - {opponent_score:.2f} ({opponent_rank})"
                    elif award_type == 'clapper_collapse':
                        # Change content to show projected vs actual
                        projected_score = award.get('projected_score', 0)
                        actual_score = award.get('actual_score', 0)
                        content = f"Projected: {projected_score:.2f}, Actual: {actual_score:.2f}"
                        # Add opponent information
                        opponent_info = opponent_lookup.get(award['team_name'])
                        if opponent_info:
                            opponent_rank = get_score_rank(opponent_info['name'])
                            note = f"vs. {opponent_info['name']} - {opponent_info['score']:.2f} ({opponent_rank})"

                    # Special naming for clapper collapse
                    display_name = award_type.upper()
                    if award_type == 'clapper_collapse':
                        display_name = 'THE CLAPPER'

                    collapse_awards.append({
                        'name': award_type,
                        'display_name': display_name,
                        'description': award_definitions[award_type],
                        'team_name': award['team_name'],
                        'content': content,
                        'note': note,
                        'team_bg_color': team_bg_color,
                        'team_font_color': team_font_color,
                        'team_logo': team_logo
                    })

        # Prepare honorable mentions
        honorable_mentions = []
        if 'honorable_mentions' in awards and awards['honorable_mentions']:
            for mention in awards['honorable_mentions']:
                # Generate description based on award type and statistics
                if mention['award_type'] == 'mccollapse':
                    description = f"scored {mention['primary_stat']:.2f} (vs. Optimal {mention['secondary_stat']:.2f}) against {mention['opponent_name']} ({mention['opponent_score']:.2f})"
                elif mention['award_type'] == 'clapper_collapse':
                    description = f"scored {mention['secondary_stat']:.2f} (vs. Projected {mention['primary_stat']:.2f}) against {mention['opponent_name']} ({mention['opponent_score']:.2f})"
                else:
                    description = f"vs. {mention['opponent_name']} ({mention['opponent_score']:.2f})"

                # Get team theme colors for this honorable mention
                team_bg_color, team_font_color = self._get_team_theme_colors(mention['team_name'])
                team_logo_url = team_logos.get(mention['team_name'], '')
                team_logo = self._render_logo_helper(team_logo_url, mention['team_name'])

                honorable_mentions.append({
                    'award_name': mention['award_name'],
                    'team_name': mention['team_name'],
                    'opponent_name': mention['opponent_name'],
                    'opponent_score': mention['opponent_score'],
                    'description': description,
                    'award_type': mention['award_type'],
                    'team_bg_color': team_bg_color,
                    'team_font_color': team_font_color,
                    'team_logo': team_logo
                })

        return {
            'player_awards': player_awards,
            'team_awards': team_awards,
            'collapse_awards': collapse_awards,
            'honorable_mentions': honorable_mentions
        }

    def _prepare_matchups_data(self, data: Dict[str, Any], team_logos: Dict[str, str]) -> List[Dict]:
        """Prepare matchups data for template rendering."""
        # Sort matchups by score difference (closest games first)
        def calculate_score_difference(matchup):
            return abs(matchup['home_score'] - matchup['away_score'])

        sorted_matchups = sorted(data['matchups'], key=calculate_score_difference)

        prepared_matchups = []
        for matchup in sorted_matchups:
            home_team = matchup['home_team']
            away_team = matchup['away_team']

            # Get logos
            home_logo = self._render_logo_helper(team_logos.get(home_team['name'], ''), home_team['name'])
            away_logo = self._render_logo_helper(team_logos.get(away_team['name'], ''), away_team['name'])

            # Get theme colors
            away_bg_color, away_font_color = self._get_team_theme_colors(away_team['name'])
            home_bg_color, home_font_color = self._get_team_theme_colors(home_team['name'])

            # Prepare player data for both teams
            home_player_data = self._prepare_team_player_data(matchup['players'], home_team['name'], matchup)
            away_player_data = self._prepare_team_player_data(matchup['players'], away_team['name'], matchup)

            prepared_matchups.append({
                'home_team': home_team,
                'away_team': away_team,
                'home_score': matchup['home_score'],
                'away_score': matchup['away_score'],
                'home_projected_score': matchup['home_projected_score'],
                'away_projected_score': matchup['away_projected_score'],
                'home_logo': home_logo,
                'away_logo': away_logo,
                'home_bg_color': home_bg_color,
                'home_font_color': home_font_color,
                'away_bg_color': away_bg_color,
                'away_font_color': away_font_color,
                'players': matchup['players'],

                # Team-specific player data
                'home_players': home_player_data['team_players'],
                'home_starter_total': home_player_data['starter_total'],
                'home_optimal_score': home_player_data['optimal_score'],
                'home_accuracy_percentage': home_player_data['accuracy_percentage'],

                'away_players': away_player_data['team_players'],
                'away_starter_total': away_player_data['starter_total'],
                'away_optimal_score': away_player_data['optimal_score'],
                'away_accuracy_percentage': away_player_data['accuracy_percentage']
            })

        return prepared_matchups

    def _prepare_running_totals_data(self, data: Dict[str, Any], team_logos: Dict[str, str]) -> List[Tuple[int, Dict[str, Any]]]:
        """Prepare running totals data for template rendering."""
        running_totals = []

        # Check if this is enhanced data with running totals
        if 'season_context' in data and 'running_totals' in data['season_context']:
            # Use the running totals from enhanced data
            totals_data = data['season_context']['running_totals']

            for team_id, team_data in totals_data.items():
                if isinstance(team_data, dict) and 'error' not in team_data:
                    running_totals.append((team_id, team_data))
        else:
            # Fall back to calculating from current week data
            running_totals = self._calculate_current_week_totals(data)

        # Sort by efficiency (highest to lowest) as requested
        running_totals.sort(key=lambda x: x[1].get('efficiency', 0), reverse=True)

        return running_totals

    def _calculate_current_week_totals(self, data: Dict[str, Any]) -> List[Tuple[int, Dict[str, Any]]]:
        """Calculate totals from current week data as fallback."""
        team_totals = {}

        # Get all team info from divisions
        all_teams = {}
        for division in data.get('divisions', []):
            for team in division.get('teams', []):
                team_id = team.get('id')
                if team_id:
                    all_teams[team_id] = {
                        'name': team.get('name', ''),
                        'logo': team.get('logo', ''),
                        'division': team.get('division', ''),
                        'actual': 0.0,
                        'projected': 0.0,
                        'optimal': 0.0,
                        'efficiency': 0.0
                    }

        # Extract scores from matchups
        for matchup in data.get('matchups', []):
            home_team_id = matchup.get('home_team', {}).get('id')
            away_team_id = matchup.get('away_team', {}).get('id')

            home_score = matchup.get('home_score', 0)
            away_score = matchup.get('away_score', 0)
            home_projected = matchup.get('home_projected_score', 0)
            away_projected = matchup.get('away_projected_score', 0)
            home_optimal = matchup.get('home_optimal_score', 0)
            away_optimal = matchup.get('away_optimal_score', 0)

            # Update home team totals
            if home_team_id and home_team_id in all_teams:
                all_teams[home_team_id]['actual'] += home_score
                all_teams[home_team_id]['projected'] += home_projected
                all_teams[home_team_id]['optimal'] += home_optimal

            # Update away team totals
            if away_team_id and away_team_id in all_teams:
                all_teams[away_team_id]['actual'] += away_score
                all_teams[away_team_id]['projected'] += away_projected
                all_teams[away_team_id]['optimal'] += away_optimal

        # Calculate efficiency percentages
        result = []
        for team_id, team_data in all_teams.items():
            if team_data['optimal'] > 0:
                team_data['efficiency'] = (team_data['actual'] / team_data['optimal']) * 100
            else:
                team_data['efficiency'] = 0.0

            result.append((team_id, team_data))

        return result

    def _prepare_team_player_data(self, all_players: List[Dict[str, Any]], team_name: str, matchup: Dict[str, Any]) -> Dict:
        """Prepare player data for a specific team."""
        # Filter players for this team
        team_players = [p for p in all_players if p['team'] == team_name]

        # Find MVP (highest scoring starter) and prepare player data
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

        # Sort players by position
        position_order = ['QB', 'RB', 'WR', 'TE', 'OP', 'RB/WR/TE', 'K', 'D/ST']

        # Prepare all players with extra metadata
        prepared_players = []
        for player in team_players:
            prepared_player = dict(player)  # Copy all existing data
            prepared_player['is_mvp'] = (player == mvp_player)
            prepared_players.append(prepared_player)

        # Sort players: starters first (by position), then bench players
        starters_sorted = sorted([p for p in prepared_players if p['is_starter']],
                                key=lambda p: position_order.index(p['roster_slot']) if p['roster_slot'] in position_order else 999)

        # Sort bench players: should-have-started first, then others, IR last
        bench_players = [p for p in prepared_players if not p['is_starter']]
        should_start = [p for p in bench_players if p['should_have_started'] and p['roster_slot'] != 'IR']
        regular_bench = [p for p in bench_players if not p['should_have_started'] and p['roster_slot'] != 'IR']
        ir_players = [p for p in bench_players if p['roster_slot'] == 'IR']

        should_start_sorted = sorted(should_start, key=lambda p: position_order.index(p['roster_slot']) if p['roster_slot'] in position_order else 999)
        regular_bench_sorted = sorted(regular_bench, key=lambda p: position_order.index(p['roster_slot']) if p['roster_slot'] in position_order else 999)
        ir_players_sorted = sorted(ir_players, key=lambda p: position_order.index(p['roster_slot']) if p['roster_slot'] in position_order else 999)

        # Combine: starters first, then bench in order
        bench_sorted = should_start_sorted + regular_bench_sorted + ir_players_sorted
        all_players_sorted = starters_sorted + bench_sorted

        return {
            'team_players': all_players_sorted,
            'starter_total': starter_total,
            'optimal_score': optimal_score,
            'accuracy_percentage': accuracy_percentage
        }

    def _get_team_color_data(self, team_name: str) -> dict:
        """Get structured color data for a team (supports solid colors and gradients)."""
        team_colors = {
            "They Stole Danny's Dimes": {
                "type": "solid",
                "css_value": "rgb(189, 142, 156)"
            },
            "Opportune Play Odunze": {
                "type": "solid",
                "css_value": "rgb(251, 66, 29)"
            },
            "Atlanta Faldone": {
                "type": "solid",
                "css_value": "rgb(123, 0, 19)"
            },
            "The Williams Football Team": {
                "type": "solid",
                "css_value": "rgb(100, 54, 30)"
            },
            "Moore's Law": {
                "type": "solid",
                "css_value": "rgb(222, 176, 71)"
            },
            "Topless Fondue": {
                "type": "solid",
                "css_value": "rgb(35, 50, 98)"
            },
            "O'ahu State Warriors": {
                "type": "gradient",
                "css_value": "linear-gradient(90deg, #ff0000 0%, #ff8000 16.6%, #ffff00 33.3%, #80ff00 50%, #0080ff 66.6%, #8000ff 83.3%, #ff00ff 100%)"
            },
            "Darnold Schwarzenegger": {
                "type": "solid",
                "css_value": "rgb(244, 129, 25)"
            },
            "Weak(ly) Showing": {
                "type": "solid",
                "css_value": "rgb(0, 0, 0)"
            },
            "Team Team": {
                "type": "solid",
                "css_value": "rgb(27, 120, 51)"
            },
            "Bad JuJu": {
                "type": "solid",
                "css_value": "rgb(252, 1, 31)"
            },
            "Honolulu Corpse Reviver": {
                "type": "solid",
                "css_value": "rgb(212, 213, 214)"
            }
        }
        return team_colors.get(team_name, {"type": "solid", "css_value": "rgb(255, 255, 255)"})

    def _create_player_lookup(self, data: Dict[str, Any]) -> Dict[str, Dict]:
        """
        Create a lookup dictionary for player data by player name and team.

        Args:
            data: Weekly report data containing matchups with player information

        Returns:
            Dictionary mapping (player_name, team_name) -> player_data
        """
        player_lookup = {}

        for matchup in data.get('matchups', []):
            for player in matchup.get('players', []):
                key = (player.get('name'), player.get('team'))
                player_lookup[key] = player

        return player_lookup

    def _get_player_stats_display(self, player_data: Dict[str, Any]) -> str:
        """
        Generate a statistics display string for a player based on position.

        Args:
            player_data: Player dictionary with position and available stats

        Returns:
            Formatted statistics string for display
        """
        if not player_data:
            return "Stats not available"

        position = player_data.get('position', '').upper()
        actual_score = player_data.get('actual_score', 0)
        projected_score = player_data.get('projected_score', 0)
        statistics = player_data.get('statistics')

        # If no detailed statistics available, return empty string (points already shown in player name)
        if not statistics:
            return "Stats not available"

        # Generate position-specific statistics display
        if position == 'QB':
            stats_parts = []
            if statistics.get('passing_completions') is not None and statistics.get('passing_attempts') is not None:
                stats_parts.append(f"{statistics['passing_completions']}/{statistics['passing_attempts']} pass")
            if statistics.get('passing_yards') is not None:
                stats_parts.append(f"{statistics['passing_yards']:.0f} pass yds")
            if statistics.get('passing_touchdowns') is not None:
                stats_parts.append(f"{statistics['passing_touchdowns']} pass TD")
            if statistics.get('rushing_attempts') is not None and statistics['rushing_attempts'] > 0:
                stats_parts.append(f"{statistics['rushing_attempts']} rush")
            if statistics.get('rushing_yards') is not None and statistics['rushing_yards'] > 0:
                stats_parts.append(f"{statistics['rushing_yards']:.0f} rush yds")

            if stats_parts:
                return '; '.join(stats_parts)

        elif position in ['RB', 'FB']:
            stats_parts = []
            if statistics.get('rushing_attempts') is not None:
                stats_parts.append(f"{statistics['rushing_attempts']} rush")
            if statistics.get('rushing_yards') is not None:
                stats_parts.append(f"{statistics['rushing_yards']:.0f} rush yds")
            if statistics.get('rushing_touchdowns') is not None and statistics['rushing_touchdowns'] > 0:
                stats_parts.append(f"{statistics['rushing_touchdowns']} rush TD")
            if statistics.get('receiving_receptions') is not None:
                stats_parts.append(f"{statistics['receiving_receptions']} rec")
            if statistics.get('receiving_yards') is not None and statistics['receiving_yards'] > 0:
                stats_parts.append(f"{statistics['receiving_yards']:.0f} rec yds")

            if stats_parts:
                return '; '.join(stats_parts)

        elif position in ['WR', 'TE']:
            stats_parts = []
            if statistics.get('receiving_receptions') is not None:
                stats_parts.append(f"{statistics['receiving_receptions']} rec")
            if statistics.get('receiving_yards') is not None:
                stats_parts.append(f"{statistics['receiving_yards']:.0f} yds")
            if statistics.get('receiving_touchdowns') is not None and statistics['receiving_touchdowns'] > 0:
                stats_parts.append(f"{statistics['receiving_touchdowns']} rec TD")
            if statistics.get('receiving_targets') is not None:
                stats_parts.append(f"{statistics['receiving_targets']} tgts")

            if stats_parts:
                return '; '.join(stats_parts)

        elif position == 'K':
            stats_parts = []
            if statistics.get('field_goals_made') is not None and statistics.get('field_goals_attempted') is not None:
                stats_parts.append(f"{statistics['field_goals_made']}/{statistics['field_goals_attempted']} FG")
            if statistics.get('extra_points_made') is not None and statistics.get('extra_points_attempted') is not None:
                stats_parts.append(f"{statistics['extra_points_made']}/{statistics['extra_points_attempted']} XP")

            if stats_parts:
                return '; '.join(stats_parts)

        elif position == 'D/ST':
            stats_parts = []
            if statistics.get('defensive_touchdowns') is not None and statistics['defensive_touchdowns'] > 0:
                stats_parts.append(f"{statistics['defensive_touchdowns']} def TD")
            if statistics.get('defensive_interceptions') is not None and statistics['defensive_interceptions'] > 0:
                stats_parts.append(f"{statistics['defensive_interceptions']} int")
            if statistics.get('defensive_sacks') is not None and statistics['defensive_sacks'] > 0:
                stats_parts.append(f"{statistics['defensive_sacks']:.0f} sacks")
            if statistics.get('points_allowed') is not None:
                stats_parts.append(f"{statistics['points_allowed']} pts allowed")

            if stats_parts:
                return '; '.join(stats_parts)

        # Fallback if no position-specific stats found
        return "No detailed stats available"

    def _get_team_theme_color(self, team_name: str) -> str:
        """Get the theme background color for a specific team (backward compatibility)."""
        color_data = self._get_team_color_data(team_name)

        # Special handling for "Bad JuJu" - darken their bright red background so logo stands out
        if team_name == "Bad JuJu":
            return "rgb(180, 1, 22)"  # Darkened version of their original rgb(252, 1, 31)

        # Special handling for "Moore's Law" - shift background more towards gold and darker for better text contrast
        if team_name == "Moore's Law":
            return "rgb(184, 134, 11)"  # Darker, more golden background so light text stands out

        return color_data["css_value"]

    def _get_team_font_color(self, team_name: str) -> str:
        """Get the appropriate font color for a team based on their theme color."""
        # Get the structured color data
        color_data = self._get_team_color_data(team_name)

        # For gradients, use black text for better readability
        if color_data["type"] == "gradient":
            return "rgb(0, 0, 0)"

        # For solid colors, calculate contrast color
        # Use the actual theme color (which may include special adjustments) for contrast calculation
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

        # Step 3: Check if highly saturated (S > 70% and L between 30%-70%)
        is_highly_saturated = s > 0.7 and 0.3 <= l <= 0.7

        # Apply hue shift for thematic appropriateness (+30° or -30°)
        # Choose direction based on team name hash for consistency
        hue_shift_direction = 1 if hash(team_name) % 2 == 0 else -1
        h_shifted = (h + (30.0 / 360.0) * hue_shift_direction) % 1.0

        # Moderate desaturation - keep some color but not overwhelming
        s_adjusted = s * 0.7 if is_highly_saturated else s * 0.9

        # Step 4: Adjust lightness to achieve high contrast ratio
        def contrast_ratio(lum1, lum2):
            """Calculate contrast ratio between two luminance values"""
            lighter = max(lum1, lum2)
            darker = min(lum1, lum2)
            return (lighter + 0.05) / (darker + 0.05)

        def luminance_from_lightness(lightness):
            """Calculate proper luminance from HSL lightness"""
            # Convert HSL back to RGB to calculate proper luminance
            test_r, test_g, test_b = colorsys.hls_to_rgb(h_shifted, lightness, s_adjusted)

            # Apply proper sRGB to linear conversion
            def linearize_component(value):
                if value <= 0.03928:
                    return value / 12.92
                else:
                    return math.pow((value + 0.055) / 1.055, 2.4)

            r_linear = linearize_component(test_r)
            g_linear = linearize_component(test_g)
            b_linear = linearize_component(test_b)

            # Calculate luminance using proper formula
            return 0.2126 * r_linear + 0.7152 * g_linear + 0.0722 * b_linear

        # Target contrast ratio of 7:1 for good readability
        target_contrast = 7

        # Binary search for the right lightness value (moderately aggressive ranges)
        if is_dark_bg:
            # Dark background needs light text - push toward white
            l_min, l_max = 0.6, 1.0
        else:
            # Light background needs dark text - push toward black
            l_min, l_max = 0.0, 0.4

        # Find lightness that achieves target contrast
        best_l = l_min
        best_contrast = 0

        for _ in range(25):  # Sufficient iterations for good precision
            test_l = (l_min + l_max) / 2
            test_luminance = luminance_from_lightness(test_l)
            contrast = contrast_ratio(bg_luminance, test_luminance)

            if contrast >= target_contrast:
                best_l = test_l
                best_contrast = contrast
                if is_dark_bg:
                    l_max = test_l
                else:
                    l_min = test_l
            else:
                if is_dark_bg:
                    l_min = test_l
                else:
                    l_max = test_l

        # Fallback: if we didn't achieve target contrast, use strong but not extreme values
        if best_contrast < target_contrast:
            if is_dark_bg:
                best_l = 0.85  # Bright text for dark backgrounds
            else:
                best_l = 0.15  # Dark text for light backgrounds

        # Convert back to RGB
        font_r, font_g, font_b = colorsys.hls_to_rgb(h_shifted, best_l, s_adjusted)

        # Convert to 0-255 range and format as RGB string
        font_r = int(round(font_r * 255))
        font_g = int(round(font_g * 255))
        font_b = int(round(font_b * 255))

        return f"rgb({font_r}, {font_g}, {font_b})"

    def _get_team_theme_colors(self, team_name: str) -> tuple:
        """Get the complete theme colors for a team (background and font color)."""
        background_color = self._get_team_theme_color(team_name)
        font_color = self._get_team_font_color(team_name)
        return (background_color, font_color)

    def _lighten_color(self, color_string: str, lighten_factor: float = 0.7) -> str:
        """
        Lighten a color by mixing it with white (supports both solid colors and gradients).

        Args:
            color_string: RGB color string like 'rgb(255, 0, 0)' or gradient like 'linear-gradient(...)'
            lighten_factor: How much to lighten (0.0 = no change, 1.0 = white)

        Returns:
            Lightened color string (RGB for solid colors, layered gradient for gradients)
        """
        import re

        # Check if this is a gradient
        if color_string.startswith('linear-gradient'):
            # For gradients, add a white overlay to lighten
            opacity = lighten_factor * 0.8  # Convert lighten factor to opacity (max 0.8 for visibility)
            return f"linear-gradient(rgba(255,255,255,{opacity}), rgba(255,255,255,{opacity})), {color_string}"

        # For solid colors, use existing RGB lightening logic
        # Extract RGB values from string like 'rgb(255, 0, 0)'
        match = re.search(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', color_string)
        if not match:
            return color_string

        r, g, b = map(int, match.groups())

        # Lighten by mixing with white (255, 255, 255)
        r_light = int(r + (255 - r) * lighten_factor)
        g_light = int(g + (255 - g) * lighten_factor)
        b_light = int(b + (255 - b) * lighten_factor)

        return f"rgb({r_light}, {g_light}, {b_light})"

    def _get_background_css(self, color_string: str) -> str:
        """
        Get the appropriate CSS property for background based on color type.
        Returns complete CSS declaration (e.g., "background-color: rgb(255,0,0)" or "background: linear-gradient(...)").

        Args:
            color_string: Color value (RGB string or gradient)

        Returns:
            Complete CSS declaration string
        """
        if color_string.startswith('linear-gradient'):
            return f"background: {color_string}"
        else:
            return f"background-color: {color_string}"

    def _get_combined_background(self, color_string: str, logo_url: str = None, lighten_factor: float = None, blend_mode: str = None) -> str:
        """
        Get CSS for combining team color/gradient with team logo background image.

        Args:
            color_string: Team color (RGB or gradient)
            logo_url: Optional team logo URL for background image
            lighten_factor: Optional lightening factor for gradients (0.0-1.0)
            blend_mode: Optional blend mode override (defaults to "hue" for gradients, "soft-light" for others)

        Returns:
            Complete CSS background declaration
        """
        if not logo_url:
            # No logo, just return the color CSS
            return self._get_background_css(color_string)

        # Determine blend mode: default to "hue" for gradients, "soft-light" for solid colors
        if blend_mode is None:
            blend_mode = "hue" if color_string.startswith('linear-gradient') else "soft-light"

        if color_string.startswith('linear-gradient'):
            # For gradients, apply lightening if specified and layer with logo
            if lighten_factor is not None:
                # Create white overlay for lightening
                opacity = lighten_factor * 0.8
                white_overlay = f"linear-gradient(rgba(255,255,255,{opacity}), rgba(255,255,255,{opacity}))"
                return f"background-image: url('{logo_url}'), {white_overlay}, {color_string}; background-size: 60%, cover, cover; background-repeat: no-repeat; background-position: center center; background-blend-mode: {blend_mode}"
            else:
                return f"background-image: url('{logo_url}'), {color_string}; background-size: 60%, cover; background-repeat: no-repeat; background-position: center center; background-blend-mode: {blend_mode}"
        else:
            # For solid colors, use background-color + background-image
            return f"background-color: {color_string}; background-image: url('{logo_url}'); background-size: 60%; background-repeat: no-repeat; background-position: center center; background-blend-mode: {blend_mode}"

    def _prepare_weekly_summary_data(self, data: Dict[str, Any], team_logos: Dict[str, str]) -> Dict[str, Any]:
        """
        Prepare weekly summary data showing all teams' current week performance.

        Args:
            data: Current week data
            team_logos: Team logo lookup dictionary

        Returns:
            Dictionary with 'team_scores' list and 'median_score'
        """
        # Extract team scores from current week matchups
        team_results = []
        all_scores = []

        for matchup in data.get('matchups', []):
            home_team = matchup['home_team']
            away_team = matchup['away_team']
            home_score = matchup['home_score']
            away_score = matchup['away_score']

            # Determine winner and calculate margins
            if home_score > away_score:
                home_result = "Win"
                away_result = "Loss"
                home_margin = f"+{home_score - away_score:.2f}"
                away_margin = f"-{home_score - away_score:.2f}"
            elif away_score > home_score:
                home_result = "Loss"
                away_result = "Win"
                home_margin = f"-{away_score - home_score:.2f}"
                away_margin = f"+{away_score - home_score:.2f}"
            else:
                # Tie
                home_result = "Tie"
                away_result = "Tie"
                home_margin = "0.00"
                away_margin = "0.00"

            # Add home team data
            team_results.append({
                'team_name': home_team['name'],
                'score': home_score,
                'result': home_result,
                'margin_display': home_margin
            })

            # Add away team data
            team_results.append({
                'team_name': away_team['name'],
                'score': away_score,
                'result': away_result,
                'margin_display': away_margin
            })

            # Collect scores for median calculation
            all_scores.extend([home_score, away_score])

        # Sort teams by score (highest first)
        team_results.sort(key=lambda x: x['score'], reverse=True)

        # Calculate median score
        median_score = statistics.median(all_scores) if all_scores else 0.0

        return {
            'team_scores': team_results,
            'median_score': median_score
        }

    def _prepare_strength_of_schedule_data(self, data: Dict[str, Any], team_logos: Dict[str, str]) -> Dict[str, Any]:
        """
        Prepare strength of schedule data showing difficulty of each team's opponents.
        Args:
            data: Full enhanced data (with season_context)
            team_logos: Team logo lookup dictionary
        Returns:
            Dictionary with 'teams' list, 'average_points_per_game', and 'total_weeks'
        """
        # Get team standings data for points_against and wins/losses
        team_standings = {}
        if 'season_context' in data and 'team_standings' in data['season_context']:
            team_standings = data['season_context']['team_standings']

        # Calculate league average points per game
        total_points = 0.0
        total_teams = len(team_standings)
        total_weeks = 0

        # Sum all points_for across all teams to get total points scored in league
        for team_data in team_standings.values():
            total_points += team_data.get('points_for', 0.0)

        # Determine number of weeks from metadata
        if 'metadata' in data:
            total_weeks = data['metadata'].get('total_weeks_processed', 1)
        else:
            # Fallback: estimate from current_week data
            total_weeks = data.get('current_week', {}).get('week', 1)

        # Calculate average points per game
        # Total points divided by (number of teams * number of weeks)
        games_played = total_teams * total_weeks
        average_points_per_game = total_points / games_played if games_played > 0 else 0.0

        # Prepare strength of schedule data for each team
        sos_teams = []
        for team_id, team_data in team_standings.items():
            points_against = team_data.get('points_against', 0.0)
            points_against_per_game = points_against / total_weeks if total_weeks > 0 else 0.0

            # Calculate percentage above/below average
            if average_points_per_game > 0:
                percentage_vs_average = ((points_against_per_game - average_points_per_game) / average_points_per_game) * 100
            else:
                percentage_vs_average = 0.0

            # Format head-to-head record
            wins = team_data.get('wins', 0)
            losses = team_data.get('losses', 0)
            ties = team_data.get('ties', 0)
            if ties > 0:
                record = f"{wins}-{losses}-{ties}"
            else:
                record = f"{wins}-{losses}"

            sos_teams.append({
                'team_id': team_id,
                'name': team_data.get('name', ''),
                'logo': team_data.get('logo', ''),
                'division': team_data.get('division', ''),
                'record': record,
                'points_against': points_against,
                'points_against_per_game': points_against_per_game,
                'percentage_vs_average': percentage_vs_average,
                'wins': wins,
                'losses': losses,
                'ties': ties
            })

        # Sort by most difficult schedule (highest points against per game) first
        sos_teams.sort(key=lambda x: x['points_against_per_game'], reverse=True)

        # Add ranking (1 = most difficult, 12 = least difficult)
        for rank, team in enumerate(sos_teams, 1):
            team['sos_rank'] = rank

        return {
            'teams': sos_teams,
            'average_points_per_game': average_points_per_game,
            'total_weeks': total_weeks
        }

    def _prepare_division_strength_data(self, data: Dict[str, Any], team_logos: Dict[str, str]) -> Dict[str, Any]:
        """
        Prepare division strength data for template rendering.

        Extracts division strength data from enhanced JSON and formats for HTML table.

        Args:
            data: Full fantasy football data (enhanced structure)
            team_logos: Team logo lookup dictionary

        Returns:
            Dict containing division strength data for template
        """
        try:
            # Get division strength data from season context
            season_context = data.get('season_context', {})
            division_strength = season_context.get('division_strength', {})
            divisions = division_strength.get('divisions', [])

            # If no division strength data available, return empty structure
            if not divisions:
                return {
                    'divisions': [],
                    'ranking_criteria': 'No data available'
                }

            # Format divisions for template (already ranked by aggregate stage)
            formatted_divisions = []
            for division in divisions:
                # Prepare team data with logos for this division
                teams_with_logos = []
                for team_name in division.get('teams', []):
                    teams_with_logos.append({
                        'name': team_name,
                        'logo': team_logos.get(team_name, '')
                    })

                formatted_divisions.append({
                    'name': division.get('name', ''),
                    'rank': division.get('rank', 0),
                    'wins': division.get('wins', 0),
                    'losses': division.get('losses', 0),
                    'points_for': round(division.get('points_for', 0), 1),
                    'points_against': round(division.get('points_against', 0), 1),
                    'teams': teams_with_logos
                })

            return {
                'divisions': formatted_divisions,
                'ranking_criteria': division_strength.get('ranking_criteria', 'Wins (desc), Losses (asc), Points For (desc), Points Against (desc)')
            }

        except Exception as e:
            # Return empty structure on error
            return {
                'divisions': [],
                'ranking_criteria': f'Error: {str(e)}'
            }

    def _prepare_team_lightbox_data(self, data: Dict[str, Any], team_logos: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        """
        Prepare team-specific data for interactive lightbox popovers.

        Creates comprehensive team data including season statistics and week-by-week results
        for use in interactive team information popovers.

        Args:
            data: Full fantasy football data (enhanced or raw structure)
            team_logos: Team logo lookup dictionary

        Returns:
            Dict mapping team IDs to team lightbox data containing season stats and weekly results
        """
        try:
            current_week_data = data.get('current_week_data', data.get('current_week', data))
            lightbox_data = {}

            # Get team standings - computed or from current data
            team_standings = self._get_team_standings_from_data(data)

            # Get all teams from divisions
            all_teams = {}
            for division in current_week_data.get('divisions', []):
                for team in division.get('teams', []):
                    team_id = str(team.get('id', ''))
                    team_name = team.get('name', '')
                    all_teams[team_id] = {
                        'id': team_id,
                        'name': team_name,
                        'owner': team.get('owner', ''),
                        'division': team.get('division', division.get('name', '')),
                        'abbreviation': team.get('abbreviation', ''),
                        'logo': team_logos.get(team_name, '')
                    }

            # Get historical matchup data for week-by-week results
            weekly_results = self._calculate_team_weekly_results(data, all_teams)

            # Create lightbox data for each team
            for team_id, team_info in all_teams.items():
                # Get season statistics from standings
                team_standings_data = team_standings.get(team_id, {})

                # Get team theme colors
                theme_colors = self._get_team_theme_colors(team_info['name'])

                lightbox_data[team_id] = {
                    'name': team_info['name'],
                    'owner': team_info['owner'],
                    'division': team_info['division'],
                    'logo': team_info['logo'],
                    'themeColors': theme_colors,
                    'seasonStats': {
                        'rank': team_standings_data.get('overall_rank', 0),
                        'wins': team_standings_data.get('wins', 0),
                        'losses': team_standings_data.get('losses', 0),
                        'ties': team_standings_data.get('ties', 0),
                        'pointsFor': round(team_standings_data.get('points_for', 0), 1),
                        'pointsAgainst': round(team_standings_data.get('points_against', 0), 1)
                    },
                    'weeklyResults': weekly_results.get(team_id, [])
                }

            return lightbox_data

        except Exception as e:
            # Return empty structure on error
            return {}

    def _calculate_team_weekly_results(self, data: Dict[str, Any], all_teams: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Calculate week-by-week results for each team from historical matchup data.

        Args:
            data: Full fantasy football data with season context
            all_teams: Dictionary of all teams by ID

        Returns:
            Dictionary mapping team IDs to list of weekly result data
        """
        try:
            weekly_results = {team_id: [] for team_id in all_teams.keys()}

            # Try to get historical data from enhanced structure first
            season_context = data.get('season_context', {})
            matchup_history = season_context.get('matchup_history', {})
            weekly_matchups = matchup_history.get('weekly_results', {})

            if weekly_matchups:
                # Process each week's matchups from the new structure
                for week_num, matchups in weekly_matchups.items():
                    # Handle both integer keys and float-string keys (backward compatibility)
                    try:
                        week_number = int(float(week_num))  # Handles "1", "1.0", 1, 1.0
                    except (ValueError, TypeError):
                        continue  # Skip invalid week numbers

                    for matchup in matchups:
                        home_team = matchup.get('home_team', {})
                        away_team = matchup.get('away_team', {})
                        home_score = float(matchup.get('home_score', 0))
                        away_score = float(matchup.get('away_score', 0))

                        # Handle both string and numeric IDs from matchup data
                        home_team_id = str(int(float(home_team.get('id', 0)))) if home_team.get('id') is not None else ''
                        away_team_id = str(int(float(away_team.get('id', 0)))) if away_team.get('id') is not None else ''

                        # Add result for home team
                        if home_team_id in all_teams:
                            result = self._determine_match_result(home_team_id, matchup.get('winner_id'), matchup.get('loser_id'))
                            weekly_results[home_team_id].append({
                                'week': week_number,
                                'opponent': away_team.get('name', ''),
                                'opponentDivision': all_teams.get(away_team_id, {}).get('division', ''),
                                'homeAway': 'vs',
                                'teamScore': round(home_score, 1),
                                'opponentScore': round(away_score, 1),
                                'result': result,
                                'recordAfter': self._calculate_record_after_week(weekly_results[home_team_id], result)
                            })

                        # Add result for away team
                        if away_team_id in all_teams:
                            result = self._determine_match_result(away_team_id, matchup.get('winner_id'), matchup.get('loser_id'))
                            weekly_results[away_team_id].append({
                                'week': week_number,
                                'opponent': home_team.get('name', ''),
                                'opponentDivision': all_teams.get(home_team_id, {}).get('division', ''),
                                'homeAway': '@',
                                'teamScore': round(away_score, 1),
                                'opponentScore': round(home_score, 1),
                                'result': result,
                                'recordAfter': self._calculate_record_after_week(weekly_results[away_team_id], result)
                            })

            else:
                # Fallback: use current week data only if no historical data available
                current_week_data = data.get('current_week_data', data)
                week_number = current_week_data.get('week', 1)

                for matchup in current_week_data.get('matchups', []):
                    home_team = matchup.get('home_team', {})
                    away_team = matchup.get('away_team', {})
                    home_score = float(matchup.get('home_score', 0))
                    away_score = float(matchup.get('away_score', 0))

                    home_team_id = str(home_team.get('id', ''))
                    away_team_id = str(away_team.get('id', ''))

                    # Add result for home team
                    if home_team_id in all_teams:
                        result = self._determine_match_result_from_scores(home_score, away_score)
                        weekly_results[home_team_id].append({
                            'week': week_number,
                            'opponent': away_team.get('name', ''),
                            'opponentDivision': all_teams.get(away_team_id, {}).get('division', ''),
                            'homeAway': 'vs',
                            'teamScore': round(home_score, 1),
                            'opponentScore': round(away_score, 1),
                            'result': result,
                            'recordAfter': self._calculate_record_after_week(weekly_results[home_team_id], result)
                        })

                    # Add result for away team
                    if away_team_id in all_teams:
                        result = self._determine_match_result_from_scores(away_score, home_score)
                        weekly_results[away_team_id].append({
                            'week': week_number,
                            'opponent': home_team.get('name', ''),
                            'opponentDivision': all_teams.get(home_team_id, {}).get('division', ''),
                            'homeAway': '@',
                            'teamScore': round(away_score, 1),
                            'opponentScore': round(home_score, 1),
                            'result': result,
                            'recordAfter': self._calculate_record_after_week(weekly_results[away_team_id], result)
                        })

            # Sort weekly results by week number for all teams
            for team_id in weekly_results:
                weekly_results[team_id].sort(key=lambda x: x['week'])

            return weekly_results

        except Exception as e:
            return {}

    def _determine_match_result(self, team_id: str, winner_id: str, loser_id: str) -> str:
        """Determine match result from winner and loser IDs."""
        if winner_id is None and loser_id is None:
            return "Tie"
        elif str(team_id) == str(winner_id):
            return "Win"
        elif str(team_id) == str(loser_id):
            return "Loss"
        else:
            return "Tie"  # Default to tie if team not found in winner/loser

    def _determine_match_result_from_scores(self, team_score: float, opponent_score: float) -> str:
        """Determine match result from scores (fallback method)."""
        if team_score > opponent_score:
            return "Win"
        elif team_score < opponent_score:
            return "Loss"
        else:
            return "Tie"

    def _calculate_record_after_week(self, weekly_results: List[Dict[str, Any]], current_result: str) -> str:
        """Calculate team's record after adding current result."""
        wins = sum(1 for result in weekly_results if result.get('result') == 'Win')
        losses = sum(1 for result in weekly_results if result.get('result') == 'Loss')
        ties = sum(1 for result in weekly_results if result.get('result') == 'Tie')

        # Add current result
        if current_result == 'Win':
            wins += 1
        elif current_result == 'Loss':
            losses += 1
        else:
            ties += 1

        # Only include ties in format if there are any
        if ties > 0:
            return f"{wins}-{losses}-{ties}"
        else:
            return f"{wins}-{losses}"