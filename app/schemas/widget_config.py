"""Pydantic shapes for embeddable chat widget configuration."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.lib.widget_allowed_domains import normalize_allowed_domains


class PreChatFormField(BaseModel):
    """Single field definition inside the pre-chat form."""

    name: str = Field(max_length=64, description="Machine key (e.g. 'email', 'phone').")
    label: str = Field(max_length=128, description="User-visible label.")
    type: str = Field(
        default="text",
        max_length=32,
        description="Input type: text, email, tel, textarea, select.",
    )
    required: bool = False
    placeholder: str | None = Field(default=None, max_length=256)
    options: list[str] | None = Field(
        default=None,
        description="Choice list for 'select' type.",
    )


class WidgetConfigRead(BaseModel):
    """Full widget row for authenticated owner APIs."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bot_id: UUID
    owner_id: UUID
    public_widget_key: str
    is_enabled: bool
    allowed_domains_json: list[str]
    theme: str | None = Field(default=None, max_length=64)
    welcome_text: str | None = Field(default=None, max_length=2048)
    pre_chat_form_json: list[dict[str, object]] | None = None
    custom_css: str | None = Field(default=None, max_length=8192)
    widget_settings_json: dict[str, object] | None = None
    created_at: datetime
    updated_at: datetime


class WidgetConfigUpdate(BaseModel):
    """Partial update; immutable identifiers and public_widget_key omitted."""

    model_config = ConfigDict(extra="forbid")

    is_enabled: bool | None = None
    allowed_domains_json: list[str] | None = None
    theme: str | None = Field(default=None, max_length=64)
    welcome_text: str | None = Field(default=None, max_length=2048)
    pre_chat_form_json: list[PreChatFormField] | None = None
    custom_css: str | None = Field(default=None, max_length=8192)
    widget_settings_json: dict[str, object] | None = None

    @field_validator("allowed_domains_json")
    @classmethod
    def validate_domains(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        try:
            return normalize_allowed_domains(v)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc


class WidgetPublicBootstrapResponse(BaseModel):
    """
    Minimal safe payload for unauthenticated widget bootstrap (by ``public_widget_key``).

    No owner ids, no internal bot settings, no domain allowlist. ``Origin`` / ``Referer``
    are validated server-side when an allowlist is configured.
    """

    model_config = ConfigDict(from_attributes=True)

    is_enabled: bool = Field(description="Always true when this response is returned.")
    welcome_text: str | None = Field(default=None, max_length=2048)
    theme: str | None = Field(default=None, max_length=64)
    bot_display_name: str = Field(
        description="Public bot title for the widget shell (same as dashboard bot name).",
        max_length=160,
    )
    pre_chat_form: list[dict[str, object]] | None = Field(
        default=None,
        description="Pre-chat form field definitions (if configured).",
    )
    custom_css: str | None = Field(
        default=None,
        max_length=8192,
        description="Owner-provided CSS for widget styling.",
    )
    show_branding: bool = Field(
        default=True,
        description="When True, display a 'Powered by BotForge' badge in the widget footer.",
    )


class BotWidgetConfigResponse(BaseModel):
    """
    Owner API response for ``GET/PATCH /bots/{bot_id}/widget``.

    ``allowed_domains`` is the normalized hostname allowlist (stored as JSON in the database).
    """

    id: UUID = Field(description="Widget configuration id")
    bot_id: UUID
    public_widget_key: str = Field(description="Opaque public token for the embed script (stable once issued).")
    is_enabled: bool
    allowed_domains: list[str]
    theme: str | None = Field(default=None, max_length=64)
    welcome_text: str | None = Field(default=None, max_length=2048)
    pre_chat_form: list[dict[str, object]] | None = Field(
        default=None,
        description="Pre-chat form field definitions.",
    )
    custom_css: str | None = Field(default=None, max_length=8192)
    widget_settings: dict[str, object] | None = Field(
        default=None,
        description="Optional extension object (branding, layout, etc.).",
    )
    created_at: datetime
    updated_at: datetime


def bot_widget_config_response_from_read(read: WidgetConfigRead) -> BotWidgetConfigResponse:
    """Map internal read model to the owner HTTP response shape."""
    return BotWidgetConfigResponse(
        id=read.id,
        bot_id=read.bot_id,
        public_widget_key=read.public_widget_key,
        is_enabled=read.is_enabled,
        allowed_domains=list(read.allowed_domains_json),
        theme=read.theme,
        welcome_text=read.welcome_text,
        pre_chat_form=read.pre_chat_form_json,
        custom_css=read.custom_css,
        widget_settings=read.widget_settings_json,
        created_at=read.created_at,
        updated_at=read.updated_at,
    )
