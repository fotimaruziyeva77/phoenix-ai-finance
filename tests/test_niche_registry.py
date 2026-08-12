from __future__ import annotations

from collections.abc import Mapping

from app.lib.niche_registry import (
    NicheDefinition,
    get_niche_by_id,
    list_supported_niches,
    validate_niche_id,
)


def test_all_supported_niches_present() -> None:
    niches = list_supported_niches()
    assert len(niches) == 4
    assert [n.id for n in niches] == [
        "education",
        "healthcare",
        "dev_agency",
        "services",
    ]


def test_get_niche_by_id_works_for_known_niches() -> None:
    healthcare = get_niche_by_id("healthcare")
    assert healthcare is not None
    assert healthcare.id == "healthcare"
    assert healthcare.label == "Healthcare / Clinic"
    assert healthcare.icon_key == "stethoscope"
    assert len(healthcare.supported_goals) == 4
    assert len(healthcare.default_lead_fields) >= 1


def test_invalid_niche_id_rejected() -> None:
    assert get_niche_by_id("unknown_niche") is None
    assert validate_niche_id("unknown_niche") is False
    assert validate_niche_id(" education ") is True


def test_registry_structure_future_ready_and_stable() -> None:
    niche = get_niche_by_id("dev_agency")
    assert niche is not None
    assert isinstance(niche, NicheDefinition)

    # Stable shape for future qualification/scoring/crm/prompt expansion.
    assert hasattr(niche, "qualification_questions")
    assert hasattr(niche, "scoring_rules")
    assert hasattr(niche, "crm_mapping")
    assert hasattr(niche, "prompt_templates")

    assert isinstance(niche.qualification_questions, tuple)
    assert isinstance(niche.scoring_rules, tuple)
    assert isinstance(niche.crm_mapping, Mapping)
    assert isinstance(niche.prompt_templates, Mapping)
