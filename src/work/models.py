from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

WorkStatus = Literal["pending", "accepted", "running", "completed", "failed", "skipped"]
OutcomeStatus = Literal["success", "failure", "skipped"]
WorkActor = Literal["system", "owner", "external", "none"]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class WorkItem:
    """A real piece of work LingJi has accepted responsibility for."""

    title: str
    source_id: str | None = None
    status: WorkStatus = "pending"
    owner_approved: bool = False
    work_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)


@dataclass
class ExecutionEvent:
    """An immutable fact describing one execution step."""

    work_id: str
    event_type: str
    detail: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=_now)


@dataclass
class Outcome:
    """Human-readable final result of a work item."""

    work_id: str
    status: OutcomeStatus
    summary: str
    evidence: dict[str, Any] = field(default_factory=dict)
    completed_at: str = field(default_factory=_now)


@dataclass
class NextAction:
    """The next actor and action after the latest known work state."""

    work_id: str
    description: str
    actor: WorkActor = "system"


@dataclass
class PendingAction:
    """Only exists when an owner decision is genuinely required."""

    work_id: str
    description: str
    reason: str | None = None
    resolved: bool = False
    action_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=_now)
    resolved_at: str | None = None
