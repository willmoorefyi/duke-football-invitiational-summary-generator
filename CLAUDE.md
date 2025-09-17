# Claude Code Context - Fantasy Football Summary Generator

## Application Overview

This is the **Duke Football Invitational Summary Generator** - a Python application that extracts structured data from ESPN Fantasy Football leagues and processes it through a comprehensive 5-stage data pipeline, generating enhanced reports and deployed websites designed for creating humorous, engaging summaries.

### Core Purpose
- Extract fantasy football data from ESPN leagues via API
- Process data through a full 5-stage pipeline: Extract → Upload → Aggregate → Generate → Deploy
- Generate structured JSON reports and enhanced season analytics for LLM analysis
- Deploy static websites with comprehensive league data and visualizations
- Store historical data in DynamoDB for season-long trends and analytics
- Create witty weekly summaries in the style of comedians like Mitch Hedberg and Norm MacDonald
- Track elaborate weekly awards and achievements with historical context

## Key Architecture Components

### 1. Pipeline Architecture (`src/pipeline/`)
- **5-Stage Pipeline**: Complete data processing from ESPN API to deployed websites
  - **Stage 1 - Extract**: ESPN data extraction using existing `FantasyFootballExtractor`
  - **Stage 2 - Upload**: DynamoDB storage with schema versioning and AWS integration
  - **Stage 3 - Aggregate**: Season context creation with historical data and analytics
  - **Stage 4 - Generate**: HTML generation using existing templated HTML generator
  - **Stage 5 - Deploy**: S3 deployment with CloudFront integration
- **Orchestrator**: `src/pipeline/orchestrator.py:48` - `PipelineOrchestrator` class manages execution
- **Stages**: `src/pipeline/stages.py` - Individual stage implementations with dependency management

### 2. Main Entry Points
- **CLI Tool**: `./fantasy-extractor` - Command-line interface for all operations
  - **Simple Commands**: `extract`, `info`, `generate-html` (original functionality)
  - **Pipeline Commands**: `pipeline run`, `pipeline extract`, `pipeline generate`, `pipeline status` (new functionality)
- **Python API**: `src/fantasy_extractor.py:16` - Main `FantasyFootballExtractor` class
- **Pipeline API**: `src/pipeline/orchestrator.py:48` - `PipelineOrchestrator` class
- **Config**: `config/config.yaml` and `config/secrets.yaml` for settings and authentication

### 3. Data Models (`src/models/data_models.py`)
- **Core Models**: `Team`, `Player`, `Matchup`, `Division`, `WeeklyReport`
- **Award Models**: `PlayerAward`, `TeamAward`, `LineupEfficiencyAward`, `CollapseAward`, `ProjectionFailAward`
- **Enums**: `InjuryStatus` for player health tracking
- All models use Pydantic for validation and JSON serialization

### 4. Data Extraction (`src/extractors/`)
- **TeamExtractor**: Handles team standings and division data
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

#### Collapse Awards (Lists)
- **McCollapse**: Teams that would've won with optimal lineup but lost
- **Clapper Collapse**: Teams projected to win but lost

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
./fantasy-extractor generate-html report.json

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

### DynamoDB Upload Implementation (`src/pipeline/stages.py:148`)
- **Schema Alignment**: Refactored to match CloudFormation template (`season_week` + `data_type_id` primary key)
- **Multi-Record Strategy**: Creates 1 main record + N team records per upload for optimal GSI performance
- **Data Transformation**: Recursive float-to-Decimal conversion for DynamoDB compatibility
- **Error Handling**: Comprehensive exception handling with detailed logging and metadata tracking
- **Testing Coverage**: 10 comprehensive unit tests covering success, failure, and edge cases

### S3 Deploy Implementation (`src/pipeline/stages.py:699-878`)
- **S3 Upload**: Deploys HTML files to `will.moore.fyi` S3 bucket with standardized naming conversion
- **CloudFront Integration**: Automatic cache invalidation using distribution `E10BJV5LJCPKIE` for immediate updates
- **Filename Processing**: Converts timestamped files (`fantasy_report_week_5_20250915_142530.html`) to standardized format (`fantasy_report_2025_week_5.html`)
- **Error Handling**: Comprehensive AWS service error handling with graceful CloudFront failure (deployment succeeds with warning)
- **Testing Coverage**: 10 comprehensive unit tests covering S3 upload, CloudFront invalidation, error scenarios, and edge cases
- **Configuration**: Pre-configured for `will.moore.fyi` bucket with `duke-football-invitational/weekly-reports/` path structure
- **Cache Management**: 1-hour TTL with automatic invalidation ensures immediate visibility of updates

### Data Flow

#### Simple Extraction (Original)
1. **Authentication** → ESPN cookies for private league access
2. **Week Calculation** → Automatic NFL week determination (Thursday-Wednesday schedule)
3. **Data Extraction** → Team standings, matchups, player performance
4. **Analysis** → Projected vs actual scores, optimal lineups, efficiency metrics
5. **Awards** → Calculate all 11 award categories with negative case handling
6. **Output** → Structured JSON saved to `output/` directory

#### Pipeline Flow (New)
1. **Stage 1 - Extract** → ESPN data extraction → Raw JSON (`output/raw/`)
2. **Stage 2 - Upload** → DynamoDB storage with schema versioning
3. **Stage 3 - Aggregate** → Historical data combination → Enhanced JSON (`output/enhanced/`)
4. **Stage 4 - Generate** → HTML generation → HTML Files (`output/html/`)
5. **Stage 5 - Deploy** → S3 upload + CloudFront invalidation → Live URL
6. **Logging** → Pipeline execution logs saved to `output/logs/`

#### Pipeline Architecture
```
ESPN API → [Extract] → Raw JSON → [Upload] → DynamoDB
                                      ↓
                                 [Aggregate] → Enhanced JSON
                                      ↑              ↓
                             Historical Data    [Generate] → HTML Files
                                                      ↓
                                CloudFront ← [Deploy] ← S3 Bucket
```

### Output Formats

#### Raw JSON (`output/raw/`) - Stage 1 Output
- League standings by division with rankings
- Complete matchup analysis with player performance
- Injury tracking for starters
- Comprehensive awards system with detailed metrics
- Optimal lineup calculations and efficiency percentages

#### Enhanced JSON (`output/enhanced/`) - Stage 3 Output
- **Current Week Data**: Full raw weekly report
- **Season Context**: Historical standings progression, matchup statistics
- **Award Summaries**: Season-long award tracking and analytics
- **Performance Trends**: Team metrics, league averages, performance analytics
- **Metadata**: Aggregation timestamps, DynamoDB record IDs, data source tracking

#### HTML Files (`output/html/`) - Stage 4 Output
- **Responsive HTML**: Mobile-friendly fantasy football reports
- **Team Standings**: Division rankings with logos and records
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
- **Mock ESPN Client**: Tests use mocked ESPN API to avoid external dependencies
- **Edge Cases**: Zero scores, ties, missing optimal data, empty player lists

## File Structure
```
├── src/
│   ├── fantasy_extractor.py     # Main orchestrator class
│   ├── models/data_models.py    # Pydantic data models
│   ├── extractors/              # Data extraction modules
│   ├── pipeline/                # 5-stage data pipeline
│   │   ├── orchestrator.py      # Pipeline coordination and management
│   │   └── stages.py            # Pipeline stage implementations (Extract, Upload, Aggregate, Generate, Deploy)
│   ├── generators/              # HTML generation and templates
│   └── utils/                   # Config, ESPN client, date utilities
├── tests/
│   ├── test_data_models.py      # Model validation tests
│   ├── test_award_calculations.py # Award calculation negative case tests
│   ├── test_generate_stage.py   # HTML generation stage tests
│   ├── test_upload_stage.py     # DynamoDB upload stage tests
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

## Recent Changes & Fixes

### Major Pipeline Implementation (Latest)
- **5-Stage Data Pipeline**: Complete end-to-end processing from ESPN API to deployed websites
- **Pipeline Orchestrator**: `src/pipeline/orchestrator.py` - Comprehensive stage coordination, error handling, and progress tracking
- **Pipeline Stages**: `src/pipeline/stages.py` - Five implemented stages (Extract, Upload, Aggregate, Generate, Deploy)
- **CLI Integration**: Added `pipeline` command group with 8 subcommands including new `generate` command
- **AWS Integration**: DynamoDB storage with boto3, intelligent fallback to mock mode
- **Enhanced JSON**: Season context, historical analytics, and performance trends in Stage 3 output
- **HTML Generation**: Stage 4 uses existing templated HTML generator for responsive reports
- **Development Features**: Dry-run mode, comprehensive logging, individual stage execution

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