"""Bounded cleanup for adapter-dispatch files derived from durable raw input.

The files handled here are hard-link views of an already content-addressed raw
object.  They are never an authority: a job/lease identity in the filename is
checked against the existing extraction queue before a file can be removed.
"""

from __future__ import annotations

import re
import errno
import hashlib
import os
import socket
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


_SEGMENT_MAX_LENGTH = 64
_SEGMENT = rf"[A-Za-z0-9][A-Za-z0-9_-]{{0,{_SEGMENT_MAX_LENGTH - 1}}}"
_MARKER_RE = re.compile(rf"^\.automatic-memory-v1-({_SEGMENT})\.({_SEGMENT})(\.[A-Za-z0-9][A-Za-z0-9._-]{{0,31}})$")
_LEGACY_MARKER_RE = re.compile(r"^\.automatic-memory-([0-9a-fA-F]{32})(\.[A-Za-z0-9][A-Za-z0-9._-]{0,31})$")
_RAW_NAME_RE = re.compile(r"^[0-9a-f]{64}$")


class _QueueReadFailure(RuntimeError):
    """Internal sentinel used to keep queue/SQLite failures in the receipt."""


def _safe_segment(value: str, label: str) -> str:
    value = str(value or "")
    if re.fullmatch(_SEGMENT, value) is None:
        raise ValueError(f"automatic-memory {label} is not a bounded safe token")
    return value


def automatic_memory_dispatch_path(
    raw_root: Path | str, job_id: str, lease_token: str, suffix: str
) -> Path:
    """Return a direct-child marker name carrying the queue job and lease."""

    root = Path(raw_root).expanduser()
    suffix = str(suffix or "")
    if not re.fullmatch(r"\.[A-Za-z0-9][A-Za-z0-9._-]{0,31}", suffix):
        raise ValueError("automatic-memory dispatch suffix is not safe")
    job = _safe_segment(job_id, "job id")
    lease = _safe_segment(lease_token, "lease token")
    return root / f".automatic-memory-v1-{job}.{lease}{suffix}"


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        # SQLite queue timestamps historically use UTC-naive ISO strings.
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _queue_ownership(queue: Any, job_id: str, marker_lease_fingerprint: str) -> dict[str, Any] | None:
    """Read a queue ownership predicate without exposing lease material."""
    try:
        reader = getattr(queue, "ownership_receipt", None)
        if callable(reader):
            value = reader(job_id, marker_lease_fingerprint)
        else:
            value = queue.get(job_id)
            if not isinstance(value, dict):
                return None
            current = str(value.get("lease_token") or "")
            durable = str(value.get("last_claim_lease_fingerprint") or "").lower()
            value = {
                "status": value.get("status"),
                "input_path": value.get("input_path"),
                "locked_by": value.get("locked_by"),
                "heartbeat_at": value.get("heartbeat_at"),
                "locked_at": value.get("locked_at"),
                "current_lease_matches": bool(current and hashlib.sha256(current.encode()).hexdigest() == marker_lease_fingerprint),
                "durable_lease_matches": bool(durable and durable == marker_lease_fingerprint),
                "durable_lease_present": bool(durable),
            }
    except (LookupError, KeyError):
        return None
    except Exception as exc:
        raise _QueueReadFailure from exc
    return value if isinstance(value, dict) else None


def _identity(info: os.stat_result) -> tuple[int, int, int, int]:
    return (int(info.st_dev), int(info.st_ino), int(info.st_mode), int(info.st_size))


def _sha256(path: Path) -> str | None:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except Exception:
        return None
    return digest.hexdigest()


def _content_addressed_raw(root: Path, raw_path: Path) -> os.stat_result | None:
    """Return raw identity only for a safe direct-child content-addressed file."""
    if raw_path.parent != root or _RAW_NAME_RE.fullmatch(raw_path.name) is None:
        return None
    try:
        info = raw_path.lstat()
    except Exception:
        return None
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
        return None
    if _sha256(raw_path) != raw_path.name:
        return None
    return info


def _legacy_proof(root: Path, marker: Path, marker_info: os.stat_result) -> str | None:
    """Require a same-directory raw object to prove an old marker is derived."""
    content_match = False
    try:
        candidates = tuple(root.iterdir())
    except Exception:
        return "legacy_hardlink_proof_missing"
    for candidate in candidates:
        if candidate == marker or _RAW_NAME_RE.fullmatch(candidate.name) is None:
            continue
        raw_info = _content_addressed_raw(root, candidate)
        if raw_info is None:
            continue
        content_match = True
        if _identity(marker_info) == _identity(raw_info):
            return None
    return "identity_mismatch" if content_match else "legacy_hardlink_proof_missing"


def _v1_raw_proof(root: Path, marker_info: os.stat_result, job: dict[str, Any]) -> str | None:
    raw_value = job.get("input_path")
    if not isinstance(raw_value, (str, Path)) or not str(raw_value).strip():
        return "lease_unverifiable"
    try:
        raw_path = Path(raw_value).expanduser()
        raw_info = _content_addressed_raw(root, raw_path)
    except Exception:
        return "lease_unverifiable"
    if raw_info is None:
        return "lease_unverifiable"
    if _identity(marker_info) != _identity(raw_info):
        return "identity_mismatch"
    return None


def _remove_if_unchanged(
    entry: Path,
    initial_info: os.stat_result,
    report: dict[str, Any],
    reason: str,
) -> bool:
    """Re-check identity immediately before unlinking (M1)."""
    try:
        current_info = entry.lstat()
    except FileNotFoundError:
        return False
    except Exception:
        report["preserved"].append({"reason": "identity_changed"})
        return False
    if _identity(current_info) != _identity(initial_info):
        report["preserved"].append({"reason": "identity_changed"})
        return False
    try:
        entry.unlink()
    except FileNotFoundError:
        return False
    except Exception:
        report["errors"].append({"reason": "unlink_failed"})
        return False
    report["removed"].append({"reason": reason})
    return True


def _worker_is_provably_dead(worker_id: Any) -> bool:
    """Recognize only the pipeline's local ``hostname:pid`` worker identity."""
    value = str(worker_id or "")
    host, separator, pid_text = value.rpartition(":")
    if not separator or host != socket.gethostname() or not pid_text.isdigit():
        return False
    pid = int(pid_text)
    if pid <= 0 or pid == os.getpid():
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except OSError as exc:
        if exc.errno == errno.ESRCH:
            return True
        return False
    return False


def reconcile_automatic_memory_transients(
    raw_root: Path | str,
    queue: Any,
    *,
    stale_after_seconds: float = 1800,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Reconcile only direct-child, regular, LingJi-owned dispatch files.

    Unknown, malformed, foreign, active, symlink and directory entries are
    preserved.  An unlink exception is returned as an error and never counted
    as a removal, so callers can expose the receipt through existing runtime
    status/worker results and retry on the next reconciliation.
    """

    root = Path(raw_root).expanduser()
    report: dict[str, Any] = {
        "scanned_count": 0,
        "removed_count": 0,
        "preserved_count": 0,
        "removed": [],
        "preserved": [],
        "errors": [],
    }
    try:
        root_exists = root.exists()
        root_symlink = root.is_symlink()
        root_directory = root.is_dir()
    except Exception:
        report["errors"].append({"reason": "root_unavailable"})
        return report
    if not root_exists or root_symlink or not root_directory:
        return report
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    stale_after = timedelta(seconds=max(float(stale_after_seconds), 0.0))
    try:
        entries = tuple(root.iterdir())
    except Exception:
        report["errors"].append({"reason": "scan_failed"})
        return report

    for entry in entries:
        if not entry.name.startswith(".automatic-memory-"):
            continue
        report["scanned_count"] += 1
        try:
            info = entry.lstat()
        except FileNotFoundError:
            continue
        except Exception:
            report["preserved"].append({"reason": "lstat_failed"})
            continue
        if stat.S_ISLNK(info.st_mode):
            report["preserved"].append({"reason": "symlink"})
            continue
        if not stat.S_ISREG(info.st_mode):
            report["preserved"].append({"reason": "not_regular_file"})
            continue
        legacy = _LEGACY_MARKER_RE.fullmatch(entry.name)
        matched = _MARKER_RE.fullmatch(entry.name)
        if legacy is not None:
            proof_reason = _legacy_proof(root, entry, info)
            if proof_reason is not None:
                report["preserved"].append({"reason": proof_reason})
                continue
            _remove_if_unchanged(entry, info, report, "legacy_hardlink")
            continue
        if matched is None:
            report["preserved"].append({"reason": "unknown_marker"})
            continue
        job_id, lease_token, _suffix = matched.groups()
        marker_fingerprint = hashlib.sha256(lease_token.encode("utf-8")).hexdigest()
        try:
            job = _queue_ownership(queue, job_id, marker_fingerprint)
        except _QueueReadFailure:
            report["preserved"].append({"reason": "queue_read_failed"})
            report["errors"].append({"reason": "queue_read_failed"})
            continue
        if job is None:
            report["preserved"].append({"reason": "unknown_job"})
            continue
        status = str(job.get("status") or "")
        reason: str | None = None
        if not job.get("durable_lease_matches"):
            report["preserved"].append({"reason": "lease_unverifiable" if not job.get("durable_lease_present") else "lease_mismatch"})
            continue
        if status in {"completed", "failed", "cancelled"}:
            reason = "terminal_job"
        elif status in {"queued", "retrying"}:
            reason = "lease_released"
        elif status == "running":
            if not job.get("current_lease_matches"):
                report["preserved"].append({"reason": "lease_mismatch"})
                continue
            if _worker_is_provably_dead(job.get("locked_by")):
                reason = "dead_worker"
            else:
                heartbeat = _parse_timestamp(job.get("heartbeat_at"))
                locked = _parse_timestamp(job.get("locked_at"))
                lease_anchor = heartbeat or locked
                if lease_anchor is None or lease_anchor + stale_after > current_time:
                    report["preserved"].append({"reason": "active_lease"})
                    continue
                reason = "expired_lease"
        else:
            report["preserved"].append({"reason": "unknown_job_status"})
            continue
        proof_reason = _v1_raw_proof(root, info, job)
        if proof_reason is not None:
            report["preserved"].append({"reason": proof_reason})
            continue
        _remove_if_unchanged(entry, info, report, reason or "lease_released")

    report["removed_count"] = len(report["removed"])
    report["preserved_count"] = len(report["preserved"])
    return report


__all__ = ["automatic_memory_dispatch_path", "reconcile_automatic_memory_transients"]
