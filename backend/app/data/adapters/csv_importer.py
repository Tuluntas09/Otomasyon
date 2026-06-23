"""CSV import orchestration for holdings, watchlist, and prices.

All three functions accept a TextIO (file-like text stream). Callers are
responsible for opening files with UTF-8 encoding and passing the handle here.

Transaction semantics (D-025):
- Holdings and watchlist: all-or-nothing. Pass 1 validates every row and
  pre-checks DB duplicates before any write. Pass 2 writes only if Pass 1
  produced zero errors.
- Prices: row-level error collection. Valid rows are upserted; invalid rows
  are captured in ImportResult.errors. The function never raises CsvImportError.

CSV format (D-029): comma delimiter only. No csv.Sniffer.
Parser (D-024): stdlib csv.DictReader only. No third-party dependencies.
Extra columns (D-028): silently ignored.
"""

import csv
import sqlite3
from dataclasses import dataclass, field
from typing import TextIO

from app.core.exceptions import (
    CsvImportError,
    DuplicateTickerError,
    MissingColumnError,
    ValidationError,
)
from app.core.models import Holding, PriceRecord, WatchlistEntry
from app.data.persistence.holdings_repo import HoldingsRepo
from app.data.persistence.prices_repo import PricesRepo
from app.data.persistence.watchlist_repo import WatchlistRepo

_HOLDINGS_REQUIRED: frozenset[str] = frozenset({"ticker", "quantity", "cost_basis", "currency"})
_WATCHLIST_REQUIRED: frozenset[str] = frozenset({"ticker"})
_PRICES_REQUIRED: frozenset[str] = frozenset({"ticker", "date", "close", "currency"})


@dataclass
class RowImportError:
    """A single row that failed validation or import."""

    row_number: int
    raw_row: dict[str, str]
    error: Exception


@dataclass
class ImportResult:
    """Outcome of a CSV import operation."""

    imported_count: int
    errors: list[RowImportError] = field(default_factory=list)


def _check_headers(fieldnames, required: frozenset[str], import_type: str) -> None:
    if fieldnames is None:
        raise MissingColumnError(
            f"{import_type} CSV has no header row. "
            f"Required columns: {sorted(required)}."
        )
    missing = required - set(fieldnames)
    if missing:
        raise MissingColumnError(
            f"{import_type} CSV is missing required column(s): {sorted(missing)}. "
            f"Required: {sorted(required)}."
        )


def _parse_float(raw_row: dict[str, str], column: str) -> float:
    raw = (raw_row.get(column) or "").strip()
    try:
        return float(raw)
    except ValueError:
        raise ValidationError(
            f"Column '{column}' value {raw!r} is not a valid decimal number."
        )


def import_holdings_csv(file_obj: TextIO, conn: sqlite3.Connection) -> ImportResult:
    """Import holdings from a UTF-8 CSV stream. All-or-nothing (D-025).

    Pass 1: validate every row and pre-check DB duplicates. No writes occur.
    Pass 2: insert all holdings only when Pass 1 reports zero errors.
    Raises CsvImportError if any row fails.
    """
    reader = csv.DictReader(file_obj)
    _check_headers(reader.fieldnames, _HOLDINGS_REQUIRED, "holdings")

    errors: list[RowImportError] = []
    holdings: list[Holding] = []
    seen_tickers: set[str] = set()
    existing_tickers: set[str] = {h.ticker for h in HoldingsRepo(conn).get_all()}

    for row_number, raw_row in enumerate(reader, start=2):
        raw_row = dict(raw_row)
        ticker_raw = (raw_row.get("ticker") or "").strip()
        try:
            if ticker_raw in seen_tickers:
                raise DuplicateTickerError(
                    f"Ticker {ticker_raw!r} appears more than once in this CSV."
                )
            if ticker_raw in existing_tickers:
                raise DuplicateTickerError(
                    f"Ticker {ticker_raw!r} already exists in the database."
                )
            quantity = _parse_float(raw_row, "quantity")
            cost_basis = _parse_float(raw_row, "cost_basis")
            currency = (raw_row.get("currency") or "").strip()
            holding = Holding(
                ticker=ticker_raw,
                quantity=quantity,
                cost_basis=cost_basis,
                currency=currency,
            )
            seen_tickers.add(holding.ticker)
            holdings.append(holding)
        except Exception as exc:
            errors.append(RowImportError(row_number=row_number, raw_row=raw_row, error=exc))
            if ticker_raw:
                seen_tickers.add(ticker_raw)

    if errors:
        raise CsvImportError(errors=errors)

    repo = HoldingsRepo(conn)
    for holding in holdings:
        repo.insert(holding)

    return ImportResult(imported_count=len(holdings))


def import_watchlist_csv(file_obj: TextIO, conn: sqlite3.Connection) -> ImportResult:
    """Import watchlist entries from a UTF-8 CSV stream. All-or-nothing (D-025).

    Pass 1: validate every row and pre-check DB duplicates.
    Pass 2: insert only when Pass 1 is error-free.
    Raises CsvImportError if any row fails.
    """
    reader = csv.DictReader(file_obj)
    _check_headers(reader.fieldnames, _WATCHLIST_REQUIRED, "watchlist")

    errors: list[RowImportError] = []
    entries: list[WatchlistEntry] = []
    seen_tickers: set[str] = set()
    existing_tickers: set[str] = {e.ticker for e in WatchlistRepo(conn).get_all()}

    for row_number, raw_row in enumerate(reader, start=2):
        raw_row = dict(raw_row)
        ticker_raw = (raw_row.get("ticker") or "").strip()
        try:
            if ticker_raw in seen_tickers:
                raise DuplicateTickerError(
                    f"Ticker {ticker_raw!r} appears more than once in this CSV."
                )
            if ticker_raw in existing_tickers:
                raise DuplicateTickerError(
                    f"Ticker {ticker_raw!r} already exists in the database."
                )
            entry = WatchlistEntry(ticker=ticker_raw)
            seen_tickers.add(entry.ticker)
            entries.append(entry)
        except Exception as exc:
            errors.append(RowImportError(row_number=row_number, raw_row=raw_row, error=exc))
            if ticker_raw:
                seen_tickers.add(ticker_raw)

    if errors:
        raise CsvImportError(errors=errors)

    repo = WatchlistRepo(conn)
    for entry in entries:
        repo.add(entry)

    return ImportResult(imported_count=len(entries))


def import_prices_csv(file_obj: TextIO, conn: sqlite3.Connection) -> ImportResult:
    """Import end-of-day prices from a UTF-8 CSV stream. Row-level error collection (D-025).

    Valid rows are upserted; invalid rows are collected in ImportResult.errors.
    Never raises CsvImportError — always returns an ImportResult.
    Raises MissingColumnError if the header is absent or missing required columns.
    """
    reader = csv.DictReader(file_obj)
    _check_headers(reader.fieldnames, _PRICES_REQUIRED, "prices")

    imported_count = 0
    errors: list[RowImportError] = []
    repo = PricesRepo(conn)

    for row_number, raw_row in enumerate(reader, start=2):
        raw_row = dict(raw_row)
        try:
            ticker = (raw_row.get("ticker") or "").strip()
            price_date = (raw_row.get("date") or "").strip()
            close_price = _parse_float(raw_row, "close")
            currency = (raw_row.get("currency") or "").strip()
            record = PriceRecord(
                ticker=ticker,
                price_date=price_date,
                close_price=close_price,
                currency=currency,
            )
            repo.upsert(record)
            imported_count += 1
        except Exception as exc:
            errors.append(RowImportError(row_number=row_number, raw_row=raw_row, error=exc))

    return ImportResult(imported_count=imported_count, errors=errors)
