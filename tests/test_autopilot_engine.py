from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.autopilot.engine import AutopilotEngine


class FakeStateDb:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, str, dict]] = []

    def append_event(self, event_type, entity_type, entity_id=None, payload=None):
        self.events.append((event_type, entity_type, entity_id, dict(payload or {})))
        return len(self.events)


class FakeQueue:
    def __init__(self, *, released: int = 0, failed: int = 0) -> None:
        self.released = released
        self.failed = failed
        self.release_calls: list[int] = []
        self.retry_calls = 0

    def release_stale(self, stale_after_seconds: int) -> int:
        self.release_calls.append(stale_after_seconds)
        value, self.released = self.released, 0
        return value

    def stats(self) -> dict[str, int]:
        return {
            "queued": 0, "retrying": 0, "running": 0, "completed": 0,
            "failed": self.failed, "cancelled": 0, "pending": 0,
        }

    def retry(self, *_args, **_kwargs):
        self.retry_calls += 1
        raise AssertionError("Autopilot must not retry exhausted or cancelled jobs automatically")


class FakeMemory:
    def __init__(self, *, rebuild_required: bool = False, vector_state: str = "healthy") -> None:
        self.rebuild_required = rebuild_required
        self.vector_state = vector_state

    def snapshot(self) -> dict:
        return {
            "state": "healthy",
            "vector": {"state": self.vector_state, "rebuild_required": self.rebuild_required},
            "embedding": {"state": "healthy"},
            "warnings": [],
        }


class DynamicHealth:
    def __init__(self, settings, *, read_only=False):
        self.settings = settings
        self.read_only = read_only

    def run(self) -> dict:
        checks = [
            {"name": "data_root_policy", "status": "ok", "message": "ok"},
            {"name": "state_db", "status": "ok", "message": "ok"},
            {"name": "memory_db", "status": "ok", "message": "ok"},
            {"name": "ollama", "status": "warning", "message": "optional"},
        ]
        for name, path, missing_status in [
            ("storage", self.settings.storage_path, "error"),
            ("logs", self.settings.log_path, "error"),
            ("backup", self.settings.backup_path, "warning"),
            ("vault", self.settings.vault_path, "warning"),
        ]:
            checks.append({
                "name": name,
                "status": "ok" if Path(path).is_dir() else missing_status,
                "message": name,
            })
        errors = [item for item in checks if item["status"] == "error"]
        warnings = [item for item in checks if item["status"] == "warning"]
        return {
            "status": "error" if errors else "degraded" if warnings else "healthy",
            "checks": checks,
            "error_count": len(errors),
            "warning_count": len(warnings),
        }


class OwnerHealth(DynamicHealth):
    def run(self) -> dict:
        report = super().run()
        for item in report["checks"]:
            if item["name"] == "state_db":
                item["status"] = "error"
        report["error_count"] = sum(item["status"] == "error" for item in report["checks"])
        report["warning_count"] = sum(item["status"] == "warning" for item in report["checks"])
        report["status"] = "error"
        return report


class AutopilotEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.settings = SimpleNamespace(
            watchdog_enabled=True,
            scheduler_poll_seconds=60.0,
            extraction_stale_after_seconds=1800,
            vault_auto_init=True,
            storage_path=root / "storage",
            log_path=root / "logs",
            backup_path=root / "backups",
            vault_path=root / "vault",
        )

    def build(self, *, queue=None, memory=None, health_factory=DynamicHealth, interval_seconds=None, auth_status_provider=None):
        state_db = FakeStateDb()
        engine = AutopilotEngine(
            self.settings,
            state_db=state_db,
            queue=queue or FakeQueue(),
            memory_statistics=memory or FakeMemory(),
            auth_status_provider=auth_status_provider,
            health_factory=health_factory,
            interval_seconds=interval_seconds,
        )
        return engine, state_db

    def test_auth_blockers_remain_background_work(self):
        engine, _ = self.build(auth_status_provider=lambda: {"providers": [
            {"provider": "github", "state": "permission_insufficient"},
            {"provider": "codex", "state": "expired"},
        ]})

        status = engine.run_once()

        codes = {item["code"] for item in status["background_issues"]}
        self.assertIn("auth_permission_insufficient", codes)
        self.assertIn("auth_reauthentication_required", codes)
        self.assertEqual(status["owner_action_count"], 0)

    def test_safe_repairs_create_only_lingji_directories_release_stale_and_verify(self):
        queue = FakeQueue(released=2, failed=1)
        engine, state_db = self.build(queue=queue)
        status = engine.run_once()
        self.assertEqual(status["state"], "degraded")
        self.assertEqual(status["automatic_repair_count"], 5)
        self.assertEqual(status["owner_action_count"], 0)
        self.assertEqual(status["background_issue_count"], 2)
        self.assertTrue(self.settings.storage_path.is_dir())
        self.assertTrue(self.settings.log_path.is_dir())
        self.assertTrue(self.settings.backup_path.is_dir())
        self.assertTrue(self.settings.vault_path.is_dir())
        self.assertEqual(queue.release_calls, [1800])
        self.assertEqual(queue.retry_calls, 0)
        self.assertTrue(all(item["verified"] for item in status["recent_actions"]))
        self.assertEqual([event[0] for event in state_db.events].count("autopilot_repair"), 5)

    def test_integrity_and_vector_rebuild_block_all_automatic_writes(self):
        queue = FakeQueue(released=2)
        engine, _ = self.build(
            queue=queue,
            memory=FakeMemory(rebuild_required=True),
            health_factory=OwnerHealth,
        )
        status = engine.run_once()
        codes = {item["code"] for item in status["owner_actions"]}
        self.assertEqual(status["state"], "owner_attention")
        self.assertIn("health_state_db", codes)
        self.assertIn("vector_rebuild_required", codes)
        self.assertEqual(queue.release_calls, [])
        self.assertEqual(queue.retry_calls, 0)
        self.assertEqual(status["automatic_repair_count"], 0)
        self.assertFalse(self.settings.storage_path.exists())
        self.assertFalse(any("qdrant" in item["code"].lower() for item in status["recent_actions"]))

    def test_disabled_watchdog_never_starts_or_repairs(self):
        self.settings.watchdog_enabled = False
        queue = FakeQueue(released=3)
        engine, _ = self.build(queue=queue, interval_seconds=0.05)
        engine.start()
        time.sleep(0.08)
        status = engine.run_once()
        self.assertEqual(status["state"], "disabled")
        self.assertFalse(status["running"])
        self.assertEqual(queue.release_calls, [])
        self.assertEqual(status["automatic_repair_count"], 0)

    def test_background_thread_runs_and_stops_cleanly(self):
        engine, _ = self.build(interval_seconds=0.05)
        engine.start()
        deadline = time.time() + 1.0
        while engine.status()["cycle_count"] < 1 and time.time() < deadline:
            time.sleep(0.01)
        engine.stop(timeout=1.0)
        self.assertGreaterEqual(engine.status()["cycle_count"], 1)
        self.assertFalse(engine.status()["running"])


if __name__ == "__main__":
    unittest.main()
