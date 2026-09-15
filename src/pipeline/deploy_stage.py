"""
Deploy Stage

Stage 5: S3 Deployment
Uploads HTML website to S3 bucket with CloudFront integration.
Takes HTML file from GenerateStage and deploys to cloud infrastructure.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from .base import PipelineStage
from ..generators.templated_html_generator import TemplatedFantasyHTMLGenerator

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

    def _get_boto3_session(self) -> boto3.Session:
        """Get boto3 session with profile support from configuration."""
        profile = getattr(self.config.pipeline.aws, 'profile', None)
        region = self.config.pipeline.aws.region

        if profile:
            return boto3.Session(profile_name=profile, region_name=region)
        else:
            return boto3.Session(region_name=region)

    def execute(self, input_file: str, enhanced_json_path: Optional[str] = None) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Upload HTML website to S3 and return CloudFront URL.
        Also generates and uploads overview page if enhanced JSON is provided.

        Args:
            input_file: Path to HTML file from generate stage
            enhanced_json_path: Optional path to enhanced JSON for overview generation

        Returns:
            Tuple of (cloudfront_url, metadata)
        """
        self.logger.info(f"Starting S3 deployment for: {input_file}")

        if self.dry_run:
            self.logger.info(f"DRY RUN: Would deploy {input_file} to S3")
            if enhanced_json_path:
                self.logger.info(f"DRY RUN: Would also generate and deploy overview page")
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

            # Generate and upload overview page if enhanced JSON is provided
            overview_metadata = {}
            if enhanced_json_path:
                overview_metadata = self._generate_and_upload_overview(enhanced_json_path)

            # Collect all S3 keys for CloudFront invalidation
            s3_keys = [s3_key]
            if overview_metadata.get('s3_key'):
                s3_keys.append(overview_metadata['s3_key'])
            if overview_metadata.get('redirect_s3_key'):
                s3_keys.append(overview_metadata['redirect_s3_key'])
            if overview_metadata.get('hub', {}).get('s3_key'):
                s3_keys.append(overview_metadata['hub']['s3_key'])

            # Invalidate CloudFront cache
            invalidation_id = self._invalidate_cloudfront_cache(s3_keys)

            self.logger.info(f"Successfully deployed to: {cloudfront_url}")

            metadata = {
                "s3_key": s3_key,
                "cloudfront_url": cloudfront_url,
                "invalidation_id": invalidation_id,
                "bucket": "will.moore.fyi",
                "deployment_timestamp": datetime.now().isoformat()
            }

            if overview_metadata:
                metadata['overview'] = overview_metadata

            return cloudfront_url, metadata

        except (BotoCoreError, ClientError, NoCredentialsError) as e:
            self.logger.error(f"AWS error during deployment: {e}")
            raise RuntimeError(f"S3 deployment failed: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during deployment: {e}")
            raise RuntimeError(f"Deployment failed: {e}")

    def _generate_and_upload_overview(self, enhanced_json_path: str) -> Dict[str, Any]:
        """
        Generate and upload season overview page.
        Only generates overview if this is the latest completed week in the season.

        Args:
            enhanced_json_path: Path to enhanced JSON file

        Returns:
            Dictionary with overview deployment metadata
        """
        self.logger.info("Checking if overview page should be generated...")

        try:
            # Load enhanced JSON
            with open(enhanced_json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            # Check if this is the latest week
            is_latest_week = json_data.get('metadata', {}).get('is_latest_week', True)

            if not is_latest_week:
                self.logger.info("This is not the latest completed week in the season. Skipping overview page generation.")
                return {}

            self.logger.info("This is the latest week. Generating season overview page...")

            season = self._extract_season(json_data)

            # Generate overview HTML
            generator = TemplatedFantasyHTMLGenerator()
            overview_output_path = Path(enhanced_json_path).parent.parent / "html" / "overview.html"
            overview_output_path.parent.mkdir(parents=True, exist_ok=True)

            generator.generate_overview_page(json_data, str(overview_output_path))
            self.logger.info(f"Generated overview page: {overview_output_path}")

            # Upload the overview into its season-scoped location so past seasons
            # are preserved instead of overwritten (weekly-reports/{year}/index.html).
            bucket_name = "will.moore.fyi"
            s3_key = f"duke-football-invitational/weekly-reports/{season}/index.html"

            session = self._get_boto3_session()
            s3_client = session.client('s3')
            self.logger.info(f"Uploading overview to s3://{bucket_name}/{s3_key}")

            s3_client.upload_file(
                str(overview_output_path),
                bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': 'text/html',
                    'CacheControl': 'public, max-age=3600'
                }
            )

            cloudfront_url = f"https://will.moore.fyi/{s3_key}"
            self.logger.info(f"Successfully uploaded overview page to: {cloudfront_url}")

            result = {
                "s3_key": s3_key,
                "cloudfront_url": cloudfront_url,
                "local_path": str(overview_output_path),
                "season": season,
            }

            # Legacy redirect: weekly-reports/index.html -> current season overview,
            # so the previously-bookmarked URL keeps working.
            try:
                redirect_target = f"/duke-football-invitational/weekly-reports/{season}/index.html"
                redirect_key = "duke-football-invitational/weekly-reports/index.html"
                self._upload_html_string(
                    s3_client, bucket_name, redirect_key,
                    self._redirect_html(redirect_target),
                    cache_control='public, max-age=300'
                )
                result['redirect_s3_key'] = redirect_key
            except Exception as e:
                self.logger.warning(f"Failed to upload weekly-reports redirect: {e}")

            # Root season hub (the abstraction layer above per-season overviews).
            try:
                hub_meta = self._generate_and_upload_hub(
                    generator, s3_client, bucket_name, json_data, season, overview_output_path.parent
                )
                if hub_meta:
                    result['hub'] = hub_meta
            except Exception as e:
                self.logger.warning(f"Failed to generate/upload season hub: {e}")

            return result

        except Exception as e:
            self.logger.warning(f"Failed to generate/upload overview page: {e}")
            # Don't fail the entire deployment if overview generation fails
            return {}

    def _extract_season(self, json_data: Dict[str, Any]) -> int:
        """Derive the season year from enhanced JSON, falling back to current year."""
        current_week = json_data.get('current_week', json_data)
        season = current_week.get('season') or json_data.get('season')
        try:
            return int(season)
        except (TypeError, ValueError):
            return datetime.now().year

    def _extract_leader_name(self, json_data: Dict[str, Any]) -> Optional[str]:
        """Best-effort: name of the current #1 team from computed standings."""
        try:
            standings = json_data.get('season_context', {}).get('team_standings', {})
            entries = standings.values() if isinstance(standings, dict) else standings
            for entry in entries:
                if entry.get('overall_rank') == 1:
                    return entry.get('team_name') or entry.get('name')
        except Exception:
            pass
        return None

    def _redirect_html(self, target: str) -> str:
        """Minimal HTML meta-refresh redirect to `target`."""
        return (
            "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\">"
            f"<meta http-equiv=\"refresh\" content=\"0; url={target}\">"
            f"<link rel=\"canonical\" href=\"{target}\">"
            "<title>Redirecting…</title></head>"
            f"<body>Redirecting to <a href=\"{target}\">the current season</a>.</body></html>"
        )

    def _upload_html_string(self, s3_client, bucket_name: str, key: str, html: str,
                            cache_control: str = 'public, max-age=3600') -> None:
        """Upload an in-memory HTML string to S3."""
        s3_client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=html.encode('utf-8'),
            ContentType='text/html',
            CacheControl=cache_control,
        )
        self.logger.info(f"Uploaded s3://{bucket_name}/{key}")

    def _generate_and_upload_hub(self, generator, s3_client, bucket_name: str,
                                 json_data: Dict[str, Any], season: int,
                                 html_dir: Path) -> Dict[str, Any]:
        """Build the season hub from current data + stored league history and upload it."""
        # Best-effort: fetch stored league history for the champions roll.
        league_history = None
        try:
            league_id = getattr(self.config.league, 'league_id', None)
            table_name = self.config.pipeline.aws.dynamodb_table
            if league_id is not None:
                from ..uploaders.history_uploader import HistoryUploader
                session = self._get_boto3_session()
                dynamodb = session.resource('dynamodb')
                uploader = HistoryUploader(dynamodb_resource=dynamodb, table_name=table_name)
                league_history = uploader.fetch_league_history(str(league_id))
        except Exception as e:
            self.logger.warning(f"Could not fetch league history for hub (continuing without it): {e}")

        current_week = json_data.get('current_week', json_data)
        league_name = current_week.get('league_name', 'Duke Football Invitational')

        # Best-effort: discover which season overviews / annual recaps already exist
        # in S3 so the hub only links to pages that are actually there (no 404s).
        overview_years = self._discover_years(
            s3_client, bucket_name,
            prefix="duke-football-invitational/weekly-reports/",
            pattern=r'weekly-reports/(\d{4})/index\.html$',
        )
        recap_years = self._discover_years(
            s3_client, bucket_name,
            prefix="duke-football-invitational/annual-recap-",
            pattern=r'annual-recap-(\d{4})\.html$',
        )

        # Team logos for champion/title cards (current roster; historical-only
        # team names simply won't have a logo, which the template handles).
        try:
            team_logos = generator._create_team_logo_lookup(current_week)
        except Exception:
            team_logos = {}

        hub_data = generator.build_hub_data(
            current_season=season,
            current_week=current_week.get('week'),
            leader_name=self._extract_leader_name(json_data),
            league_history=league_history,
            league_name=league_name,
            available_overview_years=overview_years,
            available_recap_years=recap_years,
            team_logos=team_logos,
        )

        hub_output_path = html_dir / "hub.html"
        generator.generate_hub_page(hub_data, str(hub_output_path))

        hub_key = "duke-football-invitational/index.html"
        s3_client.upload_file(
            str(hub_output_path),
            bucket_name,
            hub_key,
            ExtraArgs={'ContentType': 'text/html', 'CacheControl': 'public, max-age=3600'},
        )
        self.logger.info(f"Uploaded season hub to s3://{bucket_name}/{hub_key}")
        return {"s3_key": hub_key, "cloudfront_url": f"https://will.moore.fyi/{hub_key}",
                "local_path": str(hub_output_path)}

    def _discover_years(self, s3_client, bucket_name: str, prefix: str, pattern: str) -> set:
        """
        List S3 objects under `prefix` and return the set of 4-digit years captured by
        `pattern`. Best-effort: returns an empty set if listing fails (e.g. no
        ListBucket permission), so the hub simply links fewer seasons rather than 404s.
        """
        years = set()
        try:
            paginator = s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
                for obj in page.get('Contents', []):
                    match = re.search(pattern, obj['Key'])
                    if match:
                        years.add(int(match.group(1)))
        except Exception as e:
            self.logger.warning(f"Could not list S3 for '{prefix}' (hub links limited): {e}")
        return years

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

        # Fallback: pull the week and any embedded YYYYMMDD date token from the name.
        week_pattern = r'week_(\d+)'
        week_match = re.search(week_pattern, filename)
        week = week_match.group(1) if week_match else "1"

        # Prefer a date embedded in the filename over the wall clock, so the derived
        # year matches the report's date even when the strict prefix doesn't match.
        date_match = re.search(r'(\d{8})', filename)
        if date_match:
            year = date_match.group(1)[:4]
        else:
            year = str(datetime.now().year)

        return year, week

    def _upload_to_s3(self, file_path: Path) -> Tuple[str, str]:
        """
        Upload HTML file to S3 bucket with standardized naming.

        Returns:
            Tuple of (s3_key, cloudfront_url)
        """
        # Check if this is an annual recap file
        annual_recap_pattern = r'annual-recap-(\d{4})\.html'
        annual_match = re.match(annual_recap_pattern, file_path.name)

        if annual_match:
            # Annual recap file
            year = annual_match.group(1)
            s3_key = f"duke-football-invitational/annual-recap-{year}.html"
        else:
            # Regular weekly report
            # Extract year and week from filename
            year, week = self._extract_week_and_year_from_filename(file_path.name)

            # Generate standardized S3 key: duke-football-invitational/weekly-reports/fantasy_report_YYYY_week_N.html
            s3_key = f"duke-football-invitational/weekly-reports/fantasy_report_{year}_week_{week}.html"

        # S3 configuration
        bucket_name = "will.moore.fyi"

        # Create S3 client with profile support
        session = self._get_boto3_session()
        s3_client = session.client('s3')

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

        # Create CloudFront client with profile support
        session = self._get_boto3_session()
        cloudfront_client = session.client('cloudfront')

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