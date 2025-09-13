"""
Logo Validation Utilities

This module provides functions to validate team logos and replace invalid ones.
"""

import requests
from typing import Optional
from urllib.parse import urlparse
import logging


logger = logging.getLogger(__name__)


class LogoValidator:
    """Validates team logos and provides fallback options."""
    
    # Poop emoji as fallback for invalid logos
    POOP_EMOJI = "💩"
    
    # Common invalid redirect patterns
    INVALID_PATTERNS = [
        "404",
        "not found", 
        "error",
        "redirect",
        "landing",
        "default"
    ]
    
    # Valid image content types
    VALID_IMAGE_TYPES = [
        "image/jpeg",
        "image/jpg", 
        "image/png",
        "image/gif",
        "image/webp",
        "image/svg+xml"
    ]
    
    def __init__(self, timeout: int = 5):
        """Initialize the logo validator."""
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def is_valid_logo_url(self, url: str) -> bool:
        """
        Check if a logo URL is valid and returns an actual image.
        
        Args:
            url: The logo URL to validate
            
        Returns:
            True if the URL returns a valid image, False otherwise
        """
        if not url or not isinstance(url, str):
            return False
        
        # Basic URL validation
        try:
            parsed = urlparse(url)
            if not all([parsed.scheme, parsed.netloc]):
                return False
        except Exception:
            return False
        
        try:
            # Make HEAD request first to check headers without downloading
            response = self.session.head(url, timeout=self.timeout, allow_redirects=True)
            
            # Check status code
            if response.status_code >= 400:
                logger.debug(f"Logo URL returned {response.status_code}: {url}")
                return False
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not any(img_type in content_type for img_type in self.VALID_IMAGE_TYPES):
                # If HEAD doesn't give us content-type, try GET with small range
                try:
                    response = self.session.get(url, timeout=self.timeout, 
                                              stream=True, headers={'Range': 'bytes=0-1023'})
                    if response.status_code >= 400:
                        return False
                    content_type = response.headers.get('content-type', '').lower()
                    if not any(img_type in content_type for img_type in self.VALID_IMAGE_TYPES):
                        logger.debug(f"Logo URL has invalid content-type '{content_type}': {url}")
                        return False
                except Exception:
                    return False
            
            # Check for common invalid redirect patterns in final URL
            final_url = response.url.lower()
            if any(pattern in final_url for pattern in self.INVALID_PATTERNS):
                logger.debug(f"Logo URL appears to be invalid redirect: {url} -> {response.url}")
                return False
            
            logger.debug(f"Logo URL is valid: {url}")
            return True
            
        except requests.RequestException as e:
            logger.debug(f"Logo URL request failed: {url} - {e}")
            return False
        except Exception as e:
            logger.debug(f"Unexpected error validating logo URL: {url} - {e}")
            return False
    
    def get_validated_logo(self, url: str) -> str:
        """
        Get a validated logo URL or poop emoji if invalid.
        
        Args:
            url: The logo URL to validate
            
        Returns:
            The original URL if valid, or poop emoji if invalid
        """
        if self.is_valid_logo_url(url):
            return url
        else:
            logger.info(f"Replacing invalid logo with poop emoji: {url}")
            return self.POOP_EMOJI
    
    def validate_team_logos(self, teams: list) -> list:
        """
        Validate logos for a list of teams and replace invalid ones.
        
        Args:
            teams: List of team dictionaries with 'logo' field
            
        Returns:
            Updated list of teams with validated logos
        """
        for team in teams:
            if 'logo' in team and team['logo']:
                team['logo'] = self.get_validated_logo(team['logo'])
        return teams


# Global validator instance
_validator = None


def get_logo_validator() -> LogoValidator:
    """Get a shared logo validator instance."""
    global _validator
    if _validator is None:
        _validator = LogoValidator()
    return _validator


def validate_logo_url(url: str) -> bool:
    """Convenience function to validate a single logo URL."""
    return get_logo_validator().is_valid_logo_url(url)


def get_validated_logo(url: str) -> str:
    """Convenience function to get validated logo or poop emoji."""
    return get_logo_validator().get_validated_logo(url)