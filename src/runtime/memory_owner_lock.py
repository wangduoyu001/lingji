from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO


class MemoryOwnerLockError(RuntimeError):
    """Raised when another process still owns the live memory runtime."""


class MemoryOwnerLock:
    """Cross-platform exclusive process lock for SQLite/Qdrant live ownership.

    The operating system lock and human-readable diagnostics use separate files.
    Windows may deny a second reader while an ``msvcrt`` byte-range lock is held,
    so ``*.lock`` is only the mutex and ``*.json`` remains readable by diagnostics.
    Both are task-local and contain no private content.
    """

    def __init__(
        self,
        path: Path | str,
        *,
        owner: str,
        instance_id: str,
        workspace: str,
        timeout_seconds: float = 15.0,
        poll_seconds: float = 0.2,
    ) -> None:
        self.path = Path(path).expanduser().resolve(strict=False)
        self.metadata_path = self.path.with_suffix(".json")
        self.owner = str(owner or "memory_runtime")
        self.instance_id = str(instance_id or "unknown")
        self.workspace = str(workspace or "unknown")
        self.timeout_seconds = max(float(timeout_seconds), 0.0)
        self.poll_seconds = max(float(poll_seconds), 0.05)
        self._file: BinaryIO | None = None

    @property
    def held(self) -> bool:
        return self._file is not None

    def acquire(self) -> "MemoryOwnerLock":
        if self._file is not None:
            return self
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b", buffering=0)
        if self.path.stat().st_size == 0:
            handle.write(b"\0")
            handle.flush()
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                self._lock(handle)
                break
            except (BlockingIOError, OSError) as exc:
                if time.monotonic() >= deadline:
                    detail = self._diagnostic_text()
                    handle.close()
                    raise MemoryOwnerLockError(
                        "Another LingJi memory runtime owns the embedded store"
                        + (f": {detail}" if detail else "")
                    ) from exc
                time.sleep(self.poll_seconds)
        self._file = handle
        self._write_metadata()
        return self

    def release(self) -> None:
        handle = self._file
        if handle is None:
            return
        try:
            self._unlock(handle)
        finally:
            handle.close()
            self._file = None
            self._mark_released()

    def __enter__(self) -> "MemoryOwnerLock":
        return self.acquire()

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.release()

    def _metadata_payload(self, *, released_at: str | None = None) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": 1,
            "owner": self.owner,
            "instance_id": self.instance_id,
            "workspace": self.workspace,
            "pid": os.getpid(),
            "state": "released" if released_at else "held",
            "acquired_at": datetime.now(timezone.utc).isoformat(),
        }
        if released_at:
            payload["released_at"] = released_at
        return payload

    def _write_metadata(self) -> None:
        self._write_metadata_payload(self._metadata_payload())

    def _mark_released(self) -> None:
        released_at = datetime.now(timezone.utc).isoformat()
        payload = self._read_metadata()
        if not payload:
            payload = self._metadata_payload(released_at=released_at)
        else:
            payload["state"] = "released"
            payload["released_at"] = released_at
        try:
            self._write_metadata_payload(payload)
        except OSError:
            pass

    def _write_metadata_payload(self, payload: dict[str, object]) -> None:
        temporary = self.metadata_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.metadata_path)

    def _read_metadata(self) -> dict[str, object]:
        try:
            raw = self.metadata_path.read_text(encoding="utf-8-sig").strip()
            payload = json.loads(raw)
            return dict(payload) if isinstance(payload, dict) else {}
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return {}

    def _diagnostic_text(self) -> str:
        payload = self._read_metadata()
        return ", ".join(
            part
            for part in (
                f"owner={payload.get('owner')}" if payload.get("owner") else "",
                f"pid={payload.get('pid')}" if payload.get("pid") else "",
                f"workspace={payload.get('workspace')}" if payload.get("workspace") else "",
                f"state={payload.get('state')}" if payload.get("state") else "",
            )
            if part
        )

    @staticmethod
    def _lock(handle: BinaryIO) -> None:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    @staticmethod
    def _unlock(handle: BinaryIO) -> None:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
            return
        import fcntl

        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
