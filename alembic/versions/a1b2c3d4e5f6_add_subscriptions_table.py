"""Add subscriptions table with plan_slug and subscription_status enums.

Revision ID: a1b2c3d4e5f6
Revises: d0e1f2a3b4c5
Create Date: 2026-04-15

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create enums idempotently ────────────────────────────────────────
    op.execute(
        "DO $$ BEGIN "
        "  CREATE TYPE plan_slug AS ENUM "
        "  ('free', 'starter', 'pro', 'business', 'enterprise'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "  CREATE TYPE subscription_status AS ENUM "
        "  ('active', 'trialing', 'past_due', 'canceled', 'expired'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )

    # ── 2. Create table using raw SQL (avoids SQLAlchemy re-emitting CREATE TYPE) ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id                      UUID PRIMARY KEY NOT NULL,
            user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            plan_slug               plan_slug NOT NULL DEFAULT 'free',
            status                  subscription_status NOT NULL DEFAULT 'active',
            stripe_customer_id      VARCHAR(64),
            stripe_subscription_id  VARCHAR(64),
            stripe_price_id         VARCHAR(64),
            current_period_start    TIMESTAMPTZ,
            current_period_end      TIMESTAMPTZ,
            canceled_at             TIMESTAMPTZ,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_subscriptions_user_id UNIQUE (user_id)
        )
    """)

    # ── 3. Indexes ─────────────────────────────────────────────────────────
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_subscriptions_user_id "
        "ON subscriptions (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_subscriptions_stripe_customer_id "
        "ON subscriptions (stripe_customer_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_subscriptions_stripe_subscription_id "
        "ON subscriptions (stripe_subscription_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS subscriptions")
    op.execute("DROP TYPE IF EXISTS subscription_status")
    op.execute("DROP TYPE IF EXISTS plan_slug")
