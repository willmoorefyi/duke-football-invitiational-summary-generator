"""
Tests for annual recap generator
"""

import pytest
import json
from pathlib import Path
from src.generators.annual_recap_generator import AnnualRecapGenerator


@pytest.fixture
def sample_weekly_reports():
    """
    Fixture providing sample weekly report data.
    Note: Team wins/losses/points in divisions are set to None to simulate
    raw data from DynamoDB that doesn't have pre-calculated standings.
    """
    return [
        {
            "week": 1,
            "season": 2025,
            "league_id": 123456,
            "league_name": "Test League",
            "league_logo_url": "https://example.com/logo.png",
            "divisions": [
                {
                    "name": "Division A",
                    "teams": [
                        {"id": 1, "name": "Team Alpha", "owner": "Owner 1", "logo": "logo1.png"},
                        {"id": 2, "name": "Team Bravo", "owner": "Owner 2", "logo": "logo2.png"}
                    ]
                }
            ],
            "matchups": [
                {
                    "week": 1,
                    "home_team": {"id": 1, "name": "Team Alpha", "logo": "logo1.png"},
                    "away_team": {"id": 2, "name": "Team Bravo", "logo": "logo2.png"},
                    "home_score": 125.5,
                    "away_score": 118.3,
                    "winner_id": 1
                }
            ],
            "awards": {
                "mvp": {
                    "player_name": "Patrick Mahomes",
                    "team_name": "Team Alpha",
                    "position": "QB",
                    "score": 35.2
                },
                "hsl": {
                    "team_name": "Team Bravo",
                    "score": 118.3,
                    "additional_info": "Lost by 7.2"
                }
            }
        },
        {
            "week": 2,
            "season": 2025,
            "league_id": 123456,
            "league_name": "Test League",
            "league_logo_url": "https://example.com/logo.png",
            "divisions": [
                {
                    "name": "Division A",
                    "teams": [
                        {"id": 1, "name": "Team Alpha", "owner": "Owner 1", "logo": "logo1.png"},
                        {"id": 2, "name": "Team Bravo", "owner": "Owner 2", "logo": "logo2.png"}
                    ]
                }
            ],
            "matchups": [
                {
                    "week": 2,
                    "home_team": {"id": 2, "name": "Team Bravo", "logo": "logo2.png"},
                    "away_team": {"id": 1, "name": "Team Alpha", "logo": "logo1.png"},
                    "home_score": 117.4,
                    "away_score": 113.2,
                    "winner_id": 2
                }
            ],
            "awards": {
                "mvp": {
                    "player_name": "Josh Allen",
                    "team_name": "Team Bravo",
                    "position": "QB",
                    "score": 38.5
                },
                "mwp": {
                    "player_name": "Tyreek Hill",
                    "team_name": "Team Alpha",
                    "position": "WR",
                    "score": 32.1
                }
            }
        }
    ]


class TestAnnualRecapGenerator:
    """Tests for AnnualRecapGenerator class."""

    def test_aggregate_team_data_cumulative_calculation(self, sample_weekly_reports):
        """Test cumulative team standings calculation from matchup results."""
        generator = AnnualRecapGenerator()
        result = generator._aggregate_team_data(sample_weekly_reports)

        # Verify structure
        assert 'teams' in result
        assert 'weeklyStandings' in result  # camelCase for JavaScript
        assert 'weeklyRecords' in result

        # Verify teams
        assert len(result['teams']) == 2
        assert result['teams'][0]['id'] == 1
        assert result['teams'][0]['name'] == 'Team Alpha'
        assert result['teams'][1]['id'] == 2

        # Verify weekly standings calculated from matchups
        assert len(result['weeklyStandings']) == 2

        # Week 1: Team Alpha wins (1-0 with 125.5 pts), Team Bravo loses (0-1 with 118.3 pts)
        assert result['weeklyStandings'][0] == [1, 2]  # Alpha first after week 1

        # Week 2: Team Bravo wins (now 1-1), Team Alpha loses (now 1-1)
        # Tie-breaker: points_for - Alpha has 238.7 total, Bravo has 235.7 total
        assert result['weeklyStandings'][1] == [1, 2]  # Alpha still first (more points)

        # Verify weekly records show cumulative stats
        assert len(result['weeklyRecords']) == 2

        # Week 1 records
        assert result['weeklyRecords'][0][0]['wins'] == 1  # Team Alpha: 1 win
        assert result['weeklyRecords'][0][0]['losses'] == 0
        assert result['weeklyRecords'][0][0]['points'] == 125.5
        assert result['weeklyRecords'][0][1]['wins'] == 0  # Team Bravo: 0 wins
        assert result['weeklyRecords'][0][1]['losses'] == 1
        assert result['weeklyRecords'][0][1]['points'] == 118.3

        # Week 2 records (cumulative)
        assert result['weeklyRecords'][1][0]['wins'] == 1  # Team Alpha: still 1 win
        assert result['weeklyRecords'][1][0]['losses'] == 1  # now 1 loss
        assert result['weeklyRecords'][1][0]['points'] == 125.5 + 113.2  # cumulative points
        assert result['weeklyRecords'][1][1]['wins'] == 1  # Team Bravo: now 1 win
        assert result['weeklyRecords'][1][1]['losses'] == 1  # still 1 loss
        assert result['weeklyRecords'][1][1]['points'] == 118.3 + 117.4  # cumulative points

    def test_aggregate_awards_data(self, sample_weekly_reports):
        """Test awards aggregation across weeks."""
        generator = AnnualRecapGenerator()
        result = generator._aggregate_awards_data(sample_weekly_reports)

        # Verify structure
        assert 'awards' in result
        assert len(result['awards']) > 0

        # Find MVP award
        mvp_award = next((a for a in result['awards'] if a['id'] == 'mvp'), None)
        assert mvp_award is not None
        assert mvp_award['title'] == 'Most Valuable Player'
        assert mvp_award['icon'] == '🏆'

        # Verify winners list (should include both Team Alpha and Team Bravo with 1 win each due to tie)
        assert 'winners' in mvp_award
        assert len(mvp_award['winners']) >= 1
        # Each winner should have teamName, logo, count, and details
        for winner in mvp_award['winners']:
            assert 'teamName' in winner
            assert 'logo' in winner
            assert 'count' in winner
            assert winner['count'] >= 1
            assert 'details' in winner
            assert len(winner['details']) >= 1

    def test_aggregate_weekly_highlights(self, sample_weekly_reports):
        """Test weekly highlights aggregation."""
        generator = AnnualRecapGenerator()
        result = generator._aggregate_weekly_highlights(sample_weekly_reports)

        # Verify structure
        assert 'weeks' in result
        assert len(result['weeks']) == 2

        # Verify week 1 data
        week1 = result['weeks'][0]
        assert week1['week'] == 1
        assert 'highestScorer' in week1
        assert 'lowestScorer' in week1
        assert 'winners' in week1

        # Team Alpha scored highest in week 1 (125.5)
        assert week1['highestScorer']['teamName'] == 'Team Alpha'
        assert week1['highestScorer']['score'] == 125.5

        # Team Bravo scored lowest in week 1 (118.3)
        assert week1['lowestScorer']['teamName'] == 'Team Bravo'
        assert week1['lowestScorer']['score'] == 118.3

        # One winner in week 1
        assert len(week1['winners']) == 1
        assert week1['winners'][0]['teamId'] == 1

    def test_build_award_stat_description_player_award(self):
        """Test stat description building for player awards."""
        generator = AnnualRecapGenerator()

        award_data = {
            'player_name': 'Patrick Mahomes',
            'score': 35.2
        }

        result = generator._build_award_stat_description('mvp', award_data)
        assert result == 'Patrick Mahomes - 35.2 pts'

    def test_build_award_stat_description_team_award(self):
        """Test stat description building for team awards."""
        generator = AnnualRecapGenerator()

        award_data = {
            'score': 118.3,
            'additional_info': 'Lost by 7.2'
        }

        result = generator._build_award_stat_description('hsl', award_data)
        assert result == '118.3 pts - Lost by 7.2'

    def test_get_team_logo(self, sample_weekly_reports):
        """Test team logo retrieval from weekly reports."""
        generator = AnnualRecapGenerator()

        logo = generator._get_team_logo(sample_weekly_reports, 'Team Alpha')
        assert logo == 'logo1.png'

        logo = generator._get_team_logo(sample_weekly_reports, 'Team Bravo')
        assert logo == 'logo2.png'

        # Non-existent team
        logo = generator._get_team_logo(sample_weekly_reports, 'Non-Existent Team')
        assert logo == ''

    def test_generate_html_structure(self, sample_weekly_reports, tmp_path):
        """Test HTML generation creates valid output."""
        generator = AnnualRecapGenerator()

        output_file = tmp_path / "test_annual_recap.html"
        result = generator.generate(sample_weekly_reports, str(output_file))

        # Verify file was created
        assert Path(result).exists()

        # Read and verify HTML structure
        with open(result, 'r') as f:
            html_content = f.read()

        # Verify key HTML elements exist
        assert '<!DOCTYPE html>' in html_content
        assert '2025 Season Wrapped' in html_content  # Season wrapped text
        assert 'const teamData' in html_content
        assert 'const awardsData' in html_content
        assert 'const weeklyRecapData' in html_content

        # Verify real data is embedded
        assert 'Team Alpha' in html_content
        assert 'Team Bravo' in html_content
        assert 'Test League' in html_content  # League name from fixture

    def test_empty_reports_handling(self):
        """Test handling of empty weekly reports."""
        generator = AnnualRecapGenerator()

        result = generator._aggregate_team_data([])
        assert result['teams'] == []
        assert result['weeklyStandings'] == []
        assert result['weeklyRecords'] == []

    def test_cumulative_standings_with_tie_game(self):
        """Test cumulative standings calculation when a game ends in a tie."""
        generator = AnnualRecapGenerator()

        reports = [
            {
                "week": 1,
                "divisions": [{"name": "Div", "teams": [
                    {"id": 1, "name": "Team A", "logo": "logo1.png"},
                    {"id": 2, "name": "Team B", "logo": "logo2.png"}
                ]}],
                "matchups": [
                    {
                        "home_team": {"id": 1, "name": "Team A"},
                        "away_team": {"id": 2, "name": "Team B"},
                        "home_score": 100.0,
                        "away_score": 100.0,
                        "winner_id": None  # Tie game
                    }
                ],
                "awards": {}
            }
        ]

        result = generator._aggregate_team_data(reports)

        # Both teams should have 0-0 record after tie
        assert result['weeklyRecords'][0][0]['wins'] == 0
        assert result['weeklyRecords'][0][0]['losses'] == 0
        assert result['weeklyRecords'][0][0]['points'] == 100.0
        assert result['weeklyRecords'][0][1]['wins'] == 0
        assert result['weeklyRecords'][0][1]['losses'] == 0
        assert result['weeklyRecords'][0][1]['points'] == 100.0

    def test_cumulative_standings_ranking_tiebreakers(self):
        """Test that standings ranking uses proper tiebreakers (wins, losses, points_for, points_against)."""
        generator = AnnualRecapGenerator()

        reports = [
            {
                "week": 1,
                "divisions": [{"name": "Div", "teams": [
                    {"id": 1, "name": "Team A", "logo": "logo1.png"},
                    {"id": 2, "name": "Team B", "logo": "logo2.png"},
                    {"id": 3, "name": "Team C", "logo": "logo3.png"},
                    {"id": 4, "name": "Team D", "logo": "logo4.png"}
                ]}],
                "matchups": [
                    {
                        "home_team": {"id": 1, "name": "Team A"},
                        "away_team": {"id": 2, "name": "Team B"},
                        "home_score": 120.0,
                        "away_score": 100.0,
                        "winner_id": 1
                    },
                    {
                        "home_team": {"id": 3, "name": "Team C"},
                        "away_team": {"id": 4, "name": "Team D"},
                        "home_score": 110.0,
                        "away_score": 90.0,
                        "winner_id": 3
                    }
                ],
                "awards": {}
            }
        ]

        result = generator._aggregate_team_data(reports)

        # Both Team A and Team C have 1-0 record
        # Team A should rank first (120 pts > 110 pts)
        assert result['weeklyStandings'][0][0] == 1  # Team A first
        assert result['weeklyStandings'][0][1] == 3  # Team C second
        # Losers: Team B (100 pts) > Team D (90 pts)
        assert result['weeklyStandings'][0][2] == 2  # Team B third
        assert result['weeklyStandings'][0][3] == 4  # Team D fourth

    def test_cumulative_standings_multiple_weeks(self):
        """Test that standings update correctly over multiple weeks."""
        generator = AnnualRecapGenerator()

        reports = [
            {
                "week": 1,
                "divisions": [{"name": "Div", "teams": [
                    {"id": 1, "name": "Team A", "logo": "logo1.png"},
                    {"id": 2, "name": "Team B", "logo": "logo2.png"}
                ]}],
                "matchups": [
                    {
                        "home_team": {"id": 1},
                        "away_team": {"id": 2},
                        "home_score": 100.0,
                        "away_score": 90.0,
                        "winner_id": 1
                    }
                ],
                "awards": {}
            },
            {
                "week": 2,
                "divisions": [{"name": "Div", "teams": [
                    {"id": 1, "name": "Team A", "logo": "logo1.png"},
                    {"id": 2, "name": "Team B", "logo": "logo2.png"}
                ]}],
                "matchups": [
                    {
                        "home_team": {"id": 2},
                        "away_team": {"id": 1},
                        "home_score": 110.0,
                        "away_score": 95.0,
                        "winner_id": 2
                    }
                ],
                "awards": {}
            },
            {
                "week": 3,
                "divisions": [{"name": "Div", "teams": [
                    {"id": 1, "name": "Team A", "logo": "logo1.png"},
                    {"id": 2, "name": "Team B", "logo": "logo2.png"}
                ]}],
                "matchups": [
                    {
                        "home_team": {"id": 1},
                        "away_team": {"id": 2},
                        "home_score": 105.0,
                        "away_score": 95.0,
                        "winner_id": 1
                    }
                ],
                "awards": {}
            }
        ]

        result = generator._aggregate_team_data(reports)

        # Week 1: Team A (1-0), Team B (0-1)
        assert result['weeklyRecords'][0][0]['wins'] == 1
        assert result['weeklyRecords'][0][1]['wins'] == 0
        assert result['weeklyStandings'][0] == [1, 2]

        # Week 2: Team A (1-1), Team B (1-1) - tie, B has more points
        assert result['weeklyRecords'][1][0]['wins'] == 1
        assert result['weeklyRecords'][1][0]['losses'] == 1
        assert result['weeklyRecords'][1][1]['wins'] == 1
        assert result['weeklyRecords'][1][1]['losses'] == 1
        # Team B: 200 total points, Team A: 195 total points
        assert result['weeklyStandings'][1] == [2, 1]  # B now leads

        # Week 3: Team A (2-1, 300 pts), Team B (1-2, 295 pts)
        assert result['weeklyRecords'][2][0]['wins'] == 2
        assert result['weeklyRecords'][2][0]['losses'] == 1
        assert result['weeklyRecords'][2][1]['wins'] == 1
        assert result['weeklyRecords'][2][1]['losses'] == 2
        assert result['weeklyStandings'][2] == [1, 2]  # A back on top

    def test_league_metadata_extraction(self):
        """Test extraction of league metadata from weekly reports."""
        generator = AnnualRecapGenerator()

        reports = [
            {
                "week": 1,
                "season": 2025,
                "league_name": "My Fantasy League",
                "league_logo_url": "https://example.com/my-logo.png",
                "divisions": [],
                "matchups": [],
                "awards": {}
            }
        ]

        metadata = generator._extract_league_metadata(reports)

        assert metadata['league_name'] == "My Fantasy League"
        assert metadata['season'] == 2025
        assert metadata['league_logo_url'] == "https://example.com/my-logo.png"

    def test_league_metadata_with_missing_data(self):
        """Test league metadata extraction with missing fields uses defaults."""
        generator = AnnualRecapGenerator()

        reports = [{"week": 1, "divisions": [], "matchups": [], "awards": {}}]

        metadata = generator._extract_league_metadata(reports)

        assert metadata['league_name'] == 'Fantasy League'
        assert metadata['season'] == 2024  # Default
        assert 'duke-football-invitational' in metadata['league_logo_url']  # Default logo

    def test_league_metadata_empty_reports(self):
        """Test league metadata extraction with no reports returns defaults."""
        generator = AnnualRecapGenerator()

        metadata = generator._extract_league_metadata([])

        assert metadata['league_name'] == 'Fantasy League'
        assert metadata['season'] == 2024
        assert 'duke-football-invitational' in metadata['league_logo_url']

    def test_decimal_conversion(self):
        """Test Decimal objects are converted to int/float for JSON serialization."""
        from decimal import Decimal
        generator = AnnualRecapGenerator()

        # Test various Decimal scenarios
        test_data = {
            'whole_number': Decimal('10'),
            'decimal_number': Decimal('10.5'),
            'nested_dict': {
                'value': Decimal('20.25')
            },
            'nested_list': [Decimal('1'), Decimal('2.5'), Decimal('3')]
        }

        result = generator._convert_decimals(test_data)

        assert result['whole_number'] == 10  # Should be int
        assert isinstance(result['whole_number'], int)
        assert result['decimal_number'] == 10.5  # Should be float
        assert isinstance(result['decimal_number'], float)
        assert result['nested_dict']['value'] == 20.25
        assert isinstance(result['nested_dict']['value'], float)
        assert result['nested_list'] == [1, 2.5, 3]
        assert isinstance(result['nested_list'][0], int)
        assert isinstance(result['nested_list'][1], float)

    def test_aggregate_team_data_with_missing_matchup_data(self):
        """Test that aggregate handles weeks with missing or incomplete matchup data."""
        generator = AnnualRecapGenerator()

        reports = [
            {
                "week": 1,
                "divisions": [{"name": "Div", "teams": [
                    {"id": 1, "name": "Team A", "logo": "logo1.png"},
                    {"id": 2, "name": "Team B", "logo": "logo2.png"}
                ]}],
                "matchups": [
                    {
                        "home_team": {"id": 1},
                        "away_team": {"id": 2},
                        "home_score": 100.0,
                        "away_score": 90.0,
                        "winner_id": 1
                    }
                ],
                "awards": {}
            },
            {
                "week": 2,
                "divisions": [{"name": "Div", "teams": [
                    {"id": 1, "name": "Team A", "logo": "logo1.png"},
                    {"id": 2, "name": "Team B", "logo": "logo2.png"}
                ]}],
                "matchups": [],  # No matchups for week 2
                "awards": {}
            }
        ]

        result = generator._aggregate_team_data(reports)

        # Week 1 should have data
        assert result['weeklyRecords'][0][0]['wins'] == 1

        # Week 2 should maintain week 1 records (no new matchups)
        assert result['weeklyRecords'][1][0]['wins'] == 1
        assert result['weeklyRecords'][1][0]['losses'] == 0
        assert result['weeklyRecords'][1][0]['points'] == 100.0

    def test_html_generation_embeds_correct_data(self, sample_weekly_reports, tmp_path):
        """Test that HTML generation properly embeds data with correct property names."""
        generator = AnnualRecapGenerator()

        output_file = tmp_path / "test_recap.html"
        result = generator.generate(sample_weekly_reports, str(output_file))

        with open(result, 'r') as f:
            html_content = f.read()

        # Verify camelCase property names are used (not snake_case)
        assert 'weeklyStandings' in html_content
        assert 'weeklyRecords' in html_content
        assert 'weekly_standings' not in html_content  # Old snake_case should not exist
        assert 'weekly_records' not in html_content

        # Verify league metadata is embedded
        assert '2025' in html_content  # Season year
        assert 'Test League' in html_content  # League name
        assert 'https://example.com/logo.png' in html_content  # Logo URL

    def test_html_generation_includes_restart_button(self, sample_weekly_reports, tmp_path):
        """Test that HTML includes restart button with proper styling and functionality."""
        generator = AnnualRecapGenerator()

        output_file = tmp_path / "test_recap.html"
        result = generator.generate(sample_weekly_reports, str(output_file))

        with open(result, 'r') as f:
            html_content = f.read()

        # Verify restart button exists
        assert 'id="restartBtn"' in html_content
        assert '↻ Restart Journey' in html_content

        # Verify restart button CSS
        assert '.restart-btn' in html_content
        assert 'restart-btn.visible' in html_content

        # Verify restart functionality exists
        assert 'function restartRace()' in html_content
        assert "restartBtn.classList.add('visible')" in html_content
        assert "restartBtn.classList.remove('visible')" in html_content
        assert "addEventListener('click', restartRace)" in html_content

    def test_html_generation_includes_d3_bar_chart(self, sample_weekly_reports, tmp_path):
        """Test that HTML includes D3.js library and bar chart implementation."""
        generator = AnnualRecapGenerator()

        output_file = tmp_path / "test_recap.html"
        result = generator.generate(sample_weekly_reports, str(output_file))

        with open(result, 'r') as f:
            html_content = f.read()

        # Verify D3.js library is included
        assert 'd3js.org/d3' in html_content
        assert 'script src=' in html_content

        # Verify SVG element for chart
        assert 'svg id="raceChart"' in html_content

        # Verify D3 bar chart CSS classes
        assert '.bar-rect' in html_content
        assert '.bar-label' in html_content
        assert '.bar-value' in html_content
        assert '.bar-record' in html_content
        assert '.bar-rank' in html_content

        # Verify D3 bar chart JavaScript
        assert 'd3.select' in html_content
        assert 'xScale' in html_content
        assert 'yScale' in html_content
        assert 'barHeight' in html_content
        assert '.attr(\'class\', \'bar-group\')' in html_content

        # Verify animations use D3 transitions
        assert '.transition()' in html_content
        assert '.duration(' in html_content

    def test_awards_with_multiple_winners_same_team(self):
        """Test award aggregation when same team wins multiple times."""
        generator = AnnualRecapGenerator()

        reports = [
            {
                "week": 1,
                "divisions": [{"name": "Div", "teams": [
                    {"id": 1, "name": "Team Alpha", "logo": "logo.png",
                     "wins": 1, "losses": 0, "points_for": 100, "points_against": 90}
                ]}],
                "matchups": [],
                "awards": {
                    "mvp": {"player_name": "Player A", "team_name": "Team Alpha", "score": 30.0}
                }
            },
            {
                "week": 2,
                "divisions": [{"name": "Div", "teams": [
                    {"id": 1, "name": "Team Alpha", "logo": "logo.png",
                     "wins": 2, "losses": 0, "points_for": 200, "points_against": 180}
                ]}],
                "matchups": [],
                "awards": {
                    "mvp": {"player_name": "Player B", "team_name": "Team Alpha", "score": 35.0}
                }
            },
            {
                "week": 3,
                "divisions": [{"name": "Div", "teams": [
                    {"id": 1, "name": "Team Alpha", "logo": "logo.png",
                     "wins": 3, "losses": 0, "points_for": 300, "points_against": 270}
                ]}],
                "matchups": [],
                "awards": {
                    "mvp": {"player_name": "Player C", "team_name": "Team Alpha", "score": 32.0}
                }
            }
        ]

        result = generator._aggregate_awards_data(reports)
        mvp_award = next((a for a in result['awards'] if a['id'] == 'mvp'), None)

        assert mvp_award is not None
        # Team Alpha won all 3 times, so should be the only winner
        assert len(mvp_award['winners']) == 1
        winner = mvp_award['winners'][0]
        assert winner['teamName'] == 'Team Alpha'
        assert winner['count'] == 3
        assert len(winner['details']) == 3

    def test_new_award_types_included(self):
        """Test that all new award types are included in aggregation."""
        generator = AnnualRecapGenerator()

        reports = [
            {
                "week": 1,
                "divisions": [{"name": "Div", "teams": [
                    {"id": 1, "name": "Team Alpha", "logo": "logo.png",
                     "wins": 1, "losses": 0, "points_for": 100, "points_against": 90}
                ]}],
                "matchups": [],
                "awards": {
                    "ssl": {"team_name": "Team Alpha", "actual_score": 120.0, "optimal_score": 125.0, "efficiency_percentage": 96.0},
                    "ifm": {"team_name": "Team Bravo", "actual_score": 90.0, "optimal_score": 120.0, "efficiency_percentage": 75.0},
                    "accidental_genius": {"team_name": "Team Charlie", "actual_score": 100.0, "optimal_score": 140.0, "efficiency_percentage": 71.4},
                    "mccollapse": {"team_name": "Team Delta", "actual_score": 110.0, "optimal_score": 130.0, "opponent_score": 115.0, "points_difference": 20.0},
                    "clapper_collapse": {"team_name": "Team Echo", "projected_score": 125.0, "actual_score": 95.0, "opponent_projected_score": 100.0, "opponent_actual_score": 110.0}
                }
            }
        ]

        result = generator._aggregate_awards_data(reports)

        # Verify all new award types are present
        award_ids = [award['id'] for award in result['awards']]
        assert 'ssl' in award_ids
        assert 'ifm' in award_ids
        assert 'accidental_genius' in award_ids
        assert 'mccollapse' in award_ids
        assert 'clapper_collapse' in award_ids

        # Verify SSL award has correct structure
        ssl_award = next((a for a in result['awards'] if a['id'] == 'ssl'), None)
        assert ssl_award is not None
        assert ssl_award['title'] == 'Smartest Starting Lineup'
        assert ssl_award['icon'] == '🧠'

        # Verify McCollapse award
        mccollapse_award = next((a for a in result['awards'] if a['id'] == 'mccollapse'), None)
        assert mccollapse_award is not None
        assert mccollapse_award['title'] == 'Mike McCoy "McCollapse" Award'

        # Verify Clapper award
        clapper_award = next((a for a in result['awards'] if a['id'] == 'clapper_collapse'), None)
        assert clapper_award is not None
        assert clapper_award['title'] == 'Jason Garrett "The Clapper" Award'

    def test_awards_with_tied_winners(self):
        """Test that tied winners are both included in the winners list."""
        generator = AnnualRecapGenerator()

        reports = [
            {
                "week": 1,
                "divisions": [{"name": "Div", "teams": [
                    {"id": 1, "name": "Team Alpha", "logo": "logo_alpha.png", "wins": 1, "losses": 0, "points_for": 100, "points_against": 90},
                    {"id": 2, "name": "Team Bravo", "logo": "logo_bravo.png", "wins": 1, "losses": 0, "points_for": 110, "points_against": 95}
                ]}],
                "matchups": [],
                "awards": {
                    "mvp": {"player_name": "Player A", "team_name": "Team Alpha", "score": 30.0}
                }
            },
            {
                "week": 2,
                "divisions": [{"name": "Div", "teams": [
                    {"id": 1, "name": "Team Alpha", "logo": "logo_alpha.png", "wins": 2, "losses": 0, "points_for": 200, "points_against": 180},
                    {"id": 2, "name": "Team Bravo", "logo": "logo_bravo.png", "wins": 2, "losses": 0, "points_for": 220, "points_against": 195}
                ]}],
                "matchups": [],
                "awards": {
                    "mvp": {"player_name": "Player B", "team_name": "Team Bravo", "score": 35.0}
                }
            }
        ]

        result = generator._aggregate_awards_data(reports)
        mvp_award = next((a for a in result['awards'] if a['id'] == 'mvp'), None)

        assert mvp_award is not None
        # Both teams won once, so should be tied with 2 winners
        assert len(mvp_award['winners']) == 2

        # Verify both teams are in winners list
        winner_names = {winner['teamName'] for winner in mvp_award['winners']}
        assert 'Team Alpha' in winner_names
        assert 'Team Bravo' in winner_names

        # Both should have count of 1
        for winner in mvp_award['winners']:
            assert winner['count'] == 1
            assert len(winner['details']) == 1

    def test_mdp_award_title_fix(self):
        """Test that MDP award has correct title 'Most Disrespected Player'."""
        generator = AnnualRecapGenerator()

        reports = [
            {
                "week": 1,
                "divisions": [{"name": "Div", "teams": [
                    {"id": 1, "name": "Team Alpha", "logo": "logo.png", "wins": 1, "losses": 0, "points_for": 100, "points_against": 90}
                ]}],
                "matchups": [],
                "awards": {
                    "mdp": {"player_name": "Bench Star", "team_name": "Team Alpha", "score": 28.0}
                }
            }
        ]

        result = generator._aggregate_awards_data(reports)
        mdp_award = next((a for a in result['awards'] if a['id'] == 'mdp'), None)

        assert mdp_award is not None
        assert mdp_award['title'] == 'Most Disrespected Player'
        assert mdp_award['icon'] == '🪑'
