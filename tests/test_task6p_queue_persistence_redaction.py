from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from src.extraction.queue import SQLiteExtractionQueue, _without_lease_material
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
