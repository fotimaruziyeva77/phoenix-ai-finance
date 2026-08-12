"""Domain errors for Telegram configuration (owner dashboard flows)."""

from __future__ import annotations

from typing import ClassVar


class TelegramConfigServiceError(Exception):
    status_code: ClassVar[int] = 400
    code: ClassVar[str] = "telegram_config_error"
    default_message: ClassVar[str] = "Telegram configuration operation failed"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class TelegramConfigNotFoundError(TelegramConfigServiceError):
    status_code = 404
    code = "telegram_config_not_found"
    default_message = "Telegram is not connected for this bot"


class TelegramConfigPersistenceError(TelegramConfigServiceError):
    status_code = 500
    code = "telegram_config_persistence_error"
    default_message = "Could not persist Telegram configuration"


class TelegramTokenInvalidError(TelegramConfigServiceError):
    status_code = 422
    code = "telegram_token_invalid"
    default_message = "Telegram did not accept this bot token"


class TelegramTokenDecryptError(TelegramConfigServiceError):
    status_code = 500
    code = "telegram_token_decrypt_error"
    default_message = "Stored Telegram credentials could not be read"


class TelegramFernetKeyNotConfiguredError(TelegramConfigServiceError):
    status_code = 503
    code = "telegram_fernet_key_not_configured"
    default_message = (
        "Telegram at-rest encryption is not configured. Set APP_TELEGRAM_TOKEN_FERNET_KEY "
        "(or TELEGRAM_TOKEN_FERNET_KEY) to a Fernet key from Fernet.generate_key(); "
        "it is separate from JWT_SECRET_KEY."
    )


class TelegramPublicBaseUrlNotConfiguredError(TelegramConfigServiceError):
    status_code = 503
    code = "telegram_public_base_url_not_configured"
    default_message = (
        "Public API base URL is not configured or is not valid for Telegram webhooks "
        "(set APP_PUBLIC_API_BASE_URL to the HTTPS origin Telegram can reach)."
    )


class TelegramWebhookRegistrationError(TelegramConfigServiceError):
    status_code = 502
    code = "telegram_webhook_registration_failed"
    default_message = "Telegram webhook could not be registered. Try again in a moment."


class TelegramWebhookClearError(TelegramConfigServiceError):
    status_code = 503
    code = "telegram_webhook_clear_failed"
    default_message = "Could not remove the Telegram webhook. Try disconnect again shortly."


class TelegramBotAlreadyAttachedError(TelegramConfigServiceError):
    status_code = 409
    code = "telegram_bot_already_attached"
    default_message = "This Telegram bot is already connected to another BotForge bot."


class TelegramChannelNotReadyError(TelegramConfigServiceError):
    status_code = 400
    code = "telegram_channel_not_ready"
    default_message = "Telegram is not fully connected yet; complete token validation and webhook setup first."
