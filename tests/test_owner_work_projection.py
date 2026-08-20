from __future__ import annotations

import json

from src.control.capture import CaptureControlService


def test_owner_work_projection_drops_raw_worker_and_private_fields() -> None:
    service = object.__new__(CaptureControlService)
    row = {
        "job_id": "LJ-JOB-PRIVACY",
        "source_type": "text",
        "adapter_name": "web_capture",
        "status": "running",
        "priority": 100,
        "attempts": 1,
        "max_attempts": 3,
        "progress_current": 1,
        "progress_total": 0,
        "progress_message": r"processing D:\Users\Private\secret.txt token=top-secret",
        "input_path": r"D:\Users\Private\secret.txt",
        "last_error": r"failed at D:\Users\Private\state.db Authorization: Bearer secret",
        "lease_token": "lease-secret",
        "locked_by": "worker-private",
        "payload": {
            "capture_id": "LJ-CAP-PRIVACY",
            "capture_method": "owner_command_bar",
            "title": "主人快速记录",
            "text": "owner private body",
            "html": "<p>owner private html</p>",
            "metadata": {"private": "payload"},
        },
        "result": {},
        "created_at": "2026-08-20T00:00:00Z",
        "updated_at": "2026-08-20T00:00:01Z",
    }

    dto = service.job_dto(row)
    serialized = json.dumps(dto, ensure_ascii=False)

    assert dto["job_id"] == "LJ-JOB-PRIVACY"
    assert dto["work_item_id"] == "LJ-JOB-PRIVACY"
    assert dto["capture_id"] == "LJ-CAP-PRIVACY"
    assert dto["title"] == "主人快速记录"
    assert dto["outcome_state"] == "running"
    assert dto["next_actor"] == "system"
    assert dto["file_name"] == "secret.txt"

    for forbidden in (
        "progress_message",
        "processing D:",
        "owner private body",
        "owner private html",
        "token=top-secret",
        "Authorization",
        "Bearer secret",
        "lease-secret",
        "worker-private",
        "D:\\Users\\Private",
        '"payload"',
        '"last_error"',
        '"input_path"',
    ):
        assert forbidden not in serialized
