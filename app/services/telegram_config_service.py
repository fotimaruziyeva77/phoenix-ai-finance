"""
Owner-scoped Telegram channel provisioning: explicit states, token verify, encrypted storage, webhooks.

**States (API ``channel_status``)** — ``draft`` is returned when no ``telegram_configs`` row exists;
persisted rows use ``provisioning_status`` on :class:`~app.models.telegram_config.TelegramConfig`.

* **connect** — Verifies token with Telegram, rejects duplicate Telegram bot IDs on other bots,
  encrypts token, calls ``setWebhook``, then marks ``active`` only after Telegram accepts the webhook.
* **start_provisioning** — Creates (or re-opens) a pending row without a token (``channel_pending``).
* **sync_webhook** — Re-runs ``setWebhook`` for an already stored token (recovery / URL change).
* **Disconnect** — ``deleteWebhook`` when a plaintext token exists, then delete the row.
"""

from __future__ import annotations

import hmac
import secrets
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.telegram_channel_events import (
    TELEGRAM_CONNECT_FAILURE,
    TELEGRAM_CONNECT_SUCCESS,
    TELEGRAM_PROVISIONING_STARTED,
    TELEGRAM_TOKEN_VALIDATE_SUCCESS,
    TELEGRAM_WEBHOOK_SYNC_FAILURE,
    TELEGRAM_WEBHOOK_SYNC_SUCCESS,
    emit_telegram_channel_event,
)
from app.domain.telegram_channel_status import (
    PROVISIONING_LAST_ERROR_META_KEY,
    TELEGRAM_PROVISIONING_ACTIVE,
    TELEGRAM_PROVISIONING_CHANNEL_PENDING,
    TELEGRAM_PROVISIONING_FAILED_VALIDATION,
)
from app.integrations.telegram_bot_api.errors import TelegramBotApiError
from app.integrations.telegram_bot_verify import (
    TelegramBotVerificationResult,
    TelegramTokenVerificationError,
    verify_telegram_bot_token_with_client,
)
from app.integrations.telegram_bot_verify import (
    verify_telegram_bot_token as http_verify_telegram_bot_token,
)
from app.integrations.telegram_webhook_registration import (
    delete_telegram_bot_webhook,
    set_telegram_bot_webhook,
)
from app.integrations.telegram_webhook_urls import (
    build_telegram_webhook_url,
    normalize_public_api_base_url,
    public_base_url_allowed_for_telegram_webhook,
)
from app.lib.integration_secrets_crypto import (
    IntegrationSecretCryptoError,
    IntegrationSecretKeyConfigurationError,
    decrypt_integration_secret,
    encrypt_integration_secret,
)
from app.lib.telegram_token_crypto import (
    TelegramTokenConfigurationError,
    TelegramTokenCryptoError,
    decrypt_telegram_bot_token,
    encrypt_telegram_bot_token,
)
from app.models.bot import Bot
from app.models.telegram_config import TelegramConfig
from app.models.user import User
from app.repositories.bot_repository import BotRepository
from app.schemas.telegram_config import (
    BotTelegramStatusResponse,
    TelegramConfigRead,
    TelegramWebhookBulkResyncItem,
    TelegramWebhookBulkResyncResponse,
    bot_telegram_status_disconnected,
    bot_telegram_status_from_orm_row,
    telegram_row_has_stored_token,
)
from app.services.bot_exceptions import BotForbiddenError, BotNotFoundError
from app.services.telegram_config_exceptions import (
    TelegramBotAlreadyAttachedError,
    TelegramChannelNotReadyError,
    TelegramConfigNotFoundError,
    TelegramConfigPersistenceError,
    TelegramConfigServiceError,
    TelegramFernetKeyNotConfiguredError,
    TelegramPublicBaseUrlNotConfiguredError,
    TelegramTokenDecryptError,
    TelegramTokenInvalidError,
    TelegramWebhookClearError,
    TelegramWebhookRegistrationError,
)

VerifyTokenFn = Callable[..., Awaitable[TelegramBotVerificationResult]]
SetBotWebhookFn = Callable[[str, str, str], Awaitable[None]]
DeleteBotWebhookFn = Callable[[str], Awaitable[None]]

_LOG = get_logger(__name__)


async def _default_set_bot_webhook(token: str, url: str, secret: str) -> None:
    await set_telegram_bot_webhook(bot_token=token, webhook_https_url=url, secret_token=secret)


async def _default_delete_bot_webhook(token: str) -> None:
    await delete_telegram_bot_webhook(bot_token=token)


class TelegramConfigService:
    def __init__(
        self,
        session: AsyncSession,
        bot_repo: BotRepository,
        settings: Settings,
        *,
        verify_token: VerifyTokenFn | None = None,
        set_bot_webhook: SetBotWebhookFn | None = None,
        delete_bot_webhook: DeleteBotWebhookFn | None = None,
    ) -> None:
        self._session = session
        self._bots = bot_repo
        self._settings = settings
        self._verify_token: VerifyTokenFn = verify_token or http_verify_telegram_bot_token
        self._set_bot_webhook: SetBotWebhookFn = set_bot_webhook or _default_set_bot_webhook
        self._delete_bot_webhook: DeleteBotWebhookFn = delete_bot_webhook or _default_delete_bot_webhook

    @staticmethod
    def _is_telegram_channel_live(row: TelegramConfig) -> bool:
        return (
            telegram_row_has_stored_token(row)
            and row.is_connected
            and (row.provisioning_status or "") == TELEGRAM_PROVISIONING_ACTIVE
        )

    async def _telegram_id_attached_elsewhere(
        self,
        *,
        telegram_bot_id: int,
        exclude_bot_id: uuid.UUID,
    ) -> bool:
        tid = str(int(telegram_bot_id))
        stmt = (
            select(TelegramConfig.id)
            .where(
                TelegramConfig.bot_id != exclude_bot_id,
                TelegramConfig.metadata_json["telegram_bot_id"].as_string() == tid,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _upsert_failed_validation_row(
        self,
        owner: User,
        bot_id: uuid.UUID,
        *,
        error_code: str,
    ) -> None:
        row = await self._get_config_row(owner_id=owner.id, bot_id=bot_id)
        meta: dict[str, object] = dict(row.metadata_json or {}) if row else {}
        meta[PROVISIONING_LAST_ERROR_META_KEY] = error_code
        meta.pop("telegram_bot_id", None)
        if row is None:
            row = TelegramConfig(
                bot_id=bot_id,
                owner_id=owner.id,
                bot_token_encrypted=None,
                bot_username=None,
                webhook_url=None,
                webhook_secret_token_encrypted=None,
                is_connected=False,
                last_verified_at=None,
                metadata_json=meta,
                provisioning_status=TELEGRAM_PROVISIONING_FAILED_VALIDATION,
            )
            self._session.add(row)
        else:
            row.provisioning_status = TELEGRAM_PROVISIONING_FAILED_VALIDATION
            row.is_connected = False
            row.bot_token_encrypted = None
            row.bot_username = None
            row.webhook_url = None
            row.webhook_secret_token_encrypted = None
            row.last_verified_at = None
            row.metadata_json = meta
        try:
            await self._session.flush()
            await self._session.refresh(row)
            await self._bots.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise TelegramConfigPersistenceError() from exc

        emit_telegram_channel_event(
            telegram_event="telegram_provisioning_failed_validation",
            level="warning",
            bot_id=bot_id,
            telegram_config_id=row.id,
            error_code=error_code,
        )

    async def _mark_webhook_registration_failed(self, row: TelegramConfig) -> None:
        row.is_connected = False
        row.provisioning_status = TELEGRAM_PROVISIONING_CHANNEL_PENDING
        meta = dict(row.metadata_json or {})
        meta[PROVISIONING_LAST_ERROR_META_KEY] = "telegram_webhook_registration_failed"
        row.metadata_json = meta
        try:
            await self._session.flush()
            await self._session.refresh(row)
            await self._bots.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise TelegramConfigPersistenceError() from exc

        emit_telegram_channel_event(
            telegram_event="telegram_webhook_registration_failed_persisted",
            level="warning",
            bot_id=row.bot_id,
            telegram_config_id=row.id,
            error_code="telegram_webhook_registration_failed",
        )

    async def start_telegram_channel_provisioning(
        self,
        owner: User,
        bot_id: uuid.UUID,
    ) -> BotTelegramStatusResponse:
        await self._ensure_bot_owned(owner, bot_id)
        row = await self._get_config_row(owner_id=owner.id, bot_id=bot_id)
        if row is not None and self._is_telegram_channel_live(row):
            return bot_telegram_status_from_orm_row(row)

        if row is None:
            row = TelegramConfig(
                bot_id=bot_id,
                owner_id=owner.id,
                bot_token_encrypted=None,
                bot_username=None,
                webhook_url=None,
                webhook_secret_token_encrypted=None,
                is_connected=False,
                last_verified_at=None,
                metadata_json=None,
                provisioning_status=TELEGRAM_PROVISIONING_CHANNEL_PENDING,
            )
            self._session.add(row)
        elif row.provisioning_status == TELEGRAM_PROVISIONING_FAILED_VALIDATION:
            row.provisioning_status = TELEGRAM_PROVISIONING_CHANNEL_PENDING
            meta = dict(row.metadata_json or {})
            meta.pop(PROVISIONING_LAST_ERROR_META_KEY, None)
            row.metadata_json = meta or None

        try:
            await self._session.flush()
            await self._session.refresh(row)
            await self._bots.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise TelegramConfigPersistenceError() from exc

        emit_telegram_channel_event(
            telegram_event=TELEGRAM_PROVISIONING_STARTED,
            bot_id=bot_id,
            telegram_config_id=row.id,
            extra={"channel_status": "channel_pending", "configured": False},
        )
        return bot_telegram_status_from_orm_row(row)

    async def sync_telegram_webhook_for_bot(
        self,
        owner: User,
        bot_id: uuid.UUID,
    ) -> BotTelegramStatusResponse:
        await self._ensure_bot_owned(owner, bot_id)
        row = await self._get_config_row(owner_id=owner.id, bot_id=bot_id)
        if row is None or not telegram_row_has_stored_token(row):
            raise TelegramChannelNotReadyError()

        base = normalize_public_api_base_url(self._settings.public_api_base_url)
        if base is None or not public_base_url_allowed_for_telegram_webhook(
            base_url=base,
            environment=self._settings.environment,
        ):
            raise TelegramPublicBaseUrlNotConfiguredError()

        full_webhook_url = build_telegram_webhook_url(base, bot_id)
        row.webhook_url = full_webhook_url

        plain = self.decrypt_stored_bot_token(row)
        enc_secret = (row.webhook_secret_token_encrypted or "").strip()
        secret_plain: str
        if enc_secret:
            try:
                secret_plain = decrypt_integration_secret(enc_secret, self._settings)
            except IntegrationSecretKeyConfigurationError as exc:
                raise TelegramFernetKeyNotConfiguredError(message=str(exc)) from exc
            except IntegrationSecretCryptoError:
                secret_plain = secrets.token_hex(32)
                try:
                    row.webhook_secret_token_encrypted = encrypt_integration_secret(
                        secret_plain, self._settings
                    )
                except IntegrationSecretKeyConfigurationError as exc:
                    raise TelegramFernetKeyNotConfiguredError(message=str(exc)) from exc
                except IntegrationSecretCryptoError as exc:
                    raise TelegramConfigPersistenceError() from exc
        else:
            secret_plain = secrets.token_hex(32)
            try:
                row.webhook_secret_token_encrypted = encrypt_integration_secret(
                    secret_plain, self._settings
                )
            except IntegrationSecretKeyConfigurationError as exc:
                raise TelegramFernetKeyNotConfiguredError(message=str(exc)) from exc
            except IntegrationSecretCryptoError as exc:
                raise TelegramConfigPersistenceError() from exc

        try:
            await self._session.flush()
            await self._session.refresh(row)
            await self._bots.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise TelegramConfigPersistenceError() from exc

        try:
            await self._set_bot_webhook(plain, full_webhook_url, secret_plain)
        except TelegramBotApiError as exc:
            await self._mark_webhook_registration_failed(row)
            emit_telegram_channel_event(
                telegram_event=TELEGRAM_WEBHOOK_SYNC_FAILURE,
                level="warning",
                bot_id=bot_id,
                telegram_config_id=row.id,
                error_code="telegram_webhook_registration_failed",
            )
            raise TelegramWebhookRegistrationError() from exc

        row.is_connected = True
        row.provisioning_status = TELEGRAM_PROVISIONING_ACTIVE
        meta = dict(row.metadata_json or {})
        meta.pop(PROVISIONING_LAST_ERROR_META_KEY, None)
        row.metadata_json = meta or None
        now = datetime.now(UTC).replace(microsecond=0)
        row.last_verified_at = now
        try:
            await self._session.flush()
            await self._session.refresh(row)
            await self._bots.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise TelegramConfigPersistenceError() from exc

        emit_telegram_channel_event(
            telegram_event=TELEGRAM_WEBHOOK_SYNC_SUCCESS,
            bot_id=bot_id,
            telegram_config_id=row.id,
            extra={"channel_status": "active", "configured": True},
        )
        return bot_telegram_status_from_orm_row(row)

    async def resync_all_telegram_webhooks_for_owner(
        self,
        owner: User,
    ) -> TelegramWebhookBulkResyncResponse:
        """
        Re-register Telegram webhooks for every live bot in this workspace.

        Uses the current ``APP_PUBLIC_API_BASE_URL`` (and stored encrypted tokens/secrets).
        Typical use: local/staging tunnel URL changed — call from dashboard without manual curl.
        """
        stmt = (
            select(TelegramConfig.bot_id)
            .join(Bot, Bot.id == TelegramConfig.bot_id)
            .where(
                TelegramConfig.owner_id == owner.id,
                TelegramConfig.is_connected.is_(True),
                TelegramConfig.provisioning_status == TELEGRAM_PROVISIONING_ACTIVE,
                Bot.status != "archived",
                TelegramConfig.bot_token_encrypted.isnot(None),
                TelegramConfig.bot_token_encrypted != "",
            )
            .order_by(TelegramConfig.bot_id)
        )
        result = await self._session.execute(stmt)
        bot_ids = [row[0] for row in result.all()]

        results: list[TelegramWebhookBulkResyncItem] = []
        succeeded = 0
        for bid in bot_ids:
            try:
                await self.sync_telegram_webhook_for_bot(owner, bid)
                results.append(TelegramWebhookBulkResyncItem(bot_id=bid, success=True))
                succeeded += 1
            except TelegramConfigServiceError as exc:
                code = type(exc).code
                results.append(
                    TelegramWebhookBulkResyncItem(
                        bot_id=bid,
                        success=False,
                        error_code=str(code),
                        error_message=exc.message,
                    )
                )

        failed = len(results) - succeeded
        _LOG.info(
            "telegram_webhook_bulk_resync_complete",
            owner_id=str(owner.id),
            eligible_count=len(bot_ids),
            succeeded=succeeded,
            failed=failed,
        )
        return TelegramWebhookBulkResyncResponse(
            eligible_count=len(bot_ids),
            succeeded=succeeded,
            failed=failed,
            results=results,
        )

    async def connect_telegram_for_bot(
        self,
        owner: User,
        bot_id: uuid.UUID,
        token: str,
    ) -> TelegramConfigRead:
        try:
            read = await self._connect_telegram_for_bot_impl(owner, bot_id, token)
        except TelegramConfigServiceError as exc:
            emit_telegram_channel_event(
                telegram_event=TELEGRAM_CONNECT_FAILURE,
                level="warning",
                bot_id=bot_id,
                error_code=exc.code,
            )
            raise
        api_uid = read.metadata_json.get("telegram_bot_id") if read.metadata_json else None
        tid = api_uid if isinstance(api_uid, int) else None
        emit_telegram_channel_event(
            telegram_event=TELEGRAM_CONNECT_SUCCESS,
            bot_id=bot_id,
            telegram_config_id=read.id,
            telegram_bot_api_user_id=tid,
            extra={
                "provisioning_status": TELEGRAM_PROVISIONING_ACTIVE,
                "channel_status": "active",
                "is_connected": True,
            },
        )
        return read

    async def _connect_telegram_for_bot_impl(
        self,
        owner: User,
        bot_id: uuid.UUID,
        token: str,
    ) -> TelegramConfigRead:
        await self._ensure_bot_owned(owner, bot_id)
        plain = (token or "").strip()
        row_existing = await self._get_config_row(owner_id=owner.id, bot_id=bot_id)
        has_stored = row_existing is not None and telegram_row_has_stored_token(row_existing)

        if len(plain) < 10:
            if not has_stored:
                await self._upsert_failed_validation_row(
                    owner,
                    bot_id,
                    error_code="telegram_token_invalid",
                )
            raise TelegramTokenInvalidError()

        try:
            verified = await self._verify_token(plain)
        except TelegramTokenVerificationError as exc:
            if not has_stored:
                await self._upsert_failed_validation_row(
                    owner,
                    bot_id,
                    error_code="telegram_token_invalid",
                )
            raise TelegramTokenInvalidError() from exc

        if await self._telegram_id_attached_elsewhere(
            telegram_bot_id=verified.telegram_bot_id,
            exclude_bot_id=bot_id,
        ):
            raise TelegramBotAlreadyAttachedError()

        try:
            ciphertext = encrypt_telegram_bot_token(plain, self._settings)
        except TelegramTokenConfigurationError as exc:
            raise TelegramFernetKeyNotConfiguredError(message=str(exc)) from exc
        except TelegramTokenCryptoError as exc:
            raise TelegramConfigPersistenceError() from exc

        assert plain not in ciphertext

        base = normalize_public_api_base_url(self._settings.public_api_base_url)
        if base is None or not public_base_url_allowed_for_telegram_webhook(
            base_url=base,
            environment=self._settings.environment,
        ):
            raise TelegramPublicBaseUrlNotConfiguredError()

        secret_plain = secrets.token_hex(32)
        try:
            secret_cipher = encrypt_integration_secret(secret_plain, self._settings)
        except IntegrationSecretKeyConfigurationError as exc:
            raise TelegramFernetKeyNotConfiguredError(message=str(exc)) from exc
        except IntegrationSecretCryptoError as exc:
            raise TelegramConfigPersistenceError() from exc

        full_webhook_url = build_telegram_webhook_url(base, bot_id)
        row = row_existing
        meta: dict[str, object] = dict(row.metadata_json or {}) if row else {}
        meta["telegram_bot_id"] = verified.telegram_bot_id
        meta.pop(PROVISIONING_LAST_ERROR_META_KEY, None)

        now = datetime.now(UTC).replace(microsecond=0)
        if row is None:
            row = TelegramConfig(
                bot_id=bot_id,
                owner_id=owner.id,
                bot_token_encrypted=ciphertext,
                bot_username=verified.username,
                webhook_url=full_webhook_url,
                webhook_secret_token_encrypted=secret_cipher,
                is_connected=False,
                last_verified_at=now,
                metadata_json=meta,
                provisioning_status=TELEGRAM_PROVISIONING_CHANNEL_PENDING,
            )
            self._session.add(row)
        else:
            row.bot_token_encrypted = ciphertext
            row.bot_username = verified.username
            row.webhook_url = full_webhook_url
            row.webhook_secret_token_encrypted = secret_cipher
            row.is_connected = False
            row.last_verified_at = now
            row.metadata_json = meta
            row.provisioning_status = TELEGRAM_PROVISIONING_CHANNEL_PENDING

        try:
            await self._session.flush()
            await self._session.refresh(row)
            await self._bots.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise TelegramConfigPersistenceError() from exc

        try:
            await self._set_bot_webhook(plain, full_webhook_url, secret_plain)
        except TelegramBotApiError as exc:
            await self._mark_webhook_registration_failed(row)
            raise TelegramWebhookRegistrationError() from exc

        row.is_connected = True
        row.provisioning_status = TELEGRAM_PROVISIONING_ACTIVE
        meta_ok = dict(row.metadata_json or {})
        meta_ok.pop(PROVISIONING_LAST_ERROR_META_KEY, None)
        row.metadata_json = meta_ok or None
        try:
            await self._session.flush()
            await self._session.refresh(row)
            await self._bots.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise TelegramConfigPersistenceError() from exc

        bot_row = await self._bots.get_bot_by_id(owner_id=owner.id, bot_id=bot_id)
        if (
            bot_row is not None
            and bot_row.status == "channel_pending"
            and (bot_row.primary_channel or "") in ("telegram", "both")
        ):
            bot_row.status = "active"
            try:
                await self._session.flush()
                await self._bots.commit()
            except SQLAlchemyError as exc:
                await self._session.rollback()
                raise TelegramConfigPersistenceError() from exc

        return TelegramConfigRead.model_validate(row)

    async def get_telegram_config_for_bot(
        self,
        owner: User,
        bot_id: uuid.UUID,
    ) -> TelegramConfigRead | None:
        await self._ensure_bot_owned(owner, bot_id)
        row = await self._get_config_row(owner_id=owner.id, bot_id=bot_id)
        if row is None:
            return None
        return TelegramConfigRead.model_validate(row)

    async def get_telegram_integration_status(
        self,
        owner: User,
        bot_id: uuid.UUID,
    ) -> BotTelegramStatusResponse:
        """Safe status for owner dashboard (no secrets)."""
        await self._ensure_bot_owned(owner, bot_id)
        row = await self._get_config_row(owner_id=owner.id, bot_id=bot_id)
        if row is None:
            return bot_telegram_status_disconnected()
        return bot_telegram_status_from_orm_row(row)

    async def disconnect_telegram_for_bot(self, owner: User, bot_id: uuid.UUID) -> None:
        await self._ensure_bot_owned(owner, bot_id)
        row = await self._get_config_row(owner_id=owner.id, bot_id=bot_id)
        if row is None:
            raise TelegramConfigNotFoundError()

        if telegram_row_has_stored_token(row):
            try:
                plain_token = self.decrypt_stored_bot_token(row)
            except TelegramTokenDecryptError:
                plain_token = None
            if plain_token:
                try:
                    await self._delete_bot_webhook(plain_token)
                except TelegramBotApiError as exc:
                    raise TelegramWebhookClearError() from exc

        try:
            await self._session.delete(row)
            await self._bots.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise TelegramConfigPersistenceError() from exc

    async def verify_telegram_webhook_request(
        self,
        bot_id: uuid.UUID,
        *,
        secret_header_value: str | None,
    ) -> bool:
        """
        Public ingress: validate ``X-Telegram-Bot-Api-Secret-Token`` for this ``bot_id``.

        No owner context; authorization is the shared secret issued at connect time.
        """
        stmt = select(TelegramConfig).where(TelegramConfig.bot_id == bot_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return False
        if not self._is_telegram_channel_live(row):
            return False
        enc = (row.webhook_secret_token_encrypted or "").strip()
        if not enc:
            return False
        try:
            expected = decrypt_integration_secret(enc, self._settings)
        except IntegrationSecretCryptoError:
            return False
        if secret_header_value is None:
            return False
        if len(secret_header_value) > 256:
            return False
        return hmac.compare_digest(expected, secret_header_value)

    async def verify_telegram_bot_token(
        self,
        token: str,
        *,
        httpx_client: httpx.AsyncClient | None = None,
    ) -> TelegramBotVerificationResult:
        """
        Verify a token with Telegram (e.g. dry-run before connect). Does not persist.

        When ``httpx_client`` is provided, it is used for the request (tests); otherwise a
        short-lived client is created.
        """
        plain = (token or "").strip()
        if len(plain) < 10:
            raise TelegramTokenInvalidError()
        try:
            if httpx_client is not None:
                return await verify_telegram_bot_token_with_client(httpx_client, plain)
            return await http_verify_telegram_bot_token(plain)
        except TelegramTokenVerificationError as exc:
            raise TelegramTokenInvalidError() from exc

    async def validate_telegram_token_for_bot(
        self,
        owner: User,
        bot_id: uuid.UUID,
        token: str,
    ) -> TelegramBotVerificationResult:
        """
        Verify token with Telegram and ensure this Telegram bot is not attached to another
        BotForge bot. Does not persist credentials or call setWebhook.
        """
        await self._ensure_bot_owned(owner, bot_id)
        verified = await self.verify_telegram_bot_token(token)
        if await self._telegram_id_attached_elsewhere(
            telegram_bot_id=verified.telegram_bot_id,
            exclude_bot_id=bot_id,
        ):
            raise TelegramBotAlreadyAttachedError()
        emit_telegram_channel_event(
            telegram_event=TELEGRAM_TOKEN_VALIDATE_SUCCESS,
            bot_id=bot_id,
            telegram_bot_api_user_id=verified.telegram_bot_id,
            extra={"bot_username": verified.username},
        )
        return verified

    async def update_telegram_webhook_metadata(
        self,
        owner: User,
        bot_id: uuid.UUID,
        *,
        webhook_url: str | None = None,
        metadata_json: dict[str, object] | None = None,
    ) -> TelegramConfigRead:
        """Update webhook URL and/or replace extension metadata (owner must have an existing row)."""
        await self._ensure_bot_owned(owner, bot_id)
        row = await self._get_config_row(owner_id=owner.id, bot_id=bot_id)
        if row is None:
            raise TelegramConfigNotFoundError()

        if webhook_url is None and metadata_json is None:
            return TelegramConfigRead.model_validate(row)

        if webhook_url is not None:
            w = webhook_url.strip()
            row.webhook_url = w if w else None

        if metadata_json is not None:
            row.metadata_json = metadata_json

        try:
            await self._session.flush()
            await self._session.refresh(row)
            await self._bots.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise TelegramConfigPersistenceError() from exc

        return TelegramConfigRead.model_validate(row)

    def decrypt_stored_bot_token(self, row: TelegramConfig) -> str:
        """
        Decrypt token for internal use (webhook registration, outbound API). Never expose in APIs/logs.
        """
        enc = (row.bot_token_encrypted or "").strip()
        if not enc:
            raise TelegramTokenDecryptError()
        try:
            return decrypt_telegram_bot_token(enc, self._settings)
        except TelegramTokenConfigurationError as exc:
            raise TelegramFernetKeyNotConfiguredError(message=str(exc)) from exc
        except TelegramTokenCryptoError as exc:
            raise TelegramTokenDecryptError() from exc

    async def _get_config_row(self, *, owner_id: uuid.UUID, bot_id: uuid.UUID) -> TelegramConfig | None:
        stmt = select(TelegramConfig).where(
            TelegramConfig.bot_id == bot_id,
            TelegramConfig.owner_id == owner_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _ensure_bot_owned(self, owner: User, bot_id: uuid.UUID) -> None:
        bot = await self._bots.get_bot_by_id(owner_id=owner.id, bot_id=bot_id)
        if bot is not None:
            return
        if await self._bots.exists_by_id(bot_id=bot_id):
            raise BotForbiddenError()
        raise BotNotFoundError()
