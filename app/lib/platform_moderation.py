"""
Lightweight helpers for platform operator suspension flags.

**MVP runtime (enforced in app code)**

* **User suspension** (superadmin): sets ``User.is_active=False`` plus ``suspended_at`` and optional
  ``suspension_reason``. The user cannot log in or use authenticated APIs. Public widget/Telegram
  traffic for their bots is blocked while the owner is inactive (same path as missing owner).
* **Bot platform suspension**: sets ``Bot.platform_suspended_at`` (and optional reason). That bot
  does not process public widget chat, Telegram inbound messages (generic reply only), or dashboard
  test chat, until cleared. Owner-driven ``status='paused'`` is unchanged and separate.

Login continues to use :attr:`~app.models.user.User.is_active`. Timestamps and reasons are for
operators and :class:`~app.models.audit_log.AuditLog` review.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.bot import Bot
    from app.models.user import User


def user_has_platform_suspension_record(user: User) -> bool:
    """True if superadmin suspension timestamp is set (companion to ``is_active``)."""
    return user.suspended_at is not None


def bot_is_platform_suspended(bot: Bot) -> bool:
    """True if the bot is suspended by platform operators (block ingress/runtime when enforced)."""
    return bot.platform_suspended_at is not None


__all__ = ["bot_is_platform_suspended", "user_has_platform_suspension_record"]
