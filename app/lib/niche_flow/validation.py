"""
Structural validation for :class:`~app.lib.niche_flow.schema.NicheConversationFlowDefinition`.

Used by tests and orchestration to fail fast on misconfigured niche modules (no I/O).
"""

from __future__ import annotations

import re

from app.lib.niche_flow.schema import CollectedFieldSpec, NicheConversationFlowDefinition

_FIELD_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*\Z")


def _non_empty_str_tuple(name: str, items: tuple[str, ...]) -> list[str]:
    errs: list[str] = []
    if len(items) < 1:
        errs.append(f"{name} must contain at least one entry")
        return errs
    for i, s in enumerate(items):
        if not isinstance(s, str) or not s.strip():
            errs.append(f"{name}[{i}] must be a non-empty string")
    return errs


def validate_niche_conversation_flow(
    flow: NicheConversationFlowDefinition,
    *,
    allow_generic: bool = True,
) -> list[str]:
    """
    Return a list of human-readable validation errors; empty means the definition is usable.

    ``allow_generic`` controls whether ``niche_id == \"generic\"`` is accepted as a valid id.
    """
    errs: list[str] = []

    nid = flow.niche_id
    if not isinstance(nid, str) or not nid.strip():
        errs.append("niche_id must be a non-empty string")
    elif not _FIELD_KEY_RE.match(nid.strip()):
        errs.append(f"niche_id must match snake_case pattern, got {nid!r}")
    elif nid == "generic" and not allow_generic:
        errs.append("generic niche_id is not allowed in this context")

    errs.extend(_non_empty_str_tuple("qualification_goals", flow.qualification_goals))
    errs.extend(_non_empty_str_tuple("qualification_question_examples", flow.qualification_question_examples))
    errs.extend(_non_empty_str_tuple("clarification_question_examples", flow.clarification_question_examples))
    errs.extend(_non_empty_str_tuple("offer_framing", flow.offer_framing))
    errs.extend(_non_empty_str_tuple("objection_handling_hints", flow.objection_handling_hints))
    errs.extend(_non_empty_str_tuple("closing_objectives", flow.closing_objectives))

    fields = flow.core_fields
    if len(fields) < 1:
        errs.append("core_fields must contain at least one CollectedFieldSpec")
    else:
        keys: list[str] = []
        for i, spec in enumerate(fields):
            if not isinstance(spec, CollectedFieldSpec):
                errs.append(f"core_fields[{i}] must be CollectedFieldSpec")
                continue
            k = spec.key
            if not isinstance(k, str) or not _FIELD_KEY_RE.match(k):
                errs.append(f"core_fields[{i}].key must match snake_case pattern, got {k!r}")
            else:
                keys.append(k)
            desc = spec.description
            if not isinstance(desc, str) or not desc.strip():
                errs.append(f"core_fields[{i}].description must be non-empty")

        if keys and len(keys) != len(set(keys)):
            errs.append("duplicate core_fields.key values present")

        if fields and all(isinstance(f, CollectedFieldSpec) for f in fields):
            if not any(f.required_for_qualification for f in fields):
                errs.append("at least one core field must have required_for_qualification=True")

    return errs


def assert_valid_niche_conversation_flow(
    flow: NicheConversationFlowDefinition,
    *,
    allow_generic: bool = True,
) -> None:
    """Raise ``ValueError`` with joined messages if validation fails."""
    errors = validate_niche_conversation_flow(flow, allow_generic=allow_generic)
    if errors:
        raise ValueError("; ".join(errors))
