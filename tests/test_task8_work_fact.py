from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.config import Settings
from src.control.api import create_control_app
from src.control.work_service import WorkControlService
from src.storage.state_db import StateDatabase
from src.work.capture_bridge import CaptureWorkBridge
from src.work.models import ExecutionEvent, Failure, NextAction, Outcome, PendingAction, WorkItem
from src.work.projector import WorkProjector
from src.work.store import WorkStore


def test_work_facts_survive_restart_and_events_are_immutable_idempotent(tmp_path: Path):
    state_path = tmp_path / "state.db"
    store = WorkStore(StateDatabase(state_path))
    work = WorkItem(title="restartable", source_id="capture-1", status="running")
    store.create_work(work)
    event = ExecutionEvent(
        work_id=work.work_id,
        event_id="event-capture-1",
        event_type="capture.accepted",
        detail={"capture_id": "capture-1"},
    )
    store.append_event(event)
    store.append_event(ExecutionEvent(
        work_id=work.work_id,
        event_id=event.event_id,
        event_type="tampered",
        detail={"secret": "must-not-replace"},
    ))
    store.save_outcome(Outcome(work_id=work.work_id, status="completed", summary="done"))
    store.save_next_action(NextAction(work_id=work.work_id, description="none", actor="system"))
    store.save_failure(Failure(work_id=work.work_id, stage="index", reason="transient", retryable=True))
    store.add_pending_action(PendingAction(action_id="owner-1", work_id=work.work_id, description="confirm", actor="owner"))

    restarted = WorkStore(StateDatabase(state_path))
    events = restarted.list_events(work.work_id)
    assert len(events) == 1
    assert events[0].event_type == "capture.accepted"
    assert restarted.get_outcome(work.work_id).summary == "done"
    assert restarted.get_next_action(work.work_id).actor == "system"
    assert restarted.get_failure(work.work_id).reason == "transient"
    assert restarted.list_pending(work_id=work.work_id)[0].action_id == "owner-1"


def test_projector_exposes_one_work_fact_contract_without_items_alias(tmp_path: Path):
    store = WorkStore(StateDatabase(tmp_path / "state.db"))
    work = WorkItem(title="projected", status="running")
    store.create_work(work)
    store.append_event(ExecutionEvent(work_id=work.work_id, event_type="started"))
    store.save_outcome(Outcome(work_id=work.work_id, status="success", summary="saved"))
    store.save_next_action(NextAction(work_id=work.work_id, description="wait", actor="system"))

    fact = WorkProjector(store).current_fact()
    assert set(fact) == {"work", "events", "outcome", "next_action", "pending_actions", "failure"}
    assert fact["work"]["work_id"] == work.work_id
    assert fact["events"][0]["work_id"] == work.work_id
    assert fact["outcome"]["work_id"] == work.work_id
    assert fact["next_action"]["work_id"] == work.work_id
    assert fact["pending_actions"] == []
    assert fact["failure"] is None


def test_capture_bridge_is_idempotent_and_records_failure_retry_owner_paths(tmp_path: Path):
    bridge = CaptureWorkBridge(WorkStore(StateDatabase(tmp_path / "state.db")))
    first = bridge.create_from_capture("capture-1", "remember", approved=False)
    duplicate = bridge.create_from_capture("capture-1", "remember", approved=False)
    assert duplicate.work_id == first.work_id
    assert len(bridge.store.list_work()) == 1
    assert len(bridge.store.list_events(first.work_id)) == 1
    assert bridge.store.list_pending(work_id=first.work_id)

    bridge.record_failure(first.work_id, stage="extract", reason="bad input", retryable=True)
    bridge.retry(first.work_id)
    events = bridge.store.list_events(first.work_id)
    assert [event.event_type for event in events] == ["work.retrying", "work.failed", "capture.accepted"]
    assert bridge.store.get_failure(first.work_id).retryable is True


def test_authenticated_work_routes_use_same_state_db_and_hide_paths(tmp_path: Path):
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
    client_context = TestClient(create_control_app(settings, token="secret"))
    with client_context as client:
        assert client.get("/api/work/current").status_code == 401
        response = client.get("/api/work/current", headers={"X-LingJi-Token": "secret"})
        assert response.status_code == 200
        assert set(response.json()) == {"work", "events", "outcome", "next_action", "pending_actions", "failure"}
        assert "workspace" not in json.dumps(response.json())
        assert client.get("/api/work/pending-actions", headers={"X-LingJi-Token": "secret"}).status_code == 200
        assert client.get("/api/work/timeline/unknown", headers={"X-LingJi-Token": "secret"}).status_code == 404


def test_history_and_pending_routes_share_persisted_projection_and_bound_inputs(tmp_path: Path):
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
    control = WorkControlService(StateDatabase(settings.state_db_path))
    work = WorkItem(work_id="shared-work", title="共享投影", status="running")
    control.store.create_work(work)
    control.store.append_event(ExecutionEvent(work_id=work.work_id, event_id="shared-event", event_type="started"))
    control.store.add_pending_action(PendingAction(work_id=work.work_id, action_id="shared-action", description="需要主人确认"))

    with TestClient(create_control_app(settings, token="secret")) as client:
        headers = {"X-LingJi-Token": "secret"}
        history = client.get("/api/work/history?limit=1&offset=0", headers=headers)
        pending = client.get("/api/work/pending-actions", headers=headers)
        timeline = client.get(f"/api/work/timeline/{work.work_id}", headers=headers)
        too_large = client.get("/api/work/history?limit=201", headers=headers)
        negative = client.get("/api/work/history?offset=-1", headers=headers)

    assert history.status_code == 200
    assert history.json()["items"][0]["work"]["work_id"] == work.work_id
    assert pending.status_code == 200
    assert pending.json()["pending_actions"][0]["action_id"] == "shared-action"
    assert timeline.status_code == 200
    assert timeline.json()["work"]["work_id"] == work.work_id
    assert too_large.status_code == 422
    assert negative.status_code == 422
