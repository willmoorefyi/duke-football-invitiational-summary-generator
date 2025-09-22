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
- **Core Models**: `Team` (basic info only - standings calculated), `Player`, `Matchup`, `Division`, `WeeklyReport`
- **Award Models**: `PlayerAward`, `TeamAward`, `LineupEfficiencyAward`, `CollapseAward`, `ProjectionFailAward`, `HonorableMention`
- **Enums**: `InjuryStatus` for player health tracking
- **Team Model**: Contains only basic info (id, name, owner, division, logo) - wins/losses/points/ranks computed in aggregate stage
- All models use Pydantic for validation and JSON serialization

### 4. Data Extraction (`src/extractors/`)
- **TeamExtractor**: Extracts basic team information (name, owner, division, logo) - no ESPN standings
- **MatchupExtractor**: Processes weekly matchup results
- **PlayerExtractor**: Extracts individual player performance and injury data
- **Base classes** provide common functionality

### 5. AWS Integration
- **DynamoDB Storage**: Historical data persistence with schema versioning (Stage 2)
- **S3 Deployment**: Static website hosting with asset management (Stage 5 - Not Yet Implemented)
- **CloudFront**: Global content delivery network integration (Stage 5 - Not Yet Implemented)
- **Requirements**: Stages 2 and 5 require actual AWS resources and will fail if not available

### 6. Weekly Awards System
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

### 7. Configuration & Authentication
- **ESPN Cookies**: Requires `espn_s2` and `swid` cookies for private leagues
- **AWS Credentials**: Required for pipeline functionality (DynamoDB, S3, CloudFront)
- **League ID**: Set in config or pass via CLI
- **Output**: Multiple output directories - `output/raw/`, `output/enhanced/`, `output/html/`, `output/logs/`

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

### Output Directory Management
```bash
# Clean old files from output directory with default settings (7 days, keep 3 latest)
./fantasy-extractor clean

# Preview what would be cleaned without actually removing files
./fantasy-extractor clean --dry-run

# Clean with custom retention settings
./fantasy-extractor clean --keep-days 14 --keep-latest 5

# Clean with detailed output showing file processing
./fantasy-extractor clean --verbose

# More aggressive cleanup (keep only 2 days, 1 file per directory)
./fantasy-extractor clean --keep-days 2 --keep-latest 1
```

### Testing
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_data_models.py -v
python -m pytest tests/test_award_calculations.py -v
python -m pytest tests/test_upload_stage.py -v
python -m pytest tests/test_clean_command.py -v

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

### DynamoDB Upload Implementation (`src/pipeline/upload_stage.py`)
- **Schema Alignment**: Refactored to match CloudFormation template (`season_week` + `data_type_id` primary key)
- **Multi-Record Strategy**: Creates 1 main record + N team records per upload for optimal GSI performance
- **Data Transformation**: Recursive float-to-Decimal conversion for DynamoDB compatibility
- **Error Handling**: Comprehensive exception handling with detailed logging and metadata tracking
- **Testing Coverage**: 10 comprehensive unit tests covering success, failure, and edge cases

### S3 Deploy Implementation (`src/pipeline/deploy_stage.py`)
- **S3 Upload**: Deploys HTML files to `will.moore.fyi` S3 bucket with standardized naming conversion
- **CloudFront Integration**: Automatic cache invalidation using distribution `E10BJV5LJCPKIE` for immediate updates
- **Filename Processing**: Converts timestamped files (`fantasy_report_week_5_20250915_142530.html`) to standardized format (`fantasy_report_2025_week_5.html`)
- **Error Handling**: Comprehensive AWS service error handling with graceful CloudFront failure (deployment succeeds with warning)
- **Testing Coverage**: 10 comprehensive unit tests covering S3 upload, CloudFront invalidation, error scenarios, and edge cases
- **Configuration**: Pre-configured for `will.moore.fyi` bucket with `duke-football-invitational/weekly-reports/` path structure
- **Cache Management**: 1-hour TTL with automatic invalidation ensures immediate visibility of updates

### Multi-Week Data Aggregation Implementation (`src/pipeline/aggregate_stage.py`)
- **Historical Data Fetching**: `_fetch_historical_data()` automatically queries DynamoDB for all previous weeks in current season
  - **Smart Querying**: Retrieves weeks 1 through (current_week - 1) using `season_week` format (`2025-01`, `2025-02`, etc.)
  - **League Filtering**: Validates `league_id` match to ensure correct historical data
  - **Error Handling**: Graceful degradation for missing AWS credentials, table not found, or network issues
  - **Type Conversion**: Automatic conversion of DynamoDB Decimal objects to float using `_convert_decimal_to_float()`
- **Cross-Week Analytics**: Comprehensive multi-week calculation methods for season-long insights
  - **`_calculate_multi_week_team_performance()`**: Team averages, league statistics, and performance trends across all weeks
  - **`_calculate_multi_week_running_totals()`**: Cumulative actual vs projected vs optimal scoring for all teams
  - **`_calculate_multi_week_matchup_statistics()`**: Season-long blowouts, close games, and upset tracking
  - **`_calculate_multi_week_award_summaries()`**: Award winner tracking across all weeks for season context
  - **`_calculate_all_weeks_statistics()`**: Individual week statistics for Weekly Totals table (median, average, max/min, efficiency)
- **Enhanced JSON Structure**: Creates comprehensive `season_context` with multi-week data
  - **`weekly_statistics.weeks`**: Array of individual week statistics for template iteration
  - **`running_totals`**: Cumulative team performance across all weeks
  - **`performance_trends`**: Cross-week analytics and league averages
  - **`metadata`**: Tracks historical weeks included, total weeks processed, and data source type
- **Type Safety & Compatibility**: Robust data type handling for template and JavaScript compatibility
  - **Decimal Conversion**: Recursive conversion of all DynamoDB Decimal objects to float
  - **Template Variables**: Ensures all numeric values are properly typed for Jinja2 templates
  - **JavaScript Compatibility**: Prevents "must be real number, not str" errors in template rendering

### HTML Frontend Enhancements (`src/generators/templates/`)
- **Interactive Tables**: JavaScript-powered sortable column headers for all data tables
  - **Visual Indicators**: Sort direction arrows (⇅ → ↑ → ↓) with hover effects and blue underline animation
  - **Smart Data Detection**: Automatic numeric vs string sorting with proper comparisons
  - **Consistent UX**: Applies to all `.standings-table` elements, opt-out with `data-no-sort`
  - **Implementation**: `src/generators/templates/scripts.js` and `src/generators/templates/styles.css`
- **Running Totals Table**: Season-long efficiency tracking with comprehensive metrics
  - **Data Source**: Enhanced JSON with aggregated historical data from `season_context.running_totals`
  - **Fallback Calculation**: Automatic computation from raw matchup data when enhanced data unavailable
  - **Efficiency Metrics**: Shows actual points, projected points, optimal points, and efficiency percentage
  - **Default Sorting**: Orders by efficiency (highest to lowest) for immediate insights
  - **Styling Consistency**: Uses same visual design as Overall League Standings (background logos, team colors)
- **Weekly Summary Table**: Current week team performance analysis
  - **Data Preparation**: `src/generators/templated_html_generator.py:_prepare_weekly_summary_data()`
  - **Performance Metrics**: Team scores, win/loss/tie results, and score margins vs opponents
  - **Median Indicator**: League median score divider row between positions 6 and 7
  - **Result Format**: Full text ("Win", "Loss", "Tie") with properly formatted margins ("+12.50", "-45.26")
  - **Non-Sortable**: Fixed ranking by score with `data-no-sort` to maintain current week context
  - **Template Integration**: Uses same visual styling as other standings tables
- **Smart Table Styling**: Optimized column widths and specialized styling
  - **Numeric Columns**: 50px max-width for better table proportions
  - **Divider Rows**: Gray background with italic styling for median indicators
  - **Responsive Layout**: Maintains readability across all screen sizes
- **Multi-Week Template Rendering**: Enhanced HTML generator support for historical data
  - **`_get_week_statistics_data()`**: Intelligently uses pre-calculated weekly statistics from enhanced JSON when available
  - **Template Variables**: Provides `all_weeks_stats` array for multi-week template iteration
  - **Weekly Totals Table**: Displays multiple rows (Week 1, Week 2, etc.) instead of current week only
  - **Backward Compatibility**: Graceful fallback to current-week-only when enhanced data unavailable
  - **Type Safety**: All template variables properly converted to JavaScript-compatible types
- **Template Architecture**: `scripts.js`, `styles.css`, and modular Jinja2 templates
- **Responsive Design**: All interactive features work across all screen sizes and devices

### Data Flow

#### Simple Extraction (Original)
1. **Authentication** → ESPN cookies for private league access
2. **Week Calculation** → Automatic NFL week determination (Thursday-Wednesday schedule)
3. **Data Extraction** → Basic team info, matchups, player performance (no ESPN standings)
4. **Analysis** → Projected vs actual scores, optimal lineups, efficiency metrics
5. **Awards** → Calculate all 11 award categories with negative case handling
6. **Output** → Structured JSON saved to `output/` directory

#### Pipeline Flow (New)
1. **Stage 1 - Extract** → ESPN data extraction → Raw JSON (`output/raw/`)
2. **Stage 2 - Aggregate** → Calculate historical standings + season context → Enhanced JSON (`output/enhanced/`)
3. **Stage 3 - Upload** → DynamoDB storage of enhanced data with computed standings
4. **Stage 4 - Generate** → HTML generation using computed standings → HTML Files (`output/html/`)
5. **Stage 5 - Deploy** → S3 upload + CloudFront invalidation → Live URL
6. **Logging** → Pipeline execution logs saved to `output/logs/`

#### Pipeline Architecture
```
ESPN API → [Extract] → Raw JSON → [Aggregate] → Enhanced JSON
                                      ↑              ↓
                                Historical Data   [Upload] → DynamoDB
                                                      ↓
                                                 [Generate] → HTML Files
                                                      ↓
                                CloudFront ← [Deploy] ← S3 Bucket
```

### Output Formats

#### Raw JSON (`output/raw/`) - Stage 1 Output
- Basic team information by division (no ESPN standings)
- Complete matchup analysis with player performance
- Injury tracking for starters
- Comprehensive awards system with detailed metrics
- Optimal lineup calculations and efficiency percentages

#### Enhanced JSON (`output/enhanced/`) - Stage 2 Output
- **Current Week Data**: Full raw weekly report with computed team standings
- **Season Context**: Multi-week historical data aggregation, computed standings, and analytics
  - **`team_standings`**: Computed team standings with wins/losses/points/ranks calculated from matchup history
  - **`weekly_statistics.weeks`**: Array of individual week statistics (median, average, max/min, efficiency) for template iteration
  - **`running_totals`**: Cumulative team performance across all weeks (actual vs projected vs optimal scoring)
  - **`performance_trends`**: Cross-week team metrics, league averages, and season progression
  - **`matchup_history`**: Historical matchup patterns, blowouts, close games, and season summary statistics
  - **`award_summaries`**: Season-long award tracking with winner history across multiple weeks
- **Multi-Week Analytics**: Comprehensive cross-week calculations and trends
- **Metadata**: Aggregation timestamps, DynamoDB record IDs, historical weeks included, total weeks processed, data source tracking

#### HTML Files (`output/html/`) - Stage 4 Output
- **Responsive HTML**: Mobile-friendly fantasy football reports with computed historical standings
- **Team Standings**: Division rankings with computed wins/losses/points and logos, sortable columns
- **Running Totals Table**: Season-long efficiency tracking showing actual vs optimal scores across all weeks
- **Weekly Totals Table**: Multi-week statistical breakdown showing individual week data (Week 1, Week 2, etc.) with median, average, max/min scores, and efficiency metrics
- **Weekly Summary Table**: Current week team performance with win/loss results and score margins
- **Interactive Features**: JavaScript-powered sortable tables with visual indicators
- **Smart Table Design**: Optimized column widths and median divider rows
- **Weekly Awards**: All 11 award categories with detailed descriptions
- **Matchup Analysis**: Game summaries with projected vs actual scores
- **Player Performance**: Starter tables with injury indicators

#### Pipeline Logs (`output/logs/`)
- **Execution Tracking**: Stage-by-stage execution details
- **Performance Metrics**: Timing information for each stage
- **Error Handling**: Comprehensive error logs and status tracking
- **Metadata**: Pipeline execution IDs, timestamps, configuration used

## Debugging & Troubleshooting

### Common Issues

#### ESPN-Related (All Commands)
1. **ESPN Authentication**:
   - Ensure `config/secrets.yaml` exists with valid cookies
   - Cookies expire periodically and need refreshing
2. **League Access**: Verify league ID and user permissions
3. **Missing Data**: Some weeks may have incomplete ESPN data
4. **Rate Limiting**: ESPN may throttle requests

#### Pipeline-Specific Issues
5. **AWS Credentials**:
   - Stages 2 and 5 will fail without valid AWS credentials
   - Check AWS CLI configuration: `aws sts get-caller-identity`
   - Ensure proper DynamoDB and S3 permissions
6. **DynamoDB Issues**:
   - Table `fantasy-league-data` must exist or Stage 2 will fail with ResourceNotFoundException
   - Check AWS region configuration (defaults to `us-east-1`)
   - Verify DynamoDB permissions for PutItem operations
7. **Pipeline Stage Dependencies**:
   - Each stage requires output from previous stage
   - Use `--verbose` flag to see detailed execution logs
   - Check `output/logs/` for pipeline execution details
8. **S3 Deploy Issues**:
   - Stage 5 requires valid AWS credentials and S3/CloudFront permissions
   - S3 bucket `will.moore.fyi` must be accessible
   - CloudFront distribution `E10BJV5LJCPKIE` must exist
   - Use `--dry-run` for testing deployment workflow without AWS calls

### Testing Considerations
- **Award Tests**: Comprehensive negative case testing in `tests/test_award_calculations.py`
- **Multi-Week Data Aggregation Tests**: Comprehensive coverage of historical data processing and cross-week analytics
  - **Aggregate Stage**: 22 tests covering DynamoDB historical fetching, multi-week calculations, type conversion, and error handling (`tests/test_aggregate_stage.py`)
    - `test_fetch_historical_data_*`: 7 tests for DynamoDB integration (success, credentials, table not found, league mismatch, etc.)
    - `test_calculate_multi_week_*`: 5 tests for cross-week analytics (team performance, running totals, award summaries, statistics)
    - `test_convert_decimal_to_float`: Type conversion and compatibility testing
  - **HTML Generator Multi-Week**: 11 tests for template rendering and data preparation (`tests/test_templated_html_generator_multiweek.py`)
    - `test_get_week_statistics_data_*`: Multi-week data handling, fallbacks, and edge cases
    - `test_template_variables_*`: Template variable preparation for multi-week iteration
    - `test_integration_*`: End-to-end template variable preparation with enhanced data structures
- **Running Totals Tests**: Full coverage of calculation logic, error handling, and data structure variations
  - **HTML Generator**: Tests data preparation, sorting, fallback calculations (`tests/test_templated_html_generator_running_totals.py`)
  - **Generate Stage**: Tests enhanced vs raw data handling, full data structure passing
- **Weekly Summary Tests**: Complete coverage of current week performance analysis
  - **Data Preparation**: Tests team scoring, win/loss determination, margin calculations (`tests/test_templated_html_generator_weekly_summary.py`)
  - **Edge Cases**: Tie games, single matchups, no matchups, margin formatting
  - **Median Calculation**: Tests median score calculation with even and odd number of teams
  - **Template Integration**: Validates proper data flow to template rendering system
- **Frontend Features**: Interactive table sorting and template rendering validation
- **Mock ESPN Client**: Tests use mocked ESPN API to avoid external dependencies
- **Edge Cases**: Zero scores, ties, missing optimal data, empty player lists, malformed data structures
- **Pipeline Coverage**: 127 total tests with comprehensive stage-by-stage validation and multi-week functionality

## File Structure
```
├── src/
│   ├── fantasy_extractor.py     # Main orchestrator class
│   ├── models/data_models.py    # Pydantic data models
│   ├── extractors/              # Data extraction modules
│   ├── pipeline/                # 5-stage data pipeline (refactored into modules)
│   │   ├── __init__.py          # Clean public API exports
│   │   ├── orchestrator.py      # Pipeline coordination and management
│   │   ├── base.py              # Abstract PipelineStage base class (48 lines)
│   │   ├── extract_stage.py     # Stage 1: ESPN data extraction (80 lines)
│   │   ├── upload_stage.py      # Stage 2: DynamoDB upload (156 lines)
│   │   ├── aggregate_stage.py   # Stage 3: Data aggregation (307 lines)
│   │   ├── generate_stage.py    # Stage 4: HTML generation (75 lines)
│   │   └── deploy_stage.py      # Stage 5: S3 deployment (178 lines)
│   ├── generators/              # HTML generation and templates
│   └── utils/                   # Config, ESPN client, date utilities
├── tests/
│   ├── test_data_models.py      # Model validation tests
│   ├── test_award_calculations.py # Award calculation negative case tests
│   ├── test_aggregate_stage.py  # Multi-week aggregation and running totals tests (22 tests)
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
│   ├── html/                    # Stage 4: Generated HTML files
│   └── logs/                    # Pipeline execution logs
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

### Standings Calculation Refactor (December 2025)
- **Historical Accuracy Implementation**: Complete refactor to calculate team standings from matchup data instead of ESPN API
- **Pipeline Reordering**: Changed stage order from Extract → Upload → Aggregate → Generate → Deploy to Extract → Aggregate → Upload → Generate → Deploy
- **Data Model Changes**: Removed ESPN standings fields (`wins`, `losses`, `ties`, `points_for`, `points_against`, `overall_rank`, `division_rank`) from Team model
- **Team Extractor Refactor**: Now extracts only basic team information (id, name, owner, division, logo) without ESPN standings
- **Aggregate Stage Enhancement**: Added `_calculate_team_standings()` method that computes cumulative standings from historical matchup data
- **Ranking Algorithm**: Teams ranked by (1) wins, (2) losses, (3) points for, (4) points against for consistent historical accuracy
- **HTML Generator Updates**: Modified to merge computed standings with team data during template rendering
- **Upload Stage Updates**: Enhanced to handle enhanced JSON structure with computed standings
- **Comprehensive Testing**: Added 12 new tests covering standings calculation, HTML integration, and model refactor (total: 139 tests)

### Honorable Mentions System for Awards (September 2025)
- **Award Selection Enhancement**: McCollapse and Clapper Collapse awards now select only the top team based on greatest statistical difference
  - **McCollapse**: Ranked by greatest difference between optimal and actual scores (`optimal_score - actual_score`)
  - **Clapper Collapse**: Ranked by greatest difference between projected and actual scores (`projected_score - actual_score`)
- **Honorable Mentions Section**: Additional eligible teams are displayed in a dedicated "Honorable Mentions" section after the main awards
  - **Format**: "Award Full Name: Team Name - Statistics" (e.g., "Mike McCoy 'McCollapse' Award: Team Name - Actual: 87.50, vs. Optimal: 119.94")
  - **Styling**: Clean list format with left border accent and responsive mobile design
- **Data Model Updates**: Added `HonorableMention` model and `honorable_mentions` field to `WeeklyAwards`
- **Template Integration**: New `honorable_mentions.html` template included in weekly stats section
- **Comprehensive Testing**: 5 new test cases covering single/multiple team scenarios and mixed award types

### Multi-Week Historical Data Aggregation (September 2025)
- **Historical Data Fetching**: Stage 3 (Aggregate) now automatically retrieves all previous weeks from current season via DynamoDB
  - **`_fetch_historical_data()`**: Intelligent querying for weeks 1 through (current_week - 1) with league ID validation
  - **DynamoDB Integration**: Seamless integration with existing upload schema using `season_week` keys
  - **Type Conversion**: Automatic conversion of DynamoDB Decimal objects to float using `_convert_decimal_to_float()`
  - **Error Handling**: Graceful degradation for AWS credential issues, missing tables, or network failures
- **Cross-Week Analytics**: Comprehensive multi-week calculation methods for season-long insights
  - **Team Performance**: Multi-week averages, league statistics, highest/lowest scores across all weeks
  - **Running Totals**: Cumulative actual vs projected vs optimal scoring for comprehensive team analysis
  - **Weekly Statistics**: Individual week breakdowns (median, average, max/min, efficiency) for Weekly Totals table
  - **Award Summaries**: Season-long award winner tracking with historical context
  - **Matchup History**: Cross-week blowouts, close games, and season summary statistics
- **Enhanced JSON Structure**: Comprehensive `season_context` expansion with multi-week data
  - **`weekly_statistics.weeks`**: Array of individual week statistics enabling template iteration over multiple weeks
  - **`running_totals`**: Multi-week cumulative team performance data
  - **`performance_trends`**: Cross-week analytics, league averages, and progression metrics
  - **`metadata`**: Tracks `historical_weeks_included`, `total_weeks_processed`, and `data_source` type
- **Template Rendering Enhancements**: Updated HTML generator for multi-week display capabilities
  - **`_get_week_statistics_data()`**: Intelligent use of pre-calculated weekly statistics from enhanced JSON
  - **Weekly Totals Table**: Now displays multiple rows (Week 1, Week 2, etc.) instead of current week only
  - **Template Variables**: New `all_weeks_stats` array enables dynamic week iteration in templates
  - **Backward Compatibility**: Graceful fallback to current-week-only calculation when enhanced data unavailable
- **Comprehensive Testing**: 23 new tests covering all aspects of multi-week functionality
  - **`test_aggregate_stage.py`**: 12 new tests for historical fetching, multi-week calculations, and type conversion
  - **`test_templated_html_generator_multiweek.py`**: 11 new tests for template rendering and data preparation
  - **Total Coverage**: 127 tests ensuring robust multi-week functionality with comprehensive edge case handling

### Interactive HTML Features & Weekly Summary (September 2025)
- **Sortable Tables**: JavaScript-powered interactive column headers for all data tables
  - **Visual Indicators**: Sort direction arrows (⇅ → ↑ → ↓) with hover effects and blue underline animation
  - **Smart Detection**: Automatic numeric vs string sorting with proper data type handling
  - **Universal Application**: Works on all `.standings-table` elements, opt-out with `data-no-sort`
  - **Implementation**: `src/generators/templates/scripts.js` and `src/generators/templates/styles.css`
- **Running Totals Table**: Comprehensive season-long efficiency tracking
  - **Efficiency Calculation**: (actual points / optimal points) * 100 for each team
  - **Data Sources**: Enhanced JSON from `season_context.running_totals` with fallback calculation
  - **Visual Design**: Matches Overall League Standings (background logos, team colors, consistent styling)
  - **Default Sorting**: Orders by efficiency (highest to lowest) for immediate insights
  - **Implementation**: `src/pipeline/aggregate_stage.py:_calculate_running_totals()` and `src/generators/templated_html_generator.py:_prepare_running_totals_data()`
- **Weekly Summary Table**: Current week team performance analysis and ranking
  - **Performance Metrics**: All teams ranked by score with win/loss results and score margins vs opponents
  - **Median Indicator**: League median score displayed as divider row between positions 6 and 7
  - **Result Formatting**: Full text ("Win", "Loss", "Tie") with precise margin calculations ("+12.50", "-45.26")
  - **Non-Sortable Design**: Fixed ranking maintains current week context with `data-no-sort` attribute
  - **Implementation**: `src/generators/templated_html_generator.py:_prepare_weekly_summary_data()` with comprehensive edge case handling
- **Smart Table Styling**: Optimized layout and visual enhancements
  - **Numeric Columns**: 50px max-width constraint prevents overly wide columns and improves table proportions
  - **Divider Rows**: Gray background with italic styling for median indicators and special separators
  - **Responsive Design**: All interactive features maintain functionality across screen sizes
- **Enhanced Testing**: 28 new tests covering table functionality, data preparation, and edge cases
  - **`tests/test_aggregate_stage.py`**: 10 tests for running totals calculation logic
  - **`tests/test_templated_html_generator_running_totals.py`**: 10 tests for HTML generator running totals data preparation
  - **`tests/test_templated_html_generator_weekly_summary.py`**: 8 tests for weekly summary functionality including tie games, median calculation, and margin formatting
  - **Total Coverage**: 104 tests across all functionality with comprehensive validation

### Major Pipeline Implementation (Latest)
- **5-Stage Data Pipeline**: Complete end-to-end processing from ESPN API to deployed websites
- **Pipeline Orchestrator**: `src/pipeline/orchestrator.py` - Comprehensive stage coordination, error handling, and progress tracking
- **Pipeline Stages**: Modular stage implementation with clean separation
- **CLI Integration**: Added `pipeline` command group with 8 subcommands including new `generate` command
- **AWS Integration**: DynamoDB storage with boto3, intelligent fallback to mock mode
- **Enhanced JSON**: Season context, historical analytics, and performance trends in Stage 3 output
- **HTML Generation**: Stage 4 uses existing templated HTML generator for responsive reports
- **Development Features**: Dry-run mode, comprehensive logging, individual stage execution

### Pipeline Stages Refactor (September 2025)
- **Modular Architecture**: Refactored monolithic 877-line `src/pipeline/stages.py` into clean, maintainable modules
- **Single Responsibility**: Each stage now has its own module with clear purpose and manageable size
- **Clean Imports**: Updated import structure for better IDE support and reduced coupling
- **Module Structure**:
  - `base.py` - Abstract PipelineStage class (48 lines)
  - `extract_stage.py` - ESPN data extraction (80 lines)
  - `upload_stage.py` - DynamoDB upload (156 lines)
  - `aggregate_stage.py` - Data aggregation (307 lines)
  - `generate_stage.py` - HTML generation (75 lines)
  - `deploy_stage.py` - S3 deployment (178 lines)
- **Backward Compatibility**: Maintained same public API, all imports and tests work unchanged
- **Better Navigation**: Find specific stage logic immediately without scrolling through 800+ lines

### Clean Command Enhancement (September 2025)
- **Mutually Exclusive Options**: `--keep-days` and `--keep-latest` are now mutually exclusive for cleaner behavior
- **Clear Retention Policies**: Choose either age-based (`--keep-days N`) or count-based (`--keep-latest N`) retention
- **Default Behavior**: Defaults to `--keep-days 7` if no options provided
- **Updated Documentation**: Clear examples and help text for both retention strategies

### Code Cleanup (September 2025)
- **Removed Duplicate HTML Generator**: Deleted `src/generators/html_generator.py` (1,524 lines) - superseded by `TemplatedFantasyHTMLGenerator`
- **Removed Logo Validation**: Deleted `src/utils/logo_validator.py` - server-side validation disabled in favor of client-side
- **Removed Debug Scripts**: Deleted `debug_team_data.py` and `debug_standings.py` - development utilities no longer needed
- **Removed Duplicate CLI Commands**: Removed standalone `extract` and `generate-html` commands - use `pipeline extract` and `pipeline generate` instead
- **Streamlined CLI**: Main commands are now `pipeline` (primary), `info`, `validate`, `config`, `week`, `clean` (utilities)

### Previous Fixes
- **Fixed Award Bug**: Tie games no longer incorrectly assign winners/losers
- **Added Negative Case Tests**: Comprehensive testing for all award scenarios where no qualifying teams exist
- **Updated Award Descriptions**: Added "Accidental Genius" award to prompt template
- **Enhanced Data Models**: Full Pydantic validation with optional fields and default lists
- **Clean Command**: Added comprehensive output directory cleanup functionality with smart retention policies

### Pipeline Status
- ✅ **Stage 1 (Extract)**: Complete - ESPN data extraction using existing functionality
- ✅ **Stage 2 (Upload)**: Complete - DynamoDB storage with schema versioning (requires AWS resources)
- ✅ **Stage 3 (Aggregate)**: Complete - Enhanced JSON with season analytics and context
- ✅ **Stage 4 (Generate)**: Complete - HTML generation using existing templated HTML generator
- ✅ **Stage 5 (Deploy)**: Complete - S3 upload with CloudFront cache invalidation
- ⚠️  **Configuration**: Pipeline config sections need to be added to config files
- ✅ **Stage 2 Testing**: Comprehensive unit tests implemented (10 test cases covering DynamoDB upload)
- ✅ **Stage 4 Testing**: Comprehensive unit tests implemented (12 test cases covering HTML generation)
- ✅ **Stage 5 Testing**: Comprehensive unit tests implemented (10 test cases covering S3 upload and CloudFront)
- ⚠️  **End-to-End Testing**: Full pipeline integration testing framework needed

### Development Mode Removed
- ❌ **No Automatic Fallbacks**: Stages fail properly when AWS resources unavailable
- ✅ **Dry-Run Mode**: Use `--dry-run` flag for testing without AWS
- ✅ **Individual Stages**: Run stages 1, 3, and 4 independently for development