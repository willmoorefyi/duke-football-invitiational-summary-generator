# Fantasy Football Data Extractor

Extract structured data from ESPN Fantasy Football leagues for LLM analysis and witty weekly summaries.

## Overview

This Python application extracts comprehensive fantasy football data from ESPN leagues and outputs it in a structured JSON format designed for LLM analysis. The extracted data includes team standings, matchup results, player performances, and injury information.

## Features

- **5-Stage Data Pipeline**: Complete end-to-end processing from ESPN API to deployed websites
  - **Stage 1 - Extract**: ESPN data extraction (team info, matchups, players - no standings)
  - **Stage 2 - Aggregate**: Calculate historical standings from matchup data and season analytics
  - **Stage 3 - Upload**: DynamoDB storage with computed standings and schema versioning
  - **Stage 4 - Generate**: HTML generation using computed standings
  - **Stage 5 - Deploy**: S3 deployment with automatic CloudFront cache invalidation
- **Historical Standings Calculation**: Compute accurate team standings from matchup results for any historical week
- **Team Data**: Extract basic team information (name, owner, division, logo) - standings calculated from game results
- **Matchup Results**: Get weekly matchup data with scores and winners/losers
- **Player Performance**: Extract projected vs actual scores for all players with detailed statistics (QB: completions/attempts, passing/rushing yards and TDs; RB: rushing attempts, yards, TDs, receptions; WR/TE: receptions, receiving yards, TDs, targets; K: FG/XP made/attempted; D/ST: defensive stats)
- **Injury Tracking**: Identify starters who are currently injured
- **Weekly Awards**: Calculate 11 different weekly awards (MVP, MWP, SSL, McCollapse, etc.) with honorable mentions system for multiple eligible teams
- **Ranking Algorithm**: Teams ranked by (1) wins, (2) losses, (3) points for, (4) points against for consistent historical accuracy
- **HTML Website Generator**: Create shareable HTML reports using Jinja2 templates with league standings, awards, and game summaries
- **Cloud Integration**: DynamoDB for persistence, S3 for hosting, CloudFront for distribution
- **Season Analytics**: Multi-week historical data aggregation, standings progression, matchup statistics, and performance trends
- **Division Strength Analysis**: Inter-division performance rankings with visual team representation and sortable metrics
- **Multi-Week Data Processing**: Automatic historical data fetching from DynamoDB for comprehensive season context
- **Weekly Statistics**: Individual week statistics tracking with cumulative season analysis
- **Development Features**: Dry-run mode, comprehensive logging, individual stage execution
- **Flexible Dating**: Extract data for specific weeks or dates
- **CLI Interface**: Easy-to-use command-line interface with both simple commands and full pipeline
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

**Key Dependencies:**
- `espn-api`: ESPN Fantasy Sports API wrapper
- `pydantic`: Data validation and serialization
- `click`: Command-line interface framework
- `jinja2`: Template engine for HTML generation
- `markupsafe`: HTML escaping and safety utilities
- `boto3`: AWS SDK for DynamoDB and S3 integration

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

### Pipeline Architecture

The application now includes a full **5-stage data pipeline** that processes ESPN league data through extraction, storage, aggregation, HTML generation, and deployment:

#### Pipeline Overview

```
ESPN API → [Extract] → Raw JSON → [Aggregate] → Enhanced JSON
                                      ↑              ↓
                                Historical Data   [Upload] → DynamoDB
                                                      ↓
                                                 [Generate] → HTML Files
                                                      ↓
                                 CloudFront ← [Deploy] ← S3 Bucket
```

**Stage 1: Extract** - ESPN data extraction (team info, matchups, players - no ESPN standings)
**Stage 2: Aggregate** - Calculate historical standings from matchup data, multi-week analytics, and season context
**Stage 3: Upload** - DynamoDB storage of enhanced JSON with computed standings
**Stage 4: Generate** - HTML generation using computed standings from aggregate stage
**Stage 5: Deploy** - S3 deployment with CloudFront cache invalidation

#### Pipeline Commands

##### Run Full Pipeline
```bash
# Execute all 5 stages in sequence
./fantasy-extractor pipeline run 123456 --week 5     # with league ID
./fantasy-extractor pipeline run --week 5            # uses league_id from config

# Run with options
./fantasy-extractor pipeline run --dry-run           # simulate without changes
./fantasy-extractor pipeline run --verbose           # detailed logging
./fantasy-extractor pipeline run --output-dir custom # custom base output directory
```

##### Individual Pipeline Stages
```bash
# Stage 1: Extract ESPN data
./fantasy-extractor pipeline extract --week 5
# Output: output/raw/raw_week_5_TIMESTAMP.json

# Stage 2: Aggregate with historical standings calculation
./fantasy-extractor pipeline aggregate output/raw/raw_week_5_TIMESTAMP.json
# Output: output/enhanced/enhanced_week_5_TIMESTAMP.json

# Stage 3: Upload enhanced data to DynamoDB
./fantasy-extractor pipeline upload output/enhanced/enhanced_week_5_TIMESTAMP.json
# Output: DynamoDB record ID

# Stage 4: Generate HTML website
./fantasy-extractor pipeline generate output/enhanced/enhanced_week_5_TIMESTAMP.json
# Output: output/html/fantasy_report_week_5_TIMESTAMP.html

# Stage 5: Deploy to S3
./fantasy-extractor pipeline deploy output/html/fantasy_report_week_5_TIMESTAMP.html
# Output: CloudFront URL
```

##### Pipeline Monitoring
```bash
# View pipeline execution status
./fantasy-extractor pipeline status [execution_id]

# View pipeline logs
./fantasy-extractor pipeline logs
./fantasy-extractor pipeline logs --stage extract
./fantasy-extractor pipeline logs --execution-id pipeline_123456_20241015_120000
```

#### Pipeline Features

**🔄 Stage Orchestration**
- Automatic dependency management between stages
- Data flow validation and error handling
- Progress tracking and execution logging
- Rollback capabilities for failed deployments

**☁️ Cloud Integration**
- DynamoDB for historical data persistence
- S3 bucket deployment for static websites
- CloudFront integration for fast global access
- Intelligent fallbacks for development environments

#### DynamoDB Upload Stage Details

**Stage 3: Upload** transforms enhanced JSON data (with computed standings) into a DynamoDB-optimized schema with multiple record types:

**Schema Design:**
- **Primary Key**: `season_week` (partition) + `data_type_id` (sort)
- **GSI1**: `team_id` + `season_week` for team-based queries
- **GSI2**: `team_name` + `season_week` for name-based queries

**Record Types Created:**
1. **Main Weekly Report** (`data_type_id: "weekly_report"`)
   - Complete enhanced JSON data from aggregate stage
   - Computed team standings, full season context, matchups, and awards
   - Example: `season_week="2025-01"` + `data_type_id="weekly_report"`

2. **Individual Team Records** (`data_type_id: "team_{team_id}"`)
   - One record per team for efficient GSI queries
   - Computed team standings, performance metrics, division info
   - Example: `season_week="2025-01"` + `data_type_id="team_3"`

**Data Transformations:**
- Float values converted to Decimal for DynamoDB compatibility
- Nested JSON structures preserved with proper typing
- Metadata includes upload timestamps and schema versioning

**Upload Process:**
```bash
# Upload creates multiple DynamoDB records from enhanced JSON
./fantasy-extractor pipeline upload output/enhanced/enhanced_week_1_20250915.json

# Creates records like:
# 1. Main record: season_week="2025-01" + data_type_id="weekly_report"
# 2. Team records: season_week="2025-01" + data_type_id="team_1", "team_2", etc.
```

**Query Capabilities:**
- Get all data for a specific week: Query by `season_week`
- Get team history: Query GSI1 by `team_id`
- Search teams by name: Query GSI2 by `team_name`

**📊 Enhanced Data Processing**
- Season context and standings progression
- Historical matchup records and analytics
- Award summaries across multiple weeks
- Performance trends and team metrics

**🏆 Multi-Week Historical Data Aggregation**
- **Automatic Historical Fetching**: Stage 3 automatically retrieves all previous weeks from current season via DynamoDB
- **Cross-Week Analytics**: Team performance trends, cumulative statistics, and season progression analysis
- **Weekly Statistics Table**: Individual week breakdowns showing median, average, max/min scores, and efficiency metrics for each week
- **Enhanced JSON Structure**: Includes `season_context.weekly_statistics.weeks` array for template iteration
- **Type Safety**: Automatic conversion of DynamoDB Decimal values to float for JavaScript/template compatibility
- **Intelligent Fallback**: Graceful degradation to current-week-only when historical data unavailable

**🛠️ Development & Testing**
- Dry-run mode for safe testing
- Mock implementations for local development
- Comprehensive logging and status tracking
- Individual stage execution for debugging

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

#### Generate HTML Report
```bash
# Generate HTML website from JSON report (auto-names output file)
./fantasy-extractor pipeline generate output/fantasy_report_week_1_2025-09-10.json

# Generate with custom output directory
./fantasy-extractor pipeline generate report.json --output-dir custom/

# The generated HTML includes:
# - Overall league standings with team logos and sortable columns
# - Weekly totals table with multi-week historical data (Week 1, Week 2, etc.) and lineup accuracy with interactive sorting
# - Division strength table showing inter-division performance rankings with team logos (140px width, responsive)
# - Weekly summary table with current week team performance, win/loss results, and margins
# - Strength of schedule table showing opponent difficulty rankings with points against analysis and percentage vs league average
# - All 11 weekly awards (MVP, MWP, SSL, McCollapse, etc.) with honorable mentions for multiple eligible teams and detailed player statistics (passing/rushing/receiving stats)
# - Detailed game summaries with starter performance
# - Player injury indicators and optimal lineup analysis
# - JavaScript-powered table sorting with grouped row support for maintaining visual relationships
```

**HTML Generator Features:**
- **Jinja2 Templates**: Clean separation of presentation and data logic
- **Responsive Design**: Mobile-friendly layout with flexible grids
- **Team Theming**: Automatic color schemes for each team with accessibility compliance
- **Logo Handling**: Intelligent logo fallback system (🗩 emoji for failed loads)
- **Component Architecture**: Reusable template components for consistent styling
- **Interactive Tables**: Sortable column headers for all data tables with visual indicators and grouped row support
- **Division Strength Analysis**: Inter-division performance rankings with visual team logo representation (140px logos, responsive scaling)
- **Grouped Row Sorting**: Advanced table sorting that keeps related rows together (division + team logo rows)
- **Weekly Summary**: Current week performance ranking with win/loss results and score margins
- **Smart Styling**: Optimized column widths and median divider rows for better readability
- **Client-side Enhancements**: JavaScript for enhanced user experience and intelligent table interactions

**Template System:**
- Templates located in `src/generators/templates/`
- Modular design with separate files for each section
- Easy customization without touching Python code
- See `TEMPLATE_STRUCTURE.md` for complete documentation

#### Deploy to S3
```bash
# Deploy HTML file to S3 with CloudFront cache invalidation
./fantasy-extractor pipeline deploy output/html/fantasy_report_week_5_*.html

# Deploy with dry-run (test without AWS calls)
./fantasy-extractor pipeline deploy report.html --dry-run

# Deploy with detailed logging
./fantasy-extractor pipeline deploy report.html --verbose

# Deploy returns the CloudFront URL for immediate access
# Example output:
# ✓ Deploy completed: https://will.moore.fyi/duke-football-invitational/weekly-reports/fantasy_report_2025_week_5.html
#   CloudFront invalidation: I2J3K4L5M6N7O8P9Q0
```

**Deploy Command Features:**
- **S3 Upload**: Uploads HTML files to `will.moore.fyi` S3 bucket
- **CloudFront Integration**: Automatic cache invalidation for immediate updates
- **Standardized Naming**: Converts timestamped files to `fantasy_report_YYYY_week_N.html` format
- **Error Handling**: Clear error messages with solution guidance for AWS issues
- **Dry-Run Mode**: Test deployment workflow without making actual changes

**AWS Configuration Required:**
- **S3 Bucket**: `will.moore.fyi` (pre-configured)
- **CloudFront Distribution**: `E10BJV5LJCPKIE` (pre-configured)
- **Permissions**: `s3:PutObject`, `cloudfront:CreateInvalidation`
- **Output URL**: `https://will.moore.fyi/duke-football-invitational/weekly-reports/fantasy_report_YYYY_week_N.html`

**Error Handling:**
- **Missing boto3**: Clear installation instructions
- **AWS Credentials**: Guidance for AWS CLI setup
- **S3 Access**: Bucket permission troubleshooting
- **CloudFront Failures**: Deployment succeeds with warning if invalidation fails

#### Clean Output Directory
```bash
# Clean old files from output directory with default settings
./fantasy-extractor clean

# Preview what would be cleaned without actually removing files
./fantasy-extractor clean --dry-run

# Clean with custom retention settings (choose one strategy)
./fantasy-extractor clean --keep-days 14          # Age-based: keep files from last 14 days
./fantasy-extractor clean --keep-latest 3         # Count-based: keep 3 newest per directory

# Clean with detailed output
./fantasy-extractor clean --verbose

# More aggressive cleanup examples
./fantasy-extractor clean --keep-days 2           # Keep only files from last 2 days
./fantasy-extractor clean --keep-latest 1         # Keep only 1 newest file per directory
```

**Clean Command Features:**
- **Flexible Retention Strategies**: Choose age-based (`--keep-days N`, default: 7) OR count-based (`--keep-latest N`) retention
- **Mutually Exclusive Options**: `--keep-days` and `--keep-latest` cannot be used together for clear behavior
- **Directory Management**: Cleans all output subdirectories (`raw/`, `enhanced/`, `html/`, `logs/`)
- **Safety Features**: Never removes directories or protected files (README*, .gitkeep, .gitignore)
- **Dry-Run Mode**: Preview changes before execution with `--dry-run`
- **Detailed Reporting**: Shows file ages, sizes, and cleanup summary

**Directories Cleaned:**
- `output/` - Root output files (test files, old reports)
- `output/raw/` - Raw JSON extracts from Stage 1
- `output/enhanced/` - Enhanced JSON files from Stage 3
- `output/html/` - Generated HTML reports from Stage 4
- `output/logs/` - Pipeline execution logs

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
          "abbreviation": "TN",
          "logo": "https://example.com/logo.png"
          // Note: wins, losses, points_for, points_against, ranks calculated in aggregate stage
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

## Enhanced Output Formats

The pipeline generates two structured JSON outputs for different use cases:

### Raw/Enhanced JSON (Primary Output)
The main output contains comprehensive data with full seasonal context, multi-week analytics, and detailed nested structures designed for complete HTML generation and analysis.

### Condensed JSON (Limited Context Output)
The aggregate stage also generates a **condensed JSON format** optimized for systems with limited context requirements. This format is saved to `output/condensed/` and contains a simplified, flattened structure with:

- **League Information**: Basic league name and current week number
- **Team Standings**: Array of teams sorted by overall rank, including wins/losses/ties, points for/against (rounded), and division rankings
- **Current Week Matchups**: Simplified matchup data with team names, scores (actual/projected/optimal), and player performance
- **Enhanced Matchup Analysis**: Three winning team fields showing actual winner, projected winner, and optimal lineup winner
- **Complete Awards**: All 11 weekly award categories with winner details or `null` when no winner exists
- **Player Data**: Essential player information (name, position, roster slot, scores) organized by team

**Key Benefits:**
- **External System Ready**: Designed for feeding into systems with limited context for human-readable output generation
- **Simplified Structure**: Flattened data format eliminates complex nested objects for easier processing
- **Essential Data Only**: Contains core information needed for summary generation without overwhelming detail

**File Output:**
```bash
# Both formats generated by aggregate stage
output/enhanced/enhanced_week_2_20240915_142530.json   # Full format
output/condensed/condensed_week_2_20240915_142530.json  # Condensed format
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

## AWS Configuration (Pipeline Only)

The pipeline functionality requires AWS credentials for DynamoDB and S3 operations. **Note**: Individual pipeline stages (extract, generate) work without AWS setup.

### AWS Setup Options

1. **AWS CLI Configuration** (recommended):
   ```bash
   # Install AWS CLI
   pip install awscli

   # Configure credentials
   aws configure
   # OR for SSO users
   aws sso login --profile your-profile
   # e.g.
   ### Login to AWS
   aws sso login --profile will-aws-admin
   ```

2. **Environment Variables**:
   ```bash
   export AWS_ACCESS_KEY_ID="your_access_key"
   export AWS_SECRET_ACCESS_KEY="your_secret_key"
   export AWS_DEFAULT_REGION="us-east-1"
   ```

3. **IAM Instance Profile** (for EC2 deployment)

### Required AWS Permissions

For the pipeline to work, your AWS credentials need permissions for:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/fantasy-league-data"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:PutObjectAcl",
                "s3:GetObject"
            ],
            "Resource": "arn:aws:s3:::will.moore.fyi/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "cloudfront:CreateInvalidation"
            ],
            "Resource": "*"
        }
    ]
}
```

### Development Mode

For development and testing without AWS infrastructure:
- **Dry-Run Mode**: Use `--dry-run` flag to simulate pipeline execution without making any changes
- **Individual Stages**: Run stages 1, 3, and 4 independently (`pipeline extract`, `pipeline aggregate`, `pipeline generate`)
- **S3 Deploy Testing**: Use `pipeline deploy --dry-run` to test deployment workflow without AWS

**Note**: Stages 2 and 5 require actual AWS resources (DynamoDB table and S3 bucket) and will fail if not available.

## Historical Standings Accuracy

### Problem Solved
Previously, the application used ESPN's current season standings, which caused **inaccurate historical reporting**:
- Week 5 reports would show current (e.g., Week 10) win-loss records
- Team rankings reflected the entire season, not performance through that specific week
- Historical analysis was impossible with constantly changing ESPN data

### Solution: Computed Historical Standings
**Stage 2 (Aggregate)** now calculates accurate historical standings:
- **Matchup-Based Calculation**: Wins, losses, and points computed from actual game results
- **Week-Specific Accuracy**: Week 5 reports show exactly what standings were after Week 5
- **Historical Consistency**: Past reports remain accurate and don't change over time
- **Ranking Algorithm**: Teams ranked by (1) wins, (2) losses, (3) points for, (4) points against

### Benefits
✅ **Historical Reports**: Past week reports show accurate standings for that point in time
✅ **Season Analysis**: Track how standings evolved week by week
✅ **Data Integrity**: Reports remain consistent and don't change over time
✅ **Flexible Querying**: Generate accurate reports for any historical week

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

# Run specific test categories
pytest tests/test_data_models.py -v
pytest tests/test_award_calculations.py -v
pytest tests/test_standings_calculation.py -v  # New standings calculation tests
pytest tests/test_html_generator_standings.py -v  # HTML generator standings integration
pytest tests/test_team_model_refactor.py -v  # Refactored Team model tests
pytest tests/test_aggregate_stage.py -v  # Includes multi-week aggregation tests
pytest tests/test_templated_html_generator_division_strength.py -v  # Division strength HTML generator tests
pytest tests/test_templated_html_generator_weekly_summary.py -v
pytest tests/test_templated_html_generator_multiweek.py -v  # New multi-week HTML generator tests
```

## Development

### Project Structure
```
fantasy-football-extractor/
├── src/
│   ├── extractors/          # Data extraction modules
│   ├── generators/          # Output generators (HTML, etc.)
│   │   └── templates/       # Jinja2 HTML templates
│   ├── models/              # Pydantic data models
│   ├── pipeline/            # 5-stage data pipeline (modular architecture)
│   │   ├── __init__.py      # Clean public API exports
│   │   ├── orchestrator.py  # Pipeline coordination and management
│   │   ├── base.py          # Abstract PipelineStage base class
│   │   ├── extract_stage.py # Stage 1: ESPN data extraction
│   │   ├── upload_stage.py  # Stage 2: DynamoDB upload
│   │   ├── aggregate_stage.py # Stage 3: Data aggregation
│   │   ├── generate_stage.py # Stage 4: HTML generation
│   │   └── deploy_stage.py  # Stage 5: S3 deployment
│   ├── utils/               # Utilities (config, ESPN client, etc.)
│   ├── cli.py               # Command-line interface
│   └── fantasy_extractor.py # Main orchestrator
├── config/
│   └── config.yaml          # Default configuration
├── output/                  # Generated reports and pipeline data
│   ├── raw/                 # Stage 1: Raw ESPN JSON data
│   ├── enhanced/            # Stage 3: Enhanced JSON with season context
│   ├── html/                # Stage 4: Generated HTML files
│   └── logs/                # Pipeline execution logs
├── tests/                   # Test suite (195 tests total)
│   ├── test_data_models.py      # Model validation tests
│   ├── test_award_calculations.py # Award calculation negative case tests
│   ├── test_standings_calculation.py # New standings calculation tests (5 tests)
│   ├── test_html_generator_standings.py # HTML generator standings integration tests (3 tests)
│   ├── test_team_model_refactor.py # Refactored Team model tests (4 tests)
│   ├── test_aggregate_stage.py   # Multi-week aggregation and division strength tests (37 tests)
│   ├── test_templated_html_generator_division_strength.py # Division strength HTML generator tests (9 tests)
│   ├── test_templated_html_generator_weekly_summary.py # HTML generator weekly summary tests (8 tests)
│   ├── test_templated_html_generator_multiweek.py # Multi-week HTML generator tests (11 tests)
│   ├── test_generate_stage.py   # HTML generation stage tests (15 tests)
│   ├── test_upload_stage.py     # DynamoDB upload stage tests (10 tests)
│   ├── test_deploy_stage.py     # S3 deployment stage tests (10 tests)
│   ├── test_team_logo_extraction.py # Logo extraction tests
│   └── test_clean_command.py    # CLI clean command tests
├── PIPELINE_PLAN.md         # Pipeline architecture documentation
├── TEMPLATE_STRUCTURE.md    # Template system documentation
└── requirements.txt         # Dependencies
```

### Template Customization

The HTML generator uses a modular Jinja2 template system that makes it easy to customize the appearance and layout:

**Modifying Existing Templates:**
1. Edit files in `src/generators/templates/`
2. No Python code changes required
3. Test with existing JSON reports: `./fantasy-extractor pipeline generate report.json`

**Adding New Sections:**
1. Create new template file in `templates/` directory
2. Add data preparation in `TemplatedFantasyHTMLGenerator._prepare_template_variables()`
3. Include template in appropriate parent template
4. Update `TEMPLATE_STRUCTURE.md` documentation

**Template Architecture:**
- `main.html`: Page structure and layout
- `styles.css`: All styling and responsive design
- `scripts.js`: Client-side JavaScript functionality
- Component templates: Reusable sections for awards, tables, etc.
- `team_player_table.html`: Complex reusable component with context variables

See `TEMPLATE_STRUCTURE.md` for complete template documentation and usage patterns.

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