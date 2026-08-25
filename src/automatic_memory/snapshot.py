from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat as stat_module
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from src.extraction.sink import VaultExtractionSink
from src.storage import StateDatabase


@dataclass(frozen=True)
class FileStat:
    size: int
    mtime_ns: int
    inode: int | None


@dataclass(frozen=True)
class SnapshotResult:
    source_id: str
    relative_path: str
    raw_id: str
    sha256: str
    stat_before: FileStat
    stat_after: FileStat
    stable: bool
    attempt: int


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ConsistentSnapshot:
    """Copy one authorized ordinary file without observing a torn write."""

    def __init__(
        self,
        registry_or_state: Any | None = None,
        raw_root: Path | str | None = None,
        *,
        registry: Any | None = None,
        source_registry: Any | None = None,
        state_db: StateDatabase | None = None,
        storage_path: Path | str | None = None,
        storage_root: Path | str | None = None,
        sink: Any | None = None,
        before_raw_commit: Any | None = None,
    ):
        selected = registry_or_state or registry or source_registry or state_db
        if selected is None:
            raise TypeError("registry or state_db is required")
        self.registry = selected
        self.state_db: StateDatabase = getattr(selected, "state_db", selected)
        if sink is not None:
            self._sink = sink
            self.raw_root = Path(getattr(sink, "raw_root"))
        else:
            selected_root = raw_root or storage_path or storage_root
            if selected_root is None:
                raise TypeError("raw_root or storage_path is required")
            self.raw_root = Path(selected_root).expanduser()
            if (storage_path is not None or storage_root is not None) and raw_root is None:
                self.raw_root = self.raw_root / "raw"
            self._sink = VaultExtractionSink.__new__(VaultExtractionSink)
            self._sink.raw_root = self.raw_root
        self.raw_root.mkdir(parents=True, exist_ok=True)
        self.before_raw_commit = before_raw_commit
        self._copy_source_fd: int | None = None

    def capture(
        self,
        source_id: str,
        path: Path | str,
        max_attempts: int = 3,
        *,
        scan_id: str | None = None,
        lease_id: str | None = None,
        lease_guard: Callable[[], None] | None = None,
    ) -> SnapshotResult:
        root, relative = self._authorized_path(source_id, Path(path).expanduser())
        source = root / Path(relative)
        attempts = max(int(max_attempts), 1)
        last_before: FileStat | None = None
        last_after: FileStat | None = None
        last_digest = ""
        for attempt in range(1, attempts + 1):
            # Recheck authorization and path policy on every retry. A revoked
            # grant must not finish a copy that began while it was authorized.
            root, relative = self._authorized_path(source_id, source)
            source = root / Path(relative)
            stat_before = self._file_stat(source)
            last_before = stat_before
            temporary = self._temporary_path()
            try:
                source_fd = self._secure_open_source(root, relative)
                self._copy_source_fd = source_fd
                self._copy_to_temp(source, temporary)
                os.close(source_fd)
                self._copy_source_fd = None
                last_digest = self._sha256_file(temporary)
                self._fsync_directory(temporary.parent)
                stat_after = self._file_stat(source)
                last_after = stat_after
                stable = stat_before == stat_after
                if stable:
                    self._authorized_path(source_id, source)
                    if lease_guard is not None:
                        lease_guard()
                    if self.before_raw_commit is not None:
                        self.before_raw_commit()
                    def commit() -> None:
                        if lease_guard is not None:
                            lease_guard()
                        self._sink.commit_raw_temp(temporary, last_digest)
                    if scan_id and lease_id:
                        self.state_db.commit_authorized_snapshot(
                            scan_id, lease_id, str(source_id), commit
                        )
                    else:
                        commit()
                    return SnapshotResult(
                        source_id=str(source_id),
                        relative_path=relative,
                        raw_id=last_digest,
                        sha256=last_digest,
                        stat_before=stat_before,
                        stat_after=stat_after,
                        stable=True,
                        attempt=attempt,
                    )
                temporary.unlink(missing_ok=True)
            except Exception as exc:
                if self._copy_source_fd is not None:
                    try:
                        os.close(self._copy_source_fd)
                    except OSError:
                        pass
                    self._copy_source_fd = None
                if isinstance(exc, ValueError) and "content-addressed raw object" in str(exc):
                    temporary.unlink(missing_ok=True)
                    if scan_id and lease_id:
                        actual_match = re.search(r"has SHA-256\s+([0-9a-f]{64})", str(exc))
                        actual = actual_match.group(1) if actual_match else "unknown"
                        diagnostic = (
                            f"raw conflict target={self.raw_root / last_digest}; "
                            f"expected={last_digest}; actual={actual}; detail={str(exc)[:1200]}"
                        )
                        try:
                            self.state_db.update_automatic_memory_scan_owned(
                                scan_id,
                                lease_id,
                                last_error=diagnostic,
                            )
                        except Exception:
                            pass
                else:
                    temporary.unlink(missing_ok=True)
                raise
        assert last_before is not None and last_after is not None
        return SnapshotResult(
            source_id=str(source_id),
            relative_path=relative,
            raw_id="",
            sha256=last_digest,
            stat_before=last_before,
            stat_after=last_after,
            stable=False,
            attempt=attempts,
        )

    def _authorized_path(self, source_id: str, path: Path) -> tuple[Path, str]:
        source = self.state_db.get_automatic_memory_source(
            str(source_id), now=_now_iso()
        )
        if source is None:
            raise PermissionError("source is not authorized for snapshot capture")
        if source.get("status") != "authorized":
            raise PermissionError("source authorization is not active")
        grant = self.state_db.get_automatic_memory_grant(str(source["grant_id"]))
        if not grant or not bool(grant.get("owner_confirmed")):
            raise PermissionError("owner authorization is required")
        expires_at = grant.get("expires_at")
        if expires_at and expires_at <= _now_iso():
            raise PermissionError("source authorization has expired")

        root = Path(source["root"]).expanduser()
        root_abs = Path(os.path.abspath(os.path.normpath(str(root))))
        if root_abs.is_symlink() or not root_abs.is_dir():
            raise PermissionError("authorized source root must be a real directory")
        path_abs = Path(os.path.abspath(os.path.normpath(str(path))))
        try:
            relative = path_abs.relative_to(root_abs).as_posix()
        except ValueError as exc:
            raise PermissionError("snapshot path escapes the authorized source root") from exc
        if not relative or path_abs.is_symlink():
            raise PermissionError("symbolic-link snapshot paths are not allowed")
        current = path_abs
        while current != root_abs:
            if current.is_symlink():
                raise PermissionError("symbolic-link snapshot paths are not allowed")
            current = current.parent
        if not path_abs.exists():
            raise FileNotFoundError(path_abs)
        if not path_abs.is_file():
            raise ValueError("snapshot path must be an ordinary file")
        return root_abs, relative

    @staticmethod
    def _file_stat(path: Path) -> FileStat:
        stat = path.lstat()
        if stat_module.S_ISLNK(stat.st_mode):
            raise PermissionError("symbolic-link snapshot paths are not allowed")
        if not stat_module.S_ISREG(stat.st_mode):
            raise ValueError("snapshot path must be an ordinary file")
        return FileStat(
            size=int(stat.st_size),
            mtime_ns=int(stat.st_mtime_ns),
            inode=int(getattr(stat, "st_ino", 0)) or None,
        )

    def _temporary_path(self) -> Path:
        fd, name = tempfile.mkstemp(prefix=".snapshot-", suffix=".tmp", dir=self.raw_root)
        os.close(fd)
        return Path(name)

    @staticmethod
    def _secure_open_source(root: Path, relative: str) -> int:
        """Open an authorized path without following a replaceable component."""
        nofollow = getattr(os, "O_NOFOLLOW", None)
        directory = getattr(os, "O_DIRECTORY", 0)
        if nofollow is None or not hasattr(os, "supports_dir_fd") or os.open not in os.supports_dir_fd:
            raise PermissionError("platform cannot safely open authorized snapshot paths")
        parts = tuple(part for part in Path(relative).parts if part not in {"", "."})
        if not parts or any(part == ".." for part in parts):
            raise PermissionError("snapshot path escapes the authorized source root")
        root_fd = os.open(root, os.O_RDONLY | directory | nofollow)
        current_fd = root_fd
        try:
            for part in parts[:-1]:
                next_fd = os.open(
                    part,
                    os.O_RDONLY | directory | nofollow,
                    dir_fd=current_fd,
                )
                if current_fd != root_fd:
                    os.close(current_fd)
                current_fd = next_fd
            return os.open(parts[-1], os.O_RDONLY | nofollow, dir_fd=current_fd)
        finally:
            os.close(current_fd)
            if current_fd != root_fd:
                os.close(root_fd)

    def _copy_to_temp(self, source: Path, temporary: Path) -> None:
        if self._copy_source_fd is None:
            raise PermissionError("authorized source descriptor is not available")
        source_handle = os.fdopen(os.dup(self._copy_source_fd), "rb", closefd=True)
        with source_handle, temporary.open("wb") as temp_handle:
            shutil.copyfileobj(source_handle, temp_handle, length=1024 * 1024)
            temp_handle.flush()
            os.fsync(temp_handle.fileno())

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        try:
            fd = os.open(path, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError:
            pass


__all__ = ["ConsistentSnapshot", "FileStat", "SnapshotResult"]
