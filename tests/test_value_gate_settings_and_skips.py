"""Regression tests for PERF_RESOURCE_CLOSEOUT_20260927B (B1 收尾).

Covers: thresholds served dynamically to a running SnapshotJobRunner, the
``skipped_by_value_gate`` manifest status value domain (a gated skip never
masquerades as "queued"), the skipped display endpoint, and per-source rescan
undo (红线：绝不静默丢弃，误杀可撤销).
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.automatic_memory.checkpoint import (
    VALUE_GATE_SKIPPED_STATUS,
    SnapshotJobRunner,
    value_gate_audit_path,
)
from src.automatic_memory.models import AuthorizationScope
from src.automatic_memory.snapshot import ConsistentSnapshot
from src.automatic_memory.source_registry import SourceRegistry
from src.control.runtime_settings import RuntimeSettingsStore
from src.extraction.queue import SQLiteExtractionQueue
from src.storage.state_db import StateDatabase


def _fixture(tmp_path: Path):
    state = StateDatabase(tmp_path / "lingji_state.db")
    root = tmp_path / "authorized"
    root.mkdir()
    (root / "tiny-01.txt").write_text("你好", encoding="utf-8")
    registry = SourceRegistry(state)
    source = registry.register(
        AuthorizationScope(
            grant_id="grant-b1",
            source_kinds=("generic_file",),
            roots=(str(root),),
            granted_at=datetime.now(timezone.utc),
            expires_at=None,
            owner_confirmed=True,
        ),
        "generic_file",
        str(root),
    )
    scan = registry.start_scan(source.source_id)
    raw_root = tmp_path / "storage" / "raw"
    snapshot = ConsistentSnapshot(registry, raw_root)
    queue = SQLiteExtractionQueue(tmp_path / "lingji_state.db")
    return state, source, registry, root, snapshot, queue


def _scan_item_statuses(state: StateDatabase) -> list[str]:
    with sqlite3.connect(str(state.path)) as conn:
        return [
            str(row[0])
            for row in conn.execute("SELECT status FROM automatic_memory_scan_items")
        ]


def _queued_job_count(state: StateDatabase) -> int:
    with sqlite3.connect(str(state.path)) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM extraction_jobs").fetchone()[0])


def test_dynamic_threshold_provider_gates_and_admits(tmp_path: Path) -> None:
    state, source, registry, root, snapshot, queue = _fixture(tmp_path)
    config = {"enabled": True, "turns": 2, "chars": 300}
    result = SnapshotJobRunner(
        snapshot,
        queue,
        state,
        path_provider=lambda scan, src: list(root.glob("*.txt")),
        value_gate_enabled=False,  # static off: the provider is authoritative
        value_gate_config_provider=lambda: (
            config["enabled"],
            config["turns"],
            config["chars"],
        ),
    ).run(registry.start_scan(source.source_id).scan_id)
    assert result.status == "completed"
    assert _scan_item_statuses(state) == [VALUE_GATE_SKIPPED_STATUS]
    # 绝不静默：被拦会话不入队、审计留痕。
    assert _queued_job_count(state) == 0
    audit_path = value_gate_audit_path(snapshot.raw_root)
    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert entries and entries[0]["source_id"] == source.source_id
    assert "reason" in entries[0]

    # 主人放宽阈值（1 轮 / 1 字），撤销后重扫即放行入队。
    cleared = state.clear_automatic_memory_scan_items_by_status(
        VALUE_GATE_SKIPPED_STATUS, source_id=source.source_id
    )
    assert cleared == 1
    config.update({"turns": 1, "chars": 1})
    SnapshotJobRunner(
        snapshot,
        queue,
        state,
        path_provider=lambda scan, src: list(root.glob("*.txt")),
        value_gate_config_provider=lambda: (
            config["enabled"],
            config["turns"],
            config["chars"],
        ),
    ).run(registry.start_scan(source.source_id).scan_id)
    assert VALUE_GATE_SKIPPED_STATUS not in _scan_item_statuses(state)
    assert _queued_job_count(state) == 1


def test_gate_disabled_via_provider_never_records_skips(tmp_path: Path) -> None:
    state, source, registry, root, snapshot, queue = _fixture(tmp_path)
    SnapshotJobRunner(
        snapshot,
        queue,
        state,
        path_provider=lambda scan, src: list(root.glob("*.txt")),
        value_gate_config_provider=lambda: (False, 2, 300),
    ).run(registry.start_scan(source.source_id).scan_id)
    assert VALUE_GATE_SKIPPED_STATUS not in _scan_item_statuses(state)
    assert _queued_job_count(state) == 1
    assert not value_gate_audit_path(snapshot.raw_root).exists()


def test_runtime_settings_value_gate_definitions(tmp_path: Path) -> None:
    settings = SimpleNamespace(
        storage_path=tmp_path, runtime_settings_file="runtime_settings.json"
    )
    store = RuntimeSettingsStore(settings)
    keys = {"value_gate_enabled", "value_gate_min_turns", "value_gate_min_chars"}
    assert keys <= set(store.definitions())
    assert store.snapshot()["values"]["value_gate_enabled"] is True
    store.update({"value_gate_min_turns": 5, "value_gate_min_chars": 1000})
    values = store.snapshot()["values"]
    assert values["value_gate_min_turns"] == 5
    assert values["value_gate_min_chars"] == 1000
    with pytest.raises((KeyError, ValueError)):
        store.update({"value_gate_min_turns": 10_000})


def test_threshold_precedence_owner_override_over_static_config(tmp_path: Path) -> None:
    """目录默认值不得压过静态配置；只有主人的显式覆盖才改运行行为。"""
    from src.automatic_memory.runtime import AutomaticMemoryRuntime

    settings = SimpleNamespace(
        storage_path=tmp_path,
        runtime_settings_file="runtime_settings.json",
        value_gate_enabled=True,
    )
    runtime = AutomaticMemoryRuntime.__new__(AutomaticMemoryRuntime)
    runtime.settings = settings
    runtime._runner_settings_store = None
    runtime._runner_settings_store_failed = False
    # 无覆盖时以静态配置为准。
    assert runtime._value_gate_config() == (True, 2, 300)
    # 主人显式覆盖（写入非默认值）后立即生效。
    RuntimeSettingsStore(settings).update(
        {"value_gate_enabled": False, "value_gate_min_turns": 7}
    )
    assert runtime._value_gate_config() == (False, 7, 300)


def _api_control(tmp_path: Path):
    from src.control.api import create_control_app
    from src.control.service import LocalControlService

    storage = tmp_path / "storage"
    storage.mkdir()
    raw_root = storage / "raw"
    raw_root.mkdir()
    control = LocalControlService.__new__(LocalControlService)
    state = StateDatabase(storage / "lingji_state.db")
    control.state_db = state
    audit = value_gate_audit_path(raw_root)
    audit.parent.mkdir(parents=True, exist_ok=True)
    # Two authorized sources, each with one gated-skip manifest item.
    registry = SourceRegistry(state)
    source_ids: list[str] = []
    for index in range(2):
        root = tmp_path / f"authorized-{index}"
        root.mkdir()
        source = registry.register(
            AuthorizationScope(
                grant_id=f"grant-b1-{index}",
                source_kinds=("generic_file",),
                roots=(str(root),),
                granted_at=datetime.now(timezone.utc),
                expires_at=None,
                owner_confirmed=True,
            ),
            "generic_file",
            str(root),
        )
        source_ids.append(source.source_id)
        scan = registry.start_scan(source.source_id)
        lease = state.acquire_automatic_memory_scan_lease(
            scan.scan_id, f"lease-{index}", ttl_seconds=60
        )
        assert lease
        state.upsert_automatic_memory_scan_item_owned(
            scan.scan_id,
            f"lease-{index}",
            source_id=source.source_id,
            relative_path="tiny.txt",
            sentinel="1:1:0:0",
            status=VALUE_GATE_SKIPPED_STATUS,
        )
    audit.write_text(
        json.dumps({"source_id": source_ids[0], "reason": "below value floor", "total_chars": 2})
        + "\n"
        + json.dumps({"action": "rescan_requested", "source_id": "unrelated"})
        + "\n",
        encoding="utf-8",
    )
    runner = SimpleNamespace(_value_gate_config=lambda: (True, 2, 300))
    control.runtime = SimpleNamespace(
        runner=runner, snapshot=SimpleNamespace(raw_root=raw_root)
    )
    app = create_control_app(settings=SimpleNamespace(storage_path=storage), service=control, token="local-secret")
    return app, control, source_ids


def test_value_gate_endpoints(tmp_path: Path) -> None:
    app, control, source_ids = _api_control(tmp_path)
    headers = {"X-LingJi-Token": "local-secret"}
    with TestClient(app) as client:
        assert client.get(
            "/api/automatic-memory/value-gate/skipped"
        ).status_code == 401
        payload = client.get(
            "/api/automatic-memory/value-gate/skipped", headers=headers
        ).json()
        assert payload["enabled"] is True
        assert payload["thresholds"] == {"min_turns": 2, "min_chars": 300}
        assert payload["total"] == 1  # rescan markers never inflate the count
        # 倒序：最新在前，被拦会话记录在最旧端。
        assert payload["entries"][-1]["source_id"] == source_ids[0]

        cleared = client.post(
            "/api/automatic-memory/value-gate/rescan",
            headers=headers,
            json={"source_id": source_ids[0]},
        ).json()
        assert cleared["cleared"] == 1
        # 按来源撤销只影响该来源：第二来源的拦截仍在，全量撤销清掉它。
        remaining = client.post(
            "/api/automatic-memory/value-gate/rescan", headers=headers, json={}
        ).json()
        assert remaining["cleared"] == 1
        assert client.post(
            "/api/automatic-memory/value-gate/rescan", headers=headers, json={}
        ).json()["cleared"] == 0
        after = client.get(
            "/api/automatic-memory/value-gate/skipped", headers=headers
        ).json()
        assert after["entries"][0]["action"] == "rescan_requested"
        with sqlite3.connect(str(control.state_db.path)) as conn:
            left = conn.execute(
                "SELECT COUNT(*) FROM automatic_memory_scan_items WHERE status = ?",
                (VALUE_GATE_SKIPPED_STATUS,),
            ).fetchone()[0]
        assert left == 0
