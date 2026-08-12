"""TOTP two-factor authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, TotpServiceDep

router = APIRouter(tags=["auth-2fa"])


# ── Request / Response schemas ──────────────────────────────────────────────


class TotpStatusResponse(BaseModel):
    is_configured: bool
    is_active: bool


class TotpSetupResponse(BaseModel):
    secret: str = Field(description="Base32 TOTP secret (show once, then discard).")
    provisioning_uri: str = Field(description="otpauth:// URI for QR code generation.")
    recovery_codes: list[str] = Field(description="One-time recovery codes (show once).")


class TotpCodeRequest(BaseModel):
    code: str = Field(min_length=6, max_length=8, description="6-digit TOTP code or recovery code.")


class TotpActivateResponse(BaseModel):
    activated: bool = True


class TotpVerifyResponse(BaseModel):
    verified: bool = True


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.get(
    "/2fa/status",
    response_model=TotpStatusResponse,
    summary="Check 2FA status for current user",
)
async def get_2fa_status(
    user: CurrentUser,
    totp_service: TotpServiceDep,
) -> TotpStatusResponse:
    data = await totp_service.get_totp_status(user.id)
    return TotpStatusResponse(**data)


@router.post(
    "/2fa/setup",
    response_model=TotpSetupResponse,
    summary="Generate TOTP secret and recovery codes",
    description="Returns a TOTP secret, provisioning URI (for QR code), and recovery codes. "
    "Must call /2fa/activate with a valid code to finalize.",
)
async def setup_2fa(
    user: CurrentUser,
    totp_service: TotpServiceDep,
) -> TotpSetupResponse:
    data = await totp_service.setup_totp(user.id, user.email)
    return TotpSetupResponse(**data)


@router.post(
    "/2fa/activate",
    response_model=TotpActivateResponse,
    summary="Activate 2FA by verifying the first TOTP code",
)
async def activate_2fa(
    body: TotpCodeRequest,
    user: CurrentUser,
    totp_service: TotpServiceDep,
) -> TotpActivateResponse:
    await totp_service.activate_totp(user.id, body.code)
    return TotpActivateResponse()


@router.post(
    "/2fa/verify",
    response_model=TotpVerifyResponse,
    summary="Verify a TOTP code (login step 2 or authenticated verification)",
)
async def verify_2fa(
    body: TotpCodeRequest,
    user: CurrentUser,
    totp_service: TotpServiceDep,
) -> TotpVerifyResponse:
    await totp_service.verify_totp(user.id, body.code)
    return TotpVerifyResponse()


@router.delete(
    "/2fa",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disable 2FA for current user",
)
async def disable_2fa(
    user: CurrentUser,
    totp_service: TotpServiceDep,
) -> None:
    await totp_service.disable_totp(user.id)
