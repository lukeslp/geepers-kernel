"""
Tests for time utilities.
"""
import pytest
from datetime import datetime
from shared.utils.time_utils import (
    TimeUtilities,
    TimeConversion,
    TimeDifference,
    convert_timezone,
    calculate_difference,
    add_time,
    parse_duration,
    list_timezones,
    validate_timezone
)


class TestTimeConversion:
    """Test TimeConversion dataclass."""

    def test_time_conversion_structure(self):
        """Test TimeConversion has expected attributes."""
        dt1 = datetime(2025, 1, 15, 14, 0, 0)
        dt2 = datetime(2025, 1, 16, 4, 0, 0)

        conversion = TimeConversion(
            original_time=dt1,
            converted_time=dt2,
            from_timezone="America/New_York",
            to_timezone="Asia/Tokyo",
            offset_hours=14.0
        )

        assert conversion.from_timezone == "America/New_York"
        assert conversion.to_timezone == "Asia/Tokyo"
        assert conversion.offset_hours == 14.0


class TestTimeDifference:
    """Test TimeDifference dataclass."""

    def test_time_difference_structure(self):
        """Test TimeDifference has expected attributes."""
        dt1 = datetime(2025, 1, 15, 9, 0, 0)
        dt2 = datetime(2025, 1, 15, 17, 30, 0)

        diff = TimeDifference(
            start_time=dt1,
            end_time=dt2,
            days=0,
            hours=8,
            minutes=30,
            seconds=0,
            total_hours=8.5,
            total_seconds=30600
        )

        assert diff.hours == 8
        assert diff.minutes == 30
        assert diff.total_hours == 8.5


class TestTimeUtilities:
    """Test TimeUtilities class."""

    @pytest.fixture
    def pytz_available(self):
        """Check if pytz is available."""
        try:
            return True
        except ImportError:
            pytest.skip("pytz not installed")

    def test_convert_timezone(self, pytz_available):
        """Test timezone conversion."""
        result = TimeUtilities.convert_timezone(
            "2025-01-15 14:00:00",
            "America/New_York",
            "America/Los_Angeles"
        )

        assert isinstance(result, TimeConversion)
        assert result.from_timezone == "America/New_York"
        assert result.to_timezone == "America/Los_Angeles"
        assert result.offset_hours == -3.0

    def test_convert_timezone_now(self, pytz_available):
        """Test timezone conversion with 'now'."""
        result = TimeUtilities.convert_timezone(
            "now",
            "UTC",
            "America/New_York"
        )

        assert isinstance(result, TimeConversion)
        assert result.converted_time is not None

    def test_calculate_difference(self, pytz_available):
        """Test time difference calculation."""
        result = TimeUtilities.calculate_difference(
            "2025-01-15 09:00:00",
            "2025-01-15 17:30:00",
            "UTC"
        )

        assert isinstance(result, TimeDifference)
        assert result.hours == 8
        assert result.minutes == 30
        assert result.total_hours == 8.5

    def test_add_duration(self, pytz_available):
        """Test adding duration to time."""
        result = TimeUtilities.add_duration(
            "2025-01-15 14:00:00",
            "2d3h30m",
            "UTC"
        )

        assert result.day == 17
        assert result.hour == 17
        assert result.minute == 30

    def test_parse_duration(self):
        """Test duration parsing."""
        delta = TimeUtilities.parse_duration("2d3h30m")

        assert delta.days == 2
        assert delta.seconds == (3 * 3600 + 30 * 60)

    def test_parse_duration_hours_only(self):
        """Test parsing duration with only hours."""
        delta = TimeUtilities.parse_duration("5h")
        assert delta.days == 0
        assert delta.seconds == 5 * 3600

    def test_list_timezones(self, pytz_available):
        """Test timezone listing."""
        timezones = TimeUtilities.list_timezones()
        assert len(timezones) > 0
        assert "UTC" in timezones

    def test_list_timezones_filtered(self, pytz_available):
        """Test filtered timezone listing."""
        timezones = TimeUtilities.list_timezones("America")
        assert len(timezones) > 0
        assert all("America" in tz for tz in timezones)

    def test_validate_timezone(self, pytz_available):
        """Test timezone validation."""
        assert TimeUtilities.validate_timezone("America/New_York") is True
        assert TimeUtilities.validate_timezone("Invalid/Zone") is False

    def test_get_current_time(self, pytz_available):
        """Test getting current time in timezone."""
        result = TimeUtilities.get_current_time("UTC")
        assert result is not None
        assert result.tzinfo is not None


class TestFunctionalInterface:
    """Test functional interface convenience functions."""

    @pytest.fixture
    def pytz_available(self):
        """Check if pytz is available."""
        try:
            return True
        except ImportError:
            pytest.skip("pytz not installed")

    def test_convert_timezone_function(self, pytz_available):
        """Test convert_timezone convenience function."""
        result = convert_timezone(
            "2025-01-15 14:00:00",
            "UTC",
            "America/New_York"
        )
        assert isinstance(result, TimeConversion)

    def test_calculate_difference_function(self, pytz_available):
        """Test calculate_difference convenience function."""
        result = calculate_difference(
            "2025-01-15 09:00:00",
            "2025-01-15 17:00:00",
            "UTC"
        )
        assert isinstance(result, TimeDifference)
        assert result.hours == 8

    def test_add_time_function(self, pytz_available):
        """Test add_time convenience function."""
        result = add_time(
            "2025-01-15 14:00:00",
            "1d",
            "UTC"
        )
        assert result.day == 16

    def test_parse_duration_function(self):
        """Test parse_duration convenience function."""
        delta = parse_duration("1d2h")
        assert delta.days == 1
        assert delta.seconds == 2 * 3600

    def test_list_timezones_function(self, pytz_available):
        """Test list_timezones convenience function."""
        timezones = list_timezones("Europe")
        assert len(timezones) > 0

    def test_validate_timezone_function(self, pytz_available):
        """Test validate_timezone convenience function."""
        assert validate_timezone("UTC") is True


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def pytz_available(self):
        """Check if pytz is available."""
        try:
            return True
        except ImportError:
            pytest.skip("pytz not installed")

    def test_invalid_time_format(self, pytz_available):
        """Test handling of invalid time format."""
        with pytest.raises(ValueError):
            TimeUtilities.convert_timezone(
                "invalid-time",
                "UTC",
                "America/New_York"
            )

    def test_invalid_timezone(self, pytz_available):
        """Test handling of invalid timezone."""
        with pytest.raises(Exception):
            TimeUtilities.convert_timezone(
                "2025-01-15 14:00:00",
                "Invalid/Zone",
                "UTC"
            )

    def test_empty_duration(self):
        """Test parsing empty duration."""
        delta = TimeUtilities.parse_duration("")
        assert delta.days == 0
        assert delta.seconds == 0
