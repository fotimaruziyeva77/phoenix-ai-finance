from __future__ import annotations

from app.schemas.bots import ALLOWED_GOAL_TYPES
from fastapi.testclient import TestClient


def test_niche_catalog_returns_versioned_envelope(client: TestClient) -> None:
    r = client.get("/api/v1/catalog/niches")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["schema_version"] == 1
    assert isinstance(body["niches"], list)
    assert len(body["niches"]) == 4
    ids = [n["id"] for n in body["niches"]]
    assert ids == ["education", "healthcare", "dev_agency", "services"]


def test_niche_catalog_item_shape(client: TestClient) -> None:
    r = client.get("/api/v1/catalog/niches")
    edu = next(n for n in r.json()["niches"] if n["id"] == "education")
    assert edu["display_name"] == "Education"
    assert "learner" in edu["description"].lower() or "enrollment" in edu["description"].lower()
    assert edu["wizard_hint"]
    assert edu["icon_key"] == "graduation-cap"
    assert isinstance(edu["supported_goals"], list)
    assert isinstance(edu["onboarding_hints"], list)
    assert edu["visible"] is True


def test_niche_catalog_supported_goals_subset_of_bot_goals(client: TestClient) -> None:
    allowed = set(ALLOWED_GOAL_TYPES)
    r = client.get("/api/v1/catalog/niches")
    for n in r.json()["niches"]:
        for g in n["supported_goals"]:
            assert g in allowed, f"unknown goal {g!r} for niche {n['id']}"
