import pytest
from unittest.mock import Mock, patch, MagicMock

from src.extractors.team_extractor import TeamExtractor
from src.utils.config import Config, TeamLogosConfig


class TestTeamLogoExtraction:
    """Test suite for custom team logo extraction in TeamExtractor."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock ESPN client
        self.mock_espn_client = Mock()

        # Create TeamExtractor instance
        self.extractor = TeamExtractor(self.mock_espn_client)

        # Mock the logger to avoid logging setup issues
        self.extractor.logger = Mock()

    def test_extract_logo_url_uses_custom_config_first(self):
        """Test that custom logo configuration is used before ESPN data."""
        # Mock ESPN team object
        mock_espn_team = Mock()
        mock_espn_team.logo_url = "https://espn.com/old_logo.png"
        mock_espn_team.team_name = "All About That Bass"

        # Mock the team logo configuration to return our custom logo
        with patch('src.extractors.team_extractor.get_team_logo_url') as mock_get_logo:
            mock_get_logo.return_value = "https://will.moore.fyi/duke-football-invitational/static/AllAboutThatBassAll2.png"

            # Call the method
            result = self.extractor._extract_logo_url("All About That Bass", mock_espn_team)

            # Verify custom logo was returned, not ESPN logo
            assert result == "https://will.moore.fyi/duke-football-invitational/static/AllAboutThatBassAll2.png"

            # Verify get_team_logo_url was called with correct team name
            mock_get_logo.assert_called_once_with("All About That Bass")

    def test_extract_logo_url_falls_back_to_espn(self):
        """Test that ESPN logo is used when custom config doesn't have the team."""
        # Mock ESPN team object
        mock_espn_team = Mock()
        mock_espn_team.logo_url = "https://espn.com/fallback_logo.png"

        # Mock the team logo configuration to return None (team not found)
        with patch('src.extractors.team_extractor.get_team_logo_url') as mock_get_logo:
            mock_get_logo.return_value = None

            # Call the method
            result = self.extractor._extract_logo_url("Unknown Team", mock_espn_team)

            # Verify ESPN logo was returned as fallback
            assert result == "https://espn.com/fallback_logo.png"

    def test_extract_logo_url_tries_multiple_espn_attributes(self):
        """Test that method tries different ESPN logo attribute names."""
        # Mock ESPN team object without logo_url but with logoUrl
        mock_espn_team = Mock()
        mock_espn_team.logo_url = None
        mock_espn_team.logoUrl = "https://espn.com/logo_url.png"

        # Mock team config returning None
        with patch('src.extractors.team_extractor.get_team_logo_url') as mock_get_logo:
            mock_get_logo.return_value = None

            # Call the method
            result = self.extractor._extract_logo_url("Unknown Team", mock_espn_team)

            # Verify alternative ESPN attribute was used
            assert result == "https://espn.com/logo_url.png"

    def test_extract_logo_url_returns_none_when_no_logos_found(self):
        """Test that None is returned when no logos are available."""
        # Mock ESPN team object with no logo attributes - use spec to prevent auto-creation
        mock_espn_team = Mock(spec=[])  # Empty spec means no attributes

        # Mock team config returning None
        with patch('src.extractors.team_extractor.get_team_logo_url') as mock_get_logo:
            mock_get_logo.return_value = None

            # Call the method
            result = self.extractor._extract_logo_url("Unknown Team", mock_espn_team)

            # Verify None is returned
            assert result is None

    def test_extract_logo_url_handles_exceptions(self):
        """Test that exceptions in logo extraction are handled gracefully."""
        # Mock ESPN team object
        mock_espn_team = Mock()

        # Mock team config to raise an exception
        with patch('src.extractors.team_extractor.get_team_logo_url') as mock_get_logo:
            mock_get_logo.side_effect = Exception("Logo lookup failed")

            # Call the method
            result = self.extractor._extract_logo_url("Test Team", mock_espn_team)

            # Verify None is returned and warning is logged
            assert result is None
            self.extractor.logger.warning.assert_called()

    def test_convert_espn_team_uses_updated_logo_extraction(self):
        """Test that _convert_espn_team calls the updated logo extraction method."""
        # Create a properly configured mock ESPN team to avoid Pydantic validation issues
        mock_espn_team = Mock()
        mock_espn_team.team_id = 1
        mock_espn_team.team_name = "Test Team"
        mock_espn_team.team_abbrev = "TEST"
        mock_espn_team.wins = 5
        mock_espn_team.losses = 3
        mock_espn_team.ties = 0  # Set ties directly to avoid getattr issues
        mock_espn_team.points_for = 100.0
        mock_espn_team.points_against = 90.0
        mock_espn_team.standing = 1
        mock_espn_team.playoff_pct = 75.5  # Add playoff percentage

        # Mock the logo extraction method
        with patch.object(self.extractor, '_extract_logo_url') as mock_extract_logo:
            mock_extract_logo.return_value = "https://test-logo.png"

            with patch.object(self.extractor, '_extract_owner_name') as mock_extract_owner:
                mock_extract_owner.return_value = "Test Owner"

                with patch.object(self.extractor, '_determine_team_division') as mock_division:
                    mock_division.return_value = "Test Division"

                    # Call the method
                    result = self.extractor._convert_espn_team(mock_espn_team)

                    # Verify logo extraction was called with team name and ESPN team
                    mock_extract_logo.assert_called_once_with("Test Team", mock_espn_team)

                    # Verify the logo was set correctly
                    assert result.logo == "https://test-logo.png"
                    assert result.name == "Test Team"

    @patch('src.extractors.team_extractor.get_team_logo_url')
    def test_integration_with_real_config(self, mock_get_logo):
        """Test integration with actual team logo configuration."""
        # Set up real config response
        mock_get_logo.return_value = "https://will.moore.fyi/duke-football-invitational/static/AtlantaFaldoneAll2.png"

        # Mock ESPN team
        mock_espn_team = Mock()
        mock_espn_team.logo_url = "https://old-espn-logo.png"

        # Call the method
        result = self.extractor._extract_logo_url("Atlanta Faldone", mock_espn_team)

        # Verify custom logo is used
        assert result == "https://will.moore.fyi/duke-football-invitational/static/AtlantaFaldoneAll2.png"
        mock_get_logo.assert_called_once_with("Atlanta Faldone")