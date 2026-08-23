from pathlib import Path

from src.storage.state_db import StateDatabase
from src.work.models import ExecutionEvent, WorkItem
from src.work.store import WorkStore


def test_work_store_persists_and_reads_work_facts(tmp_path: Path):
    store = WorkStore(StateDatabase(tmp_path / "state.db"))
    item = WorkItem(title="capture test", status="accepted")

    store.create_work(item)
    store.append_event(
        ExecutionEvent(work_id=item.work_id, event_type="capture.accepted")
    )

    works = store.list_work()
    events = store.list_events(item.work_id)

    assert works[0].work_id == item.work_id
    assert events[0].event_type == "capture.accepted"
