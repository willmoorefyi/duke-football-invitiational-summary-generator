"""Integration tests for matchup history and team lightbox functionality."""

import pytest
from src.pipeline.aggregate_stage import AggregateStage
from src.generators.templated_html_generator import TemplatedFantasyHTMLGenerator


class TestMatchupHistoryIntegration:
    """Test end-to-end integration of matchup history and lightbox functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.aggregate_stage = AggregateStage("test_league")
        self.html_generator = TemplatedFantasyHTMLGenerator()

        # Real-world-like data structure with mixed ID types (simulating ESPN data)
        self.sample_weeks_data = [
            {
                'week': 1.0,  # Float week number (common in ESPN data)
                'matchups': [
                    {
                        'home_team': {'id': 1.0, 'name': 'Team Alpha'},  # Numeric ID
                        'away_team': {'id': 2.0, 'name': 'Team Beta'},
                        'home_score': 125.5,
                        'away_score': 118.3,
                        'home_projected_score': 120.0,
                        'away_projected_score': 115.0,
                        'home_optimal_score': 135.2,
                        'away_optimal_score': 128.7
                    },
                    {
                        'home_team': {'id': 3.0, 'name': 'Team Gamma'},
                        'away_team': {'id': 4.0, 'name': 'Team Delta'},
                        'home_score': 110.2,
                        'away_score': 105.8,
                        'home_projected_score': 108.0,
                        'away_projected_score': 112.0,
                        'home_optimal_score': 125.0,
                        'away_optimal_score': 120.0
                    }
                ]
            },
            {
                'week': 2.0,
                'matchups': [
                    {
                        'home_team': {'id': 2.0, 'name': 'Team Beta'},
                        'away_team': {'id': 1.0, 'name': 'Team Alpha'},
                        'home_score': 142.8,
                        'away_score': 135.2,
                        'home_projected_score': 130.0,
                        'away_projected_score': 125.0,
                        'home_optimal_score': 148.5,
                        'away_optimal_score': 142.1
                    },
                    {
                        'home_team': {'id': 4.0, 'name': 'Team Delta'},
                        'away_team': {'id': 3.0, 'name': 'Team Gamma'},
                        'home_score': 98.5,
                        'away_score': 103.2,
                        'home_projected_score': 105.0,
                        'away_projected_score': 100.0,
                        'home_optimal_score': 115.0,
                        'away_optimal_score': 118.0
                    }
                ]
            }
        ]

        # Team data structure (string IDs as typically used in frontend)
        self.sample_teams = {
            '1': {
                'id': '1',
                'name': 'Team Alpha',
                'owner': 'Owner A',
                'division': 'Division A',
                'logo': 'https://example.com/alpha.png'
            },
            '2': {
                'id': '2',
                'name': 'Team Beta',
                'owner': 'Owner B',
                'division': 'Division B',
                'logo': 'https://example.com/beta.png'
            },
            '3': {
                'id': '3',
                'name': 'Team Gamma',
                'owner': 'Owner C',
                'division': 'Division A',
                'logo': 'https://example.com/gamma.png'
            },
            '4': {
                'id': '4',
                'name': 'Team Delta',
                'owner': 'Owner D',
                'division': 'Division B',
                'logo': 'https://example.com/delta.png'
            }
        }

    def test_end_to_end_matchup_history_flow(self):
        """Test complete flow from aggregate stage through to lightbox data."""
        # Step 1: Generate matchup history structure
        matchup_history = self.aggregate_stage._calculate_matchup_history(self.sample_weeks_data)

        # Verify structure
        assert 'weekly_results' in matchup_history
        weekly_results = matchup_history['weekly_results']

        # Should have integer keys (not float strings)
        assert 1 in weekly_results
        assert 2 in weekly_results
        assert len(weekly_results[1]) == 2  # 2 matchups in week 1
        assert len(weekly_results[2]) == 2  # 2 matchups in week 2

        # Step 2: Create enhanced data structure
        enhanced_data = {
            'current_week_data': {
                'divisions': [
                    {
                        'name': 'Division A',
                        'teams': list(self.sample_teams.values())
                    }
                ]
            },
            'season_context': {
                'team_standings': {
                    '1': {'wins': 1, 'losses': 1, 'ties': 0, 'points_for': 260.7, 'points_against': 261.1, 'overall_rank': 1},
                    '2': {'wins': 1, 'losses': 1, 'ties': 0, 'points_for': 261.1, 'points_against': 260.7, 'overall_rank': 2},
                    '3': {'wins': 1, 'losses': 1, 'ties': 0, 'points_for': 213.4, 'points_against': 204.0, 'overall_rank': 3},
                    '4': {'wins': 1, 'losses': 1, 'ties': 0, 'points_for': 204.3, 'points_against': 213.7, 'overall_rank': 4}
                },
                'matchup_history': matchup_history
            }
        }

        # Step 3: Test HTML generator processing
        team_weekly_results = self.html_generator._calculate_team_weekly_results(enhanced_data, self.sample_teams)

        # Verify all teams have results
        assert len(team_weekly_results) == 4
        for team_id in ['1', '2', '3', '4']:
            assert team_id in team_weekly_results
            assert len(team_weekly_results[team_id]) == 2  # 2 weeks of results

        # Verify specific results for Team Alpha (ID '1')
        team1_results = team_weekly_results['1']

        # Week 1: Team Alpha won at home vs Team Beta
        week1_result = team1_results[0]
        assert week1_result['week'] == 1
        assert week1_result['opponent'] == 'Team Beta'
        assert week1_result['homeAway'] == 'vs'
        assert week1_result['result'] == 'Win'
        assert week1_result['recordAfter'] == '1-0'

        # Week 2: Team Alpha lost away at Team Beta
        week2_result = team1_results[1]
        assert week2_result['week'] == 2
        assert week2_result['opponent'] == 'Team Beta'
        assert week2_result['homeAway'] == '@'
        assert week2_result['result'] == 'Loss'
        assert week2_result['recordAfter'] == '1-1'

        # Step 4: Test lightbox data preparation
        team_logos = {team['name']: team.get('logo', '') for team in self.sample_teams.values()}
        lightbox_data = self.html_generator._prepare_team_lightbox_data(enhanced_data, team_logos)

        # Verify lightbox data structure
        assert len(lightbox_data) == 4
        for team_id in ['1', '2', '3', '4']:
            assert team_id in lightbox_data
            team_data = lightbox_data[team_id]

            # Verify basic team info
            assert 'name' in team_data
            assert 'seasonStats' in team_data
            assert 'weeklyResults' in team_data

            # Verify weekly results in lightbox
            weekly_results = team_data['weeklyResults']
            assert len(weekly_results) == 2  # Should have 2 weeks of results

            # Verify each result has required fields
            for result in weekly_results:
                assert 'week' in result
                assert 'opponent' in result
                assert 'homeAway' in result
                assert 'result' in result
                assert 'recordAfter' in result

    def test_json_serialization_compatibility(self):
        """Test that the matchup history survives JSON serialization/deserialization."""
        import json

        # Generate matchup history
        matchup_history = self.aggregate_stage._calculate_matchup_history(self.sample_weeks_data)

        # Simulate JSON serialization/deserialization (what happens in real pipeline)
        json_str = json.dumps(matchup_history)
        deserialized_history = json.loads(json_str)

        # Keys should be strings after JSON round-trip
        weekly_results = deserialized_history['weekly_results']
        assert '1' in weekly_results or 1 in weekly_results  # Should handle both

        # Test HTML generator can handle string keys
        enhanced_data = {
            'season_context': {
                'matchup_history': deserialized_history
            }
        }

        team_weekly_results = self.html_generator._calculate_team_weekly_results(enhanced_data, self.sample_teams)

        # Should still process correctly
        for team_id in ['1', '2', '3', '4']:
            assert team_id in team_weekly_results
            assert len(team_weekly_results[team_id]) == 2

    def test_backward_compatibility_with_float_keys(self):
        """Test that HTML generator handles float-string keys (1.0, 2.0) from old data."""
        # Simulate old data structure with float-string keys
        old_format_history = {
            'weekly_results': {
                '1.0': self.sample_weeks_data[0]['matchups'],
                '2.0': self.sample_weeks_data[1]['matchups']
            }
        }

        enhanced_data = {
            'season_context': {
                'matchup_history': old_format_history
            }
        }

        # Should still work with backward compatibility
        team_weekly_results = self.html_generator._calculate_team_weekly_results(enhanced_data, self.sample_teams)

        # Verify results
        for team_id in ['1', '2', '3', '4']:
            assert team_id in team_weekly_results
            assert len(team_weekly_results[team_id]) == 2