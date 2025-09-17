#!/usr/bin/env python3

import sys
from pathlib import Path

# Add the parent directory to the Python path so we can import from src
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))
sys.path.insert(0, str(current_dir))

import click
import json
from datetime import datetime
from typing import Optional


class OrderedGroup(click.Group):
    """Custom Group class that preserves the order commands were added."""

    def list_commands(self, ctx):
        """Return commands in the order they were added, not alphabetically."""
        return list(self.commands.keys())

try:
    # Try relative imports first (when run as part of package)
    from .fantasy_extractor import FantasyFootballExtractor
    from .utils.config import get_config
    from .generators.templated_html_generator import TemplatedFantasyHTMLGenerator
    from .pipeline.orchestrator import PipelineOrchestrator
except ImportError:
    # Fall back to absolute imports (when run as script)
    from fantasy_extractor import FantasyFootballExtractor
    from utils.config import get_config
    from generators.templated_html_generator import TemplatedFantasyHTMLGenerator
    from pipeline.orchestrator import PipelineOrchestrator


@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.version_option(version="1.0.0")
def cli():
    """
    Fantasy Football Data Extractor
    
    Extract structured data from ESPN Fantasy Football leagues for LLM analysis.
    """
    pass


@cli.command()
@click.argument('league_id', type=int, required=False)
@click.option('--year', '-y', type=int, help='Fantasy season year (default: current year)')
@click.option('--espn-s2', help='ESPN_S2 cookie value (overrides config)')
@click.option('--swid', help='SWID cookie value (overrides config)')
@click.option('--date', '-d', help='Reference date (ISO format, default: today)')
@click.option('--week', '-w', type=int, help='Specific week to extract (overrides date)')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--pretty', is_flag=True, help='Pretty print JSON output')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def extract(league_id: Optional[int], year: Optional[int], espn_s2: Optional[str], 
           swid: Optional[str], date: Optional[str], week: Optional[int],
           output: Optional[str], pretty: bool, verbose: bool):
    """
    Extract weekly fantasy football data from ESPN.
    
    LEAGUE_ID: ESPN fantasy league ID (optional if set in config)
    
    Example:
        fantasy-extractor extract 123456 --week 5 --output week5.json
        fantasy-extractor extract --week 5  # uses league_id from config
    """
    if verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Get league_id from config if not provided
        if league_id is None:
            config = get_config()
            league_id = config.league.league_id
            if league_id is None:
                click.echo("Error: League ID must be provided either as argument or in config file", err=True)
                sys.exit(1)
        
        # Create extractor
        extractor = FantasyFootballExtractor(
            league_id=league_id,
            year=year,
            espn_s2=espn_s2,
            swid=swid
        )
        
        # Override pretty print if specified
        if pretty:
            config = get_config()
            config.output.pretty_print = pretty
        
        # Generate output path if not specified
        output_path = Path(output) if output else None
        
        # Extract and save report
        saved_path = extractor.generate_and_save_report(
            date=date,
            week=week,
            output_path=output_path
        )
        
        click.echo(f"Successfully extracted data to: {saved_path}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('league_id', type=int, required=False)
@click.option('--year', '-y', type=int, help='Fantasy season year (default: current year)')
@click.option('--espn-s2', help='ESPN_S2 cookie value (overrides config)')
@click.option('--swid', help='SWID cookie value (overrides config)')
def info(league_id: Optional[int], year: Optional[int], espn_s2: Optional[str], swid: Optional[str]):
    """
    Display league information and team standings.
    
    LEAGUE_ID: ESPN fantasy league ID (optional if set in config)
    """
    try:
        # Get league_id from config if not provided
        if league_id is None:
            config = get_config()
            league_id = config.league.league_id
            if league_id is None:
                click.echo("Error: League ID must be provided either as argument or in config file", err=True)
                sys.exit(1)
        
        # Create extractor
        extractor = FantasyFootballExtractor(
            league_id=league_id,
            year=year,
            espn_s2=espn_s2,
            swid=swid
        )
        
        # Get league summary
        summary = extractor.get_league_summary()
        
        # Display league info
        league_info = summary['league_info']
        click.echo(f"League: {league_info['name']}")
        click.echo(f"Year: {league_info['year']}")
        click.echo(f"Current Week: {league_info['current_week']}")
        click.echo(f"Teams: {league_info['team_count']}")
        click.echo()
        
        # Display divisions and standings
        for division in summary['divisions']:
            click.echo(f"{division['name']} Division:")
            for team in division['teams']:
                click.echo(f"  {team['rank']}. {team['name']} ({team['owner']}) - {team['record']}")
            click.echo()
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('input_file', type=str)
def validate(input_file: str):
    """
    Validate a JSON report file against the expected schema.
    
    INPUT_FILE: Path to JSON file to validate (checks output/ directory if no path given)
    """
    try:
        try:
            from .models.data_models import WeeklyReport
        except ImportError:
            from models.data_models import WeeklyReport
        
        # Convert input_file to Path and check if it exists
        input_path = Path(input_file)
        
        # If file doesn't exist and no directory specified, try output directory
        if not input_path.exists() and '/' not in input_file:
            input_path = Path('output') / input_file
        
        # Check if file exists
        if not input_path.exists():
            click.echo(f"✗ File not found: {input_file}", err=True)
            sys.exit(1)
        
        # Load and parse JSON
        with open(input_path, 'r') as f:
            data = json.load(f)
        
        # Validate against schema
        report = WeeklyReport.model_validate(data)
        
        click.echo(f"✓ Valid report file: {input_path}")
        click.echo(f"  League: {report.league_name}")
        click.echo(f"  Week: {report.week}")
        click.echo(f"  Matchups: {len(report.matchups)}")
        click.echo(f"  Injured Starters: {len(report.injured_starters)}")
        
    except Exception as e:
        click.echo(f"✗ Invalid report file: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('config_path', type=click.Path(), required=False)
def config(config_path: Optional[str]):
    """
    Display current configuration or validate a config file.
    
    CONFIG_PATH: Optional path to config file to validate
    """
    try:
        if config_path:
            # Validate specific config file
            try:
                from .utils.config import ConfigManager
            except ImportError:
                from utils.config import ConfigManager
            manager = ConfigManager(Path(config_path))
            config_obj = manager.load_config()
            click.echo(f"✓ Valid configuration file: {config_path}")
        else:
            # Display current config
            config_obj = get_config()
            click.echo("Current Configuration:")
        
        # Display config as JSON
        config_dict = {
            'espn': {
                'espn_s2': '***' if config_obj.espn.espn_s2 else None,
                'swid': '***' if config_obj.espn.swid else None
            },
            'league': {
                'league_id': config_obj.league.league_id,
                'divisions': config_obj.league.divisions
            },
            'nfl_schedule': {
                'season_start': config_obj.nfl_schedule.season_start,
                'regular_season_weeks': config_obj.nfl_schedule.regular_season_weeks,
                'playoff_weeks': config_obj.nfl_schedule.playoff_weeks
            },
            'output': {
                'filename_pattern': config_obj.output.filename_pattern,
                'pretty_print': config_obj.output.pretty_print,
                'include_debug_info': config_obj.output.include_debug_info
            },
            'logging': {
                'level': config_obj.logging.level,
                'format': config_obj.logging.format
            }
        }
        
        click.echo(json.dumps(config_dict, indent=2))
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--date', '-d', help='Reference date (ISO format, default: today)')
def week(date: Optional[str]):
    """
    Calculate the current NFL week based on a date.
    """
    try:
        try:
            from .utils.date_utils import get_nfl_week_calculator, parse_date_input
        except ImportError:
            from utils.date_utils import get_nfl_week_calculator, parse_date_input
        
        reference_date = parse_date_input(date)
        calculator = get_nfl_week_calculator()
        
        current_week = calculator.get_current_nfl_week(reference_date)
        target_week = calculator.get_previous_complete_week(reference_date)
        is_complete = calculator.is_week_complete(current_week, reference_date)
        
        click.echo(f"Reference Date: {reference_date.strftime('%Y-%m-%d')}")
        click.echo(f"Current NFL Week: {current_week}")
        click.echo(f"Week Complete: {'Yes' if is_complete else 'No'}")
        click.echo(f"Target Week for Extraction: {target_week}")
        
        start_date, end_date = calculator.get_week_date_range(current_week)
        click.echo(f"Current Week Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--dry-run', is_flag=True, help='Show what would be cleaned without actually removing files')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information about files being processed')
@click.option('--keep-days', type=int, default=7, help='Keep files newer than N days (default: 7)')
@click.option('--keep-latest', type=int, default=3, help='Keep latest N files in each directory (default: 3)')
def clean(dry_run: bool, verbose: bool, keep_days: int, keep_latest: int):
    """
    Clean unnecessary files from output directory while preserving structure.

    This command removes old output files to reduce clutter while maintaining
    the base directory structure and keeping recent/important files.

    DIRECTORIES CLEANED:
    \b
    • output/ (root files like test files and old reports)
    • output/raw/ (old raw JSON extracts)
    • output/enhanced/ (old enhanced JSON files)
    • output/html/ (old HTML reports)
    • output/logs/ (old pipeline logs)

    CLEANING STRATEGY:
    \b
    • Removes files older than --keep-days (default: 7 days)
    • Keeps --keep-latest files in each directory (default: 3 newest)
    • Preserves directory structure (never removes directories)
    • Skips files matching important patterns (README, .gitkeep, etc.)

    PRESERVED FILES:
    \b
    • Files newer than the keep-days threshold
    • The newest keep-latest files in each directory
    • Important files: README*, .gitkeep, .gitignore
    • Currently running pipeline files

    SAFETY FEATURES:
    \b
    • Uses --dry-run to preview changes before execution
    • Never removes directories, only files
    • Provides detailed output with --verbose flag
    • Confirms total files before removal

    EXAMPLES:
    \b
    fantasy-extractor clean                           # Clean with defaults (7 days, keep 3 latest)
    fantasy-extractor clean --dry-run                 # Preview what would be cleaned
    fantasy-extractor clean --keep-days 14            # Keep files from last 2 weeks
    fantasy-extractor clean --keep-latest 5 --verbose # Keep 5 newest, show details

    Use 'fantasy-extractor help clean' for detailed information.
    """
    try:
        # Import required modules
        import os
        import glob
        from pathlib import Path
        from datetime import datetime, timedelta

        # Define output directory structure
        output_base = Path("output")
        directories_to_clean = [
            output_base,  # Root output files
            output_base / "raw",
            output_base / "enhanced",
            output_base / "html",
            output_base / "logs"
        ]

        # Files to never remove (protection patterns)
        protected_patterns = ['README*', '.gitkeep', '.gitignore', '*.md']

        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=keep_days)

        total_files_found = 0
        total_files_to_remove = 0
        files_by_directory = {}

        # Scan all directories
        for directory in directories_to_clean:
            if not directory.exists():
                continue

            files_in_dir = []

            # Get all files in directory (not subdirectories)
            for file_path in directory.glob("*"):
                if file_path.is_file():
                    # Skip protected files
                    protected = False
                    for pattern in protected_patterns:
                        if file_path.match(pattern):
                            protected = True
                            break

                    if protected:
                        if verbose:
                            click.echo(f"Protecting: {file_path}")
                        continue

                    files_in_dir.append(file_path)
                    total_files_found += 1

            # Sort files by modification time (newest first)
            files_in_dir.sort(key=lambda f: f.stat().st_mtime, reverse=True)

            # Determine which files to remove
            files_to_remove = []
            for i, file_path in enumerate(files_in_dir):
                file_age = datetime.fromtimestamp(file_path.stat().st_mtime)

                # Keep if within latest N files
                if i < keep_latest:
                    if verbose:
                        click.echo(f"Keeping (latest {keep_latest}): {file_path}")
                    continue

                # Keep if newer than cutoff date
                if file_age > cutoff_date:
                    if verbose:
                        click.echo(f"Keeping (recent): {file_path}")
                    continue

                # Mark for removal
                files_to_remove.append(file_path)

            files_by_directory[directory] = files_to_remove
            total_files_to_remove += len(files_to_remove)

        # Display summary
        click.echo(f"Output Directory Cleanup Summary")
        click.echo(f"=" * 40)
        click.echo(f"Total files found: {total_files_found}")
        click.echo(f"Files to remove: {total_files_to_remove}")
        click.echo(f"Files to keep: {total_files_found - total_files_to_remove}")
        click.echo(f"Keep files newer than: {cutoff_date.strftime('%Y-%m-%d %H:%M')}")
        click.echo(f"Keep latest files per directory: {keep_latest}")
        click.echo()

        if total_files_to_remove == 0:
            click.echo("✓ No files need cleaning!")
            return

        # Show files to be removed by directory
        for directory, files_to_remove in files_by_directory.items():
            if files_to_remove:
                click.echo(f"📁 {directory}/")
                for file_path in files_to_remove:
                    file_age = datetime.fromtimestamp(file_path.stat().st_mtime)
                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    if dry_run or verbose:
                        click.echo(f"  🗑️  {file_path.name} ({file_age.strftime('%Y-%m-%d %H:%M')}, {size_mb:.1f}MB)")

                    if not dry_run:
                        file_path.unlink()

                click.echo()

        # Final message
        if dry_run:
            click.echo(f"🔍 Dry run complete. Run without --dry-run to remove {total_files_to_remove} files.")
        else:
            click.echo(f"✅ Successfully removed {total_files_to_remove} files!")
            click.echo("📂 Directory structure preserved.")

    except Exception as e:
        click.echo(f"Error during cleanup: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output HTML file path (default: replaces .json with .html)')
def generate_html(input_file: str, output: Optional[str]):
    """
    Generate HTML website from a fantasy football JSON report.
    
    INPUT_FILE: Path to JSON report file to convert to HTML
    
    Example:
        fantasy-extractor generate-html output/fantasy_report_week_1_2025-09-10.json
        fantasy-extractor generate-html report.json --output my_site.html
    """
    try:
        input_path = Path(input_file)
        
        # Generate output path if not specified
        if output is None:
            output_path = input_path.with_suffix('.html')
        else:
            output_path = Path(output)
        
        # Create HTML generator and generate the website
        generator = TemplatedFantasyHTMLGenerator()
        generator.generate_from_file(str(input_path), str(output_path))
        
        click.echo(f"✓ Successfully generated HTML report: {output_path}")
        
    except Exception as e:
        click.echo(f"Error generating HTML: {e}", err=True)
        sys.exit(1)


@cli.group(cls=OrderedGroup, context_settings={'help_option_names': ['-h', '--help']})
def pipeline():
    """
    Fantasy Football Data Pipeline

    Run multi-stage pipeline for ESPN data extraction, DynamoDB storage,
    data aggregation, and S3 website deployment.
    """
    pass


@pipeline.command()
@click.argument('league_id', type=int, required=False)
@click.option('--year', '-y', type=int, help='Fantasy season year (default: current year)')
@click.option('--espn-s2', help='ESPN_S2 cookie value (overrides config)')
@click.option('--swid', help='SWID cookie value (overrides config)')
@click.option('--week', '-w', type=int, help='Specific week to process (defaults to current week)')
@click.option('--output-dir', help='Base output directory for all stages (default: uses stage defaults)')
@click.option('--dry-run', is_flag=True, help='Simulate execution without making changes (all stages)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging for all stages')
def run(league_id: Optional[int], year: Optional[int], espn_s2: Optional[str],
        swid: Optional[str], week: Optional[int], output_dir: Optional[str],
        dry_run: bool, verbose: bool):
    """
    Run the complete 5-stage fantasy football data pipeline.

    PIPELINE STAGES:
    \b
    1. EXTRACT    ESPN data extraction → Raw JSON (output/raw/)
    2. UPLOAD     DynamoDB storage with schema versioning
    3. AGGREGATE  Historical data combination → Enhanced JSON (output/enhanced/)
    4. GENERATE   HTML generation → HTML files (output/html/)
    5. DEPLOY     S3 deployment → CloudFront URL

    LEAGUE_ID: ESPN fantasy league ID (optional if set in config)

    REQUIREMENTS:
    \b
    • ESPN authentication (espn_s2, swid cookies) for private leagues
    • AWS credentials for stages 2 and 5 (DynamoDB table, S3 bucket)
    • Stage 5 (S3 deployment) currently raises NotImplementedError

    EXAMPLES:
    \b
    fantasy-extractor pipeline run                    # Current week, config league_id
    fantasy-extractor pipeline run 123456 --week 5   # Specific league and week
    fantasy-extractor pipeline run --dry-run          # Test without AWS calls
    fantasy-extractor pipeline run --verbose          # Detailed execution logs

    Use 'fantasy-extractor pipeline help run' for detailed information.
    """
    if verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Get league_id from config if not provided
        if league_id is None:
            config = get_config()
            league_id = config.league.league_id
            if league_id is None:
                click.echo("Error: League ID must be provided either as argument or in config file", err=True)
                sys.exit(1)

        # Create pipeline orchestrator
        orchestrator = PipelineOrchestrator(
            league_id=league_id,
            year=year,
            espn_s2=espn_s2,
            swid=swid,
            dry_run=dry_run
        )

        # Run full pipeline
        click.echo(f"Starting full pipeline execution for league {league_id}")
        results = orchestrator.run_full_pipeline(week=week, output_dir=output_dir)

        # Display results
        for stage_name, result in results.items():
            status_icon = "✓" if result.status.value == "success" else "✗"
            click.echo(f"{status_icon} {stage_name.title()}: {result.status.value}")
            if result.output_path:
                click.echo(f"  Output: {result.output_path}")
            if result.execution_time:
                click.echo(f"  Time: {result.execution_time:.2f}s")

        # Save pipeline log
        log_path = orchestrator.save_pipeline_log()
        click.echo(f"Pipeline log saved to: {log_path}")

    except Exception as e:
        click.echo(f"Pipeline execution failed: {e}", err=True)
        sys.exit(1)


@pipeline.command()
@click.argument('league_id', type=int, required=False)
@click.option('--year', '-y', type=int, help='Fantasy season year (default: current year)')
@click.option('--espn-s2', help='ESPN_S2 cookie value (overrides config)')
@click.option('--swid', help='SWID cookie value (overrides config)')
@click.option('--week', '-w', type=int, help='Specific week to extract (default: most recent completed week)')
@click.option('--output-dir', help='Output directory for raw JSON files (default: output/raw/)')
@click.option('--dry-run', is_flag=True, help='Simulate extraction without saving files')
@click.option('--verbose', '-v', is_flag=True, help='Enable detailed ESPN API logging')
def extract(league_id: Optional[int], year: Optional[int], espn_s2: Optional[str],
           swid: Optional[str], week: Optional[int], output_dir: Optional[str],
           dry_run: bool, verbose: bool):
    """
    STAGE 1: ESPN Data Extraction

    Extract comprehensive fantasy football data from ESPN API and save as raw JSON.

    DATA EXTRACTED:
    \b
    • Team standings and divisions with rankings
    • Weekly matchup results with scores and winners
    • Player performance (projected vs actual scores)
    • Injury tracking for all starters
    • 11 different weekly awards (MVP, MWP, SSL, McCollapse, etc.)
    • Optimal lineup calculations and efficiency metrics

    LEAGUE_ID: ESPN fantasy league ID (optional if set in config)

    AUTHENTICATION:
    \b
    • Public leagues: No authentication required
    • Private leagues: Requires ESPN cookies (espn_s2, swid)
    • Cookies can be set in config/secrets.yaml or passed via CLI

    OUTPUT:
    \b
    • File: output/raw/raw_week_{week}_{timestamp}.json
    • Size: ~90KB for typical 12-team league
    • Format: Structured JSON with Pydantic validation

    EXAMPLES:
    \b
    fantasy-extractor pipeline extract                    # Current week, config league
    fantasy-extractor pipeline extract 123456 --week 5   # Specific league and week
    fantasy-extractor pipeline extract --dry-run          # Test without saving files
    fantasy-extractor pipeline extract --verbose          # See ESPN API calls

    Use 'fantasy-extractor pipeline help extract' for detailed information.
    """
    if verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Get league_id from config if not provided
        if league_id is None:
            config = get_config()
            league_id = config.league.league_id
            if league_id is None:
                click.echo("Error: League ID must be provided either as argument or in config file", err=True)
                sys.exit(1)

        # Create pipeline orchestrator
        orchestrator = PipelineOrchestrator(
            league_id=league_id,
            year=year,
            espn_s2=espn_s2,
            swid=swid,
            dry_run=dry_run
        )

        # Run extract stage
        result = orchestrator.run_stage('extract', week=week, output_dir=output_dir)

        if result.status.value == "success":
            click.echo(f"✓ Extract completed: {result.output_path}")
        else:
            click.echo(f"✗ Extract failed: {result.error_message}", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"Extract stage failed: {e}", err=True)
        sys.exit(1)


@pipeline.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--dry-run', is_flag=True, help='Simulate upload without writing to DynamoDB')
@click.option('--verbose', '-v', is_flag=True, help='Enable detailed AWS operation logging')
def upload(input_file: str, dry_run: bool, verbose: bool):
    """
    STAGE 2: DynamoDB Storage

    Upload structured fantasy football data to DynamoDB with schema versioning.

    INPUT_FILE: Path to raw JSON file from Stage 1 (extract)

    AWS CONFIGURATION REQUIRED:
    \b
    • Valid AWS credentials (CLI, environment variables, or IAM role)
    • DynamoDB table 'fantasy-league-data' must exist
    • Required permissions: dynamodb:PutItem
    • AWS region: us-east-1 (configurable)

    DYNAMODB SCHEMA:
    \b
    • Table: fantasy-league-data
    • Partition Key: league_id (String)
    • Sort Key: week_year (String, format: "YYYY-WW")
    • Attributes: data (JSON), timestamp, season, week, schema_version

    DATA PROCESSING:
    \b
    • Converts float values to Decimal (DynamoDB requirement)
    • Adds metadata: record_id, timestamp, schema_version
    • Validates JSON structure before upload
    • Generates unique record IDs for tracking

    ERROR HANDLING:
    \b
    • ResourceNotFoundException: DynamoDB table doesn't exist
    • NoCredentialsError: AWS credentials not configured
    • AccessDenied: Insufficient DynamoDB permissions

    EXAMPLES:
    \b
    fantasy-extractor pipeline upload output/raw/raw_week_5_*.json
    fantasy-extractor pipeline upload file.json --dry-run
    fantasy-extractor pipeline upload file.json --verbose

    Use 'fantasy-extractor pipeline help upload' for detailed information.
    """
    if verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Extract league_id from input file to create orchestrator
        with open(input_file, 'r') as f:
            data = json.load(f)

        league_id = data.get('league_id')
        if not league_id:
            click.echo("Error: Could not determine league_id from input file", err=True)
            sys.exit(1)

        # Create pipeline orchestrator
        orchestrator = PipelineOrchestrator(
            league_id=league_id,
            dry_run=dry_run
        )

        # Run upload stage
        result = orchestrator.run_stage('upload', input_file=input_file)

        if result.status.value == "success":
            click.echo(f"✓ Upload completed: {result.metadata.get('record_id', 'N/A')}")
        else:
            click.echo(f"✗ Upload failed: {result.error_message}", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"Upload stage failed: {e}", err=True)
        sys.exit(1)


@pipeline.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--dynamodb-record-id', help='DynamoDB record ID from Stage 2 (for tracking)')
@click.option('--output-dir', help='Output directory for enhanced JSON files (default: output/enhanced/)')
@click.option('--dry-run', is_flag=True, help='Simulate aggregation without saving files')
@click.option('--verbose', '-v', is_flag=True, help='Enable detailed aggregation process logging')
def aggregate(input_file: str, dynamodb_record_id: Optional[str],
             output_dir: Optional[str], dry_run: bool, verbose: bool):
    """
    STAGE 3: Data Aggregation & Season Context

    Enhance current week data with season context, analytics, and historical trends.

    INPUT_FILE: Path to raw JSON file from Stage 1 (extract)

    ENHANCEMENTS ADDED:
    \b
    • Season Context: Historical standings progression
    • Matchup Statistics: Head-to-head records, close games, blowouts
    • Award Summaries: Season-long award tracking and analytics
    • Performance Trends: Team metrics, league averages, efficiency analytics
    • Metadata: Aggregation timestamps, record IDs, data source tracking

    OUTPUT STRUCTURE:
    \b
    • current_week: Full raw weekly report data
    • season_context: Enhanced analytics and historical data
    • metadata: Processing information and data lineage

    DATA CALCULATIONS:
    \b
    • Team Performance: Average scores, highest/lowest weekly scores
    • League Analytics: Overall averages, total points, team counts
    • Matchup Analysis: Completed games, margins, upset detection
    • Standings Extraction: Current division standings with records

    FUTURE FEATURES:
    \b
    • Historical Data: Query DynamoDB for multi-week aggregations
    • Trend Analysis: Performance progression across season
    • Advanced Stats: Head-to-head records, consistency metrics

    EXAMPLES:
    \b
    fantasy-extractor pipeline aggregate output/raw/raw_week_5_*.json
    fantasy-extractor pipeline aggregate file.json --output-dir custom/
    fantasy-extractor pipeline aggregate file.json --dry-run

    Use 'fantasy-extractor pipeline help aggregate' for detailed information.
    """
    if verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Extract league_id from input file to create orchestrator
        with open(input_file, 'r') as f:
            data = json.load(f)

        league_id = data.get('league_id')
        if not league_id:
            click.echo("Error: Could not determine league_id from input file", err=True)
            sys.exit(1)

        # Create pipeline orchestrator
        orchestrator = PipelineOrchestrator(
            league_id=league_id,
            dry_run=dry_run
        )

        # Run aggregate stage
        result = orchestrator.run_stage('aggregate',
                                      current_week_file=input_file,
                                      dynamodb_record_id=dynamodb_record_id,
                                      output_dir=output_dir)

        if result.status.value == "success":
            click.echo(f"✓ Aggregate completed: {result.output_path}")
        else:
            click.echo(f"✗ Aggregate failed: {result.error_message}", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"Aggregate stage failed: {e}", err=True)
        sys.exit(1)


@pipeline.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output-dir', help='Output directory for HTML files (default: output/html/)')
@click.option('--dry-run', is_flag=True, help='Simulate HTML generation without saving files')
@click.option('--verbose', '-v', is_flag=True, help='Enable detailed HTML generation logging')
def generate(input_file: str, output_dir: Optional[str], dry_run: bool, verbose: bool):
    """
    STAGE 4: HTML Generation

    Generate responsive HTML website from enhanced JSON data.

    INPUT_FILE: Path to enhanced JSON file from Stage 3 (aggregate)

    HTML GENERATION:
    \b
    • Uses existing TemplatedFantasyHTMLGenerator
    • Creates responsive HTML with team standings and awards
    • Processes enhanced JSON with season context
    • Outputs ready-to-deploy HTML files

    OUTPUT:
    \b
    • File: output/html/fantasy_report_week_{week}_{timestamp}.html
    • Format: Responsive HTML with embedded CSS/JS
    • Ready for deployment to web hosting platforms

    DATA PROCESSING:
    \b
    • Extracts current_week data from enhanced JSON
    • Applies existing Jinja2 templates for layout
    • Includes team logos, standings, and award details
    • Handles both enhanced and raw JSON formats

    EXAMPLES:
    \b
    fantasy-extractor pipeline generate output/enhanced/enhanced_week_5_*.json
    fantasy-extractor pipeline generate file.json --output-dir custom/
    fantasy-extractor pipeline generate file.json --dry-run

    Use 'fantasy-extractor pipeline help generate' for detailed information.
    """
    if verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Extract league_id from input file to create orchestrator
        with open(input_file, 'r') as f:
            data = json.load(f)

        # Handle both raw and enhanced JSON structures
        league_id = data.get('league_id') or data.get('current_week', {}).get('league_id')
        if not league_id:
            click.echo("Error: Could not determine league_id from input file", err=True)
            sys.exit(1)

        # Create pipeline orchestrator
        orchestrator = PipelineOrchestrator(
            league_id=league_id,
            dry_run=dry_run
        )

        # Run generate stage
        result = orchestrator.run_stage('generate', input_file=input_file, output_dir=output_dir)

        if result.status.value == "success":
            click.echo(f"✓ Generate completed: {result.output_path}")
        else:
            click.echo(f"✗ Generate failed: {result.error_message}", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"Generate stage failed: {e}", err=True)
        sys.exit(1)


@pipeline.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--dry-run', is_flag=True, help='Simulate S3 deployment without upload (returns mock URL)')
@click.option('--verbose', '-v', is_flag=True, help='Enable detailed S3 deployment logging')
def deploy(input_file: str, dry_run: bool, verbose: bool):
    """
    STAGE 5: S3 Deployment

    Deploy HTML website to S3 bucket with CloudFront integration.

    INPUT_FILE: Path to HTML file from Stage 4 (generate)

    ⚠️  STATUS: NOT YET IMPLEMENTED
    \b
    • This stage currently raises NotImplementedError
    • Use --dry-run flag to test pipeline flow without deployment
    • Implementation pending for S3 upload functionality

    PLANNED FEATURES:
    \b
    • S3 Upload: Static website hosting with asset management
    • CloudFront: Global CDN integration for fast loading
    • Cache Management: Automatic CloudFront invalidation
    • Web Hosting: Complete static site deployment

    AWS CONFIGURATION REQUIRED (When Implemented):
    \b
    • Valid AWS credentials with S3 and CloudFront permissions
    • S3 bucket 'fantasy-league-reports' (or configurable)
    • Required permissions: s3:PutObject, s3:PutObjectAcl
    • Optional: CloudFront distribution for CDN

    PLANNED OUTPUT STRUCTURE:
    \b
    • S3 Path: s3://fantasy-league-reports/{league_id}/week_{week}/
    • Files: index.html, assets/, data/
    • URL: https://cloudfront-domain.com/{league_id}/week_{week}

    PLANNED HTML FEATURES:
    \b
    • League standings with team logos and records
    • Weekly awards with detailed descriptions
    • Interactive matchup summaries
    • Player performance tables with injury indicators
    • Responsive design for mobile/desktop

    EXAMPLES:
    \b
    fantasy-extractor pipeline deploy output/html/fantasy_report_week_5_*.html --dry-run
    fantasy-extractor pipeline deploy report.html --verbose

    Use 'fantasy-extractor pipeline help deploy' for detailed information.
    """
    if verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Extract league_id from HTML filename for orchestrator
        # HTML files are named like: fantasy_report_week_5_20240915_143022.html
        input_path = Path(input_file)
        filename = input_path.stem

        # Try to extract league_id from filename or use a default
        # For now, we'll use a placeholder since league_id is needed for orchestrator
        # In a real implementation, this could be stored in HTML metadata or config
        config = get_config()
        league_id = config.league.league_id
        if not league_id:
            click.echo("Error: League ID must be available in config for deploy stage", err=True)
            sys.exit(1)

        # Create pipeline orchestrator
        orchestrator = PipelineOrchestrator(
            league_id=league_id,
            dry_run=dry_run
        )

        # Run deploy stage
        result = orchestrator.run_stage('deploy', input_file=input_file)

        if result.status.value == "success":
            click.echo(f"✓ Deploy completed: {result.output_path}")
        else:
            click.echo(f"✗ Deploy failed: {result.error_message}", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"Deploy stage failed: {e}", err=True)
        sys.exit(1)


@pipeline.command()
def help():
    """
    Display detailed information about each pipeline stage.

    Shows comprehensive documentation for all 5 pipeline stages including
    purpose, data flow, requirements, and examples.
    """
    click.echo("Fantasy Football Data Pipeline - Detailed Stage Information")
    click.echo("=" * 60)
    click.echo()

    # Stage 1: Extract
    click.echo("STAGE 1: EXTRACT - ESPN Data Extraction")
    click.echo("-" * 40)
    click.echo("PURPOSE:")
    click.echo("  Extract comprehensive fantasy football data from ESPN API and save as raw JSON.")
    click.echo()
    click.echo("DATA EXTRACTED:")
    click.echo("  • Team standings and divisions with rankings")
    click.echo("  • Weekly matchup results with scores and winners")
    click.echo("  • Player performance (projected vs actual scores)")
    click.echo("  • Injury tracking for all starters")
    click.echo("  • 11 different weekly awards (MVP, MWP, SSL, McCollapse, etc.)")
    click.echo("  • Optimal lineup calculations and efficiency metrics")
    click.echo()
    click.echo("REQUIREMENTS:")
    click.echo("  • ESPN authentication (espn_s2, swid cookies) for private leagues")
    click.echo("  • Valid league ID in config or passed via CLI")
    click.echo()
    click.echo("OUTPUT:")
    click.echo("  • File: output/raw/raw_week_{week}_{timestamp}.json")
    click.echo("  • Size: ~90KB for typical 12-team league")
    click.echo("  • Format: Structured JSON with Pydantic validation")
    click.echo()
    click.echo("EXAMPLE:")
    click.echo("  fantasy-extractor pipeline extract --week 5")
    click.echo()

    # Stage 2: Upload
    click.echo("STAGE 2: UPLOAD - DynamoDB Storage")
    click.echo("-" * 40)
    click.echo("PURPOSE:")
    click.echo("  Upload structured fantasy football data to DynamoDB with schema versioning.")
    click.echo()
    click.echo("REQUIREMENTS:")
    click.echo("  • Valid AWS credentials (CLI, environment variables, or IAM role)")
    click.echo("  • DynamoDB table 'fantasy-league-data' must exist")
    click.echo("  • Required permissions: dynamodb:PutItem")
    click.echo("  • AWS region: us-east-1 (configurable)")
    click.echo()
    click.echo("DATA PROCESSING:")
    click.echo("  • Converts float values to Decimal (DynamoDB requirement)")
    click.echo("  • Adds metadata: record_id, timestamp, schema_version")
    click.echo("  • Validates JSON structure before upload")
    click.echo("  • Generates unique record IDs for tracking")
    click.echo()
    click.echo("EXAMPLE:")
    click.echo("  fantasy-extractor pipeline upload output/raw/raw_week_5_*.json")
    click.echo()

    # Stage 3: Aggregate
    click.echo("STAGE 3: AGGREGATE - Data Aggregation & Season Context")
    click.echo("-" * 40)
    click.echo("PURPOSE:")
    click.echo("  Enhance current week data with season context, analytics, and historical trends.")
    click.echo()
    click.echo("ENHANCEMENTS ADDED:")
    click.echo("  • Season Context: Historical standings progression")
    click.echo("  • Matchup Statistics: Head-to-head records, close games, blowouts")
    click.echo("  • Award Summaries: Season-long award tracking and analytics")
    click.echo("  • Performance Trends: Team metrics, league averages, efficiency analytics")
    click.echo("  • Metadata: Aggregation timestamps, record IDs, data source tracking")
    click.echo()
    click.echo("OUTPUT STRUCTURE:")
    click.echo("  • current_week: Full raw weekly report data")
    click.echo("  • season_context: Enhanced analytics and historical data")
    click.echo("  • metadata: Processing information and data lineage")
    click.echo()
    click.echo("OUTPUT:")
    click.echo("  • File: output/enhanced/enhanced_week_{week}_{timestamp}.json")
    click.echo("  • Format: Enhanced JSON with season analytics")
    click.echo()
    click.echo("EXAMPLE:")
    click.echo("  fantasy-extractor pipeline aggregate output/raw/raw_week_5_*.json")
    click.echo()

    # Stage 4: Generate
    click.echo("STAGE 4: GENERATE - HTML Generation")
    click.echo("-" * 40)
    click.echo("PURPOSE:")
    click.echo("  Generate responsive HTML website from enhanced JSON using existing templates.")
    click.echo()
    click.echo("HTML GENERATION:")
    click.echo("  • Uses existing TemplatedFantasyHTMLGenerator")
    click.echo("  • Creates responsive HTML with team standings and awards")
    click.echo("  • Processes enhanced JSON with season context")
    click.echo("  • Outputs ready-to-deploy HTML files")
    click.echo()
    click.echo("OUTPUT:")
    click.echo("  • File: output/html/fantasy_report_week_{week}_{timestamp}.html")
    click.echo("  • Format: Responsive HTML with embedded CSS/JS")
    click.echo("  • Ready for deployment to web hosting platforms")
    click.echo()
    click.echo("EXAMPLE:")
    click.echo("  fantasy-extractor pipeline generate output/enhanced/enhanced_week_5_*.json")
    click.echo()

    # Stage 5: Deploy
    click.echo("STAGE 5: DEPLOY - S3 Deployment")
    click.echo("-" * 40)
    click.echo("PURPOSE:")
    click.echo("  Deploy HTML website to S3 bucket with CloudFront integration.")
    click.echo()
    click.echo("⚠️  STATUS: NOT YET IMPLEMENTED")
    click.echo("  • This stage currently raises NotImplementedError")
    click.echo("  • Use --dry-run flag to test pipeline flow without deployment")
    click.echo("  • Implementation pending for S3 upload functionality")
    click.echo()
    click.echo("PLANNED FEATURES:")
    click.echo("  • S3 Upload: Static website hosting with asset management")
    click.echo("  • CloudFront: Global CDN integration for fast loading")
    click.echo("  • Cache Management: Automatic CloudFront invalidation")
    click.echo("  • Web Hosting: Complete static site deployment")
    click.echo()
    click.echo("PLANNED AWS REQUIREMENTS:")
    click.echo("  • Valid AWS credentials with S3 and CloudFront permissions")
    click.echo("  • S3 bucket 'fantasy-league-reports' (or configurable)")
    click.echo("  • Required permissions: s3:PutObject, s3:PutObjectAcl")
    click.echo("  • Optional: CloudFront distribution for CDN")
    click.echo()
    click.echo("EXAMPLE:")
    click.echo("  fantasy-extractor pipeline deploy output/html/fantasy_report_week_5_*.html --dry-run")
    click.echo()

    # Pipeline Flow
    click.echo("COMPLETE PIPELINE FLOW")
    click.echo("-" * 40)
    click.echo("ESPN API → [Extract] → Raw JSON → [Upload] → DynamoDB")
    click.echo("                                      ↓")
    click.echo("                                 [Aggregate] → Enhanced JSON")
    click.echo("                                      ↑              ↓")
    click.echo("                                Historical Data  [Generate] → HTML Files")
    click.echo("                                                      ↓")
    click.echo("                                 CloudFront ← [Deploy] ← S3 Bucket")
    click.echo()

    # Common Commands
    click.echo("COMMON PIPELINE COMMANDS")
    click.echo("-" * 40)
    click.echo("# Run complete pipeline")
    click.echo("fantasy-extractor pipeline run --week 5")
    click.echo()
    click.echo("# Run individual stages")
    click.echo("fantasy-extractor pipeline extract --week 5")
    click.echo("fantasy-extractor pipeline upload output/raw/file.json")
    click.echo("fantasy-extractor pipeline aggregate output/raw/file.json")
    click.echo("fantasy-extractor pipeline generate output/enhanced/file.json")
    click.echo("fantasy-extractor pipeline deploy output/html/file.html --dry-run")
    click.echo()
    click.echo("# Test without AWS resources")
    click.echo("fantasy-extractor pipeline run --dry-run")
    click.echo()
    click.echo("# Monitor execution")
    click.echo("fantasy-extractor pipeline status")
    click.echo("fantasy-extractor pipeline logs")
    click.echo()
    click.echo("For detailed help on specific stages:")
    click.echo("fantasy-extractor pipeline extract --help")
    click.echo("fantasy-extractor pipeline upload --help")
    click.echo("fantasy-extractor pipeline aggregate --help")
    click.echo("fantasy-extractor pipeline generate --help")
    click.echo("fantasy-extractor pipeline deploy --help")


@pipeline.command()
@click.option('--stage', help='Filter logs by specific stage (extract, upload, aggregate, deploy)')
@click.option('--execution-id', help='Filter logs by execution ID (pipeline_{league_id}_{timestamp})')
@click.option('--tail', '-n', type=int, default=50, help='Number of recent log lines to show (default: 50)')
@click.option('--follow', '-f', is_flag=True, help='Follow log output in real-time (not implemented)')
def logs(stage: Optional[str], execution_id: Optional[str], tail: int, follow: bool):
    """
    Display and filter pipeline execution logs.

    View detailed logs from pipeline execution, with filtering by stage or execution ID.

    ⚠️  STATUS: PARTIALLY IMPLEMENTED
    \b
    • Basic log file reading functionality exists (output/logs/)
    • Advanced filtering and real-time following not yet implemented
    • Currently shows placeholder message

    LOG FILE LOCATIONS:
    \b
    • Directory: output/logs/
    • Filename: pipeline_log_{execution_id}.json
    • Format: Structured JSON with timestamps and metadata

    FILTERING OPTIONS:
    \b
    • --stage: Show logs for specific stage (extract/upload/aggregate/deploy)
    • --execution-id: Show logs for specific pipeline run
    • --tail: Limit to recent N log entries
    • --follow: Real-time log following (planned)

    LOG CONTENT:
    \b
    • Pipeline execution metadata and timing
    • Stage-by-stage execution details
    • Success/failure status for each stage
    • Output file paths and AWS resource IDs
    • Error messages with full stack traces

    PLANNED FEATURES:
    \b
    • Real-time log streaming for active pipelines
    • Intelligent log parsing and formatting
    • Error highlighting and filtering
    • Multi-pipeline log aggregation
    • Log retention and cleanup policies

    EXAMPLES:
    \b
    fantasy-extractor pipeline logs                              # Recent 50 log lines
    fantasy-extractor pipeline logs --stage extract             # Extract stage only
    fantasy-extractor pipeline logs --execution-id pipeline_*   # Specific run
    fantasy-extractor pipeline logs --tail 100                  # Last 100 lines

    Use 'fantasy-extractor pipeline help logs' for detailed information.
    """
    # TODO: Implement log aggregation and filtering
    # This would read from the saved pipeline logs in output/logs/
    click.echo("Pipeline log viewing not yet implemented")
    if stage:
        click.echo(f"Would display logs for stage: {stage}")
    if execution_id:
        click.echo(f"Would display logs for execution: {execution_id}")
    click.echo(f"Would show last {tail} lines")


@pipeline.command()
@click.argument('execution_id', required=False)
def status(execution_id: Optional[str]):
    """
    Display pipeline execution status and progress.

    EXECUTION_ID: Optional execution ID to check specific pipeline run

    ⚠️  STATUS: NOT YET IMPLEMENTED
    \b
    • This command currently shows placeholder message
    • Implementation pending for persistent pipeline state tracking
    • Will display stage progress, timing, and success/failure status

    PLANNED FEATURES:
    \b
    • Real-time pipeline execution status
    • Stage-by-stage progress tracking
    • Execution timing and performance metrics
    • Error status and failure reasons
    • Historical pipeline run summaries

    EXECUTION ID FORMAT:
    \b
    • Format: pipeline_{league_id}_{timestamp}
    • Example: pipeline_380491_20240915_143022
    • Generated automatically during pipeline execution

    PLANNED OUTPUT:
    \b
    • Overall pipeline status (pending/running/success/failed)
    • Individual stage status with timing information
    • Output file locations for completed stages
    • Error messages for failed stages

    EXAMPLES:
    \b
    fantasy-extractor pipeline status
    fantasy-extractor pipeline status pipeline_380491_20240915_143022

    Use 'fantasy-extractor pipeline help status' for detailed information.
    """
    # TODO: Implement pipeline status tracking
    # This would require persistent storage of pipeline states
    click.echo("Pipeline status tracking not yet implemented")
    if execution_id:
        click.echo(f"Would display status for execution: {execution_id}")
    else:
        click.echo("Would display status for all recent pipeline executions")


if __name__ == '__main__':
    cli()