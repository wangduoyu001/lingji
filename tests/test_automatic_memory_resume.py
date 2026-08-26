from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
    queue = SQLiteExtractionQueue(tmp_path / "lingji_state.db")
    return state, registry, source, scan, root, snapshot, queue


def test_active_owned_snapshot_temp_survives_second_snapshot_constructor(tmp_path: Path):
    state, _, _, scan, _, snapshot, _ = _scan_fixture(tmp_path, count=1)
    lease_id = "active-copy-lease"
    state.acquire_automatic_memory_scan_lease(scan.scan_id, lease_id, ttl_seconds=60)
    temporary = snapshot._temporary_path(scan.scan_id, lease_id)
    temporary.write_bytes(b"active staging")

    ConsistentSnapshot(state, tmp_path / "storage" / "raw")

    assert temporary.exists()


def test_expired_owned_snapshot_temp_is_reclaimed_on_restart(tmp_path: Path):
    state, _, _, scan, _, snapshot, _ = _scan_fixture(tmp_path, count=1)
    lease_id = "expired-copy-lease"
    state.acquire_automatic_memory_scan_lease(scan.scan_id, lease_id, ttl_seconds=60)
    temporary = snapshot._temporary_path(scan.scan_id, lease_id)
    temporary.write_bytes(b"expired staging")
    with state._connection() as connection:
        connection.execute(
            "UPDATE automatic_memory_scans SET lease_expires_at = ? WHERE scan_id = ?",
            ("2000-01-01T00:00:00.000000+00:00", scan.scan_id),
        )

    ConsistentSnapshot(state, tmp_path / "storage" / "raw")

    assert not temporary.exists()


def test_active_owned_temp_with_legacy_null_expiry_is_preserved(tmp_path: Path):
    state, _, _, scan, _, snapshot, _ = _scan_fixture(tmp_path, count=1)
    lease_id = "legacy-null-expiry"
    state.acquire_automatic_memory_scan_lease(scan.scan_id, lease_id, ttl_seconds=60)
    temporary = snapshot._temporary_path(scan.scan_id, lease_id)
    temporary.write_bytes(b"legacy active staging")
    with state._connection() as connection:
        connection.execute(
            "UPDATE automatic_memory_scans SET lease_expires_at = NULL WHERE scan_id = ?",
            (scan.scan_id,),
        )

    ConsistentSnapshot(state, tmp_path / "storage" / "raw")

    assert temporary.exists()


@pytest.mark.parametrize("status", ["completed", "cancelled", "failed", "paused"])
def test_terminal_owned_snapshot_temp_is_reclaimed_without_lease(
    tmp_path: Path, status: str
):
    state, _, _, scan, _, snapshot, _ = _scan_fixture(tmp_path, count=1)
    temporary = snapshot._temporary_path(scan.scan_id, f"terminal-{status}")
    temporary.write_bytes(b"terminal staging")
    with state._connection() as connection:
        connection.execute(
            "UPDATE automatic_memory_scans SET status = ?, lease_id = NULL, "
            "lease_expires_at = NULL WHERE scan_id = ?",
            (status, scan.scan_id),
        )

    ConsistentSnapshot(state, snapshot.raw_root)

    assert not temporary.exists()


def test_running_owned_snapshot_temp_with_mismatched_lease_is_preserved(
    tmp_path: Path,
):
    state, _, _, scan, _, snapshot, _ = _scan_fixture(tmp_path, count=1)
    state.acquire_automatic_memory_scan_lease(scan.scan_id, "current-lease", ttl_seconds=60)
    temporary = snapshot._temporary_path(scan.scan_id, "old-lease")
    temporary.write_bytes(b"mismatched staging")
    with state._connection() as connection:
        connection.execute(
            "UPDATE automatic_memory_scans SET lease_expires_at = ? WHERE scan_id = ?",
            ("2000-01-01T00:00:00.000000+00:00", scan.scan_id),
        )

    ConsistentSnapshot(state, snapshot.raw_root)

    assert temporary.exists()


@pytest.mark.parametrize(
    "kind, keep",
    [
        ("future-offset", True),
        ("past-offset", False),
        ("future-z", True),
        ("past-z", False),
        ("future-utc", True),
        ("past-utc", False),
        ("future-naive", True),
        ("past-naive", True),
        ("invalid", True),
    ],
)
def test_owned_temp_expiry_parsing_is_timezone_aware_and_fail_closed(
    tmp_path: Path, kind: str, keep: bool
):
    now = datetime.now(timezone.utc)
    offset = timezone(timedelta(hours=5))
    expiry = {
        "future-offset": (now + timedelta(days=1)).astimezone(offset).isoformat(),
        "past-offset": (now - timedelta(days=1)).astimezone(offset).isoformat(),
        "future-z": (now + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
        "past-z": (now - timedelta(days=1)).isoformat().replace("+00:00", "Z"),
        "future-utc": (now + timedelta(days=1)).isoformat(),
        "past-utc": (now - timedelta(days=1)).isoformat(),
        "future-naive": (now + timedelta(days=1)).replace(tzinfo=None).isoformat(),
        "past-naive": (now - timedelta(days=1)).replace(tzinfo=None).isoformat(),
        "invalid": "not-a-timestamp",
    }[kind]
    state, _, _, scan, _, snapshot, _ = _scan_fixture(tmp_path, count=1)
    lease_id = f"lease-{kind}"
    state.acquire_automatic_memory_scan_lease(scan.scan_id, lease_id, ttl_seconds=60)
    temporary = snapshot._temporary_path(scan.scan_id, lease_id)
    temporary.write_bytes(b"timestamp staging")
    with state._connection() as connection:
        connection.execute(
            "UPDATE automatic_memory_scans SET lease_expires_at = ? WHERE scan_id = ?",
            (expiry, scan.scan_id),
        )

    ConsistentSnapshot(state, snapshot.raw_root)

    assert temporary.exists() is keep, kind


def test_malformed_owned_stale_temp_is_fail_closed_and_db_errors_preserve(tmp_path: Path, monkeypatch):
    state, _, _, scan, _, snapshot, _ = _scan_fixture(tmp_path, count=1)
    malformed = snapshot.raw_root / ".snapshot-owned-NOT-BASE64.tmp"
    malformed.write_bytes(b"malformed staging")
    undecodable = snapshot.raw_root / ".snapshot-owned-A.A.legacy.tmp"
    undecodable.write_bytes(b"undecodable staging")
    old = time.time() - 3 * 24 * 60 * 60
    os.utime(malformed, (old, old))
    os.utime(undecodable, (old, old))
    ConsistentSnapshot(state, snapshot.raw_root)
    assert malformed.exists()
    assert undecodable.exists()

    owned = snapshot._temporary_path(scan.scan_id, "lease-db-error")
    owned.write_bytes(b"db error staging")
    os.utime(owned, (old, old))
    monkeypatch.setattr(
        state,
        "get_automatic_memory_scan",
        lambda scan_id: (_ for _ in ()).throw(RuntimeError("state unavailable")),
    )
    ConsistentSnapshot(state, snapshot.raw_root)
    assert owned.exists()


def test_valid_owned_stale_temp_for_unknown_scan_is_preserved(tmp_path: Path):
    state, _, _, _, _, snapshot, _ = _scan_fixture(tmp_path, count=1)
    scan_id = "scan-missing-but-valid"
    lease_id = "lease-missing-but-valid"
    temporary = snapshot.raw_root / (
        f".snapshot-owned-{snapshot._encode_owner(scan_id)}."
        f"{snapshot._encode_owner(lease_id)}.token123.tmp"
    )
    temporary.write_bytes(b"unknown scan staging")
    old = time.time() - 3 * 24 * 60 * 60
    os.utime(temporary, (old, old))

    ConsistentSnapshot(state, snapshot.raw_root)

    assert temporary.exists()


def test_overlong_owned_token_is_preserved_as_unknown_stale_temp(tmp_path: Path):
    state, _, _, scan, _, snapshot, _ = _scan_fixture(tmp_path, count=1)
    lease_id = "lease-overlong-token"
    state.acquire_automatic_memory_scan_lease(scan.scan_id, lease_id, ttl_seconds=60)
    with state._connection() as connection:
        connection.execute(
            "UPDATE automatic_memory_scans SET lease_expires_at = ? WHERE scan_id = ?",
            ("2000-01-01T00:00:00+00:00", scan.scan_id),
        )
    token = "x" * 129
    temporary = snapshot.raw_root / (
        f".snapshot-owned-{snapshot._encode_owner(scan.scan_id)}."
        f"{snapshot._encode_owner(lease_id)}.{token}.tmp"
    )
    temporary.write_bytes(b"overlong token staging")
    old = time.time() - 3 * 24 * 60 * 60
    os.utime(temporary, (old, old))

    ConsistentSnapshot(state, snapshot.raw_root)

    assert temporary.exists()


@pytest.mark.parametrize("owner", ["../escape", "中文", "x" * 129, ""])
def test_owned_temp_creation_rejects_untrusted_owner_tokens(
    tmp_path: Path, owner: str
):
    """Creation must enforce the same bounded token grammar as cleanup parsing."""
    _, _, _, _, _, snapshot, _ = _scan_fixture(tmp_path, count=1)

    with pytest.raises(ValueError, match="owner"):
        snapshot._temporary_path(owner, "safe-lease")

    assert list(snapshot.raw_root.glob(".snapshot-owned-*.tmp")) == []


def test_unknown_fresh_temp_is_preserved_but_legacy_stale_temp_is_reclaimed(tmp_path: Path):
    _, registry, _, _, _, snapshot, _ = _scan_fixture(tmp_path, count=1)
    raw_root = snapshot.raw_root
    fresh = raw_root / ".snapshot-legacy-fresh.tmp"
    stale = raw_root / ".snapshot-legacy-stale.tmp"
    fresh.write_bytes(b"fresh unknown staging")
    stale.write_bytes(b"stale unknown staging")
    old = time.time() - 3 * 24 * 60 * 60
    os.utime(stale, (old, old))

    ConsistentSnapshot(registry, raw_root)

    assert fresh.exists()
    assert not stale.exists()


def test_concurrent_sources_keep_each_others_active_snapshot_temp(tmp_path: Path):
    state, registry, source_a, scan_a, root_a, snapshot_a, queue = _scan_fixture(tmp_path, count=1)
    root_b = tmp_path / "authorized-b"
    root_b.mkdir()
    source_b = registry.register(
        AuthorizationScope(
            grant_id="grant-runner-b",
            source_kinds=("generic_file",),
            roots=(str(root_b),),
            granted_at=datetime.now(timezone.utc),
            expires_at=None,
            owner_confirmed=True,
        ),
        "generic_file",
        str(root_b),
    )
    (root_b / "item-b.txt").write_text("item b", encoding="utf-8")
    scan_b = registry.start_scan(source_b.source_id)
    copy_started = threading.Event()
    release_copy = threading.Event()

    class PausedSnapshot(ConsistentSnapshot):
        def _copy_to_temp(self, source: Path, temporary: Path) -> None:
            copy_started.set()
            assert release_copy.wait(10)
            super()._copy_to_temp(source, temporary)

    runner_a = SnapshotJobRunner(
        PausedSnapshot(state, snapshot_a.raw_root),
        queue,
        state,
        path_provider=lambda current_scan, current_source: list(root_a.glob("*.txt")),
    )
    result_a: list = []
    worker_a = threading.Thread(target=lambda: result_a.append(runner_a.run(scan_a.scan_id)))
    worker_a.start()
    assert copy_started.wait(10)
    runner_b = SnapshotJobRunner(
        ConsistentSnapshot(state, snapshot_a.raw_root),
        queue,
        state,
        path_provider=lambda current_scan, current_source: list(root_b.glob("*.txt")),
    )
    result_b = runner_b.run(scan_b.scan_id)
    assert list(snapshot_a.raw_root.glob(".snapshot-owned-*.tmp"))
    release_copy.set()
    worker_a.join(timeout=10)

    assert result_a and result_a[0].status == "completed"
    assert result_b.status == "completed"
    assert queue.count(source_type="automatic_memory_snapshot") == 2
    assert len(list(snapshot_a.raw_root.iterdir())) == 2


def _acquire_from_process(db_path: str, scan_id: str, lease_id: str, start, output) -> None:
    state = StateDatabase(db_path)
    start.wait(10)
    row = state.acquire_automatic_memory_scan_lease(scan_id, lease_id)
    output.put((lease_id, row["lease_id"] if row else None))


def _run_snapshot_runner_from_process(db_path: str, raw_root: str, source_root: str, scan_id: str, output) -> None:
    state = StateDatabase(db_path)
    queue = SQLiteExtractionQueue(db_path)
    snapshot = ConsistentSnapshot(state, raw_root)
    runner = SnapshotJobRunner(
        snapshot,
        queue,
        state,
        path_provider=lambda current_scan, current_source: list(Path(source_root).glob("*.txt")),
    )
    try:
        output.put(runner.run(scan_id).status)
    except Exception as exc:
        output.put(f"error:{type(exc).__name__}:{exc}")


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
    state.acquire_automatic_memory_scan_lease(scan.scan_id, "lease-a")
    result: list[dict | None] = []
    second = threading.Thread(
        target=lambda: result.append(
            state.acquire_automatic_memory_scan_lease(scan.scan_id, "lease-b")
        )
    )
    second.start()
    second.join()
    assert result == [None]
    winner = "lease-a"
    state.release_automatic_memory_scan_lease(scan.scan_id, winner)
    replacement = "lease-replacement"
    state.acquire_automatic_memory_scan_lease(scan.scan_id, replacement)
    with pytest.raises(LeaseLostError):
        state.release_automatic_memory_scan_lease(scan.scan_id, winner)
    assert state.get_automatic_memory_scan(scan.scan_id)["lease_id"] == replacement


def test_lease_ttl_reclaims_dead_same_process_thread_but_not_active_heartbeat(tmp_path: Path):
    state, _, _, scan, _, _, _ = _scan_fixture(tmp_path, count=1)
    acquired = []

    def dead_worker() -> None:
        acquired.append(
            state.acquire_automatic_memory_scan_lease(
                scan.scan_id, "thread-owner", ttl_seconds=60
            )
        )

    worker = threading.Thread(target=dead_worker)
    worker.start()
    worker.join()
    assert acquired[0]["lease_id"] == "thread-owner"
    reclaimed = state.acquire_automatic_memory_scan_lease(scan.scan_id, "blocked")
    assert reclaimed["lease_id"] == "blocked"
    state.renew_automatic_memory_scan_lease(scan.scan_id, "blocked", ttl_seconds=60)
    assert state.acquire_automatic_memory_scan_lease(scan.scan_id, "still-blocked") is None


def test_lease_ttl_expiry_allows_reclaim_without_unix_signal_authority(tmp_path: Path):
    state, _, _, scan, _, _, _ = _scan_fixture(tmp_path, count=1)
    state.acquire_automatic_memory_scan_lease(
        scan.scan_id, "expiring", now="2020-01-01T00:00:00+00:00", ttl_seconds=1
    )
    reclaimed = state.acquire_automatic_memory_scan_lease(
        scan.scan_id, "replacement", now="2020-01-01T00:00:02+00:00", ttl_seconds=60
    )
    assert reclaimed["lease_id"] == "replacement"


def test_legacy_null_lease_expiry_is_reclaimed_with_safe_expiration(tmp_path: Path):
    state, _, _, scan, _, _, _ = _scan_fixture(tmp_path, count=1)
    state.acquire_automatic_memory_scan_lease(scan.scan_id, "legacy-owner")
    with state._connection() as connection:
        connection.execute(
            "UPDATE automatic_memory_scans SET lease_expires_at = NULL WHERE scan_id = ?",
            (scan.scan_id,),
        )

    replacement = state.acquire_automatic_memory_scan_lease(
        scan.scan_id,
        "replacement",
        ttl_seconds=5,
    )

    assert replacement is not None
    assert replacement["lease_id"] == "replacement"


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


def test_two_snapshot_runners_compete_cross_process_and_converge_idempotently(tmp_path: Path):
    state, _, source, scan, root, _, _ = _scan_fixture(tmp_path, count=5)
    context = multiprocessing.get_context("spawn")
    output = context.Queue()
    processes = [
        context.Process(
            target=_run_snapshot_runner_from_process,
            args=(
                str(tmp_path / "lingji_state.db"),
                str(tmp_path / "storage" / "raw"),
                str(root),
                scan.scan_id,
                output,
            ),
        )
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=15)
        assert process.exitcode == 0
    statuses = [output.get(timeout=2) for _ in processes]

    assert all(status in {"completed", "paused", "running"} for status in statuses), statuses
    reopened_queue = SQLiteExtractionQueue(tmp_path / "lingji_state.db")
    reopened_state = StateDatabase(tmp_path / "lingji_state.db")
    final = SnapshotJobRunner(
        ConsistentSnapshot(reopened_state, tmp_path / "storage" / "raw"),
        reopened_queue,
        reopened_state,
        path_provider=lambda current_scan, current_source: list(root.glob("*.txt")),
    ).run(scan.scan_id)
    assert final.status == "completed"
    assert reopened_queue.count(source_type="automatic_memory_snapshot") == 5
    assert len(list((tmp_path / "storage" / "raw").iterdir())) == 5


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


def test_runner_does_not_fail_cancelled_scan_after_source_revoke_race(tmp_path: Path):
    state, registry, source, scan, root, snapshot, queue = _scan_fixture(tmp_path, count=2)
    runner = SnapshotJobRunner(
        snapshot,
        queue,
        state,
        path_provider=lambda current_scan, current_source: list(root.glob("*.txt")),
        before_queue=lambda: registry.revoke(source.source_id),
    )

    result = runner.run(scan.scan_id)

    assert result.status == "cancelled"
    assert "revoked" in state.get_automatic_memory_scan(scan.scan_id)["last_error"]
    assert queue.count(source_type="automatic_memory_snapshot") == 0


def test_revoke_before_raw_commit_linearization_prevents_raw_object(tmp_path: Path):
    state, registry, source, scan, root, _, queue = _scan_fixture(tmp_path, count=1)
    state.acquire_automatic_memory_scan_lease(scan.scan_id, "raw-race")
    snapshot = ConsistentSnapshot(
        registry,
        tmp_path / "storage" / "raw",
        before_raw_commit=lambda: registry.revoke(source.source_id),
    )
    source_file = root / "item-00.txt"

    with pytest.raises(LeaseLostError):
        snapshot.capture(
            source.source_id,
            source_file,
            scan_id=scan.scan_id,
            lease_id="raw-race",
        )
    assert list((tmp_path / "storage" / "raw").iterdir()) == []
    assert queue.count(source_type="automatic_memory_snapshot") == 0


def test_subprocess_killed_immediately_after_lease_recovers(tmp_path: Path):
    state, _, _, scan, root, _, _ = _scan_fixture(tmp_path, count=2)
    marker = tmp_path / "lease.marker"
    code = """
from pathlib import Path
from src.automatic_memory.checkpoint import SnapshotJobRunner
from src.automatic_memory.snapshot import ConsistentSnapshot
from src.extraction.queue import SQLiteExtractionQueue
from src.storage import StateDatabase
import os
root = Path(os.environ['LJ_ROOT'])
state = StateDatabase(os.environ['LJ_DB'])
queue = SQLiteExtractionQueue(os.environ['LJ_DB'])
snapshot = ConsistentSnapshot(state, Path(os.environ['LJ_RAW']))
def provider(scan, source): return list(root.glob('*.txt'))
def after_lease():
    Path(os.environ['LJ_MARKER']).write_text('leased', encoding='utf-8')
    while True: pass
SnapshotJobRunner(snapshot, queue, state, path_provider=provider, after_lease=after_lease).run(os.environ['LJ_SCAN'])
"""
    env = os.environ.copy()
    env.update(
        {
            "LJ_ROOT": str(root),
            "LJ_DB": str(tmp_path / "lingji_state.db"),
            "LJ_RAW": str(tmp_path / "storage" / "raw"),
            "LJ_MARKER": str(marker),
            "LJ_SCAN": scan.scan_id,
            "PYTHONPATH": str(Path.cwd()),
        }
    )
    child = subprocess.Popen([sys.executable, "-c", code], env=env)
    deadline = time.time() + 10
    while time.time() < deadline and not marker.exists(): time.sleep(0.02)
    assert marker.exists()
    child.send_signal(signal.SIGKILL)
    child.wait(timeout=10)
    reopened = StateDatabase(tmp_path / "lingji_state.db")
    queue = SQLiteExtractionQueue(tmp_path / "lingji_state.db")
    result = SnapshotJobRunner(
        ConsistentSnapshot(reopened, tmp_path / "storage" / "raw"),
        queue,
        reopened,
        path_provider=lambda current_scan, current_source: list(root.glob("*.txt")),
    ).run(scan.scan_id)
    assert result.status == "completed"
    assert queue.count(source_type="automatic_memory_snapshot") == 2


def test_incremental_manifest_stays_per_path_and_scales_without_growing_token(tmp_path: Path):
    state, _, _, scan, _, _, _ = _scan_fixture(tmp_path, count=1)
    state.acquire_automatic_memory_scan_lease(scan.scan_id, "manifest-lease")
    store = CheckpointStore(state)
    for index in range(2000):
        store.save(
            ResumeToken(
                scan.scan_id,
                f"item-{index:04d}.txt",
                f"{index}:mtime:{index}",
                "manifest-lease",
                1,
            )
        )
    items = state.list_automatic_memory_scan_items(scan.scan_id)
    assert len(items) == 2000
    assert max(len(item["sentinel"]) for item in items) < 64
    assert len(state.get_automatic_memory_scan(scan.scan_id)["source_sentinel"] or "") < 64


def test_runner_rejects_queue_on_different_sqlite_file_before_any_snapshot_side_effect(tmp_path: Path):
    state, _, _, scan, root, snapshot, _ = _scan_fixture(tmp_path, count=1)
    other_queue = SQLiteExtractionQueue(tmp_path / "other.db")
    runner = SnapshotJobRunner(
        snapshot,
        other_queue,
        state,
        path_provider=lambda current_scan, current_source: list(root.glob("*.txt")),
    )

    with pytest.raises(ValueError, match="same SQLite"):
        runner.run(scan.scan_id)

    assert list((tmp_path / "storage" / "raw").iterdir()) == []
    assert other_queue.stats()["pending"] == 0
    assert state.get_automatic_memory_scan(scan.scan_id)["progress"] == 0


def test_runner_renews_short_ttl_during_slow_copy_and_stops_after_lease_release(tmp_path: Path):
    state, _, _, scan, root, snapshot, queue = _scan_fixture(tmp_path, count=1)

    class SlowSnapshot(ConsistentSnapshot):
        def _copy_to_temp(self, source: Path, temporary: Path) -> None:
            time.sleep(0.35)
            super()._copy_to_temp(source, temporary)

    slow = SlowSnapshot(state, tmp_path / "storage" / "raw")
    runner = SnapshotJobRunner(
        slow,
        queue,
        state,
        path_provider=lambda current_scan, current_source: list(root.glob("*.txt")),
        lease_ttl_seconds=0.1,
    )

    result = runner.run(scan.scan_id)

    assert result.status == "completed"
    assert queue.stats()["queued"] == 1
    assert state.get_automatic_memory_scan(scan.scan_id)["lease_id"] is None


def test_manifest_cleanup_removes_retired_scan_without_touching_current_recovery(tmp_path: Path):
    state, _, _, old_scan, _, _, _ = _scan_fixture(tmp_path, count=1)
    state.acquire_automatic_memory_scan_lease(old_scan.scan_id, "old-lease")
    CheckpointStore(state).save(
        ResumeToken(old_scan.scan_id, "item-00.txt", "8:1:1", "old-lease", 1)
    )
    state.release_automatic_memory_scan_lease(old_scan.scan_id, "old-lease")
    state.update_automatic_memory_scan(old_scan.scan_id, status="completed")

    current = state.create_automatic_memory_scan(
        {
            "scan_id": "scan-current",
            "source_id": old_scan.source_id,
            "status": "paused",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    state.acquire_automatic_memory_scan_lease(current["scan_id"], "current-lease")
    CheckpointStore(state).save(
        ResumeToken(current["scan_id"], "item-00.txt", "8:2:2", "current-lease", 1)
    )
    state.release_automatic_memory_scan_lease(current["scan_id"], "current-lease")

    state.cleanup_automatic_memory_scan_manifest(old_scan.scan_id)

    assert state.list_automatic_memory_scan_items(old_scan.scan_id) == []
    assert len(state.list_automatic_memory_scan_items(current["scan_id"])) == 1


def test_failed_scan_manifest_cannot_be_cleaned_before_recovery(tmp_path: Path):
    state, _, _, scan, _, _, _ = _scan_fixture(tmp_path, count=1)
    state.update_automatic_memory_scan(scan.scan_id, status="failed")

    with pytest.raises(ValueError, match="completed or cancelled"):
        state.cleanup_automatic_memory_scan_manifest(scan.scan_id)


def test_expired_lease_rejects_raw_commit_and_queue_admission(tmp_path: Path):
    state, _, source, scan, root, snapshot, queue = _scan_fixture(tmp_path, count=1)
    state.acquire_automatic_memory_scan_lease(
        scan.scan_id,
        "expired-lease",
        now="2020-01-01T00:00:00+00:00",
        ttl_seconds=0.1,
    )
    source_file = root / "item-00.txt"

    with pytest.raises(LeaseLostError):
        snapshot.capture(
            source.source_id,
            source_file,
            scan_id=scan.scan_id,
            lease_id="expired-lease",
        )
    assert list((tmp_path / "storage" / "raw").iterdir()) == []
    with pytest.raises(LeaseLostError):
        queue.enqueue_authorized_snapshot(
            scan_id=scan.scan_id,
            lease_id="expired-lease",
            source_id=source.source_id,
            relative_path="item-00.txt",
            raw_id="0" * 64,
            sha256="0" * 64,
            input_path=tmp_path / "storage" / "raw" / ("0" * 64),
        )


def test_zero_inode_sentinel_is_stable_across_scan_and_resume(tmp_path: Path, monkeypatch):
    state, _, _, scan, root, snapshot, queue = _scan_fixture(tmp_path, count=1)
    source_file = root / "item-00.txt"
    original_lstat = Path.lstat

    class ZeroInode:
        st_size = 6
        st_mtime_ns = 123
        st_ino = 0
        st_mode = source_file.stat().st_mode

    monkeypatch.setattr(Path, "lstat", lambda self: ZeroInode() if self == source_file else original_lstat(self))
    runner = SnapshotJobRunner(
        snapshot,
        queue,
        state,
        path_provider=lambda current_scan, current_source: [source_file],
    )

    assert runner.run(scan.scan_id).status == "completed"
    assert state.list_automatic_memory_scan_items(scan.scan_id)[0]["sentinel"].endswith(":0")


def test_revoke_cancels_admitted_snapshot_jobs_but_preserves_other_source_jobs(tmp_path: Path):
    state, registry, source, scan, root, snapshot, queue = _scan_fixture(tmp_path, count=2)
    other_root = tmp_path / "other-authorized"
    other_root.mkdir()
    other = registry.register(
        AuthorizationScope(
            grant_id="grant-other",
            source_kinds=("generic_file",),
            roots=(str(other_root),),
            granted_at=datetime.now(timezone.utc),
            expires_at=None,
            owner_confirmed=True,
        ),
        "generic_file",
        str(other_root),
    )
    other_scan = registry.start_scan(other.source_id)
    state.acquire_automatic_memory_scan_lease(scan.scan_id, "source-lease")
    state.acquire_automatic_memory_scan_lease(other_scan.scan_id, "other-lease")
    raw = snapshot.capture(
        source.source_id,
        root / "item-00.txt",
        scan_id=scan.scan_id,
        lease_id="source-lease",
    )
    other_file = other_root / "other.txt"
    other_file.write_text("other", encoding="utf-8")
    other_raw = snapshot.capture(
        other.source_id,
        other_file,
        scan_id=other_scan.scan_id,
        lease_id="other-lease",
    )
    queue.enqueue_authorized_snapshot(
        scan_id=scan.scan_id,
        lease_id="source-lease",
        source_id=source.source_id,
        relative_path=raw.relative_path,
        raw_id=raw.raw_id,
        sha256=raw.sha256,
        input_path=snapshot.raw_root / raw.raw_id,
    )
    queue.enqueue_authorized_snapshot(
        scan_id=other_scan.scan_id,
        lease_id="other-lease",
        source_id=other.source_id,
        relative_path=other_raw.relative_path,
        raw_id=other_raw.raw_id,
        sha256=other_raw.sha256,
        input_path=snapshot.raw_root / other_raw.raw_id,
    )

    registry.revoke(source.source_id)

    source_jobs = [job for job in queue.list() if job["payload"].get("source_id") == source.source_id]
    other_jobs = [job for job in queue.list() if job["payload"].get("source_id") == other.source_id]
    assert source_jobs and all(job["status"] == "cancelled" for job in source_jobs)
    assert other_jobs and other_jobs[0]["status"] == "queued"
    assert queue.claim("worker", job_id=source_jobs[0]["job_id"]) is None
