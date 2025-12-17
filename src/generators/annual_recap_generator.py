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
        season_recap = self._aggregate_season_recap(weekly_reports)
        team_stats = self._aggregate_team_stats(weekly_reports)

        # Generate HTML
        html_content = self._generate_html(teams_data, awards_data, weekly_highlights,
                                           season_recap, team_stats, league_metadata)

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
                    'score': highest['score'],
                    'bgColor': highest['team'].get('bg_color', 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'),
                    'fontColor': highest['team'].get('font_color', '#ffffff')
                },
                'lowestScorer': {
                    'teamId': lowest['team'].get('id'),
                    'teamName': lowest['team'].get('name'),
                    'logo': lowest['team'].get('logo', ''),
                    'score': lowest['score'],
                    'bgColor': lowest['team'].get('bg_color', 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'),
                    'fontColor': lowest['team'].get('font_color', '#ffffff')
                },
                'winners': winners
            })

        return {'weeks': weeks_list}

    def _aggregate_season_recap(self, weekly_reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate overall season statistics.

        Returns:
            {
                'weeklyHighScorerChampion': {...},  # Team(s) with most weekly high scores
                'weeklyLowScorerChampion': {...},   # Team(s) with most weekly low scores
                'luckiestTeam': {...},              # Top-half team with highest Pythagorean wins difference
                'unluckiestTeam': {...},            # Bottom-half team with lowest Pythagorean wins difference
                'narrowestPlayoffWinner': {...},    # Top-half team with lowest avg margin of victory
                'closestPlayoffLoser': {...}        # Bottom-half team with lowest avg margin of loss
            }
        """
        from collections import defaultdict

        # Track weekly high/low scorers
        high_scorer_count = defaultdict(int)
        low_scorer_count = defaultdict(int)

        # Track margins for each team
        team_wins_margins = defaultdict(list)  # team_id -> [margins in wins]
        team_loss_margins = defaultdict(list)  # team_id -> [margins in losses]

        # Track points for Pythagorean wins calculation
        team_points_for = defaultdict(float)
        team_points_against = defaultdict(float)

        # Get team info mapping
        team_id_to_info = {}
        if weekly_reports:
            for division in weekly_reports[0].get('divisions', []):
                for team in division.get('teams', []):
                    team_id_to_info[team['id']] = {
                        'name': team['name'],
                        'logo': team.get('logo', ''),
                        'id': team['id']
                    }

        # Process each week
        for report in weekly_reports:
            matchups = report.get('matchups', [])

            # Find highest and lowest scorers this week
            all_scores = []
            for matchup in matchups:
                home_team = matchup.get('home_team', {})
                away_team = matchup.get('away_team', {})
                home_score = float(matchup.get('home_score', 0.0))
                away_score = float(matchup.get('away_score', 0.0))

                all_scores.append({'team_id': home_team.get('id'), 'score': home_score})
                all_scores.append({'team_id': away_team.get('id'), 'score': away_score})

            if all_scores:
                all_scores.sort(key=lambda x: x['score'])
                highest_team_id = all_scores[-1]['team_id']
                lowest_team_id = all_scores[0]['team_id']

                if highest_team_id:
                    high_scorer_count[highest_team_id] += 1
                if lowest_team_id:
                    low_scorer_count[lowest_team_id] += 1

            # Track margins and points
            for matchup in matchups:
                home_team = matchup.get('home_team', {})
                away_team = matchup.get('away_team', {})
                home_score = float(matchup.get('home_score', 0.0))
                away_score = float(matchup.get('away_score', 0.0))
                winner_id = matchup.get('winner_id')

                home_id = home_team.get('id')
                away_id = away_team.get('id')

                if home_id and away_id:
                    # Track points for/against for Pythagorean wins
                    team_points_for[home_id] += home_score
                    team_points_against[home_id] += away_score
                    team_points_for[away_id] += away_score
                    team_points_against[away_id] += home_score

                    if winner_id:
                        margin = abs(home_score - away_score)

                        if winner_id == home_id:
                            team_wins_margins[home_id].append(margin)
                            team_loss_margins[away_id].append(margin)
                        elif winner_id == away_id:
                            team_wins_margins[away_id].append(margin)
                            team_loss_margins[home_id].append(margin)

        # Get final standings from last week
        # Note: DynamoDB returns Decimal objects, so we convert to int
        final_report = weekly_reports[-1] if weekly_reports else {}
        final_standings = []
        for division in final_report.get('divisions', []):
            for team in division.get('teams', []):
                final_standings.append({
                    'id': team['id'],
                    'standing': int(team.get('standing', 99)),
                    'wins': int(team.get('wins', 0)),
                    'losses': int(team.get('losses', 0))
                })

        # Find weekly high scorer champion (team with most weekly highs)
        high_scorer_champion = None
        if high_scorer_count:
            max_count = max(high_scorer_count.values())
            champions = [tid for tid, count in high_scorer_count.items() if count == max_count]
            high_scorer_champion = {
                'teams': [team_id_to_info.get(tid, {}) for tid in champions],
                'count': max_count
            }

        # Find weekly low scorer "champion" (team with most weekly lows)
        low_scorer_champion = None
        if low_scorer_count:
            max_count = max(low_scorer_count.values())
            champions = [tid for tid, count in low_scorer_count.items() if count == max_count]
            low_scorer_champion = {
                'teams': [team_id_to_info.get(tid, {}) for tid in champions],
                'count': max_count
            }

        # Calculate Pythagorean wins for all teams
        team_pythagorean = {}
        for team in final_standings:
            team_id = team['id']
            pf = team_points_for.get(team_id, 0.0)
            pa = team_points_against.get(team_id, 0.0)
            actual_wins = team['wins']
            games_played = team['wins'] + team['losses']

            if pf > 0 and pa > 0 and games_played > 0:
                expected_win_pct = (pf ** 2.37) / ((pf ** 2.37) + (pa ** 2.37))
                expected_wins = expected_win_pct * games_played
                team_pythagorean[team_id] = {
                    'expected': round(expected_wins, 1),
                    'actual': actual_wins,
                    'difference': round(actual_wins - expected_wins, 1)
                }
            else:
                team_pythagorean[team_id] = {'expected': 0.0, 'actual': actual_wins, 'difference': 0.0}

        # Find luckiest team (top 6, highest Pythagorean wins difference)
        luckiest_team = None
        top_half_teams = [t for t in final_standings if t['standing'] <= 6]
        if top_half_teams:
            team_pyth_list = []
            for team in top_half_teams:
                pyth = team_pythagorean.get(team['id'], {})
                team_pyth_list.append({
                    'team_id': team['id'],
                    'expected': pyth.get('expected', 0.0),
                    'actual': pyth.get('actual', 0),
                    'difference': pyth.get('difference', 0.0),
                    'wins': team['wins'],
                    'losses': team['losses']
                })

            if team_pyth_list:
                team_pyth_list.sort(key=lambda x: x['difference'], reverse=True)  # Highest first
                luckiest = team_pyth_list[0]
                luckiest_team = {
                    **team_id_to_info.get(luckiest['team_id'], {}),
                    'expectedWins': luckiest['expected'],
                    'actualWins': luckiest['actual'],
                    'difference': luckiest['difference'],
                    'wins': luckiest['wins'],
                    'losses': luckiest['losses']
                }

        # Find unluckiest team (bottom 6, lowest Pythagorean wins difference)
        unluckiest_team = None
        bottom_half_teams = [t for t in final_standings if t['standing'] > 6]
        if bottom_half_teams:
            team_pyth_list = []
            for team in bottom_half_teams:
                pyth = team_pythagorean.get(team['id'], {})
                team_pyth_list.append({
                    'team_id': team['id'],
                    'expected': pyth.get('expected', 0.0),
                    'actual': pyth.get('actual', 0),
                    'difference': pyth.get('difference', 0.0),
                    'wins': team['wins'],
                    'losses': team['losses']
                })

            if team_pyth_list:
                team_pyth_list.sort(key=lambda x: x['difference'])  # Lowest first
                unluckiest = team_pyth_list[0]
                unluckiest_team = {
                    **team_id_to_info.get(unluckiest['team_id'], {}),
                    'expectedWins': unluckiest['expected'],
                    'actualWins': unluckiest['actual'],
                    'difference': unluckiest['difference'],
                    'wins': unluckiest['wins'],
                    'losses': unluckiest['losses']
                }

        # Find narrowest playoff winner (top 6, lowest avg margin of victory)
        narrowest_playoff_winner = None
        top_half_with_wins = [t for t in final_standings if t['standing'] <= 6 and t['id'] in team_wins_margins]
        if top_half_with_wins:
            team_avg_margins = []
            for team in top_half_with_wins:
                margins = team_wins_margins[team['id']]
                if margins:
                    avg_margin = sum(margins) / len(margins)
                    team_avg_margins.append({
                        'team_id': team['id'],
                        'avg_margin': avg_margin,
                        'wins': team['wins'],
                        'losses': team['losses']
                    })

            if team_avg_margins:
                team_avg_margins.sort(key=lambda x: x['avg_margin'])
                narrowest = team_avg_margins[0]
                narrowest_playoff_winner = {
                    **team_id_to_info.get(narrowest['team_id'], {}),
                    'avgMargin': round(narrowest['avg_margin'], 1),
                    'wins': narrowest['wins'],
                    'losses': narrowest['losses']
                }

        # Find closest playoff loser (bottom 6, lowest avg margin of loss)
        closest_playoff_loser = None
        bottom_half_with_losses = [t for t in final_standings if t['standing'] > 6 and t['id'] in team_loss_margins]
        if bottom_half_with_losses:
            team_avg_margins = []
            for team in bottom_half_with_losses:
                margins = team_loss_margins[team['id']]
                if margins:
                    avg_margin = sum(margins) / len(margins)
                    team_avg_margins.append({
                        'team_id': team['id'],
                        'avg_margin': avg_margin,
                        'wins': team['wins'],
                        'losses': team['losses']
                    })

            if team_avg_margins:
                team_avg_margins.sort(key=lambda x: x['avg_margin'])
                closest = team_avg_margins[0]
                closest_playoff_loser = {
                    **team_id_to_info.get(closest['team_id'], {}),
                    'avgMargin': round(closest['avg_margin'], 1),
                    'wins': closest['wins'],
                    'losses': closest['losses']
                }

        return {
            'weeklyHighScorerChampion': high_scorer_champion,
            'weeklyLowScorerChampion': low_scorer_champion,
            'luckiestTeam': luckiest_team,
            'unluckiestTeam': unluckiest_team,
            'narrowestPlayoffWinner': narrowest_playoff_winner,
            'closestPlayoffLoser': closest_playoff_loser
        }

    def _aggregate_team_stats(self, weekly_reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate per-team player statistics.

        Returns:
            {
                'teams': [
                    {
                        'teamId': int,
                        'teamName': str,
                        'logo': str,
                        'bgColor': str,
                        'fontColor': str,
                        'mostStarted': {...},
                        'mostBenched': {...},
                        'highestScorer': {...},
                        'lowestScoringStarter': {...},
                        'mostDisrespected': {...},
                        'winStreak': int,
                        'pythagoreanWins': {...}
                    },
                    ...
                ]
            }
        """
        from collections import defaultdict

        # Track player stats per team
        team_player_starts = defaultdict(lambda: defaultdict(int))  # team_id -> player_name -> start_count
        team_player_benches = defaultdict(lambda: defaultdict(int))  # team_id -> player_name -> bench_count
        team_player_total_points = defaultdict(lambda: defaultdict(float))  # team_id -> player_name -> total points while starting
        team_player_bench_points = defaultdict(lambda: defaultdict(float))  # team_id -> player_name -> total points while benched
        team_player_positions = defaultdict(lambda: defaultdict(str))  # team_id -> player_name -> position

        # Track win streaks
        team_win_history = defaultdict(list)  # team_id -> [True/False for each week]

        # Track points for/against for Pythagorean wins
        team_points_for = defaultdict(float)
        team_points_against = defaultdict(float)
        team_actual_wins = defaultdict(int)

        # Get team info
        team_id_to_info = {}
        if weekly_reports:
            for division in weekly_reports[0].get('divisions', []):
                for team in division.get('teams', []):
                    team_id_to_info[team['id']] = {
                        'teamId': team['id'],
                        'teamName': team['name'],
                        'logo': team.get('logo', ''),
                        'bgColor': team.get('bg_color', 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'),
                        'fontColor': team.get('font_color', '#ffffff')
                    }

        # Process each week
        for report in weekly_reports:
            week = report.get('week')
            matchups = report.get('matchups', [])

            # Track win/loss for each team this week
            week_winners = set()
            week_losers = set()

            # Process matchups
            for matchup in matchups:
                home_team = matchup.get('home_team', {})
                away_team = matchup.get('away_team', {})
                home_score = float(matchup.get('home_score', 0.0))
                away_score = float(matchup.get('away_score', 0.0))
                winner_id = matchup.get('winner_id')

                home_id = home_team.get('id')
                away_id = away_team.get('id')

                # Track points for/against
                if home_id:
                    team_points_for[home_id] += home_score
                    team_points_against[home_id] += away_score
                if away_id:
                    team_points_for[away_id] += away_score
                    team_points_against[away_id] += home_score

                # Track wins
                if winner_id == home_id:
                    team_actual_wins[home_id] += 1
                    week_winners.add(home_id)
                    week_losers.add(away_id)
                elif winner_id == away_id:
                    team_actual_wins[away_id] += 1
                    week_winners.add(away_id)
                    week_losers.add(home_id)

                # Get team names for player matching
                home_team_name = home_team.get('name', '')
                away_team_name = away_team.get('name', '')

                # Process players - try both data structures
                # Structure 1: home_players/away_players arrays (from templated HTML generator)
                home_players = matchup.get('home_players', [])
                away_players = matchup.get('away_players', [])

                # Structure 2: single players array with team field (from DynamoDB/raw JSON)
                if not home_players and not away_players:
                    all_players = matchup.get('players', [])
                    for player in all_players:
                        player_team = player.get('team', '')
                        if player_team == home_team_name:
                            home_players.append(player)
                        elif player_team == away_team_name:
                            away_players.append(player)

                # Process home team players
                for player in home_players:
                    self._process_player_stats(
                        player, home_id,
                        team_player_starts, team_player_benches,
                        team_player_total_points, team_player_bench_points,
                        team_player_positions
                    )

                # Process away team players
                for player in away_players:
                    self._process_player_stats(
                        player, away_id,
                        team_player_starts, team_player_benches,
                        team_player_total_points, team_player_bench_points,
                        team_player_positions
                    )

            # Record win/loss for all teams this week
            for team_id in team_id_to_info.keys():
                if team_id in week_winners:
                    team_win_history[team_id].append(True)
                elif team_id in week_losers:
                    team_win_history[team_id].append(False)

        # Calculate win streaks
        team_longest_streak = {}
        for team_id, history in team_win_history.items():
            max_streak = 0
            current_streak = 0
            for won in history:
                if won:
                    current_streak += 1
                    max_streak = max(max_streak, current_streak)
                else:
                    current_streak = 0
            team_longest_streak[team_id] = max_streak

        # Calculate Pythagorean wins
        team_pythagorean_wins = {}
        for team_id in team_id_to_info.keys():
            pf = team_points_for.get(team_id, 0.0)
            pa = team_points_against.get(team_id, 0.0)
            actual_wins = team_actual_wins.get(team_id, 0)

            if pf > 0 and pa > 0:
                expected_win_pct = (pf ** 2.37) / ((pf ** 2.37) + (pa ** 2.37))
                games_played = len(team_win_history.get(team_id, []))
                expected_wins = expected_win_pct * games_played
                team_pythagorean_wins[team_id] = {
                    'expected': round(expected_wins, 1),
                    'actual': actual_wins,
                    'difference': round(actual_wins - expected_wins, 1)
                }
            else:
                team_pythagorean_wins[team_id] = {
                    'expected': 0.0,
                    'actual': actual_wins,
                    'difference': 0.0
                }

        # Build team stats list
        teams_list = []
        for team_id, team_info in team_id_to_info.items():
            # Most started player
            most_started = None
            if team_id in team_player_starts and team_player_starts[team_id]:
                player_name = max(team_player_starts[team_id].items(), key=lambda x: x[1])[0]
                most_started = {
                    'playerName': player_name,
                    'position': team_player_positions[team_id].get(player_name, 'N/A'),
                    'startCount': team_player_starts[team_id][player_name]
                }

            # Most benched player
            most_benched = None
            if team_id in team_player_benches and team_player_benches[team_id]:
                player_name = max(team_player_benches[team_id].items(), key=lambda x: x[1])[0]
                most_benched = {
                    'playerName': player_name,
                    'position': team_player_positions[team_id].get(player_name, 'N/A'),
                    'benchCount': team_player_benches[team_id][player_name]
                }

            # Highest scoring player (season total while starting)
            highest_scorer = None
            if team_id in team_player_total_points and team_player_total_points[team_id]:
                player_name = max(team_player_total_points[team_id].items(), key=lambda x: x[1])[0]
                highest_scorer = {
                    'playerName': player_name,
                    'position': team_player_positions[team_id].get(player_name, 'N/A'),
                    'totalPoints': round(team_player_total_points[team_id][player_name], 1)
                }

            # Lowest scoring starter (regular starters only - started > 1 week, by average)
            lowest_starter = None
            if team_id in team_player_starts and team_player_starts[team_id]:
                # Filter to players who started more than 1 week, calculate averages
                regular_starters = {}
                for name, starts in team_player_starts[team_id].items():
                    if starts > 1:
                        total_pts = team_player_total_points[team_id][name]
                        avg_pts = total_pts / starts
                        regular_starters[name] = {
                            'total': total_pts,
                            'starts': starts,
                            'avg': avg_pts
                        }
                if regular_starters:
                    # Find player with lowest average
                    player_name = min(regular_starters.items(), key=lambda x: x[1]['avg'])[0]
                    stats = regular_starters[player_name]
                    lowest_starter = {
                        'playerName': player_name,
                        'position': team_player_positions[team_id].get(player_name, 'N/A'),
                        'avgPoints': round(stats['avg'], 1),
                        'startCount': stats['starts']
                    }

            # Most disrespected player (highest total bench points over season)
            most_disrespected = None
            if team_id in team_player_bench_points and team_player_bench_points[team_id]:
                player_name = max(team_player_bench_points[team_id].items(), key=lambda x: x[1])[0]
                total_bench_pts = team_player_bench_points[team_id][player_name]
                bench_count = team_player_benches[team_id].get(player_name, 0)
                most_disrespected = {
                    'playerName': player_name,
                    'position': team_player_positions[team_id].get(player_name, 'N/A'),
                    'totalPoints': round(total_bench_pts, 1),
                    'benchCount': bench_count
                }

            teams_list.append({
                **team_info,
                'mostStarted': most_started,
                'mostBenched': most_benched,
                'highestScorer': highest_scorer,
                'lowestScoringStarter': lowest_starter,
                'mostDisrespected': most_disrespected,
                'winStreak': team_longest_streak.get(team_id, 0),
                'pythagoreanWins': team_pythagorean_wins.get(team_id, {'expected': 0.0, 'actual': 0, 'difference': 0.0})
            })

        # Sort alphabetically by team name
        teams_list.sort(key=lambda t: t['teamName'])

        return {'teams': teams_list}

    def _process_player_stats(self, player: Dict[str, Any], team_id: int,
                              team_player_starts: defaultdict, team_player_benches: defaultdict,
                              team_player_total_points: defaultdict, team_player_bench_points: defaultdict,
                              team_player_positions: defaultdict) -> None:
        """Helper method to process individual player stats."""
        player_name = player.get('name')
        if not player_name:
            return

        position = player.get('position', 'N/A')
        is_starter = player.get('is_starter', False)
        roster_slot = player.get('roster_slot', '')
        actual_score = float(player.get('actual_score', 0.0))

        # Store position
        team_player_positions[team_id][player_name] = position

        # Track starts - accumulate total points while starting
        if is_starter:
            team_player_starts[team_id][player_name] += 1
            team_player_total_points[team_id][player_name] += actual_score

        # Track benches - accumulate total bench points for "most disrespected"
        if roster_slot == 'BE':
            team_player_benches[team_id][player_name] += 1
            team_player_bench_points[team_id][player_name] += actual_score

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
                      season_recap: Dict[str, Any],
                      team_stats: Dict[str, Any],
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
        season_recap = self._convert_decimals(season_recap)
        team_stats = self._convert_decimals(team_stats)
        league_metadata = self._convert_decimals(league_metadata)

        # Convert data to JSON strings for embedding
        teams_json = json.dumps(teams_data, indent=4)
        awards_json = json.dumps(awards_data, indent=4)
        weekly_json = json.dumps(weekly_highlights, indent=4)
        season_recap_json = json.dumps(season_recap, indent=4)
        team_stats_json = json.dumps(team_stats, indent=4)

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

        # Replace seasonRecapData
        season_recap_pattern = r'const seasonRecapData = \{[\s\S]*?\n        \};'
        html_content = re.sub(season_recap_pattern,
                             lambda m: f'const seasonRecapData = {season_recap_json};',
                             html_content, count=1)

        # Replace teamStatsData
        team_stats_pattern = r'const teamStatsData = \{[\s\S]*?\n        \};'
        html_content = re.sub(team_stats_pattern,
                             lambda m: f'const teamStatsData = {team_stats_json};',
                             html_content, count=1)

        return html_content
