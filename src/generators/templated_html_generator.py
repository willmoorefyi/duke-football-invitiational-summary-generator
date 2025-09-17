"""
Templated HTML Generator for Fantasy Football Reports

This module generates HTML websites from fantasy football JSON data using Jinja2 templates.
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import statistics
import colorsys
import math

from jinja2 import Environment, FileSystemLoader, select_autoescape
try:
    from jinja2 import Markup
except ImportError:
    from markupsafe import Markup

try:
    from ..utils.logo_validator import get_logo_validator
except ImportError:
    from utils.logo_validator import get_logo_validator


class TemplatedFantasyHTMLGenerator:
    """Generates HTML websites from fantasy football JSON data using Jinja2 templates."""

    def __init__(self, validate_logos: bool = False):
        """Initialize the templated HTML generator."""
        self.validate_logos = False

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
        # Create centralized team logo lookup
        team_logos = self._create_team_logo_lookup(data)

        # Format date
        report_date = datetime.fromisoformat(data['report_date'].replace('Z', '+00:00'))
        formatted_date = report_date.strftime("%B %d, %Y at %I:%M %p")

        # Prepare all team data sorted by overall rank
        all_teams_sorted = []
        for division in data['divisions']:
            for team in division['teams']:
                all_teams_sorted.append(team)
        all_teams_sorted.sort(key=lambda x: x['overall_rank'])

        # Calculate week statistics
        week_stats = self._calculate_week_statistics(data)

        # Prepare weekly awards data
        awards_data = self._prepare_awards_data(data, team_logos)

        # Prepare matchup data for game summaries
        matchups_data = self._prepare_matchups_data(data, team_logos)

        return {
            # Basic info
            'league_name': data['league_name'],
            'week': data['week'],
            'season': data['season'],
            'report_date': data['report_date'],
            'formatted_date': formatted_date,

            # Team data
            'team_logos': team_logos,
            'all_teams_sorted': all_teams_sorted,

            # Statistics
            'week_stats': week_stats,

            # Awards
            'player_awards': awards_data['player_awards'],
            'team_awards': awards_data['team_awards'],
            'collapse_awards': awards_data['collapse_awards'],

            # Game summaries
            'matchups_sorted': matchups_data,

            # Helper functions
            'render_logo': self._render_logo_helper,
            'get_team_theme_colors': self._get_team_theme_colors,
            'lighten_color': self._lighten_color,
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

    def _render_logo_helper(self, logo_url: str, team_name: str) -> Markup:
        """
        Render a team logo with client-side fallback to poop emoji if image fails to load.

        Args:
            logo_url: URL to the logo image
            team_name: Name of the team for alt text

        Returns:
            HTML string for the logo with error handling (marked as safe for Jinja2)
        """
        if not logo_url:
            return Markup("")

        # Always render as image with client-side error handling via JavaScript
        return Markup(f'<img src="{logo_url}" class="team-logo" alt="{team_name}" title="{team_name}">')

    def _calculate_week_statistics(self, data: Dict[str, Any]) -> Dict:
        """Calculate summary statistics for the week."""
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
                'max_content': '0.00',
                'min_content': '0.00'
            }

        scores = [ts['score'] for ts in team_scores]
        max_score = max(scores)
        min_score = min(scores)

        # Find teams with max and min scores
        max_team = next(ts['team'] for ts in team_scores if ts['score'] == max_score)
        min_team = next(ts['team'] for ts in team_scores if ts['score'] == min_score)

        # Create content with logos
        team_logos = self._create_team_logo_lookup(data)
        max_logo = self._render_logo_helper(team_logos.get(max_team['name'], ''), max_team['name'])
        min_logo = self._render_logo_helper(team_logos.get(min_team['name'], ''), min_team['name'])
        max_content = Markup(f"{max_score:.2f} {max_logo}")
        min_content = Markup(f"{min_score:.2f} {min_logo}")

        return {
            'median': statistics.median(scores),
            'average': statistics.mean(scores),
            'max': max_score,
            'min': min_score,
            'std_dev': statistics.stdev(scores) if len(scores) > 1 else 0.0,
            'max_content': max_content,
            'min_content': min_content
        }

    def _prepare_awards_data(self, data: Dict[str, Any], team_logos: Dict[str, str]) -> Dict[str, List]:
        """Prepare awards data for template rendering."""
        if 'awards' not in data:
            return {'player_awards': [], 'team_awards': [], 'collapse_awards': []}

        awards = data['awards']

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

        # Prepare player awards
        player_awards = []
        for award_key in ['mvp', 'mwp', 'mup', 'mdp']:
            if award_key in awards and awards[award_key]:
                award = awards[award_key]
                team_bg_color, team_font_color = self._get_team_theme_colors(award['team_name'])
                team_logo_url = team_logos.get(award['team_name'], '')
                team_logo = self._render_logo_helper(team_logo_url, award['team_name'])
                winner_logo = self._render_logo_helper(team_logo_url, award['team_name']).replace('class="team-logo"', 'class="award-winner-logo"')

                player_awards.append({
                    'name': award_key,
                    'description': award_definitions[award_key],
                    'data': award,
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
                        content = f"Lost by {award['points_difference']:.2f} pts"
                        note = "With optimal lineup"
                    elif award_type == 'clapper_collapse':
                        content = "Projected to win but lost"

                    collapse_awards.append({
                        'name': award_type,
                        'description': award_definitions[award_type],
                        'team_name': award['team_name'],
                        'content': content,
                        'note': note,
                        'team_bg_color': team_bg_color,
                        'team_font_color': team_font_color,
                        'team_logo': team_logo
                    })

        return {
            'player_awards': player_awards,
            'team_awards': team_awards,
            'collapse_awards': collapse_awards
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

    def _get_team_theme_color(self, team_name: str) -> str:
        """Get the theme background color for a specific team."""
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
        return team_colors.get(team_name, "rgb(255, 255, 255)")

    def _get_team_font_color(self, team_name: str) -> str:
        """Get the appropriate font color for a team based on their theme color."""
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
        Lighten a color by mixing it with white.

        Args:
            color_string: RGB color string like 'rgb(255, 0, 0)'
            lighten_factor: How much to lighten (0.0 = no change, 1.0 = white)

        Returns:
            Lightened RGB color string
        """
        import re

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