"""Owner-visible work fact read endpoints.

Routes are intentionally read-only. Desktop should render the same facts
returned here instead of maintaining a second UI state model.
"""

from fastapi import APIRouter

from .work_service import WorkService


router = APIRouter(prefix="/v1/work", tags=["work"])
_service = WorkService()


@router.get("/current")
def current_work():
    return {"items": _service.current_work()}


@router.get("/pending-actions")
def pending_actions():
    return {"items": _service.pending_actions()}


@router.get("/timeline/{work_id}")
def work_timeline(work_id: str):
    return {"work_id": work_id, "events": _service.timeline(work_id)}
