"""Ensure :class:`TelegramConfigService` exposes the provisioning port surface."""

from __future__ import annotations

from app.contracts.telegram_channel_provisioning import TelegramChannelProvisioningPort
from app.services.telegram_config_service import TelegramConfigService


def test_telegram_config_service_satisfies_provisioning_port() -> None:
    required = (
        "start_telegram_channel_provisioning",
        "connect_telegram_for_bot",
        "validate_telegram_token_for_bot",
        "sync_telegram_webhook_for_bot",
        "resync_all_telegram_webhooks_for_owner",
        "get_telegram_integration_status",
        "disconnect_telegram_for_bot",
        "verify_telegram_webhook_request",
    )
    for name in required:
        assert callable(getattr(TelegramConfigService, name, None)), name
    assert isinstance(TelegramConfigService, type)
    # Structural: instances implement the protocol at runtime.
    assert issubclass(TelegramConfigService, TelegramChannelProvisioningPort)
