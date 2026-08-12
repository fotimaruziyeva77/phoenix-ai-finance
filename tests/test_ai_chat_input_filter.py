"""
Unit tests for Layer 1 — ai_chat_input_filter (trivial fast-path).

Coverage goals
--------------
* Required inputs from task spec: hi, hello, salom, assalomu alaykum, привет, ok, 👍,
  short punctuation variants, greeting + real question (must NOT be trivial).
* Language-response routing (Uzbek / Russian / English).
* Normalisation robustness: extra spaces, mixed case, trailing punctuation.
* Emoji-only messages.
* False-positive guard: messages with substantive content must pass through.
* Internal: trivial_detection_normalized exposes the same form used for matching.
"""

from __future__ import annotations

import pytest

from app.services.ai_chat_input_filter import (
    handle_trivial_message,
    trivial_detection_normalized,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _trivial(text: str, *, lang: str | None = None) -> bool:
    """Return True iff the message is classified trivial."""
    return handle_trivial_message(text, bot_language=lang) is not None


def _reply(text: str, *, lang: str | None = None) -> str:
    """Assert trivial and return the canned reply (raises if not trivial)."""
    r = handle_trivial_message(text, bot_language=lang)
    assert r is not None, f"Expected trivial for {text!r}, got None"
    return r


# ---------------------------------------------------------------------------
# Task-spec required inputs
# ---------------------------------------------------------------------------


class TestRequiredInputs:
    def test_hi(self) -> None:
        assert _trivial("hi")

    def test_hello(self) -> None:
        assert _trivial("hello")

    def test_salom(self) -> None:
        assert _trivial("salom")

    def test_assalomu_alaykum(self) -> None:
        assert _trivial("Assalomu alaykum")

    def test_assalomu_alaykum_lowercase(self) -> None:
        assert _trivial("assalomu alaykum")

    def test_privet_cyrillic(self) -> None:
        assert _trivial("привет")

    def test_privet_cyrillic_exclamation(self) -> None:
        # Punctuation stripped by normalisation
        assert _trivial("Привет!")

    def test_ok_standalone(self) -> None:
        assert _trivial("ok")

    def test_ok_uppercase(self) -> None:
        assert _trivial("OK")

    def test_thumbs_up_emoji(self) -> None:
        assert _trivial("👍")

    def test_multi_emoji(self) -> None:
        assert _trivial("👍🎉🙏")


# ---------------------------------------------------------------------------
# Punctuation / whitespace variants
# ---------------------------------------------------------------------------


class TestNormalisationVariants:
    def test_hi_with_trailing_exclamation(self) -> None:
        assert _trivial("hi!")

    def test_hello_with_comma_and_space(self) -> None:
        assert _trivial("hello,")

    def test_salom_extra_whitespace(self) -> None:
        assert _trivial("  salom  ")

    def test_hello_mixed_case(self) -> None:
        assert _trivial("HELLO")

    def test_hey_with_ellipsis(self) -> None:
        assert _trivial("hey...")

    def test_assalomu_alaykum_with_punctuation(self) -> None:
        assert _trivial("Assalomu alaykum!")

    def test_zdrastvuyte_with_exclamation(self) -> None:
        assert _trivial("Здравствуйте!")

    def test_dobry_den_phrase(self) -> None:
        assert _trivial("Добрый день")

    def test_g_day_apostrophe(self) -> None:
        # "g'day" normalises to "g day" which is in _GREETING_EN
        assert _trivial("g'day")

    def test_as_salamu_alaykum_hyphen(self) -> None:
        # "as-salamu alaykum" normalises to "as salamu alaykum"
        assert _trivial("as-salamu alaykum")


# ---------------------------------------------------------------------------
# Extended greeting coverage — Uzbek
# ---------------------------------------------------------------------------


class TestUzbekGreetings:
    def test_assalam_alaykum_variant(self) -> None:
        assert _trivial("assalam alaykum")

    def test_assalamu_alaykum(self) -> None:
        assert _trivial("assalamu alaykum")

    def test_va_alaykum_assalom(self) -> None:
        assert _trivial("Va alaykum assalom")

    def test_salom_upper(self) -> None:
        assert _trivial("SALOM")

    def test_salom_cyrillic(self) -> None:
        # Cyrillic Uzbek form
        assert _trivial("Салом")


# ---------------------------------------------------------------------------
# Extended greeting coverage — Russian
# ---------------------------------------------------------------------------


class TestRussianGreetings:
    def test_zdrastvuyte(self) -> None:
        assert _trivial("Здравствуйте")

    def test_zdrastvuy(self) -> None:
        assert _trivial("здравствуй")

    def test_privetstvuyu(self) -> None:
        assert _trivial("приветствую")

    def test_dobryy_vecher(self) -> None:
        assert _trivial("Добрый вечер")

    def test_dobroye_utro(self) -> None:
        assert _trivial("Доброе утро")

    def test_dobro_pozhalovat(self) -> None:
        assert _trivial("Добро пожаловать")


# ---------------------------------------------------------------------------
# Extended greeting coverage — English
# ---------------------------------------------------------------------------


class TestEnglishGreetings:
    def test_hey(self) -> None:
        assert _trivial("hey")

    def test_howdy(self) -> None:
        assert _trivial("howdy")

    def test_hiya(self) -> None:
        assert _trivial("hiya")

    def test_heya(self) -> None:
        assert _trivial("heya")

    def test_sup(self) -> None:
        assert _trivial("sup")

    def test_good_morning(self) -> None:
        assert _trivial("good morning")

    def test_good_evening(self) -> None:
        assert _trivial("good evening")

    def test_good_afternoon(self) -> None:
        assert _trivial("Good afternoon")

    def test_morning_single_word(self) -> None:
        assert _trivial("morning")

    def test_greetings(self) -> None:
        assert _trivial("greetings")


# ---------------------------------------------------------------------------
# Short acknowledgements
# ---------------------------------------------------------------------------


class TestShortAcknowledgements:
    def test_okay(self) -> None:
        assert _trivial("okay")

    def test_ok_dot(self) -> None:
        assert _trivial("ok.")

    def test_sure(self) -> None:
        assert _trivial("sure")

    def test_alright(self) -> None:
        assert _trivial("alright")

    def test_thanks(self) -> None:
        assert _trivial("thanks")

    def test_thx(self) -> None:
        assert _trivial("thx")

    def test_ty(self) -> None:
        assert _trivial("ty")

    def test_yes(self) -> None:
        assert _trivial("yes")

    def test_no(self) -> None:
        assert _trivial("no")

    def test_yep(self) -> None:
        assert _trivial("yep")

    def test_nope(self) -> None:
        assert _trivial("nope")

    def test_ha_uzbek(self) -> None:
        # Uzbek "yes"
        assert _trivial("ha")

    def test_yoq_uzbek(self) -> None:
        # Uzbek "no"
        assert _trivial("yoq")

    def test_np(self) -> None:
        # "no problem"
        assert _trivial("np")

    def test_ok_thanks_two_word(self) -> None:
        # 2-word, both in lexicon → trivial
        assert _trivial("ok thanks")

    def test_hi_there_two_word(self) -> None:
        assert _trivial("hi there")

    def test_hey_there_two_word(self) -> None:
        assert _trivial("hey there")


# ---------------------------------------------------------------------------
# FALSE-POSITIVE GUARD — these must NEVER be trivialised
# ---------------------------------------------------------------------------


class TestFalsePositiveGuard:
    """
    Any message that contains real sales/support intent must pass through to
    the LLM pipeline unchanged.  These tests are the most important in this file.
    """

    def test_greeting_plus_real_question_en(self) -> None:
        # Canonical false-positive scenario from task spec
        assert not _trivial("hi, what is your pricing?")

    def test_greeting_plus_real_question_uz(self) -> None:
        assert not _trivial("salom, narx qancha?")

    def test_greeting_plus_real_question_ru(self) -> None:
        assert not _trivial("привет, сколько стоит подписка?")

    def test_three_word_greeting_with_question(self) -> None:
        # 3+ words beyond greeting → not trivial
        assert not _trivial("hello how are you")

    def test_long_business_inquiry(self) -> None:
        assert not _trivial(
            "I need a detailed quote for a 200-page migration from Oracle to PostgreSQL."
        )

    def test_ok_with_followup(self) -> None:
        # "ok" alone = trivial; "ok what" = 2 words — "what" not in lexicon → not trivial
        assert not _trivial("ok what")

    def test_ok_and_question(self) -> None:
        assert not _trivial("ok and the price is?")

    def test_yes_please_real_question(self) -> None:
        # "yes please" = 2 words; "please" is not in lexicon → not trivial
        assert not _trivial("yes please send me the proposal")

    def test_good_question_not_trivial(self) -> None:
        # "good question" — "question" not in lexicon
        assert not _trivial("good question")

    def test_sure_with_follow_on(self) -> None:
        assert not _trivial("sure but I want the enterprise tier")

    def test_number_only_not_trivial(self) -> None:
        # Digits → _is_emoji_only returns False
        assert not _trivial("1")

    def test_alphanumeric_not_trivial(self) -> None:
        assert not _trivial("pro100")

    def test_empty_string_not_trivial(self) -> None:
        assert handle_trivial_message("") is None

    def test_whitespace_only_not_trivial(self) -> None:
        assert handle_trivial_message("   ") is None

    def test_salom_price_three_words(self) -> None:
        # "salom narx qancha" = 3 words; "narx" and "qancha" not in lexicon
        assert not _trivial("salom narx qancha")

    def test_hello_tell_me_about(self) -> None:
        assert not _trivial("hello tell me about your plans")

    def test_hi_and_need_quote(self) -> None:
        assert not _trivial("hi I need a quote")

    def test_morning_with_request(self) -> None:
        assert not _trivial("morning can you send me the contract?")


# ---------------------------------------------------------------------------
# Language / response routing
# ---------------------------------------------------------------------------


class TestResponseLanguageRouting:
    def test_salom_returns_uzbek_response(self) -> None:
        r = _reply("salom")
        assert "Salom" in r
        assert "?" in r  # ends with question

    def test_hi_no_lang_hint_returns_english(self) -> None:
        r = _reply("hi", lang=None)
        assert "Hello" in r

    def test_hi_en_lang_returns_english(self) -> None:
        r = _reply("hi", lang="en")
        assert "Hello" in r

    def test_privet_returns_russian(self) -> None:
        r = _reply("привет")
        assert "Привет" in r

    def test_zdrastvuyte_returns_russian(self) -> None:
        r = _reply("Здравствуйте")
        assert "Привет" in r

    def test_bot_lang_ru_overrides_english_greeting(self) -> None:
        r = _reply("hi", lang="ru")
        assert "Привет" in r

    def test_bot_lang_uz_overrides_cyrillic_greeting(self) -> None:
        # Even if Cyrillic script detected, explicit bot_language="uz" wins
        r = _reply("привет", lang="uz")
        assert "Salom" in r

    def test_bot_lang_uz_en_greeting(self) -> None:
        r = _reply("hello", lang="uz")
        assert "Salom" in r

    def test_emoji_only_no_lang_hint_returns_english(self) -> None:
        r = _reply("👍", lang=None)
        assert "Hello" in r or "Salom" in r  # either is acceptable default

    def test_assalomu_alaykum_returns_uzbek(self) -> None:
        r = _reply("Assalomu alaykum")
        assert "Salom" in r

    def test_dobry_den_returns_russian(self) -> None:
        r = _reply("Добрый день")
        assert "Привет" in r


# ---------------------------------------------------------------------------
# trivial_detection_normalized — public normalisation contract
# ---------------------------------------------------------------------------


class TestNormalisedForm:
    def test_lowercase(self) -> None:
        assert trivial_detection_normalized("SALOM") == "salom"

    def test_strips_whitespace(self) -> None:
        assert trivial_detection_normalized("  hi  ") == "hi"

    def test_punctuation_becomes_space_and_collapses(self) -> None:
        assert trivial_detection_normalized("hello!") == "hello"

    def test_apostrophe_removed(self) -> None:
        # "g'day" → "g day"
        assert trivial_detection_normalized("g'day") == "g day"

    def test_hyphen_removed(self) -> None:
        assert trivial_detection_normalized("as-salamu alaykum") == "as salamu alaykum"

    def test_cyrillic_preserved(self) -> None:
        n = trivial_detection_normalized("Привет!")
        assert n == "привет"

    def test_multi_space_collapsed(self) -> None:
        assert trivial_detection_normalized("good   morning") == "good morning"

    def test_nfkc_applied(self) -> None:
        # Full-width ASCII 'Ａ' (U+FF21) → 'A' after NFKC, then lowercased to 'a'
        assert trivial_detection_normalized("\uff21") == "a"


# ---------------------------------------------------------------------------
# Emoji-only edge cases
# ---------------------------------------------------------------------------


class TestEmojiOnly:
    def test_single_emoji(self) -> None:
        assert _trivial("🙂")

    def test_heart_with_variation_selector(self) -> None:
        assert _trivial("❤️")

    def test_check_mark_symbol(self) -> None:
        assert _trivial("✓")

    def test_thumbs_up_down(self) -> None:
        assert _trivial("👍👎")

    def test_emoji_plus_acknowledgement_is_trivial(self) -> None:
        # "👍 ok" → normalises to "ok" (emoji stripped) → single lexicon word → trivial
        assert _trivial("👍 ok")

    def test_emoji_with_real_question_not_trivial(self) -> None:
        # "👍 what is the pricing plan?" → 5 meaningful words after normalisation → not trivial
        assert not _trivial("👍 what is the pricing plan?")
