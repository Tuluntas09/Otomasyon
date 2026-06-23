"""Unit tests for the Phase 5 compliance guard.

All tests are pure: no DB, no file I/O, no CSV.
Inputs are plain strings constructed in-memory.
"""

import pytest

from app.compliance.guard import ComplianceViolation, check_compliance
from app.core.exceptions import ComplianceViolationError


# ---------------------------------------------------------------------------
# Clean / empty input
# ---------------------------------------------------------------------------


def test_clean_text_passes():
    check_compliance("Portfolio value is 12.4% below its 90-day peak.")


def test_empty_string_passes():
    check_compliance("")


# ---------------------------------------------------------------------------
# English single-word forbidden terms
# ---------------------------------------------------------------------------


def test_buy_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("You should buy more equities.")


def test_sell_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Consider sell positions before the deadline.")


def test_hold_standalone_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("The recommendation is to hold.")


def test_threshold_does_not_trigger_hold():
    # "threshold" contains "hold" but \bhold\b does not match inside a word
    check_compliance("The volatility threshold is 2.00%.")


def test_profit_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("This trade could generate profit.")


def test_loss_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Avoid a loss by acting quickly.")


def test_glossy_does_not_trigger_loss():
    # "glossy" contains "loss" but \bloss\b does not match inside a word
    check_compliance("The glossy report shows metrics.")


def test_should_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("You should review the allocation.")


def test_must_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("You must rebalance now.")


def test_guaranteed_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Returns are guaranteed.")


def test_opportunity_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("There is an opportunity here.")


def test_reduce_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Reduce your exposure to this sector.")


def test_increase_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Increase the position size.")


def test_recommend_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Analysts recommend this action.")


def test_suggest_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Data suggest buying more.")


def test_execute_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Execute the strategy immediately.")


def test_order_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Place an order at market price.")


def test_broker_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Contact your broker.")


# ---------------------------------------------------------------------------
# English multi-word forbidden phrases
# ---------------------------------------------------------------------------


def test_target_price_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("The target price is $150.")


def test_price_target_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("The analyst set a price target.")


def test_price_prediction_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Here is a price prediction for next week.")


def test_take_profit_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Set a take profit level.")


def test_stop_loss_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Use a stop loss to limit downside.")


def test_paper_trade_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("You can paper trade to practice.")


def test_live_trade_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Start a live trade session.")


# ---------------------------------------------------------------------------
# Multiple violations reported together
# ---------------------------------------------------------------------------


def test_multiple_violations_reported():
    with pytest.raises(ComplianceViolationError) as exc_info:
        check_compliance("Buy low and sell high for profit.")
    err = exc_info.value
    matched_terms = {v.matched_term for v in err.violations}
    assert "buy" in matched_terms
    assert "sell" in matched_terms
    assert "profit" in matched_terms


def test_violations_contain_matched_term_and_context():
    with pytest.raises(ComplianceViolationError) as exc_info:
        check_compliance("This is a guaranteed return.")
    violations = exc_info.value.violations
    assert len(violations) >= 1
    v = violations[0]
    assert isinstance(v, ComplianceViolation)
    assert isinstance(v.matched_term, str)
    assert isinstance(v.context, str)
    assert v.matched_term in v.context.lower()


# ---------------------------------------------------------------------------
# Turkish forbidden terms
# ---------------------------------------------------------------------------


def test_turkish_firsat_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Bu bir fırsat.")


def test_turkish_al_standalone_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Hemen al ve kâr et.")


def test_total_does_not_trigger_al():
    # "total" ends with "al" but \bal\b does not match inside a word
    check_compliance("The total market value is $10,000.")


def test_capital_does_not_trigger_al():
    # "capital" ends with "al" but \bal\b does not match inside a word
    check_compliance("The capital at risk is 15%.")


def test_turkish_sat_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Hisseni sat.")


def test_turkish_tut_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Pozisyonunu tut.")


def test_turkish_emir_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Bir emir ver.")


def test_turkish_hedef_fiyat_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Hedef fiyat 200 TL.")


def test_turkish_kar_al_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Kar al seviyesine geldi.")


def test_turkish_zarar_durdur_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Zarar durdur emri koy.")


def test_turkish_islem_ac_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Şimdi işlem aç.")


def test_turkish_islem_kapat_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("İşlem kapat zamanı.")


def test_turkish_araci_kurum_raises():
    with pytest.raises(ComplianceViolationError):
        check_compliance("Aracı kurum ile iletişime geç.")


# ---------------------------------------------------------------------------
# All planned alert explanation templates pass compliance
# ---------------------------------------------------------------------------


def test_conc_fired_template_passes():
    check_compliance(
        "Concentration alert [CONC-001]: AAPL weight is 30.0%,"
        " above the single-position ceiling of 25.0%."
    )


def test_conc_not_fired_template_passes():
    check_compliance(
        "Concentration check [CONC-001]: all priced positions are within the"
        " 25.0% single-position ceiling."
    )


def test_conc_no_priced_template_passes():
    check_compliance(
        "Concentration check [CONC-001]: no priced positions are available"
        " for concentration evaluation."
    )


def test_dd_fired_template_passes():
    check_compliance(
        "Drawdown alert [DD-001]: portfolio value is 18.0% below its"
        " 90-day peak, above the 15.0% ceiling."
    )


def test_dd_not_fired_template_passes():
    check_compliance(
        "Drawdown check [DD-001]: portfolio value is 5.0% below its"
        " 90-day peak, within the 15.0% ceiling."
    )


def test_dd_no_data_template_passes():
    check_compliance(
        "Drawdown check [DD-001]: insufficient price history to compute"
        " a drawdown value."
    )


def test_vol_fired_template_passes():
    check_compliance(
        "Volatility alert [VOL-001]: rolling standard deviation of daily"
        " returns is 2.80%, above the 2.00% threshold."
    )


def test_vol_not_fired_template_passes():
    check_compliance(
        "Volatility check [VOL-001]: rolling standard deviation of daily"
        " returns is 1.20%, within the 2.00% threshold."
    )


def test_vol_no_data_template_passes():
    check_compliance(
        "Volatility check [VOL-001]: insufficient price history to compute"
        " a volatility proxy."
    )


def test_cov_fired_template_passes():
    check_compliance(
        "Coverage alert [COV-001]: 2 position(s) have no price data: AAPL, MSFT."
    )


def test_cov_not_fired_template_passes():
    check_compliance(
        "Coverage check [COV-001]: 0 position(s) have no price data,"
        " within the configured maximum of 0."
    )
