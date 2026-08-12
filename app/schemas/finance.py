"""Request/response contracts for the finance advisory endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

# --- catalogue ---


class SectorItem(BaseModel):
    id: str
    label_uz: str
    label_ru: str
    label_en: str
    gross_margin_pct: float
    avg_check_som: int
    preferential_sector: bool


class LocationIncentiveItem(BaseModel):
    code: str
    title_uz: str
    detail_uz: str
    verified: bool
    source_note: str


class LocationItem(BaseModel):
    id: str
    label_uz: str
    label_ru: str
    label_en: str
    region_uz: str
    avg_monthly_salary_som: int
    tax_category: int | None
    tax_category_verified: bool
    incentives: list[LocationIncentiveItem]


class FinanceCatalogResponse(BaseModel):
    schema_version: int = 1
    data_as_of: str
    sectors: list[SectorItem]
    locations: list[LocationItem]
    demo_comparison_pair: list[str]


# --- business plan ---


class BusinessPlanRequest(BaseModel):
    business_name: str = Field(min_length=1, max_length=200)
    sector_id: str
    location_id: str
    initial_capital_som: int = Field(ge=0, le=1_000_000_000_000)
    employee_count: int = Field(ge=0, le=1000)
    monthly_rent_som: int = Field(ge=0, le=10_000_000_000)
    product_description: str = Field(default="", max_length=2000)
    goal: str = Field(default="", max_length=2000)
    expected_monthly_revenue_som: int | None = Field(default=None, ge=0)
    is_individual_entrepreneur: bool = True
    #: When set, the same plan is recomputed for these cities too.
    compare_location_ids: list[str] | None = None


class AssumptionItem(BaseModel):
    key: str
    label_uz: str
    value_som: int | None
    value_text: str
    editable: bool


class TaxRegimeItem(BaseModel):
    regime: str
    label_uz: str
    eligible: bool
    ineligible_reason_uz: str | None
    annual_tax_som: int
    monthly_tax_som: int
    effective_rate_pct: float
    breakdown_uz: list[tuple[str, int]]


class TaxComparisonItem(BaseModel):
    annual_revenue_som: int
    results: list[TaxRegimeItem]
    cheapest_regime: str | None
    savings_vs_worst_som: int
    disclaimer_uz: str


class BusinessPlanItem(BaseModel):
    business_name: str
    sector_id: str
    sector_label_uz: str
    location_id: str
    location_label_uz: str

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

    verdict: str
    verdict_title_uz: str
    verdict_reasons_uz: list[str]
    recommendations_uz: list[str]
    assumptions: list[AssumptionItem]
    tax: TaxComparisonItem


class LocationComparisonItem(BaseModel):
    plans: list[BusinessPlanItem]
    best_location_id: str
    verdict_differs: bool
    summary_uz: str


class BusinessPlanResponse(BaseModel):
    schema_version: int = 1
    plan: BusinessPlanItem
    comparison: LocationComparisonItem | None = None


# --- credit ---


class CreditRequest(BaseModel):
    principal_som: int = Field(gt=0, le=1_000_000_000_000)
    annual_rate_pct: float = Field(ge=0, le=200)
    months: int = Field(gt=0, le=480)
    method: str = Field(default="annuity", pattern="^(annuity|differentiated)$")
    grace_months: int = Field(default=0, ge=0, le=120)
    monthly_revenue_som: int | None = Field(default=None, ge=0)


class PaymentRowItem(BaseModel):
    month: int
    payment_som: int
    principal_som: int
    interest_som: int
    balance_som: int


class CreditLoadItem(BaseModel):
    load_pct: float
    level: str
    message_uz: str


class CreditResponse(BaseModel):
    schema_version: int = 1
    principal_som: int
    annual_rate_pct: float
    months: int
    method: str
    grace_months: int
    monthly_payment_som: int
    last_payment_som: int
    total_payment_som: int
    total_interest_som: int
    overpayment_pct: float
    schedule: list[PaymentRowItem]
    load: CreditLoadItem | None = None


# --- tax ---


class TaxRequest(BaseModel):
    annual_revenue_som: int = Field(ge=0, le=1_000_000_000_000)
    annual_cost_of_goods_som: int = Field(default=0, ge=0)
    annual_payroll_som: int = Field(default=0, ge=0)
    annual_other_costs_som: int = Field(default=0, ge=0)
    is_individual_entrepreneur: bool = True


class TaxResponse(BaseModel):
    schema_version: int = 1
    comparison: TaxComparisonItem
