"""Regression tests for the adaptive snapshot throttle (主人 2026-09-27 拍板).

固定 30 分钟窗口下，177MB 滚动大库的整库重拷占空比随体积膨胀（实测稳态
~26% CPU）。节流窗口改为 max(基准, 最近一次真采集最大快照字节 ÷ 实测吞吐 ÷
5% 目标占空比)：大库自动拉长间隔，小源保持基准响应。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.automatic_memory.models import AuthorizationScope
from src.automatic_memory.scheduler import AutomaticMemoryScheduler
from src.automatic_memory.source_registry import SourceRegistry
from src.storage.state_db import StateDatabase

MIN = 60
MB = 1024 * 1024


def _completed_scan_with_items(
    state: StateDatabase,
    registry: SourceRegistry,
    source_id: str,
    *,
    age_minutes: float,
    items: list[tuple[str, str, int]],
):
    scan = registry.start_scan(source_id)
    lease_id = f"lease-{scan.scan_id[:8]}"
    assert state.acquire_automatic_memory_scan_lease(scan.scan_id, lease_id, ttl_seconds=60)
    for relative_path, status, size in items:
        state.upsert_automatic_memory_scan_item_owned(
            scan.scan_id,
            lease_id,
            source_id=source_id,
            relative_path=relative_path,
            sentinel=f"{size}:0:0:0",
            status=status,
        )
    completed_at = datetime.now(timezone.utc) - timedelta(minutes=age_minutes)
    state.update_automatic_memory_scan_owned(
        scan.scan_id,
        lease_id,
        status="completed",
        updated_at=completed_at.isoformat(),
    )
    return scan


def _scheduler(tmp_path: Path):
    state = StateDatabase(tmp_path / "lingji_state.db")
    registry = SourceRegistry(state)
    root = tmp_path / "authorized"
    root.mkdir()
    source = registry.register(
        AuthorizationScope(
            grant_id="grant-adaptive",
            source_kinds=("generic_file",),
            roots=(str(root),),
            granted_at=datetime.now(timezone.utc),
            expires_at=None,
            owner_confirmed=True,
        ),
        "generic_file",
        str(root),
    )
    scheduler = AutomaticMemoryScheduler(
        state, registry, scan_runner=lambda *args: None
    )
    return state, registry, source.source_id, scheduler


def _next_action_text(report) -> str:
    return str(report.next_action or "")


def test_large_capture_stretches_window_beyond_base(tmp_path: Path) -> None:
    state, registry, source_id, scheduler = _scheduler(tmp_path)
    _completed_scan_with_items(
        state, registry, source_id,
        age_minutes=10,
        items=[("big.db", "job:job-1:new", 177 * MB)],
    )
    report = scheduler._snapshot_throttle_deferral(source_id)
    assert report is not None
    text = _next_action_text(report)
    # 177MiB ÷ 0.5MB/s ÷ 5% ≈ 7424s ≈ 124m 窗口；10 分钟前采的，还需 ~114 分钟。
    assert "window 124m" in text, text


def test_window_elapses_and_admits_again(tmp_path: Path) -> None:
    state, registry, source_id, scheduler = _scheduler(tmp_path)
    _completed_scan_with_items(
        state, registry, source_id,
        age_minutes=3 * 60,
        items=[("big.db", "job:job-1:new", 177 * MB)],
    )
    assert scheduler._snapshot_throttle_deferral(source_id) is None


def test_reuse_only_scan_keeps_base_window(tmp_path: Path) -> None:
    state, registry, source_id, scheduler = _scheduler(tmp_path)
    _completed_scan_with_items(
        state, registry, source_id,
        age_minutes=10,
        items=[("big.db", "reused", 177 * MB)],
    )
    report = scheduler._snapshot_throttle_deferral(source_id)
    assert report is not None
    assert "window 30m" in _next_action_text(report)


def test_small_capture_stays_on_base_window(tmp_path: Path) -> None:
    state, registry, source_id, scheduler = _scheduler(tmp_path)
    _completed_scan_with_items(
        state, registry, source_id,
        age_minutes=10,
        items=[("note.txt", "job:job-1:new", 2 * MB)],
    )
    report = scheduler._snapshot_throttle_deferral(source_id)
    assert report is not None
    assert "window 30m" in _next_action_text(report)


def test_value_gate_skipped_items_carry_no_cost(tmp_path: Path) -> None:
    state, registry, source_id, scheduler = _scheduler(tmp_path)
    _completed_scan_with_items(
        state, registry, source_id,
        age_minutes=10,
        items=[
            ("tiny.txt", "skipped_by_value_gate", 177 * MB),
            ("rest.db", "job:job-1:existing", 177 * MB),
        ],
    )
    report = scheduler._snapshot_throttle_deferral(source_id)
    assert report is not None
    assert "window 30m" in _next_action_text(report)


def test_base_window_still_applies_without_items(tmp_path: Path) -> None:
    state, registry, source_id, scheduler = _scheduler(tmp_path)
    _completed_scan_with_items(state, registry, source_id, age_minutes=20, items=[])
    report = scheduler._snapshot_throttle_deferral(source_id)
    assert report is not None
    assert "window 30m" in _next_action_text(report)


def test_throttle_uses_the_latest_completed_scan(tmp_path: Path) -> None:
    state, registry, source_id, scheduler = _scheduler(tmp_path)
    _completed_scan_with_items(state, registry, source_id, age_minutes=100, items=[])
    _completed_scan_with_items(state, registry, source_id, age_minutes=45, items=[])
    # 最新一次完成在 45 分钟前：基准 30 分钟窗口已过，应放行。
    assert scheduler._snapshot_throttle_deferral(source_id) is None
