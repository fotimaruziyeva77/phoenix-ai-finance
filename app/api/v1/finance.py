"""Finance advisory endpoints — business plan, credit, tax.

No auth and no persistence: these are stateless calculators over data the caller
supplies, so there is nothing owner-scoped to protect. Keep it that way — if a
future endpoint reads or writes a user's saved profile it belongs behind
``Depends(get_current_user)`` in a separate module.

All arithmetic lives in :mod:`app.lib.finance`; handlers only translate shapes.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.lib.finance import DATA_AS_OF
from app.lib.finance.business_plan import (
    BusinessPlanInput,
    BusinessPlanResult,
    build_business_plan,
    compare_locations,
)
from app.lib.finance.credit_calculator import calculate_credit, evaluate_credit_load
from app.lib.finance.locations import DEMO_COMPARISON_PAIR, list_locations
from app.lib.finance.sectors import list_sectors
from app.lib.finance.tax_calculator import TaxComparison, calculate_tax_regimes
from app.schemas.finance import (
    AssumptionItem,
    BusinessPlanItem,
    BusinessPlanRequest,
    BusinessPlanResponse,
    CreditLoadItem,
    CreditRequest,
    CreditResponse,
    FinanceCatalogResponse,
    LocationComparisonItem,
    LocationIncentiveItem,
    LocationItem,
    PaymentRowItem,
    SectorItem,
    TaxComparisonItem,
    TaxRegimeItem,
    TaxRequest,
    TaxResponse,
)

router = APIRouter(tags=["finance"])


def _tax_to_item(tax: TaxComparison) -> TaxComparisonItem:
    return TaxComparisonItem(
        annual_revenue_som=tax.annual_revenue_som,
        results=[
            TaxRegimeItem(
                regime=r.regime,
                label_uz=r.label_uz,
                eligible=r.eligible,
                ineligible_reason_uz=r.ineligible_reason_uz,
                annual_tax_som=r.annual_tax_som,
                monthly_tax_som=r.monthly_tax_som,
                effective_rate_pct=r.effective_rate_pct,
                breakdown_uz=list(r.breakdown_uz),
            )
            for r in tax.results
        ],
        cheapest_regime=tax.cheapest.regime if tax.cheapest else None,
        savings_vs_worst_som=tax.savings_vs_worst_som,
        disclaimer_uz=tax.disclaimer_uz,
    )


def _plan_to_item(p: BusinessPlanResult) -> BusinessPlanItem:
    return BusinessPlanItem(
        business_name=p.business_name,
        sector_id=p.sector.id,
        sector_label_uz=p.sector.label_uz,
        location_id=p.location.id,
        location_label_uz=p.location.label_uz,
        monthly_fixed_costs_som=p.monthly_fixed_costs_som,
        monthly_rent_som=p.monthly_rent_som,
        monthly_payroll_som=p.monthly_payroll_som,
        monthly_other_costs_som=p.monthly_other_costs_som,
        break_even_revenue_som=p.break_even_revenue_som,
        break_even_units=p.break_even_units,
        break_even_customers_per_day=p.break_even_customers_per_day,
        capacity_revenue_som=p.capacity_revenue_som,
        planned_revenue_som=p.planned_revenue_som,
        utilisation_pct=p.utilisation_pct,
        monthly_gross_profit_som=p.monthly_gross_profit_som,
        monthly_net_profit_som=p.monthly_net_profit_som,
        payback_months=p.payback_months,
        verdict=p.verdict,
        verdict_title_uz=p.verdict_title_uz,
        verdict_reasons_uz=list(p.verdict_reasons_uz),
        recommendations_uz=list(p.recommendations_uz),
        assumptions=[
            AssumptionItem(
                key=a.key,
                label_uz=a.label_uz,
                value_som=a.value_som,
                value_text=a.value_text,
                editable=a.editable,
            )
            for a in p.assumptions
        ],
        tax=_tax_to_item(p.tax),
    )


@router.get(
    "/finance/catalog",
    response_model=FinanceCatalogResponse,
    summary="Sectors and locations available to the finance tools",
)
async def get_finance_catalog() -> FinanceCatalogResponse:
    return FinanceCatalogResponse(
        data_as_of=DATA_AS_OF,
        sectors=[
            SectorItem(
                id=s.id,
                label_uz=s.label_uz,
                label_ru=s.label_ru,
                label_en=s.label_en,
                gross_margin_pct=s.gross_margin_pct,
                avg_check_som=s.avg_check_som,
                preferential_sector=s.preferential_sector,
            )
            for s in list_sectors()
        ],
        locations=[
            LocationItem(
                id=loc.id,
                label_uz=loc.label_uz,
                label_ru=loc.label_ru,
                label_en=loc.label_en,
                region_uz=loc.region_uz,
                avg_monthly_salary_som=loc.avg_monthly_salary_som,
                tax_category=loc.tax_category,
                tax_category_verified=loc.tax_category_verified,
                incentives=[
                    LocationIncentiveItem(
                        code=i.code,
                        title_uz=i.title_uz,
                        detail_uz=i.detail_uz,
                        verified=i.verified,
                        source_note=i.source_note,
                    )
                    for i in loc.incentives
                ],
            )
            for loc in list_locations()
        ],
        demo_comparison_pair=list(DEMO_COMPARISON_PAIR),
    )


@router.post(
    "/finance/business-plan",
    response_model=BusinessPlanResponse,
    summary="Break-even, payback, tax regime and a plain-language verdict",
)
async def post_business_plan(payload: BusinessPlanRequest) -> BusinessPlanResponse:
    data = BusinessPlanInput(
        business_name=payload.business_name,
        sector_id=payload.sector_id,
        location_id=payload.location_id,
        initial_capital_som=payload.initial_capital_som,
        employee_count=payload.employee_count,
        monthly_rent_som=payload.monthly_rent_som,
        product_description=payload.product_description,
        goal=payload.goal,
        expected_monthly_revenue_som=payload.expected_monthly_revenue_som,
        is_individual_entrepreneur=payload.is_individual_entrepreneur,
    )
    try:
        plan = build_business_plan(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    comparison_item: LocationComparisonItem | None = None
    if payload.compare_location_ids:
        ids = tuple(dict.fromkeys(payload.compare_location_ids))
        try:
            comparison = compare_locations(data, ids)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        comparison_item = LocationComparisonItem(
            plans=[_plan_to_item(p) for p in comparison.plans],
            best_location_id=comparison.best_location_id,
            verdict_differs=comparison.verdict_differs,
            summary_uz=comparison.summary_uz,
        )

    return BusinessPlanResponse(plan=_plan_to_item(plan), comparison=comparison_item)


@router.post(
    "/finance/credit",
    response_model=CreditResponse,
    summary="Loan schedule, overpayment, and affordability signal",
)
async def post_credit(payload: CreditRequest) -> CreditResponse:
    try:
        result = calculate_credit(
            principal_som=payload.principal_som,
            annual_rate_pct=payload.annual_rate_pct,
            months=payload.months,
            method=payload.method,  # type: ignore[arg-type]
            grace_months=payload.grace_months,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    load_item: CreditLoadItem | None = None
    if payload.monthly_revenue_som:
        load = evaluate_credit_load(
            monthly_payment_som=result.monthly_payment_som,
            monthly_revenue_som=payload.monthly_revenue_som,
        )
        load_item = CreditLoadItem(
            load_pct=load.load_pct, level=load.level, message_uz=load.message_uz
        )

    return CreditResponse(
        principal_som=result.principal_som,
        annual_rate_pct=result.annual_rate_pct,
        months=result.months,
        method=result.method,
        grace_months=result.grace_months,
        monthly_payment_som=result.monthly_payment_som,
        last_payment_som=result.last_payment_som,
        total_payment_som=result.total_payment_som,
        total_interest_som=result.total_interest_som,
        overpayment_pct=result.overpayment_pct,
        schedule=[
            PaymentRowItem(
                month=r.month,
                payment_som=r.payment_som,
                principal_som=r.principal_som,
                interest_som=r.interest_som,
                balance_som=r.balance_som,
            )
            for r in result.schedule
        ],
        load=load_item,
    )


@router.post(
    "/finance/tax",
    response_model=TaxResponse,
    summary="Compare 2026 tax regimes and pick the cheapest eligible one",
)
async def post_tax(payload: TaxRequest) -> TaxResponse:
    try:
        comparison = calculate_tax_regimes(
            annual_revenue_som=payload.annual_revenue_som,
            annual_cost_of_goods_som=payload.annual_cost_of_goods_som,
            annual_payroll_som=payload.annual_payroll_som,
            annual_other_costs_som=payload.annual_other_costs_som,
            is_individual_entrepreneur=payload.is_individual_entrepreneur,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return TaxResponse(comparison=_tax_to_item(comparison))
