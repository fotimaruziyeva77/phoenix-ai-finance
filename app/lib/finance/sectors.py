"""Per-sector economics benchmarks for small business in Uzbekistan.

**Honesty contract:** these are *approximate planning benchmarks*, not measured
statistics. Every figure is exposed to the UI as an editable assumption so the
entrepreneur can override it with their own numbers. Never present them as
official data.

Fields:
    ``gross_margin_pct`` — revenue minus cost-of-goods, as a share of revenue
    ``avg_check_som``    — typical single-purchase amount
    ``monthly_other_costs_som`` — utilities/consumables baseline beyond rent+payroll
    ``monthly_revenue_per_employee_som`` — capacity ceiling driver; how much revenue
        one person can realistically service per month in this sector
    ``typical_payback_months`` — sanity band used only to flag outliers
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class SectorBenchmark:
    id: str
    label_uz: str
    label_ru: str
    label_en: str
    gross_margin_pct: float
    avg_check_som: int
    monthly_other_costs_som: int
    monthly_revenue_per_employee_som: int
    typical_payback_months: int
    # Sectors that unlock state preferential-credit programs (see programs.py)
    preferential_sector: bool = False


_SECTORS: tuple[SectorBenchmark, ...] = (
    SectorBenchmark(
        id="oziq_ovqat",
        label_uz="Oziq-ovqat do'koni",
        label_ru="Продуктовый магазин",
        label_en="Grocery store",
        gross_margin_pct=18.0,
        avg_check_som=45_000,
        monthly_other_costs_som=3_500_000,
        monthly_revenue_per_employee_som=90_000_000,
        typical_payback_months=14,
    ),
    SectorBenchmark(
        id="kafe",
        label_uz="Kafe / oshxona",
        label_ru="Кафе / столовая",
        label_en="Cafe",
        gross_margin_pct=35.0,
        avg_check_som=70_000,
        monthly_other_costs_som=6_000_000,
        monthly_revenue_per_employee_som=55_000_000,
        typical_payback_months=18,
    ),
    SectorBenchmark(
        id="nonvoyxona",
        label_uz="Nonvoyxona",
        label_ru="Пекарня",
        label_en="Bakery",
        gross_margin_pct=30.0,
        avg_check_som=25_000,
        monthly_other_costs_som=5_000_000,
        monthly_revenue_per_employee_som=48_000_000,
        typical_payback_months=15,
    ),
    SectorBenchmark(
        id="kiyim",
        label_uz="Kiyim do'koni",
        label_ru="Магазин одежды",
        label_en="Clothing store",
        gross_margin_pct=40.0,
        avg_check_som=250_000,
        monthly_other_costs_som=2_500_000,
        monthly_revenue_per_employee_som=60_000_000,
        typical_payback_months=16,
    ),
    SectorBenchmark(
        id="gozallik",
        label_uz="Go'zallik saloni",
        label_ru="Салон красоты",
        label_en="Beauty salon",
        gross_margin_pct=55.0,
        avg_check_som=120_000,
        monthly_other_costs_som=3_000_000,
        monthly_revenue_per_employee_som=32_000_000,
        typical_payback_months=12,
    ),
    SectorBenchmark(
        id="avtoservis",
        label_uz="Avtoservis",
        label_ru="Автосервис",
        label_en="Auto service",
        gross_margin_pct=45.0,
        avg_check_som=400_000,
        monthly_other_costs_som=4_000_000,
        monthly_revenue_per_employee_som=45_000_000,
        typical_payback_months=15,
    ),
    SectorBenchmark(
        id="chorvachilik",
        label_uz="Chorvachilik",
        label_ru="Животноводство",
        label_en="Livestock",
        gross_margin_pct=28.0,
        avg_check_som=2_500_000,
        monthly_other_costs_som=4_500_000,
        monthly_revenue_per_employee_som=30_000_000,
        typical_payback_months=24,
        preferential_sector=True,
    ),
    SectorBenchmark(
        id="parrandachilik",
        label_uz="Parrandachilik",
        label_ru="Птицеводство",
        label_en="Poultry",
        gross_margin_pct=25.0,
        avg_check_som=800_000,
        monthly_other_costs_som=4_000_000,
        monthly_revenue_per_employee_som=35_000_000,
        typical_payback_months=20,
        preferential_sector=True,
    ),
    SectorBenchmark(
        id="it_xizmat",
        label_uz="IT / raqamli xizmat",
        label_ru="IT / цифровые услуги",
        label_en="IT services",
        gross_margin_pct=65.0,
        avg_check_som=3_000_000,
        monthly_other_costs_som=2_000_000,
        monthly_revenue_per_employee_som=30_000_000,
        typical_payback_months=9,
    ),
    SectorBenchmark(
        id="yuk_tashish",
        label_uz="Yuk tashish / dostavka",
        label_ru="Грузоперевозки / доставка",
        label_en="Delivery / logistics",
        gross_margin_pct=32.0,
        avg_check_som=150_000,
        monthly_other_costs_som=5_500_000,
        monthly_revenue_per_employee_som=40_000_000,
        typical_payback_months=16,
    ),
)

SECTORS_BY_ID: MappingProxyType[str, SectorBenchmark] = MappingProxyType(
    {s.id: s for s in _SECTORS}
)


def list_sectors() -> list[SectorBenchmark]:
    """All benchmarks in catalogue order."""
    return list(_SECTORS)


def get_sector(sector_id: str) -> SectorBenchmark | None:
    return SECTORS_BY_ID.get(sector_id)
