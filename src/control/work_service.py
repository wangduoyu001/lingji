from __future__ import annotations

from typing import Any

from src.work.projector import WorkProjector


class WorkControlService:
    """Control-layer adapter for work facts consumed by local API and desktop."""

    def __init__(self, state_db: Any):
        self.projector = WorkProjector(state_db)

    def current_work(self) -> dict[str, Any]:
        return self.projector.current_work()

    def pending_actions(self) -> dict[str, Any]:
        return self.projector.pending_actions()

    def work_timeline(self, work_id: str) -> dict[str, Any]:
        return self.projector.timeline(work_id)
