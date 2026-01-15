"""
Input validation for Monarch Money API calls using Pydantic.

Provides type-safe validation for common parameters like dates, amounts, and IDs.
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class DateRangeValidator(BaseModel):
    """Validates date range parameters."""

    start_date: date
    end_date: date

    @field_validator('end_date')
    @classmethod
    def end_after_start(cls, v: date, info) -> date:
        """Ensure end_date is after start_date."""
        if 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError('end_date must be after start_date')
        return v


class TransactionFilterValidator(BaseModel):
    """Validates transaction filter parameters."""

    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    search: Optional[str] = Field(default=None, max_length=500)

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v: Optional[date], info) -> Optional[date]:
        """Ensure end_date is after start_date if both provided."""
        if v and 'start_date' in info.data and info.data['start_date']:
            if v < info.data['start_date']:
                raise ValueError('end_date must be after start_date')
        return v


class AmountValidator(BaseModel):
    """Validates monetary amounts."""

    amount: float = Field(ge=0)

    @field_validator('amount')
    @classmethod
    def validate_precision(cls, v: float) -> float:
        """Ensure amount has at most 2 decimal places."""
        if round(v, 2) != v:
            raise ValueError('amount can have at most 2 decimal places')
        return v


class AccountIDValidator(BaseModel):
    """Validates account IDs."""

    account_id: str = Field(min_length=1, max_length=100)

    @field_validator('account_id')
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Ensure account_id is not empty or just whitespace."""
        if not v.strip():
            raise ValueError('account_id cannot be empty')
        return v.strip()


def validate_date_string(date_str: str) -> date:
    """
    Validate and parse a date string in YYYY-MM-DD format.

    Args:
        date_str: Date string to validate

    Returns:
        Parsed date object

    Raises:
        ValueError: If date string is invalid
    """
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError as e:
        raise ValueError(f"Invalid date format '{date_str}'. Expected YYYY-MM-DD") from e


def validate_limit(limit: int, max_limit: int = 1000) -> int:
    """
    Validate a limit parameter.

    Args:
        limit: Limit value to validate
        max_limit: Maximum allowed limit

    Returns:
        Validated limit

    Raises:
        ValueError: If limit is out of range
    """
    if limit < 1:
        raise ValueError(f"limit must be at least 1, got {limit}")
    if limit > max_limit:
        raise ValueError(f"limit cannot exceed {max_limit}, got {limit}")
    return limit
