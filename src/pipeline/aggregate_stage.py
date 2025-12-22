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

    def _validate_historical_data(self, current_week: int, historical_data: List[Dict[str, Any]],
                                   regular_season_weeks: int) -> None:
        """
        Validate that all required historical weeks exist in DynamoDB.

        Args:
            current_week: The week being processed
            historical_data: List of historical week data from DynamoDB
            regular_season_weeks: Number of regular season weeks (from league settings)

        Raises:
            ValueError: If any weeks are missing from historical data
        """
        if current_week <= 1:
            return  # Week 1 has no historical data requirement

        # Only validate up to regular season weeks (playoff weeks don't require prior playoff data)
        max_week_to_validate = min(current_week - 1, regular_season_weeks)
        expected_weeks = set(range(1, max_week_to_validate + 1))
        found_weeks = {week_data.get('week') for week_data in historical_data}
        missing_weeks = expected_weeks - found_weeks

        if missing_weeks:
            raise ValueError(
                f"Missing historical data for weeks: {sorted(missing_weeks)}. "
                f"Cannot calculate accurate standings without complete historical data."
            )

    def _validate_team_matchups(self, week_data: Dict[str, Any], team_ids: set,
                                 week_num: int) -> None:
        """
        Validate that all teams have matchups in a regular season week.

        Args:
            week_data: Data for a single week
            team_ids: Set of all team IDs in the league
            week_num: The week number being validated

        Raises:
            ValueError: If any team is missing a matchup
        """
        # Collect all team IDs that appear in matchups
        teams_with_matchups = set()
        for matchup in week_data.get('matchups', []):
            home_id = matchup.get('home_team', {}).get('id')
            away_id = matchup.get('away_team', {}).get('id')
            if home_id:
                teams_with_matchups.add(home_id)
            if away_id:
                teams_with_matchups.add(away_id)

        missing_teams = team_ids - teams_with_matchups
        if missing_teams:
            raise ValueError(
                f"Teams with IDs {sorted(missing_teams)} have no matchup in week {week_num}. "
                f"All teams must have matchups during regular season weeks."
            )

    def _get_league_settings(self, current_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Get league settings including regular season weeks and playoff team count.

        Args:
            current_data: Current week data

        Returns:
            Dictionary with regular_season_weeks and playoff_team_count
        """
        try:
            # Try to get from ESPN client
            try:
                from ..utils.espn_client import ESPNClient
            except ImportError:
                from src.utils.espn_client import ESPNClient

            league_id = current_data.get('league_id')
            if league_id:
                client = ESPNClient(league_id=league_id)
                league_info = client.get_league_info()
                return {
                    'regular_season_weeks': league_info.get('regular_season_count', 14),
                    'playoff_team_count': league_info.get('playoff_team_count', 6)
                }
        except Exception as e:
            self.logger.warning(f"Could not get league settings from ESPN: {e}")

        # Fallback defaults
        return {
            'regular_season_weeks': 14,
            'playoff_team_count': 6
        }

    def _create_playoff_context(self, current_data: Dict[str, Any], league_settings: Dict[str, int]) -> Dict[str, Any]:
        """
        Create playoff context including full bracket structure.

        Args:
            current_data: Current week data with matchups
            league_settings: Dictionary with regular_season_weeks and playoff_team_count

        Returns:
            Playoff context dictionary with full bracket structure
        """
        week = current_data.get('week', 1)
        regular_season_weeks = league_settings.get('regular_season_weeks', 14)
        playoff_team_count = league_settings.get('playoff_team_count', 6)

        is_playoff_week = week > regular_season_weeks
        playoff_week_number = max(0, week - regular_season_weeks) if is_playoff_week else 0

        # Initialize bracket lists for current week
        championship_bracket = []
        consolation_bracket = []

        # Build full tournament bracket structure
        bracket_structure = self._build_bracket_structure(current_data, playoff_team_count)

        if is_playoff_week:
            matchups = current_data.get('matchups', [])

            for matchup in matchups:
                home_team = matchup.get('home_team', {})
                away_team = matchup.get('away_team', {})

                home_standing = home_team.get('standing', 999)
                away_standing = away_team.get('standing', 999)

                is_championship_game = (
                    home_standing <= playoff_team_count and
                    away_standing <= playoff_team_count
                )

                matchup_info = {
                    'home_team': {
                        'id': home_team.get('id'),
                        'name': home_team.get('name', ''),
                        'seed': home_standing,
                        'logo': home_team.get('logo', '')
                    },
                    'away_team': {
                        'id': away_team.get('id'),
                        'name': away_team.get('name', ''),
                        'seed': away_standing,
                        'logo': away_team.get('logo', '')
                    },
                    'home_score': matchup.get('home_score', 0),
                    'away_score': matchup.get('away_score', 0),
                    'is_complete': matchup.get('is_complete', False),
                    'winner_id': matchup.get('winner_id')
                }

                if is_championship_game:
                    championship_bracket.append(matchup_info)
                else:
                    consolation_bracket.append(matchup_info)

        return {
            'is_playoff_week': is_playoff_week,
            'playoff_week_number': playoff_week_number,
            'regular_season_weeks': regular_season_weeks,
            'playoff_team_count': playoff_team_count,
            'championship_bracket': championship_bracket,
            'consolation_bracket': consolation_bracket,
            'bracket_structure': bracket_structure
        }

    def _build_bracket_structure(self, current_data: Dict[str, Any], playoff_team_count: int) -> Dict[str, Any]:
        """
        Build full March Madness-style bracket structure from team standings.

        For a 6-team playoff:
        - Seeds 1 and 2 get byes
        - Quarterfinals: #3 vs #6, #4 vs #5
        - Semifinals: #1 vs QF winner (lower seed), #2 vs QF winner (higher seed)
        - Finals: SF winners

        Args:
            current_data: Current week data
            playoff_team_count: Number of playoff teams (typically 6)

        Returns:
            Bracket structure with all rounds
        """
        # Get playoff teams from divisions data, sorted by standing
        playoff_teams = []
        divisions = current_data.get('divisions', [])

        for division in divisions:
            for team in division.get('teams', []):
                standing = team.get('standing', 999)
                if standing <= playoff_team_count:
                    playoff_teams.append({
                        'id': team.get('id'),
                        'name': team.get('name', ''),
                        'seed': standing,
                        'logo': team.get('logo', ''),
                        'wins': team.get('wins', 0),
                        'losses': team.get('losses', 0)
                    })

        # Sort by seed
        playoff_teams.sort(key=lambda t: t['seed'])

        # Build bracket structure for 6-team playoff
        # Quarterfinals (Week 15): #3 vs #6, #4 vs #5
        # Semifinals (Week 16): #1 vs lowest remaining, #2 vs highest remaining
        # Finals (Week 17): Championship

        # Find teams by seed
        teams_by_seed = {t['seed']: t for t in playoff_teams}

        # Get current matchup results to populate bracket
        matchups = current_data.get('matchups', [])
        matchup_results = {}
        for m in matchups:
            home = m.get('home_team', {})
            away = m.get('away_team', {})
            key = tuple(sorted([home.get('standing', 0), away.get('standing', 0)]))
            matchup_results[key] = {
                'home_team': home,
                'away_team': away,
                'home_score': m.get('home_score', 0),
                'away_score': m.get('away_score', 0),
                'is_complete': m.get('is_complete', False),
                'winner_id': m.get('winner_id')
            }

        # Build quarterfinals
        qf1 = self._build_matchup_slot(teams_by_seed.get(3), teams_by_seed.get(6), matchup_results.get((3, 6)))
        qf2 = self._build_matchup_slot(teams_by_seed.get(4), teams_by_seed.get(5), matchup_results.get((4, 5)))

        # Build semifinals (with byes)
        # SF1: #2 seed vs winner of QF1 (#3 vs #6)
        sf1 = self._build_matchup_slot(
            teams_by_seed.get(2),
            qf1.get('winner') if qf1.get('is_complete') else {'name': 'Winner of #3/#6', 'seed': None},
            matchup_results.get((2, 3)) or matchup_results.get((2, 6))
        )
        # SF2: #1 seed vs winner of QF2 (#4 vs #5)
        sf2 = self._build_matchup_slot(
            teams_by_seed.get(1),
            qf2.get('winner') if qf2.get('is_complete') else {'name': 'Winner of #4/#5', 'seed': None},
            matchup_results.get((1, 4)) or matchup_results.get((1, 5))
        )

        # Build finals
        finals = self._build_matchup_slot(
            sf1.get('winner') if sf1.get('is_complete') else {'name': 'Winner SF1', 'seed': None},
            sf2.get('winner') if sf2.get('is_complete') else {'name': 'Winner SF2', 'seed': None},
            None  # Finals result
        )

        return {
            'playoff_teams': playoff_teams,
            'rounds': {
                'quarterfinals': [qf1, qf2],
                'semifinals': [sf1, sf2],
                'finals': [finals]
            },
            'bye_teams': [teams_by_seed.get(1), teams_by_seed.get(2)]
        }

    def _build_matchup_slot(self, team1: Optional[Dict], team2: Optional[Dict],
                            result: Optional[Dict]) -> Dict[str, Any]:
        """Build a single matchup slot for the bracket."""
        slot = {
            'team1': team1 or {'name': 'TBD', 'seed': None},
            'team2': team2 or {'name': 'TBD', 'seed': None},
            'is_complete': False,
            'team1_score': None,
            'team2_score': None,
            'winner': None
        }

        if result and result.get('is_complete'):
            slot['is_complete'] = True
            # Determine which team is team1 and team2 based on seeds
            home_seed = result.get('home_team', {}).get('standing', 0)
            away_seed = result.get('away_team', {}).get('standing', 0)

            if team1 and team1.get('seed') == home_seed:
                slot['team1_score'] = result.get('home_score')
                slot['team2_score'] = result.get('away_score')
            else:
                slot['team1_score'] = result.get('away_score')
                slot['team2_score'] = result.get('home_score')

            # Determine winner
            if result.get('home_score', 0) > result.get('away_score', 0):
                winner_seed = home_seed
            else:
                winner_seed = away_seed

            slot['winner'] = team1 if team1 and team1.get('seed') == winner_seed else team2

        return slot

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

            # Get league settings for playoff detection and standings calculation
            league_settings = self._get_league_settings(current_data)
            regular_season_weeks = league_settings.get('regular_season_weeks', 14)

            # Validate historical data completeness (fail fast)
            self._validate_historical_data(week, historical_data, regular_season_weeks)

            # Create playoff context
            playoff_context = self._create_playoff_context(current_data, league_settings)

            # Combine current data with historical data for comprehensive analysis
            all_weeks_data = historical_data + [current_data]

            # Calculate team performance metrics across all weeks
            team_performance = self._calculate_multi_week_team_performance(all_weeks_data)

            # Calculate cumulative team standings from matchup results
            team_standings = self._calculate_team_standings(all_weeks_data, week, regular_season_weeks)

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
                    "division_strength": division_strength,
                    "playoff_context": playoff_context
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
                    "is_playoff_week": playoff_context.get('is_playoff_week', False),
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

    def _calculate_team_standings(self, all_weeks_data: List[Dict[str, Any]], current_week: int,
                                    regular_season_weeks: int = 14) -> Dict[str, Any]:
        """
        Calculate team standings by computing wins/losses/points from matchup results.

        Iterates through all weeks' matchups to build accurate cumulative standings.
        Only processes regular season weeks - playoff weeks don't affect standings.

        Args:
            all_weeks_data: List of weekly data (historical + current)
            current_week: Current week number
            regular_season_weeks: Number of regular season weeks (default 14)

        Returns:
            Dictionary with team standings data
        """
        try:
            self.logger.info(f"Computing team standings from matchups for week {current_week}")

            # Initialize team standings from current week's team data (for names, logos, etc.)
            current_data = all_weeks_data[-1] if all_weeks_data else {}
            team_standings = self._initialize_team_standings(current_data)
            team_ids = set(team_standings.keys())

            # Iterate through regular season weeks only
            for week_data in all_weeks_data:
                week_num = week_data.get('week', 0)
                if week_num > regular_season_weeks:
                    continue  # Skip playoff weeks

                # Validate all teams have matchups in regular season weeks
                self._validate_team_matchups(week_data, team_ids, week_num)

                # Process matchups for standings
                for matchup in week_data.get('matchups', []):
                    self._process_matchup_for_standings(matchup, team_standings)

            # Calculate overall and division rankings
            self._calculate_overall_ranks(team_standings)
            self._calculate_division_ranks(team_standings)

            self.logger.info(f"Successfully computed standings for {len(team_standings)} teams from matchups")
            return team_standings

        except Exception as e:
            self.logger.error(f"Failed to calculate team standings: {e}")
            raise

    def _initialize_team_standings(self, current_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize team standings structure with zero wins/losses/points.

        Uses team metadata from current week data (names, divisions, logos, etc.)
        but starts all standings values at zero for computation.

        Args:
            current_data: Current week data containing divisions and teams

        Returns:
            Dictionary with team standings initialized to zero
        """
        team_standings = {}
        divisions = current_data.get('divisions', [])

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
                        # Initialize standings values to zero - will be computed from matchups
                        'wins': 0,
                        'losses': 0,
                        'ties': 0,
                        'points_for': 0.0,
                        'points_against': 0.0,
                        'overall_rank': 0,
                        'division_rank': 0
                    }

        return team_standings

    def _process_matchup_for_standings(self, matchup: Dict[str, Any], standings: Dict[str, Any]) -> None:
        """
        Process a single matchup and update team standings.

        Updates wins/losses/ties and points for/against based on matchup results.

        Args:
            matchup: Matchup data containing teams and scores
            standings: Team standings dictionary (modified in place)
        """
        home_team = matchup.get('home_team', {})
        away_team = matchup.get('away_team', {})
        home_id = home_team.get('id')
        away_id = away_team.get('id')
        home_score = float(matchup.get('home_score', 0))
        away_score = float(matchup.get('away_score', 0))

        if home_id not in standings or away_id not in standings:
            return  # Skip if team not found

        # Update points
        standings[home_id]['points_for'] += home_score
        standings[home_id]['points_against'] += away_score
        standings[away_id]['points_for'] += away_score
        standings[away_id]['points_against'] += home_score

        # Update wins/losses/ties
        if home_score > away_score:
            standings[home_id]['wins'] += 1
            standings[away_id]['losses'] += 1
        elif away_score > home_score:
            standings[away_id]['wins'] += 1
            standings[home_id]['losses'] += 1
        else:  # Tie game
            standings[home_id]['ties'] += 1
            standings[away_id]['ties'] += 1

    def _calculate_overall_ranks(self, team_standings: Dict[str, Any]) -> None:
        """
        Calculate overall league rankings for all teams.

        Uses the existing ranking algorithm based on:
        1. Wins (most)
        2. Losses (fewest)
        3. Points For (most)
        4. Points Against (fewest)

        Args:
            team_standings: Dictionary of team standings (modified in place)
        """
        teams_list = list(team_standings.values())
        ranked_teams = self._rank_teams_by_performance(teams_list)

        for rank, team in enumerate(ranked_teams, 1):
            team_standings[team['id']]['overall_rank'] = rank

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
        Calculate division rankings for teams based on computed performance.

        Uses the same ranking criteria as overall rankings but within each division.

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

        # Rank teams within each division using performance criteria
        for division_teams in divisions.values():
            # Use the same ranking algorithm as overall rankings
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
        """Calculate award summaries across multiple weeks for all 11 award types."""
        try:
            summaries = {
                "season_totals": {
                    # Player awards
                    "mvp_winners": [],
                    "mwp_winners": [],
                    "mup_winners": [],
                    "mdp_winners": [],
                    # Team awards
                    "hsl_winners": [],
                    "lsw_winners": [],
                    "ssl_winners": [],
                    "ifm_winners": [],
                    "accidental_genius_winners": [],
                    "mccollapse_winners": [],
                    "clapper_collapse_winners": []
                }
            }

            for week_data in all_weeks_data:
                week_num = week_data.get('week', 0)
                awards = week_data.get('awards', {})
                matchups = week_data.get('matchups', [])

                # Build team matchup lookup for this week
                team_matchup_lookup = self._build_team_matchup_lookup(matchups)

                # Track player awards (MVP, MWP, MUP, MDP)
                for award_type in ['mvp', 'mwp', 'mup', 'mdp']:
                    if awards.get(award_type):
                        award = awards[award_type]
                        team_name = award.get('team_name')
                        matchup_info = team_matchup_lookup.get(team_name, {})

                        summaries["season_totals"][f"{award_type}_winners"].append({
                            "week": week_num,
                            "player": award.get('player_name'),
                            "team": team_name,
                            "position": award.get('position', ''),
                            "score": award.get('score'),
                            "team_logo": matchup_info.get('team_logo', ''),
                            "result": matchup_info.get('result', '')
                        })

                # Calculate scoring ranks for this week
                scoring_ranks = self._calculate_week_scoring_ranks(matchups)

                # Track HSL (Highest Scoring Loser)
                if awards.get('hsl'):
                    award = awards['hsl']
                    team_name = award.get('team_name')
                    matchup_info = team_matchup_lookup.get(team_name, {})
                    summaries["season_totals"]["hsl_winners"].append({
                        "week": week_num,
                        "team": team_name,
                        "team_logo": matchup_info.get('team_logo', ''),
                        "score": award.get('score'),
                        "opponent_score": matchup_info.get('opponent_score', 0),
                        "opponent_name": matchup_info.get('opponent_name', ''),
                        "place": scoring_ranks.get(team_name, 0)
                    })

                # Track LSW (Lowest Scoring Winner)
                if awards.get('lsw'):
                    award = awards['lsw']
                    team_name = award.get('team_name')
                    matchup_info = team_matchup_lookup.get(team_name, {})
                    summaries["season_totals"]["lsw_winners"].append({
                        "week": week_num,
                        "team": team_name,
                        "team_logo": matchup_info.get('team_logo', ''),
                        "score": award.get('score'),
                        "opponent_score": matchup_info.get('opponent_score', 0),
                        "opponent_name": matchup_info.get('opponent_name', ''),
                        "place": scoring_ranks.get(team_name, 0)
                    })

                # Track SSL (Smartest Starting Lineup)
                if awards.get('ssl'):
                    award = awards['ssl']
                    team_name = award.get('team_name')
                    matchup_info = team_matchup_lookup.get(team_name, {})
                    summaries["season_totals"]["ssl_winners"].append({
                        "week": week_num,
                        "team": team_name,
                        "team_logo": matchup_info.get('team_logo', ''),
                        "actual": award.get('actual_score', 0),
                        "optimal": award.get('optimal_score', 0),
                        "efficiency": award.get('efficiency_percentage', 0),
                        "result": matchup_info.get('result', '')
                    })

                # Track IFM (I Fucked Myself)
                if awards.get('ifm'):
                    award = awards['ifm']
                    team_name = award.get('team_name')
                    matchup_info = team_matchup_lookup.get(team_name, {})
                    summaries["season_totals"]["ifm_winners"].append({
                        "week": week_num,
                        "team": team_name,
                        "team_logo": matchup_info.get('team_logo', ''),
                        "actual": award.get('actual_score', 0),
                        "optimal": award.get('optimal_score', 0),
                        "efficiency": award.get('efficiency_percentage', 0),
                        "result": matchup_info.get('result', '')
                    })

                # Track Accidental Genius
                if awards.get('accidental_genius'):
                    award = awards['accidental_genius']
                    team_name = award.get('team_name')
                    matchup_info = team_matchup_lookup.get(team_name, {})
                    summaries["season_totals"]["accidental_genius_winners"].append({
                        "week": week_num,
                        "team": team_name,
                        "team_logo": matchup_info.get('team_logo', ''),
                        "actual": award.get('actual_score', 0),
                        "optimal": award.get('optimal_score', 0),
                        "efficiency": award.get('efficiency_percentage', 0),
                        "result": matchup_info.get('result', '')
                    })

                # Track McCollapse
                if awards.get('mccollapse'):
                    award = awards['mccollapse']
                    team_name = award.get('team_name')
                    matchup_info = team_matchup_lookup.get(team_name, {})
                    summaries["season_totals"]["mccollapse_winners"].append({
                        "week": week_num,
                        "team": team_name,
                        "team_logo": matchup_info.get('team_logo', ''),
                        "actual": award.get('actual_score', 0),
                        "optimal": award.get('optimal_score', 0),
                        "opponent_score": award.get('opponent_score', 0),
                        "points_difference": award.get('points_difference', 0),
                        "result": "L"  # McCollapse is always a loss
                    })

                # Track Clapper Collapse
                if awards.get('clapper_collapse'):
                    award = awards['clapper_collapse']
                    team_name = award.get('team_name')
                    matchup_info = team_matchup_lookup.get(team_name, {})
                    summaries["season_totals"]["clapper_collapse_winners"].append({
                        "week": week_num,
                        "team": team_name,
                        "team_logo": matchup_info.get('team_logo', ''),
                        "projected": award.get('projected_score', 0),
                        "actual": award.get('actual_score', 0),
                        "opponent_projected": award.get('opponent_projected_score', 0),
                        "opponent_actual": award.get('opponent_actual_score', 0),
                        "result": "L"  # Clapper Collapse is always a loss
                    })

            return summaries

        except Exception as e:
            self.logger.warning(f"Failed to calculate multi-week award summaries: {e}")
            return {"error": str(e)}

    def _build_team_matchup_lookup(self, matchups: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Build a lookup dictionary mapping team names to their matchup info for a week."""
        lookup = {}
        for matchup in matchups:
            home_team = matchup.get('home_team', {})
            away_team = matchup.get('away_team', {})
            home_name = home_team.get('name', '')
            away_name = away_team.get('name', '')
            home_score = matchup.get('home_score', 0)
            away_score = matchup.get('away_score', 0)
            winner_id = matchup.get('winner_id')

            # Determine results
            home_result = 'W' if winner_id == home_team.get('id') else ('L' if winner_id == away_team.get('id') else 'T')
            away_result = 'W' if winner_id == away_team.get('id') else ('L' if winner_id == home_team.get('id') else 'T')

            lookup[home_name] = {
                'opponent_name': away_name,
                'opponent_score': away_score,
                'team_score': home_score,
                'team_logo': home_team.get('logo', ''),
                'result': home_result
            }
            lookup[away_name] = {
                'opponent_name': home_name,
                'opponent_score': home_score,
                'team_score': away_score,
                'team_logo': away_team.get('logo', ''),
                'result': away_result
            }
        return lookup

    def _calculate_week_scoring_ranks(self, matchups: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate scoring ranks (1st, 2nd, etc.) for all teams in a week's matchups."""
        scores = []
        for matchup in matchups:
            home_team = matchup.get('home_team', {})
            away_team = matchup.get('away_team', {})
            home_name = home_team.get('name', '')
            away_name = away_team.get('name', '')
            home_score = matchup.get('home_score', 0) or 0
            away_score = matchup.get('away_score', 0) or 0

            if home_name:
                scores.append((home_name, home_score))
            if away_name:
                scores.append((away_name, away_score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        # Create rank lookup (1-based)
        return {name: rank + 1 for rank, (name, _) in enumerate(scores)}

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