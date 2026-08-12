"""City / region layer: local cost baselines and location-bound incentives.

Two very different kinds of data live here, and the UI must keep them visually
separate because their trustworthiness differs:

**1. Cost baselines** (``avg_monthly_salary_som``, ``utilities_index``) — planning
   *assumptions*. They are returned to the client as editable inputs, never as facts.

**2. Legal incentives** (``tax_category``, ``incentives``) — statements about law.
   Each carries ``verified`` and ``source_note``. Anything with ``verified=False``
   must render with a "tasdiqlanishi kerak" badge and must NOT be summed into the
   headline savings figure.

Rent is deliberately absent: the entrepreneur enters their own rent, because no
reliable open dataset of district-level commercial rent exists in Uzbekistan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class LocationIncentive:
    """One location-bound benefit. ``verified`` gates it out of headline totals."""

    code: str
    title_uz: str
    detail_uz: str
    verified: bool
    source_note: str


@dataclass(frozen=True, slots=True)
class Location:
    id: str
    label_uz: str
    label_ru: str
    label_en: str
    region_uz: str
    # Planning assumption — typical SMALL-BUSINESS wage in this city (below the
    # national average, which is pulled up by large employers). Editable in the UI.
    avg_monthly_salary_som: int
    # Multiplier applied to a sector's baseline "other costs" (utilities, logistics).
    utilities_index: float
    # District development category (1 = most developed). None = not established.
    tax_category: int | None
    tax_category_verified: bool
    incentives: tuple[LocationIncentive, ...] = field(default_factory=tuple)


_TOSHKENT = Location(
    id="toshkent",
    label_uz="Toshkent shahri",
    label_ru="город Ташкент",
    label_en="Tashkent city",
    region_uz="Toshkent shahri",
    avg_monthly_salary_som=4_500_000,
    utilities_index=1.15,
    tax_category=1,
    tax_category_verified=False,
    incentives=(),
)

_NAVOIY = Location(
    id="navoiy",
    label_uz="Navoiy shahri",
    label_ru="город Навои",
    label_en="Navoi city",
    region_uz="Navoiy viloyati",
    avg_monthly_salary_som=3_400_000,
    utilities_index=0.90,
    tax_category=None,
    tax_category_verified=False,
    incentives=(
        LocationIncentive(
            code="navoi_fez",
            title_uz="Navoiy erkin iqtisodiy zonasi",
            detail_uz=(
                "Navoiyda erkin iqtisodiy zona faoliyat yuritadi. Rezident maqomini "
                "olgan loyihalar uchun soliq va bojxona imtiyozlari nazarda tutilgan. "
                "Shartlari loyiha turi va investitsiya hajmiga bog'liq."
            ),
            verified=False,
            source_note="EIZ rezidentligi shartlari alohida tekshirilishi kerak",
        ),
    ),
)

_SAMARQAND = Location(
    id="samarqand",
    label_uz="Samarqand shahri",
    label_ru="город Самарканд",
    label_en="Samarkand city",
    region_uz="Samarqand viloyati",
    avg_monthly_salary_som=3_600_000,
    utilities_index=0.95,
    tax_category=None,
    tax_category_verified=False,
)

_BUXORO = Location(
    id="buxoro",
    label_uz="Buxoro shahri",
    label_ru="город Бухара",
    label_en="Bukhara city",
    region_uz="Buxoro viloyati",
    avg_monthly_salary_som=3_400_000,
    utilities_index=0.92,
    tax_category=None,
    tax_category_verified=False,
)

_LOCATIONS: tuple[Location, ...] = (_TOSHKENT, _NAVOIY, _SAMARQAND, _BUXORO)

LOCATIONS_BY_ID: MappingProxyType[str, Location] = MappingProxyType(
    {loc.id: loc for loc in _LOCATIONS}
)

#: Pair the demo highlights — same business, two cities, two verdicts.
DEMO_COMPARISON_PAIR: tuple[str, str] = ("toshkent", "navoiy")


def list_locations() -> list[Location]:
    return list(_LOCATIONS)


def get_location(location_id: str) -> Location | None:
    return LOCATIONS_BY_ID.get(location_id)


def monthly_staff_cost(location: Location, employee_count: int) -> int:
    """Gross monthly payroll baseline for ``employee_count`` staff in this city."""
    if employee_count <= 0:
        return 0
    return location.avg_monthly_salary_som * employee_count
