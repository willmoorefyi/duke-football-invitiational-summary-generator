"""
Shared S3 + CloudFront deploy helpers.

Extracted from the deploy stage so both the deploy stage (Stage 5) and the
newsletter stage (Stage 6) upload HTML and invalidate CloudFront through one
implementation instead of duplicating the boto3 calls. Each function takes an
explicit boto3 client and a logger, keeping it free of pipeline-stage state.
"""

from datetime import datetime
from typing import List

try:
    from botocore.exceptions import ClientError
except ImportError:  # pragma: no cover - mirrors deploy_stage's optional import
    ClientError = Exception


def upload_html_string(s3_client, bucket_name: str, key: str, html: str, logger,
                       cache_control: str = 'public, max-age=3600') -> None:
    """Upload an in-memory HTML string to S3."""
    s3_client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=html.encode('utf-8'),
        ContentType='text/html',
        CacheControl=cache_control,
    )
    logger.info(f"Uploaded s3://{bucket_name}/{key}")


def invalidate_cloudfront_cache(cloudfront_client, distribution_id: str,
                                s3_keys: List[str], logger) -> str:
    """
    Invalidate CloudFront cache for the uploaded files.

    Args:
        cloudfront_client: boto3 CloudFront client
        distribution_id: CloudFront distribution ID to invalidate
        s3_keys: List of S3 keys to invalidate
        logger: Logger for progress / error reporting

    Returns:
        CloudFront invalidation ID (or "failed" for non-fatal errors)
    """
    # Convert S3 keys to CloudFront paths (add leading slash)
    paths = [f"/{s3_key}" for s3_key in s3_keys]

    logger.info(f"Invalidating CloudFront cache for paths: {paths}")

    try:
        response = cloudfront_client.create_invalidation(
            DistributionId=distribution_id,
            InvalidationBatch={
                'Paths': {
                    'Quantity': len(paths),
                    'Items': paths
                },
                'CallerReference': f"fantasy-extractor-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            }
        )

        invalidation_id = response['Invalidation']['Id']
        logger.info(f"CloudFront invalidation created: {invalidation_id}")

        return invalidation_id

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchDistribution':
            raise RuntimeError(f"CloudFront distribution '{distribution_id}' does not exist")
        elif error_code == 'AccessDenied':
            raise RuntimeError(f"Access denied to CloudFront distribution '{distribution_id}'. Check AWS credentials and permissions")
        else:
            # Log the error but don't fail the deployment
            logger.warning(f"CloudFront invalidation failed: {e}")
            return "failed"
