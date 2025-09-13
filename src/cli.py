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

try:
    # Try relative imports first (when run as part of package)
    from .fantasy_extractor import FantasyFootballExtractor
    from .utils.config import get_config
    from .generators.html_generator import FantasyHTMLGenerator
except ImportError:
    # Fall back to absolute imports (when run as script)
    from fantasy_extractor import FantasyFootballExtractor
    from utils.config import get_config
    from generators.html_generator import FantasyHTMLGenerator


@click.group()
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
        generator = FantasyHTMLGenerator()
        generator.generate_from_file(str(input_path), str(output_path))
        
        click.echo(f"✓ Successfully generated HTML report: {output_path}")
        
    except Exception as e:
        click.echo(f"Error generating HTML: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()