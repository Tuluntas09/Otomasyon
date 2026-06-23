"""Typed exception hierarchy for Otomasyon domain errors."""


class OtomasyonError(Exception):
    """Root exception for all Otomasyon errors."""


class ValidationError(OtomasyonError):
    """A domain value failed a validation rule."""


class InvalidTickerError(ValidationError):
    """Ticker symbol does not match the required format."""


class CurrencyError(ValidationError):
    """Currency is not USD (the only supported currency in v0.1)."""


class NegativeQuantityError(ValidationError):
    """Quantity is zero or negative; short positions are not supported."""


class InvalidCostBasisError(ValidationError):
    """Cost basis is negative."""


class NegativePriceError(ValidationError):
    """Close price is zero or negative."""


class InvalidDateError(ValidationError):
    """Date string is not a valid ISO 8601 date (YYYY-MM-DD)."""


class DuplicateTickerError(OtomasyonError):
    """A ticker that already exists was inserted again."""


class MissingColumnError(ValidationError):
    """A required CSV column is absent from the header row."""


class CsvImportError(OtomasyonError):
    """One or more rows in an all-or-nothing CSV import failed validation.

    Attributes:
        errors: list of RowImportError describing each failed row.
    """

    def __init__(self, errors: list) -> None:
        self.errors = errors
        n = len(errors)
        super().__init__(f"{n} row{'s' if n != 1 else ''} failed validation during CSV import.")
