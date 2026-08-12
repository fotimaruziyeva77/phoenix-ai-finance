"""Billing endpoints — plan catalogue, subscription status, Stripe checkout/portal/webhook."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel

from app.api.deps import (
    BillingServiceDep,
    CurrentUser,
    DbSession,
    SettingsDep,
    rate_limit_billing_checkout,
)
from app.repositories.webhook_log_repository import WebhookLogRepository
from app.services.billing_exceptions import (
    AlreadyOnPlanError,
    BillingError,
    InvalidStripeWebhookError,
    PlanNotFoundError,
    StripeNotConfiguredError,
)
from app.services.plan_limits import get_all_plans, get_plan

router = APIRouter(tags=["billing"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class PlanResponse(BaseModel):
    slug: str
    name: str
    price_cents: int
    price_dollars: float
    tagline: str
    is_popular: bool
    conversations_per_month: int | None
    bots_max: int | None
    pdf_files_max: int | None
    storage_mb: int | None
    telegram_allowed: bool
    analytics_detailed: bool
    show_branding: bool

    model_config = {"from_attributes": True}


class SubscriptionResponse(BaseModel):
    plan_slug: str
    plan_name: str
    status: str
    price_cents: int
    price_dollars: float
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    current_period_end: str | None  # ISO 8601
    canceled_at: str | None

    model_config = {"from_attributes": True}


class CheckoutRequest(BaseModel):
    plan_slug: str
    success_url: str | None = None
    cancel_url: str | None = None


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


# ---------------------------------------------------------------------------
# Plan catalogue (public)
# ---------------------------------------------------------------------------


@router.get(
    "/billing/plans",
    response_model=list[PlanResponse],
    summary="List all available subscription plans",
)
async def list_plans() -> list[PlanResponse]:
    """
    Public endpoint — returns all plans ordered FREE → ENTERPRISE.
    No authentication required.
    """
    return [
        PlanResponse(
            slug=p.slug,
            name=p.name,
            price_cents=p.price_cents,
            price_dollars=p.price_dollars(),
            tagline=p.tagline,
            is_popular=p.is_popular,
            conversations_per_month=p.conversations_per_month,
            bots_max=p.bots_max,
            pdf_files_max=p.pdf_files_max,
            storage_mb=p.storage_mb,
            telegram_allowed=p.telegram_allowed,
            analytics_detailed=p.analytics_detailed,
            show_branding=p.show_branding,
        )
        for p in get_all_plans()
    ]


# ---------------------------------------------------------------------------
# Current user subscription
# ---------------------------------------------------------------------------


@router.get(
    "/billing/subscription",
    response_model=SubscriptionResponse,
    summary="Get the current user's active subscription",
)
async def get_subscription(
    user: CurrentUser,
    billing_service: BillingServiceDep,
) -> SubscriptionResponse:
    """Returns the authenticated user's subscription, auto-provisioning FREE if absent."""
    sub = await billing_service.get_or_create_subscription(user)
    plan = get_plan(sub.plan_slug.value)
    return SubscriptionResponse(
        plan_slug=sub.plan_slug.value,
        plan_name=plan.name,
        status=sub.status.value,
        price_cents=plan.price_cents,
        price_dollars=plan.price_dollars(),
        stripe_customer_id=sub.stripe_customer_id,
        stripe_subscription_id=sub.stripe_subscription_id,
        current_period_end=(
            sub.current_period_end.isoformat() if sub.current_period_end else None
        ),
        canceled_at=(sub.canceled_at.isoformat() if sub.canceled_at else None),
    )


# ---------------------------------------------------------------------------
# Stripe Checkout
# ---------------------------------------------------------------------------


@router.post(
    "/billing/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Create a Stripe Checkout session to upgrade plan",
    dependencies=[Depends(rate_limit_billing_checkout)],
)
async def create_checkout(
    user: CurrentUser,
    body: CheckoutRequest,
    billing_service: BillingServiceDep,
    settings: SettingsDep,
) -> CheckoutResponse:
    """
    Creates a Stripe Checkout session for the requested plan.
    Returns ``checkout_url`` — redirect the user there to complete payment.

    Raises **402** if Stripe is not configured.
    Raises **404** if the plan slug is invalid.
    Raises **409** if already on that plan.
    """
    frontend_url = settings.frontend_base_url.rstrip("/")
    success_url = body.success_url or f"{frontend_url}/dashboard/billing?status=success"
    cancel_url = body.cancel_url or f"{frontend_url}/dashboard/billing?status=canceled"

    checkout_url = await billing_service.create_checkout_session(
        user,
        body.plan_slug,
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return CheckoutResponse(checkout_url=checkout_url)


# ---------------------------------------------------------------------------
# Stripe Customer Portal
# ---------------------------------------------------------------------------


@router.post(
    "/billing/portal",
    response_model=PortalResponse,
    status_code=status.HTTP_200_OK,
    summary="Create a Stripe Customer Portal session to manage billing",
)
async def create_portal(
    user: CurrentUser,
    billing_service: BillingServiceDep,
    settings: SettingsDep,
) -> PortalResponse:
    """
    Creates a Stripe Customer Portal session.
    Returns ``portal_url`` — redirect the user there to manage invoices, cancel, etc.

    Raises **503** if Stripe is not configured or user has no Stripe customer.
    """
    return_url = f"{settings.frontend_base_url.rstrip('/')}/dashboard/billing"
    portal_url = await billing_service.create_portal_session(user, return_url=return_url)
    return PortalResponse(portal_url=portal_url)


# ---------------------------------------------------------------------------
# Stripe Webhook  (raw body — no auth, verified by signature)
# ---------------------------------------------------------------------------


@router.post(
    "/billing/webhook/stripe",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Stripe webhook receiver (Stripe → backend)",
    include_in_schema=False,  # Keep out of public docs
)
async def stripe_webhook(
    request: Request,
    billing_service: BillingServiceDep,
    session: DbSession,
    stripe_signature: Annotated[str | None, Header(alias="stripe-signature")] = None,
) -> Response:
    """
    Stripe sends signed webhook events here.
    Verifies ``Stripe-Signature`` header, then processes the event.

    **Important:** Stripe requires the raw request body for signature verification.
    Do NOT parse the body through Pydantic before passing to the service.
    """
    import json as _json
    payload = await request.body()
    sig = stripe_signature or ""

    # Extract event_type for logging (best-effort, don't fail on parse error)
    event_type: str | None = None
    payload_preview: dict | None = None
    try:
        parsed = _json.loads(payload[:2048])
        event_type = parsed.get("type")
        payload_preview = {"type": event_type, "id": parsed.get("id"), "livemode": parsed.get("livemode")}
    except Exception:  # noqa: BLE001
        pass

    wh_repo = WebhookLogRepository(session)
    log_status = "processed"
    error_msg: str | None = None

    try:
        await billing_service.handle_stripe_webhook(payload, sig)
    except Exception as exc:  # noqa: BLE001
        log_status = "failed"
        error_msg = str(exc)[:500]
        raise
    finally:
        from datetime import UTC, datetime
        try:
            await wh_repo.create(
                source="stripe",
                event_type=event_type,
                status=log_status,
                error_message=error_msg,
                payload_preview=payload_preview,
                processed_at=datetime.now(UTC),
            )
            await wh_repo.commit()
        except Exception:  # noqa: BLE001
            pass  # Never fail the webhook because of logging

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Exception handlers registered via FastAPI app (wire in main.py)
# Public helper to map BillingError → HTTP
# ---------------------------------------------------------------------------


def billing_error_to_http(exc: BillingError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message},
    )
