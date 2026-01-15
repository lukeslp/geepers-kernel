"""
Tests for input validators.

Tests Pydantic validators and utility validation functions.
"""

import pytest
from datetime import date
from pydantic import ValidationError
from monarchmoney.validators import (
    DateRangeValidator,
    TransactionFilterValidator,
    AmountValidator,
    AccountIDValidator,
    validate_date_string,
    validate_limit,
)


class TestDateRangeValidator:
    """Test date range validation."""

    def test_valid_date_range(self):
        """Test valid date range."""
        validator = DateRangeValidator(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31)
        )
        assert validator.start_date == date(2026, 1, 1)
        assert validator.end_date == date(2026, 1, 31)

    def test_invalid_date_range(self):
        """Test that end_date before start_date raises error."""
        with pytest.raises(ValidationError) as exc_info:
            DateRangeValidator(
                start_date=date(2026, 1, 31),
                end_date=date(2026, 1, 1)
            )
        assert 'end_date must be after start_date' in str(exc_info.value)


class TestTransactionFilterValidator:
    """Test transaction filter validation."""

    def test_default_values(self):
        """Test default values are applied."""
        validator = TransactionFilterValidator()
        assert validator.limit == 100
        assert validator.offset == 0
        assert validator.start_date is None
        assert validator.end_date is None

    def test_custom_limit(self):
        """Test custom limit within range."""
        validator = TransactionFilterValidator(limit=500)
        assert validator.limit == 500

    def test_limit_too_high(self):
        """Test limit exceeding maximum."""
        with pytest.raises(ValidationError):
            TransactionFilterValidator(limit=2000)

    def test_limit_too_low(self):
        """Test limit below minimum."""
        with pytest.raises(ValidationError):
            TransactionFilterValidator(limit=0)

    def test_negative_offset(self):
        """Test negative offset raises error."""
        with pytest.raises(ValidationError):
            TransactionFilterValidator(offset=-10)

    def test_search_too_long(self):
        """Test search string exceeding max length."""
        with pytest.raises(ValidationError):
            TransactionFilterValidator(search='x' * 501)


class TestAmountValidator:
    """Test amount validation."""

    def test_valid_amount(self):
        """Test valid monetary amount."""
        validator = AmountValidator(amount=123.45)
        assert validator.amount == 123.45

    def test_zero_amount(self):
        """Test zero is valid."""
        validator = AmountValidator(amount=0.0)
        assert validator.amount == 0.0

    def test_negative_amount(self):
        """Test negative amount raises error."""
        with pytest.raises(ValidationError):
            AmountValidator(amount=-10.0)

    def test_too_many_decimals(self):
        """Test amount with >2 decimal places raises error."""
        with pytest.raises(ValidationError) as exc_info:
            AmountValidator(amount=123.456)
        assert 'at most 2 decimal places' in str(exc_info.value)


class TestAccountIDValidator:
    """Test account ID validation."""

    def test_valid_account_id(self):
        """Test valid account ID."""
        validator = AccountIDValidator(account_id="acc_123456")
        assert validator.account_id == "acc_123456"

    def test_whitespace_trimmed(self):
        """Test whitespace is trimmed."""
        validator = AccountIDValidator(account_id="  acc_123  ")
        assert validator.account_id == "acc_123"

    def test_empty_account_id(self):
        """Test empty account ID raises error."""
        with pytest.raises(ValidationError):
            AccountIDValidator(account_id="")

    def test_whitespace_only(self):
        """Test whitespace-only ID raises error."""
        with pytest.raises(ValidationError) as exc_info:
            AccountIDValidator(account_id="   ")
        assert 'cannot be empty' in str(exc_info.value)


class TestValidateDateString:
    """Test date string validation utility."""

    def test_valid_date_string(self):
        """Test valid YYYY-MM-DD format."""
        result = validate_date_string("2026-01-05")
        assert result == date(2026, 1, 5)

    def test_invalid_format(self):
        """Test invalid date format raises error."""
        with pytest.raises(ValueError) as exc_info:
            validate_date_string("01/05/2026")
        assert 'Invalid date format' in str(exc_info.value)
        assert 'Expected YYYY-MM-DD' in str(exc_info.value)

    def test_invalid_date_values(self):
        """Test invalid date values raise error."""
        with pytest.raises(ValueError):
            validate_date_string("2026-13-01")  # Invalid month


class TestValidateLimit:
    """Test limit validation utility."""

    def test_valid_limit(self):
        """Test valid limit."""
        result = validate_limit(50)
        assert result == 50

    def test_limit_at_max(self):
        """Test limit at maximum."""
        result = validate_limit(1000, max_limit=1000)
        assert result == 1000

    def test_limit_exceeds_max(self):
        """Test limit exceeding maximum."""
        with pytest.raises(ValueError) as exc_info:
            validate_limit(2000, max_limit=1000)
        assert 'cannot exceed 1000' in str(exc_info.value)

    def test_limit_below_min(self):
        """Test limit below minimum."""
        with pytest.raises(ValueError) as exc_info:
            validate_limit(0)
        assert 'must be at least 1' in str(exc_info.value)

    def test_custom_max_limit(self):
        """Test custom max limit."""
        result = validate_limit(250, max_limit=500)
        assert result == 250
