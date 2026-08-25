from __future__ import annotations

import os
import multiprocessing
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.automatic_memory.models import AuthorizationScope
from src.automatic_memory.source_registry import SourceRegistry
from src.extraction.sink import VaultExtractionSink
from src.memory import VaultLayout
from src.storage import StateDatabase

try:
    from src.automatic_memory.snapshot import ConsistentSnapshot
except ModuleNotFoundError:
    ConsistentSnapshot = None  # type: ignore[assignment,misc]


def _commit_from_process(storage: str, temporary_name: str, digest: str, output) -> None:
    sink = VaultExtractionSink(VaultLayout(Path(storage).parent / "vault"), storage)
    try:
        result = sink.commit_raw_temp(Path(temporary_name), digest)
        output.put(("ok", str(result)))
    except Exception as exc:
        output.put((type(exc).__name__, str(exc)))


def _authorized_source(tmp_path: Path):
    if ConsistentSnapshot is None:
        pytest.fail("automatic-memory snapshot production module is absent")
    state = StateDatabase(tmp_path / "lingji_state.db")
    root = tmp_path / "authorized"
    root.mkdir()
    registry = SourceRegistry(state)
    source = registry.register(
        AuthorizationScope(
            grant_id="grant-task2",
            source_kinds=("generic_file",),
            roots=(str(root),),
            granted_at=datetime.now(timezone.utc),
            expires_at=None,
            owner_confirmed=True,
        ),
        "generic_file",
        str(root),
    )
    return state, registry, source, root


def test_consistent_snapshot_preserves_stable_source_and_does_not_mutate_sentinel(tmp_path: Path):
    state, registry, source, root = _authorized_source(tmp_path)
    source_file = root / "notes.txt"
    source_file.write_text("owner evidence\n", encoding="utf-8")
    before = source_file.stat()
    snapshot = ConsistentSnapshot(registry, tmp_path / "storage" / "raw")

    result = snapshot.capture(source.source_id, source_file)

    after = source_file.stat()
    assert result.stable is True
    assert result.relative_path == "notes.txt"
    assert result.raw_id == result.sha256
    assert result.stat_before.size == len("owner evidence\n".encode())
    assert result.stat_before == result.stat_after
    assert (tmp_path / "storage" / "raw" / result.raw_id).read_bytes() == b"owner evidence\n"
    assert (after.st_mtime_ns, after.st_mode, getattr(after, "st_ino", None)) == (
        before.st_mtime_ns,
        before.st_mode,
        getattr(before, "st_ino", None),
    )


def test_content_addressed_snapshot_deduplicates_identical_content_across_paths(tmp_path: Path):
    _, registry, source, root = _authorized_source(tmp_path)
    first = root / "a.txt"
    second = root / "nested" / "b.txt"
    second.parent.mkdir()
    first.write_text("same bytes", encoding="utf-8")
    second.write_text("same bytes", encoding="utf-8")
    snapshot = ConsistentSnapshot(registry, tmp_path / "storage" / "raw")

    one = snapshot.capture(source.source_id, first)
    two = snapshot.capture(source.source_id, second)

    assert one.raw_id == two.raw_id == one.sha256
    assert sorted(path.name for path in (tmp_path / "storage" / "raw").iterdir()) == [one.raw_id]


def test_snapshot_rejects_symlink_directory_and_root_escape(tmp_path: Path):
    _, registry, source, root = _authorized_source(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = root / "escape.txt"
    link.symlink_to(outside)
    directory = root / "directory"
    directory.mkdir()
    snapshot = ConsistentSnapshot(registry, tmp_path / "storage" / "raw")

    with pytest.raises(PermissionError):
        snapshot.capture(source.source_id, link)
    with pytest.raises(ValueError):
        snapshot.capture(source.source_id, directory)
    with pytest.raises(PermissionError):
        snapshot.capture(source.source_id, outside)


def test_snapshot_rejects_revoked_and_expired_source(tmp_path: Path):
    state, registry, source, root = _authorized_source(tmp_path)
    source_file = root / "notes.txt"
    source_file.write_text("evidence", encoding="utf-8")
    snapshot = ConsistentSnapshot(registry, tmp_path / "storage" / "raw")
    registry.revoke(source.source_id)
    with pytest.raises(PermissionError):
        snapshot.capture(source.source_id, source_file)

    state2 = StateDatabase(tmp_path / "expired.db")
    expired_root = tmp_path / "expired"
    expired_root.mkdir()
    expired_registry = SourceRegistry(state2)
    state2.create_automatic_memory_grant(
        {
            "grant_id": "grant-expired",
            "source_kinds_json": '["generic_file"]',
            "roots_json": f'["{expired_root}"]',
            "granted_at": "2020-01-01T00:00:00+00:00",
            "expires_at": "2020-01-02T00:00:00+00:00",
            "owner_confirmed": True,
            "created_at": "2020-01-01T00:00:00+00:00",
        }
    )
    expired = state2.create_automatic_memory_source(
        {
            "source_id": "src-expired",
            "grant_id": "grant-expired",
            "kind": "generic_file",
            "root": str(expired_root),
            "status": "authorized",
            "capability": "metadata_discovery",
            "policy_version": "automatic-memory-source-v1",
            "created_at": "2020-01-01T00:00:00+00:00",
        }
    )
    expired_file = expired_root / "expired.txt"
    expired_file.write_text("expired", encoding="utf-8")
    with pytest.raises(PermissionError):
        ConsistentSnapshot(expired_registry, tmp_path / "storage" / "raw").capture(
            expired["source_id"], expired_file
        )


if ConsistentSnapshot is not None:
    class _ChangingSnapshot(ConsistentSnapshot):
        def __init__(self, *args, changing_file: Path, **kwargs):
            super().__init__(*args, **kwargs)
            self._changing_file = changing_file
            self._copies = 0

        def _copy_to_temp(self, source: Path, temporary: Path) -> None:
            super()._copy_to_temp(source, temporary)
            self._copies += 1
            source.write_text(f"changed during copy {self._copies}", encoding="utf-8")
else:
    _ChangingSnapshot = object


def test_changed_source_retries_three_times_and_cleans_unstable_temps(tmp_path: Path):
    _, registry, source, root = _authorized_source(tmp_path)
    source_file = root / "changing.txt"
    source_file.write_text("initial", encoding="utf-8")
    snapshot = _ChangingSnapshot(
        registry,
        tmp_path / "storage" / "raw",
        changing_file=source_file,
    )

    result = snapshot.capture(source.source_id, source_file, max_attempts=3)

    assert result.stable is False
    assert result.attempt == 3
    assert list((tmp_path / "storage" / "raw").glob("*.tmp")) == []


def test_raw_commit_rejects_corrupt_existing_object_and_preserves_diagnostic_temp(tmp_path: Path):
    storage = tmp_path / "storage"
    sink = VaultExtractionSink(VaultLayout(tmp_path / "vault"), storage)
    digest = __import__("hashlib").sha256(b"expected").hexdigest()
    target = sink.content_addressed_raw_path(digest)
    target.parent.mkdir(parents=True)
    target.write_bytes(b"corrupt")
    temporary = storage / "raw" / ".snapshot-corrupt.tmp"
    temporary.write_bytes(b"expected")

    with pytest.raises(ValueError, match="content-addressed raw object"):
        sink.commit_raw_temp(temporary, digest)
    assert temporary.exists()


def test_raw_commit_rejects_existing_directory_at_content_address(tmp_path: Path):
    sink = VaultExtractionSink(VaultLayout(tmp_path / "vault"), tmp_path / "storage")
    digest = __import__("hashlib").sha256(b"expected").hexdigest()
    target = sink.content_addressed_raw_path(digest)
    target.mkdir(parents=True)
    temporary = sink.raw_root / ".snapshot-directory.tmp"
    temporary.write_bytes(b"expected")

    with pytest.raises(ValueError, match="content-addressed raw object"):
        sink.commit_raw_temp(temporary, digest)
    assert temporary.exists()


def test_raw_commit_concurrent_processes_converges_without_overwrite(tmp_path: Path):
    storage = tmp_path / "storage"
    sink = VaultExtractionSink(VaultLayout(tmp_path / "vault"), storage)
    digest = __import__("hashlib").sha256(b"same").hexdigest()
    sink.raw_root.mkdir(parents=True)
    first = sink.raw_root / ".one.tmp"
    second = sink.raw_root / ".two.tmp"
    first.write_bytes(b"same")
    second.write_bytes(b"same")
    context = multiprocessing.get_context("spawn")
    output = context.Queue()
    processes = [
        context.Process(target=_commit_from_process, args=(str(storage), str(path), digest, output))
        for path in (first, second)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=10)
        assert process.exitcode == 0
    results = [output.get(timeout=2) for _ in processes]
    assert all(result[0] == "ok" for result in results)
    assert sink.content_addressed_raw_path(digest).read_bytes() == b"same"
    assert list(sink.raw_root.glob("*.tmp")) == []


def test_raw_commit_rejects_existing_symlink_object(tmp_path: Path):
    sink = VaultExtractionSink(VaultLayout(tmp_path / "vault"), tmp_path / "storage")
    digest = __import__("hashlib").sha256(b"expected").hexdigest()
    target = sink.content_addressed_raw_path(digest)
    target.parent.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.write_bytes(b"expected")
    target.symlink_to(outside)
    temporary = sink.raw_root / ".snapshot-symlink.tmp"
    temporary.write_bytes(b"expected")

    with pytest.raises(ValueError, match="content-addressed raw object"):
        sink.commit_raw_temp(temporary, digest)
    assert temporary.exists()


def test_capture_quarantines_raw_conflict_for_diagnosis(tmp_path: Path):
    _, registry, source, root = _authorized_source(tmp_path)
    source_file = root / "conflict.txt"
    source_file.write_bytes(b"expected")
    raw_root = tmp_path / "storage" / "raw"
    raw_root.mkdir(parents=True)
    digest = __import__("hashlib").sha256(b"expected").hexdigest()
    (raw_root / digest).write_bytes(b"corrupt")
    snapshot = ConsistentSnapshot(registry, raw_root)

    with pytest.raises(ValueError, match="content-addressed raw object"):
        snapshot.capture(source.source_id, source_file)
    assert list(raw_root.glob("*.conflict"))


def test_revoke_during_copy_never_commits_raw_object(tmp_path: Path):
    state, registry, source, root = _authorized_source(tmp_path)
    source_file = root / "revoked.txt"
    source_file.write_text("must not commit", encoding="utf-8")

    class RevokeDuringCopy(ConsistentSnapshot):
        def _copy_to_temp(self, source_path: Path, temporary: Path) -> None:
            super()._copy_to_temp(source_path, temporary)
            registry.revoke(source.source_id)

    snapshot = RevokeDuringCopy(registry, tmp_path / "storage" / "raw")

    with pytest.raises(PermissionError):
        snapshot.capture(source.source_id, source_file)
    assert list((tmp_path / "storage" / "raw").iterdir()) == []
