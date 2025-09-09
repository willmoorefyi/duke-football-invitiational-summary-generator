import logging
from abc import ABC, abstractmethod
from typing import Any, Optional
from datetime import datetime

from ..utils.espn_client import ESPNClient
from ..utils.date_utils import get_nfl_week_calculator
from ..utils.config import get_config


logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """
    Abstract base class for all data extractors.
    Provides common functionality and interface for extracting data from ESPN.
    """
    
    def __init__(self, espn_client: ESPNClient, reference_date: Optional[datetime] = None):
        """
        Initialize the extractor.
        
        Args:
            espn_client: Connected ESPN client
            reference_date: Date to use for calculations (defaults to now)
        """
        self.espn_client = espn_client
        self.reference_date = reference_date or datetime.now()
        self.config = get_config()
        self.week_calculator = get_nfl_week_calculator()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Cache for expensive operations
        self._cache = {}
    
    def get_current_week(self) -> int:
        """Get the current NFL week based on reference date."""
        return self.week_calculator.get_current_nfl_week(self.reference_date)
    
    def get_target_week(self) -> int:
        """
        Get the week that should be extracted.
        This is typically the most recent completed week.
        """
        return self.week_calculator.get_previous_complete_week(self.reference_date)
    
    def is_week_complete(self, week: int) -> bool:
        """Check if a given week is complete."""
        return self.week_calculator.is_week_complete(week, self.reference_date)
    
    def get_cached_data(self, key: str) -> Any:
        """Get data from cache."""
        return self._cache.get(key)
    
    def set_cached_data(self, key: str, data: Any) -> None:
        """Store data in cache."""
        self._cache[key] = data
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
    
    @abstractmethod
    def extract(self) -> Any:
        """
        Extract the relevant data from ESPN.
        Must be implemented by subclasses.
        
        Returns:
            Extracted data in the appropriate format
        """
        pass
    
    def validate_week(self, week: int) -> bool:
        """
        Validate that a week number is reasonable.
        
        Args:
            week: Week number to validate
            
        Returns:
            True if week is valid
        """
        max_weeks = self.config.nfl_schedule.regular_season_weeks + self.config.nfl_schedule.playoff_weeks
        return 1 <= week <= max_weeks
    
    def log_extraction_start(self, data_type: str, week: Optional[int] = None) -> None:
        """Log the start of an extraction operation."""
        if week:
            self.logger.info(f"Starting extraction of {data_type} for week {week}")
        else:
            self.logger.info(f"Starting extraction of {data_type}")
    
    def log_extraction_complete(self, data_type: str, count: int, week: Optional[int] = None) -> None:
        """Log the completion of an extraction operation."""
        if week:
            self.logger.info(f"Completed extraction of {data_type} for week {week}: {count} items")
        else:
            self.logger.info(f"Completed extraction of {data_type}: {count} items")
    
    def handle_extraction_error(self, error: Exception, data_type: str, week: Optional[int] = None) -> None:
        """Handle and log extraction errors."""
        if week:
            self.logger.error(f"Failed to extract {data_type} for week {week}: {error}")
        else:
            self.logger.error(f"Failed to extract {data_type}: {error}")
        
        # Re-raise the error for the caller to handle
        raise