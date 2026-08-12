"""Unit tests for the business-plan verdict engine (app/lib/finance/business_plan).

The verdict is the product's core promise — a straight "does this work?" — so the
tests pin the boundaries between viable / tight / unprofitable and the location
comparison the demo is built around.
"""

from __future__ import annotations

import pytest
from app.lib.finance.business_plan import (
    BusinessPlanInput,
    build_business_plan,
    compare_locations,
)


def make_input(**overrides: object) -> BusinessPlanInput:
    base = {
        "business_name": "Baraka Market",
        "sector_id": "oziq_ovqat",
        "location_id": "toshkent",
        "initial_capital_som": 150_000_000,
        "employee_count": 2,
        "monthly_rent_som": 8_000_000,
    }
    base.update(overrides)
    return BusinessPlanInput(**base)  # type: ignore[arg-type]


def test_unknown_sector_rejected() -> None:
    with pytest.raises(ValueError, match="unknown sector_id"):
        build_business_plan(make_input(sector_id="nonexistent"))


def test_unknown_location_rejected() -> None:
    with pytest.raises(ValueError, match="unknown location_id"):
        build_business_plan(make_input(location_id="atlantida"))


def test_negative_amounts_rejected() -> None:
    with pytest.raises(ValueError):
        build_business_plan(make_input(monthly_rent_som=-1))


def test_fixed_costs_are_rent_plus_payroll_plus_other() -> None:
    plan = build_business_plan(make_input())
    assert plan.monthly_fixed_costs_som == (
        plan.monthly_rent_som + plan.monthly_payroll_som + plan.monthly_other_costs_som
    )


def test_break_even_revenue_covers_fixed_costs_at_sector_margin() -> None:
    plan = build_business_plan(make_input())
    gross_at_break_even = plan.break_even_revenue_som * plan.sector.gross_margin_pct / 100
    assert gross_at_break_even == pytest.approx(plan.monthly_fixed_costs_som, rel=0.001)


def test_break_even_customers_per_day_is_derived_from_average_check() -> None:
    plan = build_business_plan(make_input())
    expected_units = plan.break_even_revenue_som // plan.sector.avg_check_som
    assert plan.break_even_units == expected_units
    # 26 working days, rounded up — you cannot serve a fraction of a customer.
    assert plan.break_even_customers_per_day == -(-expected_units // 26)


def test_high_rent_makes_business_unprofitable() -> None:
    plan = build_business_plan(make_input(monthly_rent_som=90_000_000))
    assert plan.verdict == "unprofitable"
    assert plan.payback_months is None


def test_low_cost_high_margin_business_is_viable() -> None:
    plan = build_business_plan(
        make_input(
            sector_id="it_xizmat",
            monthly_rent_som=3_000_000,
            employee_count=3,
            initial_capital_som=40_000_000,
        )
    )
    assert plan.verdict == "viable"
    assert plan.payback_months is not None
    assert plan.monthly_net_profit_som > 0


def test_verdict_reasons_and_assumptions_always_populated() -> None:
    plan = build_business_plan(make_input())
    assert plan.verdict_reasons_uz
    assert plan.assumptions
    # Assumptions must be visible so the entrepreneur can challenge them.
    keys = {a.key for a in plan.assumptions}
    assert {"avg_salary", "gross_margin", "avg_check"} <= keys


def test_preferential_sector_surfaces_program_hint() -> None:
    plan = build_business_plan(
        make_input(sector_id="chorvachilik", monthly_rent_som=4_000_000)
    )
    assert any("imtiyoz" in rec.lower() for rec in plan.recommendations_uz)


def test_rent_heavy_structure_is_called_out() -> None:
    plan = build_business_plan(make_input(monthly_rent_som=40_000_000))
    assert any("ijara" in rec.lower() for rec in plan.recommendations_uz)


def test_expected_revenue_override_is_respected() -> None:
    plan = build_business_plan(make_input(expected_monthly_revenue_som=200_000_000))
    assert plan.planned_revenue_som == 200_000_000


# ------------------------------------------------------------------ locations


def test_comparison_keeps_every_input_except_location() -> None:
    data = make_input()
    comparison = compare_locations(data, ("toshkent", "navoiy"))
    assert [p.location.id for p in comparison.plans] == ["toshkent", "navoiy"]
    for plan in comparison.plans:
        assert plan.monthly_rent_som == data.monthly_rent_som
        assert plan.sector.id == data.sector_id


def test_cheaper_city_yields_lower_break_even() -> None:
    comparison = compare_locations(make_input(), ("toshkent", "navoiy"))
    toshkent, navoiy = comparison.plans
    # Lower wages and utilities in Navoiy must lower the break-even point.
    assert navoiy.break_even_revenue_som < toshkent.break_even_revenue_som


def test_comparison_picks_the_better_verdict_as_best() -> None:
    comparison = compare_locations(make_input(), ("toshkent", "navoiy"))
    rank = {"viable": 0, "tight": 1, "unprofitable": 2}
    best = next(p for p in comparison.plans if p.location.id == comparison.best_location_id)
    assert all(rank[best.verdict] <= rank[p.verdict] for p in comparison.plans)


def test_comparison_summary_mentions_both_cities_when_verdicts_differ() -> None:
    comparison = compare_locations(make_input(), ("toshkent", "navoiy"))
    if comparison.verdict_differs:
        assert "Toshkent" in comparison.summary_uz
        assert "Navoiy" in comparison.summary_uz


def test_single_location_comparison_does_not_crash() -> None:
    comparison = compare_locations(make_input(), ("navoiy",))
    assert len(comparison.plans) == 1
    assert comparison.verdict_differs is False
    assert comparison.best_location_id == "navoiy"
