from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import sqlite3
from pathlib import Path

import pytest

from src.extraction.queue import SQLiteExtractionQueue
from src.extraction.transient import automatic_memory_dispatch_path, reconcile_automatic_memory_transients
from src.mcp.extraction_submission import durable_job_response


def _queue(tmp_path: Path) -> SQLiteExtractionQueue:
    return SQLiteExtractionQueue(tmp_path / "lingji_state.db")


def _raw(root: Path, content: bytes = b"durable") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / hashlib.sha256(content).hexdigest()
    path.write_bytes(content)
    return path


def _job(queue: SQLiteExtractionQueue, raw: Path, key: str) -> dict:
    return queue.enqueue(
        "automatic_memory_snapshot",
        input_path=raw,
        payload={"source_id": "source", "raw_id": raw.name},
        idempotency_key=key,
    )


def _claim(queue: SQLiteExtractionQueue, raw: Path, key: str, worker: str = "worker") -> dict:
    job = _job(queue, raw, key)
    claimed = queue.claim(worker, job_id=job["job_id"], allowed_source_types={"automatic_memory_snapshot"})
    assert claimed is not None
    return claimed


def _marker(raw: Path, claimed: dict, suffix: str = ".json") -> Path:
    marker = automatic_memory_dispatch_path(raw.parent, claimed["job_id"], claimed["lease_token"], suffix)
    os.link(raw, marker)
    return marker


def _stored_fingerprint(queue: SQLiteExtractionQueue, job_id: str) -> str | None:
    with queue._connection() as connection:
        row = connection.execute(
            "SELECT last_claim_lease_fingerprint FROM extraction_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
    return row["last_claim_lease_fingerprint"] if row else None


def test_existing_db_migrates_nullable_last_claim_fingerprint_idempotently(tmp_path: Path) -> None:
    db = tmp_path / "legacy.db"
    SQLiteExtractionQueue(db)
    with sqlite3.connect(db) as connection:
        connection.execute("ALTER TABLE extraction_jobs DROP COLUMN last_claim_lease_fingerprint")
    SQLiteExtractionQueue(db)
    SQLiteExtractionQueue(db)
    with sqlite3.connect(db) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(extraction_jobs)")}
    assert "last_claim_lease_fingerprint" in columns


def test_claim_persists_hash_atomically_and_terminal_lifecycle_keeps_receipt(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    raw = _raw(tmp_path / "raw")
    claimed = _claim(queue, raw, "lifecycle")
    expected = hashlib.sha256(claimed["lease_token"].encode()).hexdigest()
    with queue._connection() as connection:
        row = connection.execute("SELECT lease_token, last_claim_lease_fingerprint FROM extraction_jobs WHERE job_id = ?", (claimed["job_id"],)).fetchone()
    assert row["lease_token"] == claimed["lease_token"]
    assert row["last_claim_lease_fingerprint"] == expected
    queue.complete(claimed["job_id"], {}, worker_id="worker", lease_token=claimed["lease_token"])
    final = queue.get(claimed["job_id"])
    assert "lease_token" not in final
    assert _stored_fingerprint(queue, claimed["job_id"]) == expected


def test_release_and_stale_keep_last_fingerprint_but_retry_and_force_reset_generation(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    raw = _raw(tmp_path / "raw")
    claimed = _claim(queue, raw, "release")
    queue.release_claim(claimed["job_id"], worker_id="worker", lease_token=claimed["lease_token"])
    expected = hashlib.sha256(claimed["lease_token"].encode()).hexdigest()
    assert _stored_fingerprint(queue, claimed["job_id"]) == expected
    claimed_again = queue.claim("worker-2", job_id=claimed["job_id"], allowed_source_types={"automatic_memory_snapshot"})
    assert claimed_again is not None
    old = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(timespec="seconds")
    with queue._connection() as connection:
        connection.execute("UPDATE extraction_jobs SET heartbeat_at = ?, locked_at = ? WHERE job_id = ?", (old, old, claimed["job_id"]))
    queue.release_stale(30)
    assert _stored_fingerprint(queue, claimed["job_id"]) == hashlib.sha256(claimed_again["lease_token"].encode()).hexdigest()
    retried_job = _claim(queue, raw, "retry", worker="worker-3")
    queue.fail(retried_job["job_id"], "terminal", worker_id="worker-3", lease_token=retried_job["lease_token"], terminal=True)
    retried = queue.retry(retried_job["job_id"])
    assert "last_claim_lease_fingerprint" not in retried
    assert _stored_fingerprint(queue, retried["job_id"]) is None


def test_force_reenqueue_clears_old_fingerprint(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    raw = _raw(tmp_path / "raw")
    claimed = _claim(queue, raw, "force")
    queue.complete(claimed["job_id"], {}, worker_id="worker", lease_token=claimed["lease_token"])
    reset = queue.enqueue("automatic_memory_snapshot", input_path=raw, payload={"source_id": "source", "raw_id": raw.name}, idempotency_key="force", force=True)
    assert "last_claim_lease_fingerprint" not in reset
    assert _stored_fingerprint(queue, reset["job_id"]) is None


def test_terminal_wrong_lease_same_raw_hardlink_is_preserved(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    raw = _raw(tmp_path / "raw")
    claimed = _claim(queue, raw, "wrong-terminal")
    marker = automatic_memory_dispatch_path(raw.parent, claimed["job_id"], "WRONGLEASE", ".json")
    os.link(raw, marker)
    queue.complete(claimed["job_id"], {}, worker_id="worker", lease_token=claimed["lease_token"])
    report = reconcile_automatic_memory_transients(raw.parent, queue)
    assert marker.exists()
    assert report["preserved"][0]["reason"] == "lease_mismatch"


def test_matching_released_marker_is_removed_and_null_fingerprint_fails_closed(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    raw = _raw(tmp_path / "raw")
    claimed = _claim(queue, raw, "matching")
    marker = _marker(raw, claimed)
    queue.release_claim(claimed["job_id"], worker_id="worker", lease_token=claimed["lease_token"])
    report = reconcile_automatic_memory_transients(raw.parent, queue)
    assert not marker.exists()
    assert report["removed_count"] == 1

    claimed = _claim(queue, raw, "null-fingerprint")
    marker = _marker(raw, claimed)
    with queue._connection() as connection:
        connection.execute("UPDATE extraction_jobs SET last_claim_lease_fingerprint = NULL WHERE job_id = ?", (claimed["job_id"],))
    report = reconcile_automatic_memory_transients(raw.parent, queue)
    assert marker.exists()
    assert report["preserved"][0]["reason"] == "lease_unverifiable"


def test_retrying_marker_uses_durable_fingerprint_after_failure(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    raw = _raw(tmp_path / "raw")
    claimed = _claim(queue, raw, "retrying")
    marker = _marker(raw, claimed)
    queue.fail(claimed["job_id"], "retry later", worker_id="worker", lease_token=claimed["lease_token"], retry_delay_seconds=0)
    report = reconcile_automatic_memory_transients(raw.parent, queue)
    assert not marker.exists()
    assert report["removed"][0]["reason"] == "lease_released"


def test_old_generation_marker_survives_new_claim_generation(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    raw = _raw(tmp_path / "raw")
    first = _claim(queue, raw, "generation")
    old_marker = _marker(raw, first, ".old")
    queue.fail(first["job_id"], "terminal", worker_id="worker", lease_token=first["lease_token"], terminal=True)
    queue.retry(first["job_id"])
    second = queue.claim("worker-2", job_id=first["job_id"], allowed_source_types={"automatic_memory_snapshot"})
    assert second is not None
    new_marker = _marker(raw, second, ".new")
    report = reconcile_automatic_memory_transients(raw.parent, queue)
    assert old_marker.exists()
    assert new_marker.exists()
    assert report["removed_count"] == 0


def test_queue_read_error_preserves_marker_without_exception_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    queue = _queue(tmp_path)
    raw = _raw(tmp_path / "raw")
    claimed = _claim(queue, raw, "queue-error")
    marker = _marker(raw, claimed)

    def broken(*_args: object, **_kwargs: object) -> dict:
        raise RuntimeError("/private/secret/token=abc")

    monkeypatch.setattr(queue, "ownership_receipt", broken)
    report = reconcile_automatic_memory_transients(raw.parent, queue)
    encoded = json.dumps(report, ensure_ascii=False)
    assert marker.exists()
    assert report["errors"][0]["reason"] == "queue_read_failed"
    assert "token=abc" not in encoded
    assert "/private" not in encoded


def test_reconcile_permission_and_runtime_errors_are_sanitized_and_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    queue = _queue(tmp_path)
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    marker = raw_root / ".automatic-memory-v1-LJ-JOB-SECRET.LEASESECRET.json"
    marker.write_text("secret", encoding="utf-8")
    monkeypatch.setattr(Path, "iterdir", lambda self: (_ for _ in ()).throw(PermissionError("/private/secret/token=abc")))
    report = reconcile_automatic_memory_transients(raw_root, queue)
    encoded = json.dumps(report, ensure_ascii=False)
    assert report["errors"][0]["reason"] == "scan_failed"
    assert "secret" not in encoded.lower()
    assert "token=abc" not in encoded
    assert "/private" not in encoded


def test_public_job_response_does_not_expose_lease_or_fingerprint(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    raw = _raw(tmp_path / "raw")
    claimed = _claim(queue, raw, "public")
    response = durable_job_response(queue.get(claimed["job_id"]))
    encoded = json.dumps(response, ensure_ascii=False)
    assert "lease_token" not in response
    assert "last_claim_lease_fingerprint" not in response
    assert claimed["lease_token"] not in encoded

    nested = durable_job_response(
        {
            "job_id": claimed["job_id"],
            "lease_token": claimed["lease_token"],
            "last_claim_lease_fingerprint": "fingerprint-secret",
            "result": {
                "lease_token": claimed["lease_token"],
                "last_claim_lease_fingerprint": "fingerprint-secret",
            },
            "error": [
                {"lease_token": claimed["lease_token"]},
                {"message": f"failure-{claimed['lease_token']}"},
            ],
        }
    )
    nested_encoded = json.dumps(nested, ensure_ascii=False)
    assert claimed["lease_token"] not in nested_encoded
    assert "fingerprint-secret" not in nested_encoded


def test_ordinary_queue_reads_hide_lease_material_but_private_seam_supports_worker_lifecycle(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    raw = _raw(tmp_path / "raw")
    claimed = _claim(queue, raw, "safe-reads")
    reads = [
        queue.get(claimed["job_id"]),
        queue.list()[0],
        queue.list_page(limit=10)[0],
        queue.get_by_idempotency_key("safe-reads"),
    ]
    for value in reads:
        assert value is not None
        assert "lease_token" not in value
        assert "last_claim_lease_fingerprint" not in value
    internal = queue._get_claimed_job_internal(claimed["job_id"])
    assert internal["lease_token"] == claimed["lease_token"]
    assert "last_claim_lease_fingerprint" not in internal
    assert queue.heartbeat(claimed["job_id"], "worker", internal["lease_token"])
    completed = queue.complete(claimed["job_id"], {}, worker_id="worker", lease_token=internal["lease_token"])
    assert "lease_token" not in completed
    assert "last_claim_lease_fingerprint" not in completed
