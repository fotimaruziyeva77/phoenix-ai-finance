"""
Prompt assembly for AI calls (bounded history, secret scrubbing, extension hooks).

Extension points (see :mod:`app.prompting.builder`):
    * ``PromptExtensionContext`` — niche scripts, PDF/RAG excerpts, lead-flow hints.
    * ``PromptBuildOptions`` — history/message/total caps; system override policy.
    * Registry-backed niche blurbs via ``get_niche_by_id`` when ``niche_context`` is omitted.
"""

from app.prompting.adapters import bot_to_prompt_source
from app.prompting.builder import build_chat_prompt, build_prompt_package
from app.prompting.safety import scrub_secrets_for_prompt
from app.prompting.style import WARM_TONE_SECTION_TITLE, assemble_warm_tone_section, operator_tone_addon
from app.prompting.types import (
    BotPromptSource,
    HistoryTurn,
    PromptBuildInput,
    PromptBuildOptions,
    PromptExtensionContext,
    PromptPackage,
)
from app.prompting.warm_tone_evaluation import evaluate_warm_tone_response

__all__ = [
    "BotPromptSource",
    "HistoryTurn",
    "PromptBuildInput",
    "PromptBuildOptions",
    "PromptExtensionContext",
    "PromptPackage",
    "WARM_TONE_SECTION_TITLE",
    "assemble_warm_tone_section",
    "bot_to_prompt_source",
    "build_chat_prompt",
    "build_prompt_package",
    "evaluate_warm_tone_response",
    "operator_tone_addon",
    "scrub_secrets_for_prompt",
]
