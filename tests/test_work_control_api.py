from pathlib import Path

from src.control.work_service import WorkControlService
from src.config import Settings
from src.control.api import create_control_app
from src.control.service import LocalControlService
from src.storage.state_db import StateDatabase
from src.work.models import ExecutionEvent, NextAction, Outcome, PendingAction, WorkItem
from fastapi.testclient import TestClient


def test_work_api_contract_source_is_work_control_service(tmp_path: Path):
    """Keep the API boundary backed by Work Fact projection, not UI state."""
    service = WorkControlService(StateDatabase(tmp_path / "state.db"))
    item = WorkItem(title="api contract")
    service.store.create_work(item)
    service.store.append_event(
        ExecutionEvent(work_id=item.work_id, event_type="created")
    )

    current = service.current_work()
    timeline = service.work_timeline(item.work_id)

    assert current["work"]["work_id"] == item.work_id
    assert timeline["work"]["work_id"] == item.work_id
    assert timeline["events"][0]["event_type"] == "created"


def test_work_history_is_bounded_paginated_and_keeps_stable_fact_identity(tmp_path: Path):
    state = StateDatabase(tmp_path / "state.db")
    service = WorkControlService(state)
    works = []
    for index in range(4):
        item = WorkItem(work_id=f"work-{index}", title=f"工作 {index}", created_at=f"2026-08-28T00:00:0{index}+00:00")
        service.store.create_work(item)
        service.store.append_event(ExecutionEvent(work_id=item.work_id, event_id=f"event-{index}", event_type="created", created_at=item.created_at))
        works.append(item)

    first = service.work_history(limit=2, offset=0)
    second = service.work_history(limit=2, offset=2)

    assert first["limit"] == 2
    assert first["offset"] == 0
    assert first["has_more"] is True
    assert len(first["items"]) == 2
    assert len(second["items"]) == 2
    assert {item["work"]["work_id"] for item in first["items"]}.isdisjoint(
        {item["work"]["work_id"] for item in second["items"]}
    )
    assert all(item["work"]["work_id"] for item in first["items"])
    assert all("summary" in item for item in first["items"])


def test_work_timeline_is_chronological_and_preserves_event_identity_after_restart(tmp_path: Path):
    state_path = tmp_path / "state.db"
    service = WorkControlService(StateDatabase(state_path))
    item = WorkItem(work_id="timeline-work", title="时间线")
    service.store.create_work(item)
    service.store.append_event(ExecutionEvent(work_id=item.work_id, event_id="event-2", event_type="completed", created_at="2026-08-28T00:00:02+00:00"))
    service.store.append_event(ExecutionEvent(work_id=item.work_id, event_id="event-1", event_type="started", created_at="2026-08-28T00:00:01+00:00"))

    timeline = WorkControlService(StateDatabase(state_path)).work_timeline(item.work_id)
    assert [event["event_id"] for event in timeline["events"]] == ["event-1", "event-2"]
    assert [event["created_at"] for event in timeline["events"]] == sorted(event["created_at"] for event in timeline["events"])
    assert timeline["work"]["work_id"] == item.work_id


def test_pending_action_resolve_is_authenticated_truthful_and_idempotent(tmp_path: Path):
    root = tmp_path / "workspace"
    settings = Settings(
        _env_file=None,
        vault_dir=str(root / "vault"),
        storage_dir=str(root / "storage"),
        log_dir=str(root / "logs"),
        backup_dir=str(root / "backup"),
        startup_min_free_gb=0,
    )
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    control = LocalControlService(settings)
    work = WorkItem(work_id="resolve-work", title="待办")
    control.state_db and WorkControlService(control.state_db).store.create_work(work)
    WorkControlService(control.state_db).store.add_pending_action(
        PendingAction(work_id=work.work_id, action_id="owner-action", description="请确认")
    )
    with TestClient(create_control_app(settings, service=control, token="secret")) as client:
        assert client.post("/api/work/pending-actions/owner-action/resolve").status_code == 401
        headers = {"X-LingJi-Token": "secret"}
        first = client.post("/api/work/pending-actions/owner-action/resolve", headers=headers)
        replay = client.post("/api/work/pending-actions/owner-action/resolve", headers=headers)
        missing = client.post("/api/work/pending-actions/missing/resolve", headers=headers)

    assert first.status_code == 200
    assert first.json()["action_id"] == "owner-action"
    assert first.json()["resolved"] is True
    assert replay.status_code == 200
    assert replay.json()["resolved"] is True
    assert missing.status_code == 404
