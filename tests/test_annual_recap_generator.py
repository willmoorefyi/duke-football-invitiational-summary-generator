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

    def test_annual_recap_with_decimal_values_from_dynamodb(self, tmp_path):
        """
        Integration test: Ensure annual recap generation works with Decimal values.

        DynamoDB returns Decimal objects for numeric fields, which can cause
        TypeError when mixed with floats in calculations like Pythagorean wins.
        This test ensures the generator handles Decimal values correctly.
        """
        from decimal import Decimal

        generator = AnnualRecapGenerator()

        # Create sample data with Decimal values (simulating DynamoDB response)
        weekly_reports = []
        for week in range(1, 15):  # 14 weeks of data
            report = {
                "week": week,
                "season": 2025,
                "league_id": 123456,
                "league_name": "Test League",
                "league_logo_url": "https://example.com/logo.png",
                "divisions": [
                    {
                        "name": "Division A",
                        "teams": [
                            {
                                "id": 1, "name": "Team Alpha", "owner": "Owner 1", "logo": "logo1.png",
                                # Decimal values like DynamoDB returns
                                "wins": Decimal(str(min(week, 10))),
                                "losses": Decimal(str(max(0, week - 10))),
                                "points_for": Decimal("1500.50"),
                                "points_against": Decimal("1400.25"),
                                "standing": Decimal("1")
                            },
                            {
                                "id": 2, "name": "Team Bravo", "owner": "Owner 2", "logo": "logo2.png",
                                "wins": Decimal(str(max(0, week - 5))),
                                "losses": Decimal(str(min(week, 5))),
                                "points_for": Decimal("1400.25"),
                                "points_against": Decimal("1500.50"),
                                "standing": Decimal("2")
                            },
                            {
                                "id": 3, "name": "Team Charlie", "owner": "Owner 3", "logo": "logo3.png",
                                "wins": Decimal(str(week // 2)),
                                "losses": Decimal(str(week - week // 2)),
                                "points_for": Decimal("1300.00"),
                                "points_against": Decimal("1350.00"),
                                "standing": Decimal("7")  # Bottom half
                            },
                            {
                                "id": 4, "name": "Team Delta", "owner": "Owner 4", "logo": "logo4.png",
                                "wins": Decimal(str(max(0, week - 8))),
                                "losses": Decimal(str(min(week, 8))),
                                "points_for": Decimal("1200.00"),
                                "points_against": Decimal("1450.00"),
                                "standing": Decimal("8")  # Bottom half
                            }
                        ]
                    }
                ],
                "matchups": [
                    {
                        "week": week,
                        "home_team": {"id": 1, "name": "Team Alpha", "logo": "logo1.png"},
                        "away_team": {"id": 2, "name": "Team Bravo", "logo": "logo2.png"},
                        "home_score": Decimal("125.50"),
                        "away_score": Decimal("118.30"),
                        "winner_id": 1,
                        "players": [
                            {"name": "Player 1", "team": "Team Alpha", "position": "QB",
                             "is_starter": True, "roster_slot": "QB", "actual_score": Decimal("25.5")},
                            {"name": "Player 2", "team": "Team Bravo", "position": "RB",
                             "is_starter": True, "roster_slot": "RB", "actual_score": Decimal("18.3")},
                            {"name": "Bench Player", "team": "Team Alpha", "position": "WR",
                             "is_starter": False, "roster_slot": "BE", "actual_score": Decimal("22.0")}
                        ]
                    },
                    {
                        "week": week,
                        "home_team": {"id": 3, "name": "Team Charlie", "logo": "logo3.png"},
                        "away_team": {"id": 4, "name": "Team Delta", "logo": "logo4.png"},
                        "home_score": Decimal("110.00"),
                        "away_score": Decimal("105.00"),
                        "winner_id": 3
                    }
                ],
                "awards": {
                    "mvp": {"player_name": "Player 1", "team_name": "Team Alpha", "score": Decimal("25.5")}
                }
            }
            weekly_reports.append(report)

        # Generate the annual recap - this should not raise TypeError
        output_file = tmp_path / "test-annual-recap.html"
        result_path = generator.generate(weekly_reports, str(output_file))

        # Verify the output was created
        assert Path(result_path).exists()

        # Verify the HTML contains expected content
        with open(result_path) as f:
            html_content = f.read()

        # Check that key sections are present
        assert "seasonRecapData" in html_content
        assert "teamStatsData" in html_content
        assert "Team Alpha" in html_content
        assert "luckiestTeam" in html_content
        assert "unluckiestTeam" in html_content
        assert "narrowestPlayoffWinner" in html_content
        assert "closestPlayoffLoser" in html_content

        # Verify no Decimal objects leaked into JSON (would cause issues)
        assert "Decimal" not in html_content


class TestAnnualRecapIntegration:
    """
    Comprehensive end-to-end integration tests for the annual recap generator.

    These tests validate the entire pipeline without generating actual HTML files
    or talking to AWS. They use realistic mock data that simulates DynamoDB responses.
    """

    @pytest.fixture
    def realistic_season_data(self):
        """
        Create realistic 14-week season data with 12 teams across 2 divisions.

        This fixture simulates data as it would come from DynamoDB, including:
        - Decimal values for numeric fields
        - All award types
        - Player data with starters and bench players
        - Varying scores and margins
        """
        from decimal import Decimal
        import random

        # Seed for reproducibility
        random.seed(42)

        # Define 12 teams across 2 divisions
        teams = [
            {"id": 1, "name": "Moore's Law", "owner": "Will", "logo": "logo1.png", "division": "East"},
            {"id": 2, "name": "Touchdown Titans", "owner": "Mike", "logo": "logo2.png", "division": "East"},
            {"id": 3, "name": "Gridiron Gang", "owner": "Sarah", "logo": "logo3.png", "division": "East"},
            {"id": 4, "name": "Fantasy Phenoms", "owner": "Tom", "logo": "logo4.png", "division": "East"},
            {"id": 5, "name": "Pigskin Pros", "owner": "Lisa", "logo": "logo5.png", "division": "East"},
            {"id": 6, "name": "End Zone Elite", "owner": "Dave", "logo": "logo6.png", "division": "East"},
            {"id": 7, "name": "Blitz Brigade", "owner": "Amy", "logo": "logo7.png", "division": "West"},
            {"id": 8, "name": "Hail Mary Heroes", "owner": "John", "logo": "logo8.png", "division": "West"},
            {"id": 9, "name": "Fumble Force", "owner": "Kate", "logo": "logo9.png", "division": "West"},
            {"id": 10, "name": "Draft Dodgers", "owner": "Chris", "logo": "logo10.png", "division": "West"},
            {"id": 11, "name": "Sack Attack", "owner": "Emma", "logo": "logo11.png", "division": "West"},
            {"id": 12, "name": "Red Zone Raiders", "owner": "Bob", "logo": "logo12.png", "division": "West"},
        ]

        # Track cumulative stats for standings
        team_stats = {t["id"]: {"wins": 0, "losses": 0, "pf": 0.0, "pa": 0.0} for t in teams}

        # Define matchup pairings for each week (6 matchups per week)
        weekly_pairings = [
            [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12)],  # Week 1
            [(1, 3), (2, 4), (5, 7), (6, 8), (9, 11), (10, 12)],  # Week 2
            [(1, 4), (2, 3), (5, 8), (6, 7), (9, 12), (10, 11)],  # Week 3
            [(1, 5), (2, 6), (3, 7), (4, 8), (9, 10), (11, 12)],  # Week 4
            [(1, 6), (2, 5), (3, 8), (4, 7), (9, 11), (10, 12)],  # Week 5
            [(1, 7), (2, 8), (3, 5), (4, 6), (9, 12), (10, 11)],  # Week 6
            [(1, 8), (2, 7), (3, 6), (4, 5), (9, 10), (11, 12)],  # Week 7
            [(1, 9), (2, 10), (3, 11), (4, 12), (5, 6), (7, 8)],  # Week 8
            [(1, 10), (2, 9), (3, 12), (4, 11), (5, 7), (6, 8)],  # Week 9
            [(1, 11), (2, 12), (3, 9), (4, 10), (5, 8), (6, 7)],  # Week 10
            [(1, 12), (2, 11), (3, 10), (4, 9), (5, 6), (7, 8)],  # Week 11
            [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12)],  # Week 12
            [(1, 3), (2, 4), (5, 7), (6, 8), (9, 11), (10, 12)],  # Week 13
            [(1, 4), (2, 3), (5, 8), (6, 7), (9, 12), (10, 11)],  # Week 14
        ]

        # Sample players for each team
        team_players = {
            t["id"]: [
                {"name": f"QB-{t['name'][:3]}", "position": "QB"},
                {"name": f"RB1-{t['name'][:3]}", "position": "RB"},
                {"name": f"RB2-{t['name'][:3]}", "position": "RB"},
                {"name": f"WR1-{t['name'][:3]}", "position": "WR"},
                {"name": f"WR2-{t['name'][:3]}", "position": "WR"},
                {"name": f"TE-{t['name'][:3]}", "position": "TE"},
                {"name": f"FLEX-{t['name'][:3]}", "position": "WR"},
                {"name": f"K-{t['name'][:3]}", "position": "K"},
                {"name": f"DEF-{t['name'][:3]}", "position": "DEF"},
                {"name": f"BE1-{t['name'][:3]}", "position": "RB"},
                {"name": f"BE2-{t['name'][:3]}", "position": "WR"},
            ] for t in teams
        }

        weekly_reports = []

        for week_num in range(1, 15):
            pairings = weekly_pairings[week_num - 1]
            matchups = []

            for home_id, away_id in pairings:
                home_team = next(t for t in teams if t["id"] == home_id)
                away_team = next(t for t in teams if t["id"] == away_id)

                # Generate realistic scores (80-160 range)
                home_score = Decimal(str(round(random.uniform(85, 155), 2)))
                away_score = Decimal(str(round(random.uniform(85, 155), 2)))

                # Determine winner
                if home_score > away_score:
                    winner_id = home_id
                    team_stats[home_id]["wins"] += 1
                    team_stats[away_id]["losses"] += 1
                elif away_score > home_score:
                    winner_id = away_id
                    team_stats[away_id]["wins"] += 1
                    team_stats[home_id]["losses"] += 1
                else:
                    winner_id = None  # Tie

                # Update points
                team_stats[home_id]["pf"] += float(home_score)
                team_stats[home_id]["pa"] += float(away_score)
                team_stats[away_id]["pf"] += float(away_score)
                team_stats[away_id]["pa"] += float(home_score)

                # Generate player data
                players = []
                roster_slots = ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DEF", "BE", "BE"]

                for team_id in [home_id, away_id]:
                    team_name = next(t["name"] for t in teams if t["id"] == team_id)
                    for i, player_info in enumerate(team_players[team_id]):
                        is_starter = i < 9  # First 9 are starters
                        slot = roster_slots[i]
                        score = Decimal(str(round(random.uniform(2, 35), 1)))

                        players.append({
                            "name": player_info["name"],
                            "team": team_name,
                            "position": player_info["position"],
                            "is_starter": is_starter,
                            "roster_slot": slot,
                            "actual_score": score
                        })

                matchups.append({
                    "week": week_num,
                    "home_team": {"id": home_id, "name": home_team["name"], "logo": home_team["logo"]},
                    "away_team": {"id": away_id, "name": away_team["name"], "logo": away_team["logo"]},
                    "home_score": home_score,
                    "away_score": away_score,
                    "winner_id": winner_id,
                    "players": players
                })

            # Build divisions with current standings
            east_teams = []
            west_teams = []

            # Sort teams by standings criteria
            sorted_teams = sorted(
                teams,
                key=lambda t: (-team_stats[t["id"]]["wins"],
                              team_stats[t["id"]]["losses"],
                              -team_stats[t["id"]]["pf"]),
            )

            for rank, team in enumerate(sorted_teams, 1):
                team_data = {
                    "id": team["id"],
                    "name": team["name"],
                    "owner": team["owner"],
                    "logo": team["logo"],
                    "wins": Decimal(str(team_stats[team["id"]]["wins"])),
                    "losses": Decimal(str(team_stats[team["id"]]["losses"])),
                    "points_for": Decimal(str(round(team_stats[team["id"]]["pf"], 2))),
                    "points_against": Decimal(str(round(team_stats[team["id"]]["pa"], 2))),
                    "standing": Decimal(str(rank))
                }

                if team["division"] == "East":
                    east_teams.append(team_data)
                else:
                    west_teams.append(team_data)

            # Generate awards for this week
            awards = self._generate_week_awards(matchups, teams, week_num)

            weekly_reports.append({
                "week": week_num,
                "season": 2025,
                "league_id": 123456,
                "league_name": "Duke Football Invitational",
                "league_logo_url": "https://example.com/logo.png",
                "divisions": [
                    {"name": "East", "teams": east_teams},
                    {"name": "West", "teams": west_teams}
                ],
                "matchups": matchups,
                "awards": awards
            })

        return weekly_reports

    def _generate_week_awards(self, matchups, teams, week_num):
        """Generate realistic awards for a week."""
        from decimal import Decimal
        import random

        # Find highest/lowest scorers
        all_scores = []
        for m in matchups:
            all_scores.append((m["home_team"]["name"], float(m["home_score"])))
            all_scores.append((m["away_team"]["name"], float(m["away_score"])))

        all_scores.sort(key=lambda x: x[1])
        highest = all_scores[-1]
        lowest = all_scores[0]

        # Find a losing team for HSL
        losing_teams = []
        for m in matchups:
            if m["winner_id"] == m["away_team"]["id"]:
                losing_teams.append((m["home_team"]["name"], float(m["home_score"])))
            elif m["winner_id"] == m["home_team"]["id"]:
                losing_teams.append((m["away_team"]["name"], float(m["away_score"])))

        hsl_team = max(losing_teams, key=lambda x: x[1]) if losing_teams else None

        awards = {
            "mvp": {
                "player_name": f"Star-{highest[0][:3]}",
                "team_name": highest[0],
                "position": "QB",
                "score": Decimal(str(round(random.uniform(25, 40), 1)))
            },
            "mwp": {
                "player_name": f"Wasted-{lowest[0][:3]}",
                "team_name": lowest[0],
                "position": "RB",
                "score": Decimal(str(round(random.uniform(20, 35), 1)))
            }
        }

        if hsl_team:
            awards["hsl"] = {
                "team_name": hsl_team[0],
                "score": Decimal(str(hsl_team[1])),
                "additional_info": "Lost by narrow margin"
            }

        # Add efficiency awards every few weeks
        if week_num % 3 == 0:
            awards["ssl"] = {
                "team_name": highest[0],
                "actual_score": Decimal(str(highest[1])),
                "optimal_score": Decimal(str(highest[1] + 5)),
                "efficiency_percentage": Decimal("96.5")
            }
            awards["ifm"] = {
                "team_name": lowest[0],
                "actual_score": Decimal(str(lowest[1])),
                "optimal_score": Decimal(str(lowest[1] + 25)),
                "efficiency_percentage": Decimal("75.0")
            }

        return awards

    def test_full_pipeline_with_realistic_data(self, realistic_season_data, tmp_path):
        """
        End-to-end test: Generate annual recap from realistic 14-week season data.

        This test validates the entire pipeline works without errors when given
        data that simulates DynamoDB responses (including Decimal values).
        """
        generator = AnnualRecapGenerator()

        output_file = tmp_path / "integration-test-recap.html"
        result_path = generator.generate(realistic_season_data, str(output_file))

        # Verify file was created
        assert Path(result_path).exists()

        # Read and parse the HTML
        with open(result_path) as f:
            html_content = f.read()

        # Verify basic HTML structure
        assert "<!DOCTYPE html>" in html_content
        assert "2025 Season Wrapped" in html_content
        assert "Duke Football Invitational" in html_content

        # Verify all data sections are present
        assert "const teamData" in html_content
        assert "const awardsData" in html_content
        assert "const weeklyRecapData" in html_content
        assert "const seasonRecapData" in html_content
        assert "const teamStatsData" in html_content

        # Verify no Decimal objects leaked into output
        assert "Decimal(" not in html_content

    def test_team_data_aggregation_correctness(self, realistic_season_data):
        """
        Validate that team data aggregation produces correct standings.

        Verifies:
        - All 12 teams are present
        - 14 weeks of standings data
        - Weekly records have correct structure
        """
        generator = AnnualRecapGenerator()

        result = generator._aggregate_team_data(realistic_season_data)

        # Verify all teams present
        assert len(result['teams']) == 12

        # Verify 14 weeks of data
        assert len(result['weeklyStandings']) == 14
        assert len(result['weeklyRecords']) == 14

        # Verify each week has 12 team rankings
        for week_standings in result['weeklyStandings']:
            assert len(week_standings) == 12
            # Each team ID should appear exactly once
            assert len(set(week_standings)) == 12

        # Verify weekly records structure
        for week_records in result['weeklyRecords']:
            assert len(week_records) == 12
            for record in week_records:
                assert 'wins' in record
                assert 'losses' in record
                assert 'points' in record

        # Verify cumulative nature - last week should have most games
        final_week = result['weeklyRecords'][-1]
        total_wins = sum(r['wins'] for r in final_week)
        total_losses = sum(r['losses'] for r in final_week)
        # 14 weeks * 6 matchups = 84 games, so 84 wins and 84 losses
        assert total_wins == 84
        assert total_losses == 84

    def test_season_recap_pythagorean_calculation(self, realistic_season_data):
        """
        Validate Pythagorean wins calculation in season recap.

        Verifies:
        - Luckiest/unluckiest teams are identified
        - Pythagorean calculations produce valid results
        - Top-half/bottom-half filtering works correctly
        """
        generator = AnnualRecapGenerator()

        result = generator._aggregate_season_recap(realistic_season_data)

        # Verify all 6 recap stats are present
        assert 'weeklyHighScorerChampion' in result
        assert 'weeklyLowScorerChampion' in result
        assert 'luckiestTeam' in result
        assert 'unluckiestTeam' in result
        assert 'narrowestPlayoffWinner' in result
        assert 'closestPlayoffLoser' in result

        # Verify Pythagorean-based stats have expected fields
        if result['luckiestTeam']:
            lucky = result['luckiestTeam']
            assert 'expectedWins' in lucky
            assert 'actualWins' in lucky
            assert 'difference' in lucky
            assert isinstance(lucky['expectedWins'], (int, float))
            assert isinstance(lucky['actualWins'], int)

        if result['unluckiestTeam']:
            unlucky = result['unluckiestTeam']
            assert 'expectedWins' in unlucky
            assert 'actualWins' in unlucky
            assert 'difference' in unlucky

        # Verify margin-based stats have expected fields
        if result['narrowestPlayoffWinner']:
            narrow = result['narrowestPlayoffWinner']
            assert 'avgMargin' in narrow
            assert isinstance(narrow['avgMargin'], (int, float))

        if result['closestPlayoffLoser']:
            closest = result['closestPlayoffLoser']
            assert 'avgMargin' in closest

    def test_team_stats_player_aggregation(self, realistic_season_data):
        """
        Validate team stats aggregation includes player data.

        Verifies:
        - All 12 teams have stats
        - Player statistics are calculated
        - Win streaks and Pythagorean wins are computed
        """
        generator = AnnualRecapGenerator()

        result = generator._aggregate_team_stats(realistic_season_data)

        assert 'teams' in result
        assert len(result['teams']) == 12

        for team in result['teams']:
            # Verify required fields
            assert 'teamId' in team
            assert 'teamName' in team
            assert 'logo' in team
            assert 'winStreak' in team
            assert 'pythagoreanWins' in team

            # Verify Pythagorean structure
            pyth = team['pythagoreanWins']
            assert 'expected' in pyth
            assert 'actual' in pyth
            assert 'difference' in pyth

            # Verify player stats (should have data from fixture)
            assert 'mostStarted' in team
            assert 'mostBenched' in team
            assert 'highestScorer' in team
            assert 'lowestScoringStarter' in team
            assert 'mostDisrespected' in team

            # If player data exists, verify structure
            if team['mostStarted']:
                assert 'playerName' in team['mostStarted']
                assert 'startCount' in team['mostStarted']
                assert team['mostStarted']['startCount'] > 0

    def test_embedded_json_is_valid(self, realistic_season_data, tmp_path):
        """
        Validate that embedded JSON in HTML can be parsed.

        This catches issues with JSON serialization, Decimal conversion,
        and regex replacement errors.
        """
        import re

        generator = AnnualRecapGenerator()

        output_file = tmp_path / "json-validation-test.html"
        generator.generate(realistic_season_data, str(output_file))

        with open(output_file) as f:
            html_content = f.read()

        # Extract and parse each JSON block
        json_patterns = [
            (r'const teamData = ({[\s\S]*?});', 'teamData'),
            (r'const awardsData = ({[\s\S]*?});', 'awardsData'),
            (r'const weeklyRecapData = ({[\s\S]*?});', 'weeklyRecapData'),
            (r'const seasonRecapData = ({[\s\S]*?});', 'seasonRecapData'),
            (r'const teamStatsData = ({[\s\S]*?});', 'teamStatsData'),
        ]

        for pattern, name in json_patterns:
            match = re.search(pattern, html_content)
            assert match is not None, f"Could not find {name} in HTML"

            json_str = match.group(1)
            try:
                parsed = json.loads(json_str)
                assert parsed is not None, f"{name} parsed to None"
            except json.JSONDecodeError as e:
                pytest.fail(f"Failed to parse {name} JSON: {e}")

    def test_handles_missing_player_data_gracefully(self, tmp_path):
        """
        Test that generator handles weeks with missing player data.

        Some historical data may not have player-level details.
        """
        from decimal import Decimal

        generator = AnnualRecapGenerator()

        # Create minimal data without player details
        reports = [{
            "week": 1,
            "season": 2025,
            "league_name": "Test League",
            "divisions": [{"name": "Div", "teams": [
                {"id": 1, "name": "Team A", "logo": "a.png",
                 "wins": Decimal("1"), "losses": Decimal("0"), "standing": Decimal("1")},
                {"id": 2, "name": "Team B", "logo": "b.png",
                 "wins": Decimal("0"), "losses": Decimal("1"), "standing": Decimal("2")}
            ]}],
            "matchups": [{
                "home_team": {"id": 1, "name": "Team A", "logo": "a.png"},
                "away_team": {"id": 2, "name": "Team B", "logo": "b.png"},
                "home_score": Decimal("120.5"),
                "away_score": Decimal("100.0"),
                "winner_id": 1
                # No players field
            }],
            "awards": {}
        }]

        output_file = tmp_path / "missing-players-test.html"
        result = generator.generate(reports, str(output_file))

        assert Path(result).exists()

        # Verify team stats still generates (with null player data)
        team_stats = generator._aggregate_team_stats(reports)
        assert len(team_stats['teams']) == 2

    def test_awards_aggregation_correctness(self, realistic_season_data):
        """
        Validate awards are aggregated correctly across weeks.

        Verifies:
        - Award winners are identified
        - Tie handling works
        - All award types are processed
        """
        generator = AnnualRecapGenerator()

        result = generator._aggregate_awards_data(realistic_season_data)

        assert 'awards' in result

        # Should have MVP and MWP awards (from fixture)
        award_ids = [a['id'] for a in result['awards']]
        assert 'mvp' in award_ids
        assert 'mwp' in award_ids

        # Verify award structure
        for award in result['awards']:
            assert 'id' in award
            assert 'title' in award
            assert 'icon' in award
            assert 'winners' in award

            # Winners should be a list
            assert isinstance(award['winners'], list)
            assert len(award['winners']) >= 1

            for winner in award['winners']:
                assert 'teamName' in winner
                assert 'count' in winner
                assert winner['count'] >= 1

    def test_weekly_highlights_aggregation(self, realistic_season_data):
        """
        Validate weekly highlights are aggregated correctly.

        Verifies:
        - All 14 weeks have highlights
        - Highest/lowest scorers are identified
        - Winners list is populated
        """
        generator = AnnualRecapGenerator()

        result = generator._aggregate_weekly_highlights(realistic_season_data)

        assert 'weeks' in result
        assert len(result['weeks']) == 14

        for week_data in result['weeks']:
            assert 'week' in week_data
            assert 'highestScorer' in week_data
            assert 'lowestScorer' in week_data
            assert 'winners' in week_data

            # Verify scorer structure
            high = week_data['highestScorer']
            assert 'teamName' in high
            assert 'score' in high
            assert high['score'] > 0

            low = week_data['lowestScorer']
            assert 'teamName' in low
            assert 'score' in low

            # Highest should be >= lowest
            assert high['score'] >= low['score']

            # Should have winners (6 matchups = 6 winners)
            assert len(week_data['winners']) == 6
