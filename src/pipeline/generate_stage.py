"""
Generate Stage

Stage 4: HTML Generation
Generates HTML website from enhanced JSON using existing templated HTML generator.
Outputs HTML files ready for deployment.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from .base import PipelineStage


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