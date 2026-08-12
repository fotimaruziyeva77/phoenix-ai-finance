"""
AI foundation migration verification (schema + Alembic head + FK rules).
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from app.core.config import get_settings
from app.core.db import normalize_database_url
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.integration_db import integration_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _integration_db_url() -> str | None:
    return integration_database_url()


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _integration_db_url(),
        reason=(
            "Set TEST_DATABASE_URL (recommended) or host-reachable DATABASE_URL "
            "(not @postgres: — use 127.0.0.1 when testing from the host)."
        ),
    ),
]


def _alembic_upgrade_head(url: str) -> None:
    prev = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    try:
        cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
        command.upgrade(cfg, "head")
    finally:
        if prev is not None:
            os.environ["DATABASE_URL"] = prev
        else:
            os.environ.pop("DATABASE_URL", None)
        get_settings.cache_clear()


@pytest.fixture(scope="module", autouse=True)
def _alembic_for_ai_foundation_migration_tests() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


def test_ai_foundation_migration_applies_to_script_head(live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    async def body() -> None:
        cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
        expected_head = ScriptDirectory.from_config(cfg).get_current_head()
        engine = create_async_engine(normalize_database_url(live_db_url), pool_pre_ping=True)
        try:
            async with engine.connect() as conn:
                row = (await conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))).first()
                version = str(row[0]) if row else None
        finally:
            await engine.dispose()
        assert version == expected_head

    monkeypatch.setenv("DATABASE_URL", live_db_url)
    get_settings.cache_clear()
    asyncio.run(body())


@pytest.mark.parametrize(
    "table_name,expected_columns",
    [
        (
            "conversations",
            [
                "id",
                "bot_id",
                "owner_id",
                "channel",
                "status",
                "created_at",
                "updated_at",
                "current_state",
                "detected_intent",
                "niche_id_snapshot",
                "collected_data_json",
                "last_user_message_at",
                "last_assistant_message_at",
                "public_visitor_session_key",
                "visitor_client_hint",
            ],
        ),
        (
            "messages",
            [
                "id",
                "conversation_id",
                "bot_id",
                "role",
                "content",
                "tokens_input",
                "tokens_output",
                "tokens_total",
                "latency_ms",
                "cost_usd",
                "model_name",
                "created_at",
            ],
        ),
        (
            "ai_usage_logs",
            [
                "id",
                "bot_id",
                "conversation_id",
                "message_id",
                "provider_name",
                "model_name",
                "tokens_input",
                "tokens_output",
                "tokens_total",
                "latency_ms",
                "cost_usd",
                "success",
                "error_code",
                "created_at",
            ],
        ),
        (
            "daily_ai_usage_aggregates",
            [
                "id",
                "bot_id",
                "usage_date",
                "total_requests",
                "total_tokens",
                "total_cost_usd",
                "avg_latency_ms",
            ],
        ),
        (
            "leads",
            [
                "id",
                "bot_id",
                "owner_id",
                "conversation_id",
                "niche_id",
                "lead_score",
                "lead_temperature",
                "status",
                "name",
                "phone",
                "summary",
                "source_channel",
                "collected_data_json",
                "created_at",
                "updated_at",
                "notes",
            ],
        ),
    ],
)
def test_ai_foundation_table_columns_exist(
    live_db_url: str,
    table_name: str,
    expected_columns: list[str],
) -> None:
    async def body() -> None:
        engine = create_async_engine(normalize_database_url(live_db_url), pool_pre_ping=True)
        try:
            async with engine.connect() as conn:
                result = await conn.execute(
                    text(
                        """
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema='public' AND table_name=:t
                        ORDER BY ordinal_position
                        """
                    ),
                    {"t": table_name},
                )
                col_names = [str(row[0]) for row in result.fetchall()]
                assert col_names == expected_columns, (table_name, col_names)
        finally:
            await engine.dispose()

    asyncio.run(body())


def test_ai_foundation_check_constraints_exist(live_db_url: str) -> None:
    async def body() -> None:
        engine = create_async_engine(normalize_database_url(live_db_url), pool_pre_ping=True)
        try:
            async with engine.connect() as conn:
                checks = await conn.execute(
                    text(
                        """
                        SELECT t.relname, c.conname
                        FROM pg_constraint c
                        JOIN pg_class t ON c.conrelid = t.oid
                        JOIN pg_namespace n ON n.oid = t.relnamespace AND n.nspname = 'public'
                        WHERE c.contype = 'c'
                        AND t.relname IN ('conversations', 'messages')
                        ORDER BY t.relname, c.conname
                        """
                    )
                )
                rows = {(str(r[0]), str(r[1])) for r in checks.fetchall()}
                assert ("conversations", "ck_conversations_status_allowed") in rows
                assert ("conversations", "ck_conversations_current_state_allowed") in rows
                assert ("conversations", "ck_conversations_detected_intent_allowed") in rows
                assert ("conversations", "ck_conversations_web_widget_requires_visitor_key") in rows
                assert ("messages", "ck_messages_role_allowed") in rows

                uq = await conn.execute(
                    text(
                        """
                        SELECT conname FROM pg_constraint c
                        JOIN pg_class t ON c.conrelid = t.oid
                        JOIN pg_namespace n ON n.oid = t.relnamespace AND n.nspname = 'public'
                        WHERE c.contype = 'u' AND t.relname = 'daily_ai_usage_aggregates'
                        """
                    )
                )
                assert any("uq_daily_ai_usage_bot_date" in str(r[0]) for r in uq.fetchall())
        finally:
            await engine.dispose()

    asyncio.run(body())


def test_ai_foundation_foreign_key_delete_rules(live_db_url: str) -> None:
    """PostgreSQL FK ON DELETE matches migration (CASCADE vs SET NULL)."""
    expected = {
        ("ai_usage_logs", "bot_id"): "CASCADE",
        ("ai_usage_logs", "conversation_id"): "SET NULL",
        ("ai_usage_logs", "message_id"): "SET NULL",
        ("conversations", "bot_id"): "CASCADE",
        ("conversations", "owner_id"): "CASCADE",
        ("daily_ai_usage_aggregates", "bot_id"): "CASCADE",
        ("messages", "bot_id"): "CASCADE",
        ("messages", "conversation_id"): "CASCADE",
    }

    async def body() -> None:
        engine = create_async_engine(normalize_database_url(live_db_url), pool_pre_ping=True)
        try:
            async with engine.connect() as conn:
                result = await conn.execute(
                    text(
                        """
                        SELECT
                          kcu.table_name,
                          kcu.column_name,
                          rc.delete_rule
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                          ON tc.constraint_name = kcu.constraint_name
                          AND tc.table_schema = kcu.table_schema
                        JOIN information_schema.referential_constraints rc
                          ON rc.constraint_name = tc.constraint_name
                          AND rc.constraint_schema = tc.table_schema
                        WHERE tc.table_schema = 'public'
                          AND tc.constraint_type = 'FOREIGN KEY'
                          AND kcu.table_name IN (
                            'conversations', 'messages', 'ai_usage_logs', 'daily_ai_usage_aggregates'
                          )
                        ORDER BY kcu.table_name, kcu.column_name
                        """
                    )
                )
                found = {(str(r[0]), str(r[1])): str(r[2]) for r in result.fetchall()}
        finally:
            await engine.dispose()

        for key, rule in expected.items():
            assert found.get(key) == rule, (key, found.get(key), found)

    asyncio.run(body())
