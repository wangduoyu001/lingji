from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.work.projector import WorkProjector


router = APIRouter(prefix="/v1/work", tags=["work"])


def register_work_routes(app: Any, *, projector: WorkProjector | None = None) -> None:
    reader = projector or WorkProjector()

    @app.get("/current")
    def current_work() -> dict[str, Any]:
        return reader.current_work()

    @app.get("/pending")
    def pending_actions() -> dict[str, Any]:
        return reader.pending_actions()

    @app.get("/timeline/{work_id}")
    def work_timeline(work_id: str) -> dict[str, Any]:
        return reader.timeline(work_id)
