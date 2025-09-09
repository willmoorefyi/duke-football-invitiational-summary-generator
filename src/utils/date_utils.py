from datetime import datetime, timedelta
from dateutil.parser import parse as parse_date
from typing import Tuple, Optional
from .config import get_config


class NFLWeekCalculator:
    def __init__(self, season_start: Optional[str] = None):
        config = get_config()
        self.season_start = parse_date(season_start or config.nfl_schedule.season_start)
        self.regular_season_weeks = config.nfl_schedule.regular_season_weeks
        self.playoff_weeks = config.nfl_schedule.playoff_weeks
    
    def get_current_nfl_week(self, reference_date: Optional[datetime] = None) -> int:
        """
        Calculate the current NFL week based on the reference date.
        
        Args:
            reference_date: Date to calculate from (defaults to now)
            
        Returns:
            NFL week number (1-based)
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        # Calculate days since season start
        days_since_start = (reference_date - self.season_start).days
        
        # Each NFL week runs Thursday to Wednesday (7 days)
        week_number = (days_since_start // 7) + 1
        
        # Clamp to valid range
        max_weeks = self.regular_season_weeks + self.playoff_weeks
        return max(1, min(week_number, max_weeks))
    
    def get_week_date_range(self, week: int) -> Tuple[datetime, datetime]:
        """
        Get the date range for a specific NFL week.
        
        Args:
            week: NFL week number (1-based)
            
        Returns:
            Tuple of (start_date, end_date) for the week
        """
        week_start = self.season_start + timedelta(weeks=week-1)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        return week_start, week_end
    
    def is_week_complete(self, week: int, reference_date: Optional[datetime] = None) -> bool:
        """
        Check if a given NFL week is complete.
        
        Args:
            week: NFL week number to check
            reference_date: Date to check against (defaults to now)
            
        Returns:
            True if the week is complete (past Wednesday night)
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        _, week_end = self.get_week_date_range(week)
        return reference_date > week_end
    
    def get_week_for_date(self, date: datetime) -> int:
        """
        Get the NFL week number for a specific date.
        
        Args:
            date: Date to get week for
            
        Returns:
            NFL week number (1-based)
        """
        return self.get_current_nfl_week(date)
    
    def get_previous_complete_week(self, reference_date: Optional[datetime] = None) -> int:
        """
        Get the most recent completed NFL week.
        
        Args:
            reference_date: Date to calculate from (defaults to now)
            
        Returns:
            NFL week number of the most recent completed week
        """
        current_week = self.get_current_nfl_week(reference_date)
        
        # Check if current week is complete
        if self.is_week_complete(current_week, reference_date):
            return current_week
        else:
            return max(1, current_week - 1)


def get_nfl_week_calculator() -> NFLWeekCalculator:
    """Get a configured NFL week calculator."""
    return NFLWeekCalculator()


def parse_date_input(date_str: Optional[str]) -> datetime:
    """
    Parse a date string input, defaulting to now if None.
    
    Args:
        date_str: Date string to parse (ISO format preferred)
        
    Returns:
        Parsed datetime object
    """
    if date_str is None:
        return datetime.now()
    
    try:
        return parse_date(date_str)
    except Exception as e:
        raise ValueError(f"Unable to parse date '{date_str}': {e}")