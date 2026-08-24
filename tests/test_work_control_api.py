from pathlib import Path

from src.control.work_service import WorkControlService
from src.storage.state_db import StateDatabase
from src.work.models import ExecutionEvent, WorkItem


def test_work_api_contract_source_is_work_control_service(tmp_path: Path):
    """Keep the API boundary backed by Work Fact projection, not UI state."""
    service = WorkControlService(StateDatabase(tmp_path / "state.db"))
    item = WorkItem(title="api contract")
    service.store.create_work(item)
    service.store.append_event(
        ExecutionEvent(work_id=item.work_id, event_type="created")
    )

    current = service.current_work()
    timeline = service.work_timeline(item.work_id)

    assert current["items"][0]["work_id"] == item.work_id
    assert timeline["events"][0]["event_type"] == "created"
