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

Create or modify `config/config.yaml` to customize the application:

```yaml
# ESPN API Configuration
espn:
  username: null  # Or set ESPN_USERNAME environment variable
  password: null  # Or set ESPN_PASSWORD environment variable

# League Configuration
league:
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

## Usage

### Command Line Interface

#### Extract Weekly Data
```bash
# Extract data for most recent completed week
./fantasy-extractor extract 123456

# Extract specific week
./fantasy-extractor extract 123456 --week 5

# Extract with custom output file
./fantasy-extractor extract 123456 --week 5 --output week5_report.json

# Extract with ESPN credentials
./fantasy-extractor extract 123456 --username your_username --password your_password
```

#### Get League Information
```bash
# Display league info and standings
./fantasy-extractor info 123456
```

#### Validate Output Files
```bash
# Validate a generated JSON file
./fantasy-extractor validate week5_report.json
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
    username="your_username",  # Optional
    password="your_password"   # Optional
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

For private leagues, you'll need ESPN credentials:

1. **Environment Variables** (recommended):
   ```bash
   export ESPN_USERNAME="your_username"
   export ESPN_PASSWORD="your_password"
   ```

2. **Configuration File**:
   ```yaml
   espn:
     username: "your_username"
     password: "your_password"
   ```

3. **Command Line**:
   ```bash
   fantasy-extractor extract 123456 --username your_username --password your_password
   ```

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

1. **Authentication Errors**: Ensure ESPN credentials are correct and the league is accessible
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