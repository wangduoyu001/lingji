"""后台管线故障可见性：连续失败计数、限频事件上报、恢复上报、status 透出。

治"静默失败"（2026-09-23 真机：提炼循环连续秒败数小时无人知晓）。
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.automatic_memory.pipeline_health import PipelineHealth


class RecordingStateDB:
    def __init__(self):
        self.events: list[tuple] = []

    def append_event(self, event_type, entity_type, entity_id=None, payload=None, now=None):
        self.events.append((event_type, entity_type, entity_id, payload))
        return len(self.events)


class ExplodingStateDB:
    def append_event(self, *args, **kwargs):
        raise RuntimeError("state db unavailable")


def _clock():
    return _clock.value


_clock.value = 1000.0


def test_first_failure_reports_then_rate_limits():
    db = RecordingStateDB()
    health = PipelineHealth("distill", db, event_interval_seconds=300, clock=_clock)
    health.record_failure("boom-1")
    health.record_failure("boom-2")
    health.record_failure("boom-3")
    reported = [e for e in db.events if e[0].endswith("_failed")]
    assert len(reported) == 1, "持续失败时限频：首败立即报，之后 300s 内不再刷屏"
    assert health.consecutive_failures if False else health.snapshot()["consecutive_failures"] == 3
    assert health.snapshot()["degraded"] is True


def test_failure_reports_again_after_interval():
    db = RecordingStateDB()
    health = PipelineHealth("promotion", db, event_interval_seconds=300, clock=_clock)
    health.record_failure("first")
    _clock.value += 301
    health.record_failure("second")
    reported = [e for e in db.events if e[0].endswith("_failed")]
    assert len(reported) == 2, "间隔过后必须再报，否则故障被永久静默"
    assert reported[1][3]["error"] == "second"


def test_recovery_after_degraded_emits_recovered_event():
    db = RecordingStateDB()
    health = PipelineHealth("vector_backfill", db, event_interval_seconds=300, clock=_clock)
    for i in range(3):
        health.record_failure(f"err-{i}")
    health.record_success()
    outcomes = [e[0] for e in db.events]
    assert outcomes[-1] == "pipeline_vector_backfill_recovered"
    assert health.snapshot()["consecutive_failures"] == 0
    assert health.snapshot()["degraded"] is False


def test_success_without_failures_is_silent():
    db = RecordingStateDB()
    health = PipelineHealth("distill", db, event_interval_seconds=300, clock=_clock)
    health.record_success()
    assert db.events == []


def test_missing_or_broken_state_db_never_propagates():
    health = PipelineHealth("distill", None, event_interval_seconds=300, clock=_clock)
    health.record_failure("x")
    health.record_success()
    health = PipelineHealth("distill", ExplodingStateDB(), event_interval_seconds=300, clock=_clock)
    health.record_failure("x")
    health.record_success()
    assert health.snapshot()["total_failures"] == 1


def test_snapshot_shape():
    health = PipelineHealth("distill", None, event_interval_seconds=300, clock=_clock)
    snap = health.snapshot()
    assert set(snap) == {
        "name", "consecutive_failures", "total_failures", "degraded",
        "last_error", "last_success_at", "last_failure_at",
    }
