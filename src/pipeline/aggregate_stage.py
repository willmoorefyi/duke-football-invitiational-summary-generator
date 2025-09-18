"""
Aggregate Stage

Stage 3: Aggregate Data Generation
Combines current week data with historical DynamoDB data to create
enhanced JSON with season context.
Currently a scaffold - needs DynamoDB integration.
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from .base import PipelineStage
from decimal import Decimal


class AggregateStage(PipelineStage):
    """
    Stage 3: Aggregate Data Generation

    Combines current week data with historical DynamoDB data to create
    enhanced JSON with season context.
    Currently a scaffold - needs DynamoDB integration.
    """

    def execute(self, current_week_file: str,
                dynamodb_record_id: Optional[str] = None,
                output_dir: Optional[str] = None) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Aggregate current week data with historical context.

        Args:
            current_week_file: Path to current week JSON from extract stage
            dynamodb_record_id: Record ID from upload stage (for tracking)
            output_dir: Output directory (defaults to config)

        Returns:
            Tuple of (enhanced_json_path, metadata)
        """
        self.logger.info(f"Starting data aggregation for file: {current_week_file}")

        # Determine output directory
        if output_dir is None:
            output_dir = 'output/enhanced'

        # Ensure output directory exists
        output_path = self._ensure_output_directory(output_dir)

        if self.dry_run:
            self.logger.info(f"DRY RUN: Would aggregate data and save to {output_path}")
            return None, {"dry_run": True}

        try:
            # Load current week data
            with open(current_week_file, 'r') as f:
                current_data = json.load(f)

            # Fetch historical data from DynamoDB for multi-week context
            historical_data = self._fetch_historical_data(current_data)

            # Calculate enhanced season context with historical data
            enhanced_data = self._create_enhanced_data(current_data, dynamodb_record_id, historical_data)

            # Save enhanced JSON
            week = current_data.get('week', 'unknown')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_path / f"enhanced_week_{week}_{timestamp}.json"

            with open(output_file, 'w') as f:
                json.dump(enhanced_data, f, indent=2, default=str)

            self.logger.info(f"Successfully aggregated data to {output_file}")
            self.logger.warning("Historical data aggregation not yet implemented - using current week only")

            metadata = {
                "week": week,
                "enhanced_file": str(output_file),
                "historical_weeks_count": 0,  # TODO: Actual count
                "aggregation_timestamp": timestamp
            }

            return str(output_file), metadata

        except Exception as e:
            self.logger.error(f"Failed to aggregate data: {e}")
            raise

    def _convert_decimal_to_float(self, obj: Any) -> Any:
        """
        Recursively convert DynamoDB Decimal objects to float for JSON compatibility.

        Args:
            obj: Object that may contain Decimal values

        Returns:
            Object with Decimal values converted to float
        """
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {key: self._convert_decimal_to_float(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimal_to_float(item) for item in obj]
        else:
            return obj

    def _fetch_historical_data(self, current_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch historical weekly data from DynamoDB for the current season.

        Args:
            current_data: Current week data to extract season/league info

        Returns:
            List of historical week data records
        """
        try:
            # Extract current season and league info
            current_season = current_data.get('season', datetime.now().year)
            current_week = current_data.get('week', 1)
            league_id = current_data.get('league_id')

            if not league_id:
                self.logger.warning("No league_id found, skipping historical data fetch")
                return []

            # Check if boto3 is available
            try:
                import boto3
                from botocore.exceptions import ClientError, NoCredentialsError
            except ImportError:
                self.logger.warning("boto3 not available, skipping historical data fetch")
                return []

            # Get AWS configuration
            table_name = self.config.pipeline.aws.dynamodb_table
            region = self.config.pipeline.aws.region

            self.logger.info(f"Fetching historical data from DynamoDB table '{table_name}' for league {league_id}, season {current_season}")

            # Create DynamoDB resource
            dynamodb = boto3.resource('dynamodb', region_name=region)
            table = dynamodb.Table(table_name)

            historical_records = []

            # Query for all weeks in current season (from week 1 to current_week - 1)
            for week_num in range(1, current_week):
                season_week = f"{current_season}-{week_num:02d}"

                try:
                    # Query for the weekly_report record for this season_week
                    response = table.get_item(
                        Key={
                            'season_week': season_week,
                            'data_type_id': 'weekly_report'
                        }
                    )

                    if 'Item' in response:
                        item = response['Item']
                        # Verify this record is for the correct league
                        if str(item.get('league_id', '')) == str(league_id):
                            # Extract the embedded week data and convert Decimal values to float
                            week_data = item.get('data', {})
                            if week_data:
                                # Convert Decimal values from DynamoDB to float
                                week_data_converted = self._convert_decimal_to_float(week_data)
                                historical_records.append(week_data_converted)
                                self.logger.info(f"Retrieved historical data for week {week_num}")
                        else:
                            self.logger.debug(f"League ID mismatch for week {week_num}: found {item.get('league_id')}, expected {league_id}")
                    else:
                        self.logger.debug(f"No data found for week {week_num}")

                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                    if error_code == 'ResourceNotFoundException':
                        self.logger.warning(f"DynamoDB table '{table_name}' not found")
                        return []
                    else:
                        self.logger.warning(f"Error querying DynamoDB for week {week_num}: {e}")

            self.logger.info(f"Successfully fetched {len(historical_records)} historical week records")
            return historical_records

        except NoCredentialsError:
            self.logger.warning("AWS credentials not available, skipping historical data fetch")
            return []
        except Exception as e:
            self.logger.warning(f"Failed to fetch historical data: {e}")
            return []

    def _create_enhanced_data(self, current_data: Dict[str, Any], dynamodb_record_id: Optional[str], historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create enhanced data structure with season context from current and historical week data.

        Args:
            current_data: Current week raw data
            dynamodb_record_id: DynamoDB record ID for tracking
            historical_data: List of historical week data from DynamoDB

        Returns:
            Enhanced data structure with season context
        """
        try:
            # Extract basic info
            week = current_data.get('week', 1)
            season = current_data.get('season', datetime.now().year)
            league_id = current_data.get('league_id')

            # Combine current data with historical data for comprehensive analysis
            all_weeks_data = historical_data + [current_data]

            # Calculate team performance metrics across all weeks
            team_performance = self._calculate_multi_week_team_performance(all_weeks_data)

            # Calculate standings from current week (for progression baseline)
            current_standings = self._extract_current_standings(current_data)

            # Calculate matchup statistics across all weeks
            matchup_stats = self._calculate_multi_week_matchup_statistics(all_weeks_data)

            # Calculate award summaries across all weeks
            award_summaries = self._calculate_multi_week_award_summaries(all_weeks_data)

            # Calculate running totals across all teams and weeks
            running_totals = self._calculate_multi_week_running_totals(all_weeks_data)

            # Calculate weekly statistics for all weeks (for Weekly Totals table)
            weekly_stats = self._calculate_all_weeks_statistics(all_weeks_data)

            # Create enhanced structure
            enhanced_data = {
                "current_week": current_data,
                "season_context": {
                    "standings_progression": [
                        {
                            "week": week,
                            "standings": current_standings,
                            "timestamp": datetime.now().isoformat()
                        }
                    ],
                    "matchup_history": {
                        "head_to_head_records": {},  # TODO: Requires historical data
                        "current_week_matchups": matchup_stats,
                        "season_summary": {
                            "total_weeks_processed": 1,
                            "average_scores": team_performance.get("average_scores", {}),
                            "highest_weekly_score": team_performance.get("highest_score", 0),
                            "lowest_weekly_score": team_performance.get("lowest_score", 0)
                        }
                    },
                    "award_summaries": award_summaries,
                    "performance_trends": {
                        "team_metrics": team_performance,
                        "weekly_averages": {
                            "league_average_score": team_performance.get("league_average", 0),
                            "total_points_scored": team_performance.get("total_points", 0)
                        }
                    },
                    "running_totals": running_totals,
                    "weekly_statistics": weekly_stats
                },
                "metadata": {
                    "aggregation_timestamp": datetime.now().isoformat(),
                    "dynamodb_record_id": dynamodb_record_id,
                    "historical_weeks_included": len(historical_data),
                    "season": season,
                    "league_id": league_id,
                    "current_week": week,
                    "total_weeks_processed": len(all_weeks_data),
                    "data_source": "multi_week" if historical_data else "current_week_only"
                }
            }

            return enhanced_data

        except Exception as e:
            self.logger.error(f"Failed to create enhanced data structure: {e}")
            # Return minimal structure on error
            return {
                "current_week": current_data,
                "season_context": {
                    "standings_progression": [],
                    "matchup_history": {},
                    "award_summaries": {},
                    "performance_trends": {}
                },
                "metadata": {
                    "aggregation_timestamp": datetime.now().isoformat(),
                    "dynamodb_record_id": dynamodb_record_id,
                    "historical_weeks_included": 0,
                    "error": str(e)
                }
            }

    def _calculate_team_performance_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate team performance metrics from current week data"""
        try:
            matchups = data.get('matchups', [])
            all_scores = []
            team_scores = {}

            for matchup in matchups:
                home_score = matchup.get('home_team', {}).get('score', 0)
                away_score = matchup.get('away_team', {}).get('score', 0)

                home_id = matchup.get('home_team', {}).get('id')
                away_id = matchup.get('away_team', {}).get('id')

                if home_id:
                    team_scores[home_id] = home_score
                    all_scores.append(home_score)
                if away_id:
                    team_scores[away_id] = away_score
                    all_scores.append(away_score)

            if not all_scores:
                return {"error": "No scores found"}

            return {
                "average_scores": team_scores,
                "league_average": sum(all_scores) / len(all_scores) if all_scores else 0,
                "highest_score": max(all_scores) if all_scores else 0,
                "lowest_score": min(all_scores) if all_scores else 0,
                "total_points": sum(all_scores),
                "total_teams": len(team_scores)
            }
        except Exception as e:
            return {"error": str(e)}

    def _extract_current_standings(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract current standings from division data"""
        try:
            standings = []
            divisions = data.get('divisions', [])

            for division in divisions:
                division_name = division.get('name', 'Unknown')
                teams = division.get('teams', [])

                for team in teams:
                    standings.append({
                        "team_id": team.get('id'),
                        "team_name": team.get('name'),
                        "division": division_name,
                        "wins": team.get('wins', 0),
                        "losses": team.get('losses', 0),
                        "ties": team.get('ties', 0),
                        "points_for": team.get('points_for', 0),
                        "points_against": team.get('points_against', 0),
                        "rank": team.get('rank', 0)
                    })

            return standings
        except Exception as e:
            self.logger.warning(f"Failed to extract standings: {e}")
            return []

    def _calculate_matchup_statistics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate matchup statistics from current week"""
        try:
            matchups = data.get('matchups', [])
            stats = {
                "total_matchups": len(matchups),
                "completed_matchups": 0,
                "blowouts": [],  # Wins by > 30 points
                "close_games": [],  # Wins by < 10 points
                "upsets": []  # Lower seed beating higher seed
            }

            for matchup in matchups:
                home_score = matchup.get('home_team', {}).get('score', 0)
                away_score = matchup.get('away_team', {}).get('score', 0)

                if home_score > 0 or away_score > 0:
                    stats["completed_matchups"] += 1

                    # Calculate margin
                    margin = abs(home_score - away_score)

                    if margin > 30:
                        stats["blowouts"].append({
                            "winner": matchup.get('home_team', {}).get('name') if home_score > away_score else matchup.get('away_team', {}).get('name'),
                            "margin": margin
                        })
                    elif margin < 10:
                        stats["close_games"].append({
                            "winner": matchup.get('home_team', {}).get('name') if home_score > away_score else matchup.get('away_team', {}).get('name'),
                            "margin": margin
                        })

            return stats
        except Exception as e:
            self.logger.warning(f"Failed to calculate matchup statistics: {e}")
            return {"error": str(e)}

    def _calculate_award_summaries(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate award summaries from current week awards"""
        try:
            awards = data.get('awards', {})
            summaries = {
                "current_week_awards": awards,
                "season_totals": {
                    "mvp_winners": [],
                    "mwp_winners": [],
                    "mup_winners": [],
                    "mdp_winners": [],
                    "team_awards": {}
                }
            }

            # Extract current week award winners for season tracking
            if awards.get('mvp'):
                summaries["season_totals"]["mvp_winners"].append({
                    "week": data.get('week', 1),
                    "player": awards['mvp'].get('player_name'),
                    "team": awards['mvp'].get('team_name'),
                    "score": awards['mvp'].get('score')
                })

            # Add other awards similarly
            for award_type in ['mwp', 'mup', 'mdp']:
                if awards.get(award_type):
                    summaries["season_totals"][f"{award_type}_winners"].append({
                        "week": data.get('week', 1),
                        "player": awards[award_type].get('player_name'),
                        "team": awards[award_type].get('team_name'),
                        "score": awards[award_type].get('score')
                    })

            return summaries
        except Exception as e:
            self.logger.warning(f"Failed to calculate award summaries: {e}")
            return {"error": str(e)}

    def _calculate_running_totals(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate running totals for all teams from matchup data"""
        try:
            matchups = data.get('matchups', [])
            team_totals = {}

            # Get all team info from divisions first to ensure we have all teams
            divisions = data.get('divisions', [])
            all_teams = {}
            for division in divisions:
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
            for matchup in matchups:
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

            # Calculate efficiency percentages and format data
            for team_id, team_data in all_teams.items():
                if team_data['optimal'] > 0:
                    team_data['efficiency'] = (team_data['actual'] / team_data['optimal']) * 100
                else:
                    team_data['efficiency'] = 0.0

                team_totals[team_id] = team_data

            return team_totals

        except Exception as e:
            self.logger.warning(f"Failed to calculate running totals: {e}")
            return {"error": str(e)}

    def _calculate_multi_week_team_performance(self, all_weeks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate team performance metrics across multiple weeks"""
        try:
            all_scores = []
            team_scores_by_week = {}
            team_total_scores = {}

            for week_data in all_weeks_data:
                week_num = week_data.get('week', 0)
                matchups = week_data.get('matchups', [])

                for matchup in matchups:
                    home_team = matchup.get('home_team', {})
                    away_team = matchup.get('away_team', {})
                    home_score = matchup.get('home_score', 0)
                    away_score = matchup.get('away_score', 0)

                    # Track all scores
                    all_scores.extend([home_score, away_score])

                    # Track by team
                    home_name = home_team.get('name', '')
                    away_name = away_team.get('name', '')

                    if home_name:
                        if home_name not in team_total_scores:
                            team_total_scores[home_name] = []
                        team_total_scores[home_name].append(home_score)

                    if away_name:
                        if away_name not in team_total_scores:
                            team_total_scores[away_name] = []
                        team_total_scores[away_name].append(away_score)

            # Calculate averages and totals
            team_averages = {}
            for team_name, scores in team_total_scores.items():
                team_averages[team_name] = sum(scores) / len(scores) if scores else 0

            return {
                "average_scores": team_averages,
                "league_average": sum(all_scores) / len(all_scores) if all_scores else 0,
                "highest_score": max(all_scores) if all_scores else 0,
                "lowest_score": min(all_scores) if all_scores else 0,
                "total_points": sum(all_scores),
                "total_weeks": len(all_weeks_data)
            }

        except Exception as e:
            self.logger.warning(f"Failed to calculate multi-week team performance: {e}")
            return {"error": str(e)}

    def _calculate_multi_week_matchup_statistics(self, all_weeks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate matchup statistics across multiple weeks"""
        try:
            all_matchups = []
            for week_data in all_weeks_data:
                all_matchups.extend(week_data.get('matchups', []))

            stats = {
                "total_matchups": len(all_matchups),
                "completed_matchups": 0,
                "blowouts": [],
                "close_games": [],
                "upsets": []
            }

            for matchup in all_matchups:
                home_score = matchup.get('home_score', 0)
                away_score = matchup.get('away_score', 0)

                if home_score > 0 or away_score > 0:
                    stats["completed_matchups"] += 1
                    margin = abs(home_score - away_score)

                    if margin > 30:
                        stats["blowouts"].append({
                            "winner": matchup.get('home_team', {}).get('name') if home_score > away_score else matchup.get('away_team', {}).get('name'),
                            "margin": margin,
                            "week": matchup.get('week', 0)
                        })
                    elif margin < 10:
                        stats["close_games"].append({
                            "winner": matchup.get('home_team', {}).get('name') if home_score > away_score else matchup.get('away_team', {}).get('name'),
                            "margin": margin,
                            "week": matchup.get('week', 0)
                        })

            return stats

        except Exception as e:
            self.logger.warning(f"Failed to calculate multi-week matchup statistics: {e}")
            return {"error": str(e)}

    def _calculate_multi_week_award_summaries(self, all_weeks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate award summaries across multiple weeks"""
        try:
            summaries = {
                "season_totals": {
                    "mvp_winners": [],
                    "mwp_winners": [],
                    "mup_winners": [],
                    "mdp_winners": [],
                    "team_awards": {}
                }
            }

            for week_data in all_weeks_data:
                week_num = week_data.get('week', 0)
                awards = week_data.get('awards', {})

                # Track player awards
                for award_type in ['mvp', 'mwp', 'mup', 'mdp']:
                    if awards.get(award_type):
                        award = awards[award_type]
                        summaries["season_totals"][f"{award_type}_winners"].append({
                            "week": week_num,
                            "player": award.get('player_name'),
                            "team": award.get('team_name'),
                            "score": award.get('score')
                        })

            return summaries

        except Exception as e:
            self.logger.warning(f"Failed to calculate multi-week award summaries: {e}")
            return {"error": str(e)}

    def _calculate_multi_week_running_totals(self, all_weeks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate running totals across all teams and weeks"""
        try:
            team_totals = {}

            # Get team info from the most recent week data (which should be current_data)
            if all_weeks_data:
                latest_week = all_weeks_data[-1]
                divisions = latest_week.get('divisions', [])
                for division in divisions:
                    for team in division.get('teams', []):
                        team_id = team.get('id')
                        if team_id:
                            team_totals[team_id] = {
                                'name': team.get('name', ''),
                                'logo': team.get('logo', ''),
                                'division': team.get('division', ''),
                                'actual': 0.0,
                                'projected': 0.0,
                                'optimal': 0.0,
                                'efficiency': 0.0
                            }

            # Accumulate scores across all weeks
            for week_data in all_weeks_data:
                matchups = week_data.get('matchups', [])
                for matchup in matchups:
                    home_team_id = matchup.get('home_team', {}).get('id')
                    away_team_id = matchup.get('away_team', {}).get('id')

                    home_score = matchup.get('home_score', 0)
                    away_score = matchup.get('away_score', 0)
                    home_projected = matchup.get('home_projected_score', 0)
                    away_projected = matchup.get('away_projected_score', 0)
                    home_optimal = matchup.get('home_optimal_score', 0)
                    away_optimal = matchup.get('away_optimal_score', 0)

                    # Update home team totals
                    if home_team_id and home_team_id in team_totals:
                        team_totals[home_team_id]['actual'] += home_score
                        team_totals[home_team_id]['projected'] += home_projected
                        team_totals[home_team_id]['optimal'] += home_optimal

                    # Update away team totals
                    if away_team_id and away_team_id in team_totals:
                        team_totals[away_team_id]['actual'] += away_score
                        team_totals[away_team_id]['projected'] += away_projected
                        team_totals[away_team_id]['optimal'] += away_optimal

            # Calculate efficiency percentages
            for team_id, team_data in team_totals.items():
                if team_data['optimal'] > 0:
                    team_data['efficiency'] = (team_data['actual'] / team_data['optimal']) * 100
                else:
                    team_data['efficiency'] = 0.0

            return team_totals

        except Exception as e:
            self.logger.warning(f"Failed to calculate multi-week running totals: {e}")
            return {"error": str(e)}

    def _calculate_all_weeks_statistics(self, all_weeks_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Calculate statistics for each individual week (for Weekly Totals table)"""
        try:
            weekly_statistics = []

            for week_data in all_weeks_data:
                week_num = week_data.get('week', 0)
                matchups = week_data.get('matchups', [])

                # Collect all scores for this week
                scores = []
                team_scores = []  # For finding max/min teams

                for matchup in matchups:
                    home_team = matchup.get('home_team', {})
                    away_team = matchup.get('away_team', {})
                    # Ensure scores are float, not Decimal or string
                    home_score = float(matchup.get('home_score', 0))
                    away_score = float(matchup.get('away_score', 0))
                    home_optimal = float(matchup.get('home_optimal_score', home_score))
                    away_optimal = float(matchup.get('away_optimal_score', away_score))

                    scores.extend([home_score, away_score])

                    # Calculate efficiency for each team this week
                    home_efficiency = (home_score / home_optimal * 100) if home_optimal > 0 else 0.0
                    away_efficiency = (away_score / away_optimal * 100) if away_optimal > 0 else 0.0

                    team_scores.append({
                        'team': home_team,
                        'score': home_score,
                        'efficiency': home_efficiency
                    })
                    team_scores.append({
                        'team': away_team,
                        'score': away_score,
                        'efficiency': away_efficiency
                    })

                if scores:
                    # Calculate basic statistics
                    import statistics
                    median_score = statistics.median(scores)
                    mean_score = statistics.mean(scores)
                    std_dev = statistics.stdev(scores) if len(scores) > 1 else 0.0
                    max_score = max(scores)
                    min_score = min(scores)

                    # Find teams with max/min scores
                    max_team = next((ts for ts in team_scores if ts['score'] == max_score), None)
                    min_team = next((ts for ts in team_scores if ts['score'] == min_score), None)

                    # Calculate average efficiency for the week
                    efficiencies = [ts['efficiency'] for ts in team_scores]
                    avg_efficiency = statistics.mean(efficiencies) if efficiencies else 0.0

                    weekly_statistics.append({
                        'week': int(week_num),
                        'median': float(median_score),
                        'average': float(mean_score),
                        'max': float(max_score),
                        'min': float(min_score),
                        'std_dev': float(std_dev),
                        'max_team_name': str(max_team['team'].get('name', '') if max_team else ''),
                        'max_logo_url': '', # Will be populated by template logic
                        'min_team_name': str(min_team['team'].get('name', '') if min_team else ''),
                        'min_logo_url': '', # Will be populated by template logic
                        'average_efficiency': float(avg_efficiency)
                    })

            return {'weeks': weekly_statistics}

        except Exception as e:
            self.logger.warning(f"Failed to calculate weekly statistics: {e}")
            return {"error": str(e)}