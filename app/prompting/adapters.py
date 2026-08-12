"""Map persistence models to prompt-layer DTOs."""

from __future__ import annotations

from app.models.bot import Bot
from app.prompting.types import BotPromptSource


def bot_to_prompt_source(bot: Bot) -> BotPromptSource:
    return BotPromptSource(
        name=bot.name,
        niche_id=bot.niche_id,
        goal_type=bot.goal_type,
        welcome_message=bot.welcome_message,
        tone=bot.tone,
        language=bot.language,
        short_description=bot.short_description,
    )
