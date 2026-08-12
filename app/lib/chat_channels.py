"""
Stable ``Conversation.channel`` string registry (multi-channel conversation core).

**Architecture (unified core, thin adapters)**

* **Core** — One :class:`~app.models.ai_foundation.Conversation` row per thread; ``channel`` plus
  channel-specific columns (``public_visitor_session_key``, ``telegram_chat_id``) identify the
  external thread. All turns flow through :class:`~app.services.ai_service.AIService` and, for
  sales bots, :class:`~app.services.sales_conversation_orchestrator.SalesConversationOrchestrator`.
  Lead capture reads ``conversation.channel`` into :attr:`~app.models.lead.Lead.source_channel`
  (see :mod:`app.services.sales_lead_capture_turn`) so CRM/analytics can segment by ingress without
  duplicating lead rules per channel. Owner Telegram alerts include that value as ``Source:`` in the
  formatted message (see :mod:`app.integrations.telegram.lead_alert_message`).

* **Adapters (thin)** — Resolve the right ``Conversation`` id, enforce transport policy, then call
  the shared AI service:

  * **Dashboard test chat** — :class:`~app.services.bot_chat_test_service.BotChatTestService` →
    ``AIService``; new threads get ``channel=admin_test``.
  * **Public widget** — :class:`~app.services.web_widget_session_service.WebWidgetSessionService`
    (session/thread) + :class:`~app.services.public_widget_chat_service.PublicWidgetChatService`
    (origin + ``AIService``).
  * **Telegram** — :class:`~app.services.conversation_thread_service.ConversationThreadService`
    (thread) + :class:`~app.services.telegram_webhook_inbound_service.TelegramWebhookInboundService`
    (parse + ``AIService`` + outbound reply).

* **Future channels** — Add a constant below, extend DB constraints if the channel needs new columns,
  add a small adapter + optional ``get_active_conversation_for_channel`` branch, and reuse the same
  ``AIService`` / orchestrator path.
"""

from __future__ import annotations

from typing import Final

# Owner-authenticated dashboard / API test chat (not embed, not Telegram).
CONVERSATION_CHANNEL_ADMIN_TEST: Final[str] = "admin_test"

# Public embed; anonymous visitor key in ``Conversation.public_visitor_session_key``.
CONVERSATION_CHANNEL_WEB_WIDGET: Final[str] = "web_widget"

# Telegram Bot API; thread key in ``Conversation.telegram_chat_id``.
CONVERSATION_CHANNEL_TELEGRAM: Final[str] = "telegram"

KNOWN_CONVERSATION_CHANNELS: Final[frozenset[str]] = frozenset(
    {
        CONVERSATION_CHANNEL_ADMIN_TEST,
        CONVERSATION_CHANNEL_WEB_WIDGET,
        CONVERSATION_CHANNEL_TELEGRAM,
    },
)


def is_registered_conversation_channel(value: str | None) -> bool:
    """Return True if ``value`` is a known non-legacy channel key (not for DB validation)."""
    if value is None:
        return False
    return value.strip() in KNOWN_CONVERSATION_CHANNELS
