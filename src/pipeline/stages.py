"""
Pipeline Stages

Defines all pipeline stages with their execution logic, input/output handling,
and error management.
"""

import logging
import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

try:
    from ..fantasy_extractor import FantasyFootballExtractor
    from ..utils.config import get_config
    from ..utils.date_utils import get_nfl_week_calculator
except ImportError:
    from fantasy_extractor import FantasyFootballExtractor
    from utils.config import get_config
    from utils.date_utils import get_nfl_week_calculator


class PipelineStage(ABC):
    """
    Abstract base class for all pipeline stages.

    Each stage should implement the execute method to perform its specific
    data processing tasks and return output path and metadata.
    """

    def __init__(self, league_id: int, dry_run: bool = False):
        """
        Initialize the pipeline stage.

        Args:
            league_id: ESPN fantasy league ID
            dry_run: If True, simulate execution without making changes
        """
        self.league_id = league_id
        self.dry_run = dry_run
        self.config = get_config()
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def execute(self, **kwargs) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Execute the stage logic.

        Args:
            **kwargs: Stage-specific arguments

        Returns:
            Tuple of (output_path, metadata)
        """
        pass

    def _ensure_output_directory(self, directory: str) -> Path:
        """Ensure output directory exists"""
        path = Path(directory)
        if not self.dry_run:
            path.mkdir(parents=True, exist_ok=True)
        return path


class ExtractStage(PipelineStage):
    """
    Stage 1: ESPN Data Extract

    Extracts raw fantasy football data from ESPN API using existing
    FantasyFootballExtractor functionality.
    """

    def __init__(self, league_id: int, year: Optional[int] = None,
                 espn_s2: Optional[str] = None, swid: Optional[str] = None,
                 dry_run: bool = False):
        super().__init__(league_id, dry_run)
        self.year = year or datetime.now().year
        self.espn_s2 = espn_s2
        self.swid = swid

    def execute(self, week: Optional[int] = None,
                output_dir: Optional[str] = None) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Extract ESPN fantasy data for the specified week.

        Args:
            week: NFL week to extract (defaults to current week)
            output_dir: Output directory (defaults to config)

        Returns:
            Tuple of (output_file_path, metadata)
        """
        self.logger.info(f"Starting ESPN data extraction for league {self.league_id}")

        # Determine week and output directory
        if week is None:
            calculator = get_nfl_week_calculator()
            week = calculator.get_previous_complete_week()

        if output_dir is None:
            output_dir = 'output/raw'

        # Ensure output directory exists
        output_path = self._ensure_output_directory(output_dir)

        if self.dry_run:
            self.logger.info(f"DRY RUN: Would extract week {week} data to {output_path}")
            return None, {"week": week, "dry_run": True}

        try:
            # Use existing FantasyFootballExtractor
            extractor = FantasyFootballExtractor(
                league_id=self.league_id,
                year=self.year,
                espn_s2=self.espn_s2,
                swid=self.swid
            )

            # Generate the report
            report = extractor.extract_weekly_report(week=week)

            # Save raw JSON output
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_path / f"raw_week_{week}_{timestamp}.json"

            with open(output_file, 'w') as f:
                json.dump(report.model_dump(), f, indent=2, default=str)

            self.logger.info(f"Successfully extracted week {week} data to {output_file}")

            metadata = {
                "week": week,
                "year": self.year,
                "league_id": self.league_id,
                "timestamp": timestamp,
                "report_id": f"{self.league_id}_{week}_{timestamp}"
            }

            return str(output_file), metadata

        except Exception as e:
            self.logger.error(f"Failed to extract ESPN data: {e}")
            raise


class UploadStage(PipelineStage):
    """
    Stage 2: DynamoDB Upload

    Uploads structured fantasy data to DynamoDB with schema versioning.
    Creates multiple records: main weekly report + individual team records for GSI support.
    """

    def execute(self, input_file: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Upload JSON data to DynamoDB.

        Args:
            input_file: Path to JSON file from extract stage

        Returns:
            Tuple of (None, metadata with record_id)
        """
        self.logger.info(f"Starting DynamoDB upload for file: {input_file}")

        if self.dry_run:
            self.logger.info(f"DRY RUN: Would upload {input_file} to DynamoDB")
            return None, {"dry_run": True, "record_id": "mock_record_123"}

        try:
            # Load and validate JSON data
            with open(input_file, 'r') as f:
                data = json.load(f)

            # Extract key information for DynamoDB record
            week = data.get('week')
            year = data.get('season') or data.get('year')  # Try season first, then year
            league_id = data.get('league_id')
            league_name = data.get('league_name', 'Unknown League')

            if not all([week, year, league_id]):
                raise ValueError(f"Missing required data: week={week}, year={year}, league_id={league_id}")

            # Create DynamoDB connection
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError
            from decimal import Decimal

            def convert_floats_to_decimal(obj):
                """Recursively convert float values to Decimal for DynamoDB compatibility"""
                if isinstance(obj, list):
                    return [convert_floats_to_decimal(item) for item in obj]
                elif isinstance(obj, dict):
                    return {key: convert_floats_to_decimal(value) for key, value in obj.items()}
                elif isinstance(obj, float):
                    return Decimal(str(obj))
                else:
                    return obj

            # Get configuration values
            table_name = self.config.pipeline.aws.dynamodb_table
            region = self.config.pipeline.aws.region
            schema_version = '1.0'
            timestamp = datetime.now().isoformat()

            # Create DynamoDB connection
            dynamodb = boto3.resource('dynamodb', region_name=region)
            table = dynamodb.Table(table_name)

            # Convert floats to Decimal for DynamoDB compatibility
            data_converted = convert_floats_to_decimal(data)

            # Create partition key using CloudFormation schema: season_week
            season_week = f"{year}-{week:02d}"

            # Prepare records to upload using CloudFormation schema
            records_uploaded = []

            # 1. Main weekly report record
            main_record_id = f"{league_id}_{year}_{week}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            main_item = {
                'season_week': season_week,
                'data_type_id': 'weekly_report',
                'league_id': str(league_id),
                'league_name': league_name,
                'week': week,
                'season': year,
                'data': data_converted,
                'timestamp': timestamp,
                'schema_version': schema_version,
                'record_id': main_record_id
            }

            response = table.put_item(Item=main_item)
            records_uploaded.append({
                'type': 'weekly_report',
                'season_week': season_week,
                'data_type_id': 'weekly_report',
                'record_id': main_record_id
            })

            # 2. Individual team records for GSI support
            teams = []
            for division in data.get('divisions', []):
                teams.extend(division.get('teams', []))

            for team in teams:
                team_id = team.get('id')
                team_name = team.get('name')

                if team_id and team_name:
                    team_record_id = f"{league_id}_{year}_{week}_team_{team_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    team_item = {
                        'season_week': season_week,
                        'data_type_id': f'team_{team_id}',
                        'team_id': str(team_id),
                        'team_name': team_name,
                        'league_id': str(league_id),
                        'league_name': league_name,
                        'week': week,
                        'season': year,
                        'team_data': convert_floats_to_decimal(team),
                        'timestamp': timestamp,
                        'schema_version': schema_version,
                        'record_id': team_record_id
                    }

                    table.put_item(Item=team_item)
                    records_uploaded.append({
                        'type': 'team',
                        'season_week': season_week,
                        'data_type_id': f'team_{team_id}',
                        'team_id': team_id,
                        'team_name': team_name,
                        'record_id': team_record_id
                    })

            self.logger.info(f"Successfully uploaded {len(records_uploaded)} records to DynamoDB table '{table_name}'")
            self.logger.info(f"Records: 1 weekly report + {len(records_uploaded)-1} team records")

            metadata = {
                "table_name": table_name,
                "main_record_id": main_record_id,
                "season_week": season_week,
                "schema_version": schema_version,
                "week": week,
                "year": year,
                "league_id": league_id,
                "league_name": league_name,
                "records_uploaded": len(records_uploaded),
                "record_details": records_uploaded,
                "dynamodb_response": response.get('ResponseMetadata', {}).get('HTTPStatusCode')
            }

            return None, metadata

        except Exception as e:
            self.logger.error(f"Failed to upload to DynamoDB: {e}")
            raise


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

            # Calculate enhanced season context from current week data
            enhanced_data = self._create_enhanced_data(current_data, dynamodb_record_id)

            # TODO: Query DynamoDB for historical league data and merge with current data
            # This would require implementing:
            # 1. Query DynamoDB for all weeks in current season
            # 2. Calculate actual season standings progression
            # 3. Compute real historical matchup records
            # 4. Aggregate actual award count summaries from all weeks
            # 5. Generate real performance trends and analytics

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

    def _create_enhanced_data(self, current_data: Dict[str, Any], dynamodb_record_id: Optional[str]) -> Dict[str, Any]:
        """
        Create enhanced data structure with season context from current week data.

        Args:
            current_data: Current week raw data
            dynamodb_record_id: DynamoDB record ID for tracking

        Returns:
            Enhanced data structure with season context
        """
        try:
            # Extract basic info
            week = current_data.get('week', 1)
            season = current_data.get('season', datetime.now().year)
            league_id = current_data.get('league_id')

            # Calculate team performance metrics from current week
            team_performance = self._calculate_team_performance_metrics(current_data)

            # Calculate standings from current week (for progression baseline)
            current_standings = self._extract_current_standings(current_data)

            # Calculate matchup statistics
            matchup_stats = self._calculate_matchup_statistics(current_data)

            # Calculate award summaries from current week
            award_summaries = self._calculate_award_summaries(current_data)

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
                    }
                },
                "metadata": {
                    "aggregation_timestamp": datetime.now().isoformat(),
                    "dynamodb_record_id": dynamodb_record_id,
                    "historical_weeks_included": 0,  # Will be > 0 when historical data is added
                    "season": season,
                    "league_id": league_id,
                    "current_week": week,
                    "data_source": "current_week_only"
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


class GenerateStage(PipelineStage):
    """
    Stage 4: HTML Generation

    Generates HTML website from enhanced JSON using existing templated HTML generator.
    Outputs HTML files ready for deployment.
    """

    def execute(self, input_file: str, output_dir: Optional[str] = None) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Generate HTML website from enhanced JSON.

        Args:
            input_file: Path to enhanced JSON from aggregate stage
            output_dir: Output directory for HTML files (defaults to output/html/)

        Returns:
            Tuple of (html_file_path, metadata)
        """
        self.logger.info(f"Starting HTML generation for: {input_file}")

        # Determine output directory
        if output_dir is None:
            output_dir = 'output/html'

        # Ensure output directory exists
        output_path = self._ensure_output_directory(output_dir)

        if self.dry_run:
            self.logger.info(f"DRY RUN: Would generate HTML to {output_path}")
            return None, {"dry_run": True, "html_file": str(output_path / "index.html")}

        try:
            # Load the enhanced data
            with open(input_file, 'r') as f:
                data = json.load(f)

            # Extract current week data for HTML generation
            # For enhanced data, use current_week; for raw data, use the whole data
            current_week = data.get('current_week', {})
            if not current_week:
                # Raw data without current_week wrapper
                current_week = data
            week = current_week.get('week', 'unknown')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Generate output HTML filename
            output_file = output_path / f"fantasy_report_week_{week}_{timestamp}.html"

            # Use existing TemplatedFantasyHTMLGenerator
            try:
                from ..generators.templated_html_generator import TemplatedFantasyHTMLGenerator
            except ImportError:
                from generators.templated_html_generator import TemplatedFantasyHTMLGenerator

            # Generate HTML using current week data
            generator = TemplatedFantasyHTMLGenerator()
            generator.generate_html(current_week, str(output_file))

            self.logger.info(f"Successfully generated HTML to {output_file}")

            metadata = {
                "week": week,
                "html_file": str(output_file),
                "generation_timestamp": timestamp,
                "input_file": input_file,
                "data_type": "enhanced" if "season_context" in data else "raw"
            }

            return str(output_file), metadata

        except Exception as e:
            self.logger.error(f"Failed to generate HTML: {e}")
            raise


class DeployStage(PipelineStage):
    """
    Stage 5: S3 Deployment

    Uploads HTML website to S3 bucket with CloudFront integration.
    Takes HTML file from GenerateStage and deploys to cloud infrastructure.
    """

    def execute(self, input_file: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Upload HTML website to S3 and return CloudFront URL.

        Args:
            input_file: Path to HTML file from generate stage

        Returns:
            Tuple of (cloudfront_url, metadata)
        """
        self.logger.info(f"Starting S3 deployment for: {input_file}")

        if self.dry_run:
            self.logger.info(f"DRY RUN: Would deploy {input_file} to S3")
            return None, {"dry_run": True, "cloudfront_url": "https://dry-run-mock-cloudfront.example.com"}

        # Extract information from HTML filename
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"HTML file not found: {input_file}")

        # TODO: Implement S3 deployment
        # 1. Upload HTML file to S3 bucket
        # 2. Upload any associated assets (CSS, JS, images)
        # 3. Set appropriate S3 bucket policies for web hosting
        # 4. Invalidate CloudFront cache if configured
        # 5. Return CloudFront URL or S3 website URL

        raise NotImplementedError(f"Stage 5 (Deploy) S3 upload is not yet implemented. Cannot deploy HTML file {input_file}. "
                                 f"Use --dry-run flag to test pipeline without S3 deployment.")