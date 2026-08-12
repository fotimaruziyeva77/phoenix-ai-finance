"""Tests for :mod:`app.services.lead_creation_service`.

Covers: eligible conversation creates a lead; incomplete conversations never call ``create_lead``;
duplicate prevention (same ``conversation_id``); populated fields; ``lead_score`` and ``summary``.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from app.services.lead_creation_service import (
    LeadCreationService,
    evaluate_lead_creation_gates,
    extract_phone_for_lead,
)


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
    current_state: str,
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


def test_evaluate_gates_requires_sales_bot() -> None:
    owner_id, _, _ = _ids()
    bot = _bot(owner_id=owner_id, goal_type="support")
    conv = _conversation(owner_id=owner_id, bot_id=bot.id, current_state="closing")
    ok, reason = evaluate_lead_creation_gates(
        bot=bot,
        conversation=conv,
        collected_data_json={"primary_need": "x", "phone": "+1"},
    )
    assert ok is False
    assert reason == "skipped_not_sales_bot"


def test_evaluate_gates_requires_closing_or_completed() -> None:
    owner_id, _, _ = _ids()
    bot = _bot(owner_id=owner_id)
    conv = _conversation(owner_id=owner_id, bot_id=bot.id, current_state="qualification")
    ok, reason = evaluate_lead_creation_gates(
        bot=bot,
        conversation=conv,
        collected_data_json={"primary_need": "x", "phone": "+1"},
    )
    assert ok is False
    assert reason == "skipped_funnel_not_ready"


@pytest.mark.parametrize("state", ("closing", "completed", "CLOSING"))
def test_evaluate_gates_accepts_late_funnel_states(state: str) -> None:
    owner_id, _, _ = _ids()
    bot = _bot(owner_id=owner_id)
    conv = _conversation(owner_id=owner_id, bot_id=bot.id, current_state=state)
    ok, _ = evaluate_lead_creation_gates(
        bot=bot,
        conversation=conv,
        # Phone must now carry >= 7 digits to count as a valid contact.
        collected_data_json={"primary_need": "need", "phone": "+15551234567"},
    )
    assert ok is True


def test_evaluate_gates_requires_required_core_fields_for_niche() -> None:
    owner_id, _, _ = _ids()
    bot = _bot(owner_id=owner_id, niche_id="education")
    conv = _conversation(
        owner_id=owner_id,
        bot_id=bot.id,
        current_state="closing",
        niche_snapshot="education",
    )
    # Education's only required core field is now ``student_grade``; omit it (while supplying an
    # optional field + a valid phone) so the gate fails on required fields, not on phone.
    ok, reason = evaluate_lead_creation_gates(
        bot=bot,
        conversation=conv,
        collected_data_json={"subject": "math", "phone": "+15551234567"},
    )
    assert ok is False
    assert reason == "skipped_required_fields_incomplete"

    # Providing the single required field + a valid phone satisfies every gate.
    ok2, _ = evaluate_lead_creation_gates(
        bot=bot,
        conversation=conv,
        collected_data_json={
            "student_grade": "9",
            "phone": "+15551234567",
        },
    )
    assert ok2 is True


def test_evaluate_gates_requires_phone_in_json_or_explicit() -> None:
    owner_id, _, _ = _ids()
    bot = _bot(owner_id=owner_id)
    conv = _conversation(owner_id=owner_id, bot_id=bot.id, current_state="closing")
    ok, reason = evaluate_lead_creation_gates(
        bot=bot,
        conversation=conv,
        collected_data_json={"primary_need": "x"},
        explicit_phone=None,
    )
    assert ok is False
    assert reason == "skipped_phone_required"

    ok2, _ = evaluate_lead_creation_gates(
        bot=bot,
        conversation=conv,
        collected_data_json={"primary_need": "x"},
        explicit_phone="  +15551212 ",
    )
    assert ok2 is True


def test_extract_phone_prefers_explicit() -> None:
    # Both phones are now valid (>= 7 digits); the explicit phone still wins over the JSON one.
    assert extract_phone_for_lead({"phone": "+15559990000"}, "+15551112222") == "+15551112222"


class _FakeNestedTx:
    """Async no-op savepoint context manager for stub repos."""

    async def __aenter__(self) -> "_FakeNestedTx":
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False


class _FakeSession:
    """Minimal stand-in exposing ``begin_nested()`` used by LeadCreationService."""

    def begin_nested(self) -> _FakeNestedTx:
        return _FakeNestedTx()


class _StubLeadRepo:
    def __init__(self, existing: object | None = None) -> None:
        self.existing = existing
        self.create_calls: list[dict[str, object]] = []

    @property
    def session(self) -> _FakeSession:
        return _FakeSession()

    async def get_lead_by_conversation_id(self, conversation_id: uuid.UUID) -> object | None:
        return self.existing

    async def find_open_lead_same_normalized_phone(self, **kwargs: object) -> object | None:
        return None

    async def count_leads_same_phone_recent(self, **kwargs: object) -> int:
        return 0

    async def create_lead(self, **kwargs: object) -> SimpleNamespace:
        self.create_calls.append(kwargs)
        return SimpleNamespace(id=uuid.uuid4(), **kwargs)


class _StatefulLeadRepo:
    """Simulates DB: first create stores by ``conversation_id``; later gets see the row."""

    def __init__(self) -> None:
        self._by_conversation: dict[uuid.UUID, SimpleNamespace] = {}
        self.create_calls: list[dict[str, object]] = []

    @property
    def session(self) -> _FakeSession:
        return _FakeSession()

    async def get_lead_by_conversation_id(self, conversation_id: uuid.UUID) -> SimpleNamespace | None:
        return self._by_conversation.get(conversation_id)

    async def find_open_lead_same_normalized_phone(self, **kwargs: object) -> SimpleNamespace | None:
        return None

    async def count_leads_same_phone_recent(self, **kwargs: object) -> int:
        return 0

    async def create_lead(self, **kwargs: object) -> SimpleNamespace:
        self.create_calls.append(kwargs)
        cid = kwargs["conversation_id"]
        assert isinstance(cid, uuid.UUID)
        lead = SimpleNamespace(id=uuid.uuid4(), **kwargs)
        self._by_conversation[cid] = lead
        return lead


@pytest.mark.asyncio
async def test_try_create_skips_when_owner_graph_mismatched() -> None:
    oid, other_owner, _ = _ids()
    bot = _bot(owner_id=oid)
    conv = _conversation(owner_id=other_owner, bot_id=bot.id, current_state="closing")
    owner = _owner(oid)
    svc = LeadCreationService(_StubLeadRepo())
    res = await svc.try_create_lead_from_conversation(
        bot=bot,
        owner=owner,
        conversation=conv,
        collected_data_json={"primary_need": "x", "phone": "+1"},
        lead_score=10,
        lead_temperature="cold",
        summary="s",
        source_channel="web_chat",
    )
    assert res.created is False
    assert res.reason == "skipped_owner_bot_conversation_mismatch"


@pytest.mark.asyncio
async def test_try_create_skips_duplicate_conversation() -> None:
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid)
    conv = _conversation(owner_id=oid, bot_id=bot.id, current_state="closing")
    owner = _owner(oid)
    dup = SimpleNamespace(id=uuid.uuid4())
    repo = _StubLeadRepo(existing=dup)
    svc = LeadCreationService(repo)
    res = await svc.try_create_lead_from_conversation(
        bot=bot,
        owner=owner,
        conversation=conv,
        # Valid phone so the gates pass and the duplicate-conversation check is reached.
        collected_data_json={"primary_need": "x", "phone": "+15551234567"},
        lead_score=50,
        lead_temperature="warm",
        summary="summary",
        source_channel="telegram",
    )
    assert res.created is False
    assert res.lead is dup
    assert res.reason == "skipped_duplicate_conversation"
    assert not repo.create_calls


@pytest.mark.asyncio
async def test_valid_conversation_creates_lead_closing_state() -> None:
    """Eligible ``closing`` conversation results in one ``create_lead`` and ``created=True``."""
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid, niche_id="generic")
    conv = _conversation(owner_id=oid, bot_id=bot.id, current_state="closing")
    owner = _owner(oid)
    repo = _StubLeadRepo()
    svc = LeadCreationService(repo)
    data = {"primary_need": "widgets", "phone": "+15551234567"}
    res = await svc.try_create_lead_from_conversation(
        bot=bot,
        owner=owner,
        conversation=conv,
        collected_data_json=data,
        lead_score=73,
        lead_temperature="warm",
        summary="Buyer ready for callback.",
        source_channel="web_chat",
    )
    assert res.created is True
    assert res.reason == "created"
    assert res.lead is not None
    assert getattr(res.lead, "lead_score", None) == 73
    assert getattr(res.lead, "summary", None) == "Buyer ready for callback."
    assert len(repo.create_calls) == 1


@pytest.mark.asyncio
async def test_try_create_persists_when_eligible_completed_state() -> None:
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid, niche_id="generic")
    conv = _conversation(owner_id=oid, bot_id=bot.id, current_state="completed")
    owner = _owner(oid)
    repo = _StubLeadRepo()
    svc = LeadCreationService(repo)
    data = {"primary_need": "widgets", "phone": "+15551234567", "name": "Pat"}
    res = await svc.try_create_lead_from_conversation(
        bot=bot,
        owner=owner,
        conversation=conv,
        collected_data_json=data,
        lead_score=120,
        lead_temperature="hot",
        summary="  ok  ",
        source_channel=" web ",
    )
    assert res.created is True
    assert res.reason == "created"
    assert res.lead is not None
    assert len(repo.create_calls) == 1
    call = repo.create_calls[0]
    assert call["bot_id"] == bot.id
    assert call["owner_id"] == owner.id
    assert call["conversation_id"] == conv.id
    assert call["niche_id"] == "generic"
    assert call["lead_score"] == 100
    assert call["lead_temperature"] == "hot"
    assert call["summary"] == "ok"
    assert call["source_channel"] == "web"
    assert call["phone"] == "+15551234567"
    assert call["name"] == "Pat"
    assert call["collected_data_json"] == data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "data_extra", "expected_reason"),
    [
        ("qualification", {"primary_need": "x", "phone": "+1"}, "skipped_funnel_not_ready"),
        # ``offer`` is now an eligible capture state; with an invalid (too-short) phone the gate
        # falls through to the phone requirement instead of the funnel check.
        ("offer", {"primary_need": "x", "phone": "+1"}, "skipped_phone_required"),
        (
            "closing",
            {"phone": "+1"},
            "skipped_required_fields_incomplete",
        ),
        (
            "closing",
            {"primary_need": "x"},
            "skipped_phone_required",
        ),
    ],
)
async def test_incomplete_conversation_does_not_create_lead_prematurely(
    state: str,
    data_extra: dict[str, str],
    expected_reason: str,
) -> None:
    """Service must not call ``create_lead`` when gates fail (early funnel / missing slots / no phone)."""
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid)
    conv = _conversation(owner_id=oid, bot_id=bot.id, current_state=state)
    owner = _owner(oid)
    repo = _StubLeadRepo()
    svc = LeadCreationService(repo)
    res = await svc.try_create_lead_from_conversation(
        bot=bot,
        owner=owner,
        conversation=conv,
        collected_data_json=data_extra,
        lead_score=80,
        lead_temperature="hot",
        summary="should not persist",
        source_channel="x",
    )
    assert res.created is False
    assert res.lead is None
    assert res.reason == expected_reason
    assert repo.create_calls == []


@pytest.mark.asyncio
async def test_lead_score_passed_through_and_clamped() -> None:
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid)
    conv = _conversation(owner_id=oid, bot_id=bot.id, current_state="closing")
    owner = _owner(oid)
    repo = _StubLeadRepo()
    svc = LeadCreationService(repo)
    base = {"primary_need": "a", "phone": "+15551234567"}
    res_mid = await svc.try_create_lead_from_conversation(
        bot=bot,
        owner=owner,
        conversation=conv,
        collected_data_json=base,
        lead_score=42,
        lead_temperature="cold",
        summary="s",
        source_channel=None,
    )
    assert res_mid.created is True
    assert repo.create_calls[0]["lead_score"] == 42

    conv2 = _conversation(owner_id=oid, bot_id=bot.id, current_state="closing")
    res_low = await svc.try_create_lead_from_conversation(
        bot=bot,
        owner=owner,
        conversation=conv2,
        collected_data_json={**base, "full_name": "Pat"},
        lead_score=-5,
        lead_temperature="cold",
        summary="s2",
        source_channel=None,
    )
    assert res_low.created is True
    assert repo.create_calls[1]["lead_score"] == 0

    conv3 = _conversation(owner_id=oid, bot_id=bot.id, current_state="closing")
    res_high = await svc.try_create_lead_from_conversation(
        bot=bot,
        owner=owner,
        conversation=conv3,
        collected_data_json=base,
        lead_score=999,
        lead_temperature="hot",
        summary="s3",
        source_channel=None,
    )
    assert res_high.created is True
    assert repo.create_calls[2]["lead_score"] == 100


@pytest.mark.asyncio
async def test_summary_truncated_when_exceeds_max_length() -> None:
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid)
    conv = _conversation(owner_id=oid, bot_id=bot.id, current_state="closing")
    owner = _owner(oid)
    repo = _StubLeadRepo()
    svc = LeadCreationService(repo)
    huge = "a" * 5000
    await svc.try_create_lead_from_conversation(
        bot=bot,
        owner=owner,
        conversation=conv,
        collected_data_json={"primary_need": "a", "phone": "+15551234567"},
        lead_score=1,
        lead_temperature="cold",
        summary=huge,
        source_channel=None,
    )
    stored = repo.create_calls[0]["summary"]
    assert isinstance(stored, str)
    assert len(stored) == 4000
    assert stored.endswith("…")


@pytest.mark.asyncio
async def test_summary_attached_and_empty_becomes_none() -> None:
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid)
    owner = _owner(oid)
    repo = _StubLeadRepo()
    svc = LeadCreationService(repo)
    base = {"primary_need": "a", "phone": "+15551234567"}

    conv1 = _conversation(owner_id=oid, bot_id=bot.id, current_state="closing")
    await svc.try_create_lead_from_conversation(
        bot=bot,
        owner=owner,
        conversation=conv1,
        collected_data_json=base,
        lead_score=1,
        lead_temperature="cold",
        summary="  Multi-line\nsummary  ",
        source_channel="tg",
    )
    assert repo.create_calls[0]["summary"] == "Multi-line\nsummary"

    conv2 = _conversation(owner_id=oid, bot_id=bot.id, current_state="closing")
    await svc.try_create_lead_from_conversation(
        bot=bot,
        owner=owner,
        conversation=conv2,
        collected_data_json=base,
        lead_score=20,
        lead_temperature="cold",
        summary="   ",
        source_channel="tg",
    )
    assert repo.create_calls[1]["summary"] is None


@pytest.mark.asyncio
async def test_niche_id_prefers_conversation_snapshot_over_bot() -> None:
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid, niche_id="generic")
    conv = _conversation(
        owner_id=oid,
        bot_id=bot.id,
        current_state="closing",
        niche_snapshot="education",
    )
    owner = _owner(oid)
    repo = _StubLeadRepo()
    svc = LeadCreationService(repo)
    data = {"student_grade": "10", "subject": "physics", "phone": "+15551234567"}
    res = await svc.try_create_lead_from_conversation(
        bot=bot,
        owner=owner,
        conversation=conv,
        collected_data_json=data,
        lead_score=50,
        lead_temperature="warm",
        summary="x",
        source_channel="web",
    )
    assert res.created is True
    assert repo.create_calls[0]["niche_id"] == "education"


@pytest.mark.asyncio
async def test_duplicate_second_invocation_same_conversation_no_second_insert() -> None:
    """After one successful create, a second try with the same conversation id is skipped."""
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid)
    conv = _conversation(owner_id=oid, bot_id=bot.id, current_state="closing")
    owner = _owner(oid)
    repo = _StatefulLeadRepo()
    svc = LeadCreationService(repo)
    payload = {"primary_need": "x", "phone": "+15551234567", "full_name": "Pat"}
    r1 = await svc.try_create_lead_from_conversation(
        bot=bot,
        owner=owner,
        conversation=conv,
        collected_data_json=payload,
        lead_score=10,
        lead_temperature="cold",
        summary="first",
        source_channel="a",
    )
    r2 = await svc.try_create_lead_from_conversation(
        bot=bot,
        owner=owner,
        conversation=conv,
        collected_data_json=payload,
        lead_score=99,
        lead_temperature="hot",
        summary="second attempt",
        source_channel="b",
    )
    assert r1.created is True
    assert r1.lead is not None
    assert r2.created is False
    assert r2.reason == "skipped_duplicate_conversation"
    assert r2.lead is r1.lead
    assert len(repo.create_calls) == 1
    assert repo.create_calls[0]["summary"] == "first"
    assert repo.create_calls[0]["lead_score"] == 10


class _DupOpenPhoneRepo(_StubLeadRepo):
    def __init__(self, dup: SimpleNamespace) -> None:
        super().__init__(existing=None)
        self._dup_open = dup

    async def find_open_lead_same_normalized_phone(self, **kwargs: object) -> SimpleNamespace:
        return self._dup_open


class _HighPhoneVelocityRepo(_StubLeadRepo):
    async def count_leads_same_phone_recent(self, **kwargs: object) -> int:
        return 4


@pytest.mark.asyncio
async def test_try_create_skips_low_quality_signals() -> None:
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid)
    conv = _conversation(owner_id=oid, bot_id=bot.id, current_state="closing")
    owner = _owner(oid)
    repo = _StubLeadRepo()
    svc = LeadCreationService(repo)
    res = await svc.try_create_lead_from_conversation(
        bot=bot,
        owner=owner,
        conversation=conv,
        collected_data_json={"primary_need": "x", "phone": "+15550001234"},
        lead_score=10,
        lead_temperature="cold",
        summary="short",
        source_channel="web",
    )
    assert res.created is False
    assert res.lead is None
    assert res.reason == "skipped_low_quality_signals"
    assert repo.create_calls == []


@pytest.mark.asyncio
async def test_try_create_skips_when_open_pipeline_duplicate_phone() -> None:
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid)
    conv = _conversation(owner_id=oid, bot_id=bot.id, current_state="closing")
    owner = _owner(oid)
    dup = SimpleNamespace(id=uuid.uuid4())
    repo = _DupOpenPhoneRepo(dup)
    svc = LeadCreationService(repo)
    res = await svc.try_create_lead_from_conversation(
        bot=bot,
        owner=owner,
        conversation=conv,
        collected_data_json={"primary_need": "x", "phone": "+1 (555) 000-1234"},
        lead_score=50,
        lead_temperature="warm",
        summary="Enough text here.",
        source_channel="web",
    )
    assert res.created is False
    assert res.lead is dup
    assert res.reason == "skipped_duplicate_phone_open_pipeline"
    assert repo.create_calls == []


@pytest.mark.asyncio
async def test_try_create_logs_when_same_phone_velocity_high() -> None:
    oid, _, _ = _ids()
    bot = _bot(owner_id=oid)
    conv = _conversation(owner_id=oid, bot_id=bot.id, current_state="closing")
    owner = _owner(oid)
    repo = _HighPhoneVelocityRepo()
    svc = LeadCreationService(repo)
    with patch("app.services.lead_creation_service._LOG.warning") as warn:
        res = await svc.try_create_lead_from_conversation(
            bot=bot,
            owner=owner,
            conversation=conv,
            collected_data_json={"primary_need": "x", "phone": "+15550001234"},
            lead_score=40,
            lead_temperature="warm",
            summary="Good summary length.",
            source_channel="web",
        )
    assert res.created is True
    assert len(repo.create_calls) == 1
    vel_calls = [
        c
        for c in warn.call_args_list
        if c.args and c.args[0] == "lead_creation_suspicious_phone_velocity"
    ]
    assert len(vel_calls) == 1
    assert "phone_last4" in vel_calls[0].kwargs
    assert vel_calls[0].kwargs.get("phone_last4") == "1234"
