from __future__ import annotations

from datetime import datetime, timezone
import multiprocessing
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

import pytest

from src.automatic_memory.models import AuthorizationScope
from src.automatic_memory.source_registry import SourceRegistry
from src.extraction.queue import SQLiteExtractionQueue
from src.storage import StateDatabase

try:
    from src.automatic_memory.checkpoint import (
        CheckpointStore,
        LeaseLostError,
        ResumeToken,
        SnapshotJobRunner,
    )
    from src.automatic_memory.snapshot import ConsistentSnapshot
except ImportError:
    CheckpointStore = ResumeToken = SnapshotJobRunner = ConsistentSnapshot = LeaseLostError = None  # type: ignore[assignment,misc]


def _scan_fixture(tmp_path: Path, count: int = 10):
    if CheckpointStore is None:
        import pytest

        pytest.fail("automatic-memory checkpoint production module is absent")
    state = StateDatabase(tmp_path / "lingji_state.db")
    root = tmp_path / "authorized"
    root.mkdir()
    for index in range(count):
        (root / f"item-{index:02d}.txt").write_text(f"item {index}", encoding="utf-8")
    registry = SourceRegistry(state)
    source = registry.register(
        AuthorizationScope(
            grant_id="grant-runner",
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
    queue = SQLiteExtractionQueue(tmp_path / "storage" / "lingji_state.db")
    return state, registry, source, scan, root, snapshot, queue


def _acquire_from_process(db_path: str, scan_id: str, lease_id: str, start, output) -> None:
    state = StateDatabase(db_path)
    start.wait(10)
    row = state.acquire_automatic_memory_scan_lease(scan_id, lease_id)
    output.put((lease_id, row["lease_id"] if row else None))


def test_checkpoint_round_trip_persists_resume_fields_in_existing_state_db(tmp_path: Path):
    state, _, _, scan, _, _, _ = _scan_fixture(tmp_path, count=1)
    store = CheckpointStore(state)
    state.acquire_automatic_memory_scan_lease(scan.scan_id, "lease-1")
    token = ResumeToken(
        scan_id=scan.scan_id,
        cursor="item-00.txt",
        source_sentinel="item-00.txt:8:123:9",
        lease_id="lease-1",
        attempt=2,
    )

    store.save(token)

    assert store.load(scan.scan_id) == token
    raw_scan = state.get_automatic_memory_scan(scan.scan_id)
    assert raw_scan["cursor"] == "item-00.txt"
    assert raw_scan["lease_id"] == "lease-1"
    assert raw_scan["attempt"] == 2


def test_runner_crash_at_thirty_percent_resumes_without_duplicate_raw_or_jobs(tmp_path: Path):
    state, registry, source, scan, root, snapshot, queue = _scan_fixture(tmp_path)
    provider = lambda current_scan, current_source: sorted(root.glob("*.txt"))
    runner = SnapshotJobRunner(snapshot, queue, state, path_provider=provider)

    interrupted = runner.run(scan.scan_id, crash_at="30%")
    assert interrupted.status == "paused"
    assert interrupted.progress == 3
    resumed = runner.run(scan.scan_id)
    assert resumed.status == "completed"
    assert resumed.progress == 10
    assert queue.count(source_type="automatic_memory_snapshot") == 10
    assert len(list((tmp_path / "storage" / "raw").iterdir())) == 10
    assert state.get_automatic_memory_scan(scan.scan_id)["lease_id"] is None

    again = runner.run(scan.scan_id)
    assert again.status == "completed"
    assert queue.count(source_type="automatic_memory_snapshot") == 10
    assert len(list((tmp_path / "storage" / "raw").iterdir())) == 10


def test_runner_crash_at_seventy_percent_resumes_and_releases_lease(tmp_path: Path):
    state, _, _, scan, root, snapshot, queue = _scan_fixture(tmp_path)
    runner = SnapshotJobRunner(
        snapshot,
        queue,
        state,
        path_provider=lambda current_scan, current_source: list(root.glob("*.txt")),
    )

    interrupted = runner.run(scan.scan_id, crash_at="70%")
    assert interrupted.status == "paused"
    assert interrupted.progress == 7
    assert state.get_automatic_memory_scan(scan.scan_id)["lease_id"] is None
    resumed = runner.run(scan.scan_id)
    assert resumed.status == "completed"
    assert queue.stats()["queued"] == 10


def test_runner_after_lease_crash_saves_checkpoint_without_temp_or_queue_side_effects(tmp_path: Path):
    state, _, _, scan, root, snapshot, queue = _scan_fixture(tmp_path, count=2)
    runner = SnapshotJobRunner(
        snapshot,
        queue,
        state,
        path_provider=lambda current_scan, current_source: list(root.glob("*.txt")),
    )

    interrupted = runner.run(scan.scan_id, crash_at="after-lease")

    assert interrupted.status == "paused"
    assert interrupted.progress == 0
    assert queue.stats()["pending"] == 0
    assert list((tmp_path / "storage" / "raw").glob("*.tmp")) == []
    assert state.get_automatic_memory_scan(scan.scan_id)["lease_id"] is None


def test_atomic_lease_competition_allows_one_owner_and_old_release_cannot_clear_new_owner(tmp_path: Path):
    state, _, _, scan, _, _, _ = _scan_fixture(tmp_path, count=1)
    barrier = threading.Barrier(2)
    results: list[tuple[str, str | None]] = []

    def acquire(lease_id: str) -> None:
        barrier.wait()
        row = state.acquire_automatic_memory_scan_lease(scan.scan_id, lease_id)
        results.append((lease_id, row["lease_id"] if row else None))

    first = threading.Thread(target=acquire, args=("lease-a",))
    second = threading.Thread(target=acquire, args=("lease-b",))
    first.start()
    second.start()
    first.join()
    second.join()

    winners = [lease_id for lease_id, owned in results if owned == lease_id]
    assert len(winners) == 1
    winner = winners[0]
    state.release_automatic_memory_scan_lease(scan.scan_id, winner)
    replacement = "lease-replacement"
    state.acquire_automatic_memory_scan_lease(scan.scan_id, replacement)
    with pytest.raises(LeaseLostError):
        state.release_automatic_memory_scan_lease(scan.scan_id, winner)
    assert state.get_automatic_memory_scan(scan.scan_id)["lease_id"] == replacement


def test_multiprocess_lease_competition_has_one_winner(tmp_path: Path):
    state, _, _, scan, _, _, _ = _scan_fixture(tmp_path, count=1)
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    output = context.Queue()
    processes = [
        context.Process(
            target=_acquire_from_process,
            args=(str(tmp_path / "lingji_state.db"), scan.scan_id, lease, start, output),
        )
        for lease in ("process-a", "process-b")
    ]
    for process in processes:
        process.start()
    start.set()
    for process in processes:
        process.join(timeout=10)
        assert process.exitcode == 0
    results = [output.get(timeout=2) for _ in processes]
    assert sum(lease == owned for lease, owned in results) == 1


def test_checkpoint_from_old_lease_cannot_overwrite_restarted_scan(tmp_path: Path):
    state, _, _, scan, _, _, _ = _scan_fixture(tmp_path, count=1)
    state.acquire_automatic_memory_scan_lease(scan.scan_id, "old")
    store = CheckpointStore(state)
    state.release_automatic_memory_scan_lease(scan.scan_id, "old")
    state.acquire_automatic_memory_scan_lease(scan.scan_id, "new")

    with pytest.raises(LeaseLostError):
        store.save(ResumeToken(scan.scan_id, "old.txt", "old-sentinel", "old", 1))
    row = state.get_automatic_memory_scan(scan.scan_id)
    assert row["lease_id"] == "new"
    assert row["cursor"] is None


def test_resume_rechecks_early_sentinels_and_new_paths_before_cursor(tmp_path: Path):
    state, _, _, scan, root, snapshot, queue = _scan_fixture(tmp_path)
    runner = SnapshotJobRunner(
        snapshot,
        queue,
        state,
        path_provider=lambda current_scan, current_source: list(root.glob("*.txt")),
    )
    assert runner.run(scan.scan_id, crash_at="30%").status == "paused"
    (root / "item-00.txt").write_text("changed early", encoding="utf-8")
    (root / "item-00a.txt").write_text("new before cursor", encoding="utf-8")

    resumed = runner.run(scan.scan_id)

    assert resumed.status == "completed"
    assert queue.count(source_type="automatic_memory_snapshot") == 12
    assert len(list((tmp_path / "storage" / "raw").iterdir())) == 12
    assert state.get_automatic_memory_scan(scan.scan_id)["progress"] == 11


@pytest.mark.parametrize("kill_after", [3, 7])
def test_subprocess_killed_after_queue_before_checkpoint_recovers_exactly(
    tmp_path: Path, kill_after: int
):
    state, _, _, scan, root, _, _ = _scan_fixture(tmp_path, count=10)
    marker = tmp_path / "queue-written.marker"
    code = """
from pathlib import Path
from src.automatic_memory.checkpoint import SnapshotJobRunner
from src.automatic_memory.snapshot import ConsistentSnapshot
from src.extraction.queue import SQLiteExtractionQueue
from src.storage import StateDatabase

root = Path(__import__('os').environ['LJ_ROOT'])
state = StateDatabase(__import__('os').environ['LJ_DB'])
queue = SQLiteExtractionQueue(__import__('os').environ['LJ_DB'])
snapshot = ConsistentSnapshot(state, Path(__import__('os').environ['LJ_RAW']))
def provider(scan, source):
    return list(root.glob('*.txt'))
def before_checkpoint(processed, total):
    if processed == int(__import__('os').environ['LJ_KILL_AFTER']):
        Path(__import__('os').environ['LJ_MARKER']).write_text('queue-written', encoding='utf-8')
        while True:
            pass
runner = SnapshotJobRunner(snapshot, queue, state, path_provider=provider, before_checkpoint=before_checkpoint)
runner.run(__import__('os').environ['LJ_SCAN'])
"""
    env = os.environ.copy()
    env.update(
        {
            "LJ_ROOT": str(root),
            "LJ_DB": str(tmp_path / "lingji_state.db"),
            "LJ_RAW": str(tmp_path / "storage" / "raw"),
            "LJ_MARKER": str(marker),
            "LJ_SCAN": scan.scan_id,
            "LJ_KILL_AFTER": str(kill_after),
            "PYTHONPATH": str(Path.cwd()),
        }
    )
    child = subprocess.Popen([sys.executable, "-c", code], env=env)
    deadline = time.time() + 10
    while time.time() < deadline and not marker.exists():
        time.sleep(0.02)
    assert marker.exists()
    child.send_signal(signal.SIGKILL)
    child.wait(timeout=10)
    assert child.returncode == -signal.SIGKILL

    reopened_state = StateDatabase(tmp_path / "lingji_state.db")
    reopened_queue = SQLiteExtractionQueue(tmp_path / "lingji_state.db")
    resumed = SnapshotJobRunner(
        ConsistentSnapshot(reopened_state, tmp_path / "storage" / "raw"),
        reopened_queue,
        reopened_state,
        path_provider=lambda current_scan, current_source: list(root.glob("*.txt")),
    ).run(scan.scan_id)

    assert resumed.status == "completed"
    assert reopened_queue.count(source_type="automatic_memory_snapshot") == 10
    assert len(list((tmp_path / "storage" / "raw").iterdir())) == 10
