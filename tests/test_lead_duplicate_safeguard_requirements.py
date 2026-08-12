"""
Product QA checklist: lead duplicates and creation safeguards.

CHECK 1 — Same conversation does not create multiple leads.
CHECK 2 — Obviously weak payloads are blocked when all low-signal criteria align.
CHECK 3 — Repeated identical conditions are safe (stable outcomes, no double inserts).
CHECK 4 — Suspicious phone velocity is logged; skips are logged without full phone numbers.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from app.models.lead import LEAD_OPEN_PIPELINE_STATUSES
from app.services.lead_creation_service import LeadCreationService
from app.services.lead_safeguards import normalize_phone_digits


def _ids() -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


def _bot(*, owner_id: uuid.UUID, goal_type: str = "sales", niche_id: str | None = "generic") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        owner_id=owner_id,
        goal_type=goal_type,
        niche_id=niche_id,
    )


def _conversation(
    *,
    owner_id: uuid.UUID,
    bot_id: uuid.UUID,
    current_state: str = "closing",
    niche_snapshot: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        owner_id=owner_id,
        bot_id=bot_id,
        current_state=current_state,
        niche_id_snapshot=niche_snapshot,
    )


def _owner(oid: uuid.UUID | None = None) -> SimpleNamespace:
    return SimpleNamespace(id=oid or uuid.uuid4())


def _eligible_payload(*, phone: str = "+15550009999") -> dict[str, str]:
    return {"primary_need": "widgets", "phone": phone, "full_name": "Jordan Case"}


class _StubLeadRepo:
    def __init__(self, existing: object | None = None) -> None:
        self.existing = existing
        self.create_calls: list[dict[str, object]] = []

    async def get_lead_by_conversation_id(self, conversation_id: uuid.UUID) -> object | None:
        return self.existing

    async def find_open_lead_same_normalized_phone(self, **kwargs: object) -> object | None:
        return None

    async def count_leads_same_phone_recent(self, **kwargs: object) -> int:
        return 0

    async def create_lead(self, **kwargs: object) -> SimpleNamespace:
        self.create_calls.append(dict(kwargs))
        return SimpleNamespace(id=uuid.uuid4(), **kwargs)


class _StatefulLeadRepo:
    """In-memory store by conversation_id (same pattern as unit tests)."""

    def __init__(self) -> None:
        self._by_conversation: dict[uuid.UUID, SimpleNamespace] = {}
        self.create_calls: list[dict[str, object]] = []

    async def get_lead_by_conversation_id(self, conversation_id: uuid.UUID) -> SimpleNamespace | None:
        return self._by_conversation.get(conversation_id)

    async def find_open_lead_same_normalized_phone(self, **kwargs: object) -> SimpleNamespace | None:
        return None

    async def count_leads_same_phone_recent(self, **kwargs: object) -> int:
        return 0

    async def create_lead(self, **kwargs: object) -> SimpleNamespace:
        self.create_calls.append(dict(kwargs))
        cid = kwargs["conversation_id"]
        assert isinstance(cid, uuid.UUID)
        lead = SimpleNamespace(id=uuid.uuid4(), **kwargs)
        self._by_conversation[cid] = lead
        return lead


class _PhoneAwareStatefulLeadRepo(_StatefulLeadRepo):
    """
    Mirrors duplicate-phone behavior: find_open matches normalized digits on stored rows
    (status defaults to open pipeline when omitted on the namespace).
    """

    async def find_open_lead_same_normalized_phone(
        self,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
        phone_digits: str,
        **_: object,
    ) -> SimpleNamespace | None:
        for lead in self._by_conversation.values():
            if lead.owner_id != owner_id or lead.bot_id != bot_id:
                continue
            st = getattr(lead, "status", "new")
            if st not in LEAD_OPEN_PIPELINE_STATUSES:
                continue
            if normalize_phone_digits(getattr(lead, "phone", None)) == phone_digits:
                return lead
        return None

    async def count_leads_same_phone_recent(
        self,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
        phone_digits: str,
        **_: object,
    ) -> int:
        n = 0
        for lead in self._by_conversation.values():
            if lead.owner_id != owner_id or lead.bot_id != bot_id:
                continue
            if normalize_phone_digits(getattr(lead, "phone", None)) == phone_digits:
                n += 1
        return n


class _VelocityCountRepo(_StubLeadRepo):
    def __init__(self, count: int) -> None:
        super().__init__(existing=None)
        self._count = count

    async def count_leads_same_phone_recent(self, **kwargs: object) -> int:
        return self._count


# --- CHECK 1: conversation uniqueness ---


@pytest.mark.asyncio
async def test_check1_same_conversation_never_second_insert_stateful_repo() -> None:
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid)
    conv = _conversation(owner_id=oid, bot_id=bot.id)
    owner = _owner(oid)
    repo = _StatefulLeadRepo()
    svc = LeadCreationService(repo)
    data = _eligible_payload()

    for i in range(5):
        res = await svc.try_create_lead_from_conversation(
            bot=bot,
            owner=owner,
            conversation=conv,
            collected_data_json=data,
            lead_score=30 + i,
            lead_temperature="warm",
            summary=f"Attempt {i} same conversation.",
            source_channel="web",
        )
        if i == 0:
            assert res.created is True
            assert res.reason == "created"
        else:
            assert res.created is False
            assert res.reason == "skipped_duplicate_conversation"
            assert res.lead is repo._by_conversation[conv.id]

    assert len(repo.create_calls) == 1


@pytest.mark.asyncio
async def test_check1_get_lead_by_conversation_runs_before_create_lead() -> None:
    """Duplicate conversation short-circuits before phone / quality queries."""
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid)
    conv = _conversation(owner_id=oid, bot_id=bot.id)
    owner = _owner(oid)
    existing = SimpleNamespace(id=uuid.uuid4())

    class _TrackingRepo(_StubLeadRepo):
        def __init__(self) -> None:
            super().__init__(existing=existing)
            self.seen: list[str] = []

        async def get_lead_by_conversation_id(self, conversation_id: uuid.UUID) -> object | None:
            self.seen.append("get_conversation")
            return self.existing

        async def find_open_lead_same_normalized_phone(self, **kwargs: object) -> object | None:
            self.seen.append("find_phone")
            return None

        async def count_leads_same_phone_recent(self, **kwargs: object) -> int:
            self.seen.append("count_phone")
            return 0

    track = _TrackingRepo()
    svc = LeadCreationService(track)
    res = await svc.try_create_lead_from_conversation(
        bot=bot,
        owner=owner,
        conversation=conv,
        collected_data_json=_eligible_payload(),
        lead_score=50,
        lead_temperature="warm",
        summary="ok summary here",
        source_channel="web",
    )
    assert res.reason == "skipped_duplicate_conversation"
    assert track.seen == ["get_conversation"]
    assert track.create_calls == []


# --- CHECK 2: weak lead blocked ---


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("summary", "name_key", "score"),
    [
        ("", None, 0),
        ("junk", None, 10),
        ("short", "Al", 10),
        ("x" * 7, "Al", 10),
    ],
)
async def test_check2_weak_lead_rejected_when_all_signals_weak(
    summary: str,
    name_key: str | None,
    score: int,
) -> None:
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid)
    conv = _conversation(owner_id=oid, bot_id=bot.id)
    owner = _owner(oid)
    repo = _StubLeadRepo()
    svc = LeadCreationService(repo)
    data: dict[str, str] = {"primary_need": "x", "phone": "+15550001234"}
    if name_key is not None:
        data["full_name"] = name_key

    res = await svc.try_create_lead_from_conversation(
        bot=bot,
        owner=owner,
        conversation=conv,
        collected_data_json=data,
        lead_score=score,
        lead_temperature="cold",
        summary=summary,
        source_channel="web",
    )
    assert res.created is False
    assert res.reason == "skipped_low_quality_signals"
    assert repo.create_calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("summary", "name_extra", "score"),
    [
        ("x" * 8, None, 0),
        ("", None, 15),
        ("no", "Sam", 0),
    ],
)
async def test_check2_borderline_allowed_if_any_qualification_stronger(
    summary: str,
    name_extra: str | None,
    score: int,
) -> None:
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid)
    conv = _conversation(owner_id=oid, bot_id=bot.id)
    owner = _owner(oid)
    repo = _StubLeadRepo()
    svc = LeadCreationService(repo)
    data: dict[str, str] = {"primary_need": "x", "phone": "+15550001234"}
    if name_extra:
        data["full_name"] = name_extra

    res = await svc.try_create_lead_from_conversation(
        bot=bot,
        owner=owner,
        conversation=conv,
        collected_data_json=data,
        lead_score=score,
        lead_temperature="cold",
        summary=summary,
        source_channel="web",
    )
    assert res.created is True
    assert res.reason == "created"
    assert len(repo.create_calls) == 1


# --- CHECK 3: repeated / identical conditions ---


@pytest.mark.asyncio
async def test_check3_repeated_weak_attempts_same_conversation_never_insert() -> None:
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid)
    conv = _conversation(owner_id=oid, bot_id=bot.id)
    owner = _owner(oid)
    repo = _StubLeadRepo()
    svc = LeadCreationService(repo)
    weak = {"primary_need": "x", "phone": "+15550001234"}

    for _ in range(4):
        res = await svc.try_create_lead_from_conversation(
            bot=bot,
            owner=owner,
            conversation=conv,
            collected_data_json=weak,
            lead_score=5,
            lead_temperature="cold",
            summary="bad",
            source_channel="web",
        )
        assert res.created is False
        assert res.reason == "skipped_low_quality_signals"

    assert repo.create_calls == []


@pytest.mark.asyncio
async def test_check3_duplicate_conversation_takes_precedence_over_quality_gate() -> None:
    """If a row already exists for the conversation, do not re-evaluate as low-quality skip."""
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid)
    conv = _conversation(owner_id=oid, bot_id=bot.id)
    owner = _owner(oid)
    dup = SimpleNamespace(id=uuid.uuid4())
    repo = _StubLeadRepo(existing=dup)
    svc = LeadCreationService(repo)

    res = await svc.try_create_lead_from_conversation(
        bot=bot,
        owner=owner,
        conversation=conv,
        collected_data_json={"primary_need": "x", "phone": "+15550001234"},
        lead_score=0,
        lead_temperature="cold",
        summary="x",
        source_channel="web",
    )
    assert res.reason == "skipped_duplicate_conversation"
    assert res.lead is dup
    assert repo.create_calls == []


@pytest.mark.asyncio
async def test_check3_second_conversation_same_phone_blocked_when_first_still_open() -> None:
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid)
    owner = _owner(oid)
    shared_phone = "+1 (555) 000-9999"
    data = {**_eligible_payload(phone=shared_phone)}

    conv_a = _conversation(owner_id=oid, bot_id=bot.id)
    conv_b = _conversation(owner_id=oid, bot_id=bot.id)
    repo = _PhoneAwareStatefulLeadRepo()
    svc = LeadCreationService(repo)

    r1 = await svc.try_create_lead_from_conversation(
        bot=bot,
        owner=owner,
        conversation=conv_a,
        collected_data_json=data,
        lead_score=40,
        lead_temperature="warm",
        summary="First conversation qualifies.",
        source_channel="web",
    )
    assert r1.created is True
    assert len(repo.create_calls) == 1

    r2 = await svc.try_create_lead_from_conversation(
        bot=bot,
        owner=owner,
        conversation=conv_b,
        collected_data_json=data,
        lead_score=90,
        lead_temperature="hot",
        summary="Second conversation also strong but same phone.",
        source_channel="web",
    )
    assert r2.created is False
    assert r2.reason == "skipped_duplicate_phone_open_pipeline"
    assert r2.lead is repo._by_conversation[conv_a.id]
    assert len(repo.create_calls) == 1


# --- CHECK 4: logging / safe ignore ---


@pytest.mark.asyncio
async def test_check4_low_quality_emits_safeguard_skip_log() -> None:
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid)
    conv = _conversation(owner_id=oid, bot_id=bot.id)
    owner = _owner(oid)
    repo = _StubLeadRepo()
    svc = LeadCreationService(repo)

    with patch("app.services.lead_creation_service._LOG.warning") as warn:
        res = await svc.try_create_lead_from_conversation(
            bot=bot,
            owner=owner,
            conversation=conv,
            collected_data_json={"primary_need": "x", "phone": "+15550001234"},
            lead_score=10,
            lead_temperature="cold",
            summary="weak",
            source_channel="web",
        )

    assert res.reason == "skipped_low_quality_signals"
    events = [c.args[0] for c in warn.call_args_list if c.args]
    assert "lead_creation_safeguard_skip" in events
    low_calls = [
        c for c in warn.call_args_list if c.args and c.args[0] == "lead_creation_safeguard_skip"
    ]
    assert low_calls and low_calls[0].kwargs.get("reason") == "skipped_low_quality_signals"


@pytest.mark.asyncio
async def test_check4_phone_duplicate_log_contains_last4_not_full_number() -> None:
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid)
    conv = _conversation(owner_id=oid, bot_id=bot.id)
    owner = _owner(oid)
    dup = SimpleNamespace(id=uuid.uuid4())

    class _AlwaysDupPhone(_StubLeadRepo):
        async def find_open_lead_same_normalized_phone(self, **kwargs: object) -> SimpleNamespace:
            return dup

    repo = _AlwaysDupPhone()
    svc = LeadCreationService(repo)
    full_digits = "15550001234"

    with patch("app.services.lead_creation_service._LOG.warning") as warn:
        res = await svc.try_create_lead_from_conversation(
            bot=bot,
            owner=owner,
            conversation=conv,
            collected_data_json={"primary_need": "x", "phone": "+1 (555) 000-1234"},
            lead_score=50,
            lead_temperature="warm",
            summary="Summary has enough characters.",
            source_channel="web",
        )

    assert res.reason == "skipped_duplicate_phone_open_pipeline"
    flat = repr(warn.call_args_list)
    assert full_digits not in flat
    skip = [c for c in warn.call_args_list if c.args and c.args[0] == "lead_creation_safeguard_skip"][0]
    assert skip.kwargs.get("phone_last4") == "1234"


@pytest.mark.asyncio
async def test_check4_velocity_not_logged_when_recent_count_below_four() -> None:
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid)
    conv = _conversation(owner_id=oid, bot_id=bot.id)
    owner = _owner(oid)
    repo = _VelocityCountRepo(3)
    svc = LeadCreationService(repo)

    with patch("app.services.lead_creation_service._LOG.warning") as warn:
        res = await svc.try_create_lead_from_conversation(
            bot=bot,
            owner=owner,
            conversation=conv,
            collected_data_json=_eligible_payload(),
            lead_score=50,
            lead_temperature="warm",
            summary="Enough summary for quality gate.",
            source_channel="web",
        )

    assert res.created is True
    events = [c.args[0] for c in warn.call_args_list if c.args]
    assert "lead_creation_suspicious_phone_velocity" not in events


@pytest.mark.asyncio
async def test_check4_velocity_logged_when_count_reaches_four() -> None:
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid)
    conv = _conversation(owner_id=oid, bot_id=bot.id)
    owner = _owner(oid)
    repo = _VelocityCountRepo(4)
    svc = LeadCreationService(repo)

    with patch("app.services.lead_creation_service._LOG.warning") as warn:
        res = await svc.try_create_lead_from_conversation(
            bot=bot,
            owner=owner,
            conversation=conv,
            collected_data_json=_eligible_payload(),
            lead_score=50,
            lead_temperature="warm",
            summary="Enough summary for quality gate.",
            source_channel="web",
        )

    assert res.created is True
    events = [c.args[0] for c in warn.call_args_list if c.args]
    assert "lead_creation_suspicious_phone_velocity" in events
