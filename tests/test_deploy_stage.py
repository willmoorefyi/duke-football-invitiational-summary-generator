import pytest
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path

from src.pipeline.deploy_stage import DeployStage
from src.utils.config import Config, PipelineConfig, AWSConfig


class TestDeployStage:
    """Test suite for S3 deployment functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.league_id = 380491
        self.deploy_stage = DeployStage(league_id=self.league_id)

        # Mock the config to return expected values
        self.deploy_stage.config = Config(
            pipeline=PipelineConfig(
                aws=AWSConfig(
                    region='us-east-1'
                )
            )
        )

    @patch('src.pipeline.deploy_stage.boto3')
    def test_successful_deployment(self, mock_boto3):
        """Test successful S3 upload and CloudFront invalidation."""
        # Setup mocks
        mock_s3_client = MagicMock()
        mock_cloudfront_client = MagicMock()

        # Mock Session to return clients
        mock_session = MagicMock()
        mock_session.client.side_effect = lambda service: {
            's3': mock_s3_client,
            'cloudfront': mock_cloudfront_client
        }[service]
        mock_boto3.Session.return_value = mock_session

        # Mock CloudFront response
        mock_cloudfront_client.create_invalidation.return_value = {
            'Invalidation': {'Id': 'test-invalidation-123'}
        }

        # Create temporary HTML file
        with tempfile.NamedTemporaryFile(suffix='_week_5_20250915_142530.html', delete=False) as temp_file:
            temp_file.write(b'<html><body>Test HTML</body></html>')
            temp_path = Path(temp_file.name)

        try:
            # Execute deployment
            result_url, metadata = self.deploy_stage.execute(str(temp_path))

            # Verify S3 upload was called
            mock_s3_client.upload_file.assert_called_once()
            args = mock_s3_client.upload_file.call_args
            assert args[0][0] == str(temp_path)  # local file path
            assert args[0][1] == 'will.moore.fyi'  # bucket name
            assert 'duke-football-invitational/weekly-reports/fantasy_report_2025_week_5.html' in args[0][2]  # s3 key

            # Verify CloudFront invalidation was called
            mock_cloudfront_client.create_invalidation.assert_called_once()
            invalidation_args = mock_cloudfront_client.create_invalidation.call_args
            assert invalidation_args[1]['DistributionId'] == 'E10BJV5LJCPKIE'

            # Verify return values
            assert result_url == 'https://will.moore.fyi/duke-football-invitational/weekly-reports/fantasy_report_2025_week_5.html'
            assert metadata['s3_key'] == 'duke-football-invitational/weekly-reports/fantasy_report_2025_week_5.html'
            assert metadata['cloudfront_url'] == result_url
            assert metadata['invalidation_id'] == 'test-invalidation-123'
            assert metadata['bucket'] == 'will.moore.fyi'

        finally:
            temp_path.unlink()  # cleanup

    def test_dry_run_mode(self):
        """Test dry-run mode returns mock values without AWS calls."""
        # Enable dry-run mode
        deploy_stage_dry = DeployStage(league_id=self.league_id, dry_run=True)

        # Create temporary HTML file
        with tempfile.NamedTemporaryFile(suffix='_week_3_20250910_120000.html', delete=False) as temp_file:
            temp_file.write(b'<html><body>Dry Run Test</body></html>')
            temp_path = Path(temp_file.name)

        try:
            # Execute dry-run deployment
            result_url, metadata = deploy_stage_dry.execute(str(temp_path))

            # Verify dry-run behavior
            assert result_url is None
            assert metadata['dry_run'] is True
            assert 'dry-run-mock-cloudfront.example.com' in metadata['cloudfront_url']

        finally:
            temp_path.unlink()  # cleanup

    def test_file_not_found_error(self):
        """Test deployment fails gracefully when input file doesn't exist."""
        non_existent_file = '/path/to/non/existent/file.html'

        with pytest.raises(FileNotFoundError, match="HTML file not found"):
            self.deploy_stage.execute(non_existent_file)

    @patch('src.pipeline.deploy_stage.AWS_AVAILABLE', False)
    def test_aws_not_available_error(self):
        """Test deployment fails when boto3 is not available."""
        # Create temporary HTML file
        with tempfile.NamedTemporaryFile(suffix='_week_1_20250901_120000.html', delete=False) as temp_file:
            temp_file.write(b'<html><body>Test HTML</body></html>')
            temp_path = Path(temp_file.name)

        try:
            with pytest.raises(ImportError, match="boto3 is required for S3 deployment"):
                self.deploy_stage.execute(str(temp_path))

        finally:
            temp_path.unlink()  # cleanup

    @patch('src.pipeline.deploy_stage.boto3')
    def test_s3_bucket_not_found_error(self, mock_boto3):
        """Test S3 upload fails when bucket doesn't exist."""
        # Setup mock S3 client to raise NoSuchBucket error
        mock_s3_client = MagicMock()

        # Mock Session to return S3 client
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        from botocore.exceptions import ClientError
        mock_s3_client.upload_file.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchBucket'}},
            'upload_file'
        )

        # Create temporary HTML file
        with tempfile.NamedTemporaryFile(suffix='_week_2_20250908_140000.html', delete=False) as temp_file:
            temp_file.write(b'<html><body>Test HTML</body></html>')
            temp_path = Path(temp_file.name)

        try:
            with pytest.raises(RuntimeError, match="S3 bucket 'will.moore.fyi' does not exist"):
                self.deploy_stage.execute(str(temp_path))

        finally:
            temp_path.unlink()  # cleanup

    @patch('src.pipeline.deploy_stage.boto3')
    def test_s3_access_denied_error(self, mock_boto3):
        """Test S3 upload fails when access is denied."""
        # Setup mock S3 client to raise AccessDenied error
        mock_s3_client = MagicMock()

        # Mock Session to return S3 client
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        from botocore.exceptions import ClientError
        mock_s3_client.upload_file.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied'}},
            'upload_file'
        )

        # Create temporary HTML file
        with tempfile.NamedTemporaryFile(suffix='_week_4_20250914_160000.html', delete=False) as temp_file:
            temp_file.write(b'<html><body>Test HTML</body></html>')
            temp_path = Path(temp_file.name)

        try:
            with pytest.raises(RuntimeError, match="Access denied to S3 bucket 'will.moore.fyi'"):
                self.deploy_stage.execute(str(temp_path))

        finally:
            temp_path.unlink()  # cleanup

    @patch('src.pipeline.deploy_stage.boto3')
    def test_cloudfront_invalidation_error(self, mock_boto3):
        """Test deployment succeeds even when CloudFront invalidation fails."""
        # Setup mock S3 client (successful)
        mock_s3_client = MagicMock()
        mock_cloudfront_client = MagicMock()

        # Mock Session to return clients
        mock_session = MagicMock()
        mock_session.client.side_effect = lambda service: {
            's3': mock_s3_client,
            'cloudfront': mock_cloudfront_client
        }[service]
        mock_boto3.Session.return_value = mock_session

        # Mock CloudFront to raise error
        from botocore.exceptions import ClientError
        mock_cloudfront_client.create_invalidation.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied'}},
            'create_invalidation'
        )

        # Create temporary HTML file
        with tempfile.NamedTemporaryFile(suffix='_week_7_20250920_180000.html', delete=False) as temp_file:
            temp_file.write(b'<html><body>Test HTML</body></html>')
            temp_path = Path(temp_file.name)

        try:
            # Deployment should fail when CloudFront access is denied
            with pytest.raises(RuntimeError, match="Access denied to CloudFront distribution"):
                self.deploy_stage.execute(str(temp_path))

            # Verify S3 upload was successful before CloudFront failure
            mock_s3_client.upload_file.assert_called_once()

            # Verify CloudFront was attempted
            mock_cloudfront_client.create_invalidation.assert_called_once()

        finally:
            temp_path.unlink()  # cleanup

    def test_filename_parsing_edge_cases(self):
        """Test filename parsing with various edge case formats."""
        deploy_stage = DeployStage(league_id=self.league_id)

        # Test standard format
        year, week = deploy_stage._extract_week_and_year_from_filename(
            'fantasy_report_week_5_20250915_142530.html'
        )
        assert year == '2025'
        assert week == '5'

        # Test format without timestamp
        year, week = deploy_stage._extract_week_and_year_from_filename(
            'fantasy_report_week_12_something.html'
        )
        assert year == str(datetime.now().year)  # fallback to current year
        assert week == '12'

        # Test format with no week info
        year, week = deploy_stage._extract_week_and_year_from_filename(
            'random_file_name.html'
        )
        assert year == str(datetime.now().year)  # fallback to current year
        assert week == '1'  # fallback to week 1

    @patch('src.pipeline.deploy_stage.boto3')
    def test_annual_recap_upload(self, mock_boto3):
        """Test annual recap file upload with year in filename."""
        # Setup mock S3 and CloudFront clients
        mock_s3_client = MagicMock()
        mock_cloudfront_client = MagicMock()

        # Mock Session to return clients
        mock_session = MagicMock()
        mock_session.client.side_effect = lambda service: {
            's3': mock_s3_client,
            'cloudfront': mock_cloudfront_client
        }[service]
        mock_boto3.Session.return_value = mock_session

        # Mock CloudFront response
        mock_cloudfront_client.create_invalidation.return_value = {
            'Invalidation': {'Id': 'test-invalidation-789'}
        }

        # Create temporary annual recap HTML file
        with tempfile.NamedTemporaryFile(suffix='-recap-2024.html', prefix='annual', delete=False) as temp_file:
            temp_file.write(b'<html><body>Annual Recap 2024</body></html>')
            temp_path = Path(temp_file.name)

        # Rename to match expected pattern
        annual_recap_path = temp_path.parent / 'annual-recap-2024.html'
        temp_path.rename(annual_recap_path)

        try:
            result_url, metadata = self.deploy_stage.execute(str(annual_recap_path))

            # Verify S3 upload was called with correct key
            mock_s3_client.upload_file.assert_called_once()
            call_args = mock_s3_client.upload_file.call_args
            assert call_args[0][1] == 'will.moore.fyi'
            assert call_args[0][2] == 'duke-football-invitational/annual-recap-2024.html'

            # Verify CloudFront URL
            assert result_url == 'https://will.moore.fyi/duke-football-invitational/annual-recap-2024.html'

            # Verify CloudFront invalidation was called
            mock_cloudfront_client.create_invalidation.assert_called_once()

        finally:
            annual_recap_path.unlink()  # cleanup

    @patch('src.pipeline.deploy_stage.boto3')
    def test_cloudfront_non_access_error_graceful_handling(self, mock_boto3):
        """Test deployment succeeds when CloudFront has non-access-denied errors."""
        # Setup mock S3 client (successful)
        mock_s3_client = MagicMock()
        mock_cloudfront_client = MagicMock()

        # Mock Session to return clients
        mock_session = MagicMock()
        mock_session.client.side_effect = lambda service: {
            's3': mock_s3_client,
            'cloudfront': mock_cloudfront_client
        }[service]
        mock_boto3.Session.return_value = mock_session

        # Mock CloudFront to raise non-access error (should be handled gracefully)
        from botocore.exceptions import ClientError
        mock_cloudfront_client.create_invalidation.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException'}},
            'create_invalidation'
        )

        # Create temporary HTML file
        with tempfile.NamedTemporaryFile(suffix='_week_8_20250922_200000.html', delete=False) as temp_file:
            temp_file.write(b'<html><body>Test HTML</body></html>')
            temp_path = Path(temp_file.name)

        try:
            # Deployment should succeed despite CloudFront throttling
            result_url, metadata = self.deploy_stage.execute(str(temp_path))

            # Verify S3 upload was successful
            mock_s3_client.upload_file.assert_called_once()

            # Verify CloudFront was attempted but handled gracefully
            mock_cloudfront_client.create_invalidation.assert_called_once()
            assert metadata['invalidation_id'] == 'failed'
            assert result_url == 'https://will.moore.fyi/duke-football-invitational/weekly-reports/fantasy_report_2025_week_8.html'

        finally:
            temp_path.unlink()  # cleanup

    @patch('src.pipeline.deploy_stage.boto3')
    def test_s3_generic_error(self, mock_boto3):
        """Test S3 upload fails with generic ClientError."""
        # Setup mock S3 client to raise generic error
        mock_s3_client = MagicMock()

        # Mock Session to return S3 client
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        from botocore.exceptions import ClientError
        mock_s3_client.upload_file.side_effect = ClientError(
            {'Error': {'Code': 'InternalError'}},
            'upload_file'
        )

        # Create temporary HTML file
        with tempfile.NamedTemporaryFile(suffix='_week_9_20250925_220000.html', delete=False) as temp_file:
            temp_file.write(b'<html><body>Test HTML</body></html>')
            temp_path = Path(temp_file.name)

        try:
            with pytest.raises(RuntimeError, match="S3 upload failed"):
                self.deploy_stage.execute(str(temp_path))

        finally:
            temp_path.unlink()  # cleanup