"""
Extract Stage

Stage 1: ESPN Data Extraction
Extracts raw fantasy football data from ESPN API using existing
FantasyFootballExtractor functionality.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from .base import PipelineStage

try:
    from ..fantasy_extractor import FantasyFootballExtractor
    from ..utils.date_utils import get_nfl_week_calculator
except ImportError:
    from fantasy_extractor import FantasyFootballExtractor
    from utils.date_utils import get_nfl_week_calculator


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