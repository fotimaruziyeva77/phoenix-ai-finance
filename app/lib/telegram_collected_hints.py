"""
Merge Telegram ``from`` user hints into :attr:`~app.models.ai_foundation.Conversation.collected_data_json`.

Used by the inbound webhook **before** :class:`~app.services.ai_service.AIService` runs so the shared
sales funnel and :mod:`app.services.lead_creation_service` see the same JSON shape as the web widget.
No separate Telegram CRM insert path — only optional enrichment keys.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.lib.niche_flow.planner_hooks import field_value_present


def merge_telegram_sender_into_collected(
    collected: Mapping[str, object] | None,
    *,
    from_username: str | None,
    from_first_name: str | None,
) -> tuple[dict[str, object], bool]:
    """
    Return ``(new_collected, changed)``.

    Keys written (only when absent / when name slot is still empty):

    * ``telegram_username`` — Telegram @handle without requiring ``@``.
    * ``telegram_first_name`` — ``from.first_name`` as sent by Telegram.
    * ``full_name`` — seeded from ``from_first_name`` only if no ``full_name`` / ``name`` / ``contact_name``.
    """
    # JSONB can hold any JSON; legacy or bad rows may not be an object. Avoid ``dict(list)`` / ``dict(str)``.
    if collected is not None and not isinstance(collected, Mapping):
        data: dict[str, object] = {}
    else:
        data = dict(collected or {})
    changed = False

    u = (from_username or "").strip()
    if u and "telegram_username" not in data:
        data["telegram_username"] = u[:64]
        changed = True

    fn_raw = (from_first_name or "").strip()
    if fn_raw:
        if "telegram_first_name" not in data:
            data["telegram_first_name"] = fn_raw[:128]
            changed = True
        has_name = any(
            field_value_present(data.get(k)) for k in ("full_name", "name", "contact_name")
        )
        if not has_name:
            data["full_name"] = fn_raw[:256]
            changed = True

    return data, changed


__all__ = ["merge_telegram_sender_into_collected"]
