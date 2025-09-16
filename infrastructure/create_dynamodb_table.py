#!/usr/bin/env python3
"""
Create DynamoDB table for Fantasy Football League Data

This script creates the DynamoDB table with the optimal schema for
week-based partitioning and team historical analysis.

Usage:
    python infrastructure/create_dynamodb_table.py --table-name fantasy-league-data --environment prod
"""

import boto3
import argparse
import logging
from botocore.exceptions import ClientError
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_dynamodb_table(table_name: str, environment: str = "prod"):
    """
    Create DynamoDB table with GSIs for fantasy football data.

    Args:
        table_name: Base name of the table
        environment: Environment suffix (dev, staging, prod)
    """

    # Add environment suffix
    full_table_name = f"{table_name}-{environment}"

    dynamodb = boto3.client('dynamodb', region_name='us-east-1')

    try:
        logger.info(f"Creating DynamoDB table: {full_table_name}")

        response = dynamodb.create_table(
            TableName=full_table_name,
            BillingMode='PAY_PER_REQUEST',  # On-demand pricing

            # Main table key schema
            KeySchema=[
                {
                    'AttributeName': 'season_week',
                    'KeyType': 'HASH'   # Partition Key (e.g., "2025-01")
                },
                {
                    'AttributeName': 'data_type_id',
                    'KeyType': 'RANGE'  # Sort Key (e.g., "TEAM#003", "MATCHUP#11vs8")
                }
            ],

            # Attribute definitions
            AttributeDefinitions=[
                {
                    'AttributeName': 'season_week',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'data_type_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'team_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'team_name',
                    'AttributeType': 'S'
                }
            ],

            # Global Secondary Indexes
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'team-id-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'team_id',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'season_week',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    }
                },
                {
                    'IndexName': 'team-name-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'team_name',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'season_week',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    }
                }
            ],

            # Enable point-in-time recovery
            PointInTimeRecoverySpecification={
                'PointInTimeRecoveryEnabled': True
            },

            # Server-side encryption
            SSESpecification={
                'Enabled': True
            },

            # Tags
            Tags=[
                {
                    'Key': 'Project',
                    'Value': 'FantasyFootballLeague'
                },
                {
                    'Key': 'Environment',
                    'Value': environment
                },
                {
                    'Key': 'Purpose',
                    'Value': 'WeeklyDataStorage'
                }
            ]
        )

        logger.info(f"Table creation initiated. ARN: {response['TableDescription']['TableArn']}")

        # Wait for table to become active
        logger.info("Waiting for table to become active...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(
            TableName=full_table_name,
            WaiterConfig={
                'Delay': 5,
                'MaxAttempts': 60
            }
        )

        # Verify GSIs are active
        logger.info("Waiting for Global Secondary Indexes to become active...")
        while True:
            table_description = dynamodb.describe_table(TableName=full_table_name)
            table_status = table_description['Table']['TableStatus']

            if table_status != 'ACTIVE':
                logger.info(f"Table status: {table_status}, waiting...")
                time.sleep(5)
                continue

            # Check GSI status
            gsi_statuses = []
            if 'GlobalSecondaryIndexes' in table_description['Table']:
                for gsi in table_description['Table']['GlobalSecondaryIndexes']:
                    gsi_statuses.append(gsi['IndexStatus'])

            if all(status == 'ACTIVE' for status in gsi_statuses):
                logger.info("✅ Table and all GSIs are now ACTIVE")
                break
            else:
                logger.info(f"GSI statuses: {gsi_statuses}, waiting...")
                time.sleep(5)

        # Print final table information
        table_info = dynamodb.describe_table(TableName=full_table_name)['Table']
        logger.info(f"""
        ✅ DynamoDB Table Created Successfully!

        Table Name: {table_info['TableName']}
        Table ARN: {table_info['TableArn']}
        Table Status: {table_info['TableStatus']}
        Billing Mode: {table_info.get('BillingModeSummary', {}).get('BillingMode', 'PROVISIONED')}

        Global Secondary Indexes:
        """)

        if 'GlobalSecondaryIndexes' in table_info:
            for gsi in table_info['GlobalSecondaryIndexes']:
                logger.info(f"  - {gsi['IndexName']}: {gsi['IndexStatus']}")

        return full_table_name

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceInUseException':
            logger.warning(f"Table {full_table_name} already exists!")
            return full_table_name
        else:
            logger.error(f"Failed to create table: {e}")
            raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

def delete_table(table_name: str, environment: str = "prod"):
    """Delete the DynamoDB table (useful for cleanup/testing)"""
    full_table_name = f"{table_name}-{environment}"

    dynamodb = boto3.client('dynamodb', region_name='us-east-1')

    try:
        logger.info(f"Deleting table: {full_table_name}")
        dynamodb.delete_table(TableName=full_table_name)
        logger.info(f"✅ Table {full_table_name} deletion initiated")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            logger.warning(f"Table {full_table_name} does not exist")
        else:
            logger.error(f"Failed to delete table: {e}")
            raise

def main():
    parser = argparse.ArgumentParser(description='Create DynamoDB table for fantasy football data')
    parser.add_argument('--table-name', default='fantasy-league-data',
                       help='Base name of the DynamoDB table (default: fantasy-league-data)')
    parser.add_argument('--environment', default='prod', choices=['dev', 'staging', 'prod'],
                       help='Environment suffix (default: prod)')
    parser.add_argument('--delete', action='store_true',
                       help='Delete the table instead of creating it')

    args = parser.parse_args()

    if args.delete:
        delete_table(args.table_name, args.environment)
    else:
        table_name = create_dynamodb_table(args.table_name, args.environment)
        logger.info(f"🎉 Table '{table_name}' is ready for use!")

if __name__ == '__main__':
    main()