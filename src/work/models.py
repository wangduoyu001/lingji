from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class WorkItem:
    """A real piece of work LingJi has accepted responsibility for."""

    title: str
    source_id: str | None = None
    status: str = "pending"
    owner_approved: bool = False
    work_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


@dataclass
class ExecutionEvent:
    """An immutable fact describing one execution step."""

    work_id: str
    event_type: str
    detail: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


@dataclass
class Outcome:
    """Human-readable result of a work item."""

    work_id: str
    status: str
    summary: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class NextAction:
    work_id: str
    description: str
    actor: str = "system"


@dataclass
class PendingAction:
    """Only exists when owner decision is genuinely required."""

    work_id: str
    description: str
    resolved: bool = False
