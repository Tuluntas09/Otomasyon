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
    """Price history depth and local continuity metrics for one held ticker.

    days_since_last_price: calendar days between the most recent price record
    on or before report_date and report_date itself.  None when no such record
    exists (ticker unpriced relative to the report date).

    local_price_date_count_on_or_before_report_date: count of unique local price
    dates on or before report_date.  Duplicates are collapsed.

    largest_price_date_gap_days: calendar days of the largest consecutive gap
    between local price dates on or before report_date.  None when fewer than
    two unique local price dates exist on or before report_date.

    largest_price_date_gap_start / largest_price_date_gap_end: ISO-8601 date
    strings bounding the largest gap.  None when largest_price_date_gap_days is None.

    Tie behavior: when multiple consecutive gaps share the same length, the
    earliest (first-encountered in ascending date order) gap is reported.
    """

    ticker: str
    price_record_count: int
    earliest_price_date: str | None
    latest_price_date: str | None
    days_since_last_price: int | None
    has_price_on_or_before_report_date: bool
    local_price_date_count_on_or_before_report_date: int
    largest_price_date_gap_days: int | None
    largest_price_date_gap_start: str | None
    largest_price_date_gap_end: str | None


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


def _compute_largest_gap(
    sorted_unique_dates: list[str],
) -> tuple[int | None, str | None, str | None]:
    """Return (gap_days, gap_start, gap_end) for the largest consecutive local price-date gap.

    sorted_unique_dates must be sorted ascending and contain unique values.
    Tie behavior: when multiple gaps share the same length, the earliest is returned
    (strict greater-than comparison so the first maximum found is kept).
    Returns (None, None, None) when fewer than two dates are provided.
    """
    if len(sorted_unique_dates) < 2:
        return None, None, None

    max_gap_days: int | None = None
    max_gap_start: str | None = None
    max_gap_end: str | None = None

    for i in range(len(sorted_unique_dates) - 1):
        start = sorted_unique_dates[i]
        end = sorted_unique_dates[i + 1]
        gap_days = (_date.fromisoformat(end) - _date.fromisoformat(start)).days
        if max_gap_days is None or gap_days > max_gap_days:
            max_gap_days = gap_days
            max_gap_start = start
            max_gap_end = end

    return max_gap_days, max_gap_start, max_gap_end


def compute_data_quality(
    holdings: list[Holding],
    price_records: list[PriceRecord],
    report_date: str,
) -> DataQualitySummary:
    """Compute per-ticker price history depth, local continuity, and portfolio-level coverage.

    Pure function: no I/O, no system clock, no side effects.
    report_date is caller-provided (D-031 / D-056 policy).

    Per-ticker metrics:
    - price_record_count: all PriceRecords for this ticker regardless of date.
    - earliest_price_date / latest_price_date: across all records for the ticker.
    - has_price_on_or_before_report_date: True iff at least one price_date
      <= report_date exists for this ticker.
    - days_since_last_price: (report_date - latest_date_on_or_before).days;
      None when has_price_on_or_before_report_date is False.
    - local_price_date_count_on_or_before_report_date: count of unique price dates
      on or before report_date.  Duplicate dates are collapsed before counting.
    - largest_price_date_gap_days / largest_price_date_gap_start /
      largest_price_date_gap_end: largest calendar-day gap between consecutive
      unique local price dates on or before report_date.  All three are None when
      fewer than two unique local price dates exist on or before report_date.
      Tie behavior: earliest gap wins.

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
                local_price_date_count_on_or_before_report_date=0,
                largest_price_date_gap_days=None,
                largest_price_date_gap_start=None,
                largest_price_date_gap_end=None,
            ))
            unpriced_tickers.append(holding.ticker)
            continue

        sorted_dates = sorted(dates)
        earliest = sorted_dates[0]
        latest_all = sorted_dates[-1]

        # Unique dates on or before report_date: used for gap computation and local count.
        # Duplicates are collapsed so they do not create false zero-day gaps.
        unique_dates_on_or_before = sorted(set(d for d in dates if d <= report_date))
        local_count = len(unique_dates_on_or_before)
        gap_days, gap_start, gap_end = _compute_largest_gap(unique_dates_on_or_before)

        if unique_dates_on_or_before:
            latest_on_or_before = unique_dates_on_or_before[-1]
            days_since = (report_date_obj - _date.fromisoformat(latest_on_or_before)).days
            has_price = True
            priced_count += 1
        else:
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
            local_price_date_count_on_or_before_report_date=local_count,
            largest_price_date_gap_days=gap_days,
            largest_price_date_gap_start=gap_start,
            largest_price_date_gap_end=gap_end,
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
