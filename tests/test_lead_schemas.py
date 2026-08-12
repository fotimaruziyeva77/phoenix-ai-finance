"""Pydantic lead DTOs (no database)."""

from __future__ import annotations

import uuid

import pytest
from app.schemas.lead import LeadCreateInternal, LeadListResponse, LeadPipelinePatch, LeadUpdateStatus
from pydantic import ValidationError


def test_lead_create_internal_forbids_extra_keys() -> None:
    with pytest.raises(ValidationError):
        LeadCreateInternal.model_validate(
            {
                "bot_id": uuid.uuid4(),
                "owner_id": uuid.uuid4(),
                "niche_id": "education",
                "unexpected": 1,
            }
        )


def test_lead_update_status_accepts_pipeline_values() -> None:
    u = LeadUpdateStatus(status="qualified", lead_temperature="warm")
    assert u.status == "qualified"
    assert u.lead_temperature == "warm"


def test_lead_list_response_total_non_negative() -> None:
    LeadListResponse(items=[], total=0)


def test_lead_pipeline_patch_forbids_extra_keys() -> None:
    with pytest.raises(ValidationError):
        LeadPipelinePatch.model_validate({"status": "new", "extra": 1})
