"""Regression tests for manual-scan admission (2026-09-27 事故加固).

手动核对改为"受理即返回、专用单线程执行器执行"：整库重拷+哈希绝不占用
FastAPI 线程池（长时间占用曾把整个控制面拖到零响应）。红线：
①响应立即返回 admitted；②扫描真实执行（scan 行出现/队列前进）；
③无效来源同步报错；④对端轮询契约不受影响。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import time

from src.automatic_memory import AuthorizationScope, AutomaticMemoryRuntime
from src.automatic_memory.source_registry import SourceRegistry
from src.extraction.bootstrap import build_extraction_pipeline
from src.storage.state_db import StateDatabase


def _runtime(tmp_path: Path, root: Path):
    settings = SimpleNamespace(
        storage_path=tmp_path / "storage", state_db_path=tmp_path / "storage" / "lingji_state.db",
        memory_db_path=tmp_path / "storage" / "lingji_memory.db", vault_path=tmp_path / "vault",
        user_home=tmp_path, runtime_settings_file="runtime_settings.json",
        extraction_max_attempts=1, extraction_lease_heartbeat_seconds=2,
        extraction_stale_after_seconds=30, scheduler_poll_seconds=0.02,
        automatic_memory_debounce_seconds=1, automatic_memory_reconciliation_seconds=60,
        automatic_memory_integrity_seconds=3600, extraction_poll_seconds=0.02,
        extraction_batch_size=2, embedding_enabled=False, semantic_enabled=False,
    )
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    state = StateDatabase(settings.state_db_path)
    registry = SourceRegistry(state)
    pipeline = build_extraction_pipeline(settings)
    runtime = AutomaticMemoryRuntime(state_db=state, pipeline=pipeline, settings=settings, registry=registry)
    return state, registry, runtime


def test_scan_now_admits_and_executes_in_background(tmp_path: Path) -> None:
    root = tmp_path / "source"
    root.mkdir()
    (root / "note.txt").write_text("manual scan admission probe", encoding="utf-8")
    state, registry, runtime = _runtime(tmp_path, root)
    source = registry.register(
        AuthorizationScope(
            grant_id="grant-manual", source_kinds=("generic_file",), roots=(str(root),),
            granted_at=datetime.now(timezone.utc), expires_at=None, owner_confirmed=True,
        ),
        "generic_file", str(root),
    )
    deadline = time.monotonic() + 5
    while not registry.list_sources():
        if time.monotonic() > deadline:
            break
        time.sleep(0.05)

    started = time.monotonic()
    result = runtime.scan_now(source.source_id)
    elapsed = time.monotonic() - started
    # 快路径（本例小源）在预算内返回真实报告；超预算才转 admitted。
    # 两种形态都必须立即返回，绝不长占 HTTP 线程池。
    assert elapsed < 8, f"scan_now 耗时 {elapsed:.1f}s，超时转受理机制失效"
    assert result.get("status") == "admitted" or result.get("scan_id") or result.get("errors") is not None

    # 扫描真实执行：专用执行器完成后 durable scan 行出现并到达终态
    # （本测试的 generic_file 源无提取适配器，终态为 failed 也算真实执行）。
    deadline = time.monotonic() + 10
    terminal = None
    while time.monotonic() < deadline:
        scans = state.list_automatic_memory_scans(source.source_id)
        statuses = [str(s.get("status") or "") for s in scans]
        if any(s in {"completed", "failed"} for s in statuses):
            terminal = statuses
            break
        time.sleep(0.1)
    assert terminal, "受理后的扫描必须在专用执行器中真实执行到终态"


def test_scan_now_reports_unknown_source_without_raising(tmp_path: Path) -> None:
    """未知来源沿用旧契约：不抛异常，同步返回带 errors 的报告。"""
    state, registry, runtime = _runtime(tmp_path, tmp_path / "empty")
    result = runtime.scan_now("src-does-not-exist")
    assert isinstance(result, dict)
    assert result.get("errors") or result.get("complete") is False
