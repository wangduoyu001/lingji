from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.control import obsidian_notes_api, p2_07_api, project_memory_api
from src.gateway.profiles import AIProfileRegistry
from src.project_memory.runtime import build_project_context_service


class _FakeDatabase:
    revision = 1

    def list_core_memories(self, **_kwargs):
        return []

    def list_recent(self, **_kwargs):
        return []

    def fetch_memory(self, *_args, **_kwargs):
        return None


class _FakeRetriever:
    def search(self, *_args, **_kwargs):
        return []


class _FakeSessions:
    def list_sessions(self, **_kwargs):
        return {
            "items": [
                {
                    "session_id": "LJ-CODEX-SESSION-1",
                    "project_id": "LJ-PROJ-LINGJI",
                    "status": "completed",
                }
            ]
        }

    def get_session(self, session_id: str):
        return {
            "session_id": session_id,
            "project_id": "LJ-PROJ-LINGJI",
            "title": "P2-07 wiring",
            "status": "completed",
            "privacy": "private",
            "created_at": "2026-07-21T10:00:00+00:00",
            "ended_at": "2026-07-21T11:00:00+00:00",
            "events": [
                {
                    "summary": "Codex session entered LingJi",
                    "occurred_at": "2026-07-21T11:00:00+00:00",
                }
            ],
        }


def test_route_registration_is_lazy_and_auth_precedes_runtime(monkeypatch):
    # Some contract tests intentionally import route modules with fake FastAPI
    # classes. Reload the two independently registered routers so this test
    # validates the production FastAPI integration rather than leaked fakes.
    project_routes = importlib.reload(project_memory_api)
    obsidian_routes = importlib.reload(obsidian_notes_api)
    monkeypatch.setattr(
        p2_07_api,
        "register_project_memory_routes",
        project_routes.register_project_memory_routes,
    )
    monkeypatch.setattr(
        p2_07_api,
        "register_obsidian_note_routes",
        obsidian_routes.register_obsidian_note_routes,
    )

    app = FastAPI()
    control = SimpleNamespace()
    initialized = []

    def forbidden_builder(_settings):
        initialized.append(True)
        raise AssertionError("runtime must remain lazy for unauthorized requests")

    monkeypatch.setattr(p2_07_api, "build_memory_gateway", forbidden_builder)
    p2_07_api.register_p2_07_routes(
        app,
        SimpleNamespace(),
        control,
        token="secret-token",
    )

    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/api/codex/current" in paths
    assert "/api/context/project" in paths
    assert "/api/memory/review/candidates" in paths
    assert "/api/obsidian/notes" in paths
    assert initialized == []

    response = TestClient(app).get("/api/codex/current")
    assert response.status_code == 401
    assert initialized == []


def test_completed_codex_session_is_available_to_project_context():
    gateway = SimpleNamespace(
        database=_FakeDatabase(),
        retriever=_FakeRetriever(),
        profiles=AIProfileRegistry(),
    )
    service = build_project_context_service(gateway, _FakeSessions())

    pack = service.build(
        agent_id="codex",
        project_id="LJ-PROJ-LINGJI",
        query="",
        max_chars=4000,
    )

    assert len(pack["recent_sessions"]) == 1
    session = pack["recent_sessions"][0]
    assert session["status"] == "completed"
    assert session["source_id"].startswith("LJ-SRC-")
    assert session["conversation_id"].startswith("LJ-CONV-")
    assert "Codex session entered LingJi" in pack["markdown"]


def test_production_entries_register_p2_07_control_and_context_tools():
    root = Path(__file__).resolve().parents[1]
    control_entry = (root / "run_control_api.py").read_text(encoding="utf-8")
    mcp_entry = (root / "src" / "mcp_server.py").read_text(encoding="utf-8")

    assert "register_p2_07_routes(app, settings, service, token=token)" in control_entry
    assert "register_project_context_tools(mcp, context_service" in mcp_entry
    assert "pipeline = extraction_pipeline or build_extraction_pipeline" in mcp_entry
