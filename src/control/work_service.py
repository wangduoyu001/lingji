"""Owner-visible work fact service adapter.

Keeps Desktop-facing control reads behind one service boundary.
The service projects the work fact chain:
Source -> WorkItem -> ExecutionEvent -> Outcome -> NextAction.
"""

from dataclasses import asdict
from typing import Any


class WorkService:
    """Read-only projection adapter for owner-visible work state."""

    def __init__(self, projector: Any | None = None):
        self.projector = projector

    def current_work(self) -> list[dict[str, Any]]:
        if self.projector and hasattr(self.projector, "current_work"):
            return list(self.projector.current_work())
        return []

    def pending_actions(self) -> list[dict[str, Any]]:
        if self.projector and hasattr(self.projector, "pending_actions"):
            return list(self.projector.pending_actions())
        return []

    def timeline(self, work_id: str) -> list[dict[str, Any]]:
        if self.projector and hasattr(self.projector, "timeline"):
            return list(self.projector.timeline(work_id))
        return []
