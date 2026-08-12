"""Coupon / promo code schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CouponRead(BaseModel):
    id:             UUID
    code:           str
    discount_type:  str
    discount_value: Decimal
    target_plan:    str | None = None
    max_uses:       int | None = None
    used_count:     int
    is_active:      bool
    expires_at:     datetime | None = None
    created_by_id:  UUID | None = None
    created_at:     datetime
    updated_at:     datetime


class CouponListResponse(BaseModel):
    items: list[CouponRead]
    total: int = Field(ge=0)


class CouponCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code:           str = Field(..., min_length=3, max_length=32, pattern=r"^[A-Z0-9_\-]+$",
                                description="Uppercase alphanumeric code, e.g. LAUNCH50.")
    discount_type:  str = Field(..., pattern="^(percent|usd)$")
    discount_value: Decimal = Field(..., gt=0, le=100000)
    target_plan:    str | None = Field(default=None)
    max_uses:       int | None = Field(default=None, ge=1)
    expires_at:     datetime | None = Field(default=None)


class CouponUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active:     bool | None = None
    max_uses:      int | None = Field(default=None, ge=1)
    expires_at:    datetime | None = None
    clear_expires: bool = False


class CouponApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(..., min_length=1, max_length=32)


class CouponApplyResponse(BaseModel):
    code:           str
    discount_type:  str
    discount_value: Decimal
    target_plan:    str | None = None
    message:        str
