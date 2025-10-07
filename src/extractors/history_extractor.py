"""
History extractor for fetching historical league data from ESPN API.

This module provides functionality to extract complete league history
including final standings, champions, and division information.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from espn_api.football import League

from src.models.history_models import (
    OwnerInfo,
    DivisionInfo,
    TeamSeasonStanding,
    ChampionSummary,
    SeasonHistory,
    LeagueHistory,
    LeagueHistoryMetadata
)

logger = logging.getLogger(__name__)


class HistoryExtractor:
    """Extract historical league data from ESPN API."""

    def __init__(self, league_id: int, espn_s2: Optional[str] = None, swid: Optional[str] = None):
        """
        Initialize the history extractor.

        Args:
            league_id: ESPN league ID
            espn_s2: ESPN authentication cookie (for private leagues)
            swid: ESPN authentication cookie (for private leagues)
        """
        self.league_id = league_id
        self.espn_s2 = espn_s2
        self.swid = swid

    def _get_owner_name(self, owners: List[dict]) -> str:
        """
        Get formatted owner name from owner list.

        Args:
            owners: List of owner dictionaries

        Returns:
            Formatted owner name "FirstName LastName"
        """
        if not owners:
            return "Unknown Owner"

        owner = owners[0]
        first_name = owner.get('firstName', '')
        last_name = owner.get('lastName', '')
        return f"{first_name} {last_name}".strip() or "Unknown Owner"

    def _extract_owner_info(self, owners: List[dict]) -> List[OwnerInfo]:
        """
        Extract owner information from ESPN data.

        Args:
            owners: List of owner dictionaries from ESPN API

        Returns:
            List of OwnerInfo objects
        """
        owner_list = []
        for owner in owners:
            owner_list.append(OwnerInfo(
                first_name=owner.get('firstName', 'Unknown'),
                last_name=owner.get('lastName', ''),
                id=owner.get('id', '')
            ))
        return owner_list

    def _get_championship_title(self, final_standing: int) -> Optional[str]:
        """
        Get championship title based on final standing.

        Args:
            final_standing: Team's final standing (1 = champion, 2 = runner-up, etc.)

        Returns:
            Championship title or None
        """
        titles = {
            1: "Champion",
            2: "Runner-up",
            3: "Third Place"
        }
        return titles.get(final_standing)

    def extract_season(self, year: int) -> Optional[SeasonHistory]:
        """
        Extract historical data for a single season.

        Args:
            year: Season year to extract

        Returns:
            SeasonHistory object or None if extraction fails
        """
        try:
            logger.info(f"Extracting season {year} for league {self.league_id}")

            # Initialize league for specific year
            if self.espn_s2 and self.swid:
                league = League(
                    league_id=self.league_id,
                    year=year,
                    espn_s2=self.espn_s2,
                    swid=self.swid
                )
            else:
                league = League(
                    league_id=self.league_id,
                    year=year
                )

            # Get final standings
            standings = league.standings()

            if not standings:
                logger.warning(f"No standings found for year {year}")
                return None

            # Extract division information
            divisions_dict = {}
            for team in standings:
                div_id = team.division_id
                if div_id not in divisions_dict:
                    divisions_dict[div_id] = {
                        'division_id': div_id,
                        'division_name': team.division_name,
                        'teams': []
                    }
                divisions_dict[div_id]['teams'].append(team.team_name)

            divisions = [
                DivisionInfo(**div_data)
                for div_data in divisions_dict.values()
            ]

            # Build final standings list
            final_standings = []
            for rank, team in enumerate(standings, start=1):
                final_standing = team.final_standing if team.final_standing != 0 else team.standing

                team_standing = TeamSeasonStanding(
                    rank=rank,
                    team_id=team.team_id,
                    team_name=team.team_name,
                    team_abbrev=team.team_abbrev,
                    owners=self._extract_owner_info(team.owners) if team.owners else [],
                    division_id=team.division_id,
                    division_name=team.division_name,
                    wins=team.wins,
                    losses=team.losses,
                    ties=team.ties,
                    points_for=float(team.points_for),
                    points_against=float(team.points_against),
                    playoff_seed=team.standing,
                    final_standing=final_standing,
                    championship_title=self._get_championship_title(final_standing)
                )
                final_standings.append(team_standing)

            # Get top 3 finishers
            champion_team = standings[0]
            runner_up_team = standings[1] if len(standings) > 1 else None
            third_place_team = standings[2] if len(standings) > 2 else None

            champion = ChampionSummary(
                team_id=champion_team.team_id,
                team_name=champion_team.team_name,
                owner_name=self._get_owner_name(champion_team.owners) if champion_team.owners else "Unknown Owner",
                wins=champion_team.wins,
                losses=champion_team.losses,
                points_for=float(champion_team.points_for)
            )

            runner_up = None
            if runner_up_team:
                runner_up = ChampionSummary(
                    team_id=runner_up_team.team_id,
                    team_name=runner_up_team.team_name,
                    owner_name=self._get_owner_name(runner_up_team.owners) if runner_up_team.owners else "Unknown Owner",
                    wins=runner_up_team.wins,
                    losses=runner_up_team.losses,
                    points_for=float(runner_up_team.points_for)
                )

            third_place = None
            if third_place_team:
                third_place = ChampionSummary(
                    team_id=third_place_team.team_id,
                    team_name=third_place_team.team_name,
                    owner_name=self._get_owner_name(third_place_team.owners) if third_place_team.owners else "Unknown Owner",
                    wins=third_place_team.wins,
                    losses=third_place_team.losses,
                    points_for=float(third_place_team.points_for)
                )

            # Create season history
            season_history = SeasonHistory(
                year=year,
                regular_season_weeks=league.settings.reg_season_count,
                playoff_weeks=league.settings.playoff_team_count,  # Using playoff_team_count as proxy
                total_teams=len(standings),
                divisions=divisions,
                final_standings=final_standings,
                champion=champion,
                runner_up=runner_up,
                third_place=third_place
            )

            logger.info(f"Successfully extracted season {year} - Champion: {champion.team_name}")
            return season_history

        except Exception as e:
            logger.error(f"Failed to extract season {year}: {e}")
            return None

    def extract_history(self, start_year: int, end_year: int, league_name: Optional[str] = None) -> LeagueHistory:
        """
        Extract history for a range of years.

        Args:
            start_year: First season to extract
            end_year: Last season to extract
            league_name: Optional league name (will fetch from first available season if not provided)

        Returns:
            LeagueHistory object
        """
        logger.info(f"Extracting league history for years {start_year}-{end_year}")

        seasons = []
        extracted_league_name = league_name

        for year in range(start_year, end_year + 1):
            season = self.extract_season(year)
            if season:
                seasons.append(season)

                # Get league name from first successful season if not provided
                if not extracted_league_name:
                    try:
                        if self.espn_s2 and self.swid:
                            league = League(
                                league_id=self.league_id,
                                year=year,
                                espn_s2=self.espn_s2,
                                swid=self.swid
                            )
                        else:
                            league = League(
                                league_id=self.league_id,
                                year=year
                            )
                        extracted_league_name = league.settings.name
                    except Exception:
                        extracted_league_name = f"League {self.league_id}"

        if not extracted_league_name:
            extracted_league_name = f"League {self.league_id}"

        # Create metadata
        from datetime import timezone
        metadata = LeagueHistoryMetadata(
            extracted_at=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            total_seasons=len(seasons),
            year_range=f"{start_year}-{end_year}"
        )

        league_history = LeagueHistory(
            league_id=str(self.league_id),
            league_name=extracted_league_name,
            seasons=seasons,
            metadata=metadata
        )

        logger.info(f"Extracted {len(seasons)} seasons for {extracted_league_name}")
        return league_history

    def save_to_json(self, league_history: LeagueHistory, output_dir: str = "output/history") -> str:
        """
        Save league history to JSON file.

        Args:
            league_history: LeagueHistory object to save
            output_dir: Directory to save the file (default: output/history)

        Returns:
            Path to saved file
        """
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Generate filename (sanitize year_range to remove invalid path characters)
        year_range = league_history.metadata.year_range.replace('/', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"league_history_{league_history.league_id}_{year_range}_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)

        # Save to JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(league_history.model_dump(), f, indent=2, ensure_ascii=False)

        logger.info(f"Saved league history to {filepath}")
        return filepath
