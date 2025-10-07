#!/usr/bin/env python
"""
Test script for validating league history extraction.

This script allows you to test the history extractor with your real league data
without implementing the full CLI commands.

Usage:
    python test_history_extraction.py --start-year 2020 --end-year 2024
    python test_history_extraction.py --year 2024  # Single year
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from src.extractors.history_extractor import HistoryExtractor
from src.utils.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main test script."""
    parser = argparse.ArgumentParser(description='Test league history extraction')
    parser.add_argument('--start-year', type=int, help='Start year (inclusive)')
    parser.add_argument('--end-year', type=int, help='End year (inclusive)')
    parser.add_argument('--year', type=int, help='Single year to extract')
    parser.add_argument('--league-id', type=int, help='Override config league ID')
    parser.add_argument('--output-dir', default='output/history', help='Output directory')

    args = parser.parse_args()

    # Load configuration
    try:
        config = get_config()
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # Get league ID
    league_id = args.league_id or config.league.league_id
    if not league_id:
        logger.error("No league_id specified. Use --league-id or set in config.yaml")
        sys.exit(1)

    # Get ESPN credentials
    espn_s2 = config.espn.espn_s2
    swid = config.espn.swid

    if not espn_s2 or not swid:
        logger.warning("No ESPN credentials found. This will only work for public leagues.")

    # Determine year range
    if args.year:
        start_year = args.year
        end_year = args.year
        logger.info(f"Extracting single year: {args.year}")
    elif args.start_year and args.end_year:
        start_year = args.start_year
        end_year = args.end_year
        logger.info(f"Extracting year range: {start_year}-{end_year}")
    else:
        logger.error("Must specify either --year or both --start-year and --end-year")
        sys.exit(1)

    # Create extractor
    logger.info(f"Creating history extractor for league {league_id}")
    extractor = HistoryExtractor(
        league_id=league_id,
        espn_s2=espn_s2,
        swid=swid
    )

    # Extract history
    logger.info("=" * 60)
    logger.info("Starting extraction...")
    logger.info("=" * 60)

    try:
        league_history = extractor.extract_history(start_year, end_year)

        # Display summary
        logger.info("=" * 60)
        logger.info("Extraction Complete!")
        logger.info("=" * 60)
        logger.info(f"League: {league_history.league_name}")
        logger.info(f"League ID: {league_history.league_id}")
        logger.info(f"Seasons Extracted: {league_history.metadata.total_seasons}")
        logger.info(f"Year Range: {league_history.metadata.year_range}")
        logger.info("")

        # Display champion summary for each season
        if league_history.seasons:
            logger.info("Champions by Year:")
            logger.info("-" * 60)
            for season in league_history.seasons:
                logger.info(f"  {season.year}: {season.champion.team_name} "
                          f"({season.champion.owner_name}) - "
                          f"{season.champion.wins}-{season.champion.losses}, "
                          f"{season.champion.points_for:.2f} PF")
        else:
            logger.warning("No seasons were successfully extracted!")

        # Save to JSON
        logger.info("")
        logger.info("Saving to JSON...")
        filepath = extractor.save_to_json(league_history, output_dir=args.output_dir)
        logger.info(f"✓ Saved to: {filepath}")

        # Display file info
        file_size = Path(filepath).stat().st_size
        logger.info(f"  File size: {file_size:,} bytes")

        # Validate JSON can be re-loaded
        logger.info("")
        logger.info("Validating JSON file...")
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"✓ JSON is valid and contains {len(data.get('seasons', []))} seasons")

        logger.info("")
        logger.info("=" * 60)
        logger.info("SUCCESS! History extraction completed successfully.")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"Extraction failed: {e}")
        logger.error("=" * 60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
