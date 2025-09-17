"""
Deploy Stage

Stage 5: S3 Deployment
Uploads HTML website to S3 bucket with CloudFront integration.
Takes HTML file from GenerateStage and deploys to cloud infrastructure.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from .base import PipelineStage

# AWS imports
try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
    AWS_AVAILABLE = True
except ImportError:
    boto3 = None
    BotoCoreError = ClientError = NoCredentialsError = Exception
    AWS_AVAILABLE = False


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

        # Check AWS availability
        if not AWS_AVAILABLE:
            raise ImportError("boto3 is required for S3 deployment. Install with: pip install boto3")

        try:
            # Extract week information from filename for S3 key generation
            s3_key, cloudfront_url = self._upload_to_s3(input_path)

            # Invalidate CloudFront cache
            invalidation_id = self._invalidate_cloudfront_cache([s3_key])

            self.logger.info(f"Successfully deployed to: {cloudfront_url}")

            return cloudfront_url, {
                "s3_key": s3_key,
                "cloudfront_url": cloudfront_url,
                "invalidation_id": invalidation_id,
                "bucket": "will.moore.fyi",
                "deployment_timestamp": datetime.now().isoformat()
            }

        except (BotoCoreError, ClientError, NoCredentialsError) as e:
            self.logger.error(f"AWS error during deployment: {e}")
            raise RuntimeError(f"S3 deployment failed: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during deployment: {e}")
            raise RuntimeError(f"Deployment failed: {e}")

    def _extract_week_and_year_from_filename(self, filename: str) -> Tuple[str, str]:
        """
        Extract year and week from HTML filename.

        Expected format: fantasy_report_week_N_YYYYMMDD_HHMMSS.html
        Returns (year, week) for generating S3 key in format fantasy_report_YYYY_week_N.html
        """
        # Try to match the expected pattern
        pattern = r'fantasy_report_week_(\d+)_(\d{8})_\d{6}\.html'
        match = re.match(pattern, filename)

        if match:
            week = match.group(1)
            date_str = match.group(2)
            year = date_str[:4]
            return year, week

        # Fallback: try to extract from enhanced JSON if available
        # For now, use current year and week from filename
        week_pattern = r'week_(\d+)'
        week_match = re.search(week_pattern, filename)
        week = week_match.group(1) if week_match else "1"

        # Use current year as fallback
        year = str(datetime.now().year)

        return year, week

    def _upload_to_s3(self, file_path: Path) -> Tuple[str, str]:
        """
        Upload HTML file to S3 bucket with standardized naming.

        Returns:
            Tuple of (s3_key, cloudfront_url)
        """
        # Extract year and week from filename
        year, week = self._extract_week_and_year_from_filename(file_path.name)

        # Generate standardized S3 key: duke-football-invitational/weekly-reports/fantasy_report_YYYY_week_N.html
        s3_key = f"duke-football-invitational/weekly-reports/fantasy_report_{year}_week_{week}.html"

        # S3 configuration
        bucket_name = "will.moore.fyi"

        # Create S3 client
        s3_client = boto3.client('s3')

        # Upload file
        self.logger.info(f"Uploading {file_path.name} to s3://{bucket_name}/{s3_key}")

        try:
            s3_client.upload_file(
                str(file_path),
                bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': 'text/html',
                    'CacheControl': 'public, max-age=3600'  # Cache for 1 hour
                }
            )

            # Generate CloudFront URL
            cloudfront_url = f"https://will.moore.fyi/{s3_key}"

            self.logger.info(f"Successfully uploaded to S3: {s3_key}")
            return s3_key, cloudfront_url

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                raise RuntimeError(f"S3 bucket '{bucket_name}' does not exist")
            elif error_code == 'AccessDenied':
                raise RuntimeError(f"Access denied to S3 bucket '{bucket_name}'. Check AWS credentials and permissions")
            else:
                raise RuntimeError(f"S3 upload failed: {e}")

    def _invalidate_cloudfront_cache(self, s3_keys: List[str]) -> str:
        """
        Invalidate CloudFront cache for the uploaded files.

        Args:
            s3_keys: List of S3 keys to invalidate

        Returns:
            CloudFront invalidation ID
        """
        cloudfront_distribution_id = "E10BJV5LJCPKIE"

        # Create CloudFront client
        cloudfront_client = boto3.client('cloudfront')

        # Convert S3 keys to CloudFront paths (add leading slash)
        paths = [f"/{s3_key}" for s3_key in s3_keys]

        self.logger.info(f"Invalidating CloudFront cache for paths: {paths}")

        try:
            response = cloudfront_client.create_invalidation(
                DistributionId=cloudfront_distribution_id,
                InvalidationBatch={
                    'Paths': {
                        'Quantity': len(paths),
                        'Items': paths
                    },
                    'CallerReference': f"fantasy-extractor-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                }
            )

            invalidation_id = response['Invalidation']['Id']
            self.logger.info(f"CloudFront invalidation created: {invalidation_id}")

            return invalidation_id

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchDistribution':
                raise RuntimeError(f"CloudFront distribution '{cloudfront_distribution_id}' does not exist")
            elif error_code == 'AccessDenied':
                raise RuntimeError(f"Access denied to CloudFront distribution '{cloudfront_distribution_id}'. Check AWS credentials and permissions")
            else:
                # Log the error but don't fail the deployment
                self.logger.warning(f"CloudFront invalidation failed: {e}")
                return "failed"