"""Internal structures for prompt assembly (provider-agnostic)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.ai_providers.types import ChatMessage

HistoryRole = Literal["user", "assistant"]


@dataclass(frozen=True, slots=True)
class HistoryTurn:
    """One prior conversational message (user or assistant)."""

    role: HistoryRole
    content: str


@dataclass(frozen=True, slots=True)
class BotPromptSource:
    """
    Bot fields needed for prompts — decoupled from SQLAlchemy.

    Map from :class:`~app.models.bot.Bot` via :func:`~app.prompting.adapters.bot_to_prompt_source`.
    """

    name: str
    niche_id: str
    goal_type: str
    welcome_message: str | None = None
    tone: str | None = None
    language: str | None = None
    short_description: str | None = None


@dataclass(frozen=True, slots=True)
class PromptExtensionContext:
    """
    Extension slots (optional). Wire later: niche scripts, RAG/PDF excerpts, lead flow hints.

    Non-empty strings are appended to the system prompt in stable order.
    """

    niche_script_excerpt: str | None = None
    knowledge_excerpt: str | None = None
    lead_flow_hint: str | None = None


@dataclass(frozen=True, slots=True)
class PromptBuildOptions:
    """Bounds and policy for a single build."""

    max_history_messages: int = 16
    max_chars_per_message: int = 12_000
    max_total_history_chars: int = 48_000
    allow_system_prompt_override: bool = True
    include_warm_tone_guidance: bool = True
    """When True, inject tone guidance (compact or full depending on ``use_compact_tone``)."""
    use_compact_tone: bool = True
    """When True with ``include_warm_tone_guidance``, use :mod:`app.prompting.compact_tone` (saves tokens)."""
    slim_system_prompt: bool = False
    """When True, use a compact system block for short user messages (see :mod:`app.prompting.slimming`)."""
    allow_knowledge_in_system: bool = True
    """When False, omit RAG/knowledge excerpts even if present on extensions (saves tokens)."""


@dataclass(frozen=True, slots=True)
class PromptBuildInput:
    """Inputs to :func:`~app.prompting.builder.build_prompt_package`."""

    bot: BotPromptSource
    user_message: str
    history: tuple[HistoryTurn, ...] = ()
    niche_context: str | None = None
    system_prompt_override: str | None = None
    extensions: PromptExtensionContext | None = None
    options: PromptBuildOptions | None = None


@dataclass(frozen=True, slots=True)
class PromptPackage:
    """
    Normalized prompt bundle for one model call.

    * ``system_prompt`` — single system string (may be empty; provider layer may omit).
    * ``history_messages`` — prior ``user`` / ``assistant`` turns only, already bounded.
    * ``current_user_message`` — latest user turn (scrubbed).
    """

    system_prompt: str
    history_messages: tuple[ChatMessage, ...]
    current_user_message: str

    def as_provider_messages(self) -> tuple[ChatMessage, ...]:
        """Flatten to :class:`~app.ai_providers.types.ChatMessage` sequence for :class:`~app.ai_providers.types.GenerateParams`."""
        out: list[ChatMessage] = []
        sys_stripped = self.system_prompt.strip()
        if sys_stripped:
            out.append(ChatMessage(role="system", content=sys_stripped))
        out.extend(self.history_messages)
        out.append(ChatMessage(role="user", content=self.current_user_message))
        return tuple(out)
