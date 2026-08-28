"""Bounded cleanup for adapter-dispatch files derived from durable raw input.

The files handled here are hard-link views of an already content-addressed raw
object.  They are never an authority: a job/lease identity in the filename is
checked against the existing extraction queue before a file can be removed.
"""

from __future__ import annotations

import re
import errno
import os
import socket
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


_SEGMENT_MAX_LENGTH = 64
_SEGMENT = rf"[A-Za-z0-9][A-Za-z0-9_-]{{0,{_SEGMENT_MAX_LENGTH - 1}}}"
_MARKER_RE = re.compile(rf"^\.automatic-memory-v1-({_SEGMENT})\.({_SEGMENT})(\.[A-Za-z0-9][A-Za-z0-9._-]{{0,31}})$")


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


def _queue_job(queue: Any, job_id: str) -> dict[str, Any] | None:
    try:
        value = queue.get(job_id)
    except (LookupError, KeyError):
        return None
    return value if isinstance(value, dict) else None


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
        "root": root.name,
        "scanned_count": 0,
        "removed_count": 0,
        "preserved_count": 0,
        "removed": [],
        "preserved": [],
        "errors": [],
    }
    if not root.exists() or root.is_symlink() or not root.is_dir():
        return report
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    stale_after = timedelta(seconds=max(float(stale_after_seconds), 0.0))
    try:
        entries = tuple(root.iterdir())
    except OSError as exc:
        report["errors"].append({"name": root.name, "reason": "scan_failed", "error": str(exc)[:500]})
        return report

    for entry in entries:
        if not entry.name.startswith(".automatic-memory-"):
            continue
        report["scanned_count"] += 1
        try:
            info = entry.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            report["preserved"].append({"name": entry.name, "reason": "symlink"})
            continue
        if not stat.S_ISREG(info.st_mode):
            report["preserved"].append({"name": entry.name, "reason": "not_regular_file"})
            continue
        matched = _MARKER_RE.fullmatch(entry.name)
        if matched is None:
            report["preserved"].append({"name": entry.name, "reason": "unknown_marker"})
            continue
        job_id, lease_token, _suffix = matched.groups()
        job = _queue_job(queue, job_id)
        if job is None:
            report["preserved"].append({"name": entry.name, "reason": "unknown_job"})
            continue
        status = str(job.get("status") or "")
        reason: str | None = None
        if status in {"completed", "failed", "cancelled"}:
            reason = "terminal_job"
        elif status in {"queued", "retrying"}:
            # A marker is only made after claim.  A released lease is therefore
            # no longer an active dispatch and can be rebuilt from durable raw.
            reason = "lease_released"
        elif status == "running":
            current_lease = str(job.get("lease_token") or "")
            if current_lease != lease_token:
                report["preserved"].append({"name": entry.name, "reason": "lease_mismatch"})
                continue
            if _worker_is_provably_dead(job.get("locked_by")):
                reason = "dead_worker"
            else:
                heartbeat = _parse_timestamp(job.get("heartbeat_at"))
                locked = _parse_timestamp(job.get("locked_at"))
                lease_anchor = heartbeat or locked
                if lease_anchor is None or lease_anchor + stale_after > current_time:
                    report["preserved"].append({"name": entry.name, "reason": "active_lease"})
                    continue
                reason = "expired_lease"
        else:
            report["preserved"].append({"name": entry.name, "reason": "unknown_job_status"})
            continue
        try:
            entry.unlink()
        except FileNotFoundError:
            continue
        except OSError as exc:
            report["errors"].append({"name": entry.name, "reason": "unlink_failed", "error": str(exc)[:500]})
            continue
        report["removed"].append({"name": entry.name, "reason": reason})

    report["removed_count"] = len(report["removed"])
    report["preserved_count"] = len(report["preserved"])
    return report


__all__ = ["automatic_memory_dispatch_path", "reconcile_automatic_memory_transients"]
