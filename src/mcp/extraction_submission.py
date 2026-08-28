from __future__ import annotations

from typing import Any, Mapping

from src.extraction.queue import _without_lease_material

_SENSITIVE_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)


def validate_codex_work_report(report: Mapping[str, Any]) -> dict[str, Any]:
    """Validate durable Work Report identity and shape before queue submission."""

    if not isinstance(report, Mapping):
        raise ValueError("Codex work report must be an object")
    normalized = dict(report)
    for field in ("task_id", "execution_id", "repository", "branch"):
        value = str(normalized.get(field) or "").strip()
        if not value:
            raise ValueError(f"Codex work report {field} is required")
        normalized[field] = value

    for field in ("commits", "changed_files", "tests"):
        value = normalized.get(field)
        if not isinstance(value, list):
            raise ValueError(f"Codex work report {field} must be a list")

    if not all(isinstance(item, (str, Mapping)) for item in normalized["commits"]):
        raise ValueError("Codex work report commits must contain strings or objects")
    if not all(isinstance(item, (str, Mapping)) for item in normalized["changed_files"]):
        raise ValueError("Codex work report changed_files must contain strings or objects")
    if not all(isinstance(item, (str, Mapping)) for item in normalized["tests"]):
        raise ValueError("Codex work report tests must contain strings or objects")

    sensitive_path = find_sensitive_key(normalized)
    if sensitive_path:
        raise ValueError(f"Sensitive field is not allowed in Codex work report: {sensitive_path}")
    return normalized


def find_sensitive_key(value: Any, *, path: str = "report") -> str | None:
    if isinstance(value, Mapping):
        for raw_key, item in value.items():
            key = str(raw_key)
            normalized = key.strip().lower().replace("-", "_")
            if any(fragment in normalized for fragment in _SENSITIVE_KEY_FRAGMENTS):
                return f"{path}.{key}"
            found = find_sensitive_key(item, path=f"{path}.{key}")
            if found:
                return found
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            found = find_sensitive_key(item, path=f"{path}[{index}]")
            if found:
                return found
    return None


def durable_job_response(job: Mapping[str, Any], *, message: str | None = None) -> dict[str, Any]:
    """Return a truthful queue DTO while preserving backwards-compatible job fields."""

    raw_payload = dict(job)
    lease_values = tuple(
        str(raw_payload.get(key) or "")
        for key in ("lease_token", "last_claim_lease_fingerprint")
    )
    payload = _without_lease_material(raw_payload, redact_values=lease_values)
    # Queue internals may include the current plaintext lease and its durable
    # fingerprint for worker/pipeline coordination. Neither is an API fact.
    payload.pop("lease_token", None)
    payload.pop("last_claim_lease_fingerprint", None)
    status = str(payload.get("status") or "unknown")
    existing_job = bool(payload.get("existing_job"))
    attempts = max(int(payload.get("attempts") or 0), 0)
    payload.update(
        {
            "job_id": payload.get("job_id"),
            "status": status,
            "idempotency_key": payload.get("idempotency_key"),
            "source_type": payload.get("source_type"),
            "adapter_name": payload.get("adapter_name"),
            "created_at": payload.get("created_at"),
            "existing_job": existing_job,
            "retry_count": max(attempts - 1, 0),
            "message": message
            or ("Existing durable extraction job reused" if existing_job else "Durable extraction job queued"),
        }
    )
    return payload


def enqueue_durable_submission(
    pipeline: Any,
    source_type: str,
    *,
    payload: Mapping[str, Any],
    options: Mapping[str, Any] | None,
    adapter_name: str,
    force: bool = False,
    process_now: bool = False,
) -> dict[str, Any]:
    """Always create/reuse a durable job before optional synchronous processing."""

    job = pipeline.enqueue(
        source_type,
        payload=dict(payload),
        options=dict(options or {}),
        adapter_name=adapter_name,
        force=force,
    )
    if not process_now:
        return durable_job_response(job)

    outcome = pipeline.process_job(str(job["job_id"]))
    processed_job = dict(outcome.get("job") or pipeline.queue.get(job["job_id"]))
    response = durable_job_response(
        processed_job,
        message="Durable extraction job processed through the queue",
    )
    if "result" in outcome:
        response["result"] = outcome.get("result") or {}
    if outcome.get("error"):
        response["error"] = str(outcome["error"])
    if outcome.get("lease_error"):
        response["lease_error"] = str(outcome["lease_error"])
    return response


__all__ = [
    "durable_job_response",
    "enqueue_durable_submission",
    "find_sensitive_key",
    "validate_codex_work_report",
]
