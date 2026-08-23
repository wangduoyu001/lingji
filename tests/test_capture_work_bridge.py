from pathlib import Path

from src.storage.state_db import StateDatabase
from src.work.capture_bridge import CaptureWorkBridge
from src.work.store import WorkStore


def test_capture_creates_traceable_work(tmp_path: Path):
    bridge = CaptureWorkBridge(WorkStore(StateDatabase(tmp_path / "state.db")))

    work = bridge.create_from_capture(
        "capture-1",
        "remember this",
    )

    assert work.source_id == "capture-1"
    assert bridge.store.list_work()[0].work_id == work.work_id
    assert bridge.store.list_events(work.work_id)[0].event_type == "capture.accepted"
