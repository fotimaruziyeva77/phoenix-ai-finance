"""
Authenticated AI usage quota read (cap-adjacent): proves Bearer access to quota endpoint and
aggregates from ``ai_usage_logs`` when daily soft-cap is configured.
"""

from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.integration
from fastapi.testclient import TestClient

from app.core.config import get_settings

from tests.integration.auth_db import insert_ai_usage_log_for_bot
from tests.integration.auth_setup import register_user, unique_email


def test_ai_usage_quota_read_requires_authentication(auth_http_client: TestClient) -> None:
    fake = uuid.uuid4()
    r = auth_http_client.get(f"/api/v1/bots/{fake}/ai-usage-quota")
    assert r.status_code == 401
    body = r.json()
    assert body.get("error", {}).get("code") == "not_authenticated"


def test_ai_usage_quota_read_shows_usage_over_daily_cap(
    auth_http_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    live_db_url: str,
) -> None:
    monkeypatch.setenv("AI_DAILY_TOTAL_TOKENS_SOFT_CAP_PER_BOT", "500")
    get_settings.cache_clear()
    email = unique_email("quota")
    reg = register_user(auth_http_client, email)
    token = reg["access_token"]
    bot_payload = {
        "name": "Quota Bot",
        "niche_id": "support",
        "goal_type": "support",
        "provider_name": "gemini",
    }
    br = auth_http_client.post(
        "/api/v1/bots",
        json=bot_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert br.status_code == 201, br.text
    bot_id = uuid.UUID(br.json()["id"])
    insert_ai_usage_log_for_bot(
        bot_id=bot_id,
        tokens_total=600,
        live_db_url=live_db_url,
        monkeypatch=monkeypatch,
    )
    qr = auth_http_client.get(
        f"/api/v1/bots/{bot_id}/ai-usage-quota",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert qr.status_code == 200, qr.text
    body = qr.json()
    assert body["bot_id"] == str(bot_id)
    assert body["bot_daily"]["enforced"] is True
    assert body["bot_daily"]["cap_tokens"] == 500
    assert body["bot_daily"]["used_tokens"] >= 600
