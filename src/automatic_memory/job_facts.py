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
    path = PurePosixPath(relative)
    return (
        bool(relative)
        and not any(ord(character) < 32 or ord(character) == 127 for character in relative)
        and not path.is_absolute()
        and path.as_posix() == relative
        and not any(part in {"", ".", ".."} for part in path.parts)
    )


def resolve_job_facts(
    *,
    source_id: str,
    direct_jobs: Iterable[dict[str, Any]] = (),
    associated_jobs: Iterable[tuple[dict[str, Any], str]] = (),
) -> list[dict[str, Any]]:
    """Validate, mark, and deterministically deduplicate snapshot job facts."""
    by_path: dict[tuple[str, str], dict[str, Any]] = {}
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
        relative_path = str(payload.get("relative_path") or "")
        key = (source_id, relative_path)
        current = by_path.get(key)
        candidate_order = (_updated_at(candidate.get("updated_at")), job_id)
        current_order = (
            _updated_at(current.get("updated_at")),
            str(current.get("job_id") or ""),
        ) if current is not None else None
        if current_order is None or candidate_order > current_order:
            by_path[key] = candidate
    return [by_path[key] for key in sorted(by_path)]


def summarize_job_facts(jobs: Iterable[dict[str, Any]]) -> dict[str, int]:
    """Derive scan-wide counts from the same authoritative per-path facts."""
    facts = list(jobs)
    statuses = [str(item.get("status") or "unknown").lower() for item in facts]
    new = sum(
        item.get("_automatic_memory_association") != "existing"
        for item in facts
    )
    reused = sum(
        status == "completed"
        and item.get("_automatic_memory_association") == "existing"
        for status, item in zip(statuses, facts)
    )
    imported = sum(
        status == "completed"
        and item.get("_automatic_memory_association") != "existing"
        for status, item in zip(statuses, facts)
    )
    return {
        "total": len(facts),
        "new": new,
        "reused": reused,
        "imported": imported,
        "completed": sum(status == "completed" for status in statuses),
        "failed": sum(status in {"failed", "cancelled"} for status in statuses),
        "pending": sum(status not in {"completed", "failed", "cancelled"} for status in statuses),
    }


def association_from_status(status: Any) -> tuple[str, str] | None:
    parts = str(status or "").split(":")
    if len(parts) != 3 or parts[0] != "job" or not parts[1] or parts[2] not in {"new", "existing"}:
        return None
    return parts[1], parts[2]
