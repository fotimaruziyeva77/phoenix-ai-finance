"""AIService orchestration (mocked repos + provider)."""

from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.ai_providers.base import AIProvider
from app.ai_providers.types import GenerateParams, NormalizedAIResult, TokenUsage
from app.core.config import Settings
from app.lib.chat_channels import CONVERSATION_CHANNEL_ADMIN_TEST
from app.schemas.knowledge_retrieval import (
    KnowledgeChunkHit,
    KnowledgeContextItem,
    KnowledgeContextSelectionMeta,
    KnowledgeRetrievalResponse,
)
from app.services.ai_exceptions import (
    AIServiceForbiddenError,
    AIServiceNotFoundError,
    AIServiceValidationError,
)
from app.services.ai_service import AIService
from sqlalchemy.exc import SQLAlchemyError


def _settings() -> Settings:
    return Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
            "gemini_api_key": "test-key",
            "gemini_default_model": "gemini-test",
            "ai_trivial_greeting_fast_path_enabled": False,
            "ai_exact_cache_enabled": False,
            "ai_semantic_cache_enabled": False,
        }
    )


def _user(uid: uuid.UUID | None = None) -> SimpleNamespace:
    return SimpleNamespace(id=uid or uuid.uuid4())


def _bot(*, owner_id: uuid.UUID, bid: uuid.UUID | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=bid or uuid.uuid4(),
        owner_id=owner_id,
        name="B",
        niche_id="education",
        goal_type="support",
        status="active",
        welcome_message=None,
        tone=None,
        language=None,
        short_description=None,
        provider_name="gemini",
        model_name=None,
        temperature=None,
        max_output_tokens=None,
    )


class _FakeProvider(AIProvider):
    def __init__(self, result: NormalizedAIResult) -> None:
        self._result = result
        self.closed = False
        self.last_params: GenerateParams | None = None

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return "gemini-test"

    async def generate_response(self, params: GenerateParams) -> NormalizedAIResult:
        self.last_params = params
        assert len(params.messages) >= 2
        return self._result

    def parse_usage(self, raw):
        return None

    def normalize_error(self, exc: BaseException) -> tuple[str | None, str]:
        return ("x", "y")

    async def aclose(self) -> None:
        self.closed = True


class _ExplodingProvider(AIProvider):
    """Simulates transport/SDK failure before a normalized result."""

    def __init__(self) -> None:
        self.closed = False

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return "gemini-test"

    async def generate_response(self, params: GenerateParams) -> NormalizedAIResult:
        raise RuntimeError("simulated provider crash")

    def parse_usage(self, raw):
        return None

    def normalize_error(self, exc: BaseException) -> tuple[str | None, str]:
        return ("unexpected_error", str(exc))

    async def aclose(self) -> None:
        self.closed = True


def _make_chat_and_bots(
    *,
    conv_id: uuid.UUID,
    user_mid: uuid.UUID,
    asst_mid: uuid.UUID | None = None,
    existing_conv: SimpleNamespace | None = None,
) -> tuple[AsyncMock, AsyncMock]:
    chat = AsyncMock()
    if existing_conv is not None:
        chat.get_conversation_for_bot_owner = AsyncMock(return_value=existing_conv)
        chat.create_conversation = AsyncMock()
    else:
        chat.create_conversation = AsyncMock(return_value=SimpleNamespace(id=conv_id))
        chat.get_conversation_for_bot_owner = AsyncMock()
    chat.list_recent_history_messages = AsyncMock(return_value=[])

    async def add_message(**kwargs):
        if kwargs["role"] == "user":
            return SimpleNamespace(id=user_mid)
        return SimpleNamespace(id=asst_mid or uuid.uuid4())

    chat.add_message = AsyncMock(side_effect=add_message)
    chat.add_usage_log = AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4()))
    chat.touch_conversation_updated_at = AsyncMock()
    chat.commit = AsyncMock()
    chat.rollback = AsyncMock()

    bots = AsyncMock()
    return chat, bots


def test_send_bot_message_empty_text_raises() -> None:
    async def run() -> None:
        svc = AIService(AsyncMock(), AsyncMock(), settings=_settings())
        u = _user()
        b = _bot(owner_id=u.id)
        with pytest.raises(AIServiceValidationError):
            await svc.send_bot_message(b, u, "   ")

    asyncio.run(run())


def test_send_bot_message_forbidden_wrong_owner() -> None:
    async def run() -> None:
        u = _user()
        other = uuid.uuid4()
        b = _bot(owner_id=other)
        svc = AIService(AsyncMock(), AsyncMock(), settings=_settings())
        with pytest.raises(AIServiceForbiddenError):
            await svc.send_bot_message(b, u, "hi")

    asyncio.run(run())


def test_send_bot_message_conversation_not_found() -> None:
    async def run() -> None:
        u = _user()
        b = _bot(owner_id=u.id)
        cid = uuid.uuid4()
        chat = AsyncMock()
        chat.get_conversation_for_bot_owner = AsyncMock(return_value=None)
        bots = AsyncMock()
        bots.get_bot_by_id = AsyncMock(return_value=b)
        svc = AIService(chat, bots, settings=_settings())
        with pytest.raises(AIServiceNotFoundError):
            await svc.send_bot_message(b, u, "hi", conversation_id=cid)

    asyncio.run(run())


def test_send_bot_message_success_persists_and_returns() -> None:
    async def run() -> None:
        u = _user()
        b = _bot(owner_id=u.id)
        conv_id = uuid.uuid4()
        user_mid = uuid.uuid4()
        asst_mid = uuid.uuid4()

        chat, bots = _make_chat_and_bots(conv_id=conv_id, user_mid=user_mid, asst_mid=asst_mid)
        bots.get_bot_by_id = AsyncMock(return_value=b)

        ok = NormalizedAIResult(
            success=True,
            provider_name="gemini",
            text="Hello back",
            model_name="gemini-test",
            tokens=TokenUsage(input_tokens=3, output_tokens=2, total_tokens=5),
        )
        fake = _FakeProvider(ok)

        svc = AIService(
            chat,
            bots,
            settings=_settings(),
            provider_resolver=lambda s, _pid: fake,
        )
        out = await svc.send_bot_message(b, u, "Hi there")
        assert fake.last_params is not None
        assert fake.last_params.model == "gemini-test"
        assert fake.last_params.temperature is None
        assert fake.last_params.max_output_tokens == 2048
        assert out.success is True
        assert out.conversation_id == conv_id
        assert out.user_message_id == user_mid
        assert out.assistant_message_id == asst_mid
        assert out.assistant_text == "Hello back"
        assert out.latency_ms is not None
        assert fake.closed is True
        assert chat.commit.await_count == 2
        assert out.knowledge_context is None

    asyncio.run(run())


def test_new_conversation_calls_create_not_get() -> None:
    async def run() -> None:
        u = _user()
        b = _bot(owner_id=u.id)
        conv_id = uuid.uuid4()
        user_mid = uuid.uuid4()
        chat, bots = _make_chat_and_bots(conv_id=conv_id, user_mid=user_mid)
        bots.get_bot_by_id = AsyncMock(return_value=b)

        ok = NormalizedAIResult(
            success=True,
            provider_name="gemini",
            text="ok",
            model_name="m",
        )
        svc = AIService(
            chat,
            bots,
            settings=_settings(),
            provider_resolver=lambda s, _pid: _FakeProvider(ok),
        )
        await svc.send_bot_message(b, u, "Hi")
        chat.create_conversation.assert_awaited_once()
        chat.get_conversation_for_bot_owner.assert_not_awaited()

    asyncio.run(run())


def test_new_conversation_sets_admin_test_channel_for_dashboard_turns() -> None:
    async def run() -> None:
        u = _user()
        b = _bot(owner_id=u.id)
        conv_id = uuid.uuid4()
        user_mid = uuid.uuid4()
        chat, bots = _make_chat_and_bots(conv_id=conv_id, user_mid=user_mid)
        bots.get_bot_by_id = AsyncMock(return_value=b)
        ok = NormalizedAIResult(success=True, provider_name="gemini", text="ok", model_name="m")
        svc = AIService(
            chat,
            bots,
            settings=_settings(),
            provider_resolver=lambda s, _pid: _FakeProvider(ok),
        )
        await svc.send_bot_message(b, u, "Hi")
        kwargs = chat.create_conversation.await_args.kwargs
        assert kwargs.get("channel") == CONVERSATION_CHANNEL_ADMIN_TEST
        assert kwargs.get("visitor_client_hint") == CONVERSATION_CHANNEL_ADMIN_TEST

    asyncio.run(run())


def test_existing_conversation_calls_get_not_create() -> None:
    async def run() -> None:
        u = _user()
        b = _bot(owner_id=u.id)
        conv_id = uuid.uuid4()
        user_mid = uuid.uuid4()
        chat, bots = _make_chat_and_bots(
            conv_id=conv_id,
            user_mid=user_mid,
            existing_conv=SimpleNamespace(id=conv_id),
        )
        bots.get_bot_by_id = AsyncMock(return_value=b)
        ok = NormalizedAIResult(success=True, provider_name="g", text="ok", model_name="m")
        svc = AIService(
            chat,
            bots,
            settings=_settings(),
            provider_resolver=lambda s, _pid: _FakeProvider(ok),
        )
        await svc.send_bot_message(b, u, "Hi", conversation_id=conv_id)
        chat.get_conversation_for_bot_owner.assert_awaited_once()
        chat.create_conversation.assert_not_awaited()

    asyncio.run(run())


def test_user_message_committed_before_provider_runs() -> None:
    async def run() -> None:
        u = _user()
        b = _bot(owner_id=u.id)
        conv_id = uuid.uuid4()
        user_mid = uuid.uuid4()
        chat, bots = _make_chat_and_bots(conv_id=conv_id, user_mid=user_mid)
        bots.get_bot_by_id = AsyncMock(return_value=b)

        commits_at_generate: list[int] = []

        class _Probe(_FakeProvider):
            async def generate_response(self, params: GenerateParams) -> NormalizedAIResult:
                commits_at_generate.append(chat.commit.await_count)
                return self._result

        ok = NormalizedAIResult(success=True, provider_name="g", text="x", model_name="m")
        probe = _Probe(ok)
        svc = AIService(
            chat,
            bots,
            settings=_settings(),
            provider_resolver=lambda s, _pid: probe,
        )
        await svc.send_bot_message(b, u, "Hi")
        assert commits_at_generate == [1], "first commit (user msg) must precede provider call"

    asyncio.run(run())


def test_success_path_persists_user_assistant_usage_and_touch() -> None:
    async def run() -> None:
        u = _user()
        b = _bot(owner_id=u.id)
        conv_id = uuid.uuid4()
        user_mid = uuid.uuid4()
        asst_mid = uuid.uuid4()
        chat, bots = _make_chat_and_bots(conv_id=conv_id, user_mid=user_mid, asst_mid=asst_mid)
        bots.get_bot_by_id = AsyncMock(return_value=b)
        ok = NormalizedAIResult(success=True, provider_name="gemini", text="Reply", model_name="m")
        svc = AIService(
            chat,
            bots,
            settings=_settings(),
            provider_resolver=lambda s, _pid: _FakeProvider(ok),
        )
        await svc.send_bot_message(b, u, "Q")

        assert chat.add_message.await_count == 2
        user_kw = chat.add_message.await_args_list[0].kwargs
        asst_kw = chat.add_message.await_args_list[1].kwargs
        assert user_kw["role"] == "user" and user_kw["content"] == "Q"
        assert asst_kw["role"] == "assistant" and asst_kw["content"] == "Reply"

        chat.add_usage_log.assert_awaited_once()
        ul = chat.add_usage_log.await_args.kwargs
        assert ul["success"] is True
        assert ul["message_id"] == asst_mid
        assert ul["provider_name"] == "gemini"
        chat.touch_conversation_updated_at.assert_awaited_once_with(conv_id)

    asyncio.run(run())


def test_provider_failure_persists_user_only_usage_no_assistant() -> None:
    async def run() -> None:
        u = _user()
        b = _bot(owner_id=u.id)
        conv_id = uuid.uuid4()
        user_mid = uuid.uuid4()
        chat, bots = _make_chat_and_bots(conv_id=conv_id, user_mid=user_mid)
        bots.get_bot_by_id = AsyncMock(return_value=b)
        bad = NormalizedAIResult(
            success=False,
            provider_name="gemini",
            text=None,
            model_name="m",
            error_code="rate_limited",
            error_message="Slow",
        )
        svc = AIService(chat, bots, settings=_settings(), provider_resolver=lambda s, _pid: _FakeProvider(bad))
        out = await svc.send_bot_message(b, u, "Hi")
        assert out.success is False
        assert out.assistant_message_id is None
        assert out.error_code == "rate_limited"
        assert out.error_message == "Slow"
        chat.add_message.assert_awaited_once()
        assert chat.add_message.await_args.kwargs["role"] == "user"
        chat.add_usage_log.assert_awaited_once()
        ul = chat.add_usage_log.await_args.kwargs
        assert ul["message_id"] is None
        assert ul["success"] is False
        assert ul["error_code"] == "rate_limited"
        assert ul["tokens_input"] == 0
        assert ul["tokens_output"] == 0
        assert ul["tokens_total"] == 0
        assert ul["latency_ms"] is not None

    asyncio.run(run())


def test_provider_success_with_empty_text_treated_as_failure_and_usage_logged() -> None:
    async def run() -> None:
        u = _user()
        b = _bot(owner_id=u.id)
        conv_id = uuid.uuid4()
        user_mid = uuid.uuid4()
        chat, bots = _make_chat_and_bots(conv_id=conv_id, user_mid=user_mid)
        bots.get_bot_by_id = AsyncMock(return_value=b)
        hollow = NormalizedAIResult(
            success=True,
            provider_name="gemini",
            text="   ",
            model_name="m",
        )
        svc = AIService(chat, bots, settings=_settings(), provider_resolver=lambda s, _pid: _FakeProvider(hollow))
        out = await svc.send_bot_message(b, u, "Hi")
        assert out.success is False
        assert out.error_code == "invalid_response"
        assert out.assistant_message_id is None
        chat.add_message.assert_awaited_once()
        assert chat.add_message.await_args.kwargs["role"] == "user"
        chat.add_usage_log.assert_awaited_once()
        ul = chat.add_usage_log.await_args.kwargs
        assert ul["success"] is False
        assert ul["error_code"] == "invalid_response"
        assert ul["message_id"] is None

    asyncio.run(run())


def test_unexpected_provider_exception_normalized_and_usage_logged() -> None:
    async def run() -> None:
        u = _user()
        b = _bot(owner_id=u.id)
        conv_id = uuid.uuid4()
        user_mid = uuid.uuid4()
        chat, bots = _make_chat_and_bots(conv_id=conv_id, user_mid=user_mid)
        bots.get_bot_by_id = AsyncMock(return_value=b)
        boom = _ExplodingProvider()
        svc = AIService(chat, bots, settings=_settings(), provider_resolver=lambda s, _pid: boom)
        out = await svc.send_bot_message(b, u, "Hi")
        assert out.success is False
        assert out.error_code == "unexpected_error"
        chat.add_message.assert_awaited_once()
        chat.add_usage_log.assert_awaited_once()
        assert chat.add_usage_log.await_args.kwargs["success"] is False
        assert boom.closed is True

    asyncio.run(run())


def test_first_phase_sql_error_rollbacks_and_skips_provider() -> None:
    async def run() -> None:
        u = _user()
        b = _bot(owner_id=u.id)
        conv_id = uuid.uuid4()
        chat = AsyncMock()
        chat.create_conversation = AsyncMock(return_value=SimpleNamespace(id=conv_id))
        chat.list_recent_history_messages = AsyncMock(return_value=[])
        chat.add_message = AsyncMock(side_effect=SQLAlchemyError("db user message failed"))
        chat.commit = AsyncMock()
        chat.rollback = AsyncMock()

        bots = AsyncMock()
        bots.get_bot_by_id = AsyncMock(return_value=b)

        provider_calls = 0

        def resolver(s: Settings, _pid: str | None) -> AIProvider:
            nonlocal provider_calls
            provider_calls += 1
            return _FakeProvider(
                NormalizedAIResult(success=True, provider_name="g", text="x", model_name="m")
            )

        svc = AIService(chat, bots, settings=_settings(), provider_resolver=resolver)
        with pytest.raises(AIServiceValidationError, match="persist"):
            await svc.send_bot_message(b, u, "Hi")
        chat.rollback.assert_awaited()
        assert provider_calls == 0
        chat.commit.assert_not_awaited()

    asyncio.run(run())


def test_second_phase_failure_rollbacks_no_partial_assistant_or_usage_commit() -> None:
    async def run() -> None:
        u = _user()
        b = _bot(owner_id=u.id)
        conv_id = uuid.uuid4()
        user_mid = uuid.uuid4()
        asst_mid = uuid.uuid4()

        chat = AsyncMock()
        chat.create_conversation = AsyncMock(return_value=SimpleNamespace(id=conv_id))
        chat.list_recent_history_messages = AsyncMock(return_value=[])

        async def add_message(**kwargs):
            if kwargs["role"] == "user":
                return SimpleNamespace(id=user_mid)
            return SimpleNamespace(id=asst_mid)

        chat.add_message = AsyncMock(side_effect=add_message)
        chat.add_usage_log = AsyncMock(side_effect=SQLAlchemyError("usage log failed"))
        chat.touch_conversation_updated_at = AsyncMock()
        chat.commit = AsyncMock()
        chat.rollback = AsyncMock()

        bots = AsyncMock()
        bots.get_bot_by_id = AsyncMock(return_value=b)

        ok = NormalizedAIResult(success=True, provider_name="g", text="A", model_name="m")
        svc = AIService(
            chat,
            bots,
            settings=_settings(),
            provider_resolver=lambda s, _pid: _FakeProvider(ok),
        )
        out = await svc.send_bot_message(b, u, "Hi")
        assert out.success is False
        assert out.error_code == "persistence_error"
        chat.rollback.assert_awaited()
        assert chat.commit.await_count == 1

    asyncio.run(run())


def test_send_bot_message_uses_provider_default_model_when_bot_model_blank() -> None:
    """Regression: empty bot.model_name must resolve via provider.default_model (not a stale settings-only path)."""

    class _AltDefault(_FakeProvider):
        @property
        def default_model(self) -> str:
            return "resolved-from-provider-default"

    async def run() -> None:
        u = _user()
        b = _bot(owner_id=u.id)
        b.model_name = None
        conv_id = uuid.uuid4()
        user_mid = uuid.uuid4()
        chat, bots = _make_chat_and_bots(conv_id=conv_id, user_mid=user_mid)
        bots.get_bot_by_id = AsyncMock(return_value=b)
        ok = NormalizedAIResult(success=True, provider_name="gemini", text="ok", model_name="m")
        alt = _AltDefault(ok)
        svc = AIService(chat, bots, settings=_settings(), provider_resolver=lambda s, _pid: alt)
        await svc.send_bot_message(b, u, "Hi")
        assert alt.last_params is not None
        assert alt.last_params.model == "resolved-from-provider-default"

    asyncio.run(run())


def test_send_bot_message_uses_bot_model_temperature_and_max_tokens() -> None:
    async def run() -> None:
        u = _user()
        b = _bot(owner_id=u.id)
        b.model_name = "gemini-2.5-flash"
        b.temperature = 0.4
        b.max_output_tokens = 900
        conv_id = uuid.uuid4()
        user_mid = uuid.uuid4()
        asst_mid = uuid.uuid4()
        chat, bots = _make_chat_and_bots(conv_id=conv_id, user_mid=user_mid, asst_mid=asst_mid)
        bots.get_bot_by_id = AsyncMock(return_value=b)
        ok = NormalizedAIResult(success=True, provider_name="gemini", text="x", model_name="gemini-2.5-flash")
        fake = _FakeProvider(ok)
        svc = AIService(chat, bots, settings=_settings(), provider_resolver=lambda s, _pid: fake)
        await svc.send_bot_message(b, u, "Hi")
        assert fake.last_params is not None
        assert fake.last_params.model == "gemini-2.5-flash"
        assert fake.last_params.temperature == 0.4
        assert fake.last_params.max_output_tokens == 900

    asyncio.run(run())


def test_send_bot_message_skips_retrieval_when_no_ready_knowledge_files() -> None:
    async def run() -> None:
        u = _user()
        b = _bot(owner_id=u.id)
        conv_id = uuid.uuid4()
        user_mid = uuid.uuid4()
        asst_mid = uuid.uuid4()
        chat, bots = _make_chat_and_bots(conv_id=conv_id, user_mid=user_mid, asst_mid=asst_mid)
        bots.get_bot_by_id = AsyncMock(return_value=b)
        ok = NormalizedAIResult(
            success=True,
            provider_name="gemini",
            text="Hello back",
            model_name="gemini-test",
        )
        fake = _FakeProvider(ok)
        k_files = AsyncMock()
        k_files.count_ready_knowledge_files_for_bot = AsyncMock(return_value=0)
        k_retrieval = AsyncMock()
        svc = AIService(
            chat,
            bots,
            settings=_settings(),
            provider_resolver=lambda s, _pid: fake,
            knowledge_retrieval=k_retrieval,
            knowledge_files=k_files,
        )
        out = await svc.send_bot_message(b, u, "Hi there")
        k_retrieval.retrieve_for_bot.assert_not_awaited()
        assert out.knowledge_context is not None
        assert out.knowledge_context.had_ready_knowledge_files is False

    asyncio.run(run())


def test_send_bot_message_injects_knowledge_excerpt_into_system_prompt() -> None:
    async def run() -> None:
        u = _user()
        b = _bot(owner_id=u.id)
        conv_id = uuid.uuid4()
        user_mid = uuid.uuid4()
        asst_mid = uuid.uuid4()
        chat, bots = _make_chat_and_bots(conv_id=conv_id, user_mid=user_mid, asst_mid=asst_mid)
        bots.get_bot_by_id = AsyncMock(return_value=b)
        ok = NormalizedAIResult(
            success=True,
            provider_name="gemini",
            text="Hello back",
            model_name="gemini-test",
        )
        fake = _FakeProvider(ok)
        chunk_id = uuid.uuid4()
        file_id = uuid.uuid4()
        hit = KnowledgeChunkHit(
            chunk_id=chunk_id,
            knowledge_file_id=file_id,
            chunk_index=0,
            content="SECRET_KNOWLEDGE_BODY",
            rank=0.9,
            page_number=1,
            original_filename="manual.txt",
            token_count=10,
        )
        ctx_item = KnowledgeContextItem(
            chunk_id=chunk_id,
            knowledge_file_id=file_id,
            chunk_index=0,
            content="SECRET_KNOWLEDGE_BODY",
            estimated_tokens=10,
            rank=0.9,
            page_number=1,
            original_filename="manual.txt",
        )
        sel_meta = KnowledgeContextSelectionMeta(
            chunks_retrieved=1,
            chunks_in_context=1,
            total_estimated_tokens=10,
            max_chunks_applied=8,
            max_total_tokens_estimated_applied=4000,
        )
        retrieval_resp = KnowledgeRetrievalResponse(
            query="Hi there",
            bot_id=b.id,
            hits=[hit],
            context=[ctx_item],
            context_meta=sel_meta,
        )
        k_files = AsyncMock()
        k_files.count_ready_knowledge_files_for_bot = AsyncMock(return_value=1)
        k_retrieval = AsyncMock()
        k_retrieval.retrieve_for_bot = AsyncMock(return_value=retrieval_resp)
        svc = AIService(
            chat,
            bots,
            settings=_settings(),
            provider_resolver=lambda s, _pid: fake,
            knowledge_retrieval=k_retrieval,
            knowledge_files=k_files,
        )
        out = await svc.send_bot_message(b, u, "Hi there")
        assert fake.last_params is not None
        sys_msgs = [m for m in fake.last_params.messages if m.role == "system"]
        assert len(sys_msgs) == 1
        assert "SECRET_KNOWLEDGE_BODY" in sys_msgs[0].content
        assert "manual.txt" in sys_msgs[0].content
        k_retrieval.retrieve_for_bot.assert_awaited_once()
        assert out.knowledge_context is not None
        assert out.knowledge_context.had_ready_knowledge_files is True
        assert out.knowledge_context.retrieval_hit_count == 1
        assert out.knowledge_context.context_chunk_count == 1

    asyncio.run(run())


def test_archived_bot_rejected() -> None:
    async def run() -> None:
        u = _user()
        b = _bot(owner_id=u.id)
        b.status = "archived"
        bots = AsyncMock()
        bots.get_bot_by_id = AsyncMock(return_value=b)
        svc = AIService(AsyncMock(), bots, settings=_settings())
        with pytest.raises(AIServiceValidationError):
            await svc.send_bot_message(b, u, "x")

    asyncio.run(run())


def test_send_bot_message_sales_delegates_to_sales_orchestrator() -> None:
    async def run() -> None:
        u = _user()
        b = _bot(owner_id=u.id)
        b.goal_type = "sales"
        conv_id = uuid.uuid4()
        user_mid = uuid.uuid4()
        asst_mid = uuid.uuid4()

        chat, bots = _make_chat_and_bots(conv_id=conv_id, user_mid=user_mid, asst_mid=asst_mid)
        bots.get_bot_by_id = AsyncMock(return_value=b)

        mock_orch = MagicMock()
        mock_orch.process_sales_turn = AsyncMock(
            return_value=SimpleNamespace(
                success=True,
                conversation_id=conv_id,
                assistant_text="Sales reply",
                assistant_message_id=asst_mid,
                model_name="gemini-test",
                error_code=None,
                error_message=None,
                latency_ms=20,
                tokens_input=1,
                tokens_output=2,
                tokens_total=3,
                cost_usd=Decimal("0.00001"),
                metadata=SimpleNamespace(failure_category=None),
            ),
        )

        svc = AIService(
            chat,
            bots,
            settings=_settings(),
            sales_orchestrator=mock_orch,
        )
        out = await svc.send_bot_message(b, u, "I want pricing")

        mock_orch.process_sales_turn.assert_awaited_once()
        call = mock_orch.process_sales_turn.await_args
        assert call.kwargs["persist_user_message"] is False
        assert call.args[2] == "I want pricing"

        assert out.success is True
        assert out.assistant_text == "Sales reply"
        assert out.user_message_id == user_mid

    asyncio.run(run())
