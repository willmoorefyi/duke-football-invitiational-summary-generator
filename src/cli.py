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
except ImportError:
    # Fall back to absolute imports (when run as script)
    from fantasy_extractor import FantasyFootballExtractor
    from utils.config import get_config


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    Fantasy Football Data Extractor
    
    Extract structured data from ESPN Fantasy Football leagues for LLM analysis.
    """
    pass


@cli.command()
@click.argument('league_id', type=int)
@click.option('--year', '-y', type=int, help='Fantasy season year (default: current year)')
@click.option('--espn-s2', help='ESPN_S2 cookie value (overrides config)')
@click.option('--swid', help='SWID cookie value (overrides config)')
@click.option('--date', '-d', help='Reference date (ISO format, default: today)')
@click.option('--week', '-w', type=int, help='Specific week to extract (overrides date)')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--pretty', is_flag=True, help='Pretty print JSON output')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def extract(league_id: int, year: Optional[int], espn_s2: Optional[str], 
           swid: Optional[str], date: Optional[str], week: Optional[int],
           output: Optional[str], pretty: bool, verbose: bool):
    """
    Extract weekly fantasy football data from ESPN.
    
    LEAGUE_ID: ESPN fantasy league ID (required)
    
    Example:
        fantasy-extractor extract 123456 --week 5 --output week5.json
    """
    if verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
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
@click.argument('league_id', type=int)
@click.option('--year', '-y', type=int, help='Fantasy season year (default: current year)')
@click.option('--espn-s2', help='ESPN_S2 cookie value (overrides config)')
@click.option('--swid', help='SWID cookie value (overrides config)')
def info(league_id: int, year: Optional[int], espn_s2: Optional[str], swid: Optional[str]):
    """
    Display league information and team standings.
    
    LEAGUE_ID: ESPN fantasy league ID (required)
    """
    try:
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
@click.argument('input_file', type=click.Path(exists=True))
def validate(input_file: str):
    """
    Validate a JSON report file against the expected schema.
    
    INPUT_FILE: Path to JSON file to validate
    """
    try:
        try:
            from .models.data_models import WeeklyReport
        except ImportError:
            from models.data_models import WeeklyReport
        
        # Load and parse JSON
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        # Validate against schema
        report = WeeklyReport.model_validate(data)
        
        click.echo(f"✓ Valid report file: {input_file}")
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
                'divisions': config_obj.league.divisions,
                'tiebreakers': config_obj.league.tiebreakers
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


if __name__ == '__main__':
    cli()