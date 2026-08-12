"""Tests for :mod:`app.services.lead_pipeline_service`.

Covers owner scoping (list / detail / update), status updates, and pipeline transition rules.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from app.repositories.lead_repository import LeadListFilters
from app.schemas.lead import LeadPipelinePatch
from app.services.lead_pipeline_exceptions import (
    LeadInvalidStatusTransitionError,
    LeadNotFoundError,
    LeadPipelineValidationError,
)
from app.services.lead_pipeline_service import LeadPipelineService


def _user(uid: uuid.UUID | None = None) -> SimpleNamespace:
    return SimpleNamespace(id=uid or uuid.uuid4())


def _lead_row(
    *,
    owner_id: uuid.UUID,
    lead_id: uuid.UUID | None = None,
    bot_id: uuid.UUID | None = None,
    status: str = "new",
    lead_temperature: str | None = "warm",
    notes: str | None = None,
    assignee_user_id: uuid.UUID | None = None,
    updated_at: datetime | None = None,
) -> SimpleNamespace:
    now = updated_at or datetime.now(tz=UTC)
    lid = lead_id or uuid.uuid4()
    bid = bot_id or uuid.uuid4()
    return SimpleNamespace(
        id=lid,
        bot_id=bid,
        owner_id=owner_id,
        conversation_id=None,
        niche_id="generic",
        lead_score=10,
        lead_temperature=lead_temperature,
        status=status,
        name="N",
        phone="+1",
        summary="S",
        notes=notes,
        assignee_user_id=assignee_user_id,
        source_channel="web",
        collected_data_json=None,
        created_at=now,
        updated_at=now,
    )


class _FakeLeadPipelineRepo:
    """
    In-memory stand-in for :class:`~app.repositories.lead_repository.LeadRepository`
    with the same owner-scoping contract as the real implementation.
    """

    def __init__(self, leads: list[SimpleNamespace]) -> None:
        self.leads = leads
        self.committed = False
        self.rolled_back = False

    def _matching(
        self,
        owner_id: uuid.UUID,
        filters: LeadListFilters | None,
    ) -> list[SimpleNamespace]:
        f = filters or LeadListFilters()
        out: list[SimpleNamespace] = []
        for row in self.leads:
            if row.owner_id != owner_id:
                continue
            if f.status is not None and row.status != f.status:
                continue
            if f.bot_id is not None and row.bot_id != f.bot_id:
                continue
            out.append(row)
        out.sort(key=lambda r: r.updated_at, reverse=True)
        return out

    async def list_leads_for_owner(
        self,
        *,
        owner_id: uuid.UUID,
        filters: LeadListFilters | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SimpleNamespace]:
        rows = self._matching(owner_id, filters)
        lo = max(offset, 0)
        lim = min(max(limit, 1), 200)
        return rows[lo : lo + lim]

    async def count_leads_for_owner(
        self,
        *,
        owner_id: uuid.UUID,
        filters: LeadListFilters | None = None,
    ) -> int:
        return len(self._matching(owner_id, filters))

    async def get_lead_by_id_for_owner(
        self,
        *,
        owner_id: uuid.UUID,
        lead_id: uuid.UUID,
    ) -> SimpleNamespace | None:
        for row in self.leads:
            if row.id == lead_id and row.owner_id == owner_id:
                return row
        return None

    async def update_lead_pipeline_fields(
        self,
        *,
        owner_id: uuid.UUID,
        lead_id: uuid.UUID,
        status: str | None = None,
        lead_temperature: str | None = None,
        notes: str | None = None,
        assignee_user_id: uuid.UUID | None = None,
        touch_status: bool = False,
        touch_temperature: bool = False,
        touch_notes: bool = False,
        touch_assignee: bool = False,
    ) -> SimpleNamespace | None:
        row = await self.get_lead_by_id_for_owner(owner_id=owner_id, lead_id=lead_id)
        if row is None:
            return None
        if touch_status and status is not None:
            row.status = status
        if touch_temperature:
            row.lead_temperature = lead_temperature
        if touch_notes:
            row.notes = notes
        if touch_assignee:
            row.assignee_user_id = assignee_user_id
        row.updated_at = datetime.now(tz=UTC)
        return row

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


def test_owner_lists_only_their_leads() -> None:
    alice = uuid.uuid4()
    bob = uuid.uuid4()
    la1 = _lead_row(owner_id=alice)
    la2 = _lead_row(owner_id=alice)
    lb1 = _lead_row(owner_id=bob)
    repo = _FakeLeadPipelineRepo([la1, la2, lb1])
    svc = LeadPipelineService(repo)

    async def run() -> None:
        a_out = await svc.list_leads_for_owner(_user(alice))
        b_out = await svc.list_leads_for_owner(_user(bob))
        assert a_out.total == 2
        assert {i.id for i in a_out.items} == {la1.id, la2.id}
        assert b_out.total == 1
        assert b_out.items[0].id == lb1.id

    asyncio.run(run())


def test_owner_list_respects_status_filter() -> None:
    owner_id = uuid.uuid4()
    new_lead = _lead_row(owner_id=owner_id, status="new")
    won_lead = _lead_row(owner_id=owner_id, status="won")
    repo = _FakeLeadPipelineRepo([new_lead, won_lead])
    svc = LeadPipelineService(repo)

    async def run() -> None:
        out = await svc.list_leads_for_owner(
            _user(owner_id),
            filters=LeadListFilters(status="won"),
        )
        assert out.total == 1
        assert out.items[0].id == won_lead.id

    asyncio.run(run())


def test_other_owner_list_does_not_include_foreign_leads() -> None:
    alice = uuid.uuid4()
    bob = uuid.uuid4()
    only_alice = _lead_row(owner_id=alice)
    repo = _FakeLeadPipelineRepo([only_alice])
    svc = LeadPipelineService(repo)

    async def run() -> None:
        b_out = await svc.list_leads_for_owner(_user(bob))
        assert b_out.total == 0
        assert b_out.items == []

    asyncio.run(run())


def test_owner_gets_detail_of_own_lead() -> None:
    owner_id = uuid.uuid4()
    row = _lead_row(owner_id=owner_id, notes="keep")
    svc = LeadPipelineService(_FakeLeadPipelineRepo([row]))

    async def run() -> None:
        detail = await svc.get_lead_detail_for_owner(_user(owner_id), row.id)
        assert detail.id == row.id
        assert detail.owner_id == owner_id
        assert detail.notes == "keep"
        assert detail.status == "new"

    asyncio.run(run())


def test_non_owner_cannot_get_another_users_lead_detail() -> None:
    owner_id = uuid.uuid4()
    row = _lead_row(owner_id=owner_id)
    svc = LeadPipelineService(_FakeLeadPipelineRepo([row]))

    async def run() -> None:
        with pytest.raises(LeadNotFoundError):
            await svc.get_lead_detail_for_owner(_user(uuid.uuid4()), row.id)

    asyncio.run(run())


def test_status_update_persists_open_pipeline() -> None:
    owner_id = uuid.uuid4()
    row = _lead_row(owner_id=owner_id, status="new")
    repo = _FakeLeadPipelineRepo([row])
    svc = LeadPipelineService(repo)

    async def run() -> None:
        out = await svc.update_lead_pipeline(
            _user(owner_id),
            row.id,
            LeadPipelinePatch.model_validate({"status": "contacted"}),
        )
        assert out.status == "contacted"
        assert row.status == "contacted"
        assert repo.committed is True

    asyncio.run(run())


def test_non_owner_cannot_update_another_users_lead() -> None:
    owner_id = uuid.uuid4()
    row = _lead_row(owner_id=owner_id, status="new")
    repo = _FakeLeadPipelineRepo([row])
    svc = LeadPipelineService(repo)

    async def run() -> None:
        with pytest.raises(LeadNotFoundError):
            await svc.update_lead_pipeline(
                _user(uuid.uuid4()),
                row.id,
                LeadPipelinePatch.model_validate({"status": "qualified"}),
            )
        assert row.status == "new"
        assert repo.committed is False

    asyncio.run(run())


def test_transition_allows_backward_move_in_open_pipeline() -> None:
    owner_id = uuid.uuid4()
    row = _lead_row(owner_id=owner_id, status="proposal")
    repo = _FakeLeadPipelineRepo([row])
    svc = LeadPipelineService(repo)

    async def run() -> None:
        out = await svc.update_lead_pipeline(
            _user(owner_id),
            row.id,
            LeadPipelinePatch.model_validate({"status": "new"}),
        )
        assert out.status == "new"

    asyncio.run(run())


def test_transition_terminal_blocks_leaving_won() -> None:
    owner_id = uuid.uuid4()
    row = _lead_row(owner_id=owner_id, status="won")
    repo = _FakeLeadPipelineRepo([row])
    svc = LeadPipelineService(repo)

    async def run() -> None:
        with pytest.raises(LeadInvalidStatusTransitionError):
            await svc.update_lead_pipeline(
                _user(owner_id),
                row.id,
                LeadPipelinePatch.model_validate({"status": "proposal"}),
            )
        assert repo.committed is False

    asyncio.run(run())


def test_transition_terminal_blocks_switching_between_won_and_lost() -> None:
    owner_id = uuid.uuid4()
    row = _lead_row(owner_id=owner_id, status="won")
    repo = _FakeLeadPipelineRepo([row])
    svc = LeadPipelineService(repo)

    async def run() -> None:
        with pytest.raises(LeadInvalidStatusTransitionError):
            await svc.update_lead_pipeline(
                _user(owner_id),
                row.id,
                LeadPipelinePatch.model_validate({"status": "lost"}),
            )

    asyncio.run(run())


def test_transition_idempotent_same_status_on_terminal_allowed() -> None:
    owner_id = uuid.uuid4()
    row = _lead_row(owner_id=owner_id, status="won", notes=None)
    repo = _FakeLeadPipelineRepo([row])
    svc = LeadPipelineService(repo)

    async def run() -> None:
        out = await svc.update_lead_pipeline(
            _user(owner_id),
            row.id,
            LeadPipelinePatch.model_validate({"status": "won", "notes": "paper trail"}),
        )
        assert out.status == "won"
        assert out.notes == "paper trail"
        assert repo.committed is True

    asyncio.run(run())


def test_update_notes_on_terminal_without_status_change() -> None:
    owner_id = uuid.uuid4()
    row = _lead_row(owner_id=owner_id, status="won")
    repo = _FakeLeadPipelineRepo([row])
    svc = LeadPipelineService(repo)

    async def run() -> None:
        out = await svc.update_lead_pipeline(
            _user(owner_id),
            row.id,
            LeadPipelinePatch.model_validate({"notes": "call next week"}),
        )
        assert out.notes == "call next week"
        assert out.status == "won"
        assert repo.committed is True

    asyncio.run(run())


def test_update_blocked_from_terminal_status_change() -> None:
    owner_id = uuid.uuid4()
    row = _lead_row(owner_id=owner_id, status="lost")
    repo = _FakeLeadPipelineRepo([row])
    svc = LeadPipelineService(repo)

    async def run() -> None:
        with pytest.raises(LeadInvalidStatusTransitionError):
            await svc.update_lead_pipeline(
                _user(owner_id),
                row.id,
                LeadPipelinePatch.model_validate({"status": "new"}),
            )
        assert repo.committed is False

    asyncio.run(run())


def test_empty_patch_rejected() -> None:
    owner_id = uuid.uuid4()
    row = _lead_row(owner_id=owner_id)
    svc = LeadPipelineService(_FakeLeadPipelineRepo([row]))

    async def run() -> None:
        with pytest.raises(LeadPipelineValidationError):
            await svc.update_lead_pipeline(_user(owner_id), row.id, LeadPipelinePatch())

    asyncio.run(run())
