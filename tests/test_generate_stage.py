import pytest
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path

from src.pipeline.generate_stage import GenerateStage
from src.utils.config import Config


class TestGenerateStage:
    """Test suite for HTML generation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.league_id = 380491
        self.generate_stage = GenerateStage(league_id=self.league_id)

        # Mock config
        self.generate_stage.config = Config()

        # Sample enhanced data matching the expected enhanced JSON format
        self.sample_enhanced_data = {
            "current_week": {
                "league_id": 380491,
                "league_name": "Duke Football Invitational",
                "season": 2025,
                "week": 1,
                "report_date": "2025-09-15 23:25:36.701615",
                "divisions": [
                    {
                        "name": "Adams",
                        "teams": [
                            {
                                "id": 3,
                                "name": "They Stole Danny's Dimes",
                                "abbreviation": "MPB",
                                "owner": "dukefb26",
                                "division": "Adams",
                                "wins": 1,
                                "losses": 0,
                                "ties": 0,
                                "points_for": 139.7,
                                "points_against": 132.58,
                                "overall_rank": 1,
                                "division_rank": 1
                            }
                        ]
                    }
                ],
                "matchups": [
                    {
                        "home_team": {
                            "id": 3,
                            "name": "They Stole Danny's Dimes",
                            "score": 139.7
                        },
                        "away_team": {
                            "id": 9,
                            "name": "The Williams Football Team",
                            "score": 132.58
                        },
                        "winner_id": 3
                    }
                ],
                "injured_starters": [],
                "awards": {
                    "mvp": {
                        "player_name": "Test Player",
                        "team_name": "Test Team",
                        "score": 25.5
                    }
                }
            },
            "season_context": {
                "standings_progression": [],
                "matchup_history": {},
                "award_summaries": {},
                "performance_trends": {}
            },
            "metadata": {
                "aggregation_timestamp": "2025-09-15T23:25:36.701615",
                "dynamodb_record_id": "test_record_123",
                "historical_weeks_included": 0,
                "season": 2025,
                "league_id": 380491,
                "current_week": 1,
                "data_source": "current_week_only"
            }
        }

        # Sample raw data (fallback case)
        self.sample_raw_data = {
            "league_id": 380491,
            "league_name": "Duke Football Invitational",
            "season": 2025,
            "week": 1,
            "divisions": [],
            "matchups": [],
            "injured_starters": [],
            "awards": {}
        }

    def test_dry_run_mode(self):
        """Test that dry run mode works correctly."""
        dry_run_stage = GenerateStage(league_id=self.league_id, dry_run=True)
        dry_run_stage.config = self.generate_stage.config

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_enhanced_data, f)
            temp_file = f.name

        try:
            output_path, metadata = dry_run_stage.execute(input_file=temp_file)

            assert output_path is None
            assert metadata["dry_run"] is True
            assert "html_file" in metadata
            assert metadata["html_file"].endswith("index.html")
        finally:
            Path(temp_file).unlink()

    def test_custom_output_directory(self):
        """Test specifying custom output directory."""
        dry_run_stage = GenerateStage(league_id=self.league_id, dry_run=True)
        dry_run_stage.config = self.generate_stage.config

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_enhanced_data, f)
            temp_file = f.name

        try:
            output_path, metadata = dry_run_stage.execute(
                input_file=temp_file,
                output_dir='custom/html/dir'
            )

            assert output_path is None
            assert metadata["dry_run"] is True
            assert "custom/html/dir" in metadata["html_file"]
        finally:
            Path(temp_file).unlink()

    @patch('src.generators.templated_html_generator.TemplatedFantasyHTMLGenerator')
    def test_successful_html_generation_enhanced_data(self, mock_generator_class):
        """Test successful HTML generation from enhanced JSON data."""
        # Mock the HTML generator
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator

        # Create temporary output directory
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "html_output"

            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(self.sample_enhanced_data, f)
                temp_file = f.name

            try:
                output_path, metadata = self.generate_stage.execute(
                    input_file=temp_file,
                    output_dir=str(output_dir)
                )

                # Verify return values
                assert output_path is not None
                assert Path(output_path).parent == output_dir
                assert "fantasy_report_week_1_" in Path(output_path).name
                assert Path(output_path).suffix == ".html"

                assert metadata["week"] == 1
                assert metadata["html_file"] == output_path
                assert metadata["input_file"] == temp_file
                assert metadata["data_type"] == "enhanced"
                assert "generation_timestamp" in metadata

                # Verify HTML generator was called correctly
                mock_generator_class.assert_called_once()
                mock_generator.generate_html.assert_called_once()

                # Check that full enhanced data was passed to generator (not just current_week)
                call_args = mock_generator.generate_html.call_args
                generated_data = call_args[0][0]  # First argument
                output_file = call_args[0][1]     # Second argument

                # Should pass the full enhanced data structure
                assert generated_data == self.sample_enhanced_data
                assert output_file == output_path

            finally:
                Path(temp_file).unlink()

    @patch('src.generators.templated_html_generator.TemplatedFantasyHTMLGenerator')
    def test_successful_html_generation_raw_data(self, mock_generator_class):
        """Test successful HTML generation from raw JSON data (no season_context)."""
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "html_output"

            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(self.sample_raw_data, f)
                temp_file = f.name

            try:
                output_path, metadata = self.generate_stage.execute(
                    input_file=temp_file,
                    output_dir=str(output_dir)
                )

                # Verify return values for raw data
                assert metadata["data_type"] == "raw"

                # Check that raw data was passed directly to generator
                call_args = mock_generator.generate_html.call_args
                generated_data = call_args[0][0]
                assert generated_data == self.sample_raw_data

            finally:
                Path(temp_file).unlink()

    @patch('src.generators.templated_html_generator.TemplatedFantasyHTMLGenerator')
    def test_html_generator_error_handling(self, mock_generator_class):
        """Test handling of HTML generator errors."""
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_html.side_effect = Exception("Template rendering failed")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_enhanced_data, f)
            temp_file = f.name

        try:
            with pytest.raises(Exception, match="Template rendering failed"):
                self.generate_stage.execute(input_file=temp_file)
        finally:
            Path(temp_file).unlink()

    def test_invalid_json_file(self):
        """Test handling of invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content {")
            temp_file = f.name

        try:
            with pytest.raises(json.JSONDecodeError):
                self.generate_stage.execute(input_file=temp_file)
        finally:
            Path(temp_file).unlink()

    def test_file_not_found(self):
        """Test handling of non-existent file."""
        with pytest.raises(FileNotFoundError):
            self.generate_stage.execute(input_file="/nonexistent/file.json")

    @patch('src.generators.templated_html_generator.TemplatedFantasyHTMLGenerator')
    def test_missing_current_week_data(self, mock_generator_class):
        """Test handling of enhanced data missing current_week section."""
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator

        incomplete_enhanced_data = {
            "season_context": {},
            "metadata": {
                "league_id": 380491
            }
            # Missing "current_week" key
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(incomplete_enhanced_data, f)
            temp_file = f.name

        try:
            output_path, metadata = self.generate_stage.execute(input_file=temp_file)

            # Should handle missing current_week gracefully by passing entire data
            call_args = mock_generator.generate_html.call_args
            generated_data = call_args[0][0]
            assert generated_data == incomplete_enhanced_data
            assert metadata["week"] == "unknown"
        finally:
            Path(temp_file).unlink()

    @patch('src.generators.templated_html_generator.TemplatedFantasyHTMLGenerator')
    def test_missing_week_in_current_data(self, mock_generator_class):
        """Test handling of current_week data missing week field."""
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator

        data_missing_week = {
            "current_week": {
                "league_id": 380491,
                "league_name": "Test League"
                # Missing "week" field
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data_missing_week, f)
            temp_file = f.name

        try:
            output_path, metadata = self.generate_stage.execute(input_file=temp_file)

            # Should default week to "unknown"
            assert metadata["week"] == "unknown"
            assert "fantasy_report_week_unknown_" in Path(output_path).name
        finally:
            Path(temp_file).unlink()

    def test_default_output_directory_creation(self):
        """Test that default output directory is created."""
        dry_run_stage = GenerateStage(league_id=self.league_id, dry_run=True)
        dry_run_stage.config = self.generate_stage.config

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_enhanced_data, f)
            temp_file = f.name

        try:
            output_path, metadata = dry_run_stage.execute(input_file=temp_file)

            # Should use default output/html directory
            assert "output/html" in metadata["html_file"]
        finally:
            Path(temp_file).unlink()

    @patch('src.generators.templated_html_generator.TemplatedFantasyHTMLGenerator')
    def test_output_filename_format(self, mock_generator_class):
        """Test that output filename follows expected format."""
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test_output"

            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(self.sample_enhanced_data, f)
                temp_file = f.name

            try:
                output_path, metadata = self.generate_stage.execute(
                    input_file=temp_file,
                    output_dir=str(output_dir)
                )

                # Verify filename format: fantasy_report_week_{week}_{timestamp}.html
                filename = Path(output_path).name
                assert filename.startswith("fantasy_report_week_1_")
                assert filename.endswith(".html")

                # Verify timestamp format (should be YYYYMMDD_HHMMSS)
                timestamp_part = filename.replace("fantasy_report_week_1_", "").replace(".html", "")
                assert len(timestamp_part) == 15  # YYYYMMDD_HHMMSS format
                assert "_" in timestamp_part

            finally:
                Path(temp_file).unlink()

    @patch('src.generators.templated_html_generator.TemplatedFantasyHTMLGenerator')
    def test_generator_import_error_fallback(self, mock_generator_class):
        """Test that import fallback works correctly."""
        # This test verifies that the import error handling works
        # The actual import logic is tested through successful execution
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator

        with tempfile.TemporaryDirectory() as temp_dir:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(self.sample_enhanced_data, f)
                temp_file = f.name

            try:
                # This should work regardless of which import path succeeds
                output_path, metadata = self.generate_stage.execute(
                    input_file=temp_file,
                    output_dir=temp_dir
                )

                assert output_path is not None
                assert metadata["week"] == 1

            finally:
                Path(temp_file).unlink()

    def test_generate_enhanced_data_structure_detection(self):
        """Test that generate stage correctly detects and handles enhanced data structure."""
        # Enhanced data with season_context
        enhanced_data = {
            "current_week": {
                "league_id": 380491,
                "league_name": "Duke Football Invitational",
                "week": 1,
                "season": 2025,
                "report_date": "2025-09-17T15:32:03.569584",
                "divisions": [{"name": "Adams", "teams": []}],
                "matchups": [],
                "awards": {}  # Add awards to match expected structure
            },
            "season_context": {
                "running_totals": {
                    "1": {
                        "name": "Test Team",
                        "logo": "https://example.com/logo.png",
                        "division": "Adams",
                        "actual": 100.0,
                        "projected": 95.0,
                        "optimal": 117.6,
                        "efficiency": 85.0
                    }
                }
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(enhanced_data, f)
                temp_file = f.name

            output_path = None
            try:
                output_path, metadata = self.generate_stage.execute(
                    input_file=temp_file,
                    output_dir=temp_dir
                )

                assert output_path is not None
                assert metadata["week"] == 1
                assert metadata["data_type"] == "enhanced"
                assert Path(output_path).exists()

                # Verify HTML contains running totals table
                with open(output_path, 'r') as f:
                    html_content = f.read()

                assert "Running Totals" in html_content
                assert "Test Team" in html_content

            finally:
                Path(temp_file).unlink()
                if output_path and Path(output_path).exists():
                    Path(output_path).unlink()

    def test_generate_raw_data_structure_handling(self):
        """Test that generate stage correctly handles raw data structure without season_context."""
        # Raw data without season_context (will use fallback calculation)
        raw_data = {
            "league_id": 380491,
            "league_name": "Duke Football Invitational",
            "week": 1,
            "season": 2025,
            "report_date": "2025-09-17T15:32:03.569584",
            "divisions": [
                {
                    "name": "Adams",
                    "teams": [
                        {
                            "id": 1,
                            "name": "Test Team",
                            "logo": "https://example.com/logo.png",
                            "division": "Adams",
                            "wins": 1,
                            "losses": 0,
                            "ties": 0,
                            "points_for": 100.0,
                            "points_against": 90.0,
                            "overall_rank": 1,
                            "division_rank": 1
                        }
                    ]
                }
            ],
            "matchups": [
                {
                    "home_team": {"id": 1, "name": "Test Team"},
                    "away_team": {"id": 2, "name": "Other Team"},
                    "home_score": 100.0,
                    "away_score": 90.0,
                    "home_projected_score": 95.0,
                    "away_projected_score": 85.0,
                    "home_optimal_score": 110.0,
                    "away_optimal_score": 100.0,
                    "players": []  # Add empty players list to match expected structure
                }
            ],
            "awards": {}  # Add awards to match expected structure
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(raw_data, f)
                temp_file = f.name

            output_path = None
            try:
                output_path, metadata = self.generate_stage.execute(
                    input_file=temp_file,
                    output_dir=temp_dir
                )

                assert output_path is not None
                assert metadata["week"] == 1
                assert metadata["data_type"] == "raw"
                assert Path(output_path).exists()

                # Should still generate HTML with calculated running totals
                with open(output_path, 'r') as f:
                    html_content = f.read()

                assert "Running Totals" in html_content
                assert "Test Team" in html_content

            finally:
                Path(temp_file).unlink()
                if output_path and Path(output_path).exists():
                    Path(output_path).unlink()

    @patch('src.generators.templated_html_generator.TemplatedFantasyHTMLGenerator.generate_html')
    def test_generate_passes_full_data_structure_to_generator(self, mock_generate):
        """Test that generate stage passes the full data structure to template generator."""
        enhanced_data = {
            "current_week": {"week": 1, "league_name": "Test League"},
            "season_context": {"running_totals": {}}
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(enhanced_data, f)
            temp_file = f.name

        try:
            self.generate_stage.execute(input_file=temp_file)

            # Should call generate_html with the full enhanced data structure
            mock_generate.assert_called_once()
            call_args = mock_generate.call_args
            passed_data = call_args[0][0]  # First positional argument

            # Should pass the full enhanced data, not just current_week
            assert "current_week" in passed_data
            assert "season_context" in passed_data

        finally:
            Path(temp_file).unlink()