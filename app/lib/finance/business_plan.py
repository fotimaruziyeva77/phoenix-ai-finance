"""Business-plan engine: break-even, payback, and a plain-language verdict.

The product promise is a straight answer to *"bu biznes ishlaydimi?"*, so this
module ends at a three-way :class:`Verdict` rather than a wall of numbers.

Method
------
1. Monthly fixed costs = rent + payroll + sector baseline scaled by the city's
   utilities index.
2. Break-even revenue = fixed costs / gross-margin rate.
3. Capacity revenue = staff count x sector revenue-per-employee. This is the
   ceiling one team can realistically service.
4. Utilisation = break-even / capacity. The closer break-even sits to the
   ceiling, the less room the business has to survive a bad month.
5. Payback = initial capital / monthly profit at a realistic ramp of capacity.

Every assumption is returned in :attr:`BusinessPlanResult.assumptions` so the UI
can show and let the user edit them. Nothing here is hidden from the entrepreneur.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from app.lib.finance.locations import Location, get_location, monthly_staff_cost
from app.lib.finance.sectors import SectorBenchmark, get_sector
from app.lib.finance.tax_calculator import TaxComparison, calculate_tax_regimes

Verdict = Literal["viable", "tight", "unprofitable"]

#: Share of capacity a new business is assumed to reach once it stabilises.
REALISTIC_RAMP = 0.80

#: Utilisation bands — break-even revenue as a share of capacity revenue.
UTILISATION_VIABLE_MAX = 0.60
UTILISATION_TIGHT_MAX = 0.90

#: Payback beyond this is treated as unattractive for a small business.
PAYBACK_TIGHT_MONTHS = 24
PAYBACK_BAD_MONTHS = 48

WORKING_DAYS_PER_MONTH = 26


@dataclass(frozen=True, slots=True)
class BusinessPlanInput:
    business_name: str
    sector_id: str
    location_id: str
    initial_capital_som: int
    employee_count: int
    monthly_rent_som: int
    product_description: str = ""
    goal: str = ""
    #: Optional override; when absent a realistic ramp of capacity is used.
    expected_monthly_revenue_som: int | None = None
    is_individual_entrepreneur: bool = True


@dataclass(frozen=True, slots=True)
class Assumption:
    key: str
    label_uz: str
    value_som: int | None
    value_text: str
    editable: bool


@dataclass(frozen=True, slots=True)
class BusinessPlanResult:
    business_name: str
    sector: SectorBenchmark
    location: Location

    monthly_fixed_costs_som: int
    monthly_rent_som: int
    monthly_payroll_som: int
    monthly_other_costs_som: int

    break_even_revenue_som: int
    break_even_units: int
    break_even_customers_per_day: int

    capacity_revenue_som: int
    planned_revenue_som: int
    utilisation_pct: float

    monthly_gross_profit_som: int
    monthly_net_profit_som: int
    payback_months: int | None

    tax: TaxComparison

    verdict: Verdict
    verdict_title_uz: str
    verdict_reasons_uz: tuple[str, ...]
    recommendations_uz: tuple[str, ...]
    assumptions: tuple[Assumption, ...]


def _verdict_title(verdict: Verdict) -> str:
    return {
        "viable": "Bu biznes ishlaydi",
        "tight": "Chegarada — ehtiyot bo'ling",
        "unprofitable": "Hozirgi shartlarda tavsiya etilmaydi",
    }[verdict]


def build_business_plan(data: BusinessPlanInput) -> BusinessPlanResult:
    """Run the full plan. Raises ``ValueError`` on unknown sector/location."""
    sector = get_sector(data.sector_id)
    if sector is None:
        raise ValueError(f"unknown sector_id: {data.sector_id}")
    location = get_location(data.location_id)
    if location is None:
        raise ValueError(f"unknown location_id: {data.location_id}")
    if data.employee_count < 0:
        raise ValueError("employee_count cannot be negative")
    if data.monthly_rent_som < 0 or data.initial_capital_som < 0:
        raise ValueError("amounts cannot be negative")

    payroll = monthly_staff_cost(location, data.employee_count)
    other = int(sector.monthly_other_costs_som * location.utilities_index)
    fixed = data.monthly_rent_som + payroll + other

    margin_rate = sector.gross_margin_pct / 100
    break_even_revenue = int(fixed / margin_rate) if margin_rate > 0 else 0
    break_even_units = (
        break_even_revenue // sector.avg_check_som if sector.avg_check_som else 0
    )
    break_even_per_day = -(-break_even_units // WORKING_DAYS_PER_MONTH)  # ceil

    # One owner still works the business even with zero hired staff.
    effective_people = max(data.employee_count, 1)
    capacity_revenue = effective_people * sector.monthly_revenue_per_employee_som

    planned_revenue = (
        data.expected_monthly_revenue_som
        if data.expected_monthly_revenue_som is not None
        else int(capacity_revenue * REALISTIC_RAMP)
    )

    utilisation = (
        round(break_even_revenue / capacity_revenue * 100, 1) if capacity_revenue else 999.0
    )

    gross_profit = int(planned_revenue * margin_rate)
    net_profit = gross_profit - fixed

    tax = calculate_tax_regimes(
        annual_revenue_som=planned_revenue * 12,
        annual_cost_of_goods_som=int(planned_revenue * (1 - margin_rate)) * 12,
        annual_payroll_som=payroll * 12,
        annual_other_costs_som=(data.monthly_rent_som + other) * 12,
        is_individual_entrepreneur=data.is_individual_entrepreneur,
    )
    monthly_tax = tax.cheapest.monthly_tax_som if tax.cheapest else 0
    net_after_tax = net_profit - monthly_tax

    payback = (
        -(-data.initial_capital_som // net_after_tax)
        if net_after_tax > 0 and data.initial_capital_som > 0
        else None
    )

    # --- verdict ---
    reasons: list[str] = []
    recommendations: list[str] = []

    if net_after_tax <= 0:
        verdict: Verdict = "unprofitable"
        reasons.append(
            f"Rejalashtirilgan aylanmada oylik zarar: {abs(net_after_tax):,} so'm. "
            "Doimiy xarajatlar yalpi foydadan yuqori."
        )
    elif utilisation > UTILISATION_TIGHT_MAX * 100:
        verdict = "unprofitable"
        reasons.append(
            f"Zararsizlikka chiqish uchun quvvatingizning {utilisation}% i kerak. "
            "Bu deyarli imkonsiz — bitta yomon oy zararga olib keladi."
        )
    elif utilisation > UTILISATION_VIABLE_MAX * 100:
        verdict = "tight"
        reasons.append(
            f"Zararsizlik nuqtasi quvvatingizning {utilisation}% i — zaxira kam. "
            "Aylanma biroz tushsa zararga o'tasiz."
        )
    elif payback is not None and payback > PAYBACK_TIGHT_MONTHS:
        verdict = "tight"
        reasons.append(
            f"Zararsizlik bo'yicha muammo yo'q (quvvatning {utilisation}% i), lekin "
            f"boshqa muammo bor: kapital {payback} oyda qoplanadi — bu juda sekin."
        )
    else:
        verdict = "viable"
        reasons.append(
            f"Zararsizlikka quvvatingizning {utilisation}% ida chiqasiz — zaxira yetarli."
        )

    reasons.append(
        f"Kuniga {break_even_per_day} ta mijoz (o'rtacha chek "
        f"{sector.avg_check_som:,} so'm) — zararsizlik uchun shu kerak."
    )

    if payback is None:
        reasons.append("Sof foyda manfiy — boshlang'ich kapital qoplanmaydi.")
        recommendations.append("Ijara yoki xodimlar sonini qayta ko'rib chiqing.")
    elif payback > PAYBACK_BAD_MONTHS:
        reasons.append(f"Boshlang'ich kapital {payback} oyda qoplanadi — bu juda uzoq.")
        recommendations.append("Boshlang'ich kapitalni kamaytiring yoki marjani oshiring.")
    else:
        reasons.append(f"Boshlang'ich kapital taxminan {payback} oyda qoplanadi.")

    if tax.cheapest is not None and tax.savings_vs_worst_som > 0:
        recommendations.append(
            f"Soliq rejimi: \"{tax.cheapest.label_uz}\" eng arzoni — yiliga "
            f"{tax.savings_vs_worst_som:,} so'm tejaysiz."
        )

    if data.monthly_rent_som > fixed * 0.4:
        recommendations.append(
            "Ijara doimiy xarajatlarning 40% dan ortig'ini tashkil qiladi — "
            "arzonroq joy sizni chegaradan chiqaradi."
        )

    if sector.preferential_sector:
        recommendations.append(
            "Sohangiz davlat imtiyozli kredit dasturlariga kiradi — 'Imtiyozlar' "
            "bo'limini tekshiring."
        )

    assumptions = (
        Assumption(
            key="avg_salary",
            label_uz=f"{location.label_uz} bo'yicha o'rtacha oylik ish haqi",
            value_som=location.avg_monthly_salary_som,
            value_text=f"{location.avg_monthly_salary_som:,} so'm",
            editable=True,
        ),
        Assumption(
            key="gross_margin",
            label_uz="Soha yalpi marjasi",
            value_som=None,
            value_text=f"{sector.gross_margin_pct}%",
            editable=True,
        ),
        Assumption(
            key="avg_check",
            label_uz="O'rtacha chek",
            value_som=sector.avg_check_som,
            value_text=f"{sector.avg_check_som:,} so'm",
            editable=True,
        ),
        Assumption(
            key="other_costs",
            label_uz="Kommunal va sarf materiallari",
            value_som=other,
            value_text=f"{other:,} so'm/oy",
            editable=True,
        ),
        Assumption(
            key="capacity",
            label_uz="Bir xodim xizmat ko'rsata oladigan oylik aylanma",
            value_som=sector.monthly_revenue_per_employee_som,
            value_text=f"{sector.monthly_revenue_per_employee_som:,} so'm",
            editable=True,
        ),
    )

    return BusinessPlanResult(
        business_name=data.business_name,
        sector=sector,
        location=location,
        monthly_fixed_costs_som=fixed,
        monthly_rent_som=data.monthly_rent_som,
        monthly_payroll_som=payroll,
        monthly_other_costs_som=other,
        break_even_revenue_som=break_even_revenue,
        break_even_units=break_even_units,
        break_even_customers_per_day=break_even_per_day,
        capacity_revenue_som=capacity_revenue,
        planned_revenue_som=planned_revenue,
        utilisation_pct=utilisation,
        monthly_gross_profit_som=gross_profit,
        monthly_net_profit_som=net_after_tax,
        payback_months=payback,
        tax=tax,
        verdict=verdict,
        verdict_title_uz=_verdict_title(verdict),
        verdict_reasons_uz=tuple(reasons),
        recommendations_uz=tuple(recommendations),
        assumptions=assumptions,
    )


@dataclass(frozen=True, slots=True)
class LocationComparison:
    """Same business, two cities — the demo's headline."""

    plans: tuple[BusinessPlanResult, ...]
    best_location_id: str
    verdict_differs: bool
    summary_uz: str


def compare_locations(
    data: BusinessPlanInput, location_ids: tuple[str, ...]
) -> LocationComparison:
    """Re-run the plan across cities, holding every other input constant."""
    plans: list[BusinessPlanResult] = []
    for loc_id in location_ids:
        plans.append(build_business_plan(replace(data, location_id=loc_id)))

    rank = {"viable": 0, "tight": 1, "unprofitable": 2}
    best = min(plans, key=lambda p: (rank[p.verdict], p.payback_months or 10_000))
    verdicts = {p.verdict for p in plans}

    if len(verdicts) > 1:
        others = [p for p in plans if p.location.id != best.location.id]
        other = others[0] if others else best
        summary = (
            f"{best.location.label_uz}: {best.verdict_title_uz.lower()}. "
            f"{other.location.label_uz}: {other.verdict_title_uz.lower()}. "
            "Bir xil biznes, boshqa shahar — natija boshqacha."
        )
    else:
        summary = (
            f"Har ikkala shaharda ham natija bir xil: {best.verdict_title_uz.lower()}. "
            f"Eng tez qoplanish: {best.location.label_uz}."
        )

    return LocationComparison(
        plans=tuple(plans),
        best_location_id=best.location.id,
        verdict_differs=len(verdicts) > 1,
        summary_uz=summary,
    )
