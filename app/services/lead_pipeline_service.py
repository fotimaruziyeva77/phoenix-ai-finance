"""
Owner-scoped CRM pipeline operations for :class:`~app.models.lead.Lead`.

Routers should depend on this service rather than querying ``Lead`` directly so **owner_id**
filtering and :mod:`app.services.lead_pipeline_policy` stay centralized.

Extension points (stubbed conceptually, not wired)
====================================================

* **Assignment** — add ``assignee_user_id`` to the model and require it in filters or transition
  guards when you introduce teams.

* **Follow-up reminders** — persist ``next_follow_up_at`` and have a scheduler read the same
  owner-scoped listing methods.

* **External CRM sync** — after a successful :meth:`update_lead_pipeline`, enqueue a job with
  ``(lead_id, owner_id, prior_status, new_status)``; keep this service free of vendor SDKs.
"""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.user import User
from app.repositories.lead_repository import (
    LeadListFilters,
    LeadRepository,
    decode_lead_cursor,
    encode_lead_cursor,
)
from app.schemas.lead import (
    LeadEventListResponse,
    LeadEventRead,
    LeadListItem,
    LeadListResponse,
    LeadPipelinePatch,
    LeadRead,
)
from app.services.lead_event_noop import NOOP_LEAD_EVENT_SERVICE
from app.services.lead_event_service import LeadEventService
from app.services.lead_pipeline_exceptions import (
    LeadInvalidStatusTransitionError,
    LeadNotFoundError,
    LeadPipelineValidationError,
)
from app.services.lead_pipeline_policy import LeadStatusTransitionError, validate_lead_status_change


class LeadPipelineService:
    """List, fetch, and update leads for the authenticated owner (CRM MVP)."""

    def __init__(self, repo: LeadRepository, events: LeadEventService | None = None) -> None:
        self._repo = repo
        self._events = events or NOOP_LEAD_EVENT_SERVICE

    async def list_leads_for_owner(
        self,
        current_user: User,
        *,
        filters: LeadListFilters | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> LeadListResponse:
        owner_id = current_user.id
        try:
            rows = await self._repo.list_leads_for_owner(
                owner_id=owner_id,
                filters=filters,
                limit=limit,
                offset=offset,
            )
            total = await self._repo.count_leads_for_owner(owner_id=owner_id, filters=filters)
        except SQLAlchemyError as exc:
            raise LeadPipelineValidationError("Could not load leads.") from exc
        return LeadListResponse(
            items=[LeadListItem.model_validate(r) for r in rows],
            total=total,
        )

    async def list_leads_for_owner_cursor(
        self,
        current_user: User,
        *,
        filters: LeadListFilters | None = None,
        limit: int = 50,
        after_cursor: str | None = None,
    ) -> LeadListResponse:
        """
        Cursor-based lead list ordered by ``created_at DESC, id DESC``.

        Pass the opaque ``next_cursor`` from a previous response as ``after_cursor``
        to retrieve the following page.  ``has_more`` indicates whether another
        page exists.  ``total`` is always -1 (count query omitted for performance).
        """
        owner_id = current_user.id
        after_created_at = None
        after_id = None

        if after_cursor:
            decoded = decode_lead_cursor(after_cursor)
            if decoded is not None:
                after_created_at, after_id = decoded

        try:
            rows = await self._repo.list_leads_for_owner_cursor(
                owner_id=owner_id,
                filters=filters,
                limit=limit,
                after_created_at=after_created_at,
                after_id=after_id,
            )
        except SQLAlchemyError as exc:
            raise LeadPipelineValidationError("Could not load leads.") from exc

        page_size = min(max(limit, 1), 200)
        has_more = len(rows) > page_size
        page_rows = rows[:page_size]

        next_cursor: str | None = None
        if has_more and page_rows:
            last = page_rows[-1]
            next_cursor = encode_lead_cursor(last.created_at, last.id)

        return LeadListResponse(
            items=[LeadListItem.model_validate(r) for r in page_rows],
            total=len(page_rows),
            next_cursor=next_cursor,
            has_more=has_more,
        )

    async def get_lead_detail_for_owner(
        self,
        current_user: User,
        lead_id: uuid.UUID,
    ) -> LeadRead:
        row = await self._repo.get_lead_by_id_for_owner(
            owner_id=current_user.id,
            lead_id=lead_id,
        )
        if row is None:
            raise LeadNotFoundError()
        try:
            await self._events.emit_lead_viewed(
                lead_id=lead_id,
                actor_user_id=current_user.id,
            )
            await self._repo.commit()
        except SQLAlchemyError as exc:
            await self._repo.rollback()
            raise LeadPipelineValidationError("Could not record lead view.") from exc
        return LeadRead.model_validate(row)

    async def list_lead_timeline_for_owner(
        self,
        current_user: User,
        lead_id: uuid.UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> LeadEventListResponse:
        row = await self._repo.get_lead_by_id_for_owner(
            owner_id=current_user.id,
            lead_id=lead_id,
        )
        if row is None:
            raise LeadNotFoundError()
        try:
            items, total = await self._events.list_timeline_for_owner(
                owner_id=current_user.id,
                lead_id=lead_id,
                limit=limit,
                offset=offset,
            )
        except SQLAlchemyError as exc:
            raise LeadPipelineValidationError("Could not load lead timeline.") from exc
        return LeadEventListResponse(
            items=[LeadEventRead.model_validate(e) for e in items],
            total=total,
        )

    async def update_lead_pipeline(
        self,
        current_user: User,
        lead_id: uuid.UUID,
        patch: LeadPipelinePatch,
    ) -> LeadRead:
        fields_set = patch.model_fields_set
        if not fields_set:
            raise LeadPipelineValidationError("At least one field must be provided.")

        touch_status = "status" in fields_set
        touch_temperature = "lead_temperature" in fields_set
        touch_notes = "notes" in fields_set
        touch_assignee = "assignee_user_id" in fields_set

        row = await self._repo.get_lead_by_id_for_owner(
            owner_id=current_user.id,
            lead_id=lead_id,
        )
        if row is None:
            raise LeadNotFoundError()

        if touch_status and patch.status is None:
            raise LeadPipelineValidationError(
                "status must be one of the pipeline values when included in the update.",
            )

        new_status = patch.status if touch_status and patch.status is not None else row.status

        if touch_status:
            try:
                validate_lead_status_change(row.status, new_status)
            except LeadStatusTransitionError as exc:
                raise LeadInvalidStatusTransitionError(str(exc)) from exc

        snap_status = row.status
        snap_temp = row.lead_temperature
        snap_notes = row.notes
        snap_assignee = row.assignee_user_id

        try:
            updated = await self._repo.update_lead_pipeline_fields(
                owner_id=current_user.id,
                lead_id=lead_id,
                status=new_status,
                lead_temperature=patch.lead_temperature if touch_temperature else None,
                notes=patch.notes if touch_notes else None,
                assignee_user_id=patch.assignee_user_id if touch_assignee else None,
                touch_status=touch_status,
                touch_temperature=touch_temperature,
                touch_notes=touch_notes,
                touch_assignee=touch_assignee,
            )

            assert updated is not None

            if touch_status and snap_status != updated.status:
                await self._events.emit_lead_status_changed(
                    lead_id=lead_id,
                    actor_user_id=current_user.id,
                    old_status=snap_status,
                    new_status=updated.status,
                    old_temperature=snap_temp,
                    new_temperature=updated.lead_temperature,
                )
            elif touch_temperature and snap_temp != updated.lead_temperature:
                await self._events.emit_system_action(
                    lead_id=lead_id,
                    action="lead_temperature_changed",
                    metadata={
                        "old_lead_temperature": snap_temp,
                        "new_lead_temperature": updated.lead_temperature,
                    },
                )

            if touch_notes and snap_notes != updated.notes:
                await self._events.emit_note_added(
                    lead_id=lead_id,
                    actor_user_id=current_user.id,
                    previous_notes=snap_notes,
                    new_notes=updated.notes,
                )

            if touch_assignee and snap_assignee != updated.assignee_user_id:
                await self._events.emit_assignee_change(
                    lead_id=lead_id,
                    actor_user_id=current_user.id,
                    old_assignee_id=snap_assignee,
                    new_assignee_id=updated.assignee_user_id,
                )

            await self._repo.commit()
        except IntegrityError as exc:
            await self._repo.rollback()
            raise LeadPipelineValidationError("Invalid assignee user id.") from exc
        except SQLAlchemyError as exc:
            await self._repo.rollback()
            raise LeadPipelineValidationError("Could not save lead changes.") from exc

        return LeadRead.model_validate(updated)


__all__ = ["LeadPipelineService"]
