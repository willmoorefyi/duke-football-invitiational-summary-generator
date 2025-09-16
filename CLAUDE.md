# Claude Code Context - Fantasy Football Summary Generator

## Application Overview

This is the **Duke Football Invitational Summary Generator** - a Python application that extracts structured data from ESPN Fantasy Football leagues and processes it through a comprehensive 4-stage data pipeline, generating enhanced reports and deployed websites designed for creating humorous, engaging summaries.

### Core Purpose
- Extract fantasy football data from ESPN leagues via API
- Process data through a full 4-stage pipeline: Extract → Upload → Aggregate → Deploy
- Generate structured JSON reports and enhanced season analytics for LLM analysis
- Deploy static websites with comprehensive league data and visualizations
- Store historical data in DynamoDB for season-long trends and analytics
- Create witty weekly summaries in the style of comedians like Mitch Hedberg and Norm MacDonald
- Track elaborate weekly awards and achievements with historical context

## Key Architecture Components

### 1. Pipeline Architecture (`src/pipeline/`)
- **4-Stage Pipeline**: Complete data processing from ESPN API to deployed websites
  - **Stage 1 - Extract**: ESPN data extraction using existing `FantasyFootballExtractor`
  - **Stage 2 - Upload**: DynamoDB storage with schema versioning and AWS integration
  - **Stage 3 - Aggregate**: Season context creation with historical data and analytics
  - **Stage 4 - Deploy**: HTML generation and S3 deployment with CloudFront integration
- **Orchestrator**: `src/pipeline/orchestrator.py:48` - `PipelineOrchestrator` class manages execution
- **Stages**: `src/pipeline/stages.py` - Individual stage implementations with dependency management

### 2. Main Entry Points
- **CLI Tool**: `./fantasy-extractor` - Command-line interface for all operations
  - **Simple Commands**: `extract`, `info`, `generate-html` (original functionality)
  - **Pipeline Commands**: `pipeline run`, `pipeline extract`, `pipeline status` (new functionality)
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
- **S3 Deployment**: Static website hosting with asset management (Stage 4 - Not Yet Implemented)
- **CloudFront**: Global content delivery network integration (Stage 4 - Not Yet Implemented)
- **Requirements**: Stages 2 and 4 require actual AWS resources and will fail if not available

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
- **Output**: Multiple output directories - `output/raw/`, `output/enhanced/`, `output/logs/`

## Common Tasks & Commands

### Pipeline Operations
```bash
# Run full 4-stage pipeline
./fantasy-extractor pipeline run                    # Current week, uses config league_id
./fantasy-extractor pipeline run --week 5           # Specific week
./fantasy-extractor pipeline run --dry-run          # Test without making changes

# Individual pipeline stages
./fantasy-extractor pipeline extract --week 5       # Stage 1: ESPN extraction
./fantasy-extractor pipeline upload file.json      # Stage 2: DynamoDB upload
./fantasy-extractor pipeline aggregate file.json   # Stage 3: Season aggregation
./fantasy-extractor pipeline deploy enhanced.json  # Stage 4: S3 deployment

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
4. **Stage 4 - Deploy** → HTML generation + S3 upload → CloudFront URL
5. **Logging** → Pipeline execution logs saved to `output/logs/`

#### Pipeline Architecture
```
ESPN API → [Extract] → Raw JSON → [Upload] → DynamoDB
                                      ↓
CloudFront ← [Deploy] ← Enhanced JSON ← [Aggregate]
     ↑                                    ↑
  S3 Bucket                        Historical Data
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
   - Stages 2 and 4 will fail without valid AWS credentials
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
8. **Stage 4 Not Implemented**:
   - Deploy stage will raise NotImplementedError
   - Use `--dry-run` for full pipeline testing without deployment
   - Run stages 1-3 individually for partial pipeline testing

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
│   ├── pipeline/                # 4-stage data pipeline
│   │   ├── orchestrator.py      # Pipeline coordination and management
│   │   └── stages.py            # Pipeline stage implementations (Extract, Upload, Aggregate, Deploy)
│   ├── generators/              # HTML generation and templates
│   └── utils/                   # Config, ESPN client, date utilities
├── tests/
│   ├── test_data_models.py      # Model validation tests
│   └── test_award_calculations.py # Award calculation negative case tests
├── config/
│   ├── config.yaml              # Main configuration
│   └── secrets.yaml             # ESPN authentication (git-ignored)
├── output/                      # Generated reports and pipeline data
│   ├── raw/                     # Stage 1: Raw ESPN JSON data
│   ├── enhanced/                # Stage 3: Enhanced JSON with season context
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
- **4-Stage Data Pipeline**: Complete end-to-end processing from ESPN API to deployed websites
- **Pipeline Orchestrator**: `src/pipeline/orchestrator.py` - Comprehensive stage coordination, error handling, and progress tracking
- **Pipeline Stages**: `src/pipeline/stages.py` - Four implemented stages (Extract, Upload, Aggregate, Deploy)
- **CLI Integration**: Added `pipeline` command group with 7 subcommands
- **AWS Integration**: DynamoDB storage with boto3, intelligent fallback to mock mode
- **Enhanced JSON**: Season context, historical analytics, and performance trends in Stage 3 output
- **Development Features**: Dry-run mode, comprehensive logging, individual stage execution

### Previous Fixes
- **Fixed Award Bug**: Tie games no longer incorrectly assign winners/losers
- **Added Negative Case Tests**: Comprehensive testing for all award scenarios where no qualifying teams exist
- **Updated Award Descriptions**: Added "Accidental Genius" award to prompt template
- **Enhanced Data Models**: Full Pydantic validation with optional fields and default lists

### Pipeline Status
- ✅ **Stage 1 (Extract)**: Complete - ESPN data extraction using existing functionality
- ✅ **Stage 2 (Upload)**: Complete - DynamoDB storage with schema versioning (requires AWS resources)
- ✅ **Stage 3 (Aggregate)**: Complete - Enhanced JSON with season analytics and context
- ❌ **Stage 4 (Deploy)**: Not implemented - raises NotImplementedError (S3 upload pending)
- ⚠️  **Configuration**: Pipeline config sections need to be added to config files
- ⚠️  **Testing**: End-to-end pipeline testing framework needed

### Development Mode Removed
- ❌ **No Automatic Fallbacks**: Stages fail properly when AWS resources unavailable
- ✅ **Dry-Run Mode**: Use `--dry-run` flag for testing without AWS
- ✅ **Individual Stages**: Run stages 1 and 3 independently for development