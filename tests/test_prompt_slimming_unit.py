from app.core.config import Settings
from app.prompting.slimming import prompt_build_options_for_user_text


def _settings() -> Settings:
    return Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
            "gemini_api_key": "k",
        }
    )


def test_slim_applies_for_two_word_message() -> None:
    o = prompt_build_options_for_user_text(_settings(), "salom yaxshimisiz")
    assert o.slim_system_prompt is True
    assert o.max_history_messages <= 4


def test_slim_not_applied_for_long_message() -> None:
    o = prompt_build_options_for_user_text(_settings(), "one two three four")
    assert o.slim_system_prompt is False


def test_knowledge_injected_disables_slim_even_for_short_message() -> None:
    o = prompt_build_options_for_user_text(_settings(), "hi", knowledge_injected=True)
    assert o.slim_system_prompt is False
