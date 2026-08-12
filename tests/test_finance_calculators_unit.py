"""Unit tests for the finance advisory math (app/lib/finance).

These calculators produce numbers an entrepreneur may act on financially, so the
tests pin exact arithmetic rather than smoke-checking shapes.
"""

from __future__ import annotations

import pytest
from app.lib.finance.credit_calculator import (
    calculate_credit,
    compare_rates,
    evaluate_credit_load,
)
from app.lib.finance.locations import get_location, monthly_staff_cost
from app.lib.finance.sectors import list_sectors
from app.lib.finance.tax_calculator import (
    SELF_EMPLOYED_TURNOVER_CAP_SOM,
    TURNOVER_TAX_CAP_SOM,
    calculate_tax_regimes,
)

# --------------------------------------------------------------------- credit


def test_annuity_payment_matches_standard_formula() -> None:
    result = calculate_credit(principal_som=200_000_000, annual_rate_pct=28, months=36)
    # Standard annuity: P * i * (1+i)^n / ((1+i)^n - 1), i = 28/1200
    assert result.monthly_payment_som == 8_272_718
    assert result.months == 36
    assert len(result.schedule) == 36


def test_schedule_fully_amortises_principal() -> None:
    result = calculate_credit(principal_som=150_000_000, annual_rate_pct=19, months=24)
    assert result.schedule[-1].balance_som == 0
    principal_repaid = sum(row.principal_som for row in result.schedule)
    assert principal_repaid == pytest.approx(150_000_000, abs=2)


def test_total_payment_equals_principal_plus_interest() -> None:
    result = calculate_credit(principal_som=100_000_000, annual_rate_pct=24, months=12)
    assert result.total_payment_som == pytest.approx(
        result.principal_som + result.total_interest_som, abs=12
    )


def test_grace_period_defers_principal_only() -> None:
    result = calculate_credit(
        principal_som=200_000_000, annual_rate_pct=18, months=84, grace_months=12
    )
    grace_rows = result.schedule[:12]
    assert all(row.principal_som == 0 for row in grace_rows)
    assert all(row.interest_som > 0 for row in grace_rows)
    assert all(row.balance_som == 200_000_000 for row in grace_rows)
    assert result.schedule[-1].balance_som == 0


def test_differentiated_payments_decrease_over_time() -> None:
    result = calculate_credit(
        principal_som=120_000_000, annual_rate_pct=20, months=12, method="differentiated"
    )
    payments = [row.payment_som for row in result.schedule]
    assert payments == sorted(payments, reverse=True)


def test_zero_rate_splits_principal_evenly() -> None:
    result = calculate_credit(principal_som=120_000_000, annual_rate_pct=0, months=12)
    assert result.total_interest_som == 0
    assert result.monthly_payment_som == 10_000_000


@pytest.mark.parametrize(
    ("principal", "rate", "months"),
    [(0, 20, 12), (-1, 20, 12), (100, 20, 0), (100, -5, 12)],
)
def test_invalid_credit_inputs_rejected(principal: int, rate: float, months: int) -> None:
    with pytest.raises(ValueError):
        calculate_credit(principal_som=principal, annual_rate_pct=rate, months=months)


def test_grace_cannot_consume_whole_term() -> None:
    with pytest.raises(ValueError):
        calculate_credit(
            principal_som=100_000_000, annual_rate_pct=10, months=12, grace_months=12
        )


@pytest.mark.parametrize(
    ("payment", "revenue", "expected"),
    [
        (3_000_000, 30_000_000, "safe"),
        (7_000_000, 30_000_000, "warning"),
        (12_000_000, 30_000_000, "danger"),
    ],
)
def test_credit_load_bands(payment: int, revenue: int, expected: str) -> None:
    load = evaluate_credit_load(monthly_payment_som=payment, monthly_revenue_som=revenue)
    assert load.level == expected


def test_credit_load_without_revenue_is_danger_not_crash() -> None:
    load = evaluate_credit_load(monthly_payment_som=5_000_000, monthly_revenue_som=0)
    assert load.level == "danger"


def test_cheaper_rate_always_saves_money() -> None:
    delta = compare_rates(
        principal_som=200_000_000, months=36, rate_a_pct=28, rate_b_pct=14
    )
    assert delta["savings_som"] > 0
    assert delta["monthly_b_som"] < delta["monthly_a_som"]


# ------------------------------------------------------------------------ tax


def test_self_employed_rate_ineligible_above_one_billion() -> None:
    result = calculate_tax_regimes(
        annual_revenue_som=SELF_EMPLOYED_TURNOVER_CAP_SOM + 1,
        annual_cost_of_goods_som=0,
        annual_payroll_som=0,
        annual_other_costs_som=0,
    )
    se = next(r for r in result.results if r.regime == "self_employed")
    assert se.eligible is False
    assert se.ineligible_reason_uz is not None


def test_self_employed_rate_eligible_at_cap() -> None:
    result = calculate_tax_regimes(
        annual_revenue_som=SELF_EMPLOYED_TURNOVER_CAP_SOM,
        annual_cost_of_goods_som=0,
        annual_payroll_som=0,
        annual_other_costs_som=0,
    )
    se = next(r for r in result.results if r.regime == "self_employed")
    assert se.eligible is True
    assert se.annual_tax_som == SELF_EMPLOYED_TURNOVER_CAP_SOM // 100


def test_turnover_regime_ineligible_above_five_billion() -> None:
    result = calculate_tax_regimes(
        annual_revenue_som=TURNOVER_TAX_CAP_SOM + 1,
        annual_cost_of_goods_som=0,
        annual_payroll_som=0,
        annual_other_costs_som=0,
    )
    turnover = next(r for r in result.results if r.regime == "turnover")
    assert turnover.eligible is False


def test_legal_entity_cannot_use_self_employed_regime() -> None:
    result = calculate_tax_regimes(
        annual_revenue_som=500_000_000,
        annual_cost_of_goods_som=0,
        annual_payroll_som=0,
        annual_other_costs_som=0,
        is_individual_entrepreneur=False,
    )
    se = next(r for r in result.results if r.regime == "self_employed")
    assert se.eligible is False


def test_cheapest_regime_is_among_eligible_only() -> None:
    result = calculate_tax_regimes(
        annual_revenue_som=2_000_000_000,
        annual_cost_of_goods_som=1_600_000_000,
        annual_payroll_som=120_000_000,
        annual_other_costs_som=100_000_000,
    )
    assert result.cheapest is not None
    assert result.cheapest.eligible is True
    assert result.savings_vs_worst_som >= 0


def test_payroll_adds_social_tax_to_every_regime() -> None:
    """Hiring always adds social tax; only the general regime offsets it.

    Under the turnover regimes the tax base is revenue, so payroll is pure added
    cost. Under the general regime payroll is a deductible expense, so the profit
    tax falls and the total can end up lower — that is correct, not a bug.
    """
    without = calculate_tax_regimes(
        annual_revenue_som=500_000_000,
        annual_cost_of_goods_som=300_000_000,
        annual_payroll_som=0,
        annual_other_costs_som=0,
    )
    with_payroll = calculate_tax_regimes(
        annual_revenue_som=500_000_000,
        annual_cost_of_goods_som=300_000_000,
        annual_payroll_som=100_000_000,
        annual_other_costs_som=0,
    )

    def social_tax(result: object) -> int:
        return next(
            amount
            for label, amount in result.breakdown_uz  # type: ignore[attr-defined]
            if "Ijtimoiy" in label
        )

    for a, b in zip(without.results, with_payroll.results, strict=True):
        assert social_tax(a) == 0
        assert social_tax(b) == 12_000_000  # 12% of 100 mln payroll
        if b.regime in {"self_employed", "turnover"}:
            assert b.annual_tax_som > a.annual_tax_som


def test_disclaimer_always_present() -> None:
    result = calculate_tax_regimes(
        annual_revenue_som=1,
        annual_cost_of_goods_som=0,
        annual_payroll_som=0,
        annual_other_costs_som=0,
    )
    assert "buxgalter" in result.disclaimer_uz.lower()


# ------------------------------------------------------------- sectors/places


def test_every_sector_has_sane_benchmarks() -> None:
    for sector in list_sectors():
        assert 0 < sector.gross_margin_pct < 100
        assert sector.avg_check_som > 0
        assert sector.monthly_revenue_per_employee_som > 0


def test_staff_cost_scales_with_headcount() -> None:
    location = get_location("toshkent")
    assert location is not None
    assert monthly_staff_cost(location, 0) == 0
    assert monthly_staff_cost(location, 3) == location.avg_monthly_salary_som * 3


def test_unverified_location_incentives_are_flagged() -> None:
    navoiy = get_location("navoiy")
    assert navoiy is not None
    for incentive in navoiy.incentives:
        # Anything not legally confirmed must carry a source note for the UI badge.
        if not incentive.verified:
            assert incentive.source_note
