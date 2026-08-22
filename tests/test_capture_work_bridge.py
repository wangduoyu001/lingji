from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.storage.state_db import StateDatabase
from src.work.capture_bridge import CaptureWorkBridge
from src.work.store import WorkStore


class CaptureWorkBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "state.db"
        self.store = WorkStore(StateDatabase(self.path))
        self.bridge = CaptureWorkBridge(self.store)

    def test_capture_creates_traceable_accepted_work(self) -> None:
        work = self.bridge.create_from_capture(
            "capture-1",
            "记住测试信息",
            metadata={"kind": "text"},
        )
        self.assertEqual(work.status, "accepted")
        self.assertEqual(work.source_id, "capture-1")
        stored = self.store.get_work(work.work_id)
        self.assertIsNotNone(stored)
        events = self.store.list_events(work.work_id)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "capture.accepted")
        self.assertEqual(events[0].detail["capture_id"], "capture-1")

    def test_capture_start_and_complete_updates_same_work(self) -> None:
        work = self.bridge.create_from_capture("capture-2", "完整流程")
        self.bridge.start_extraction(work.work_id, detail={"adapter": "text"})
        running = self.store.get_work(work.work_id)
        self.assertIsNotNone(running)
        assert running is not None
        self.assertEqual(running.status, "running")

        outcome = self.bridge.complete_extraction(
            work.work_id,
            "提取完成",
            evidence={"memory_id": "memory-2"},
        )
        self.assertEqual(outcome.status, "success")
        finished = self.store.get_work(work.work_id)
        self.assertIsNotNone(finished)
        assert finished is not None
        self.assertEqual(finished.status, "completed")
        self.assertEqual(
            [event.event_type for event in self.store.list_events(work.work_id)],
            ["capture.accepted", "extraction.started", "extraction.completed"],
        )
        saved = self.store.get_outcome(work.work_id)
        self.assertIsNotNone(saved)
        assert saved is not None
        self.assertEqual(saved.evidence["memory_id"], "memory-2")

    def test_failed_extraction_is_persisted_not_dropped(self) -> None:
        work = self.bridge.create_from_capture("capture-3", "失败流程")
        self.bridge.start_extraction(work.work_id)
        outcome = self.bridge.fail_extraction(
            work.work_id,
            "解析失败",
            evidence={"error_code": "EXTRACT_FAILED"},
        )
        self.assertEqual(outcome.status, "failure")
        failed = self.store.get_work(work.work_id)
        self.assertIsNotNone(failed)
        assert failed is not None
        self.assertEqual(failed.status, "failed")
        self.assertEqual(self.store.list_events(work.work_id)[-1].event_type, "extraction.failed")
        persisted = self.store.get_outcome(work.work_id)
        self.assertIsNotNone(persisted)
        assert persisted is not None
        self.assertEqual(persisted.summary, "解析失败")
        self.assertEqual(persisted.evidence["error_code"], "EXTRACT_FAILED")

    def test_work_id_and_timeline_survive_runtime_reopen(self) -> None:
        work = self.bridge.create_from_capture("capture-4", "重启测试")
        self.bridge.start_extraction(work.work_id)
        reopened = WorkStore(StateDatabase(self.path))
        restored = reopened.get_work(work.work_id)
        self.assertIsNotNone(restored)
        assert restored is not None
        self.assertEqual(restored.work_id, work.work_id)
        self.assertEqual(
            [event.event_type for event in reopened.list_events(work.work_id)],
            ["capture.accepted", "extraction.started"],
        )


if __name__ == "__main__":
    unittest.main()
