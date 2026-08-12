"""Public, unauthenticated widget bootstrap (minimal safe fields)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.public_widget_abuse import widget_key_digest
from app.core.public_widget_channel_events import (
    WIDGET_BOOTSTRAP_LOADED,
    emit_public_widget_channel_event,
)
from app.lib.platform_moderation import bot_is_platform_suspended
from app.lib.widget_origin_policy import WidgetOriginPolicyOptions
from app.models.user import User
from app.repositories.subscription_repository import SubscriptionRepository
from app.schemas.widget_config import WidgetPublicBootstrapResponse
from app.services.plan_limits import get_plan
from app.services.widget_bootstrap_exceptions import (
    WidgetBootstrapNotFoundError,
    WidgetBootstrapRuntimeBlockedError,
)
from app.services.widget_public_gate import (
    enforce_public_widget_origin_and_enabled,
    load_widget_and_bot_by_public_key,
)


class WidgetBootstrapService:
    """Resolve embed bootstrap by public key with Origin/Referer checks."""

    def __init__(self, session: AsyncSession, *, origin_policy: WidgetOriginPolicyOptions) -> None:
        self._session = session
        self._origin_policy = origin_policy

    async def get_bootstrap(
        self,
        *,
        public_widget_key: str,
        origin_header: str | None,
        referer_header: str | None,
    ) -> WidgetPublicBootstrapResponse:
        ctx = await load_widget_and_bot_by_public_key(self._session, public_widget_key)
        if ctx is None:
            raise WidgetBootstrapNotFoundError()
        wc, bot = ctx
        enforce_public_widget_origin_and_enabled(
            wc,
            origin_header=origin_header,
            referer_header=referer_header,
            origin_policy=self._origin_policy,
        )
        owner = await self._session.get(User, bot.owner_id)
        if owner is None or not owner.is_active or bot_is_platform_suspended(bot):
            raise WidgetBootstrapRuntimeBlockedError()
        emit_public_widget_channel_event(
            event=WIDGET_BOOTSTRAP_LOADED,
            bot_id=bot.id,
            widget_config_id=wc.id,
            widget_key_digest=widget_key_digest(public_widget_key),
        )
        # Resolve owner's plan to determine branding visibility
        sub_repo = SubscriptionRepository(self._session)
        sub = await sub_repo.get_by_user_id(owner.id)
        plan_slug = sub.plan_slug.value if sub else "free"
        plan = get_plan(plan_slug)

        return WidgetPublicBootstrapResponse(
            is_enabled=True,
            welcome_text=wc.welcome_text,
            theme=wc.theme,
            bot_display_name=bot.name,
            pre_chat_form=wc.pre_chat_form_json,
            custom_css=wc.custom_css,
            show_branding=plan.show_branding,
        )
