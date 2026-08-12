"""Bot management use-cases (owner-scoped CRUD lifecycle)."""

from __future__ import annotations

import uuid

from pydantic import ValidationError
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.telegram_channel_provisioning import TelegramChannelProvisioningPort
from app.core.logging import get_logger
from app.lib.niche_registry import get_default_welcome_message, validate_niche_id
from app.services.knowledge_template_seeder import seed_knowledge_templates
from app.models.user import User
from app.repositories.bot_repository import BotListFilters, BotRepository
from app.schemas.bots import ALLOWED_GOAL_TYPES, BotCreate, BotListItem, BotRead, BotUpdate
from app.services.audit_service import (
    BOT_ACTION_ARCHIVED,
    BOT_ACTION_CREATED,
    BOT_ACTION_DELETED,
    BOT_ACTION_UPDATED,
    BOT_ENTITY_TYPE,
    AuditService,
    bot_audit_snapshot,
)
from app.services.bot_exceptions import (
    BotDatabaseUnavailableError,
    BotForbiddenError,
    BotNotFoundError,
    BotPersistenceError,
    BotReadSerializationError,
    BotValidationError,
)
from app.services.telegram_config_exceptions import TelegramConfigServiceError

_LOG = get_logger("bot_service_audit")
_LOG_CREATE = get_logger(__name__)


def _sqlalchemy_cause_hint(exc: Exception | None) -> str | None:
    """Safe one-line hint for logs (no full SQL params)."""
    if exc is None:
        return None
    orig = getattr(exc, "orig", None)
    if orig is not None:
        s = str(orig).strip()
        if s:
            return s[:240]
    s2 = str(exc).strip()
    return s2[:240] if s2 else type(exc).__name__


_ALLOWED_BOT_STATUSES = frozenset({"draft", "active", "paused", "archived", "channel_pending"})


class BotService:
    def __init__(
        self,
        repo: BotRepository,
        audit_service: AuditService | None = None,
        *,
        telegram_service: TelegramChannelProvisioningPort | None = None,
        db_session: AsyncSession | None = None,
    ) -> None:
        self._repo = repo
        self._audit = audit_service
        self._telegram = telegram_service
        self._db_session = db_session
        self._allowed_goal_types = frozenset(ALLOWED_GOAL_TYPES)

    async def acquire_owner_create_lock(self, owner_id: uuid.UUID) -> None:
        """
        Take a per-owner transaction-scoped advisory lock so concurrent bot/PDF creations for the
        same owner serialize. Without this, two parallel requests both read the same pre-insert
        count and each pass the plan limit (TOCTOU), letting a user exceed ``bots_max``. The lock
        is released automatically when the request transaction ends. No-op if no session is wired.
        """
        if self._db_session is None:
            return
        await self._db_session.execute(
            text("SELECT pg_advisory_xact_lock(abs(hashtext('bot_create:' || CAST(:oid AS text))))"),
            {"oid": str(owner_id)},
        )

    async def create_bot_for_user(self, current_user: User, payload: BotCreate) -> BotRead:
        self._validate_niche_id(payload.niche_id)
        self._validate_goal_type(payload.goal_type)
        initial = payload.initial_channel
        token = payload.telegram_bot_token

        if initial is None:
            status = "draft"
            primary: str | None = None
        elif initial == "web":
            status = "active"
            primary = "web"
        else:
            primary = initial
            status = "channel_pending"

        # Auto-fill welcome message from niche defaults when not provided.
        welcome_msg = payload.welcome_message
        if not welcome_msg:
            welcome_msg = get_default_welcome_message(payload.niche_id, payload.language)

        try:
            bot = await self._repo.create_bot(
                owner_id=current_user.id,
                name=payload.name,
                niche_id=payload.niche_id,
                goal_type=payload.goal_type,
                status=status,
                primary_channel=primary,
                welcome_message=welcome_msg,
                tone=payload.tone,
                language=payload.language,
                short_description=payload.short_description,
                provider_name=payload.provider_name,
                model_name=payload.model_name,
                temperature=payload.temperature,
                max_output_tokens=payload.max_output_tokens,
            )

            # Seed niche FAQ templates into the bot's knowledge base.
            if self._db_session is not None:
                await seed_knowledge_templates(
                    self._db_session,
                    bot_id=bot.id,
                    owner_id=current_user.id,
                    niche_id=payload.niche_id,
                )

            await self._repo.commit()

            if initial in ("telegram", "both"):
                if self._telegram is None:
                    raise BotPersistenceError()
                try:
                    if token:
                        await self._telegram.connect_telegram_for_bot(current_user, bot.id, token)
                    else:
                        await self._telegram.start_telegram_channel_provisioning(current_user, bot.id)
                except TelegramConfigServiceError:
                    if await self._repo.delete_bot_owned(owner_id=current_user.id, bot_id=bot.id):
                        await self._repo.commit()
                    raise
                refreshed = await self._repo.get_bot_by_id(owner_id=current_user.id, bot_id=bot.id)
                if refreshed is not None:
                    bot = refreshed

            if self._audit is not None:
                after = bot_audit_snapshot(BotRead.model_validate(bot).model_dump())
                await self._safe_audit_log(
                    actor_user_id=current_user.id,
                    action=BOT_ACTION_CREATED,
                    entity_type=BOT_ENTITY_TYPE,
                    entity_id=bot.id,
                    after_snapshot=after,
                )
            return BotRead.model_validate(bot)
        except TelegramConfigServiceError:
            raise
        except OperationalError as exc:
            _LOG_CREATE.warning(
                "bot_create_operational_error",
                exc_type=type(exc).__name__,
                hint=_sqlalchemy_cause_hint(exc),
            )
            raise BotDatabaseUnavailableError() from exc
        except DBAPIError as exc:
            if getattr(exc, "connection_invalidated", False):
                _LOG_CREATE.warning(
                    "bot_create_connection_invalidated",
                    exc_type=type(exc).__name__,
                    hint=_sqlalchemy_cause_hint(exc),
                )
                raise BotDatabaseUnavailableError() from exc
            _LOG_CREATE.warning(
                "bot_create_dbapi_error",
                exc_type=type(exc).__name__,
                hint=_sqlalchemy_cause_hint(exc),
            )
            raise BotPersistenceError() from exc
        except IntegrityError as exc:
            _LOG_CREATE.warning(
                "bot_create_integrity_error",
                exc_type=type(exc).__name__,
                hint=_sqlalchemy_cause_hint(exc),
            )
            raise BotPersistenceError() from exc
        except SQLAlchemyError as exc:
            _LOG_CREATE.warning(
                "bot_create_sqlalchemy_error",
                exc_type=type(exc).__name__,
                hint=_sqlalchemy_cause_hint(exc),
            )
            raise BotPersistenceError() from exc
        except ValidationError as exc:
            _LOG_CREATE.error(
                "bot_create_botread_validation_failed",
                errors=exc.errors(),
            )
            raise BotReadSerializationError() from exc

    async def list_bots_for_user(self, current_user: User) -> list[BotListItem]:
        try:
            # MVP UX: keep archived bots visible (with status badge) to avoid
            # confusing "disappearing bot" behavior right after archive actions.
            rows = await self._repo.list_bots_by_owner(
                owner_id=current_user.id,
                filters=BotListFilters(include_archived=True),
            )
            return [
                BotListItem(
                    id=row.id,
                    name=row.name,
                    niche=row.niche_id,
                    niche_id=row.niche_id,
                    goal_type=row.goal_type,
                    status=row.status,
                    primary_channel=row.primary_channel,
                    channel_count=0,
                    updated_at=row.updated_at,
                )
                for row in rows
            ]
        except SQLAlchemyError as exc:
            raise BotPersistenceError() from exc

    async def get_bot_for_user(self, current_user: User, bot_id: uuid.UUID) -> BotRead:
        bot = await self._repo.get_bot_by_id(owner_id=current_user.id, bot_id=bot_id)
        if bot is not None:
            return BotRead.model_validate(bot)

        if await self._repo.exists_by_id(bot_id=bot_id):
            raise BotForbiddenError()
        raise BotNotFoundError()

    async def update_bot_for_user(
        self,
        current_user: User,
        bot_id: uuid.UUID,
        payload: BotUpdate,
    ) -> BotRead:
        updates = payload.model_dump(exclude_unset=True)
        provided_fields = set(updates.keys())

        # Non-nullable core fields should not accept explicit null on PATCH.
        for key in ("name", "niche_id", "goal_type", "status", "provider_name"):
            if key in updates and updates[key] is None:
                raise BotValidationError(f"{key} cannot be null")

        if "niche_id" in updates:
            self._validate_niche_id(str(updates["niche_id"]))
        if "goal_type" in updates:
            self._validate_goal_type(str(updates["goal_type"]))
        if "status" in updates and updates["status"] not in _ALLOWED_BOT_STATUSES:
            raise BotValidationError("status is invalid")

        before_row = await self._repo.get_bot_by_id(owner_id=current_user.id, bot_id=bot_id)
        if (
            before_row is not None
            and updates.get("status") == "active"
            and (before_row.primary_channel or "") in ("telegram", "both")
        ):
            if self._telegram is None:
                raise BotValidationError("Telegram integration is not available")
            tg_status = await self._telegram.get_telegram_integration_status(current_user, bot_id)
            if not tg_status.connected:
                raise BotValidationError(
                    "Cannot set bot to active until Telegram is connected with a valid token and webhook."
                )

        try:
            before_snapshot = (
                bot_audit_snapshot(BotRead.model_validate(before_row).model_dump())
                if before_row is not None
                else None
            )
            updated = await self._repo.update_bot(
                owner_id=current_user.id,
                bot_id=bot_id,
                provided_fields=provided_fields,
                name=updates.get("name"),
                niche_id=updates.get("niche_id"),
                goal_type=updates.get("goal_type"),
                status=updates.get("status"),
                welcome_message=updates.get("welcome_message"),
                tone=updates.get("tone"),
                language=updates.get("language"),
                short_description=updates.get("short_description"),
                provider_name=updates.get("provider_name"),
                model_name=updates.get("model_name"),
                temperature=updates.get("temperature"),
                max_output_tokens=updates.get("max_output_tokens"),
            )
            if updated is not None:
                await self._repo.commit()
                if self._audit is not None:
                    after = bot_audit_snapshot(BotRead.model_validate(updated).model_dump())
                    await self._safe_audit_log(
                        actor_user_id=current_user.id,
                        action=BOT_ACTION_UPDATED,
                        entity_type=BOT_ENTITY_TYPE,
                        entity_id=updated.id,
                        before_snapshot=before_snapshot,
                        after_snapshot=after,
                    )
                if (updated.primary_channel or "").strip() in ("telegram", "both"):
                    await self._best_effort_resync_telegram_webhook_after_bot_save(
                        current_user,
                        bot_id=updated.id,
                        primary_channel=updated.primary_channel,
                    )
                return BotRead.model_validate(updated)
        except (IntegrityError, SQLAlchemyError) as exc:
            raise BotPersistenceError() from exc

        if await self._repo.exists_by_id(bot_id=bot_id):
            raise BotForbiddenError()
        raise BotNotFoundError()

    async def _best_effort_resync_telegram_webhook_after_bot_save(
        self,
        user: User,
        *,
        bot_id: uuid.UUID,
        primary_channel: str | None,
    ) -> None:
        """After dashboard saves a Telegram-capable bot, refresh ``setWebhook`` for the current public API base URL."""
        if self._telegram is None:
            return
        if (primary_channel or "").strip() not in ("telegram", "both"):
            return
        try:
            st = await self._telegram.get_telegram_integration_status(user, bot_id)
            if not st.connected:
                return
            await self._telegram.sync_telegram_webhook_for_bot(user, bot_id)
            _LOG_CREATE.info(
                "bot_save_telegram_webhook_auto_resynced",
                bot_id=str(bot_id),
            )
        except TelegramConfigServiceError as exc:
            _LOG_CREATE.warning(
                "bot_save_telegram_webhook_auto_resync_failed",
                bot_id=str(bot_id),
                error_code=getattr(type(exc), "code", None),
            )
        except Exception as exc:
            _LOG_CREATE.warning(
                "bot_save_telegram_webhook_auto_resync_unexpected",
                bot_id=str(bot_id),
                exc_type=type(exc).__name__,
            )

    async def archive_bot_for_user(self, current_user: User, bot_id: uuid.UUID) -> BotRead:
        try:
            before_row = await self._repo.get_bot_by_id(owner_id=current_user.id, bot_id=bot_id)
            before_snapshot = (
                bot_audit_snapshot(BotRead.model_validate(before_row).model_dump())
                if before_row is not None
                else None
            )
            archived = await self._repo.archive_bot(owner_id=current_user.id, bot_id=bot_id)
            if archived is not None:
                await self._repo.commit()
                if self._audit is not None:
                    after = bot_audit_snapshot(BotRead.model_validate(archived).model_dump())
                    await self._safe_audit_log(
                        actor_user_id=current_user.id,
                        action=BOT_ACTION_ARCHIVED,
                        entity_type=BOT_ENTITY_TYPE,
                        entity_id=archived.id,
                        before_snapshot=before_snapshot,
                        after_snapshot=after,
                    )
                return BotRead.model_validate(archived)
        except (IntegrityError, SQLAlchemyError) as exc:
            raise BotPersistenceError() from exc

        if await self._repo.exists_by_id(bot_id=bot_id):
            raise BotForbiddenError()
        raise BotNotFoundError()

    async def delete_bot_for_user(self, current_user: User, bot_id: uuid.UUID) -> None:
        """Permanently delete a bot owned by ``current_user``."""
        try:
            before_row = await self._repo.get_bot_by_id(owner_id=current_user.id, bot_id=bot_id)
            before_snapshot = (
                bot_audit_snapshot(BotRead.model_validate(before_row).model_dump())
                if before_row is not None
                else None
            )
            deleted = await self._repo.delete_bot_owned(owner_id=current_user.id, bot_id=bot_id)
            if deleted:
                await self._repo.commit()
                if self._audit is not None and before_snapshot:
                    await self._safe_audit_log(
                        actor_user_id=current_user.id,
                        action=BOT_ACTION_DELETED,
                        entity_type=BOT_ENTITY_TYPE,
                        entity_id=bot_id,
                        before_snapshot=before_snapshot,
                    )
                return
        except (IntegrityError, SQLAlchemyError) as exc:
            raise BotPersistenceError() from exc

        if await self._repo.exists_by_id(bot_id=bot_id):
            raise BotForbiddenError()
        raise BotNotFoundError()

    async def clone_bot_for_user(
        self,
        current_user: User,
        bot_id: uuid.UUID,
    ) -> BotRead:
        """Duplicate a bot owned by ``current_user``, resetting it to ``draft`` status."""
        source = await self._repo.get_bot_by_id(owner_id=current_user.id, bot_id=bot_id)
        if source is None:
            if await self._repo.exists_by_id(bot_id=bot_id):
                raise BotForbiddenError()
            raise BotNotFoundError()

        try:
            cloned = await self._repo.create_bot(
                owner_id=current_user.id,
                name=f"{source.name} (copy)",
                niche_id=source.niche_id,
                goal_type=source.goal_type,
                status="draft",
                primary_channel=None,
                welcome_message=source.welcome_message,
                tone=source.tone,
                language=source.language,
                short_description=source.short_description,
                provider_name=source.provider_name,
                model_name=source.model_name,
                temperature=source.temperature,
                max_output_tokens=source.max_output_tokens,
            )
            await self._repo.commit()

            if self._audit is not None:
                after = bot_audit_snapshot(BotRead.model_validate(cloned).model_dump())
                await self._safe_audit_log(
                    actor_user_id=current_user.id,
                    action=BOT_ACTION_CREATED,
                    entity_type=BOT_ENTITY_TYPE,
                    entity_id=cloned.id,
                    after_snapshot=after,
                )
            return BotRead.model_validate(cloned)
        except (IntegrityError, SQLAlchemyError) as exc:
            raise BotPersistenceError() from exc

    async def list_bots_for_user_with_filters(
        self,
        current_user: User,
        *,
        filters: BotListFilters,
        limit: int = 50,
        offset: int = 0,
    ) -> list[BotListItem]:
        """Foundation hook for future search/filter API parameters."""
        try:
            rows = await self._repo.list_bots_by_owner(
                owner_id=current_user.id,
                filters=filters,
                limit=limit,
                offset=offset,
            )
            return [
                BotListItem(
                    id=row.id,
                    name=row.name,
                    niche=row.niche_id,
                    niche_id=row.niche_id,
                    goal_type=row.goal_type,
                    status=row.status,
                    primary_channel=row.primary_channel,
                    channel_count=0,
                    updated_at=row.updated_at,
                )
                for row in rows
            ]
        except SQLAlchemyError as exc:
            raise BotPersistenceError() from exc

    def _validate_niche_id(self, niche_id: str) -> None:
        if not validate_niche_id(niche_id):
            raise BotValidationError("niche_id is not supported")

    def _validate_goal_type(self, goal_type: str) -> None:
        if goal_type not in self._allowed_goal_types:
            raise BotValidationError("goal_type is invalid")

    async def _safe_audit_log(self, **kwargs) -> None:
        """
        Audit should not block primary lifecycle actions in MVP.
        Failures are logged for ops visibility and can be retried later.
        """
        if self._audit is None:
            return
        try:
            await self._audit.log_entity_event(**kwargs)
            await self._repo.commit()
        except Exception as exc:  # pragma: no cover - defensive hook boundary
            await self._repo.rollback()
            _LOG.warning("bot_audit_hook_failed", error=str(exc), action=str(kwargs.get("action")))
