"""
Assemble :class:`~app.prompting.types.PromptPackage` from bot config and conversation slices.

Tone guidance uses either :mod:`app.prompting.compact_tone` or the full warm-tone list
in :mod:`app.prompting.style`, per ``PromptBuildOptions``. Identity + compact tone are
LRU-cached in :mod:`app.prompting.smart_system`.
"""

from __future__ import annotations

import dataclasses

from app.ai_providers.types import ChatMessage
from app.lib.niche_registry import get_niche_by_id
from app.prompting.history import truncate_history_turns
from app.prompting.safety import scrub_secrets_for_prompt
from app.prompting.history_clean import clean_history_for_prompt
from app.prompting.engagement_rules import engagement_rules_for_goal_type
from app.prompting.smart_system import (
    cached_full_warm_tone_block,
    cached_static_identity_and_compact_tone,
    tone_cache_key,
)
from app.prompting.types import (
    BotPromptSource,
    PromptBuildInput,
    PromptBuildOptions,
    PromptExtensionContext,
    PromptPackage,
)


def _assemble_system_prompt(
    bot: BotPromptSource,
    niche_context: str | None,
    extensions: PromptExtensionContext | None,
    opts: PromptBuildOptions,
) -> str:
    """
    Three-layer system prompt:

    * **A — static core:** identity + tone (compact block is LRU-cached per bot/tone).
    * **B — contextual:** operator copy, niche blurb, locale, scripts, lead hints.
    * **C — optional knowledge:** only when ``opts.allow_knowledge_in_system`` is True.
    """
    ext0 = extensions or PromptExtensionContext()
    if not opts.allow_knowledge_in_system and ext0.knowledge_excerpt:
        ext = dataclasses.replace(ext0, knowledge_excerpt=None)
    else:
        ext = ext0

    if opts.slim_system_prompt:
        niche_one = (niche_context or "").strip()
        if not niche_one:
            niche_def = get_niche_by_id(bot.niche_id)
            if niche_def is not None:
                niche_one = (niche_def.short_description or "").strip()
        niche_one = niche_one[:240]
        lang = (bot.language or "").strip()
        lang_line = f"Reply in {lang}." if lang else "Match the user's language."
        core = (
            f'You are «{bot.name}», a {bot.goal_type} assistant (niche `{bot.niche_id}`). '
            f"{lang_line} Be brief and helpful — keep responses to 2-3 sentences max. "
            f"Stay on topic — only discuss this business's services. "
            f"Move toward capturing the customer's phone number within 3-4 exchanges. "
            f"Politely redirect off-topic questions."
        )
        if niche_one:
            return f"{core}\nContext: {niche_one}"
        if ext.lead_flow_hint and (ext.lead_flow_hint or "").strip():
            hint = (ext.lead_flow_hint or "").strip()[:400]
            return f"{core}\nLead hint: {hint}"
        return core

    parts: list[str] = []
    tkey = tone_cache_key(bot.tone)

    # Part A — static core (identity + tone); compact path deduplicates via LRU cache.
    if opts.include_warm_tone_guidance and opts.use_compact_tone:
        parts.append(
            cached_static_identity_and_compact_tone(
                bot.name,
                bot.goal_type,
                bot.niche_id,
                tkey,
            )
        )
    else:
        parts.append(
            f'You are the conversational voice of «{bot.name}» for {bot.goal_type} conversations '
            f'(niche catalog id `{bot.niche_id}`). Sound human and specific to this role—not like a generic chatbot.'
        )
        if opts.include_warm_tone_guidance:
            parts.append(cached_full_warm_tone_block(tkey))

    # Part B — contextual (dynamic per bot config / registry).
    if bot.short_description:
        parts.append(f"About this bot: {bot.short_description}")
    if bot.language:
        parts.append(f"Prefer responding in language/locale: {bot.language}.")
    if bot.welcome_message:
        parts.append(f"The bot's welcome message for reference: {bot.welcome_message}")

    niche_text = niche_context
    if not niche_text:
        niche_def = get_niche_by_id(bot.niche_id)
        if niche_def is not None:
            niche_text = niche_def.short_description
    if niche_text:
        parts.append(f"Niche context: {niche_text}")

    if ext.niche_script_excerpt:
        parts.append(f"Niche script (excerpt): {ext.niche_script_excerpt}")
    if ext.lead_flow_hint:
        parts.append(f"Lead flow hint: {ext.lead_flow_hint}")

    # Part B2 — engagement rules (goal-type-specific strategy + off-topic guardrails).
    engagement_block = engagement_rules_for_goal_type(bot.goal_type)
    if engagement_block:
        parts.append(engagement_block)

    # Part C — optional knowledge (RAG), omitted when ``allow_knowledge_in_system`` is False.
    if ext.knowledge_excerpt:
        parts.append(ext.knowledge_excerpt.strip())

    return "\n\n".join(parts)


def build_prompt_package(inp: PromptBuildInput) -> PromptPackage:
    """
    Build a scrubbed, bounded :class:`~app.prompting.types.PromptPackage`.

    System prompt override (when ``allow_system_prompt_override``) replaces the assembled
    system block entirely; it is still scrubbed for secret-shaped substrings.
    """
    opts = inp.options or PromptBuildOptions()
    ext = inp.extensions or PromptExtensionContext()

    history_cleaned = clean_history_for_prompt(inp.history, inp.user_message)
    history_bounded = truncate_history_turns(history_cleaned, opts)

    history_messages = tuple(
        ChatMessage(role=t.role, content=scrub_secrets_for_prompt(t.content)) for t in history_bounded
    )
    user_msg = scrub_secrets_for_prompt(inp.user_message.strip())

    if opts.allow_system_prompt_override and inp.system_prompt_override is not None:
        raw_override = inp.system_prompt_override.strip()
        system_prompt = scrub_secrets_for_prompt(raw_override) if raw_override else ""
    else:
        assembled = _assemble_system_prompt(inp.bot, inp.niche_context, ext, opts)
        system_prompt = scrub_secrets_for_prompt(assembled)

    return PromptPackage(
        system_prompt=system_prompt,
        history_messages=history_messages,
        current_user_message=user_msg,
    )


def build_chat_prompt(
    inp: PromptBuildInput,
    *,
    use_knowledge: bool | None = None,
    is_short: bool | None = None,
) -> PromptPackage:
    """
    Segmented build entrypoint for callers that want explicit knowledge / length policy.

    * ``use_knowledge=False`` — strips knowledge from the system block (saves tokens).
    * ``is_short=True`` — forces the slim system template (caller should also cap history).
    """
    base_opts = inp.options or PromptBuildOptions()
    o = base_opts
    if use_knowledge is False:
        o = dataclasses.replace(o, allow_knowledge_in_system=False)
    if is_short is True:
        o = dataclasses.replace(o, slim_system_prompt=True)
    return build_prompt_package(dataclasses.replace(inp, options=o))
