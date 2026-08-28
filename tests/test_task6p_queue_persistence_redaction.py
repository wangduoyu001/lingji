from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from src.extraction.queue import SQLiteExtractionQueue, _without_lease_material
from src.extraction.base import ExtractionAdapter
from src.extraction.models import ExtractedDocument, ExtractionBatch
from src.extraction.pipeline import ExtractionPipeline
from src.extraction.registry import AdapterRegistry
from src.extraction.sink import VaultExtractionSink
from src.memory import VaultLayout
from src.mcp.extraction_submission import durable_job_response


def _queue(tmp_path: Path) -> SQLiteExtractionQueue:
    return SQLiteExtractionQueue(tmp_path / "state.db")


def _claimed(queue: SQLiteExtractionQueue, key: str) -> dict:
    job = queue.enqueue("codex", payload={"message": "token is ordinary text"}, idempotency_key=key)
    claimed = queue.claim("worker", job_id=job["job_id"])
    assert claimed is not None
    return claimed


def _raw(queue: SQLiteExtractionQueue, job_id: str) -> dict:
    with sqlite3.connect(queue.path) as connection:
        row = connection.execute(
            "SELECT payload_json, options_json, result_json, last_error, lease_token, last_claim_lease_fingerprint "
            "FROM extraction_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
    assert row is not None
    return dict(zip(("payload_json", "options_json", "result_json", "last_error", "lease_token", "fingerprint"), row))


def _assert_public_material_absent(queue: SQLiteExtractionQueue, claimed: dict) -> None:
    token = claimed["lease_token"]
    fingerprint = queue.lease_fingerprint(token)
    reads = [
        queue.get(claimed["job_id"]),
        queue.list()[0],
        queue.list_page(limit=10)[0],
        queue.get_by_idempotency_key(claimed["idempotency_key"]),
    ]
    for read in reads:
        encoded = json.dumps(read, ensure_ascii=False, sort_keys=True)
        assert "lease_token" not in encoded
        assert "last_claim_lease_fingerprint" not in encoded
        assert token not in encoded
        assert fingerprint not in encoded
    response = durable_job_response(reads[0])
    encoded = json.dumps(response, ensure_ascii=False, sort_keys=True)
    assert token not in encoded
    assert fingerprint not in encoded


def test_terminal_complete_scrubs_nested_result_before_clearing_current_lease(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    claimed = _claimed(queue, "complete-redaction")
    token = claimed["lease_token"]
    fingerprint = queue.lease_fingerprint(token)
    result = {
        "nested": {
            "lease_token": token,
            "last_claim_lease_fingerprint": fingerprint,
            "message": f"completed with {token} and {fingerprint}",
        },
        "chat": "token is ordinary text",
    }

    completed = queue.complete(claimed["job_id"], result, worker_id="worker", lease_token=token)

    encoded = json.dumps(completed, ensure_ascii=False)
    assert token not in encoded
    assert fingerprint not in encoded
    assert completed["result"]["nested"]["message"] == "completed with [REDACTED] and [REDACTED]"
    assert completed["result"]["chat"] == "token is ordinary text"
    raw = _raw(queue, claimed["job_id"])
    assert token not in (raw["result_json"] or "")
    assert fingerprint not in (raw["result_json"] or "")
    _assert_public_material_absent(queue, claimed)


def test_terminal_fail_scrubs_error_and_retrying_fail_scrubs_persisted_error(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    for key, terminal in (("fail-terminal-redaction", True), ("fail-retry-redaction", False)):
        claimed = _claimed(queue, key)
        token = claimed["lease_token"]
        fingerprint = queue.lease_fingerprint(token)
        failed = queue.fail(
            claimed["job_id"],
            f"failure {token} with fingerprint {fingerprint}",
            worker_id="worker",
            lease_token=token,
            terminal=terminal,
            retry_delay_seconds=0,
        )
        assert token not in json.dumps(failed, ensure_ascii=False)
        assert fingerprint not in json.dumps(failed, ensure_ascii=False)
        raw = _raw(queue, claimed["job_id"])
        assert token not in (raw["last_error"] or "")
        assert fingerprint not in (raw["last_error"] or "")
        _assert_public_material_absent(queue, claimed)


def test_enqueue_scrubs_explicit_lease_keys_in_payload_and_options(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    job = queue.enqueue(
        "codex",
        payload={"nested": {"lease_token": "caller-material", "message": "token is ordinary text"}},
        options={"claim-lease-fingerprint": "caller-fingerprint"},
        idempotency_key="enqueue-redaction",
    )
    raw = _raw(queue, job["job_id"])
    assert "lease_token" not in (raw["payload_json"] or "")
    assert "claim-lease-fingerprint" not in (raw["options_json"] or "")
    assert "caller-material" not in (raw["payload_json"] or "")
    assert "caller-fingerprint" not in (raw["options_json"] or "")
    assert job["payload"]["nested"]["message"] == "token is ordinary text"


def test_cancel_running_scrubs_reason_before_clearing_current_lease(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    claimed = _claimed(queue, "cancel-redaction")
    token = claimed["lease_token"]
    fingerprint = queue.lease_fingerprint(token)
    cancelled = queue.cancel_running(
        claimed["job_id"],
        worker_id="worker",
        lease_token=token,
        reason=f"cancelled {token} {fingerprint}",
    )
    assert token not in json.dumps(cancelled, ensure_ascii=False)
    assert fingerprint not in json.dumps(cancelled, ensure_ascii=False)
    raw = _raw(queue, claimed["job_id"])
    assert token not in (raw["last_error"] or "")
    assert fingerprint not in (raw["last_error"] or "")


def test_persistence_scrubber_is_bounded_and_does_not_use_repr_or_generic_token_matching() -> None:
    token = "lease-material-123"
    cyclic: dict[str, object] = {"message": f"value {token}"}
    cyclic["self"] = cyclic
    scrubbed = _without_lease_material(cyclic, redact_values=(token,))
    assert scrubbed["message"] == "value [REDACTED]"
    assert scrubbed["self"] == "[REDACTED]"
    deeply_nested: object = "safe"
    for _ in range(100):
        deeply_nested = [deeply_nested]
    bounded = _without_lease_material(deeply_nested, redact_values=(token,))
    json.dumps(bounded, ensure_ascii=False)
    oversized = _without_lease_material(["safe"] * 20_000, redact_values=(token,))
    assert len(oversized) <= 10_001
    assert all(item == "safe" or item == "[REDACTED]" for item in oversized)
    assert _without_lease_material({"message": "token and secret are ordinary words"})["message"] == (
        "token and secret are ordinary words"
    )


class _CallbackAdapter(ExtractionAdapter):
    name = "callback"
    version = "1"
    source_types = ("callback",)

    def extract(self, request):
        return ExtractionBatch(
            documents=(
                ExtractedDocument(
                    stable_id="callback-doc",
                    title="callback",
                    body="# callback",
                    source_type="callback",
                ),
            )
        )


def _pipeline(tmp_path: Path) -> ExtractionPipeline:
    layout = VaultLayout(tmp_path / "vault")
    layout.ensure()
    registry = AdapterRegistry()
    registry.register(_CallbackAdapter())
    return ExtractionPipeline(
        SQLiteExtractionQueue(tmp_path / "state.db"),
        registry,
        VaultExtractionSink(layout, tmp_path / "storage"),
    )


def _assert_callback_safe(callback_value: tuple, token: str, fingerprint: str) -> None:
    encoded = json.dumps(callback_value, ensure_ascii=False, default=str)
    assert token not in encoded
    assert fingerprint not in encoded
    assert "lease_token" not in encoded
    assert "last_claim_lease_fingerprint" not in encoded


def test_process_next_success_callback_receives_safe_job_and_nested_result_copy(tmp_path: Path) -> None:
    pipeline = _pipeline(tmp_path)
    job = pipeline.enqueue("callback", payload={"message": "token is ordinary text"})
    seen: list[tuple] = []
    pipeline.add_lifecycle_callback(lambda phase, callback_job, result, error: seen.append((phase, callback_job, result, error)))
    original_execute = pipeline.execute
    materials: list[str] = []

    def execute_with_material(*args, **kwargs):
        del args, kwargs
        claimed = pipeline.queue._get_claimed_job_internal(job["job_id"])
        token = claimed["lease_token"]
        fingerprint = pipeline.queue.lease_fingerprint(token)
        materials.extend((token, fingerprint))
        return {"nested": [{"lease_token": token, "message": f"{token} {fingerprint}"}]}

    pipeline.execute = execute_with_material
    outcome = pipeline.process_job(job["job_id"], worker_id="callback-worker")
    pipeline.execute = original_execute

    assert outcome["job"]["status"] == "completed"
    assert len(seen) == 1
    _assert_callback_safe(seen[0], materials[0], materials[1])
    assert seen[0][0] == "completed"
    assert seen[0][1]["payload"]["message"] == "token is ordinary text"


def test_process_next_failure_callback_redacts_known_token_and_error(tmp_path: Path) -> None:
    pipeline = _pipeline(tmp_path)
    job = pipeline.enqueue("callback", payload={})
    seen: list[tuple] = []
    pipeline.add_lifecycle_callback(lambda phase, callback_job, result, error: seen.append((phase, callback_job, result, error)))
    claimed_token: list[str] = []

    def execute_with_failure(*args, **kwargs):
        del args, kwargs
        token = pipeline.queue._get_claimed_job_internal(job["job_id"])["lease_token"]
        claimed_token.append(token)
        raise RuntimeError(f"failed with {token}")

    pipeline.execute = execute_with_failure
    outcome = pipeline.process_job(job["job_id"], worker_id="callback-worker")

    assert outcome["job"]["status"] in {"retrying", "failed"}
    assert len(seen) == 1
    token = claimed_token[0]
    _assert_callback_safe(seen[0], token, pipeline.queue.lease_fingerprint(token))
    assert seen[0][3] == "failed with [REDACTED]"


def test_direct_execute_callback_scrubs_nested_explicit_lease_payload(tmp_path: Path) -> None:
    pipeline = _pipeline(tmp_path)
    seen: list[tuple] = []
    pipeline.add_lifecycle_callback(lambda phase, callback_job, result, error: seen.append((phase, callback_job, result, error)))
    pipeline.execute(
        "callback",
        payload={"nested": [{"lease_token": "direct-token", "message": "token is ordinary text"}]},
        execution_id="direct-execute",
    )
    assert len(seen) == 1
    encoded = json.dumps(seen[0], ensure_ascii=False, default=str)
    assert "direct-token" not in encoded
    assert "lease_token" not in encoded
    assert seen[0][1]["payload"]["nested"][0]["message"] == "token is ordinary text"


def test_automatic_snapshot_callback_scrubs_claimed_job_without_rolling_back_terminal_state(tmp_path: Path) -> None:
    pipeline = _pipeline(tmp_path)
    job = pipeline.queue.enqueue("automatic_memory_snapshot", payload={"message": "token is ordinary text"})
    seen: list[tuple] = []
    pipeline.add_lifecycle_callback(lambda phase, callback_job, result, error: seen.append((phase, callback_job, result, error)))
    materials: list[str] = []

    def execute_snapshot(claimed):
        token = claimed["lease_token"]
        materials.extend((token, pipeline.queue.lease_fingerprint(token)))
        return {"message": f"completed {token}"}

    pipeline._execute_internal_snapshot = execute_snapshot
    outcome = pipeline.process_internal_next(worker_id="automatic-worker")
    assert outcome is not None
    assert outcome["job"]["status"] == "completed"
    assert len(seen) == 1
    _assert_callback_safe(seen[0], materials[0], materials[1])


def test_callback_projection_custom_object_fails_closed_with_minimal_event(tmp_path: Path) -> None:
    pipeline = _pipeline(tmp_path)
    seen: list[tuple] = []
    pipeline.add_lifecycle_callback(lambda phase, callback_job, result, error: seen.append((phase, callback_job, result, error)))

    pipeline._notify_lifecycle(
        "completed",
        {"job_id": "job-1", "status": "completed", "source_type": "callback"},
        object(),
        None,
    )

    assert seen == [("completed", {"job_id": "job-1", "status": "completed", "source_type": "callback"}, "[REDACTED]", None)]
