from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from src.extraction.queue import SQLiteExtractionQueue
from src.extraction.adapters.generic_ai_history import GenericAIHistoryAdapter
from src.extraction.pipeline import ExtractionPipeline
from src.extraction.registry import AdapterRegistry
from src.extraction.sink import VaultExtractionSink
from src.automatic_memory.models import AuthorizationScope
from src.automatic_memory.source_registry import SourceRegistry
from src.memory import VaultLayout
from src.extraction.models import ExtractionBatch
from src.extraction.transient import (
    automatic_memory_dispatch_path,
    reconcile_automatic_memory_transients,
)


def _queue(tmp_path: Path) -> SQLiteExtractionQueue:
    return SQLiteExtractionQueue(tmp_path / "lingji_state.db")


def test_dispatch_marker_is_bounded_and_carries_job_and_lease(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    job = queue.enqueue(
        "automatic_memory_snapshot",
        input_path=tmp_path / ("a" * 64),
        payload={"source_id": "source-1", "raw_id": "a" * 64},
        idempotency_key="marker-identity",
    )
    claimed = queue.claim("worker-1", job_id=job["job_id"], allowed_source_types={"automatic_memory_snapshot"})
    assert claimed is not None
    marker = automatic_memory_dispatch_path(
        tmp_path / "raw", claimed["job_id"], claimed["lease_token"], ".jsonl"
    )
    assert marker.parent == tmp_path / "raw"
    assert marker.name.startswith(".automatic-memory-")
    assert claimed["job_id"] in marker.name
    assert claimed["lease_token"] in marker.name
    assert len(marker.name) <= 240


def test_terminal_marker_is_reconciled_and_repeat_is_idempotent(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    job = queue.enqueue(
        "automatic_memory_snapshot",
        input_path=tmp_path / ("b" * 64),
        payload={"source_id": "source-1", "raw_id": "b" * 64},
        idempotency_key="terminal-marker",
    )
    claimed = queue.claim("worker-1", job_id=job["job_id"], allowed_source_types={"automatic_memory_snapshot"})
    assert claimed is not None
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    marker = automatic_memory_dispatch_path(
        raw_root, claimed["job_id"], claimed["lease_token"], ".md"
    )
    marker.write_text("staging", encoding="utf-8")
    queue.complete(
        claimed["job_id"], {"ok": True}, worker_id="worker-1", lease_token=claimed["lease_token"]
    )

    first = reconcile_automatic_memory_transients(raw_root, queue)
    second = reconcile_automatic_memory_transients(raw_root, queue)
    assert not marker.exists()
    assert first["removed_count"] == 1
    assert first["errors"] == []
    assert second["removed_count"] == 0
    assert second["errors"] == []


def test_active_lease_is_preserved_but_expired_lease_is_removed(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    job = queue.enqueue(
        "automatic_memory_snapshot",
        input_path=tmp_path / ("c" * 64),
        payload={"source_id": "source-1", "raw_id": "c" * 64},
        idempotency_key="lease-marker",
    )
    claimed = queue.claim("worker-1", job_id=job["job_id"], allowed_source_types={"automatic_memory_snapshot"})
    assert claimed is not None
    marker = automatic_memory_dispatch_path(
        raw_root, claimed["job_id"], claimed["lease_token"], ".json"
    )
    marker.write_text("staging", encoding="utf-8")
    active = reconcile_automatic_memory_transients(raw_root, queue)
    assert marker.exists()
    assert active["preserved_count"] == 1
    assert active["preserved"][0]["reason"] == "active_lease"

    old = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(timespec="seconds")
    with queue._connection() as connection:
        connection.execute(
            "UPDATE extraction_jobs SET heartbeat_at = ?, locked_at = ? WHERE job_id = ?",
            (old, old, claimed["job_id"]),
        )
    expired = reconcile_automatic_memory_transients(raw_root, queue, stale_after_seconds=30)
    assert not marker.exists()
    assert expired["removed"][0]["reason"] == "expired_lease"


def test_unknown_malformed_symlink_and_directory_are_preserved(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    unknown = raw_root / ".automatic-memory-unknown.lease.jsonl"
    malformed = raw_root / ".automatic-memory-not-a-valid-marker.json"
    future = raw_root / ".automatic-memory-v2-LJ-JOB-FUTURE.lease-token.json"
    directory = raw_root / ".automatic-memory-directory.json"
    unknown.write_text("foreign", encoding="utf-8")
    malformed.write_text("malformed", encoding="utf-8")
    future.write_text("future", encoding="utf-8")
    directory.mkdir()
    symlink = raw_root / ".automatic-memory-link.json"
    try:
        symlink.symlink_to(unknown)
    except OSError:
        pytest.skip("symlinks unavailable on this platform")

    report = reconcile_automatic_memory_transients(raw_root, queue)
    assert unknown.exists()
    assert malformed.exists()
    assert directory.exists()
    assert symlink.is_symlink()
    assert future.exists()
    assert report["preserved_count"] == 5
    assert all(item["reason"] in {"unknown_marker", "unknown_job", "not_regular_file", "symlink"} for item in report["preserved"])


def test_unlink_permission_error_is_reported_without_false_success(tmp_path: Path, monkeypatch) -> None:
    queue = _queue(tmp_path)
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    job = queue.enqueue(
        "automatic_memory_snapshot",
        input_path=tmp_path / ("d" * 64),
        payload={"source_id": "source-1", "raw_id": "d" * 64},
        idempotency_key="unlink-error",
    )
    claimed = queue.claim("worker-1", job_id=job["job_id"], allowed_source_types={"automatic_memory_snapshot"})
    assert claimed is not None
    marker = automatic_memory_dispatch_path(raw_root, claimed["job_id"], claimed["lease_token"], ".jsonl")
    marker.write_text("staging", encoding="utf-8")
    queue.complete(claimed["job_id"], {}, worker_id="worker-1", lease_token=claimed["lease_token"])
    original_unlink = Path.unlink

    def fail_unlink(path: Path, *args, **kwargs):
        if path == marker:
            raise PermissionError("denied")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_unlink)
    report = reconcile_automatic_memory_transients(raw_root, queue)
    assert marker.exists()
    assert report["errors"][0]["reason"] == "unlink_failed"
    assert report["removed_count"] == 0
    monkeypatch.undo()
    retry = reconcile_automatic_memory_transients(raw_root, queue)
    assert not marker.exists()
    assert retry["removed_count"] == 1


def test_two_active_queue_leases_never_remove_each_other_markers(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    markers = []
    for index in range(2):
        job = queue.enqueue(
            "automatic_memory_snapshot", input_path=tmp_path / (f"{index}" * 64),
            payload={"source_id": f"source-{index}", "raw_id": f"{index}" * 64},
            idempotency_key=f"concurrent-{index}",
        )
        claimed = queue.claim(
            f"worker-{index}", job_id=job["job_id"],
            allowed_source_types={"automatic_memory_snapshot"},
        )
        assert claimed is not None
        marker = automatic_memory_dispatch_path(
            raw_root, claimed["job_id"], claimed["lease_token"], ".jsonl"
        )
        marker.write_text("staging", encoding="utf-8")
        markers.append(marker)
    report = reconcile_automatic_memory_transients(raw_root, queue)
    assert report["removed_count"] == 0
    assert all(marker.exists() for marker in markers)


def test_pipeline_dispatch_uses_queue_identity_and_leaves_durable_raw_unchanged(tmp_path: Path, monkeypatch) -> None:
    state_path = tmp_path / "lingji_state.db"
    state = __import__("src.storage", fromlist=["StateDatabase"]).StateDatabase(state_path)
    source_root = tmp_path / "source"
    source_root.mkdir()
    payload = {
        "schema": "lingji.history.inbox",
        "schema_version": "1",
        "conversations": [{
            "conversation_id": "conversation-1",
            "title": "A conversation",
            "messages": [{
                "message_id": "message-1", "role": "user",
                "content": "hello", "timestamp": "2026-01-01T00:00:00+00:00",
            }],
        }],
    }
    source_file = source_root / "history.json"
    source_file.write_text(json.dumps(payload), encoding="utf-8")
    registry = SourceRegistry(state)
    source = registry.register(
        AuthorizationScope("grant-1", ("generic_ai_history",), (str(source_root),), datetime.now(timezone.utc), None, True),
        "generic_ai_history", str(source_root),
    )
    raw_root = tmp_path / "storage" / "raw"
    raw_root.mkdir(parents=True)
    raw_bytes = source_file.read_bytes()
    raw_id = hashlib.sha256(raw_bytes).hexdigest()
    raw_path = raw_root / raw_id
    raw_path.write_bytes(raw_bytes)
    queue = SQLiteExtractionQueue(state_path)
    job = queue.enqueue(
        "automatic_memory_snapshot", input_path=raw_path,
        payload={"source_id": source.source_id, "source_type": "generic_ai_history", "raw_id": raw_id,
                 "sha256": raw_id, "relative_path": "history.json"},
        idempotency_key="pipeline-marker",
    )
    adapters = AdapterRegistry()
    adapter = GenericAIHistoryAdapter()
    adapters.register(adapter)
    sink = VaultExtractionSink(VaultLayout(tmp_path / "vault"), tmp_path / "storage", state_db=state)
    pipeline = ExtractionPipeline(queue, adapters, sink)
    observed: list[Path] = []
    original_extract = adapter.extract

    def inspect(request):
        assert request.input_path is not None
        observed.append(request.input_path)
        claimed = queue.get(job["job_id"])
        assert request.input_path.name.startswith(
            f".automatic-memory-v1-{job['job_id']}.{claimed['lease_token']}"
        )
        return original_extract(request)

    monkeypatch.setattr(adapter, "extract", inspect)
    result = pipeline.process_internal_next(worker_id="worker-1")
    assert result["job"]["status"] == "completed"
    assert observed and not observed[0].exists()
    assert raw_path.exists()
    assert hashlib.sha256(raw_path.read_bytes()).hexdigest() == raw_id


def test_real_killed_pipeline_leaves_marker_then_restart_reconciles_it(tmp_path: Path) -> None:
    state_path = tmp_path / "lingji_state.db"
    state = __import__("src.storage", fromlist=["StateDatabase"]).StateDatabase(state_path)
    source_root = tmp_path / "source"
    source_root.mkdir()
    source_file = source_root / "history.json"
    source_file.write_text(json.dumps({
        "schema": "lingji.history.inbox", "schema_version": "1",
        "conversations": [{"conversation_id": "c", "title": "c", "messages": [
            {"message_id": "m", "role": "user", "content": "hello", "timestamp": "2026-01-01T00:00:00+00:00"}
        ]}],
    }), encoding="utf-8")
    registry = SourceRegistry(state)
    source = registry.register(
        AuthorizationScope("grant-crash", ("generic_ai_history",), (str(source_root),), datetime.now(timezone.utc), None, True),
        "generic_ai_history", str(source_root),
    )
    raw_root = tmp_path / "storage" / "raw"
    raw_root.mkdir(parents=True)
    raw_bytes = source_file.read_bytes()
    raw_id = hashlib.sha256(raw_bytes).hexdigest()
    (raw_root / raw_id).write_bytes(raw_bytes)
    queue = SQLiteExtractionQueue(state_path)
    job = queue.enqueue(
        "automatic_memory_snapshot", input_path=raw_root / raw_id,
        payload={"source_id": source.source_id, "source_type": "generic_ai_history", "raw_id": raw_id,
                 "sha256": raw_id, "relative_path": "history.json"}, idempotency_key="real-crash-marker",
    )
    barrier = tmp_path / "adapter-entered"
    script = """
import os, time
from pathlib import Path
from src.extraction.adapters.generic_ai_history import GenericAIHistoryAdapter
from src.extraction.pipeline import ExtractionPipeline
from src.extraction.queue import SQLiteExtractionQueue
from src.extraction.registry import AdapterRegistry
from src.extraction.sink import VaultExtractionSink
from src.memory import VaultLayout
from src.storage import StateDatabase
class Blocking(GenericAIHistoryAdapter):
    def extract(self, request):
        Path(os.environ['LJ_BARRIER']).write_text('entered', encoding='utf-8')
        while True: time.sleep(0.05)
state = StateDatabase(Path(os.environ['LJ_STATE']))
queue = SQLiteExtractionQueue(Path(os.environ['LJ_STATE']))
registry = AdapterRegistry(); registry.register(Blocking())
sink = VaultExtractionSink(VaultLayout(Path(os.environ['LJ_VAULT'])), Path(os.environ['LJ_STORAGE']), state_db=state)
ExtractionPipeline(queue, registry, sink).process_internal_next()
"""
    env = dict(os.environ)
    env.update({"LJ_STATE": str(state_path), "LJ_STORAGE": str(tmp_path / "storage"),
                "LJ_VAULT": str(tmp_path / "vault"), "LJ_BARRIER": str(barrier)})
    process = subprocess.Popen([sys.executable, "-c", script], cwd=str(Path(__file__).parents[1]), env=env)
    try:
        deadline = time.monotonic() + 10
        while not barrier.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert barrier.exists(), "adapter did not reach the dispatch barrier"
        claimed = queue.get(job["job_id"])
        marker = automatic_memory_dispatch_path(raw_root, job["job_id"], claimed["lease_token"], ".json")
        assert marker.exists()
        os.kill(process.pid, 9)
        process.wait(timeout=10)
        assert process.returncode == -9
        restart_adapters = AdapterRegistry()
        restart_adapters.register(GenericAIHistoryAdapter())
        restart_sink = VaultExtractionSink(
            VaultLayout(tmp_path / "restart-vault"), tmp_path / "storage", state_db=state
        )
        restarted = ExtractionPipeline(queue, restart_adapters, restart_sink)
        report = restarted.transient_cleanup_inventory
        assert not marker.exists()
        assert report["removed"][0]["reason"] == "dead_worker"
        assert (raw_root / raw_id).exists()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
