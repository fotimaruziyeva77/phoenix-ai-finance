"""Build Telegram message text for new-lead alerts (pure, testable)."""

from __future__ import annotations

from datetime import timezone

from app.integrations.telegram.lead_alert_types import NewLeadAlertPayload

# Telegram hard limit; leave headroom for truncation notice.
_TELEGRAM_HARD_MAX = 4096
_RESERVE_FOR_TRUNCATION_NOTICE = 80


def format_new_lead_alert_message(payload: NewLeadAlertPayload) -> str:
    """
    Plain text (no parse_mode) so user-controlled summary cannot break Telegram HTML/Markdown.

    Includes: summary, temperature, phone, niche, source channel, timestamp, bot name, lead id (correlation only).
    """
    lines: list[str] = [
        "New lead — BotForge AI",
        "",
        f"Bot: {payload.bot_name.strip() or '(unnamed bot)'}",
        f"Niche: {payload.niche_id}",
    ]
    src = (payload.source_channel or "").strip()
    lines.append(f"Source: {src if src else '—'}")
    temp = (payload.lead_temperature or "").strip() or "—"
    lines.append(f"Temperature: {temp}")
    if payload.lead_score is not None:
        lines.append(f"Score: {payload.lead_score}")
    phone = (payload.phone or "").strip()
    lines.append(f"Phone: {phone if phone else '—'}")
    cap = payload.captured_at
    if cap.tzinfo is not None:
        utc = cap.astimezone(timezone.utc)
        lines.append(f"Captured (UTC): {utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    else:
        lines.append(f"Captured: {cap.isoformat()} (naive)")
    lines.append(f"Lead ID: {payload.lead_id}")
    lines.append("")
    lines.append("Summary:")
    summary = (payload.summary or "").strip() or "—"
    lines.append(summary)

    text = "\n".join(lines)
    if len(text) <= _TELEGRAM_HARD_MAX:
        return text

    budget = _TELEGRAM_HARD_MAX - _RESERVE_FOR_TRUNCATION_NOTICE
    head = text[:budget].rstrip()
    return f"{head}\n\n… (message truncated for Telegram)"
