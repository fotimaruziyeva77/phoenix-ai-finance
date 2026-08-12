"""Loan math: annuity and differentiated schedules, plus affordability signals.

Deterministic arithmetic only. ``Decimal`` is used throughout so the monthly
payment shown to an entrepreneur matches what a bank's own calculator produces.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

CreditMethod = Literal["annuity", "differentiated"]

#: Monthly payment above this share of revenue is flagged as dangerous.
CREDIT_LOAD_DANGER_PCT = 30.0
#: Monthly payment above this share of revenue is flagged as tight.
CREDIT_LOAD_WARNING_PCT = 20.0


def _round_som(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


@dataclass(frozen=True, slots=True)
class PaymentRow:
    month: int
    payment_som: int
    principal_som: int
    interest_som: int
    balance_som: int


@dataclass(frozen=True, slots=True)
class CreditResult:
    principal_som: int
    annual_rate_pct: float
    months: int
    method: CreditMethod
    grace_months: int
    monthly_payment_som: int
    """First (annuity: every) monthly payment."""
    last_payment_som: int
    total_payment_som: int
    total_interest_som: int
    overpayment_pct: float
    schedule: tuple[PaymentRow, ...]


def calculate_credit(
    *,
    principal_som: int,
    annual_rate_pct: float,
    months: int,
    method: CreditMethod = "annuity",
    grace_months: int = 0,
) -> CreditResult:
    """Build a full repayment schedule.

    ``grace_months`` repays interest only (principal untouched) — this is how
    Uzbek preferential programs structure their first year.
    """
    if principal_som <= 0:
        raise ValueError("principal_som must be positive")
    if months <= 0:
        raise ValueError("months must be positive")
    if annual_rate_pct < 0:
        raise ValueError("annual_rate_pct cannot be negative")
    if grace_months < 0 or grace_months >= months:
        raise ValueError("grace_months must be >= 0 and < months")

    principal = Decimal(principal_som)
    monthly_rate = Decimal(str(annual_rate_pct)) / Decimal(1200)
    repay_months = months - grace_months

    rows: list[PaymentRow] = []
    balance = principal

    for month in range(1, grace_months + 1):
        interest = balance * monthly_rate
        rows.append(
            PaymentRow(
                month=month,
                payment_som=_round_som(interest),
                principal_som=0,
                interest_som=_round_som(interest),
                balance_som=_round_som(balance),
            )
        )

    if method == "annuity":
        if monthly_rate == 0:
            annuity = principal / Decimal(repay_months)
        else:
            factor = (Decimal(1) + monthly_rate) ** repay_months
            annuity = principal * monthly_rate * factor / (factor - Decimal(1))
        for idx in range(1, repay_months + 1):
            interest = balance * monthly_rate
            principal_part = annuity - interest
            if idx == repay_months:
                principal_part = balance
                annuity_row = principal_part + interest
            else:
                annuity_row = annuity
            balance -= principal_part
            rows.append(
                PaymentRow(
                    month=grace_months + idx,
                    payment_som=_round_som(annuity_row),
                    principal_som=_round_som(principal_part),
                    interest_som=_round_som(interest),
                    balance_som=_round_som(max(balance, Decimal(0))),
                )
            )
    else:
        principal_part = principal / Decimal(repay_months)
        for idx in range(1, repay_months + 1):
            interest = balance * monthly_rate
            part = balance if idx == repay_months else principal_part
            balance -= part
            rows.append(
                PaymentRow(
                    month=grace_months + idx,
                    payment_som=_round_som(part + interest),
                    principal_som=_round_som(part),
                    interest_som=_round_som(interest),
                    balance_som=_round_som(max(balance, Decimal(0))),
                )
            )

    total_payment = sum(r.payment_som for r in rows)
    total_interest = sum(r.interest_som for r in rows)
    first_repay = rows[grace_months] if len(rows) > grace_months else rows[0]

    return CreditResult(
        principal_som=principal_som,
        annual_rate_pct=annual_rate_pct,
        months=months,
        method=method,
        grace_months=grace_months,
        monthly_payment_som=first_repay.payment_som,
        last_payment_som=rows[-1].payment_som,
        total_payment_som=total_payment,
        total_interest_som=total_interest,
        overpayment_pct=round(total_interest / principal_som * 100, 2),
        schedule=tuple(rows),
    )


@dataclass(frozen=True, slots=True)
class CreditLoad:
    monthly_payment_som: int
    monthly_revenue_som: int
    load_pct: float
    level: Literal["safe", "warning", "danger"]
    message_uz: str


def evaluate_credit_load(*, monthly_payment_som: int, monthly_revenue_som: int) -> CreditLoad:
    """How much of monthly revenue the loan eats — the number banks never show."""
    if monthly_revenue_som <= 0:
        return CreditLoad(
            monthly_payment_som=monthly_payment_som,
            monthly_revenue_som=monthly_revenue_som,
            load_pct=100.0,
            level="danger",
            message_uz="Daromad kiritilmagan — kredit yukini baholab bo'lmaydi.",
        )
    load = round(monthly_payment_som / monthly_revenue_som * 100, 1)
    if load >= CREDIT_LOAD_DANGER_PCT:
        level: Literal["safe", "warning", "danger"] = "danger"
        msg = (
            f"Oylik to'lov aylanmangizning {load}% ini oladi. Bu xavfli zona — "
            "kredit summasini kamaytiring yoki muddatni uzaytiring."
        )
    elif load >= CREDIT_LOAD_WARNING_PCT:
        level = "warning"
        msg = (
            f"Oylik to'lov aylanmangizning {load}% ini oladi. Bu chegara zona — "
            "daromad biroz tushsa to'lovda qiynalasiz."
        )
    else:
        level = "safe"
        msg = f"Oylik to'lov aylanmangizning {load}% ini oladi. Bu xavfsiz daraja."
    return CreditLoad(
        monthly_payment_som=monthly_payment_som,
        monthly_revenue_som=monthly_revenue_som,
        load_pct=load,
        level=level,
        message_uz=msg,
    )


def compare_rates(
    *, principal_som: int, months: int, rate_a_pct: float, rate_b_pct: float
) -> dict[str, int | float]:
    """Total-cost delta between two offers — the '14% vs 28%' headline."""
    a = calculate_credit(principal_som=principal_som, annual_rate_pct=rate_a_pct, months=months)
    b = calculate_credit(principal_som=principal_som, annual_rate_pct=rate_b_pct, months=months)
    return {
        "rate_a_pct": rate_a_pct,
        "rate_b_pct": rate_b_pct,
        "monthly_a_som": a.monthly_payment_som,
        "monthly_b_som": b.monthly_payment_som,
        "total_a_som": a.total_payment_som,
        "total_b_som": b.total_payment_som,
        "savings_som": a.total_payment_som - b.total_payment_som,
    }
