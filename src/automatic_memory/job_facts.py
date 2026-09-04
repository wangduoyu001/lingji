from __future__ import annotations

from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any, Iterable


def _updated_at(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _valid_payload(payload: Any, source_id: str) -> bool:
    if not isinstance(payload, dict) or str(payload.get("source_id") or "") != source_id:
        return False
    relative = str(payload.get("relative_path") or "")
    return bool(relative) and not PurePosixPath(relative).is_absolute() and PurePosixPath(relative).as_posix() == relative and ".." not in PurePosixPath(relative).parts


def resolve_job_facts(
    *,
    source_id: str,
    direct_jobs: Iterable[dict[str, Any]] = (),
    associated_jobs: Iterable[tuple[dict[str, Any], str]] = (),
) -> list[dict[str, Any]]:
    """Validate, mark, and deterministically deduplicate snapshot job facts."""
    by_id: dict[str, dict[str, Any]] = {}
    candidates = [(job, "new") for job in direct_jobs] + list(associated_jobs)
    for job, association in candidates:
        if not isinstance(job, dict) or str(job.get("source_type") or "") != "automatic_memory_snapshot":
            continue
        payload = job.get("payload")
        if not _valid_payload(payload, source_id):
            continue
        job_id = str(job.get("job_id") or "")
        if not job_id:
            continue
        candidate = dict(job)
        candidate["_automatic_memory_association"] = association
        current = by_id.get(job_id)
        if current is None or (_updated_at(candidate.get("updated_at")), job_id) > (_updated_at(current.get("updated_at")), job_id):
            by_id[job_id] = candidate
    return list(by_id.values())


def association_from_status(status: Any) -> tuple[str, str] | None:
    parts = str(status or "").split(":")
    if len(parts) != 3 or parts[0] != "job" or not parts[1] or parts[2] not in {"new", "existing"}:
        return None
    return parts[1], parts[2]
