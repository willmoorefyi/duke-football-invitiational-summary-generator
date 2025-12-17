# Claude Code Context - Fantasy Football Summary Generator

## Application Overview

This is the **Duke Football Invitational Summary Generator** - a Python application that extracts structured data from ESPN Fantasy Football leagues and processes it through a comprehensive 5-stage data pipeline, generating enhanced reports and deployed websites designed for creating humorous, engaging summaries.

### Core Purpose
- Extract fantasy football data from ESPN leagues via API
- Process data through a full 5-stage pipeline: Extract → Aggregate → Upload → Generate → Deploy
- Generate structured JSON reports and enhanced season analytics for LLM analysis
- Deploy static websites with comprehensive league data and visualizations
- Store historical data in DynamoDB for season-long trends and analytics
- Create witty weekly summaries in the style of comedians like Mitch Hedberg and Norm MacDonald
- Track elaborate weekly awards and achievements with historical context

## Key Architecture Components

### 1. Pipeline Architecture (`src/pipeline/`)
- **5-Stage Pipeline**: Complete data processing from ESPN API to deployed websites
  - **Stage 1 - Extract**: ESPN data extraction (team info, matchups, players - no ESPN standings)
  - **Stage 2 - Aggregate**: Calculate historical standings from matchup data, multi-week analytics, and season context
  - **Stage 3 - Upload**: DynamoDB storage of enhanced JSON with computed standings and AWS integration
  - **Stage 4 - Generate**: HTML generation using computed standings from aggregate stage
  - **Stage 5 - Deploy**: S3 deployment with CloudFront integration
- **Orchestrator**: `src/pipeline/orchestrator.py:48` - `PipelineOrchestrator` class manages execution
- **Stages**: Individual stage modules with clean separation and dependency management
  - `src/pipeline/base.py` - Abstract `PipelineStage` base class
  - `src/pipeline/extract_stage.py` - Stage 1: ESPN data extraction
  - `src/pipeline/aggregate_stage.py` - Stage 2: Historical standings calculation and data aggregation
  - `src/pipeline/upload_stage.py` - Stage 3: DynamoDB upload of enhanced data
  - `src/pipeline/generate_stage.py` - Stage 4: HTML generation with computed standings
  - `src/pipeline/deploy_stage.py` - Stage 5: S3 deployment

### 2. Main Entry Points
- **CLI Tool**: `./fantasy-extractor` - Command-line interface for all operations
  - **Simple Commands**: `info`, `validate`, `config`, `week`, `clean` (utility commands)
  - **Pipeline Commands**: `pipeline run`, `pipeline extract`, `pipeline generate`, `pipeline status` (new functionality)
- **Python API**: `src/fantasy_extractor.py:16` - Main `FantasyFootballExtractor` class
- **Pipeline API**: `src/pipeline/orchestrator.py:48` - `PipelineOrchestrator` class
- **Config**: `config/config.yaml` and `config/secrets.yaml` for settings and authentication

### 3. Data Models (`src/models/data_models.py`)
- **Core Models**: `Team` (basic info only - standings calculated), `Player` (with detailed `PlayerStatistics`), `Matchup`, `Division`, `WeeklyReport`
- **Award Models**: `PlayerAward`, `TeamAward`, `LineupEfficiencyAward`, `CollapseAward`, `ProjectionFailAward`, `HonorableMention`
- **Enums**: `InjuryStatus` for player health tracking
- **Team Model**: Contains only basic info (id, name, owner, division, logo) - wins/losses/points/ranks computed in aggregate stage
- All models use Pydantic for validation and JSON serialization

### 4. Data Extraction (`src/extractors/`)
- **TeamExtractor**: Extracts basic team information (name, owner, division, logo) - no ESPN standings
- **MatchupExtractor**: Processes weekly matchup results
- **PlayerExtractor**: Extracts individual player performance, injury data, and detailed statistics from ESPN API (passing/rushing/receiving/kicking/defensive stats by position)
- **HistoryExtractor**: Extracts multi-year league history with champions, standings, and season records
- **Base classes** provide common functionality

### 5. League History Management (`src/extractors/history_extractor.py`, `src/uploaders/history_uploader.py`)
- **Purpose**: Extract and permanently store complete league history across multiple seasons
- **Data Models** (`src/models/history_models.py`): LeagueHistory, SeasonHistory, ChampionSummary, TeamSeasonStanding, DivisionInfo
- **History Extractor**: Fetches historical data from ESPN API for year ranges (e.g., 2020-2024)
- **History Uploader**: Uploads to DynamoDB using single-table design with `HISTORY#{league_id}` partition key
- **DynamoDB Schema**: METADATA record + individual SEASON#{year} records for efficient querying
- **CLI Commands**: `history extract`, `history upload`, `history sync`, `history info`
- **JSON Output**: Timestamped files in `output/history/` directory
- **Testing**: 52 comprehensive tests covering models, extraction, and DynamoDB operations
- **Future Integration**: Aggregate stage will fetch history for overview page champions table

### 6. AWS Integration
- **DynamoDB Storage**:
  - Weekly reports with computed standings (Stage 3 Upload)
  - League history with champions and season records (history uploader)
  - Single-table design using `season_week` + `data_type_id` composite key
- **S3 Deployment**: Static website hosting with asset management (Stage 5)
- **CloudFront**: Global content delivery network with cache invalidation (Stage 5)
- **Requirements**: Stages 3 and 5 require actual AWS resources and will fail if not available

### 7. Weekly Awards System
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

#### Collapse Awards (Single Winner + Honorable Mentions)
- **McCollapse**: Team with greatest difference between optimal and actual score that would've won with optimal lineup but lost
- **Clapper Collapse**: Team with greatest difference between projected and actual score that was projected to win but lost
- **Honorable Mentions**: Additional eligible teams for McCollapse and Clapper awards displayed in a separate section with full award name, team, and statistics

### 8. Configuration & Authentication
- **ESPN Cookies**: Requires `espn_s2` and `swid` cookies for private leagues
- **AWS Credentials**: Required for pipeline functionality (DynamoDB, S3, CloudFront) and league history uploads
- **League ID**: Set in config or pass via CLI
- **Output**: Multiple output directories - `output/raw/`, `output/enhanced/`, `output/condensed/`, `output/html/`, `output/history/`, `output/logs/`

## Common Tasks & Commands

### Pipeline Operations
```bash
# Run full 5-stage pipeline
./fantasy-extractor pipeline run                    # Current week, uses config league_id
./fantasy-extractor pipeline run --week 5           # Specific week
./fantasy-extractor pipeline run --dry-run          # Test without making changes

# Individual pipeline stages
./fantasy-extractor pipeline extract --week 5       # Stage 1: ESPN extraction
./fantasy-extractor pipeline upload file.json      # Stage 2: DynamoDB upload
./fantasy-extractor pipeline aggregate file.json   # Stage 3: Season aggregation
./fantasy-extractor pipeline generate enhanced.json # Stage 4: HTML generation
./fantasy-extractor pipeline deploy html_file.html  # Stage 5: S3 deployment

# Pipeline monitoring
./fantasy-extractor pipeline status                 # View pipeline status
./fantasy-extractor pipeline logs                   # View execution logs
```

### Simple Data Extraction (Original)
```bash
# Extract current week data
./fantasy-extractor extract

# Extract specific week
./fantasy-extractor extract --week 5

# Get league info and standings
./fantasy-extractor info

# Generate HTML from JSON
./fantasy-extractor pipeline generate report.json

# Validate generated reports
./fantasy-extractor validate filename.json
```


### Utility Commands
```bash
# Testing
python -m pytest tests/ -v                    # Run all tests
python -m pytest --cov=src tests/            # Test with coverage

# Other utilities
./fantasy-extractor clean                    # Clean old output files (see --help for options)
./fantasy-extractor info                     # Get league info and standings
./fantasy-extractor validate file.json       # Validate JSON report
```

### League History Management
```bash
# Extract historical data from ESPN API
./fantasy-extractor history extract --start-year 2020 --end-year 2024
./fantasy-extractor history extract --start-year 2023 --end-year 2023  # Single year

# Upload history to DynamoDB
./fantasy-extractor history upload output/history/league_history_123456_2020-2024.json
./fantasy-extractor history upload file.json --dry-run  # Test without uploading

# Extract and upload in one step
./fantasy-extractor history sync --start-year 2020 --end-year 2024
./fantasy-extractor history sync --start-year 2023 --dry-run

# View stored history from DynamoDB
./fantasy-extractor history info
./fantasy-extractor history info --league-id 123456
```

### Annual Recap / Fantasy Wrapped
```bash
# Generate annual recap from DynamoDB (recommended)
./fantasy-extractor annual-recap --source dynamodb --season 2024

# Generate from local JSON files
./fantasy-extractor annual-recap --source local --directory output/enhanced/

# Output is saved to output/html/annual_recap_YYYY.html
```

### Linting & Type Checking
Check the README.md or ask the user for the specific commands to run linting and type checking, then add them to this section.

## Important Implementation Details

### Key Implementation Notes
- **Award Calculation**: Handles tie games correctly, graceful negative case handling, optimal lineup algorithm
- **DynamoDB Upload**: Multi-record strategy (`season_week` + `data_type_id` primary key), float-to-Decimal conversion
- **S3 Deploy**: Uploads to `will.moore.fyi` bucket, CloudFront invalidation (dist `E10BJV5LJCPKIE`), standardized naming
- **Multi-Week Aggregation**: `_fetch_historical_data()` queries all previous weeks, creates `season_context` with running totals, performance trends, and weekly statistics
- **League History**: Single-table design using `HISTORY#{league_id}` partition key with `METADATA` and `SEASON#{year}` sort keys for efficient querying

### League History Implementation (`src/extractors/history_extractor.py`, `src/uploaders/history_uploader.py`)

**Purpose**: Extract and store complete league history across multiple seasons for champions tracking and historical analysis.

**Architecture**:
```
ESPN API → HistoryExtractor → JSON File → HistoryUploader → DynamoDB
                              (output/history/)              (fantasy-league-data table)
```

**Data Models** (`src/models/history_models.py`):
- `LeagueHistory`: Top-level container with metadata and seasons list
- `SeasonHistory`: Individual season with standings, champion, runner-up, third place
- `ChampionSummary`: Team record (ID, name, owner, wins, losses, points)
- `TeamSeasonStanding`: Full season record with division info
- `DivisionInfo`: Division metadata and team lists

**DynamoDB Schema** (uses existing `fantasy-league-data` table):
```python
# METADATA Record
PK: "HISTORY#{league_id}"
SK: "METADATA"
Attributes: league_name, total_seasons, year_range, seasons_list[], extracted_at

# SEASON Records (one per year)
PK: "HISTORY#{league_id}"
SK: "SEASON#{year}"
Attributes: year, total_teams, divisions[], final_standings[], champion, runner_up, third_place
```

**Key Features**:
- **Multi-Year Extraction**: Fetches data for year ranges (e.g., 2020-2024) in single operation
- **Team Identity Tracking**: Stores team IDs to track teams across name/owner changes
- **Robust Error Handling**: Continues extraction even if individual seasons fail
- **Decimal Conversion**: Recursively converts floats to Decimal for DynamoDB compatibility
- **Fetch Methods**: `fetch_league_history()` and `fetch_season()` for querying stored data
- **JSON Output**: Timestamped files saved to `output/history/` with sanitized filenames

**CLI Commands** (`src/cli.py` lines 1275-1571):
- `history extract`: Fetch data from ESPN API for specified year range
- `history upload`: Upload JSON file to DynamoDB with validation
- `history sync`: Combined extract + upload operation
- `history info`: Display stored history with champions summary

**Testing** (`tests/test_history_*.py`):
- **52 comprehensive tests** covering all components
- **test_history_models.py**: 15 tests for Pydantic validation and serialization
- **test_history_extractor.py**: 20 tests for ESPN API extraction and JSON saving
- **test_history_uploader.py**: 17 tests for DynamoDB upload and fetch operations
- **Edge cases**: Single-team leagues, missing runner-up, filename sanitization, DynamoDB errors

**Future Integration**:
- Aggregate stage will fetch history during multi-week processing
- Overview page will display champions table with historical records

### HTML Frontend Enhancements (`src/generators/templates/`)
- **Interactive Sortable Tables**: JavaScript-powered column sorting with visual indicators, supports grouped rows (division + logo rows)
- **Division Strength Table**: Inter-division rankings with team logos, ranked by wins/losses/points
- **Weekly Summary Table**: Current week performance with win/loss results and margins vs median score
- **Team Lightbox Modal**: Click team rows/awards/headers to view full season history, weekly results, and stats
- **Multi-Week Rendering**: Weekly Totals table displays all weeks using `all_weeks_stats` array from enhanced JSON
- **Responsive Design**: Mobile-friendly with optimized column widths and modular Jinja2 templates

### Data Flow
1. **Extract** (Stage 1): ESPN API → Raw JSON with team info, matchups, players
2. **Aggregate** (Stage 2): Raw JSON + DynamoDB historical data → Enhanced JSON with computed standings and season context
3. **Upload** (Stage 3): Enhanced JSON → DynamoDB storage
4. **Generate** (Stage 4): Enhanced JSON → HTML reports
5. **Deploy** (Stage 5): HTML → S3 bucket + CloudFront invalidation

### Output Formats
- **Raw JSON** (`output/raw/`): ESPN data with team info, matchups, players, awards, optimal lineups
- **Enhanced JSON** (`output/enhanced/`): Raw data + computed standings + season context (team_standings, weekly_statistics, running_totals, performance_trends, matchup_history, award_summaries, is_latest_week flag)
- **Condensed JSON** (`output/condensed/`): Simplified format for external systems with essential fields only (team standings, matchups with 3 winner types, awards, players)
- **HTML Files** (`output/html/`): Mobile-friendly reports with sortable tables, team standings, division strength, weekly summaries, interactive lightbox modals
- **Overview Page** (`index.html`): Season overview with league standings, Weekly Totals table with clickable week links, deployed only for latest completed week
- **Pipeline Logs** (`output/logs/`): Execution tracking, timing, errors, metadata

## Debugging & Troubleshooting

### Common Issues
- **ESPN Authentication**: Cookies in `config/secrets.yaml` expire periodically and need refreshing
- **AWS Resources**: Stages 3 and 5 require DynamoDB table `fantasy-league-data` and S3 bucket `will.moore.fyi`
- **Pipeline Dependencies**: Each stage requires output from previous stage; use `--verbose` and check `output/logs/`
- **Testing Without AWS**: Use `--dry-run` flag to test pipeline workflow without making AWS calls

### Testing
- **323 total tests** covering data models, award calculations, pipeline stages, HTML generation, frontend features, league history, annual recap, and playoff view
- **Key areas**: DynamoDB integration, multi-week aggregation, template rendering, condensed JSON, interactive tables, overview page generation, league history extraction and storage, playoff detection, annual recap generation
- **Playoff View Tests** (`tests/test_playoff_view.py`): 8 tests covering playoff detection, bracket categorization, and matchup filtering
- **Annual Recap Tests** (`tests/test_annual_recap_generator.py`): 8 integration tests covering full pipeline, data aggregation, and edge cases
- **Overview Page Tests** (`tests/test_overview_page.py`): 6 tests covering page generation, conditional logic, week links, and deploy stage integration
- **League History Tests** (`tests/test_history_*.py`): 52 tests covering models, extraction, and DynamoDB upload
  - `test_history_models.py`: 15 tests for Pydantic validation and serialization
  - `test_history_extractor.py`: 20 tests for ESPN API extraction and JSON saving
  - `test_history_uploader.py`: 17 tests for DynamoDB upload and fetch operations
- **Edge cases**: Tie games, zero scores, missing data, malformed structures, single-team leagues, filename sanitization, playoff week detection
- **Mock ESPN Client**: Avoids external dependencies in tests

## File Structure
```
├── src/
│   ├── fantasy_extractor.py     # Main orchestrator class
│   ├── models/
│   │   ├── data_models.py       # Pydantic data models for weekly reports
│   │   └── history_models.py    # Pydantic data models for league history
│   ├── extractors/
│   │   ├── history_extractor.py # ESPN API history extraction
│   │   └── ...                  # Other extractors
│   ├── uploaders/
│   │   └── history_uploader.py  # DynamoDB history upload
│   ├── pipeline/                # 5-stage data pipeline
│   │   ├── __init__.py          # Clean public API exports
│   │   ├── orchestrator.py      # Pipeline coordination and management
│   │   ├── base.py              # Abstract PipelineStage base class
│   │   ├── extract_stage.py     # Stage 1: ESPN data extraction
│   │   ├── upload_stage.py      # Stage 2: DynamoDB upload
│   │   ├── aggregate_stage.py   # Stage 3: Data aggregation + playoff context
│   │   ├── generate_stage.py    # Stage 4: HTML generation
│   │   └── deploy_stage.py      # Stage 5: S3 deployment
│   ├── generators/              # HTML generation and templates
│   │   ├── templated_html_generator.py  # Weekly report generator with playoff detection
│   │   ├── annual_recap_generator.py    # Fantasy Wrapped/annual recap generator
│   │   └── templates/
│   │       ├── main.html                # Regular season weekly report template
│   │       ├── playoff_main.html        # Playoff week template
│   │       ├── playoff_bracket.html     # March Madness bracket visualization
│   │       ├── playoff_styles.css       # Playoff-specific CSS
│   │       ├── consolation_results.html # Consolation bracket table
│   │       └── annual-recap-template.html # Fantasy Wrapped template
│   └── utils/                   # Config, ESPN client, date utilities
├── tests/
│   ├── test_data_models.py      # Model validation tests
│   ├── test_award_calculations.py # Award calculation negative case tests
│   ├── test_playoff_view.py     # Playoff detection and bracket tests (8 tests)
│   ├── test_annual_recap_generator.py # Annual recap integration tests (8 tests)
│   ├── test_history_models.py   # History data model tests (15 tests)
│   ├── test_history_extractor.py # History extraction tests (20 tests)
│   ├── test_history_uploader.py # History DynamoDB upload tests (17 tests)
│   ├── test_aggregate_stage.py  # Multi-week aggregation and running totals tests (31 tests)
│   ├── test_aggregate_stage_condensed.py # Condensed JSON generation tests (8 tests)
│   ├── test_templated_html_generator_running_totals.py # HTML generator running totals tests (10 tests)
│   ├── test_templated_html_generator_weekly_summary.py # HTML generator weekly summary tests (8 tests)
│   ├── test_templated_html_generator_multiweek.py # Multi-week HTML generator tests (11 tests)
│   ├── test_generate_stage.py   # HTML generation stage tests (15 tests)
│   ├── test_upload_stage.py     # DynamoDB upload stage tests (10 tests)
│   ├── test_deploy_stage.py     # S3 deployment stage tests (10 tests)
│   ├── test_team_logo_extraction.py # Logo extraction tests
│   └── test_clean_command.py    # CLI clean command tests
├── config/
│   ├── config.yaml              # Main configuration
│   └── secrets.yaml             # ESPN authentication (git-ignored)
├── output/                      # Generated reports and pipeline data
│   ├── raw/                     # Stage 1: Raw ESPN JSON data
│   ├── enhanced/                # Stage 3: Enhanced JSON with season context
│   ├── condensed/               # Stage 3: Condensed JSON for limited context systems
│   ├── html/                    # Stage 4: Generated HTML files
│   ├── history/                 # League history JSON files
│   └── logs/                    # Pipeline execution logs
├── test_history_extraction.py   # Standalone history extraction test script (135 lines)
├── HISTORY_TESTING_GUIDE.md     # League history testing documentation
├── PIPELINE_PLAN.md             # Pipeline architecture documentation
└── fantasy-extractor            # CLI executable
```

## ChatGPT Integration
The `chatgpt_prompt.txt` file contains the prompt template for generating humorous weekly summaries. Key requirements:
- Mitch Hedberg + Norm MacDonald comedy style
- Division standings analysis
- All 11 award categories with descriptions
- Narrative matchup summaries with projections vs reality
- League contender forecasting

## Historical Standings Accuracy

### Problem Solved: ESPN Standings Inaccuracy
Previously, the application used ESPN's current season standings, causing **major issues with historical reporting**:
- **Week 5 reports showed Week 10+ records**: ESPN always returns current season totals
- **Impossible historical analysis**: Past reports constantly changed as season progressed
- **Inaccurate rankings**: Team positions reflected full season, not performance through specific week
- **Data integrity issues**: Historical reports became unreliable over time

### Solution: Computed Historical Standings Architecture
**Stage 2 (Aggregate)** now implements accurate historical standings calculation:

#### Ranking Algorithm
Teams ranked by precise criteria in order:
1. **Wins** (most wins = higher rank)
2. **Losses** (fewer losses = higher rank)
3. **Points For** (more points scored = higher rank)
4. **Points Against** (fewer points allowed = higher rank)

#### Implementation Details
- **Matchup-Based Calculation**: All wins/losses/points derived from actual game results stored in DynamoDB
- **Week-Specific Accuracy**: Week 5 reports show exactly what standings were after Week 5 games
- **Historical Consistency**: Past reports remain accurate and never change
- **Cross-Week Analytics**: Track standings progression throughout entire season
- **Data Integrity**: Enhanced JSON includes both current week data and computed season context

#### Benefits Achieved
✅ **Historical Accuracy**: Any week report shows correct standings for that point in season
✅ **Season Progression Analysis**: Track how teams performed week-by-week throughout season
✅ **Data Reliability**: Reports remain consistent and don't change as season progresses
✅ **Enhanced Analytics**: Season context enables cross-week trend analysis and standing progression
✅ **Flexible Reporting**: Generate accurate historical reports for any past week

## Recent Changes & Fixes

### Playoff View (December 2025 - Latest)
- **Automatic Playoff Detection**: System automatically detects playoff weeks (week > regular_season_weeks from ESPN API)
- **March Madness Bracket**: Visual tournament bracket showing all playoff rounds with team logos and team-specific colors
- **Bracket Structure** (6-team playoff):
  - Quarterfinals: #3 vs #6, #4 vs #5
  - Semifinals: #2 vs QF1 winner, #1 vs QF2 winner (bye teams)
  - Championship: SF winners
- **Visual Features**: Team logos (55x55px), team theme colors as backgrounds, winner highlighting with green glow and checkmark, champion crown emoji
- **Consolation Bracket**: Minimal table display for seeds 7-12
- **Templates**: `playoff_main.html`, `playoff_bracket.html`, `consolation_results.html`, `playoff_styles.css`
- **Data**: `playoff_context` added to `season_context` in enhanced JSON with `bracket_structure`, `championship_bracket`, `consolation_bracket`
- **Testing**: 8 tests in `tests/test_playoff_view.py` covering detection, categorization, and filtering

### Annual Recap / Fantasy Wrapped (December 2025)
- **Purpose**: Generate end-of-season recap page ("Fantasy Wrapped") with animated visualizations and comprehensive statistics
- **CLI Command**: `./fantasy-extractor annual-recap --source dynamodb --season 2024`
- **Data Source**: Fetches all weekly reports from DynamoDB for the specified season

#### Generator (`src/generators/annual_recap_generator.py`)
- `_aggregate_team_data()`: Builds week-by-week standings progression for horse-race animation
- `_aggregate_awards_data()`: Compiles season-long award tallies per team
- `_aggregate_weekly_highlights()`: Extracts weekly high/low scorers and matchup results
- `_aggregate_season_recap()`: Calculates season awards (Luckiest Team, Heartbreaking Loser, etc.)
- `_aggregate_team_stats()`: Per-team statistics including player performance

#### Template (`src/generators/templates/annual-recap-template.html`)
Five animated slides with auto-progression:
1. **Horse-Race Leaderboard**: Animated week-by-week standings progression with team logos and colors
2. **Awards Recap**: Season-long award winners with expandable team cards
3. **Weekly Highlights**: Week-by-week scores, winners, and notable performances
4. **Season Recap**: Overall season awards with Pythagorean wins calculation
5. **Team Stats**: Per-team detailed statistics in horizontal scroll cards

#### Season Recap Awards
- **Weekly High Scorer Champion**: Team with most weekly high scores
- **Weekly Low Scorer Champion**: Team with most weekly low scores
- **Luckiest Team**: Top-half finisher with lowest average margin of victory
- **Heartbreaking Loser**: Bottom-half finisher with lowest average margin of loss

#### Team Stats (per team)
- **MVP**: Highest scoring starter (cumulative)
- **Lowest Scoring Starter**: Lowest average points for starters with >1 start
- **Most Disrespected**: Highest cumulative bench points over season
- **Best Win**: Highest scoring win with opponent and score
- **Worst Loss**: Lowest scoring loss with opponent and score

#### Design Features
- **Championship Gold Theme**: Deep navy gradient with gold accents for Team Stats section
- **Mobile Responsive**: Scrollable cards, adaptive layouts
- **Auto-Advance**: Slides progress automatically with manual navigation available
- **Testing**: 8 integration tests in `tests/test_annual_recap_generator.py`

### Season Overview Page (October 2025)
- Automatic generation of season overview page (`index.html`) deployed to `https://will.moore.fyi/duke-football-invitational/weekly-reports/`
- **Conditional Generation**: Only creates overview for the latest completed week in the season
- **Latest Week Detection**: Aggregate stage checks DynamoDB for future weeks to determine if current week is latest
- **Content**: League logo, Overall League Standings, Weekly Totals table with embedded week report links
- **Week Links**: Week column in Weekly Totals table is clickable with arrow indicator (→) to access full weekly reports
- **Methods**: `generate_overview_page()` in HTML generator, `_generate_and_upload_overview()` in deploy stage
- **Testing**: 6 comprehensive tests covering page generation, conditional logic, and link structure (`tests/test_overview_page.py`)

### Team Lightbox with Full Season History
- Interactive modal showing complete game-by-game team history for entire season
- Data source: `matchup_history.weekly_results` with week-indexed matchup arrays
- Click targets: team rows, award cards, game headers, division logos
- Displays season stats, weekly results table with home/away indicators, running records
- Methods: `_calculate_matchup_history()` in aggregate stage, `_calculate_team_weekly_results()` in HTML generator

### Division Strength Table (September 2025)
- Inter-division performance rankings with wins/losses against other divisions and season points for/against
- Ranked by (1) wins, (2) losses, (3) points for, (4) points against
- Team logo rows attached to each division with grouped sorting support
- Source: `season_context.division_strength` in enhanced JSON

### Condensed JSON Output (September 2025)
- Stage 3 generates both enhanced (full) and condensed (simplified) JSON formats
- Flattened structure with essential fields: team standings, matchups, awards, player data
- Includes three winner fields: actual, projected, and optimal
- Designed for external systems with limited context windows

