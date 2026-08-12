#!/usr/bin/env python3
"""
Resettable seed data for real-stack Playwright E2E (PostgreSQL + app schema).

Creates a dedicated workspace user, two bots (support + sales), widget config with an open
allowlist (empty = MVP permissive mode), and one CRM lead row for dashboard verification.

Prerequisites:
  - DATABASE_URL (async URL, e.g. postgresql+asyncpg://user:pass@host:5432/db)
  - JWT_SECRET_KEY (any 32+ char secret for app settings load)
  - Alembic migrations applied

Usage:
  python scripts/seed_e2e_stack.py [--output PATH]

Environment:
  E2E_SEED_EMAIL     default: e2e-stack@botforge.test
  E2E_SEED_PASSWORD  default: E2E_Stack_Seed_Pass_123!
  E2E_SEED_FULL_NAME default: E2E Stack User
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

DEFAULT_EMAIL = "e2e-stack@botforge.test"
DEFAULT_PASSWORD = "E2E_Stack_Seed_Pass_123!"
DEFAULT_FULL_NAME = "E2E Stack User"
SUPPORT_BOT_NAME = "E2E Seeded Support Bot"
SALES_BOT_NAME = "E2E Seeded Sales Bot"
LEAD_NAME = "E2E Seeded Lead"


async def _run(*, output_path: Path) -> int:
    database_url = (os.environ.get("DATABASE_URL") or os.environ.get("APP_DATABASE_URL") or "").strip()
    if not database_url:
        print("DATABASE_URL (or APP_DATABASE_URL) is required.", file=sys.stderr)
        return 2
    if not (os.environ.get("JWT_SECRET_KEY") or "").strip():
        print("JWT_SECRET_KEY is required for settings load.", file=sys.stderr)
        return 2

    email = (os.environ.get("E2E_SEED_EMAIL") or DEFAULT_EMAIL).strip().lower()
    password = os.environ.get("E2E_SEED_PASSWORD") or DEFAULT_PASSWORD
    full_name = (os.environ.get("E2E_SEED_FULL_NAME") or DEFAULT_FULL_NAME).strip()

    os.environ.setdefault("DATABASE_URL", database_url)

    from app.core.config import get_settings
    from app.core.db import dispose_engine, get_session_maker
    from app.core.security import hash_password
    from app.lib.email_normalize import normalize_email
    from app.models.enums import UserRole
    from app.models.user import User
    from app.models.widget_config import WidgetConfig, new_public_widget_key
    from app.repositories.bot_repository import BotRepository
    from app.repositories.lead_repository import LeadRepository
    from sqlalchemy import select

    get_settings.cache_clear()
    get_settings()

    norm_email = normalize_email(email)
    sm = get_session_maker()

    try:
        async with sm() as session:
            existing = (
                await session.execute(select(User).where(User.email == norm_email).limit(1))
            ).scalar_one_or_none()
            if existing is not None:
                await session.delete(existing)
                await session.commit()

            user = User(
                email=norm_email,
                password_hash=hash_password(password),
                full_name=full_name or None,
                role=UserRole.customer_admin,
                is_active=True,
                is_verified=True,
            )
            session.add(user)
            await session.flush()

            bots = BotRepository(session)
            support = await bots.create_bot(
                owner_id=user.id,
                name=SUPPORT_BOT_NAME,
                niche_id="education",
                goal_type="support",
                status="draft",
            )
            sales = await bots.create_bot(
                owner_id=user.id,
                name=SALES_BOT_NAME,
                niche_id="services",
                goal_type="sales",
                status="draft",
            )

            wc = WidgetConfig(
                bot_id=support.id,
                owner_id=user.id,
                public_widget_key=new_public_widget_key(),
                is_enabled=True,
                allowed_domains_json=[],
            )
            session.add(wc)

            leads = LeadRepository(session)
            await leads.create_lead(
                bot_id=sales.id,
                owner_id=user.id,
                conversation_id=None,
                niche_id="services",
                lead_score=72,
                lead_temperature="warm",
                summary="Seeded lead for E2E dashboard verification.",
                source_channel="e2e_seed",
                collected_data_json=None,
                phone="+15555550199",
                name=LEAD_NAME,
                status="new",
            )

            await session.commit()
            await session.refresh(user)
            await session.refresh(support)
            await session.refresh(sales)
            await session.refresh(wc)

            payload = {
                "email": norm_email,
                "password": password,
                "full_name": full_name,
                "user_id": str(user.id),
                "support_bot_id": str(support.id),
                "sales_bot_id": str(sales.id),
                "support_bot_name": SUPPORT_BOT_NAME,
                "sales_bot_name": SALES_BOT_NAME,
                "widget_public_key": wc.public_widget_key,
                "lead_name": LEAD_NAME,
            }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {output_path}")
        return 0
    finally:
        await dispose_engine()
        get_settings.cache_clear()


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed E2E workspace data for Playwright real-stack tests.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("frontend/e2e/real-stack/seed-output.json"),
        help="JSON file consumed by Playwright (default: frontend/e2e/real-stack/seed-output.json).",
    )
    args = parser.parse_args()
    return asyncio.run(_run(output_path=args.output.resolve()))


if __name__ == "__main__":
    raise SystemExit(main())
