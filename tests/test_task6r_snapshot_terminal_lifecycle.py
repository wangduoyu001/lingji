from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

from src.automatic_memory.checkpoint import SnapshotJobRunner
from src.automatic_memory.models import AuthorizationScope
from src.automatic_memory.snapshot import ConsistentSnapshot
from src.automatic_memory.source_registry import SourceRegistry
from src.extraction.queue import SQLiteExtractionQueue
from src.storage import StateDatabase

import pytest


def _fixture(tmp_path: Path, *, count: int = 1):
    state = StateDatabase(tmp_path / "lingji_state.db")
    root = tmp_path / "authorized"
    root.mkdir()
    for index in range(count):
        (root / f"item-{index:02d}.txt").write_text(f"item {index}", encoding="utf-8")
    registry = SourceRegistry(state)
    source = registry.register(
        AuthorizationScope(
            grant_id="grant-task6r",
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
    return state, source, scan, root, snapshot, queue


def test_recovered_scan_reconciles_old_owned_temp_after_terminal_completion(tmp_path: Path):
    state, source, scan, root, snapshot, queue = _fixture(tmp_path)
    acquired: list[dict | None] = []
    owner = threading.Thread(
        target=lambda: acquired.append(
            state.acquire_automatic_memory_scan_lease(
                scan.scan_id, "crashed-lease", ttl_seconds=60
            )
        )
    )
    owner.start()
    owner.join()
    assert acquired[0] is not None
    temporary = snapshot._temporary_path(scan.scan_id, "crashed-lease")
    temporary.write_bytes(b"crashed staging")

    # Startup must preserve an active old lease marker before recovery acquires
    # its replacement lease.
    ConsistentSnapshot(state, snapshot.raw_root)
    assert temporary.exists()

    result = SnapshotJobRunner(
        snapshot,
        queue,
        state,
        path_provider=lambda current_scan, current_source: list(root.glob("*.txt")),
    ).run(scan.scan_id)

    assert result.status == "completed"
    assert not temporary.exists()


def test_paused_scan_reconciles_marker_after_release(tmp_path: Path):
    state, source, scan, root, snapshot, queue = _fixture(tmp_path)
    created: list[Path] = []

    def after_lease() -> None:
        lease_id = state.get_automatic_memory_scan(scan.scan_id)["lease_id"]
        marker = snapshot._temporary_path(scan.scan_id, lease_id)
        marker.write_bytes(b"paused staging")
        created.append(marker)

    result = SnapshotJobRunner(
        snapshot,
        queue,
        state,
        path_provider=lambda current_scan, current_source: list(root.glob("*.txt")),
        after_lease=after_lease,
    ).run(scan.scan_id, crash_at="after-lease")

    assert result.status == "paused"
    assert created and not created[0].exists()


def test_failed_scan_reconciles_marker_after_release(tmp_path: Path):
    state, source, scan, root, snapshot, queue = _fixture(tmp_path)
    created: list[Path] = []

    def before_queue() -> None:
        lease_id = state.get_automatic_memory_scan(scan.scan_id)["lease_id"]
        marker = snapshot._temporary_path(scan.scan_id, lease_id)
        marker.write_bytes(b"failed staging")
        created.append(marker)
        raise RuntimeError("queue admission failed")

    result = SnapshotJobRunner(
        snapshot,
        queue,
        state,
        path_provider=lambda current_scan, current_source: list(root.glob("*.txt")),
        before_queue=before_queue,
    ).run(scan.scan_id)

    assert result.status == "failed"
    assert created and not created[0].exists()


def test_reconcile_failure_is_sanitized_and_retryable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    state, source, scan, root, snapshot, queue = _fixture(tmp_path)
    state.update_automatic_memory_scan(scan.scan_id, status="completed")
    marker = snapshot._temporary_path(scan.scan_id, "finished-lease")
    marker.write_bytes(b"terminal staging")
    original_unlink = Path.unlink

    def failing_unlink(path: Path, *args, **kwargs):
        if path == marker:
            raise PermissionError("/private/secret/token=abc")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", failing_unlink)
    receipt = snapshot.reconcile_temporary_snapshots()

    assert marker.exists()
    assert receipt["clean"] is False
    assert receipt["errors"] == ("temporary_unlink_failed",)
    assert "/private" not in str(receipt)
    assert "token=abc" not in str(receipt)

    monkeypatch.setattr(Path, "unlink", original_unlink)
    retry = snapshot.reconcile_temporary_snapshots()
    assert not marker.exists()
    assert retry["removed"] == 1
    assert retry["clean"] is True


def test_reconcile_state_and_root_errors_fail_closed_with_generic_codes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    state, source, scan, root, snapshot, queue = _fixture(tmp_path)
    marker = snapshot._temporary_path(scan.scan_id, "unknown-state")
    marker.write_bytes(b"state unavailable")
    monkeypatch.setattr(
        state,
        "get_automatic_memory_scan",
        lambda scan_id: (_ for _ in ()).throw(RuntimeError("/private/secret/token=abc")),
    )
    receipt = snapshot.reconcile_temporary_snapshots()
    assert marker.exists()
    assert receipt["errors"] == ("state_read_failed",)
    assert "/private" not in str(receipt)
    assert "token=abc" not in str(receipt)

    monkeypatch.setattr(
        type(snapshot.raw_root),
        "iterdir",
        lambda self: (_ for _ in ()).throw(RuntimeError("/private/raw/secret")),
    )
    root_receipt = snapshot.reconcile_temporary_snapshots()
    assert root_receipt["errors"] == ("raw_root_scan_failed",)
    assert "/private" not in str(root_receipt)


def test_real_sigkill_restart_preserves_active_marker_then_cleans_on_terminal(
    tmp_path: Path,
):
    state, source, scan, root, snapshot, queue = _fixture(tmp_path)
    marker_signal = tmp_path / "marker-created"
    child_code = """
import os
from pathlib import Path
from src.automatic_memory.checkpoint import SnapshotJobRunner
from src.automatic_memory.snapshot import ConsistentSnapshot
from src.extraction.queue import SQLiteExtractionQueue
from src.storage import StateDatabase

root = Path(os.environ['LJ_ROOT'])
state = StateDatabase(os.environ['LJ_DB'])
queue = SQLiteExtractionQueue(os.environ['LJ_DB'])
snapshot = ConsistentSnapshot(state, Path(os.environ['LJ_RAW']))
def provider(scan, source):
    return list(root.glob('*.txt'))
def after_lease():
    lease = state.get_automatic_memory_scan(os.environ['LJ_SCAN'])['lease_id']
    marker = snapshot._temporary_path(os.environ['LJ_SCAN'], lease)
    marker.write_bytes(b'crashed staging')
    Path(os.environ['LJ_SIGNAL']).write_text('created', encoding='utf-8')
    while True:
        pass
SnapshotJobRunner(snapshot, queue, state, path_provider=provider, after_lease=after_lease).run(os.environ['LJ_SCAN'])
"""
    env = os.environ.copy()
    env.update(
        {
            "LJ_ROOT": str(root),
            "LJ_DB": str(tmp_path / "lingji_state.db"),
            "LJ_RAW": str(snapshot.raw_root),
            "LJ_SCAN": scan.scan_id,
            "LJ_SIGNAL": str(marker_signal),
            "PYTHONPATH": str(Path.cwd()),
        }
    )
    child = subprocess.Popen([sys.executable, "-c", child_code], env=env)
    try:
        deadline = time.monotonic() + 10
        while not marker_signal.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert marker_signal.exists()
        child.send_signal(signal.SIGKILL)
        child.wait(timeout=10)
        assert child.returncode == -signal.SIGKILL

        restarted = ConsistentSnapshot(state, snapshot.raw_root)
        marker_files = list(snapshot.raw_root.glob(".snapshot-owned-*.tmp"))
        assert len(marker_files) == 1
        assert marker_files[0].exists()

        result = SnapshotJobRunner(
            restarted,
            queue,
            state,
            path_provider=lambda current_scan, current_source: list(root.glob("*.txt")),
        ).run(scan.scan_id)

        assert result.status == "completed"
        assert not marker_files[0].exists()
        assert queue.count(source_type="automatic_memory_snapshot") == 1
        assert len(list(snapshot.raw_root.iterdir())) == 1
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=10)
