"""Persistence for conversations, chat messages, and AI usage logs."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.chat_channels import CONVERSATION_CHANNEL_TELEGRAM, CONVERSATION_CHANNEL_WEB_WIDGET
from app.lib.telegram_collected_hints import merge_telegram_sender_into_collected
from app.models.ai_foundation import AIUsageLog, Conversation, Message


class AIChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """Shared SQLAlchemy session (e.g. for :class:`~app.repositories.lead_repository.LeadRepository`)."""

        return self._session

    async def get_conversation_for_bot_owner(
        self,
        *,
        conversation_id: uuid.UUID,
        bot_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> Conversation | None:
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.bot_id == bot_id,
            Conversation.owner_id == owner_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_conversation(
        self,
        *,
        bot_id: uuid.UUID,
        owner_id: uuid.UUID,
        channel: str | None = None,
        niche_id_snapshot: str | None = None,
        public_visitor_session_key: str | None = None,
        visitor_client_hint: str | None = None,
        telegram_chat_id: int | None = None,
    ) -> Conversation:
        conv = Conversation(
            bot_id=bot_id,
            owner_id=owner_id,
            channel=channel,
            status="active",
            niche_id_snapshot=niche_id_snapshot,
            public_visitor_session_key=public_visitor_session_key,
            visitor_client_hint=visitor_client_hint,
            telegram_chat_id=telegram_chat_id,
        )
        self._session.add(conv)
        await self._session.flush()
        await self._session.refresh(conv)
        return conv

    async def get_active_conversation_for_channel(
        self,
        *,
        bot_id: uuid.UUID,
        channel: str,
        public_visitor_session_key: str | None = None,
        telegram_chat_id: int | None = None,
    ) -> Conversation | None:
        """
        Resolve an **active** thread for channels that carry an external thread key.

        ``admin_test`` threads are not looked up here (no external key on the row). When adding a
        channel, extend the branches below and keep adapter code thin.
        """
        if channel == CONVERSATION_CHANNEL_WEB_WIDGET:
            if not public_visitor_session_key:
                raise ValueError("web_widget requires public_visitor_session_key")
            stmt = (
                select(Conversation)
                .where(
                    Conversation.bot_id == bot_id,
                    Conversation.channel == CONVERSATION_CHANNEL_WEB_WIDGET,
                    Conversation.public_visitor_session_key == public_visitor_session_key,
                    Conversation.status == "active",
                )
                .limit(1)
            )
        elif channel == CONVERSATION_CHANNEL_TELEGRAM:
            if telegram_chat_id is None:
                raise ValueError("telegram requires telegram_chat_id")
            stmt = (
                select(Conversation)
                .where(
                    Conversation.bot_id == bot_id,
                    Conversation.channel == CONVERSATION_CHANNEL_TELEGRAM,
                    Conversation.telegram_chat_id == telegram_chat_id,
                    Conversation.status == "active",
                )
                .limit(1)
            )
        else:
            raise ValueError(
                f"Unsupported channel for external thread lookup: {channel!r}. "
                "Add a branch in get_active_conversation_for_channel or use another query.",
            )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_web_widget_conversation(
        self,
        *,
        bot_id: uuid.UUID,
        public_visitor_session_key: str,
    ) -> Conversation | None:
        return await self.get_active_conversation_for_channel(
            bot_id=bot_id,
            channel=CONVERSATION_CHANNEL_WEB_WIDGET,
            public_visitor_session_key=public_visitor_session_key,
        )

    async def get_active_telegram_conversation(
        self,
        *,
        bot_id: uuid.UUID,
        telegram_chat_id: int,
    ) -> Conversation | None:
        return await self.get_active_conversation_for_channel(
            bot_id=bot_id,
            channel=CONVERSATION_CHANNEL_TELEGRAM,
            telegram_chat_id=telegram_chat_id,
        )

    async def merge_telegram_collected_hints(
        self,
        conversation_id: uuid.UUID,
        *,
        from_username: str | None,
        from_first_name: str | None,
    ) -> None:
        """
        Persist optional ``from`` user fields into ``collected_data_json`` before the AI turn.

        Ensures :mod:`app.services.sales_lead_capture_turn` and lead creation see Telegram-derived
        display hints without channel-specific CRM code.
        """
        stmt = select(Conversation).where(Conversation.id == conversation_id).limit(1)
        result = await self._session.execute(stmt)
        conv = result.scalar_one_or_none()
        if conv is None:
            return
        new_data, changed = merge_telegram_sender_into_collected(
            conv.collected_data_json,
            from_username=from_username,
            from_first_name=from_first_name,
        )
        if not changed:
            return
        await self._session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(collected_data_json=new_data, updated_at=func.now())
        )
        await self._session.flush()

    async def list_messages_chronological(
        self,
        *,
        conversation_id: uuid.UUID,
        bot_id: uuid.UUID,
    ) -> list[Message]:
        """All messages for a conversation, oldest first (dashboard / admin review)."""
        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.bot_id == bot_id,
            )
            .order_by(Message.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_recent_history_messages(
        self,
        *,
        conversation_id: uuid.UUID,
        limit: int,
    ) -> list[Message]:
        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.role.in_(("user", "assistant")),
            )
            .order_by(Message.created_at.desc())
            .limit(max(1, limit))
        )
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        rows.reverse()
        return rows

    async def add_message(
        self,
        *,
        conversation_id: uuid.UUID,
        bot_id: uuid.UUID,
        role: str,
        content: str,
        model_name: str | None = None,
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        tokens_total: int | None = None,
        latency_ms: int | None = None,
        cost_usd: Decimal | None = None,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            bot_id=bot_id,
            role=role,
            content=content,
            model_name=model_name,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            tokens_total=tokens_total,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
        )
        self._session.add(msg)
        await self._session.flush()
        await self._session.refresh(msg)
        await self._stamp_conversation_message_activity(
            conversation_id=conversation_id,
            role=role,
            message_created_at=msg.created_at,
        )
        return msg

    async def _stamp_conversation_message_activity(
        self,
        *,
        conversation_id: uuid.UUID,
        role: str,
        message_created_at: datetime,
    ) -> None:
        """Keep conversation last-role timestamps aligned with persisted messages."""
        values: dict[str, object] = {"updated_at": func.now()}
        if role == "user":
            values["last_user_message_at"] = message_created_at
        elif role == "assistant":
            values["last_assistant_message_at"] = message_created_at
        await self._session.execute(
            update(Conversation).where(Conversation.id == conversation_id).values(**values)
        )

    async def add_usage_log(
        self,
        *,
        bot_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
        message_id: uuid.UUID | None,
        provider_name: str,
        model_name: str,
        tokens_input: int,
        tokens_output: int,
        tokens_total: int,
        latency_ms: int | None,
        cost_usd: Decimal | None,
        success: bool,
        error_code: str | None,
        step_kind: str | None = None,
    ) -> AIUsageLog:
        row = AIUsageLog(
            bot_id=bot_id,
            conversation_id=conversation_id,
            message_id=message_id,
            provider_name=provider_name,
            model_name=model_name,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            tokens_total=tokens_total,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            success=success,
            error_code=error_code,
            step_kind=(step_kind.strip()[:32] if step_kind and str(step_kind).strip() else None),
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def touch_conversation_updated_at(self, conversation_id: uuid.UUID) -> None:
        await self._session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=func.now())
        )

    async def update_conversation_sales_flow(
        self,
        conversation_id: uuid.UUID,
        *,
        current_state: str | None = None,
        detected_intent: str | None = None,
        collected_data_json: dict[str, object] | None = None,
    ) -> None:
        """Patch sales-flow columns (intent classifier, state machine, collected slots)."""
        values: dict[str, object] = {"updated_at": func.now()}
        if current_state is not None:
            values["current_state"] = current_state
        if detected_intent is not None:
            values["detected_intent"] = detected_intent
        if collected_data_json is not None:
            values["collected_data_json"] = collected_data_json
        await self._session.execute(
            update(Conversation).where(Conversation.id == conversation_id).values(**values)
        )

    async def count_conversations_this_month_for_owner(
        self,
        owner_id: uuid.UUID,
        *,
        year: int,
        month: int,
    ) -> int:
        """Count distinct conversations created by this owner in the given calendar month (UTC)."""
        from sqlalchemy import extract

        # ``created_at`` is timestamptz; ``extract`` would otherwise use the session timezone.
        # Wrap with ``timezone('UTC', …)`` so month boundaries match the UTC year/month the
        # callers pass (mirrors ai_usage_aggregate_repository) — fixes wrong-month miscounting
        # of the monthly conversation plan limit on non-UTC database servers.
        created_at_utc = func.timezone("UTC", Conversation.created_at)
        result = await self._session.execute(
            select(func.count(Conversation.id)).where(
                Conversation.owner_id == owner_id,
                extract("year", created_at_utc) == year,
                extract("month", created_at_utc) == month,
            )
        )
        return result.scalar_one() or 0

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
