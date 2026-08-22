from __future__ import annotations

from typing import Any

from src.work.projector import WorkProjector
from src.work.store import WorkStore


class WorkControlService:
    """Control-layer adapter for canonical work facts consumed by 8766/Desktop."""

    def __init__(self, state_db: Any, *, store: WorkStore | None = None):
        self.store = store or WorkStore(state_db)
        self.projector = WorkProjector(self.store)

    def current_work(self) -> dict[str, Any]:
        return self.projector.current_work()

    def recent_work(self, *, limit: int = 20) -> dict[str, Any]:
        return self.projector.recent_work(limit=limit)

    def work_detail(self, work_id: str) -> dict[str, Any]:
        return self.projector.work_detail(work_id)

    def pending_actions(self, *, limit: int = 20) -> dict[str, Any]:
        return self.projector.pending_actions(limit=limit)

    def work_timeline(self, work_id: str, *, limit: int = 100) -> dict[str, Any]:
        return self.projector.timeline(work_id, limit=limit)
