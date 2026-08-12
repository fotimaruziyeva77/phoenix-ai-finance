"""Superadmin abuse / high-usage detection (Feature 12)."""

from __future__ import annotations

import asyncio
from decimal import Decimal

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.deps import AbuseDetectionRepoDep, AdminModerationServiceDep, RequireSuperadmin

router = APIRouter(prefix="/admin/abuse", tags=["admin-abuse"])


class AbuseUserDto(BaseModel):
    owner_id: str
    owner_email: str
    total_calls: int
    failed_calls: int
    total_tokens: int
    total_cost_usd: Decimal
    error_rate: float


class ErrorCodeDto(BaseModel):
    owner_id: str
    owner_email: str
    error_code: str
    occurrences: int


class AbuseReportResponse(BaseModel):
    high_usage: list[AbuseUserDto]
    top_errors: list[ErrorCodeDto]
    threshold_calls: int
    period_days: int


@router.get(
    "/report",
    response_model=AbuseReportResponse,
    summary="High-usage & error-rate abuse report (superadmin)",
)
async def get_abuse_report(
    _admin: RequireSuperadmin,
    repo: AbuseDetectionRepoDep,
    threshold_calls: int = Query(default=500, ge=1),
    days: int = Query(default=1, ge=1, le=30),
    limit: int = Query(default=50, ge=1, le=200),
) -> AbuseReportResponse:
    # Both queries use the same `days` window — consistent reporting
    high_usage, top_errors = await asyncio.gather(
        repo.high_usage_users(threshold_calls=threshold_calls, days=days, limit=limit),
        repo.top_error_codes(days=days),
    )
    return AbuseReportResponse(
        high_usage=[
            AbuseUserDto(
                owner_id=u.owner_id,
                owner_email=u.owner_email,
                total_calls=u.total_calls,
                failed_calls=u.failed_calls,
                total_tokens=u.total_tokens,
                total_cost_usd=u.total_cost_usd,
                error_rate=u.error_rate,
            )
            for u in high_usage
        ],
        top_errors=[
            ErrorCodeDto(
                owner_id=e.owner_id,
                owner_email=e.owner_email,
                error_code=e.error_code,
                occurrences=e.occurrences,
            )
            for e in top_errors
        ],
        threshold_calls=threshold_calls,
        period_days=days,
    )
