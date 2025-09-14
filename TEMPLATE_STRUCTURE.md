# Fantasy Football HTML Template Structure

This document describes the Jinja2 template architecture used by the `TemplatedFantasyHTMLGenerator` for generating fantasy football reports.

## Overview

The templated HTML generator uses Jinja2 templates to separate presentation logic from data preparation. This creates a cleaner, more maintainable architecture where HTML/CSS is managed in dedicated template files while Python handles data processing.

## Template Directory Structure

```
src/generators/templates/
├── main.html                    # Main page structure and layout
├── styles.css                   # All CSS styling and responsive design
├── scripts.js                   # Client-side JavaScript for logo handling
├── header.html                  # Page header with title and date
├── footer.html                  # Page footer with generation info
├── season_stats.html            # Overall league standings and divisions
├── weekly_stats.html            # Weekly statistics and awards sections
├── game_summaries.html          # Individual matchup breakdowns
├── overall_standings.html       # League standings table component
├── weekly_awards.html           # Awards grid display
├── weekly_totals.html           # Weekly summary statistics table
├── strength_of_schedule.html    # Strength of schedule section
├── lineup_accuracy.html         # Lineup efficiency analysis
├── scoring_leaders.html         # Top scoring teams for the week
├── week_specific_totals.html    # Week-specific running totals
└── team_player_table.html       # Reusable player performance table
```

## Template Hierarchy

### Main Template (`main.html`)
- **Purpose**: Root template that defines the overall page structure
- **Includes**: All CSS, JavaScript, and major page sections
- **Variables**: Basic page info (league_name, week, season, formatted_date)

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <title>{{ league_name }} - Week {{ week }} Report</title>
    <style>{% include 'styles.css' %}</style>
    <script>{% include 'scripts.js' %}</script>
</head>
<body>
    <div class="container">
        {% include 'header.html' %}
        {% include 'season_stats.html' %}
        {% include 'weekly_stats.html' %}
        {% include 'game_summaries.html' %}
        {% include 'footer.html' %}
    </div>
</body>
</html>
```

### Page Sections

#### Header (`header.html`)
- **Purpose**: Page title and report metadata
- **Variables**: `league_name`, `week`, `season`, `formatted_date`

#### Season Stats (`season_stats.html`)
- **Purpose**: Container for overall league statistics
- **Includes**: `overall_standings.html`, `weekly_totals.html`, `week_specific_totals.html`, `strength_of_schedule.html`, `lineup_accuracy.html`

#### Weekly Stats (`weekly_stats.html`)
- **Purpose**: Container for week-specific analysis
- **Includes**: `scoring_leaders.html`, `weekly_awards.html`

#### Game Summaries (`game_summaries.html`)
- **Purpose**: Detailed matchup breakdowns with player tables
- **Variables**: `matchups_sorted` (list of prepared matchup data)
- **Includes**: `team_player_table.html` (with context variables)

## Key Template Components

### Team Player Table (`team_player_table.html`)
**Purpose**: Reusable component for displaying team rosters with performance metrics

**Required Context Variables**:
- `team_players`: List of player objects with performance data
- `starter_total`: Total points scored by starters
- `team_bg_color`: Team theme background color
- `team_font_color`: Team theme font color  
- `optimal_score`: Best possible score for the team
- `accuracy_percentage`: Lineup efficiency percentage

**Features**:
- MVP/LVP highlighting for starters
- Injury status indicators (❤️‍🩹 for injured players)
- Should-have-started player identification
- Optimal lineup analysis

### Awards Grid (`weekly_awards.html`)
**Purpose**: Display weekly awards in card format with team theming

**Data Structure**:
- `player_awards`: Individual player achievements (MVP, MWP, MUP, MDP)
- `team_awards`: Team-based awards (HSL, LSW, SSL, IFM, Accidental Genius)
- `collapse_awards`: Failure awards (McCollapse, Clapper Collapse)

## Data Preparation

### Template Variables Structure

The `_prepare_template_variables()` method provides these variables to all templates:

```python
{
    # Basic Info
    'league_name': str,
    'week': int,
    'season': int,
    'report_date': str,
    'formatted_date': str,
    
    # Team Data
    'team_logos': Dict[str, str],           # Team name -> logo URL mapping
    'all_teams_sorted': List[Dict],         # All teams sorted by rank
    
    # Statistics
    'week_stats': {
        'median': float,
        'average': float,
        'max': float,
        'min': float,
        'std_dev': float,
        'max_content': Markup,              # HTML with logo
        'min_content': Markup               # HTML with logo
    },
    
    # Awards
    'player_awards': List[Dict],            # Individual player awards
    'team_awards': List[Dict],              # Team-based awards
    'collapse_awards': List[Dict],          # Failure/collapse awards
    
    # Game Summaries
    'matchups_sorted': List[Dict],          # Enhanced matchup data
    
    # Helper Functions
    'render_logo': function,                # Logo rendering helper
    'get_team_theme_colors': function       # Team color helper
}
```

### Enhanced Matchup Data

Each matchup in `matchups_sorted` contains:

```python
{
    'home_team': Dict,                      # Basic team info
    'away_team': Dict,                      # Basic team info
    'home_score': float,
    'away_score': float,
    'home_projected_score': float,
    'away_projected_score': float,
    'home_logo': Markup,                    # Rendered logo HTML
    'away_logo': Markup,                    # Rendered logo HTML
    'home_bg_color': str,                   # Team theme colors
    'home_font_color': str,
    'away_bg_color': str,
    'away_font_color': str,
    
    # Enhanced player data for team_player_table.html
    'home_players': List[Dict],             # Sorted with MVP/LVP flags
    'home_starter_total': float,
    'home_optimal_score': float,
    'home_accuracy_percentage': float,
    
    'away_players': List[Dict],             # Sorted with MVP/LVP flags  
    'away_starter_total': float,
    'away_optimal_score': float,
    'away_accuracy_percentage': float
}
```

## Logo System

### Centralized Logo Lookup
The `_create_team_logo_lookup()` method prioritizes division data over matchup data to ensure reliable logo URLs:

1. **First**: Populate from matchup data (fallback)
2. **Then**: Override with division data (more reliable ESPN URLs)

### HTML Safety
Logo rendering uses Jinja2's `Markup` class to prevent HTML escaping:

```python
def _render_logo_helper(self, logo_url: str, team_name: str) -> Markup:
    if not logo_url:
        return Markup("")
    return Markup(f'<img src="{logo_url}" class="team-logo" alt="{team_name}">')
```

### Client-Side Fallback
JavaScript in `scripts.js` handles failed logo loads by replacing with 💩 emoji:

```javascript
function replaceWithPoop(imgElement) {
    const teamName = imgElement.alt || 'Team';
    const poopSpan = document.createElement('span');
    poopSpan.className = 'team-logo emoji-logo';
    poopSpan.textContent = '💩';
    poopSpan.title = `Logo failed to load for ${teamName}`;
    imgElement.parentNode.replaceChild(poopSpan, imgElement);
}
```

## Template Usage Patterns

### Including Sub-Templates
```html
{% include 'template_name.html' %}
```

### With Context Variables
```html
{% with team_players=matchup.away_players, starter_total=matchup.away_starter_total %}
    {% include 'team_player_table.html' %}
{% endwith %}
```

### Conditional Rendering
```html
{% if team_data.efficiency %}
    <td class="numeric">{{ "%.1f"|format(team_data.efficiency) }}%</td>
{% endif %}
```

### Loops with Team Theming
```html
{% for award in player_awards %}
    <div class="award-card" style="background-color: {{ award.team_bg_color }};">
        <div class="award-header" style="color: {{ award.team_font_color }};">
            <!-- Award content -->
        </div>
    </div>
{% endfor %}
```

## Styling Architecture

### CSS Organization (`styles.css`)
- **Reset/Base**: Universal styling and containers
- **Typography**: Headers, text, and font hierarchies  
- **Tables**: Standings tables and data displays
- **Components**: Logos, teams, awards, matchups
- **Layout**: Grid systems and responsive design
- **Theme Colors**: Team-specific color schemes

### Responsive Design
- Flexible grid layouts for awards and matchups
- Mobile-friendly table styling
- Scalable logo and emoji systems

## Maintenance Guidelines

### Adding New Sections
1. Create new template file in `templates/` directory
2. Add data preparation logic in `_prepare_template_variables()`
3. Include template in appropriate parent template
4. Update this documentation

### Modifying Existing Templates  
1. Edit template files directly for layout/styling changes
2. Update data preparation methods for new data requirements
3. Test with existing JSON reports to ensure compatibility

### Team Theme Colors
Team colors are defined in `_get_team_theme_color()` and automatically generate appropriate font colors for accessibility (7:1 contrast ratio).

## Benefits of This Architecture

1. **Separation of Concerns**: HTML/CSS separate from Python logic
2. **Maintainability**: Easy to modify presentation without code changes
3. **Reusability**: Component templates can be shared across sections
4. **Consistency**: Centralized styling and data preparation
5. **Debugging**: Clear separation makes issues easier to isolate
6. **Performance**: Jinja2 template caching for faster rendering

This template system generates identical output to the original embedded HTML approach while providing a much cleaner and more maintainable codebase.