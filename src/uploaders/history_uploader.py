"""
History uploader for storing league history in DynamoDB.

This module handles uploading historical league data to DynamoDB using
a single-table design pattern for efficient querying.
"""

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional

from src.models.history_models import LeagueHistory, SeasonHistory

logger = logging.getLogger(__name__)


class HistoryUploader:
    """Upload league history to DynamoDB."""

    def __init__(self, dynamodb_resource=None, table_name: str = "fantasy-league-data"):
        """
        Initialize the history uploader.

        Args:
            dynamodb_resource: boto3 DynamoDB resource (will attempt to create if None)
            table_name: Name of the DynamoDB table
        """
        self.table_name = table_name
        self.table = None

        if dynamodb_resource is not None:
            self.dynamodb = dynamodb_resource
            self.table = dynamodb_resource.Table(table_name)
        else:
            # Try to create boto3 resource
            try:
                import boto3
                self.dynamodb = boto3.resource('dynamodb')
                self.table = self.dynamodb.Table(table_name)
            except ImportError:
                logger.error("boto3 not available. Install with: pip install boto3")
                raise
            except Exception as e:
                logger.error(f"Failed to create DynamoDB resource: {e}")
                raise

    def _convert_floats_to_decimal(self, obj: Any) -> Any:
        """
        Recursively convert float values to Decimal for DynamoDB compatibility.

        Args:
            obj: Object to convert

        Returns:
            Object with floats converted to Decimal
        """
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: self._convert_floats_to_decimal(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_floats_to_decimal(item) for item in obj]
        return obj

    def upload_league_history(self, league_history: LeagueHistory, dry_run: bool = False) -> Dict[str, Any]:
        """
        Upload complete league history to DynamoDB.

        Creates three types of records:
        1. METADATA record - League history index
        2. SEASON#{year} records - Individual season data
        3. TEAM#{team_id} records - Team identifier mappings

        Args:
            league_history: LeagueHistory object to upload
            dry_run: If True, only log what would be uploaded without making changes

        Returns:
            Dictionary with upload results and metadata
        """
        league_id = league_history.league_id
        logger.info(f"Uploading league history for league {league_id}")

        if dry_run:
            logger.info("DRY RUN: No data will be written to DynamoDB")

        results = {
            "league_id": league_id,
            "records_created": 0,
            "metadata_record": None,
            "season_records": [],
            "dry_run": dry_run
        }

        try:
            # 1. Upload METADATA record
            metadata_record = self._create_metadata_record(league_history)
            if not dry_run:
                self.table.put_item(Item=metadata_record)
                logger.info(f"Created METADATA record for league {league_id}")
            else:
                logger.info(f"[DRY RUN] Would create METADATA record: {metadata_record}")
            results["metadata_record"] = metadata_record
            results["records_created"] += 1

            # 2. Upload SEASON records
            for season in league_history.seasons:
                season_record = self._create_season_record(league_id, season)
                if not dry_run:
                    self.table.put_item(Item=season_record)
                    logger.info(f"Created SEASON#{season.year} record for league {league_id}")
                else:
                    logger.info(f"[DRY RUN] Would create SEASON#{season.year} record")
                results["season_records"].append(season_record)
                results["records_created"] += 1

            logger.info(f"Successfully uploaded {results['records_created']} records for league {league_id}")
            return results

        except Exception as e:
            logger.error(f"Failed to upload league history: {e}")
            raise

    def _create_metadata_record(self, league_history: LeagueHistory) -> Dict[str, Any]:
        """
        Create METADATA record for league history index.

        Record structure:
        PK: "HISTORY#{league_id}"
        SK: "METADATA"

        Args:
            league_history: LeagueHistory object

        Returns:
            DynamoDB record dictionary
        """
        league_id = league_history.league_id
        seasons_list = [season.year for season in league_history.seasons]

        record = {
            "season_week": f"HISTORY#{league_id}",
            "data_type_id": "METADATA",
            "league_id": league_id,
            "league_name": league_history.league_name,
            "total_seasons": league_history.metadata.total_seasons,
            "year_range": league_history.metadata.year_range,
            "seasons_list": seasons_list,
            "extracted_at": league_history.metadata.extracted_at,
            "last_updated": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "extractor_version": league_history.metadata.extractor_version
        }

        return self._convert_floats_to_decimal(record)

    def _create_season_record(self, league_id: str, season: SeasonHistory) -> Dict[str, Any]:
        """
        Create SEASON record for individual season data.

        Record structure:
        PK: "HISTORY#{league_id}"
        SK: "SEASON#{year}"

        Args:
            league_id: League identifier
            season: SeasonHistory object

        Returns:
            DynamoDB record dictionary
        """
        # Convert season to dictionary
        season_data = season.model_dump()

        record = {
            "season_week": f"HISTORY#{league_id}",
            "data_type_id": f"SEASON#{season.year}",
            "league_id": league_id,
            "year": season.year,
            "regular_season_weeks": season.regular_season_weeks,
            "playoff_weeks": season.playoff_weeks,
            "total_teams": season.total_teams,
            "divisions": season_data["divisions"],
            "final_standings": season_data["final_standings"],
            "champion": season_data["champion"],
            "runner_up": season_data.get("runner_up"),
            "third_place": season_data.get("third_place"),
            "extracted_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

        return self._convert_floats_to_decimal(record)

    def upload_season(self, league_id: str, season: SeasonHistory, dry_run: bool = False) -> Dict[str, Any]:
        """
        Upload a single season to DynamoDB.

        Args:
            league_id: League identifier
            season: SeasonHistory object
            dry_run: If True, only log what would be uploaded

        Returns:
            Dictionary with upload results
        """
        logger.info(f"Uploading season {season.year} for league {league_id}")

        if dry_run:
            logger.info("DRY RUN: No data will be written to DynamoDB")

        try:
            season_record = self._create_season_record(league_id, season)

            if not dry_run:
                self.table.put_item(Item=season_record)
                logger.info(f"Created SEASON#{season.year} record for league {league_id}")
            else:
                logger.info(f"[DRY RUN] Would create SEASON#{season.year} record")

            return {
                "league_id": league_id,
                "year": season.year,
                "season_record": season_record,
                "dry_run": dry_run
            }

        except Exception as e:
            logger.error(f"Failed to upload season {season.year}: {e}")
            raise

    def fetch_league_history(self, league_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch complete league history from DynamoDB.

        Args:
            league_id: League identifier

        Returns:
            Dictionary with metadata and all seasons, or None if not found
        """
        try:
            logger.info(f"Fetching league history for league {league_id}")

            # Query for all records with PK = "HISTORY#{league_id}"
            response = self.table.query(
                KeyConditionExpression='season_week = :pk',
                ExpressionAttributeValues={
                    ':pk': f"HISTORY#{league_id}"
                }
            )

            items = response.get('Items', [])
            if not items:
                logger.warning(f"No history found for league {league_id}")
                return None

            # Separate metadata and season records
            metadata_record = None
            season_records = []

            for item in items:
                data_type_id = item.get('data_type_id', '')
                if data_type_id == 'METADATA':
                    metadata_record = item
                elif data_type_id.startswith('SEASON#'):
                    season_records.append(item)

            if not metadata_record:
                logger.warning(f"No metadata record found for league {league_id}")
                return None

            # Sort seasons by year
            season_records.sort(key=lambda x: x.get('year', 0))

            logger.info(f"Fetched {len(season_records)} seasons for league {league_id}")

            return {
                "metadata": metadata_record,
                "seasons": season_records
            }

        except Exception as e:
            logger.error(f"Failed to fetch league history: {e}")
            raise

    def fetch_season(self, league_id: str, year: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific season from DynamoDB.

        Args:
            league_id: League identifier
            year: Season year

        Returns:
            Season record dictionary or None if not found
        """
        try:
            logger.info(f"Fetching season {year} for league {league_id}")

            response = self.table.get_item(
                Key={
                    'season_week': f"HISTORY#{league_id}",
                    'data_type_id': f"SEASON#{year}"
                }
            )

            item = response.get('Item')
            if item:
                logger.info(f"Found season {year} for league {league_id}")
                return item
            else:
                logger.warning(f"Season {year} not found for league {league_id}")
                return None

        except Exception as e:
            logger.error(f"Failed to fetch season {year}: {e}")
            raise
