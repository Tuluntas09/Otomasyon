"""Pure data quality analytics — per-ticker price history depth and portfolio coverage.

All functions are stateless, deterministic, and free of I/O.
No import from data persistence or adapter layers.
report_date is always caller-provided — the system clock is never used (D-031, D-056).
"""

from dataclasses import dataclass
from datetime import date as _date

from app.core.models import Holding, PriceRecord
from app.core.validation import validate_iso_date


@dataclass(frozen=True)
class TickerQuality:
    """Price history depth metrics for one held ticker.

    days_since_last_price: calendar days between the most recent price record
    on or before report_date and report_date itself.  None when no such record
    exists (ticker unpriced relative to the report date).
    """

    ticker: str
    price_record_count: int
    earliest_price_date: str | None
    latest_price_date: str | None
    days_since_last_price: int | None
    has_price_on_or_before_report_date: bool


@dataclass(frozen=True)
class DataQualitySummary:
    """Portfolio-level and per-ticker price history depth summary.

    coverage_ratio: priced_holding_count / total_holding_count.
    0.0 when there are no holdings.
    """

    report_date: str
    total_holding_count: int
    priced_holding_count: int
    unpriced_holding_count: int
    coverage_ratio: float
    unpriced_tickers: list[str]
    ticker_quality: list[TickerQuality]


def compute_data_quality(
    holdings: list[Holding],
    price_records: list[PriceRecord],
    report_date: str,
) -> DataQualitySummary:
    """Compute per-ticker price history depth and portfolio-level coverage.

    Pure function: no I/O, no system clock, no side effects.
    report_date is caller-provided (D-031 / D-056 policy).

    Per-ticker metrics:
    - price_record_count: all PriceRecords for this ticker regardless of date.
    - earliest_price_date / latest_price_date: across all records for the ticker.
    - has_price_on_or_before_report_date: True iff at least one price_date
      <= report_date exists for this ticker.
    - days_since_last_price: (report_date - latest_date_on_or_before).days;
      None when has_price_on_or_before_report_date is False.

    Portfolio-level:
    - priced_holding_count: holdings where has_price_on_or_before_report_date is True.
    - coverage_ratio: priced / total (0.0 if no holdings).
    """
    validate_iso_date(report_date)
    report_date_obj = _date.fromisoformat(report_date)

    prices_by_ticker: dict[str, list[str]] = {}
    for pr in price_records:
        if pr.ticker not in prices_by_ticker:
            prices_by_ticker[pr.ticker] = []
        prices_by_ticker[pr.ticker].append(pr.price_date)

    ticker_quality_list: list[TickerQuality] = []
    priced_count = 0
    unpriced_tickers: list[str] = []

    for holding in holdings:
        dates = prices_by_ticker.get(holding.ticker, [])

        if not dates:
            ticker_quality_list.append(TickerQuality(
                ticker=holding.ticker,
                price_record_count=0,
                earliest_price_date=None,
                latest_price_date=None,
                days_since_last_price=None,
                has_price_on_or_before_report_date=False,
            ))
            unpriced_tickers.append(holding.ticker)
            continue

        sorted_dates = sorted(dates)
        earliest = sorted_dates[0]
        latest_all = sorted_dates[-1]

        dates_on_or_before = [d for d in sorted_dates if d <= report_date]

        if dates_on_or_before:
            latest_on_or_before = dates_on_or_before[-1]
            days_since = (report_date_obj - _date.fromisoformat(latest_on_or_before)).days
            has_price = True
            priced_count += 1
        else:
            latest_on_or_before = None
            days_since = None
            has_price = False
            unpriced_tickers.append(holding.ticker)

        ticker_quality_list.append(TickerQuality(
            ticker=holding.ticker,
            price_record_count=len(dates),
            earliest_price_date=earliest,
            latest_price_date=latest_all,
            days_since_last_price=days_since,
            has_price_on_or_before_report_date=has_price,
        ))

    total = len(holdings)
    coverage_ratio = priced_count / total if total > 0 else 0.0

    return DataQualitySummary(
        report_date=report_date,
        total_holding_count=total,
        priced_holding_count=priced_count,
        unpriced_holding_count=total - priced_count,
        coverage_ratio=coverage_ratio,
        unpriced_tickers=unpriced_tickers,
        ticker_quality=ticker_quality_list,
    )
