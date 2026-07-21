from __future__ import annotations

import pytest

from src.mcp.extraction_submission import (
    durable_job_response,
    enqueue_durable_submission,
    validate_codex_work_report,
)


class _Pipeline:
    def __init__(self):
        self.enqueued = []
        self.processed = []
        self.execute_calls = []
        self.queue = self

    def enqueue(self, source_type, **kwargs):
        self.enqueued.append((source_type, kwargs))
        return {
            "job_id": "LJ-JOB-1",
            "status": "queued",
            "idempotency_key": "abc",
            "source_type": source_type,
            "adapter_name": kwargs["adapter_name"],
            "created_at": "2026-07-22T00:00:00",
            "attempts": 0,
            "existing_job": False,
        }

    def process_job(self, job_id):
        self.processed.append(job_id)
        return {
            "job": {
                "job_id": job_id,
                "status": "completed",
                "idempotency_key": "abc",
                "source_type": "codex",
                "adapter_name": "codex_work_report",
                "created_at": "2026-07-22T00:00:00",
                "attempts": 1,
            },
            "result": {"ok": True},
        }

    def get(self, job_id):
        raise AssertionError("fallback queue lookup should not be needed")

    def execute(self, *args, **kwargs):
        self.execute_calls.append((args, kwargs))
        raise AssertionError("durable MCP submission must not call execute directly")


def _report():
    return {
        "task_id": "P2-09B",
        "execution_id": "run-1",
        "repository": "wangduoyu001/lingji",
        "branch": "work/p2-09b-idempotency-mcp",
        "commits": ["abc123"],
        "changed_files": ["src/mcp_server.py"],
        "tests": [{"command": "pytest", "status": "passed", "exit_code": 0}],
        "summary": "done",
    }


def test_work_report_requires_durable_identity_fields():
    report = _report()
    report.pop("execution_id")
    with pytest.raises(ValueError, match="execution_id"):
        validate_codex_work_report(report)


def test_work_report_requires_list_structures():
    report = _report()
    report["tests"] = "pytest passed"
    with pytest.raises(ValueError, match="tests must be a list"):
        validate_codex_work_report(report)


def test_work_report_rejects_sensitive_fields():
    report = _report()
    report["metadata"] = {"api_key": "secret"}
    with pytest.raises(ValueError, match="Sensitive field"):
        validate_codex_work_report(report)


def test_default_submission_only_enqueues():
    pipeline = _Pipeline()
    response = enqueue_durable_submission(
        pipeline,
        "codex",
        payload=validate_codex_work_report(_report()),
        options={},
        adapter_name="codex_work_report",
    )
    assert response["status"] == "queued"
    assert response["job_id"] == "LJ-JOB-1"
    assert response["existing_job"] is False
    assert pipeline.enqueued
    assert pipeline.processed == []
    assert pipeline.execute_calls == []


def test_process_now_enqueues_before_processing():
    pipeline = _Pipeline()
    response = enqueue_durable_submission(
        pipeline,
        "codex",
        payload=validate_codex_work_report(_report()),
        options={},
        adapter_name="codex_work_report",
        process_now=True,
    )
    assert pipeline.enqueued
    assert pipeline.processed == ["LJ-JOB-1"]
    assert response["status"] == "completed"
    assert response["result"] == {"ok": True}
    assert pipeline.execute_calls == []


def test_job_response_does_not_claim_completed_for_queued_job():
    response = durable_job_response(
        {
            "job_id": "LJ-JOB-2",
            "status": "queued",
            "attempts": 0,
            "existing_job": True,
        }
    )
    assert response["status"] == "queued"
    assert response["existing_job"] is True
    assert response["retry_count"] == 0
