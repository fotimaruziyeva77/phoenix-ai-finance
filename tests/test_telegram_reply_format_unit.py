"""Unit tests for :mod:`app.integrations.telegram_reply_format`."""

from __future__ import annotations

from app.integrations.telegram_reply_format import (
    TELEGRAM_REPLY_SOFT_MAX_CHARS,
    format_telegram_bot_reply_text,
)


def test_empty_and_whitespace() -> None:
    assert format_telegram_bot_reply_text("") == ""
    assert format_telegram_bot_reply_text("   \n\t  ") == ""


def test_preserves_paragraphs_and_trims_lines() -> None:
    raw = "  Hello.\n\nSecond paragraph.  \n"
    assert format_telegram_bot_reply_text(raw) == "Hello.\n\nSecond paragraph."


def test_normalizes_crlf() -> None:
    assert format_telegram_bot_reply_text("a\r\nb\rc") == "a\nb\nc"


def test_removes_null_and_control_chars_keeps_newline() -> None:
    raw = "Hi\x00there\nOK\x7f!"
    out = format_telegram_bot_reply_text(raw)
    assert "\x00" not in out
    assert "\x7f" not in out
    assert "Hi" in out and "there" in out
    assert "\n" in out


def test_collapses_excessive_blank_lines() -> None:
    raw = "a\n\n\n\nb"
    assert format_telegram_bot_reply_text(raw) == "a\n\nb"


def test_drops_lines_with_internal_markers() -> None:
    raw = "Visible line.\n__lead_capture_done: true\nAnother line.\n"
    out = format_telegram_bot_reply_text(raw)
    assert "Visible" in out and "Another" in out
    assert "__lead_capture" not in out


def test_strips_isolated_fence_lines() -> None:
    raw = "```\nHello\n```\n"
    out = format_telegram_bot_reply_text(raw)
    assert "```" not in out
    assert "Hello" in out


def test_soft_truncate_adds_ellipsis() -> None:
    long = "word " * 800
    out = format_telegram_bot_reply_text(long, soft_max_chars=500)
    assert len(out) < len(long)
    assert "…" in out
    assert out.endswith("…") or "\n\n…" in out


def test_short_string_unchanged_modulo_trim() -> None:
    s = "Short sales reply. One step: confirm your email."
    assert format_telegram_bot_reply_text(s) == s


def test_soft_default_matches_constant() -> None:
    assert TELEGRAM_REPLY_SOFT_MAX_CHARS == 2400


def test_markdown_like_special_characters_preserved_plain_text() -> None:
    """No parse_mode: *, _, `, <, > must survive so Telegram shows them literally."""
    raw = "Price is *not* final. Use `code` and <tag> & more _here_."
    out = format_telegram_bot_reply_text(raw)
    assert out == raw
    assert "*" in out and "_" in out and "`" in out and "<" in out and ">" in out


def test_unicode_and_emoji_preserved() -> None:
    raw = "Здравствуйте! 😊 日本語\nLine two €100"
    assert format_telegram_bot_reply_text(raw) == raw


def test_drops_captured_lead_id_line() -> None:
    raw = "Thanks!\n__captured_lead_id: \"550e8400-e29b-41d4-a716-446655440000\"\nBye."
    out = format_telegram_bot_reply_text(raw)
    assert "Thanks" in out and "Bye" in out
    assert "__captured_lead" not in out
    assert "550e8400" not in out


def test_drops_json_style_internal_key_line() -> None:
    raw = 'OK\n  "__lead_capture_done": true\nDone.'
    out = format_telegram_bot_reply_text(raw)
    assert "OK" in out and "Done" in out
    assert "__lead_capture" not in out


def test_very_long_single_line_soft_capped_under_soft_max() -> None:
    raw = "x" * 8000
    out = format_telegram_bot_reply_text(raw)
    assert len(out) <= TELEGRAM_REPLY_SOFT_MAX_CHARS + 4
    assert "…" in out


def test_multiline_long_respects_soft_cap_with_paragraph_break() -> None:
    para = "Sentence one. " * 200
    raw = para + "\n\n" + para + "\n\n" + para
    out = format_telegram_bot_reply_text(raw, soft_max_chars=900)
    assert len(out) < len(raw)
    assert "…" in out
