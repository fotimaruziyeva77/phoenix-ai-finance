"""Five-layer chat pipeline: trivial filter, history clean, segmented prompt, exact→semantic cache."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings
from app.prompting.history_clean import clean_history_for_prompt
from app.prompting.types import HistoryTurn, PromptBuildInput, PromptExtensionContext
from app.prompting.builder import build_chat_prompt
from app.services.ai_chat_input_filter import handle_trivial_message
from app.integrations.gemini_text_embedding import GeminiEmbeddingError
from app.services.ai_completion_cache import try_completion_cache
from app.services.semantic_completion_cache import SemanticCompletionCache


def test_salom_no_llm_path_trivial_filter() -> None:
    r = handle_trivial_message("salom", bot_language=None)
    assert r is not None
    assert "Salom" in r


def test_hi_instant_trivial() -> None:
    r = handle_trivial_message("hi", bot_language="en")
    assert r is not None
    assert "Hello" in r


def test_long_message_not_trivial() -> None:
    r = handle_trivial_message(
        "I need a detailed quote for a 200-page migration from Oracle to PostgreSQL with HA.",
        bot_language="en",
    )
    assert r is None


def test_history_no_duplicate_trailing_user() -> None:
    cur = "same"
    hist = (
        HistoryTurn(role="assistant", content="ok"),
        HistoryTurn(role="user", content=cur),
    )
    out = clean_history_for_prompt(hist, cur)
    assert len(out) == 1
    assert out[0].role == "assistant"


def test_try_cache_exact_before_semantic(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
            "gemini_api_key": "k",
            "ai_exact_cache_enabled": True,
            "ai_semantic_cache_enabled": True,
        }
    )
    cache = MagicMock(spec=SemanticCompletionCache)
    cache.lookup_exact = AsyncMock(return_value="Exact cached reply")
    cache.embed_query = AsyncMock()
    cache.lookup = AsyncMock()

    async def _run() -> None:
        hit, kind, emb_err = await try_completion_cache(
            cache,
            settings,
            bot_id=uuid.uuid4(),
            conversation_state="open",
            raw_text="hello there",
            knowledge_injected=False,
        )
        assert hit == "Exact cached reply"
        assert kind == "exact"
        assert emb_err is None
        cache.embed_query.assert_not_called()

    import asyncio

    asyncio.run(_run())


def test_trivial_fast_path_skips_provider_when_enabled() -> None:
    """Layer 1: greeting returns canned text; provider.generate_response is never called."""
    from unittest.mock import AsyncMock

    from app.services.ai_service import AIService

    owner = uuid.uuid4()
    conv_id = uuid.uuid4()
    bot = MagicMock()
    bot.id = uuid.uuid4()
    bot.owner_id = owner
    bot.name = "B"
    bot.niche_id = "education"
    bot.goal_type = "support"
    bot.status = "active"
    bot.welcome_message = None
    bot.tone = None
    bot.language = None
    bot.short_description = None
    bot.provider_name = "gemini"
    bot.model_name = None
    bot.temperature = None
    bot.max_output_tokens = None

    user = MagicMock()
    user.id = owner

    chat = AsyncMock()
    chat.get_conversation_for_bot_owner = AsyncMock(return_value=MagicMock(id=conv_id))
    chat.add_message = AsyncMock(side_effect=[MagicMock(id=uuid.uuid4()), MagicMock(id=uuid.uuid4())])
    chat.commit = AsyncMock()
    chat.touch_conversation_updated_at = AsyncMock()
    chat.add_usage_log = AsyncMock()

    bots = AsyncMock()
    bots.get_bot_by_id = AsyncMock(return_value=bot)

    called = {"n": 0}

    def _resolver(_s, _p):
        called["n"] += 1
        raise AssertionError("provider should not resolve for trivial greeting")

    settings = Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
            "gemini_api_key": "k",
            "ai_trivial_greeting_fast_path_enabled": True,
            "ai_exact_cache_enabled": False,
            "ai_semantic_cache_enabled": False,
        }
    )
    svc = AIService(chat, bots, settings=settings, provider_resolver=_resolver)
    import asyncio

    async def _run():
        out = await svc.send_bot_message(bot, user, "salom", conversation_id=conv_id)
        assert out.success is True
        assert "Salom" in (out.assistant_text or "")
        assert called["n"] == 0

    asyncio.run(_run())


def test_build_prompt_strips_knowledge_when_disabled() -> None:
    from app.prompting.types import BotPromptSource

    bot = BotPromptSource(
        name="T",
        niche_id="services",
        goal_type="support",
        tone=None,
        language="en",
    )
    ext = PromptExtensionContext(knowledge_excerpt="SECRET_KNOWLEDGE_BLOCK_DO_NOT_SEND")
    inp = PromptBuildInput(bot=bot, user_message="short", history=(), extensions=ext)
    pkg = build_chat_prompt(inp, use_knowledge=False, is_short=True)
    assert "SECRET_KNOWLEDGE" not in pkg.system_prompt
    assert pkg.history_messages == ()
