from pathlib import Path

from src.control.work_service import WorkControlService
from src.storage.state_db import StateDatabase
from src.work.models import WorkItem


def test_work_control_service_reads_projected_facts(tmp_path: Path):
    state = StateDatabase(tmp_path / "state.db")
    service = WorkControlService(state)

    service.store.create_work(WorkItem(title="control test"))

    result = service.current_work()

    assert set(result) == {"work", "events", "outcome", "next_action", "pending_actions", "failure"}
    assert result["work"]["title"] == "control test"
