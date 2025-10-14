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
            condensed_output_path = self._ensure_output_directory('output/condensed')
            self.logger.info(f"DRY RUN: Would aggregate data and save enhanced to {output_path}")
            self.logger.info(f"DRY RUN: Would save condensed data to {condensed_output_path}")
            return None, {"dry_run": True}

        try:
            # Load current week data
            with open(current_week_file, 'r') as f:
                current_data = json.load(f)

            # Fetch historical data from DynamoDB for multi-week context
            historical_data, is_latest_week = self._fetch_historical_data(current_data)

            # Fetch league history from DynamoDB
            league_id = current_data.get('league_id')
            league_history = None
            if league_id:
                league_history = self._fetch_league_history(str(league_id))

            # Calculate enhanced season context with historical data
            enhanced_data = self._create_enhanced_data(current_data, dynamodb_record_id, historical_data, is_latest_week, league_history)

            # Create condensed data from enhanced data
            condensed_data = self._create_condensed_data(enhanced_data)

            # Save enhanced JSON
            week = current_data.get('week', 'unknown')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_path / f"enhanced_week_{week}_{timestamp}.json"

            with open(output_file, 'w') as f:
                json.dump(enhanced_data, f, indent=2, default=str)

            # Save condensed JSON
            condensed_output_path = self._ensure_output_directory('output/condensed')
            condensed_output_file = condensed_output_path / f"condensed_week_{week}_{timestamp}.json"

            with open(condensed_output_file, 'w') as f:
                json.dump(condensed_data, f, indent=2, default=str)

            # Log success with historical data details
            historical_weeks_count = len(historical_data)
            total_weeks = historical_weeks_count + 1  # +1 for current week

            if historical_weeks_count > 0:
                self.logger.info(f"Successfully aggregated data to {output_file} with {historical_weeks_count} historical weeks (total: {total_weeks} weeks)")
                self.logger.info(f"Generated condensed data file: {condensed_output_file}")
            else:
                self.logger.info(f"Successfully aggregated data to {output_file} (current week only, no historical data available)")
                self.logger.info(f"Generated condensed data file: {condensed_output_file}")

            metadata = {
                "week": week,
                "enhanced_file": str(output_file),
                "condensed_file": str(condensed_output_file),
                "historical_weeks_count": historical_weeks_count,
                "aggregation_timestamp": timestamp
            }

            return str(output_file), metadata

        except Exception as e:
            self.logger.error(f"Failed to aggregate data: {e}")
            raise

    def _convert_decimal_to_float(self, obj: Any, parent_key: str = None) -> Any:
        """
        Recursively convert DynamoDB Decimal objects to float/int for JSON compatibility.

        Converts whole number floats to integers for specific fields like wins, losses,
        playoff_weeks, team_id, etc.

        Args:
            obj: Object that may contain Decimal values
            parent_key: Key name from parent dict for context

        Returns:
            Object with Decimal values converted to appropriate numeric types
        """
        # Fields that should always be integers
        integer_fields = {
            'year', 'wins', 'losses', 'ties', 'rank', 'final_standing',
            'playoff_seed', 'team_id', 'division_id', 'playoff_weeks',
            'regular_season_weeks', 'total_teams', 'total_seasons'
        }

        if isinstance(obj, Decimal):
            float_val = float(obj)
            # Convert to int if it's a whole number and should be an integer
            if parent_key in integer_fields and float_val == int(float_val):
                return int(float_val)
            return float_val
        elif isinstance(obj, float):
            # Also handle regular floats that should be integers
            if parent_key in integer_fields and obj == int(obj):
                return int(obj)
            return obj
        elif isinstance(obj, dict):
            return {key: self._convert_decimal_to_float(value, key) for key, value in obj.items()}
        elif isinstance(obj, list):
            # For lists like seasons_list, convert whole numbers to int
            if parent_key == 'seasons_list':
                return [int(item) if isinstance(item, (float, Decimal)) and item == int(item) else item for item in obj]
            return [self._convert_decimal_to_float(item, parent_key) for item in obj]
        else:
            return obj

    def _fetch_historical_data(self, current_data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Fetch historical weekly data from DynamoDB for the current season.
        Also determines if the current week is the latest completed week.

        Args:
            current_data: Current week data to extract season/league info

        Returns:
            Tuple of (historical week data records, is_latest_week flag)
        """
        try:
            # Extract current season and league info
            current_season = current_data.get('season', datetime.now().year)
            current_week = current_data.get('week', 1)
            league_id = current_data.get('league_id')

            if not league_id:
                self.logger.warning("No league_id found, skipping historical data fetch")
                return [], True  # Assume latest if no league_id

            # Check if boto3 is available
            try:
                import boto3
                from botocore.exceptions import ClientError, NoCredentialsError
            except ImportError:
                self.logger.warning("boto3 not available, skipping historical data fetch")
                return [], True  # Assume latest if boto3 not available

            # Get AWS configuration
            table_name = self.config.pipeline.aws.dynamodb_table
            region = self.config.pipeline.aws.region
            profile = getattr(self.config.pipeline.aws, 'profile', None)

            self.logger.info(f"Fetching historical data from DynamoDB table '{table_name}' for league {league_id}, season {current_season}")

            # Create DynamoDB resource with profile support
            if profile:
                session = boto3.Session(profile_name=profile, region_name=region)
                dynamodb = session.resource('dynamodb')
            else:
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
                                # Handle both raw and enhanced data formats
                                if 'current_week' in week_data:
                                    # Enhanced format: extract the raw week data from current_week
                                    raw_week_data = week_data.get('current_week', {})
                                else:
                                    # Raw format: use data as-is
                                    raw_week_data = week_data

                                # Convert Decimal values from DynamoDB to float
                                week_data_converted = self._convert_decimal_to_float(raw_week_data)
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
                        return [], True
                    else:
                        self.logger.warning(f"Error querying DynamoDB for week {week_num}: {e}")

            # Check if any weeks exist AFTER the current week (to determine if this is latest)
            is_latest_week = True
            max_check_weeks = 5  # Check up to 5 weeks ahead
            for future_week_num in range(current_week + 1, current_week + max_check_weeks + 1):
                season_week = f"{current_season}-{future_week_num:02d}"
                try:
                    response = table.get_item(
                        Key={
                            'season_week': season_week,
                            'data_type_id': 'weekly_report'
                        }
                    )

                    if 'Item' in response:
                        item = response['Item']
                        # If we find a future week for this league, current week is NOT latest
                        if str(item.get('league_id', '')) == str(league_id):
                            is_latest_week = False
                            self.logger.info(f"Found data for week {future_week_num}, so week {current_week} is NOT the latest")
                            break
                except ClientError:
                    # If we hit an error checking future weeks, ignore and continue
                    pass

            if is_latest_week:
                self.logger.info(f"Week {current_week} is the latest completed week in the season")

            self.logger.info(f"Successfully fetched {len(historical_records)} historical week records")
            return historical_records, is_latest_week

        except NoCredentialsError:
            self.logger.warning("AWS credentials not available, skipping historical data fetch")
            return [], True
        except Exception as e:
            self.logger.warning(f"Failed to fetch historical data: {e}")
            return [], True

    def _fetch_league_history(self, league_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch league history from DynamoDB.

        Args:
            league_id: League identifier

        Returns:
            League history data or None if not found/error
        """
        try:
            # Check if boto3 is available
            try:
                import boto3
                from botocore.exceptions import ClientError, NoCredentialsError
            except ImportError:
                self.logger.warning("boto3 not available, skipping league history fetch")
                return None

            # Get AWS configuration
            table_name = self.config.pipeline.aws.dynamodb_table
            region = self.config.pipeline.aws.region
            profile = getattr(self.config.pipeline.aws, 'profile', None)

            self.logger.info(f"Fetching league history from DynamoDB table '{table_name}' for league {league_id}")

            # Create DynamoDB resource with profile support
            if profile:
                session = boto3.Session(profile_name=profile, region_name=region)
                dynamodb = session.resource('dynamodb')
            else:
                dynamodb = boto3.resource('dynamodb', region_name=region)

            # Import HistoryUploader
            try:
                from ..uploaders.history_uploader import HistoryUploader
            except ImportError:
                from src.uploaders.history_uploader import HistoryUploader

            # Create uploader with configured dynamodb resource
            uploader = HistoryUploader(dynamodb_resource=dynamodb, table_name=table_name)

            # Fetch league history
            result = uploader.fetch_league_history(str(league_id))

            if result:
                # Convert Decimal values to float for JSON compatibility
                result_converted = self._convert_decimal_to_float(result)
                self.logger.info(f"Successfully fetched league history: {result_converted.get('metadata', {}).get('total_seasons', 0)} seasons")
                return result_converted
            else:
                self.logger.info(f"No league history found for league {league_id}")
                return None

        except NoCredentialsError:
            self.logger.warning("AWS credentials not available, skipping league history fetch")
            return None
        except Exception as e:
            self.logger.warning(f"Failed to fetch league history: {e}")
            return None

    def _create_enhanced_data(self, current_data: Dict[str, Any], dynamodb_record_id: Optional[str], historical_data: List[Dict[str, Any]], is_latest_week: bool, league_history: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create enhanced data structure with season context from current and historical week data.

        Args:
            current_data: Current week raw data
            dynamodb_record_id: DynamoDB record ID for tracking
            historical_data: List of historical week data from DynamoDB
            is_latest_week: Flag indicating if current week is the latest completed week
            league_history: League history data with champions and season records

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

            # Calculate cumulative team standings from matchup results
            team_standings = self._calculate_team_standings(all_weeks_data, week)

            # Calculate matchup history with weekly results
            matchup_history = self._calculate_matchup_history(all_weeks_data)

            # Calculate award summaries across all weeks
            award_summaries = self._calculate_multi_week_award_summaries(all_weeks_data)

            # Calculate running totals across all teams and weeks
            running_totals = self._calculate_multi_week_running_totals(all_weeks_data)

            # Calculate weekly statistics for all weeks (for Weekly Totals table)
            weekly_stats = self._calculate_all_weeks_statistics(all_weeks_data)

            # Calculate division strength across all weeks
            division_strength = self._calculate_division_strength(all_weeks_data)

            # Create enhanced structure
            enhanced_data = {
                "current_week": current_data,
                "season_context": {
                    "team_standings": team_standings,
                    "standings_progression": [
                        {
                            "week": week,
                            "standings": team_standings,
                            "timestamp": datetime.now().isoformat()
                        }
                    ],
                    "matchup_history": matchup_history,
                    "award_summaries": award_summaries,
                    "performance_trends": {
                        "team_metrics": team_performance,
                        "weekly_averages": {
                            "league_average_score": team_performance.get("league_average", 0),
                            "total_points_scored": team_performance.get("total_points", 0)
                        }
                    },
                    "running_totals": running_totals,
                    "weekly_statistics": weekly_stats,
                    "division_strength": division_strength
                },
                "league_history": league_history,
                "metadata": {
                    "aggregation_timestamp": datetime.now().isoformat(),
                    "dynamodb_record_id": dynamodb_record_id,
                    "historical_weeks_included": len(historical_data),
                    "season": season,
                    "league_id": league_id,
                    "current_week": week,
                    "total_weeks_processed": len(all_weeks_data),
                    "data_source": "multi_week" if historical_data else "current_week_only",
                    "is_latest_week": is_latest_week,
                    "league_history_available": league_history is not None
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
                    "matchup_history": {"weekly_results": {}},
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

    def _create_condensed_data(self, enhanced_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create condensed data structure for systems with limited context.

        Args:
            enhanced_data: Full enhanced data structure

        Returns:
            Condensed data structure with essential information
        """
        try:
            current_week = enhanced_data.get("current_week", {})
            season_context = enhanced_data.get("season_context", {})

            # Extract basic league information
            league_name = current_week.get("league_name", "Unknown League")
            week = current_week.get("week", 1)

            # Extract team standings (already sorted by rank)
            team_standings_raw = season_context.get("team_standings", {})
            team_standings = []

            # Convert team standings dict to sorted array
            for team_id, team_data in team_standings_raw.items():
                team_info = {
                    "name": team_data.get("name", "Unknown Team"),
                    "division": team_data.get("division", "Unknown"),
                    "wins": team_data.get("wins", 0),
                    "losses": team_data.get("losses", 0),
                    "ties": team_data.get("ties", 0),
                    "points_for": round(team_data.get("points_for", 0)),
                    "points_against": round(team_data.get("points_against", 0)),
                    "overall_rank": team_data.get("overall_rank", 999),
                    "division_rank": team_data.get("division_rank", 999)
                }
                team_standings.append(team_info)

            # Sort by overall rank (lowest number = best rank)
            team_standings.sort(key=lambda x: x["overall_rank"])

            # Extract current week matchups
            matchups = []
            for matchup in current_week.get("matchups", []):
                # Extract home team data
                home_team = matchup.get("home_team", {})
                home_team_data = {
                    "name": home_team.get("name", "Unknown"),
                    "points_scored": matchup.get("home_score", 0),
                    "projected_score": matchup.get("home_projected_score", 0),
                    "optimal_score": matchup.get("home_optimal_score", 0),
                    "players": []
                }

                # Extract away team data
                away_team = matchup.get("away_team", {})
                away_team_data = {
                    "name": away_team.get("name", "Unknown"),
                    "points_scored": matchup.get("away_score", 0),
                    "projected_score": matchup.get("away_projected_score", 0),
                    "optimal_score": matchup.get("away_optimal_score", 0),
                    "players": []
                }

                # Extract player data
                for player in matchup.get("players", []):
                    player_data = {
                        "name": player.get("name", "Unknown"),
                        "position": player.get("position", "UNKNOWN"),
                        "roster_slot": player.get("roster_slot", "UNKNOWN"),
                        "projected_score": player.get("projected_score", 0),
                        "actual_score": player.get("actual_score", 0)
                    }

                    # Add to appropriate team
                    if player.get("team") == home_team.get("name"):
                        home_team_data["players"].append(player_data)
                    elif player.get("team") == away_team.get("name"):
                        away_team_data["players"].append(player_data)

                # Determine winning teams for each category
                home_score = matchup.get("home_score", 0)
                away_score = matchup.get("away_score", 0)
                home_projected = matchup.get("home_projected_score", 0)
                away_projected = matchup.get("away_projected_score", 0)
                home_optimal = matchup.get("home_optimal_score", 0)
                away_optimal = matchup.get("away_optimal_score", 0)

                # Winning team (actual results)
                if home_score > away_score:
                    winning_team = home_team_data["name"]
                elif away_score > home_score:
                    winning_team = away_team_data["name"]
                else:
                    winning_team = None  # Tie game

                # Projected winning team
                if home_projected > away_projected:
                    projected_winning_team = home_team_data["name"]
                elif away_projected > home_projected:
                    projected_winning_team = away_team_data["name"]
                else:
                    projected_winning_team = None  # Tie projection

                # Optimal winning team
                if home_optimal > away_optimal:
                    optimal_winning_team = home_team_data["name"]
                elif away_optimal > home_optimal:
                    optimal_winning_team = away_team_data["name"]
                else:
                    optimal_winning_team = None  # Tie in optimal scores

                matchups.append({
                    "home_team": home_team_data,
                    "away_team": away_team_data,
                    "winning_team": winning_team,
                    "projected_winning_team": projected_winning_team,
                    "optimal_winning_team": optimal_winning_team
                })

            # Extract awards data
            awards_raw = current_week.get("awards", {})
            awards = {}

            # Individual player awards
            for award_type in ["mvp", "mwp", "mup", "mdp"]:
                if award_type in awards_raw and awards_raw[award_type]:
                    awards[award_type] = awards_raw[award_type]
                else:
                    awards[award_type] = None

            # Team awards
            for award_type in ["hsl", "lsw", "ssl", "ifm", "accidental_genius"]:
                if award_type in awards_raw and awards_raw[award_type]:
                    awards[award_type] = awards_raw[award_type]
                else:
                    awards[award_type] = None

            # Collapse awards (may be lists or single items)
            for award_type in ["mccollapse", "clapper_collapse"]:
                if award_type in awards_raw and awards_raw[award_type]:
                    awards[award_type] = awards_raw[award_type]
                else:
                    awards[award_type] = None

            # Create condensed structure
            condensed_data = {
                "league_name": league_name,
                "week": week,
                "team_standings": team_standings,
                "matchups": matchups,
                "awards": awards
            }

            return condensed_data

        except Exception as e:
            self.logger.error(f"Failed to create condensed data structure: {e}")
            # Return minimal structure on error
            return {
                "league_name": "Unknown League",
                "week": 1,
                "team_standings": [],
                "matchups": [],
                "awards": {},
                "error": str(e)
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

    def _calculate_team_standings(self, all_weeks_data: List[Dict[str, Any]], current_week: int) -> Dict[str, Any]:
        """
        Calculate cumulative team standings from matchup results across all weeks.

        Args:
            all_weeks_data: List of weekly data (historical + current)
            current_week: Current week number

        Returns:
            Dictionary with team standings data
        """
        try:
            self.logger.info(f"Calculating team standings for week {current_week}")

            # Initialize team standings
            team_standings = {}

            # Get team info from the current week (divisions data)
            current_data = all_weeks_data[-1] if all_weeks_data else {}
            divisions = current_data.get('divisions', [])

            # Initialize team records
            for division in divisions:
                for team in division.get('teams', []):
                    team_id = team.get('id')
                    if team_id:
                        team_standings[team_id] = {
                            'id': team_id,
                            'name': team.get('name', ''),
                            'division': division.get('name', 'Unknown'),
                            'owner': team.get('owner', ''),
                            'abbreviation': team.get('abbreviation', ''),
                            'logo': team.get('logo', ''),
                            'wins': 0,
                            'losses': 0,
                            'ties': 0,
                            'points_for': 0.0,
                            'points_against': 0.0,
                            'overall_rank': 0,
                            'division_rank': 0
                        }

            # Calculate cumulative records from all weeks
            for i, week_data in enumerate(all_weeks_data):
                week_num = week_data.get('week', i+1)
                matchups = week_data.get('matchups', [])

                for matchup in matchups:
                    home_team = matchup.get('home_team', {})
                    away_team = matchup.get('away_team', {})
                    home_score = float(matchup.get('home_score', 0))
                    away_score = float(matchup.get('away_score', 0))

                    home_id = home_team.get('id')
                    away_id = away_team.get('id')

                    # Update points totals
                    if home_id in team_standings:
                        team_standings[home_id]['points_for'] += home_score
                        team_standings[home_id]['points_against'] += away_score

                    if away_id in team_standings:
                        team_standings[away_id]['points_for'] += away_score
                        team_standings[away_id]['points_against'] += home_score

                    # Update win/loss/tie records
                    if home_score > away_score:
                        # Home team wins
                        if home_id in team_standings:
                            team_standings[home_id]['wins'] += 1
                        if away_id in team_standings:
                            team_standings[away_id]['losses'] += 1
                    elif away_score > home_score:
                        # Away team wins
                        if away_id in team_standings:
                            team_standings[away_id]['wins'] += 1
                        if home_id in team_standings:
                            team_standings[home_id]['losses'] += 1
                    else:
                        # Tie game
                        if home_id in team_standings:
                            team_standings[home_id]['ties'] += 1
                        if away_id in team_standings:
                            team_standings[away_id]['ties'] += 1

            # Calculate rankings
            teams_list = list(team_standings.values())
            ranked_teams = self._rank_teams_by_performance(teams_list)

            # Update rankings in standings dict
            for rank, team in enumerate(ranked_teams, 1):
                team_id = team['id']
                team_standings[team_id]['overall_rank'] = rank

            # Calculate division rankings
            self._calculate_division_ranks(team_standings)

            self.logger.info(f"Successfully calculated standings for {len(team_standings)} teams")
            return team_standings

        except Exception as e:
            self.logger.error(f"Failed to calculate team standings: {e}")
            return {}

    def _rank_teams_by_performance(self, teams: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rank teams based on performance criteria:
        1. Wins (most)
        2. Losses (fewest)
        3. Points for (most)
        4. Points against (fewest)

        Args:
            teams: List of team standing dictionaries

        Returns:
            List of teams sorted by ranking criteria
        """
        return sorted(teams, key=lambda team: (
            -team['wins'],              # More wins = better (negative for desc)
            team['losses'],             # Fewer losses = better
            -team['points_for'],        # More points for = better
            team['points_against']      # Fewer points against = better
        ))

    def _calculate_division_ranks(self, team_standings: Dict[str, Any]) -> None:
        """
        Calculate division rankings for teams.

        Args:
            team_standings: Dictionary of team standings (modified in place)
        """
        # Group teams by division
        divisions = {}
        for team in team_standings.values():
            division = team['division']
            if division not in divisions:
                divisions[division] = []
            divisions[division].append(team)

        # Rank teams within each division
        for division_teams in divisions.values():
            ranked_division_teams = self._rank_teams_by_performance(division_teams)

            for rank, team in enumerate(ranked_division_teams, 1):
                team_id = team['id']
                team_standings[team_id]['division_rank'] = rank

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

    def _calculate_matchup_history(self, all_weeks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comprehensive matchup history with weekly results"""
        try:
            weekly_results = {}

            for week_data in all_weeks_data:
                week_num = int(week_data.get('week', 0))
                if week_num <= 0:
                    continue

                weekly_results[week_num] = []

                for matchup in week_data.get('matchups', []):
                    home_team = matchup.get('home_team', {})
                    away_team = matchup.get('away_team', {})

                    # Extract all required data
                    home_score = float(matchup.get('home_score', 0))
                    away_score = float(matchup.get('away_score', 0))
                    home_projected = float(matchup.get('home_projected_score', 0))
                    away_projected = float(matchup.get('away_projected_score', 0))
                    home_optimal = float(matchup.get('home_optimal_score', 0))
                    away_optimal = float(matchup.get('away_optimal_score', 0))

                    # Determine winner and loser (ensure consistent string IDs)
                    winner_id = None
                    loser_id = None
                    if home_score > away_score:
                        winner_id = str(int(float(home_team.get('id', 0)))) if home_team.get('id') is not None else None
                        loser_id = str(int(float(away_team.get('id', 0)))) if away_team.get('id') is not None else None
                    elif away_score > home_score:
                        winner_id = str(int(float(away_team.get('id', 0)))) if away_team.get('id') is not None else None
                        loser_id = str(int(float(home_team.get('id', 0)))) if home_team.get('id') is not None else None
                    # If scores are equal, both winner_id and loser_id remain None (tie)

                    matchup_result = {
                        "home_team": {
                            "id": str(int(float(home_team.get('id', 0)))) if home_team.get('id') is not None else None,
                            "name": home_team.get('name', ''),
                            "abbreviation": home_team.get('abbreviation', '')
                        },
                        "away_team": {
                            "id": str(int(float(away_team.get('id', 0)))) if away_team.get('id') is not None else None,
                            "name": away_team.get('name', ''),
                            "abbreviation": away_team.get('abbreviation', '')
                        },
                        "home_score": home_score,
                        "away_score": away_score,
                        "home_projected_score": home_projected,
                        "away_projected_score": away_projected,
                        "home_optimal_score": home_optimal,
                        "away_optimal_score": away_optimal,
                        "winner_id": winner_id,
                        "loser_id": loser_id
                    }

                    weekly_results[week_num].append(matchup_result)

            return {"weekly_results": weekly_results}

        except Exception as e:
            self.logger.warning(f"Failed to calculate matchup history: {e}")
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

    def _calculate_division_strength(self, all_weeks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate division strength based on inter-division performance.

        Calculates for each division:
        - Wins against other divisions (excluding ties and intra-division games)
        - Losses against other divisions (excluding ties and intra-division games)
        - Points for (total points scored by all teams in division, all games)
        - Points against (total points scored by teams playing against this division)

        Rankings based on: 1) Wins (desc), 2) Losses (asc), 3) Points For (desc), 4) Points Against (desc)
        """
        try:
            # Get all divisions from current week data
            divisions = {}
            team_divisions = {}

            # Extract division information from the most recent week
            if all_weeks_data:
                current_data = all_weeks_data[-1]  # Use most recent week for division structure
                for division in current_data.get('divisions', []):
                    division_name = division.get('name', '')
                    divisions[division_name] = {
                        'name': division_name,
                        'wins': 0,
                        'losses': 0,
                        'points_for': 0,
                        'points_against': 0,
                        'teams': []
                    }

                    # Map teams to their divisions
                    for team in division.get('teams', []):
                        team_id = team.get('id')
                        team_name = team.get('name', '')
                        divisions[division_name]['teams'].append(team_name)
                        team_divisions[team_id] = division_name
                        team_divisions[team_name] = division_name  # Also map by name for flexibility

            # Process all matchups across all weeks
            for week_data in all_weeks_data:
                for matchup in week_data.get('matchups', []):
                    home_team = matchup.get('home_team', {})
                    away_team = matchup.get('away_team', {})
                    home_score = float(matchup.get('home_score', 0))
                    away_score = float(matchup.get('away_score', 0))

                    # Get team divisions
                    home_team_id = home_team.get('id')
                    away_team_id = away_team.get('id')
                    home_team_name = home_team.get('name', '')
                    away_team_name = away_team.get('name', '')

                    # Try to find division by ID first, then by name
                    home_division = team_divisions.get(home_team_id) or team_divisions.get(home_team_name)
                    away_division = team_divisions.get(away_team_id) or team_divisions.get(away_team_name)

                    if not home_division or not away_division:
                        continue

                    # Add points for each division (from all games, including intra-division)
                    if home_division in divisions:
                        divisions[home_division]['points_for'] += home_score
                    if away_division in divisions:
                        divisions[away_division]['points_for'] += away_score

                    # Add points against (points scored by opponents against this division)
                    if home_division in divisions:
                        divisions[home_division]['points_against'] += away_score
                    if away_division in divisions:
                        divisions[away_division]['points_against'] += home_score

                    # Only count wins/losses for inter-division games (exclude ties)
                    if home_division != away_division and home_score != away_score:
                        if home_score > away_score:
                            # Home team wins
                            if home_division in divisions:
                                divisions[home_division]['wins'] += 1
                            if away_division in divisions:
                                divisions[away_division]['losses'] += 1
                        else:
                            # Away team wins
                            if away_division in divisions:
                                divisions[away_division]['wins'] += 1
                            if home_division in divisions:
                                divisions[home_division]['losses'] += 1

            # Convert to list and rank divisions
            division_list = list(divisions.values())

            # Sort by ranking criteria: wins (desc), losses (asc), points_for (desc), points_against (desc)
            division_list.sort(key=lambda d: (-d['wins'], d['losses'], -d['points_for'], -d['points_against']))

            # Assign ranks
            for i, division in enumerate(division_list):
                division['rank'] = i + 1

            return {
                'divisions': division_list,
                'ranking_criteria': 'Wins (desc), Losses (asc), Points For (desc), Points Against (desc)'
            }

        except Exception as e:
            self.logger.warning(f"Failed to calculate division strength: {e}")
            return {
                'divisions': [],
                'error': str(e)
            }