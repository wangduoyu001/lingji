from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.runtime.memory_owner_lock import MemoryOwnerLock, MemoryOwnerLockError


def test_memory_owner_lock_is_exclusive_and_recoverable(tmp_path: Path) -> None:
    path = tmp_path / "runtime" / "memory-owner.lock"
    first = MemoryOwnerLock(
        path,
        owner="mcp",
        instance_id="first",
        workspace="acceptance",
        timeout_seconds=0.1,
        poll_seconds=0.05,
    ).acquire()
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
        assert metadata["owner"] == "mcp"
        assert metadata["instance_id"] == "first"
        assert metadata["workspace"] == "acceptance"

        second = MemoryOwnerLock(
            path,
            owner="mcp",
            instance_id="second",
            workspace="acceptance",
            timeout_seconds=0.1,
            poll_seconds=0.05,
        )
        with pytest.raises(MemoryOwnerLockError, match="owns the embedded store"):
            second.acquire()
    finally:
        first.release()

    recovered = MemoryOwnerLock(
        path,
        owner="mcp",
        instance_id="recovered",
        workspace="acceptance",
        timeout_seconds=0.2,
    ).acquire()
    try:
        assert recovered.held is True
        metadata = json.loads(path.read_text(encoding="utf-8"))
        assert metadata["instance_id"] == "recovered"
    finally:
        recovered.release()


def test_release_is_idempotent(tmp_path: Path) -> None:
    lock = MemoryOwnerLock(
        tmp_path / "owner.lock",
        owner="mcp",
        instance_id="one",
        workspace="production",
    )
    lock.acquire()
    lock.release()
    lock.release()
    assert lock.held is False
