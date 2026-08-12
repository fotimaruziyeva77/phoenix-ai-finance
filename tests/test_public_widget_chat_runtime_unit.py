"""
Public widget chat runtime contract (no DB): response DTO and JSON shape.

Complements ``test_public_widget_chat_api_integration.py`` (HTTP + DB + fake AI).
"""

from __future__ import annotations

import json
import uuid

from app.schemas.public_widget_chat import PublicWidgetChatResponse

_EXPECTED_RESPONSE_FIELDS = frozenset(
    {
        "conversation_id",
        "visitor_session_key",
        "user_message_id",
        "assistant_message_id",
        "assistant_text",
        "bot_display_name",
    },
)


def test_public_widget_chat_response_model_has_only_safe_fields() -> None:
    assert set(PublicWidgetChatResponse.model_fields.keys()) == _EXPECTED_RESPONSE_FIELDS


def test_public_widget_chat_response_json_encoding_has_no_extra_keys() -> None:
    cid = uuid.uuid4()
    um = uuid.uuid4()
    am = uuid.uuid4()
    row = PublicWidgetChatResponse(
        conversation_id=cid,
        visitor_session_key="x" * 16,
        user_message_id=um,
        assistant_message_id=am,
        assistant_text="hello",
        bot_display_name="Bot",
    )
    dumped = json.loads(row.model_dump_json())
    assert set(dumped.keys()) == _EXPECTED_RESPONSE_FIELDS
