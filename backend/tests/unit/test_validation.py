"""Unit tests for app.core.validation — one test per rule, in isolation."""

import pytest

from app.core.exceptions import (
    CurrencyError,
    InvalidCostBasisError,
    InvalidDateError,
    InvalidTickerError,
    NegativePriceError,
    NegativeQuantityError,
)
from app.core.validation import (
    validate_currency_usd,
    validate_iso_date,
    validate_non_negative_cost_basis,
    validate_positive_close_price,
    validate_positive_quantity,
    validate_ticker,
)


class TestValidateTicker:
    def test_valid_simple(self):
        assert validate_ticker("AAPL") == "AAPL"

    def test_valid_with_dot(self):
        assert validate_ticker("BRK.B") == "BRK.B"

    def test_valid_with_hyphen(self):
        assert validate_ticker("BF-B") == "BF-B"

    def test_valid_single_char(self):
        assert validate_ticker("A") == "A"

    def test_valid_mixed_digits(self):
        assert validate_ticker("TSM3") == "TSM3"

    def test_invalid_lowercase(self):
        with pytest.raises(InvalidTickerError):
            validate_ticker("aapl")

    def test_invalid_empty(self):
        with pytest.raises(InvalidTickerError):
            validate_ticker("")

    def test_invalid_starts_with_digit(self):
        with pytest.raises(InvalidTickerError):
            validate_ticker("1AAPL")

    def test_invalid_too_long(self):
        with pytest.raises(InvalidTickerError):
            validate_ticker("ABCDEFGHIJK")  # 11 chars

    def test_invalid_space(self):
        with pytest.raises(InvalidTickerError):
            validate_ticker("AA PL")

    def test_invalid_type(self):
        with pytest.raises(InvalidTickerError):
            validate_ticker(123)  # type: ignore[arg-type]


class TestValidateCurrencyUsd:
    def test_usd_passes(self):
        assert validate_currency_usd("USD") == "USD"

    def test_eur_raises(self):
        with pytest.raises(CurrencyError):
            validate_currency_usd("EUR")

    def test_gbp_raises(self):
        with pytest.raises(CurrencyError):
            validate_currency_usd("GBP")

    def test_empty_raises(self):
        with pytest.raises(CurrencyError):
            validate_currency_usd("")

    def test_lowercase_raises(self):
        with pytest.raises(CurrencyError):
            validate_currency_usd("usd")


class TestValidatePositiveQuantity:
    def test_positive_passes(self):
        assert validate_positive_quantity(1.0) == 1.0

    def test_fractional_passes(self):
        assert validate_positive_quantity(0.001) == 0.001

    def test_zero_raises(self):
        with pytest.raises(NegativeQuantityError):
            validate_positive_quantity(0.0)

    def test_negative_raises(self):
        with pytest.raises(NegativeQuantityError):
            validate_positive_quantity(-5.0)

    def test_large_value_passes(self):
        assert validate_positive_quantity(1_000_000.0) == 1_000_000.0


class TestValidateNonNegativeCostBasis:
    def test_zero_passes(self):
        assert validate_non_negative_cost_basis(0.0) == 0.0

    def test_positive_passes(self):
        assert validate_non_negative_cost_basis(150.0) == 150.0

    def test_negative_raises(self):
        with pytest.raises(InvalidCostBasisError):
            validate_non_negative_cost_basis(-0.01)


class TestValidatePositiveClosePrice:
    def test_positive_passes(self):
        assert validate_positive_close_price(100.0) == 100.0

    def test_zero_raises(self):
        with pytest.raises(NegativePriceError):
            validate_positive_close_price(0.0)

    def test_negative_raises(self):
        with pytest.raises(NegativePriceError):
            validate_positive_close_price(-1.0)


class TestValidateIsoDate:
    def test_valid_date(self):
        assert validate_iso_date("2024-01-15") == "2024-01-15"

    def test_leap_day(self):
        assert validate_iso_date("2024-02-29") == "2024-02-29"

    def test_invalid_format(self):
        with pytest.raises(InvalidDateError):
            validate_iso_date("15-01-2024")

    def test_invalid_month(self):
        with pytest.raises(InvalidDateError):
            validate_iso_date("2024-13-01")

    def test_invalid_day(self):
        with pytest.raises(InvalidDateError):
            validate_iso_date("2024-01-32")

    def test_not_a_leap_day(self):
        with pytest.raises(InvalidDateError):
            validate_iso_date("2023-02-29")

    def test_empty_string(self):
        with pytest.raises(InvalidDateError):
            validate_iso_date("")

    def test_none_raises(self):
        with pytest.raises(InvalidDateError):
            validate_iso_date(None)  # type: ignore[arg-type]
