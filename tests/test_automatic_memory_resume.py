from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.automatic_memory.models import AuthorizationScope
from src.automatic_memory.source_registry import SourceRegistry
from src.extraction.queue import SQLiteExtractionQueue
from src.storage import StateDatabase

try:
    from src.automatic_memory.checkpoint import CheckpointStore, ResumeToken, SnapshotJobRunner
    from src.automatic_memory.snapshot import ConsistentSnapshot
except ModuleNotFoundError:
    CheckpointStore = ResumeToken = SnapshotJobRunner = ConsistentSnapshot = None  # type: ignore[assignment,misc]


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


def test_checkpoint_round_trip_persists_resume_fields_in_existing_state_db(tmp_path: Path):
    state, _, _, scan, _, _, _ = _scan_fixture(tmp_path, count=1)
    store = CheckpointStore(state)
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
