"""同源快照节流：滚动变化的大库在最小重拍间隔内跳过核对（空间防膨胀）。

跳过语义：本次不扫描、不动哨兵，内容最多晚一个节流窗口入库；
manual/integrity 触发不受限。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.automatic_memory import SourceRegistry
from src.automatic_memory.scheduler import AutomaticMemoryScheduler
from src.storage import StateDatabase


def _scheduler(tmp_path: Path, throttle_seconds: float, calls: list):
    state_db = StateDatabase(tmp_path / "lingji_state.db")
    registry = SourceRegistry(state_db)
    scheduler = AutomaticMemoryScheduler(
        state_db,
        registry,
        scan_runner=lambda scan_id, source_id=None, reason="test": calls.append(scan_id) or {},
        snapshot_throttle_seconds=throttle_seconds,
        event_watcher_enabled=False,
    )
    return scheduler, state_db


def _seed_completed_scan(state_db: StateDatabase, registry: SourceRegistry, root: Path, age_minutes: float):
    from src.automatic_memory import AuthorizationScope
    from datetime import datetime

    record = registry.register(
        AuthorizationScope(
            grant_id="grant-throttle",
            source_kinds=("generic_ai_history",),
            roots=(str(root),),
            granted_at=datetime.now(timezone.utc),
            expires_at=None,
            owner_confirmed=True,
        ),
        "generic_ai_history",
        str(root),
    )
    scan = registry.start_scan(record.source_id)
    state_db.update_automatic_memory_scan(
        scan.scan_id,
        status="completed",
        updated_at=(datetime.now(timezone.utc) - timedelta(minutes=age_minutes)).isoformat(),
    )
    return record.source_id


def test_recent_capture_defers_reconciliation(tmp_path: Path):
    calls: list = []
    scheduler, state_db = _scheduler(tmp_path, 1800.0, calls)
    root = tmp_path / "src-root"
    root.mkdir()
    source_id = _seed_completed_scan(state_db, scheduler.registry, root, age_minutes=10)
    report = scheduler.reconcile(source_id, reason="reconciliation")
    assert report.complete is True
    assert report.scan_id is None, "节流期内不得 admitting 新扫描"
    assert "throttled" in (report.next_action or "")
    assert calls == [], "节流期内不得触发 scan_runner"


def test_expired_capture_allows_reconciliation(tmp_path: Path):
    calls: list = []
    scheduler, state_db = _scheduler(tmp_path, 1800.0, calls)
    root = tmp_path / "src-root2"
    root.mkdir()
    source_id = _seed_completed_scan(state_db, scheduler.registry, root, age_minutes=60)
    scheduler.reconcile(source_id, reason="reconciliation")
    assert len(calls) >= 1, "超过节流窗口必须放行核对"


def test_manual_scan_bypasses_throttle(tmp_path: Path):
    calls: list = []
    scheduler, state_db = _scheduler(tmp_path, 1800.0, calls)
    root = tmp_path / "src-root3"
    root.mkdir()
    source_id = _seed_completed_scan(state_db, scheduler.registry, root, age_minutes=1)
    scheduler.reconcile(source_id, reason="manual")
    assert len(calls) >= 1, "manual 触发不受节流限制"


def test_zero_throttle_disables_deferral(tmp_path: Path):
    calls: list = []
    scheduler, state_db = _scheduler(tmp_path, 0.0, calls)
    root = tmp_path / "src-root4"
    root.mkdir()
    source_id = _seed_completed_scan(state_db, scheduler.registry, root, age_minutes=0)
    scheduler.reconcile(source_id, reason="reconciliation")
    assert len(calls) >= 1, "节流=0 表示停用"
