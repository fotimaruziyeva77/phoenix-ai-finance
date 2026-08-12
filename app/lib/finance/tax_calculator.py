"""2026 tax-regime comparison for small business in Uzbekistan.

**Scope and honesty:** this is a *planning estimator*, not accounting software.
VAT is approximated as 12% of value added (revenue minus cost of goods), and
profit tax as 15% of operating profit. Real filings involve input-VAT offsets,
deductible-expense rules, and sector exemptions this module does not model.
``TaxComparison.disclaimer_uz`` carries that warning to the UI, and every screen
that renders these numbers must show it.

Rates and thresholds below were gathered from public sources on 2026-08-12 and
**must be confirmed with an accountant** before anyone acts on them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# --- 2026 parameters (see app.lib.finance.DATA_AS_OF) ---
SELF_EMPLOYED_RATE_PCT = 1.0
"""YaTT / self-employed turnover tax, annual turnover up to 1 bln so'm (from 2026-01-01)."""

SELF_EMPLOYED_TURNOVER_CAP_SOM = 1_000_000_000

TURNOVER_TAX_RATE_PCT = 4.0
"""Standard turnover-tax rate."""

TURNOVER_TAX_CAP_SOM = 5_000_000_000
"""Threshold for mandatory move to the general regime (raised from 1 bln on 2026-06-01)."""

VAT_RATE_PCT = 12.0
PROFIT_TAX_RATE_PCT = 15.0
SOCIAL_TAX_RATE_PCT = 12.0
"""Employer social tax on payroll (non-budget organisations)."""

PIT_RATE_PCT = 12.0
"""Personal income tax withheld from employee salaries."""

RegimeId = Literal["self_employed", "turnover", "general"]

DISCLAIMER_UZ = (
    "Bu hisob-kitob taxminiy va rejalashtirish uchun mo'ljallangan. Stavkalar "
    "2026-yil 12-avgust holatiga ochiq manbalardan olingan. Yakuniy qaror qabul "
    "qilishdan oldin buxgalter yoki soliq.uz orqali tasdiqlang."
)


@dataclass(frozen=True, slots=True)
class RegimeResult:
    regime: RegimeId
    label_uz: str
    eligible: bool
    ineligible_reason_uz: str | None
    annual_tax_som: int
    monthly_tax_som: int
    effective_rate_pct: float
    """Total tax as a share of annual revenue."""
    breakdown_uz: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class TaxComparison:
    annual_revenue_som: int
    results: tuple[RegimeResult, ...]
    cheapest: RegimeResult | None
    savings_vs_worst_som: int
    disclaimer_uz: str


def _payroll_social_tax(annual_payroll_som: int) -> int:
    return int(annual_payroll_som * SOCIAL_TAX_RATE_PCT / 100)


def calculate_tax_regimes(
    *,
    annual_revenue_som: int,
    annual_cost_of_goods_som: int,
    annual_payroll_som: int,
    annual_other_costs_som: int,
    is_individual_entrepreneur: bool = True,
) -> TaxComparison:
    """Compute the annual tax burden under each regime the business may use."""
    if annual_revenue_som < 0:
        raise ValueError("annual_revenue_som cannot be negative")

    social_tax = _payroll_social_tax(annual_payroll_som)
    value_added = max(annual_revenue_som - annual_cost_of_goods_som, 0)
    operating_profit = max(
        annual_revenue_som
        - annual_cost_of_goods_som
        - annual_payroll_som
        - annual_other_costs_som,
        0,
    )

    results: list[RegimeResult] = []

    # 1. Self-employed / YaTT reduced rate
    se_eligible = (
        is_individual_entrepreneur and annual_revenue_som <= SELF_EMPLOYED_TURNOVER_CAP_SOM
    )
    se_tax = int(annual_revenue_som * SELF_EMPLOYED_RATE_PCT / 100)
    results.append(
        RegimeResult(
            regime="self_employed",
            label_uz="YaTT — aylanmadan 1%",
            eligible=se_eligible,
            ineligible_reason_uz=(
                None
                if se_eligible
                else (
                    "Yillik aylanma 1 mlrd so'mdan oshadi"
                    if is_individual_entrepreneur
                    else "Faqat YaTT va o'zini o'zi band qilganlar uchun"
                )
            ),
            annual_tax_som=se_tax + social_tax,
            monthly_tax_som=(se_tax + social_tax) // 12,
            effective_rate_pct=(
                round((se_tax + social_tax) / annual_revenue_som * 100, 2)
                if annual_revenue_som
                else 0.0
            ),
            breakdown_uz=(
                ("Aylanma solig'i (1%)", se_tax),
                ("Ijtimoiy soliq (12%)", social_tax),
            ),
        )
    )

    # 2. Standard turnover tax
    to_eligible = annual_revenue_som <= TURNOVER_TAX_CAP_SOM
    to_tax = int(annual_revenue_som * TURNOVER_TAX_RATE_PCT / 100)
    results.append(
        RegimeResult(
            regime="turnover",
            label_uz="Aylanma solig'i — 4%",
            eligible=to_eligible,
            ineligible_reason_uz=(
                None if to_eligible else "Yillik aylanma 5 mlrd so'mdan oshadi"
            ),
            annual_tax_som=to_tax + social_tax,
            monthly_tax_som=(to_tax + social_tax) // 12,
            effective_rate_pct=(
                round((to_tax + social_tax) / annual_revenue_som * 100, 2)
                if annual_revenue_som
                else 0.0
            ),
            breakdown_uz=(
                ("Aylanma solig'i (4%)", to_tax),
                ("Ijtimoiy soliq (12%)", social_tax),
            ),
        )
    )

    # 3. General regime: VAT + profit tax
    vat = int(value_added * VAT_RATE_PCT / 100)
    profit_tax = int(operating_profit * PROFIT_TAX_RATE_PCT / 100)
    general_total = vat + profit_tax + social_tax
    results.append(
        RegimeResult(
            regime="general",
            label_uz="Umumiy rejim — QQS 12% + foyda solig'i 15%",
            eligible=True,
            ineligible_reason_uz=None,
            annual_tax_som=general_total,
            monthly_tax_som=general_total // 12,
            effective_rate_pct=(
                round(general_total / annual_revenue_som * 100, 2)
                if annual_revenue_som
                else 0.0
            ),
            breakdown_uz=(
                ("QQS (12%, qo'shilgan qiymatdan)", vat),
                ("Foyda solig'i (15%)", profit_tax),
                ("Ijtimoiy soliq (12%)", social_tax),
            ),
        )
    )

    eligible = [r for r in results if r.eligible]
    cheapest = min(eligible, key=lambda r: r.annual_tax_som) if eligible else None
    worst = max(eligible, key=lambda r: r.annual_tax_som) if eligible else None
    savings = (
        worst.annual_tax_som - cheapest.annual_tax_som if cheapest and worst else 0
    )

    return TaxComparison(
        annual_revenue_som=annual_revenue_som,
        results=tuple(results),
        cheapest=cheapest,
        savings_vs_worst_som=savings,
        disclaimer_uz=DISCLAIMER_UZ,
    )
