"""Unit tests for public widget chat request validation (no DB)."""

from __future__ import annotations

import uuid

import pytest
from app.schemas.public_widget_chat import PublicWidgetChatRequest
from pydantic import ValidationError


def test_conversation_id_without_visitor_key_rejected() -> None:
    with pytest.raises(ValidationError) as exc:
        PublicWidgetChatRequest(
            message="hi",
            conversation_id=uuid.uuid4(),
            visitor_session_key=None,
        )
    assert "visitor_session_key" in str(exc.value).lower()


def test_conversation_id_with_blank_visitor_key_rejected() -> None:
    with pytest.raises(ValidationError):
        PublicWidgetChatRequest(
            message="hi",
            conversation_id=uuid.uuid4(),
            visitor_session_key="   ",
        )


def test_conversation_id_with_valid_key_ok() -> None:
    cid = uuid.uuid4()
    m = PublicWidgetChatRequest(
        message="hi",
        conversation_id=cid,
        visitor_session_key="a" * 16,
    )
    assert m.conversation_id == cid
