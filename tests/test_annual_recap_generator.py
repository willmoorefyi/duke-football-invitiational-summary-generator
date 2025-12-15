"""
Tests for annual recap generator
"""

import pytest
import json
from pathlib import Path
from src.generators.annual_recap_generator import AnnualRecapGenerator


@pytest.fixture
def sample_weekly_reports():
    """Fixture providing sample weekly report data."""
    return [
        {
            "week": 1,
            "season": 2024,
            "league_id": 123456,
            "divisions": [
                {
                    "name": "Division A",
                    "teams": [
                        {"id": 1, "name": "Team Alpha", "owner": "Owner 1", "logo": "logo1.png",
                         "wins": 1, "losses": 0, "points_for": 125.5, "points_against": 98.2},
                        {"id": 2, "name": "Team Bravo", "owner": "Owner 2", "logo": "logo2.png",
                         "wins": 1, "losses": 0, "points_for": 118.3, "points_against": 102.1}
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
            "season": 2024,
            "league_id": 123456,
            "divisions": [
                {
                    "name": "Division A",
                    "teams": [
                        {"id": 1, "name": "Team Alpha", "owner": "Owner 1", "logo": "logo1.png",
                         "wins": 1, "losses": 1, "points_for": 238.7, "points_against": 215.6},
                        {"id": 2, "name": "Team Bravo", "owner": "Owner 2", "logo": "logo2.png",
                         "wins": 2, "losses": 0, "points_for": 235.7, "points_against": 220.5}
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

    def test_aggregate_team_data(self, sample_weekly_reports):
        """Test team data aggregation across weeks."""
        generator = AnnualRecapGenerator()
        result = generator._aggregate_team_data(sample_weekly_reports)

        # Verify structure
        assert 'teams' in result
        assert 'weekly_standings' in result
        assert 'weekly_records' in result

        # Verify teams
        assert len(result['teams']) == 2
        assert result['teams'][0]['id'] == 1
        assert result['teams'][0]['name'] == 'Team Alpha'
        assert result['teams'][1]['id'] == 2

        # Verify weekly standings
        assert len(result['weekly_standings']) == 2
        # Week 1: Team Alpha wins (1-0), Team Bravo loses (1-0 but lower score)
        # Week 2: Team Bravo leads (2-0), Team Alpha falls (1-1)
        assert result['weekly_standings'][0] == [1, 2]  # Alpha first in week 1
        assert result['weekly_standings'][1] == [2, 1]  # Bravo first in week 2

        # Verify weekly records
        assert len(result['weekly_records']) == 2
        assert result['weekly_records'][0][0]['wins'] == 1
        assert result['weekly_records'][0][0]['losses'] == 0
        assert result['weekly_records'][1][1]['wins'] == 2

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

        # Verify winner details (should be either Team Alpha or Team Bravo with 1 win each)
        assert 'winner' in mvp_award
        assert mvp_award['winner']['count'] >= 1
        assert 'details' in mvp_award
        assert len(mvp_award['details']) >= 1

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
        assert 'Annual recap generated' in html_content or 'Duke Football' in html_content
        assert 'const teamData' in html_content
        assert 'const awardsData' in html_content
        assert 'const weeklyRecapData' in html_content

        # Verify real data is embedded
        assert 'Team Alpha' in html_content
        assert 'Team Bravo' in html_content

    def test_empty_reports_handling(self):
        """Test handling of empty weekly reports."""
        generator = AnnualRecapGenerator()

        result = generator._aggregate_team_data([])
        assert result['teams'] == []
        assert result['weekly_standings'] == []
        assert result['weekly_records'] == []

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
        assert mvp_award['winner']['teamName'] == 'Team Alpha'
        assert mvp_award['winner']['count'] == 3
        assert len(mvp_award['details']) == 3
