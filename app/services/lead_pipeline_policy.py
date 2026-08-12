"""
MVP CRM **status transition policy** (no Kanban engine, no workflow DSL).

Design
======

* **Open pipeline** — ``new``, ``contacted``, ``qualified``, ``proposal``: the owner may move
  freely in any direction. Corrections (e.g. ``qualified`` → ``contacted``) are normal in a small
  team CRM without a heavy approval graph.

* **Terminal outcomes** — ``won`` and ``lost`` are **absorbing**. Once set, the status must not
  change to another stage. This avoids silent “un-closing” deals and keeps reporting stable.
  Operators who must reopen a deal can be handled later with an explicit ``reopen`` action or
  admin tooling.

* **No-op status** — Setting status to the current value is always allowed (idempotent PATCH),
  including on terminal rows, so clients can resend forms safely.

* **Non-status edits on terminal leads** — Updating ``lead_temperature`` or internal ``notes`` on
  ``won``/``lost`` rows remains allowed; only **changing** ``status`` away from a terminal value is
  blocked.

Future (not implemented here)
=============================

* **Assignment** — policy can accept ``assignee_id`` and enforce “only assignee or owner may move
  stage” without changing the above graph.

* **Reminders** — ``next_follow_up_at`` validation (e.g. must be set when moving to
  ``contacted``) can layer on top of :func:`validate_lead_status_change`.

* **External CRM sync** — transitions that succeed here become outbound events; terminal states map
  to closed-won / closed-lost on the remote side.
"""

from __future__ import annotations

from typing import Final

# Order is documentation-only (not enforced as a linear funnel).
OPEN_PIPELINE_STATUSES: Final[tuple[str, ...]] = (
    "new",
    "contacted",
    "qualified",
    "proposal",
)

TERMINAL_STATUSES: Final[frozenset[str]] = frozenset({"won", "lost"})

ALL_STATUSES: Final[tuple[str, ...]] = OPEN_PIPELINE_STATUSES + ("won", "lost")


class LeadStatusTransitionError(ValueError):
    """Raised when a lead status change violates pipeline rules."""

    def __init__(self, message: str, *, from_status: str, to_status: str) -> None:
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(message)


def validate_lead_status_change(from_status: str, to_status: str) -> None:
    """
    Ensure ``from_status`` → ``to_status`` is allowed.

    Raises:
        LeadStatusTransitionError: When leaving a terminal status for a different stage.
    """
    if from_status == to_status:
        return
    if from_status in TERMINAL_STATUSES:
        raise LeadStatusTransitionError(
            "Closed leads cannot move to another pipeline stage.",
            from_status=from_status,
            to_status=to_status,
        )


__all__ = [
    "ALL_STATUSES",
    "OPEN_PIPELINE_STATUSES",
    "TERMINAL_STATUSES",
    "LeadStatusTransitionError",
    "validate_lead_status_change",
]
