from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

from src.codex_sessions import CODEX_SESSION_NOT_FOUND, CodexSessionError
from src.control.codex_api import register_codex_routes


class FakeService:
    def __init__(self):
        self.closed = False

    def resolve_project(self, workspace_path):
        return {
            "project_id": "LJ-PROJ-LINGJI", "name": "LingJi",
            "repository": "wangduoyu001/lingji", "branch": "main",
            "worktree_name": "lingji", "path_display": "D:/…/lingji",
            "resolution_source": "git", "state": "resolved",
        }

    def list_projects(self):
        return [self.resolve_project(".")]

    def start_session(self, **kwargs):
        return {"session_id": "S1", "project_id": "LJ-PROJ-LINGJI", "status": "active", "created_at": "now"}

    def checkpoint(self, session_id, **kwargs):
        if session_id == "missing":
            raise CodexSessionError(CODEX_SESSION_NOT_FOUND, "Codex session not found", status_code=404)
        if self.closed:
            raise CodexSessionError("CODEX_SESSION_ALREADY_CLOSED", "Codex session is already closed", status_code=409)
        return {"session_id": session_id, "event_id": kwargs["event_id"], "status": "active"}

    def close_session(self, session_id, **kwargs):
        self.closed = True
        return {"session_id": session_id, "status": kwargs["status"]}

    def list_sessions(self, **kwargs):
        return {"items": [], "pagination": {**kwargs, "total": 0, "has_more": False}}

    def get_session(self, session_id):
        if session_id == "missing":
            raise CodexSessionError(CODEX_SESSION_NOT_FOUND, "Codex session not found", status_code=404)
        return {"session_id": session_id, "events": []}

    def activity(self, **kwargs):
        return {"items": [{"event_id": kwargs["after_id"] + 1}], "after_id": kwargs["after_id"] + 1, "has_more": False}


def app_client():
    app = FastAPI()
    service = FakeService()

    def token_validator(x_lingji_token: str | None = Header(default=None)):
        if x_lingji_token != "secret":
            raise HTTPException(status_code=401, detail="Invalid local control token")

    register_codex_routes(app, service, token_validator)
    return TestClient(app), service


def test_codex_routes_require_token_and_return_stable_errors():
    client, _ = app_client()
    assert client.get("/api/codex/projects").status_code == 401
    headers = {"X-LingJi-Token": "secret"}
    assert client.get("/api/codex/sessions/missing", headers=headers).status_code == 404
    response = client.post(
        "/api/codex/sessions/missing/checkpoint", headers=headers,
        json={"event_id": "E1", "kind": "checkpoint", "summary": "x"},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == CODEX_SESSION_NOT_FOUND


def test_project_session_and_activity_contracts():
    client, service = app_client()
    headers = {"X-LingJi-Token": "secret"}
    resolved = client.post(
        "/api/codex/projects/resolve", headers=headers,
        json={"workspace_path": "D:/code/lingji"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["path_display"] == "D:/…/lingji"
    assert "D:/code" not in resolved.text
    started = client.post(
        "/api/codex/sessions/start", headers=headers,
        json={"workspace_path": "D:/code/lingji", "external_session_id": "C1", "title": "Task"},
    )
    assert started.json()["session_id"] == "S1"
    checkpoint = client.post(
        "/api/codex/sessions/S1/checkpoint", headers=headers,
        json={"event_id": "E1", "kind": "test_result", "summary": "passed"},
    )
    assert checkpoint.status_code == 200
    close = client.post(
        "/api/codex/sessions/S1/close", headers=headers,
        json={"event_id": "E2", "summary": "done", "status": "completed"},
    )
    assert close.json()["status"] == "completed"
    conflict = client.post(
        "/api/codex/sessions/S1/checkpoint", headers=headers,
        json={"event_id": "E3", "kind": "checkpoint", "summary": "late"},
    )
    assert conflict.status_code == 409
    activity = client.get("/api/activity?after_id=10&limit=20", headers=headers)
    assert activity.json()["after_id"] == 11


def test_unexpected_api_error_is_stable_and_does_not_leak_path():
    client, service = app_client()
    headers = {"X-LingJi-Token": "secret"}
    service.resolve_project = lambda workspace_path: (_ for _ in ()).throw(
        RuntimeError(r"failed at D:\Users\Secret\codex.db")
    )
    response = client.post(
        "/api/codex/projects/resolve", headers=headers,
        json={"workspace_path": "D:/code/lingji"},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "CODEX_INGESTION_FAILED"
    assert "Users" not in response.text
    assert "codex.db" not in response.text


def test_project_and_session_read_routes_are_registered():
    client, _ = app_client()
    headers = {"X-LingJi-Token": "secret"}
    assert client.get("/api/codex/projects", headers=headers).status_code == 200
    assert client.get("/api/codex/current?workspace_path=D%3A%2Fcode%2Flingji", headers=headers).status_code == 200
    sessions = client.get(
        "/api/codex/sessions?project_id=LJ-PROJ-LINGJI&limit=10&offset=0", headers=headers,
    )
    assert sessions.status_code == 200
    assert sessions.json()["pagination"]["limit"] == 10
