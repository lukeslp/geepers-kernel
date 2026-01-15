"""
Time zone and time calculation utilities.

This module provides utilities for timezone conversions, time calculations,
and duration parsing. Built on pytz for comprehensive timezone support.

Features:
- Timezone conversion with pytz
- Time difference calculations
- Duration parsing and addition
- Timezone validation and listing

Usage:
    from shared.utils.time_utils import convert_timezone, calculate_difference

    # Convert between timezones
    result = convert_timezone("2025-01-15 14:00:00", "America/New_York", "Asia/Tokyo")
    print(f"{result.original_time} → {result.converted_time}")

    # Calculate time difference
    diff = calculate_difference("2025-01-15 09:00:00", "2025-01-15 17:30:00", "UTC")
    print(f"Difference: {diff.hours}h {diff.minutes}m")

Author: Luke Steuber
"""

import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, List, Dict

try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    pytz = None
    PYTZ_AVAILABLE = False

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class TimeConversion:
    """
    Result of timezone conversion operation.

    Attributes:
        original_time: Original datetime with source timezone
        converted_time: Converted datetime with target timezone
        from_timezone: Source timezone name
        to_timezone: Target timezone name
        offset_hours: Time offset in hours between timezones
    """
    original_time: datetime
    converted_time: datetime
    from_timezone: str
    to_timezone: str
    offset_hours: float


@dataclass
class TimeDifference:
    """
    Result of time difference calculation.

    Attributes:
        start_time: Earlier datetime
        end_time: Later datetime
        days: Difference in days
        hours: Hours component (0-23)
        minutes: Minutes component (0-59)
        seconds: Seconds component (0-59)
        total_hours: Total difference in fractional hours
        total_seconds: Total difference in seconds
    """
    start_time: datetime
    end_time: datetime
    days: int
    hours: int
    minutes: int
    seconds: int
    total_hours: float
    total_seconds: float


# ============================================================================
# Time Utilities Class
# ============================================================================

class TimeUtilities:
    """
    Comprehensive timezone and time calculation utilities.

    Example:
        >>> utils = TimeUtilities()
        >>> result = utils.convert_timezone("now", "UTC", "America/New_York")
        >>> print(f"Offset: {result.offset_hours} hours")
    """

    @staticmethod
    def convert_timezone(
        time_str: str,
        from_tz: str,
        to_tz: str
    ) -> TimeConversion:
        """
        Convert time between timezones.

        Args:
            time_str: Time string ("YYYY-MM-DD HH:MM:SS" or "now")
            from_tz: Source timezone (e.g., "America/New_York")
            to_tz: Target timezone (e.g., "Asia/Tokyo")

        Returns:
            TimeConversion with converted time and metadata

        Raises:
            ImportError: If pytz not installed
            ValueError: If time format invalid
            pytz.exceptions.UnknownTimeZoneError: If timezone invalid

        Example:
            >>> result = TimeUtilities.convert_timezone(
            ...     "2025-01-15 14:00:00",
            ...     "America/New_York",
            ...     "Asia/Tokyo"
            ... )
            >>> print(result.converted_time)
        """
        if not PYTZ_AVAILABLE:
            raise ImportError("pytz required. Install with: pip install pytz")

        # Parse input time
        if time_str.lower() == 'now':
            dt = datetime.now()
        else:
            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")

        # Add source timezone
        source_tz = pytz.timezone(from_tz)
        dt_with_tz = source_tz.localize(dt)

        # Convert to target timezone
        target_tz = pytz.timezone(to_tz)
        converted = dt_with_tz.astimezone(target_tz)

        # Calculate offset
        offset_hours = (converted.utcoffset().total_seconds() -
                       dt_with_tz.utcoffset().total_seconds()) / 3600

        logger.info(f"Converted {time_str} from {from_tz} to {to_tz}")

        return TimeConversion(
            original_time=dt_with_tz,
            converted_time=converted,
            from_timezone=from_tz,
            to_timezone=to_tz,
            offset_hours=offset_hours
        )

    @staticmethod
    def calculate_difference(
        time1_str: str,
        time2_str: str,
        timezone: str = "UTC"
    ) -> TimeDifference:
        """
        Calculate time difference between two times.

        Args:
            time1_str: First time ("YYYY-MM-DD HH:MM:SS")
            time2_str: Second time ("YYYY-MM-DD HH:MM:SS")
            timezone: Timezone for both times (default: "UTC")

        Returns:
            TimeDifference with calculated values

        Example:
            >>> diff = TimeUtilities.calculate_difference(
            ...     "2025-01-15 09:00:00",
            ...     "2025-01-15 17:30:00",
            ...     "UTC"
            ... )
            >>> print(f"{diff.hours}h {diff.minutes}m")
        """
        if not PYTZ_AVAILABLE:
            raise ImportError("pytz required. Install with: pip install pytz")

        # Parse times
        dt1 = datetime.strptime(time1_str, "%Y-%m-%d %H:%M:%S")
        dt2 = datetime.strptime(time2_str, "%Y-%m-%d %H:%M:%S")

        # Add timezone
        tz = pytz.timezone(timezone)
        dt1 = tz.localize(dt1)
        dt2 = tz.localize(dt2)

        # Calculate difference (absolute value)
        diff = abs(dt2 - dt1)

        days = diff.days
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        seconds = diff.seconds % 60

        total_hours = diff.total_seconds() / 3600
        total_seconds = diff.total_seconds()

        logger.info(f"Time difference: {days}d {hours}h {minutes}m")

        return TimeDifference(
            start_time=min(dt1, dt2),
            end_time=max(dt1, dt2),
            days=days,
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            total_hours=total_hours,
            total_seconds=total_seconds
        )

    @staticmethod
    def add_duration(
        time_str: str,
        duration: str,
        timezone: str = "UTC"
    ) -> datetime:
        """
        Add duration to a time.

        Args:
            time_str: Base time ("YYYY-MM-DD HH:MM:SS" or "now")
            duration: Duration string (format: "XdYhZm", e.g., "2d3h30m")
            timezone: Timezone for the time

        Returns:
            Datetime after adding duration

        Example:
            >>> result = TimeUtilities.add_duration(
            ...     "2025-01-15 14:00:00",
            ...     "2d3h30m",
            ...     "America/New_York"
            ... )
            >>> print(result)
        """
        if not PYTZ_AVAILABLE:
            raise ImportError("pytz required. Install with: pip install pytz")

        # Parse base time
        if time_str.lower() == 'now':
            dt = datetime.now()
        else:
            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")

        tz = pytz.timezone(timezone)
        dt = tz.localize(dt)

        # Parse duration
        delta = TimeUtilities.parse_duration(duration)

        # Add duration
        result = dt + delta

        logger.info(f"Added {duration} to {time_str} in {timezone}")

        return result

    @staticmethod
    def parse_duration(duration_str: str) -> timedelta:
        """
        Parse duration string to timedelta.

        Args:
            duration_str: Duration (format: "XdYhZm", e.g., "1d2h30m")

        Returns:
            timedelta object

        Example:
            >>> delta = TimeUtilities.parse_duration("2d3h30m")
            >>> print(delta.total_seconds() / 3600)  # hours
        """
        days = hours = minutes = 0

        remaining = duration_str
        if 'd' in remaining:
            days = int(remaining.split('d')[0])
            remaining = remaining.split('d')[1] if len(remaining.split('d')) > 1 else ""
        if 'h' in remaining:
            hours = int(remaining.split('h')[0])
            remaining = remaining.split('h')[1] if len(remaining.split('h')) > 1 else ""
        if 'm' in remaining:
            minutes = int(remaining.split('m')[0])

        return timedelta(days=days, hours=hours, minutes=minutes)

    @staticmethod
    def list_timezones(filter_text: Optional[str] = None) -> List[str]:
        """
        List available timezones with optional filtering.

        Args:
            filter_text: Optional text to filter timezones

        Returns:
            List of timezone names

        Example:
            >>> timezones = TimeUtilities.list_timezones("America")
            >>> print(len(timezones))
        """
        if not PYTZ_AVAILABLE:
            raise ImportError("pytz required. Install with: pip install pytz")

        timezones = list(pytz.all_timezones)

        if filter_text:
            timezones = [tz for tz in timezones if filter_text.lower() in tz.lower()]

        return timezones

    @staticmethod
    def group_timezones() -> Dict[str, List[str]]:
        """
        Group timezones by region.

        Returns:
            Dictionary mapping regions to lists of timezones

        Example:
            >>> groups = TimeUtilities.group_timezones()
            >>> print(groups['America'][:3])
        """
        if not PYTZ_AVAILABLE:
            raise ImportError("pytz required. Install with: pip install pytz")

        by_region = {}
        for tz in pytz.all_timezones:
            parts = tz.split('/')
            region = parts[0] if len(parts) > 1 else 'Other'
            if region not in by_region:
                by_region[region] = []
            by_region[region].append(tz)

        return by_region

    @staticmethod
    def validate_timezone(tz: str) -> bool:
        """
        Check if timezone is valid.

        Args:
            tz: Timezone name to validate

        Returns:
            True if valid, False otherwise

        Example:
            >>> TimeUtilities.validate_timezone("America/New_York")
            True
            >>> TimeUtilities.validate_timezone("Invalid/Zone")
            False
        """
        if not PYTZ_AVAILABLE:
            return False

        try:
            pytz.timezone(tz)
            return True
        except Exception:
            return False

    @staticmethod
    def get_current_time(timezone: str) -> datetime:
        """
        Get current time in specified timezone.

        Args:
            timezone: Timezone name

        Returns:
            Current datetime in that timezone

        Example:
            >>> now = TimeUtilities.get_current_time("Asia/Tokyo")
            >>> print(now)
        """
        if not PYTZ_AVAILABLE:
            raise ImportError("pytz required. Install with: pip install pytz")

        tz = pytz.timezone(timezone)
        return datetime.now(tz)


# ============================================================================
# Functional Interface (Convenience Functions)
# ============================================================================

def convert_timezone(time_str: str, from_tz: str, to_tz: str) -> TimeConversion:
    """Convert time between timezones (functional interface)."""
    return TimeUtilities.convert_timezone(time_str, from_tz, to_tz)


def calculate_difference(time1: str, time2: str, timezone: str = "UTC") -> TimeDifference:
    """Calculate time difference (functional interface)."""
    return TimeUtilities.calculate_difference(time1, time2, timezone)


def add_time(base_time: str, duration: str, timezone: str = "UTC") -> datetime:
    """Add duration to base time (functional interface)."""
    return TimeUtilities.add_duration(base_time, duration, timezone)


def parse_duration(duration: str) -> timedelta:
    """Parse duration string to timedelta (functional interface)."""
    return TimeUtilities.parse_duration(duration)


def list_timezones(filter_text: Optional[str] = None) -> List[str]:
    """List available timezones (functional interface)."""
    return TimeUtilities.list_timezones(filter_text)


def validate_timezone(tz: str) -> bool:
    """Validate timezone name (functional interface)."""
    return TimeUtilities.validate_timezone(tz)


# ============================================================================
# Testing
# ============================================================================

def _test_time_utils():
    """Test function for standalone testing."""
    print("Testing TimeUtilities...")
    print(f"pytz available: {PYTZ_AVAILABLE}")

    if not PYTZ_AVAILABLE:
        print("\nERROR: pytz package required")
        print("Install with: pip install pytz")
        return

    print("\n1. Testing timezone conversion...")
    result = convert_timezone("2025-01-15 14:00:00", "America/New_York", "Asia/Tokyo")
    print(f"   NYC: {result.original_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Tokyo: {result.converted_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Offset: {result.offset_hours} hours")

    print("\n2. Testing time difference...")
    diff = calculate_difference("2025-01-15 09:00:00", "2025-01-15 17:30:00", "UTC")
    print(f"   Difference: {diff.hours}h {diff.minutes}m")
    print(f"   Total: {diff.total_hours:.2f} hours")

    print("\n3. Testing duration addition...")
    result = add_time("2025-01-15 14:00:00", "2d3h30m", "UTC")
    print(f"   Result: {result.strftime('%Y-%m-%d %H:%M:%S')}")

    print("\n4. Testing timezone listing...")
    america_zones = list_timezones("America")
    print(f"   Found {len(america_zones)} America/* timezones")

    print("\nAll tests passed!")


if __name__ == "__main__":
    _test_time_utils()
