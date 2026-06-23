"""Architecture invariant: no broker integration, no execution logic, no advisory language.

Scans backend/app/ and frontend/src/ (when present) for patterns that would indicate:
- Broker API library imports
- Order execution or paper-trading function/class definitions
- Advisory signal function or variable names

Policy documents (docs/, README.md, PROJECT_BRAIN.md) and the test suite itself are
deliberately excluded. Policy files must mention prohibited words in order to forbid them;
scanning them would produce false positives.
"""

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_APP_DIR = _REPO_ROOT / "backend" / "app"
_FRONTEND_SRC = _REPO_ROOT / "frontend" / "src"

# Broker API library import statements
_BROKER_IMPORT_RE = re.compile(
    r"^\s*(import|from)\s+"
    r"(alpaca|alpaca_trade_api|ib_insync|ibkr|ccxt|robinhood|"
    r"td_ameritrade|tda|tastytrade|tradier|schwab|coinbase|binance|"
    r"kraken|ftx|etrade|fidelity_api|broker)",
    re.MULTILINE | re.IGNORECASE,
)

# Execution and paper-trading function or class definitions
_EXECUTION_DEF_RE = re.compile(
    r"\b(def|class)\s+"
    r"(place_order|execute_order|submit_order|cancel_order|modify_order|"
    r"buy_stock|sell_stock|buy_shares|sell_shares|"
    r"paper_trade|run_paper_trade|simulate_trade|"
    r"run_backtest|execute_backtest|backtest_strategy|"
    r"TradeExecutor|OrderManager|BrokerClient|PaperTrader|Backtester)\b"
)

# Advisory signal function names and variable assignments
_ADVISORY_RE = re.compile(
    r"\bdef\s+(get_buy_signal|get_sell_signal|get_hold_recommendation|"
    r"generate_trade_signal|get_trade_recommendation|"
    r"compute_signal|emit_signal|send_trade_signal)\b"
    r"|"
    r"\b(buy_signal|sell_signal|hold_signal|hold_recommendation|"
    r"trade_recommendation|trade_signal)\s*="
)


def _source_files() -> list[Path]:
    files: list[Path] = []
    if _APP_DIR.exists():
        files.extend(_APP_DIR.rglob("*.py"))
    if _FRONTEND_SRC.exists():
        files.extend(_FRONTEND_SRC.rglob("*.ts"))
        files.extend(_FRONTEND_SRC.rglob("*.tsx"))
    return files


def test_no_broker_integration() -> None:
    """No broker API library is imported anywhere in application source code."""
    violations: list[str] = []
    for path in _source_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        if _BROKER_IMPORT_RE.search(text):
            violations.append(str(path))
    assert not violations, (
        "Broker API imports detected in application source.\n"
        "Broker integration is off-roadmap per RISK_POLICY.md §3.\n"
        "Affected files:\n" + "\n".join(f"  {v}" for v in violations)
    )


def test_no_execution_logic() -> None:
    """No order execution, paper trading, or backtesting definitions in application source."""
    violations: list[str] = []
    for path in _source_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        if _EXECUTION_DEF_RE.search(text):
            violations.append(str(path))
    assert not violations, (
        "Execution or paper-trading logic detected in application source.\n"
        "Automation ceiling is read→compute→notify per RISK_POLICY.md §7.\n"
        "Affected files:\n" + "\n".join(f"  {v}" for v in violations)
    )


def test_no_advisory_language_in_source() -> None:
    """No advisory signal functions or variables in application source."""
    violations: list[str] = []
    for path in _source_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        if _ADVISORY_RE.search(text):
            violations.append(str(path))
    assert not violations, (
        "Advisory signal language detected in application source.\n"
        "The system describes facts; it never generates trade signals.\n"
        "See RISK_POLICY.md §3 and ALERT_POLICY.md.\n"
        "Affected files:\n" + "\n".join(f"  {v}" for v in violations)
    )


def test_quality_module_has_no_broker_imports() -> None:
    """Phase 8A metrics/quality.py does not import broker or execution libraries."""
    quality_path = _APP_DIR / "metrics" / "quality.py"
    if not quality_path.exists():
        return
    text = quality_path.read_text(encoding="utf-8", errors="replace")
    assert not _BROKER_IMPORT_RE.search(text), (
        "Broker API import detected in metrics/quality.py.\n"
        "Phase 8A is Tier 2 analytics only — no broker access."
    )


def test_quality_module_has_no_execution_definitions() -> None:
    """Phase 8A metrics/quality.py defines no execution or paper-trading functions."""
    quality_path = _APP_DIR / "metrics" / "quality.py"
    if not quality_path.exists():
        return
    text = quality_path.read_text(encoding="utf-8", errors="replace")
    assert not _EXECUTION_DEF_RE.search(text), (
        "Execution or paper-trading logic detected in metrics/quality.py.\n"
        "Phase 8A scope is data quality analytics only."
    )


def test_quality_module_has_no_advisory_language() -> None:
    """Phase 8A metrics/quality.py contains no advisory signal functions or variables."""
    quality_path = _APP_DIR / "metrics" / "quality.py"
    if not quality_path.exists():
        return
    text = quality_path.read_text(encoding="utf-8", errors="replace")
    assert not _ADVISORY_RE.search(text), (
        "Advisory signal language detected in metrics/quality.py.\n"
        "Phase 8A is descriptive analytics only — no trade signals."
    )


# ---------------------------------------------------------------------------
# Phase 8B — Broader forbidden-import scan across all of backend/app/
# ---------------------------------------------------------------------------

_SYSTEM_SHELL_RE = re.compile(
    r"\bos\.system\s*\(|subprocess\.|socket\.\w",
    re.MULTILINE,
)

_EXTERNAL_HTTP_RE = re.compile(
    r"^\s*(import|from)\s+(requests|httpx|aiohttp|urllib\.request)",
    re.MULTILINE | re.IGNORECASE,
)


def test_no_system_shell_or_socket_in_app() -> None:
    """No os.system(), subprocess calls, or raw socket usage in backend/app/."""
    violations: list[str] = []
    for path in _source_files():
        if not str(path).endswith(".py"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if _SYSTEM_SHELL_RE.search(text):
            violations.append(str(path))
    assert not violations, (
        "os.system(), subprocess, or socket usage detected in application source.\n"
        "These are forbidden in backend/app/ — analytics layers must not invoke"
        " system shells or open network sockets directly.\n"
        "Affected files:\n" + "\n".join(f"  {v}" for v in violations)
    )


def test_no_external_http_client_imports_in_app() -> None:
    """No requests, httpx, aiohttp, or urllib.request imports in backend/app/."""
    violations: list[str] = []
    for path in _source_files():
        if not str(path).endswith(".py"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if _EXTERNAL_HTTP_RE.search(text):
            violations.append(str(path))
    assert not violations, (
        "External HTTP client import detected in application source.\n"
        "The tool is local-first — no outbound HTTP from backend/app/.\n"
        "Affected files:\n" + "\n".join(f"  {v}" for v in violations)
    )


# ---------------------------------------------------------------------------
# Phase 8C — Adapter/repository boundary and route purity hardening
# ---------------------------------------------------------------------------

_ROUTES_DIR = _REPO_ROOT / "backend" / "app" / "api" / "routes"

_RAW_SQL_RE = re.compile(
    r"\b(SELECT|INSERT\s+INTO|UPDATE\s+\w|DELETE\s+FROM|CREATE\s+TABLE|DROP\s+TABLE)\b",
    re.IGNORECASE | re.MULTILINE,
)

_PERSISTENCE_IMPORT_RE = re.compile(
    r"^\s*(import|from)\s+app\.data\.persistence\.",
    re.MULTILINE,
)


def test_no_raw_sql_in_api_routes() -> None:
    """API route modules contain no raw SQL statements.

    All data access must flow through SQLiteDataAdapter, never through raw SQL
    strings executed directly in route handlers.
    """
    if not _ROUTES_DIR.exists():
        return
    violations: list[str] = []
    for path in _ROUTES_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if _RAW_SQL_RE.search(text):
            violations.append(str(path))
    assert not violations, (
        "Raw SQL detected in api/routes/.\n"
        "Route handlers must not contain raw SQL — all data access must go"
        " through SQLiteDataAdapter.\n"
        "Affected files:\n" + "\n".join(f"  {v}" for v in violations)
    )


def test_no_direct_repo_imports_in_api_routes() -> None:
    """API route modules do not import persistence repositories directly.

    Route handlers access data only through SQLiteDataAdapter, not through
    direct imports of HoldingsRepo, PricesRepo, JournalRepo, or similar.
    """
    if not _ROUTES_DIR.exists():
        return
    violations: list[str] = []
    for path in _ROUTES_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if _PERSISTENCE_IMPORT_RE.search(text):
            violations.append(str(path))
    assert not violations, (
        "Direct persistence repository import detected in api/routes/.\n"
        "Route handlers must access data only through SQLiteDataAdapter"
        " per the adapter boundary (D-066, D-072).\n"
        "Affected files:\n" + "\n".join(f"  {v}" for v in violations)
    )


def test_quality_module_has_no_layer_imports() -> None:
    """metrics/quality.py does not import from persistence, API, reports, alerts, or compliance.

    The quality module is a pure analytics function. It must not depend on any
    layer above or beside it in the architecture.
    """
    quality_path = _APP_DIR / "metrics" / "quality.py"
    if not quality_path.exists():
        return
    text = quality_path.read_text(encoding="utf-8", errors="replace")
    forbidden_patterns = [
        r"from app\.data\.persistence",
        r"from app\.api",
        r"from app\.reports",
        r"from app\.alerts",
        r"from app\.compliance",
    ]
    for pattern in forbidden_patterns:
        assert not re.search(pattern, text), (
            f"Forbidden import pattern {pattern!r} found in metrics/quality.py.\n"
            "The quality module must remain a pure analytics function with no"
            " dependency on persistence, API, reports, alerts, or compliance layers."
        )


def test_quality_module_has_no_system_clock() -> None:
    """metrics/quality.py does not call system clock functions.

    Belt-and-suspenders check alongside the unit-level purity tests.
    compute_data_quality is a pure function — report_date is always caller-provided.
    """
    quality_path = _APP_DIR / "metrics" / "quality.py"
    if not quality_path.exists():
        return
    text = quality_path.read_text(encoding="utf-8", errors="replace")
    for pattern in (".now(", ".today(", "time.time("):
        assert pattern not in text, (
            f"System clock call {pattern!r} found in metrics/quality.py.\n"
            "compute_data_quality must remain pure — report_date is caller-provided"
            " (D-031, D-056, D-082)."
        )
