"""
Aggregate Stage

Stage 3: Aggregate Data Generation
Combines current week data with historical DynamoDB data to create
enhanced JSON with season context.
Currently a scaffold - needs DynamoDB integration.
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from .base import PipelineStage


class AggregateStage(PipelineStage):
    """
    Stage 3: Aggregate Data Generation

    Combines current week data with historical DynamoDB data to create
    enhanced JSON with season context.
    Currently a scaffold - needs DynamoDB integration.
    """

    def execute(self, current_week_file: str,
                dynamodb_record_id: Optional[str] = None,
                output_dir: Optional[str] = None) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Aggregate current week data with historical context.

        Args:
            current_week_file: Path to current week JSON from extract stage
            dynamodb_record_id: Record ID from upload stage (for tracking)
            output_dir: Output directory (defaults to config)

        Returns:
            Tuple of (enhanced_json_path, metadata)
        """
        self.logger.info(f"Starting data aggregation for file: {current_week_file}")

        # Determine output directory
        if output_dir is None:
            output_dir = 'output/enhanced'

        # Ensure output directory exists
        output_path = self._ensure_output_directory(output_dir)

        if self.dry_run:
            self.logger.info(f"DRY RUN: Would aggregate data and save to {output_path}")
            return None, {"dry_run": True}

        try:
            # Load current week data
            with open(current_week_file, 'r') as f:
                current_data = json.load(f)

            # Calculate enhanced season context from current week data
            enhanced_data = self._create_enhanced_data(current_data, dynamodb_record_id)

            # TODO: Query DynamoDB for historical league data and merge with current data
            # This would require implementing:
            # 1. Query DynamoDB for all weeks in current season
            # 2. Calculate actual season standings progression
            # 3. Compute real historical matchup records
            # 4. Aggregate actual award count summaries from all weeks
            # 5. Generate real performance trends and analytics

            # Save enhanced JSON
            week = current_data.get('week', 'unknown')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_path / f"enhanced_week_{week}_{timestamp}.json"

            with open(output_file, 'w') as f:
                json.dump(enhanced_data, f, indent=2, default=str)

            self.logger.info(f"Successfully aggregated data to {output_file}")
            self.logger.warning("Historical data aggregation not yet implemented - using current week only")

            metadata = {
                "week": week,
                "enhanced_file": str(output_file),
                "historical_weeks_count": 0,  # TODO: Actual count
                "aggregation_timestamp": timestamp
            }

            return str(output_file), metadata

        except Exception as e:
            self.logger.error(f"Failed to aggregate data: {e}")
            raise

    def _create_enhanced_data(self, current_data: Dict[str, Any], dynamodb_record_id: Optional[str]) -> Dict[str, Any]:
        """
        Create enhanced data structure with season context from current week data.

        Args:
            current_data: Current week raw data
            dynamodb_record_id: DynamoDB record ID for tracking

        Returns:
            Enhanced data structure with season context
        """
        try:
            # Extract basic info
            week = current_data.get('week', 1)
            season = current_data.get('season', datetime.now().year)
            league_id = current_data.get('league_id')

            # Calculate team performance metrics from current week
            team_performance = self._calculate_team_performance_metrics(current_data)

            # Calculate standings from current week (for progression baseline)
            current_standings = self._extract_current_standings(current_data)

            # Calculate matchup statistics
            matchup_stats = self._calculate_matchup_statistics(current_data)

            # Calculate award summaries from current week
            award_summaries = self._calculate_award_summaries(current_data)

            # Create enhanced structure
            enhanced_data = {
                "current_week": current_data,
                "season_context": {
                    "standings_progression": [
                        {
                            "week": week,
                            "standings": current_standings,
                            "timestamp": datetime.now().isoformat()
                        }
                    ],
                    "matchup_history": {
                        "head_to_head_records": {},  # TODO: Requires historical data
                        "current_week_matchups": matchup_stats,
                        "season_summary": {
                            "total_weeks_processed": 1,
                            "average_scores": team_performance.get("average_scores", {}),
                            "highest_weekly_score": team_performance.get("highest_score", 0),
                            "lowest_weekly_score": team_performance.get("lowest_score", 0)
                        }
                    },
                    "award_summaries": award_summaries,
                    "performance_trends": {
                        "team_metrics": team_performance,
                        "weekly_averages": {
                            "league_average_score": team_performance.get("league_average", 0),
                            "total_points_scored": team_performance.get("total_points", 0)
                        }
                    }
                },
                "metadata": {
                    "aggregation_timestamp": datetime.now().isoformat(),
                    "dynamodb_record_id": dynamodb_record_id,
                    "historical_weeks_included": 0,  # Will be > 0 when historical data is added
                    "season": season,
                    "league_id": league_id,
                    "current_week": week,
                    "data_source": "current_week_only"
                }
            }

            return enhanced_data

        except Exception as e:
            self.logger.error(f"Failed to create enhanced data structure: {e}")
            # Return minimal structure on error
            return {
                "current_week": current_data,
                "season_context": {
                    "standings_progression": [],
                    "matchup_history": {},
                    "award_summaries": {},
                    "performance_trends": {}
                },
                "metadata": {
                    "aggregation_timestamp": datetime.now().isoformat(),
                    "dynamodb_record_id": dynamodb_record_id,
                    "historical_weeks_included": 0,
                    "error": str(e)
                }
            }

    def _calculate_team_performance_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate team performance metrics from current week data"""
        try:
            matchups = data.get('matchups', [])
            all_scores = []
            team_scores = {}

            for matchup in matchups:
                home_score = matchup.get('home_team', {}).get('score', 0)
                away_score = matchup.get('away_team', {}).get('score', 0)

                home_id = matchup.get('home_team', {}).get('id')
                away_id = matchup.get('away_team', {}).get('id')

                if home_id:
                    team_scores[home_id] = home_score
                    all_scores.append(home_score)
                if away_id:
                    team_scores[away_id] = away_score
                    all_scores.append(away_score)

            if not all_scores:
                return {"error": "No scores found"}

            return {
                "average_scores": team_scores,
                "league_average": sum(all_scores) / len(all_scores) if all_scores else 0,
                "highest_score": max(all_scores) if all_scores else 0,
                "lowest_score": min(all_scores) if all_scores else 0,
                "total_points": sum(all_scores),
                "total_teams": len(team_scores)
            }
        except Exception as e:
            return {"error": str(e)}

    def _extract_current_standings(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract current standings from division data"""
        try:
            standings = []
            divisions = data.get('divisions', [])

            for division in divisions:
                division_name = division.get('name', 'Unknown')
                teams = division.get('teams', [])

                for team in teams:
                    standings.append({
                        "team_id": team.get('id'),
                        "team_name": team.get('name'),
                        "division": division_name,
                        "wins": team.get('wins', 0),
                        "losses": team.get('losses', 0),
                        "ties": team.get('ties', 0),
                        "points_for": team.get('points_for', 0),
                        "points_against": team.get('points_against', 0),
                        "rank": team.get('rank', 0)
                    })

            return standings
        except Exception as e:
            self.logger.warning(f"Failed to extract standings: {e}")
            return []

    def _calculate_matchup_statistics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate matchup statistics from current week"""
        try:
            matchups = data.get('matchups', [])
            stats = {
                "total_matchups": len(matchups),
                "completed_matchups": 0,
                "blowouts": [],  # Wins by > 30 points
                "close_games": [],  # Wins by < 10 points
                "upsets": []  # Lower seed beating higher seed
            }

            for matchup in matchups:
                home_score = matchup.get('home_team', {}).get('score', 0)
                away_score = matchup.get('away_team', {}).get('score', 0)

                if home_score > 0 or away_score > 0:
                    stats["completed_matchups"] += 1

                    # Calculate margin
                    margin = abs(home_score - away_score)

                    if margin > 30:
                        stats["blowouts"].append({
                            "winner": matchup.get('home_team', {}).get('name') if home_score > away_score else matchup.get('away_team', {}).get('name'),
                            "margin": margin
                        })
                    elif margin < 10:
                        stats["close_games"].append({
                            "winner": matchup.get('home_team', {}).get('name') if home_score > away_score else matchup.get('away_team', {}).get('name'),
                            "margin": margin
                        })

            return stats
        except Exception as e:
            self.logger.warning(f"Failed to calculate matchup statistics: {e}")
            return {"error": str(e)}

    def _calculate_award_summaries(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate award summaries from current week awards"""
        try:
            awards = data.get('awards', {})
            summaries = {
                "current_week_awards": awards,
                "season_totals": {
                    "mvp_winners": [],
                    "mwp_winners": [],
                    "mup_winners": [],
                    "mdp_winners": [],
                    "team_awards": {}
                }
            }

            # Extract current week award winners for season tracking
            if awards.get('mvp'):
                summaries["season_totals"]["mvp_winners"].append({
                    "week": data.get('week', 1),
                    "player": awards['mvp'].get('player_name'),
                    "team": awards['mvp'].get('team_name'),
                    "score": awards['mvp'].get('score')
                })

            # Add other awards similarly
            for award_type in ['mwp', 'mup', 'mdp']:
                if awards.get(award_type):
                    summaries["season_totals"][f"{award_type}_winners"].append({
                        "week": data.get('week', 1),
                        "player": awards[award_type].get('player_name'),
                        "team": awards[award_type].get('team_name'),
                        "score": awards[award_type].get('score')
                    })

            return summaries
        except Exception as e:
            self.logger.warning(f"Failed to calculate award summaries: {e}")
            return {"error": str(e)}