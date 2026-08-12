"""Unit tests for conversation sales-flow vocabulary and CHECK SQL (no database)."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from app.models.conversation_flow import (
    CHECK_CONVERSATION_DETECTED_INTENT,
    CHECK_CONVERSATION_FLOW_STATE,
    ConversationDetectedIntent,
    ConversationFlowState,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONVERSATION_SALES_FLOW_REVISION = "g7h8i9j0k1l2"
LEADS_TABLE_REVISION = "h8i9j0k1l2m3"
LEADS_CONV_UNIQUE_INDEX_REVISION = "i9j0k1l2m3n4"
LEADS_NOTES_REVISION = "j0k1l2m3n4o5"
KNOWLEDGE_FILES_REVISION = "m4n5o6p7q8r9"
KNOWLEDGE_CHUNKS_REVISION = "n5o6p7q8r9s0"
KNOWLEDGE_CHUNKS_FTS_INDEX_REVISION = "p6q7r8s9t0u1"
WIDGET_CONFIGS_REVISION = "q7r8s9t0u1v2"
CONVERSATIONS_WEB_WIDGET_SESSION_REVISION = "s0t1u2v3w4"
# Current Alembic head (conversations.telegram_chat_id); keep in sync with alembic heads.
ALEMBIC_HEAD_REVISION = "z9y8x7w6v5u4"


def test_flow_state_enum_values_are_stable_snake_case() -> None:
    assert ConversationFlowState.start.value == "start"
    assert ConversationFlowState.objection_handling.value == "objection_handling"
    assert len(ConversationFlowState) == 8


def test_detected_intent_enum_values_are_stable_snake_case() -> None:
    assert ConversationDetectedIntent.greeting.value == "greeting"
    assert ConversationDetectedIntent.sales_interest.value == "sales_interest"
    assert len(ConversationDetectedIntent) == 6


def test_check_sql_includes_every_flow_state() -> None:
    for s in ConversationFlowState:
        assert f"'{s.value}'" in CHECK_CONVERSATION_FLOW_STATE


def test_check_sql_includes_every_intent_when_non_null() -> None:
    for i in ConversationDetectedIntent:
        assert f"'{i.value}'" in CHECK_CONVERSATION_DETECTED_INTENT
    assert "detected_intent IS NULL" in CHECK_CONVERSATION_DETECTED_INTENT


def test_conversation_sales_flow_migration_is_chained_from_bot_ai_settings() -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(CONVERSATION_SALES_FLOW_REVISION)
    assert rev is not None
    assert rev.down_revision == "f1a2b3c4d5e6"


def test_head_revision_matches_latest_migration() -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    assert ScriptDirectory.from_config(cfg).get_current_head() == ALEMBIC_HEAD_REVISION


def test_leads_migration_chains_from_conversation_sales_flow() -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(LEADS_TABLE_REVISION)
    assert rev is not None
    assert rev.down_revision == CONVERSATION_SALES_FLOW_REVISION


def test_leads_conversation_unique_index_migration_chains_from_leads_table() -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(LEADS_CONV_UNIQUE_INDEX_REVISION)
    assert rev is not None
    assert rev.down_revision == LEADS_TABLE_REVISION


def test_leads_notes_migration_chains_from_conversation_unique_index() -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(LEADS_NOTES_REVISION)
    assert rev is not None
    assert rev.down_revision == LEADS_CONV_UNIQUE_INDEX_REVISION


def test_knowledge_files_migration_chains_from_leads_notes() -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(KNOWLEDGE_FILES_REVISION)
    assert rev is not None
    assert rev.down_revision == LEADS_NOTES_REVISION


def test_knowledge_chunks_migration_chains_from_knowledge_files() -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(KNOWLEDGE_CHUNKS_REVISION)
    assert rev is not None
    assert rev.down_revision == KNOWLEDGE_FILES_REVISION


def test_knowledge_chunks_fts_index_migration_chains_from_knowledge_chunks_table() -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(KNOWLEDGE_CHUNKS_FTS_INDEX_REVISION)
    assert rev is not None
    assert rev.down_revision == KNOWLEDGE_CHUNKS_REVISION


def test_widget_configs_migration_chains_from_knowledge_chunks_fts_index() -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(WIDGET_CONFIGS_REVISION)
    assert rev is not None
    assert rev.down_revision == KNOWLEDGE_CHUNKS_FTS_INDEX_REVISION


def test_conversations_web_widget_session_migration_chains_from_widget_configs() -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(CONVERSATIONS_WEB_WIDGET_SESSION_REVISION)
    assert rev is not None
    assert rev.down_revision == WIDGET_CONFIGS_REVISION
