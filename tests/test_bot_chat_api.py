"""Bot dashboard chat HTTP routes (dependency overrides; no external AI)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from app.api import deps
from app.main import app
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.ai_chat import (
    BotDashboardChatTestResponse,
    ConversationMessagesResponse,
    SendBotMessageResult,
)
from app.schemas.ai_foundation import ConversationRead, MessageRead
from app.services.ai_error_taxonomy import exception_for_failed_send_result
from fastapi.testclient import TestClient


class _StubBotChatTestService:
    async def send_dashboard_test_message(
        self,
        *,
        user: User,
        bot_id: uuid.UUID,
        message: str,
        conversation_id: uuid.UUID | None,
    ) -> BotDashboardChatTestResponse:
        cid = conversation_id or uuid.uuid4()
        return BotDashboardChatTestResponse(
            conversation_id=cid,
            user_message_id=uuid.uuid4(),
            assistant_message_id=uuid.uuid4(),
            assistant_text="stub reply",
            model_name="stub-model",
            latency_ms=42,
            tokens_input=1,
            tokens_output=2,
            tokens_total=3,
            cost_usd=Decimal("0.000001"),
        )

    async def get_conversation_for_dashboard(
        self,
        *,
        user: User,
        bot_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> ConversationMessagesResponse:
        now = datetime.now(timezone.utc)
        return ConversationMessagesResponse(
            conversation=ConversationRead(
                id=conversation_id,
                bot_id=bot_id,
                owner_id=user.id,
                channel=None,
                status="active",
                created_at=now,
                updated_at=now,
            ),
            messages=[
                MessageRead(
                    id=uuid.uuid4(),
                    conversation_id=conversation_id,
                    bot_id=bot_id,
                    role="user",
                    content="hi",
                    tokens_input=None,
                    tokens_output=None,
                    tokens_total=None,
                    latency_ms=None,
                    cost_usd=None,
                    model_name=None,
                    created_at=now,
                )
            ],
        )


class _StubBotChatRaiseOnSend(_StubBotChatTestService):
    """Raises structured AI HTTP errors from a synthetic failed :class:`SendBotMessageResult`."""

    def __init__(self, failure: SendBotMessageResult) -> None:
        self._failure = failure

    async def send_dashboard_test_message(
        self,
        *,
        user: User,
        bot_id: uuid.UUID,
        message: str,
        conversation_id: uuid.UUID | None,
    ) -> BotDashboardChatTestResponse:
        raise exception_for_failed_send_result(self._failure)


def _assert_api_error_body_safe(body_text: str) -> None:
    lower = body_text.lower()
    assert "traceback" not in lower
    assert "  File " not in body_text
    assert "  File '" not in body_text
    dumped = json.dumps(json.loads(body_text))
    for leak in ("KeyError", "RuntimeError", "AttributeError", "SQLAlchemy", "postgres"):
        assert leak not in dumped


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def dashboard_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="dash@example.com",
        password_hash="x",
        role=UserRole.customer_admin,
    )


@pytest.fixture
def authed_client(client: TestClient, dashboard_user: User) -> TestClient:
    async def _user() -> User:
        return dashboard_user

    app.dependency_overrides[deps.get_current_user_required] = _user
    app.dependency_overrides[deps.get_bot_chat_test_service] = lambda: _StubBotChatTestService()
    return client


def test_post_chat_test_requires_auth(client: TestClient) -> None:
    bid = uuid.uuid4()
    r = client.post(f"/api/v1/bots/{bid}/chat/test", json={"message": "hello"})
    assert r.status_code == 401


def test_get_conversation_requires_auth(client: TestClient) -> None:
    bid = uuid.uuid4()
    cid = uuid.uuid4()
    r = client.get(f"/api/v1/bots/{bid}/conversations/{cid}")
    assert r.status_code == 401


def test_post_chat_test_returns_frontend_friendly_payload(authed_client: TestClient) -> None:
    bid = uuid.uuid4()
    r = authed_client.post(f"/api/v1/bots/{bid}/chat/test", json={"message": "hello bot"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["assistant_text"] == "stub reply"
    assert data["model_name"] == "stub-model"
    assert data["latency_ms"] == 42
    assert data["tokens_total"] == 3
    assert "conversation_id" in data
    assert "user_message_id" in data
    assert "assistant_message_id" in data


def test_post_chat_test_optional_conversation_id(authed_client: TestClient) -> None:
    bid = uuid.uuid4()
    cid = str(uuid.uuid4())
    r = authed_client.post(
        f"/api/v1/bots/{bid}/chat/test",
        json={"message": "continue", "conversation_id": cid},
    )
    assert r.status_code == 200, r.text
    assert r.json()["conversation_id"] == cid


def test_post_chat_test_validation_empty_message(authed_client: TestClient) -> None:
    bid = uuid.uuid4()
    r = authed_client.post(f"/api/v1/bots/{bid}/chat/test", json={"message": ""})
    assert r.status_code == 422


def test_get_conversation_returns_messages(authed_client: TestClient) -> None:
    bid = uuid.uuid4()
    cid = uuid.uuid4()
    r = authed_client.get(f"/api/v1/bots/{bid}/conversations/{cid}")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["conversation"]["id"] == str(cid)
    assert data["conversation"]["bot_id"] == str(bid)
    assert len(data["messages"]) == 1
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][0]["content"] == "hi"


def _client_with_send_failure(client: TestClient, dashboard_user: User, failure: SendBotMessageResult) -> TestClient:
    async def _user() -> User:
        return dashboard_user

    app.dependency_overrides[deps.get_current_user_required] = _user
    app.dependency_overrides[deps.get_bot_chat_test_service] = lambda: _StubBotChatRaiseOnSend(failure)
    return client


def test_post_chat_test_timeout_safe_api_envelope(client: TestClient, dashboard_user: User) -> None:
    cid, uid = uuid.uuid4(), uuid.uuid4()
    failure = SendBotMessageResult(
        conversation_id=cid,
        user_message_id=uid,
        success=False,
        error_code="timeout",
        error_message=None,
    )
    ac = _client_with_send_failure(client, dashboard_user, failure)
    bid = uuid.uuid4()
    r = ac.post(f"/api/v1/bots/{bid}/chat/test", json={"message": "hello"})
    assert r.status_code == 504, r.text
    _assert_api_error_body_safe(r.text)
    err = r.json()["error"]
    assert err["code"] == "ai_timeout"
    assert err["category"] == "ai_chat"
    assert err["ai_category"] == "timeout"
    assert err["details"]["retryable"] is True
    assert "credential" not in err["message"].lower()


def test_post_chat_test_auth_config_safe_api_envelope(client: TestClient, dashboard_user: User) -> None:
    cid, uid = uuid.uuid4(), uuid.uuid4()
    failure = SendBotMessageResult(
        conversation_id=cid,
        user_message_id=uid,
        success=False,
        error_code="auth_failed",
        error_message=None,
    )
    ac = _client_with_send_failure(client, dashboard_user, failure)
    bid = uuid.uuid4()
    r = ac.post(f"/api/v1/bots/{bid}/chat/test", json={"message": "hello"})
    assert r.status_code == 502, r.text
    _assert_api_error_body_safe(r.text)
    err = r.json()["error"]
    assert err["code"] == "ai_auth_config"
    assert err["ai_category"] == "auth_config"
    assert err["details"]["retryable"] is False


def test_post_chat_test_invalid_provider_response_safe_api_envelope(
    client: TestClient,
    dashboard_user: User,
) -> None:
    cid, uid = uuid.uuid4(), uuid.uuid4()
    failure = SendBotMessageResult(
        conversation_id=cid,
        user_message_id=uid,
        success=False,
        error_code="invalid_response",
        error_message=None,
    )
    ac = _client_with_send_failure(client, dashboard_user, failure)
    bid = uuid.uuid4()
    r = ac.post(f"/api/v1/bots/{bid}/chat/test", json={"message": "hello"})
    assert r.status_code == 502, r.text
    _assert_api_error_body_safe(r.text)
    err = r.json()["error"]
    assert err["code"] == "ai_invalid_provider_response"
    assert err["ai_category"] == "invalid_provider_response"
    assert err["details"]["retryable"] is False
