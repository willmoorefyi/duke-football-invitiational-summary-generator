# Fantasy Football Data Extractor

Extract structured data from ESPN Fantasy Football leagues for LLM analysis and witty weekly summaries.

## Overview

This Python application extracts comprehensive fantasy football data from ESPN leagues and outputs it in a structured JSON format designed for LLM analysis. The extracted data includes team standings, matchup results, player performances, and injury information.

## Features

- **Team Data**: Extract team standings organized by divisions with proper ranking
- **Matchup Results**: Get weekly matchup data with scores and winners/losers
- **Player Performance**: Extract projected vs actual scores for all players
- **Injury Tracking**: Identify starters who are currently injured
- **Flexible Dating**: Extract data for specific weeks or dates
- **CLI Interface**: Easy-to-use command-line interface
- **Configuration**: Flexible configuration system
- **Type Safety**: Full Pydantic models for data validation

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd fantasy-football-extractor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up the command-line tool:
```bash
# Make the CLI script executable (already included in repo)
chmod +x fantasy-extractor

# Test the installation
./fantasy-extractor --help
```

## Configuration

The application uses two configuration files:

### Main Configuration (`config/config.yaml`)

Modify this file to customize general application settings:

```yaml
# ESPN API Configuration
espn:
  espn_s2: null    # ESPN_S2
  swid: null       # SWID

# League Configuration
league:
  # Set your ESPN Fantasy League ID here to avoid passing it every time
  league_id: null  # e.g., 123456
  
  divisions:
    - "East"
    - "West"
  tiebreakers:
    - "head_to_head"
    - "points_for"
    - "points_against"

# Output Configuration
output:
  filename_pattern: "fantasy_report_week_{week}_{date}.json"
  pretty_print: true
```

### Secrets Configuration (`config/secrets.yaml`)

For ESPN authentication, create a separate secrets file that won't be committed to version control:

```bash
# Copy the example file
cp config/secrets.yaml.example config/secrets.yaml

# Edit with your ESPN cookie values
```

Example `config/secrets.yaml`:
```yaml
espn:
  espn_s2: "your_long_espn_s2_cookie_value_here"
  swid: "{12345678-ABCD-1234-ABCD-123456789ABC}"
```

**Note:** The `secrets.yaml` file is automatically ignored by git to keep your credentials secure.

## League ID Configuration

You can set your default league ID in the configuration to avoid specifying it every time:

```yaml
# In config/config.yaml
league:
  league_id: 123456  # Your ESPN Fantasy League ID
```

With this set, you can run commands without specifying the league ID:
```bash
# Instead of: ./fantasy-extractor extract 123456 --week 5
# You can use: ./fantasy-extractor extract --week 5
```

The league ID can still be overridden from the command line when needed.

## Output Directory

All generated reports are saved to the `output/` directory by default:

```
output/
├── fantasy_report_week_1_2024-10-01.json
├── fantasy_report_week_2_2024-10-08.json
└── fantasy_report_week_3_2024-10-15.json
```

**Benefits:**
- **Organized**: All reports in one place
- **Git-ignored**: Output files won't be committed to version control
- **Easy validation**: `./fantasy-extractor validate filename.json` automatically looks here

## Usage

### Command Line Interface

#### Extract Weekly Data
```bash
# Extract data for most recent completed week
./fantasy-extractor extract 123456                    # with league ID
./fantasy-extractor extract                          # uses league_id from config

# Extract specific week
./fantasy-extractor extract 123456 --week 5         # with league ID  
./fantasy-extractor extract --week 5                # uses league_id from config

# Extract with custom output file
./fantasy-extractor extract --week 5 --output custom_report.json

# Extract with ESPN authentication cookies
./fantasy-extractor extract --espn-s2 "YOUR_ESPN_S2_COOKIE" --swid "YOUR_SWID_COOKIE"

# All files are saved to the output/ directory by default
# Example output: output/fantasy_report_week_5_2024-10-15.json
```

#### Get League Information
```bash
# Display league info and standings
./fantasy-extractor info 123456                     # with league ID
./fantasy-extractor info                            # uses league_id from config
```

#### Validate Output Files
```bash
# Validate a generated JSON file (automatically looks in output/ directory)
./fantasy-extractor validate fantasy_report_week_5_2024-10-15.json

# Or validate with full path
./fantasy-extractor validate output/fantasy_report_week_5_2024-10-15.json

# Or validate any custom file
./fantasy-extractor validate /path/to/custom_report.json
```

#### Calculate NFL Week
```bash
# Get current NFL week
./fantasy-extractor week

# Get NFL week for specific date
./fantasy-extractor week --date 2024-10-15
```

#### View Configuration
```bash
# Display current configuration
./fantasy-extractor config
```

### Python API

```python
from src.fantasy_extractor import FantasyFootballExtractor

# Create extractor
extractor = FantasyFootballExtractor(
    league_id=123456,
    year=2024,
    espn_s2="your_espn_s2_cookie",  # Optional
    swid="your_swid_cookie"         # Optional
)

# Extract weekly report
report = extractor.extract_weekly_report(week=5)

# Save to file
extractor.save_report_to_file(report, "week5_report.json")

# Or do both in one step
saved_path = extractor.generate_and_save_report(week=5)
```

## Output Format

The application generates a structured JSON file with the following schema:

```json
{
  "league_id": 123456,
  "league_name": "My Fantasy League",
  "season": 2024,
  "week": 5,
  "report_date": "2024-10-15T10:30:00",
  "divisions": [
    {
      "name": "East",
      "teams": [
        {
          "id": 1,
          "name": "Team Name",
          "owner": "Owner Name",
          "division": "East",
          "wins": 4,
          "losses": 1,
          "points_for": 650.5,
          "points_against": 580.2,
          "division_rank": 1
        }
      ]
    }
  ],
  "matchups": [
    {
      "week": 5,
      "home_team": { /* Team object */ },
      "away_team": { /* Team object */ },
      "home_score": 120.5,
      "away_score": 115.2,
      "winner_id": 1,
      "loser_id": 2,
      "is_complete": true,
      "players": [
        {
          "name": "Player Name",
          "position": "QB",
          "team": "Team Name",
          "projected_score": 18.5,
          "actual_score": 22.3,
          "is_starter": true,
          "injury_status": "HEALTHY"
        }
      ]
    }
  ],
  "injured_starters": [
    {
      "player_name": "Injured Player",
      "team_name": "Team Name",
      "position": "RB",
      "injury_status": "QUESTIONABLE"
    }
  ]
}
```

## Authentication

For private leagues, you'll need ESPN authentication cookies. These can be obtained from your browser:

### Getting ESPN Cookies

1. **Log into ESPN Fantasy** in your web browser
2. **Open Developer Tools** (F12 or right-click → Inspect)
3. **Go to Application/Storage tab** → Cookies → espn.com
4. **Find two cookies:**
   - `espn_s2` (long string, ~1000+ characters)
   - `SWID` (shorter string with curly braces, like `{12345678-ABCD-1234-ABCD-123456789ABC}`)

### Using the Cookies

1. **Secrets File** (recommended for security):
   ```bash
   # Copy the example secrets file
   cp config/secrets.yaml.example config/secrets.yaml
   
   # Edit config/secrets.yaml with your cookie values
   # This file is automatically ignored by git
   ```

2. **Environment Variables**:
   ```bash
   export ESPN_S2="your_espn_s2_cookie_value"
   export SWID="your_swid_cookie_value"
   ```

3. **Command Line**:
   ```bash
   ./fantasy-extractor extract 123456 --espn-s2 "YOUR_ESPN_S2" --swid "YOUR_SWID"
   ```

### Priority Order

The application loads authentication in this priority order (highest to lowest):
1. Command line arguments (`--espn-s2`, `--swid`)
2. Environment variables (`ESPN_S2`, `SWID`)
3. Secrets file (`config/secrets.yaml`)
4. Main config file (`config/config.yaml`)

## NFL Week Calculation

The application automatically calculates NFL weeks based on:
- Thursday to Wednesday schedule
- Season start date (configurable)
- 18 regular season weeks + 4 playoff weeks

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_data_models.py
```

## Development

### Project Structure
```
fantasy-football-extractor/
├── src/
│   ├── extractors/          # Data extraction modules
│   ├── models/              # Pydantic data models
│   ├── utils/               # Utilities (config, ESPN client, etc.)
│   ├── cli.py               # Command-line interface
│   └── fantasy_extractor.py # Main orchestrator
├── config/
│   └── config.yaml          # Default configuration
├── tests/                   # Test suite
└── requirements.txt         # Dependencies
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## Troubleshooting

### Common Issues

1. **Authentication Errors**: 
   - Ensure ESPN cookies (`espn_s2`, `swid`) are correct and current
   - Check that `config/secrets.yaml` exists and has valid values
   - Verify the league is accessible with your ESPN account
2. **Week Calculation**: Verify the season start date in configuration
3. **Missing Data**: Some data may not be available for incomplete weeks
4. **Rate Limiting**: ESPN may rate limit requests; add delays if needed

### Logging

Enable verbose logging for debugging:

```bash
fantasy-extractor extract 123456 --verbose
```

Or set the logging level in configuration:

```yaml
logging:
  level: "DEBUG"
```

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- [espn-api](https://github.com/cwendt94/espn-api) - ESPN Fantasy Sports API wrapper
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation library
- [Click](https://click.palletsprojects.com/) - Command-line interface framework