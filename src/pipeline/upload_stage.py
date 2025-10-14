"""
Upload Stage

Stage 2: DynamoDB Upload
Uploads structured fantasy data to DynamoDB with schema versioning.
Creates multiple records: main weekly report + individual team records for GSI support.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from .base import PipelineStage


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
            # Handle both raw JSON and enhanced JSON structures
            if 'current_week' in data:
                # Enhanced JSON structure from aggregate stage
                current_week_data = data['current_week']
                week = current_week_data.get('week')
                year = current_week_data.get('season') or current_week_data.get('year')
                league_id = current_week_data.get('league_id')
                league_name = current_week_data.get('league_name', 'Unknown League')
            else:
                # Raw JSON structure (backward compatibility)
                week = data.get('week')
                year = data.get('season') or data.get('year')
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
            profile = getattr(self.config.pipeline.aws, 'profile', None)
            schema_version = '1.0'
            timestamp = datetime.now().isoformat()

            # Create DynamoDB connection with profile support
            if profile:
                session = boto3.Session(profile_name=profile, region_name=region)
                dynamodb = session.resource('dynamodb')
            else:
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