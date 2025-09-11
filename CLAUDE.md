# Claude Code Context - Fantasy Football Summary Generator

## Application Overview

This is the **Duke Football Invitational Summary Generator** - a Python application that extracts structured data from ESPN Fantasy Football leagues and generates comprehensive weekly reports designed for creating humorous, engaging summaries.

### Core Purpose
- Extract fantasy football data from ESPN leagues via API
- Generate structured JSON reports for LLM analysis
- Create witty weekly summaries in the style of comedians like Mitch Hedberg and Norm MacDonald
- Track elaborate weekly awards and achievements

## Key Architecture Components

### 1. Main Entry Points
- **CLI Tool**: `./fantasy-extractor` - Command-line interface for all operations
- **Python API**: `src/fantasy_extractor.py:16` - Main `FantasyFootballExtractor` class
- **Config**: `config/config.yaml` and `config/secrets.yaml` for settings and ESPN authentication

### 2. Data Models (`src/models/data_models.py`)
- **Core Models**: `Team`, `Player`, `Matchup`, `Division`, `WeeklyReport`
- **Award Models**: `PlayerAward`, `TeamAward`, `LineupEfficiencyAward`, `CollapseAward`, `ProjectionFailAward`
- **Enums**: `InjuryStatus` for player health tracking
- All models use Pydantic for validation and JSON serialization

### 3. Data Extraction (`src/extractors/`)
- **TeamExtractor**: Handles team standings and division data
- **MatchupExtractor**: Processes weekly matchup results
- **PlayerExtractor**: Extracts individual player performance and injury data
- **Base classes** provide common functionality

### 4. Weekly Awards System
The application calculates 11 different weekly awards:

#### Individual Player Awards
- **MVP**: Highest scoring player on a winning team
- **MWP**: Highest scoring player on a losing team  
- **MUP**: Lowest scoring healthy starter
- **MDP**: Highest scoring bench player

#### Team Awards  
- **HSL**: Highest scoring losing team
- **LSW**: Lowest scoring winning team

#### Lineup Efficiency Awards
- **SSL**: Team with most efficient lineup (closest to optimal)
- **IFM**: Losing team with worst lineup efficiency
- **Accidental Genius**: Winning team with worst lineup efficiency

#### Collapse Awards (Lists)
- **McCollapse**: Teams that would've won with optimal lineup but lost
- **Clapper Collapse**: Teams projected to win but lost

### 5. Configuration & Authentication
- **ESPN Cookies**: Requires `espn_s2` and `swid` cookies for private leagues
- **League ID**: Set in config or pass via CLI
- **Output**: Customizable filename patterns, saved to `output/` directory

## Common Tasks & Commands

### Running Data Extraction
```bash
# Extract current week data
./fantasy-extractor extract

# Extract specific week
./fantasy-extractor extract --week 5

# Get league info and standings  
./fantasy-extractor info

# Validate generated reports
./fantasy-extractor validate filename.json
```

### Testing
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_data_models.py -v
python -m pytest tests/test_award_calculations.py -v

# Test with coverage
python -m pytest --cov=src tests/
```

### Linting & Type Checking
Check the README.md or ask the user for the specific commands to run linting and type checking, then add them to this section.

## Important Implementation Details

### Award Calculation Logic (`src/fantasy_extractor.py:304`)
- **Fixed Bug**: Tie games (when `winner_id` is `None`) are now handled correctly
- **Negative Cases**: All award calculations gracefully handle scenarios where no qualifying teams exist
- **Optimal Lineup Calculation**: Complex algorithm determines best possible starting lineup for efficiency awards

### Data Flow
1. **Authentication** → ESPN cookies for private league access
2. **Week Calculation** → Automatic NFL week determination (Thursday-Wednesday schedule)  
3. **Data Extraction** → Team standings, matchups, player performance
4. **Analysis** → Projected vs actual scores, optimal lineups, efficiency metrics
5. **Awards** → Calculate all 11 award categories with negative case handling
6. **Output** → Structured JSON saved to `output/` directory

### Output Format
Generated reports contain:
- League standings by division with rankings
- Complete matchup analysis with player performance
- Injury tracking for starters
- Comprehensive awards system with detailed metrics
- Optimal lineup calculations and efficiency percentages

## Debugging & Troubleshooting

### Common Issues
1. **ESPN Authentication**: 
   - Ensure `config/secrets.yaml` exists with valid cookies
   - Cookies expire periodically and need refreshing
2. **League Access**: Verify league ID and user permissions
3. **Missing Data**: Some weeks may have incomplete ESPN data
4. **Rate Limiting**: ESPN may throttle requests

### Testing Considerations
- **Award Tests**: Comprehensive negative case testing in `tests/test_award_calculations.py`
- **Mock ESPN Client**: Tests use mocked ESPN API to avoid external dependencies
- **Edge Cases**: Zero scores, ties, missing optimal data, empty player lists

## File Structure
```
├── src/
│   ├── fantasy_extractor.py     # Main orchestrator class
│   ├── models/data_models.py    # Pydantic data models
│   ├── extractors/              # Data extraction modules
│   └── utils/                   # Config, ESPN client, date utilities
├── tests/
│   ├── test_data_models.py      # Model validation tests
│   └── test_award_calculations.py # Award calculation negative case tests
├── config/
│   ├── config.yaml              # Main configuration
│   └── secrets.yaml             # ESPN authentication (git-ignored)
├── output/                      # Generated JSON reports
└── fantasy-extractor            # CLI executable
```

## ChatGPT Integration
The `chatgpt_prompt.txt` file contains the prompt template for generating humorous weekly summaries. Key requirements:
- Mitch Hedberg + Norm MacDonald comedy style
- Division standings analysis
- All 11 award categories with descriptions
- Narrative matchup summaries with projections vs reality
- League contender forecasting

## Recent Changes & Fixes
- **Fixed Award Bug**: Tie games no longer incorrectly assign winners/losers
- **Added Negative Case Tests**: Comprehensive testing for all award scenarios where no qualifying teams exist
- **Updated Award Descriptions**: Added "Accidental Genius" award to prompt template
- **Enhanced Data Models**: Full Pydantic validation with optional fields and default lists