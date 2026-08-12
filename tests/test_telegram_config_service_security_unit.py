"""Security-focused unit tests for Telegram config DTOs and errors (no DB)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.domain.telegram_channel_status import TELEGRAM_PROVISIONING_ACTIVE
from app.schemas.telegram_config import TelegramConfigRead
from app.services.telegram_config_exceptions import TelegramTokenInvalidError


def test_telegram_config_read_schema_excludes_token_fields() -> None:
    fields = set(TelegramConfigRead.model_fields.keys())
    assert "bot_token" not in fields
    assert "bot_token_encrypted" not in fields
    assert "webhook_secret_token_encrypted" not in fields
    assert "token" not in fields


def test_telegram_config_read_serialization_excludes_sensitive_substrings() -> None:
    secret = "123456789:AAH_super_secret_botfather_token_xx"
    read = TelegramConfigRead(
        id=uuid.uuid4(),
        bot_id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        has_stored_bot_token=True,
        provisioning_status=TELEGRAM_PROVISIONING_ACTIVE,
        bot_username="x",
        webhook_url=None,
        is_connected=True,
        last_verified_at=datetime.now(UTC),
        metadata_json={"note": "no token here"},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    text_blob = read.model_dump_json()
    assert secret not in text_blob
    assert "AAH_super_secret" not in text_blob


def test_telegram_token_invalid_error_is_generic() -> None:
    err = TelegramTokenInvalidError()
    msg = str(err).lower()
    assert "123456789" not in msg
    assert "botfather" not in msg
    assert ":" not in msg
