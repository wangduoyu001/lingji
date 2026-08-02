from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.control import p2_07_api
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


def test_codex_route_registration_is_lazy_and_auth_precedes_runtime(monkeypatch):
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
    assert initialized == []

    response = TestClient(app).get("/api/codex/current")
    assert response.status_code == 401
    assert initialized == []


def test_control_project_gateway_disables_embedded_semantic_runtime(monkeypatch):
    captured = {}

    def fake_builder(settings, **kwargs):
        captured["settings"] = settings
        captured.update(kwargs)
        return object()

    marker = SimpleNamespace(name="acceptance")
    monkeypatch.setattr(p2_07_api, "build_memory_gateway", fake_builder)

    gateway = p2_07_api.build_control_read_gateway(marker)

    assert gateway is not None
    assert captured["settings"] is marker
    assert captured["runtime_values"] == {"semantic_enabled": False}


def test_independent_routers_define_and_include_required_routes():
    root = Path(__file__).resolve().parents[1]
    project_routes = (root / "src" / "control" / "project_memory_api.py").read_text(
        encoding="utf-8"
    )
    obsidian_routes = (root / "src" / "control" / "obsidian_notes_api.py").read_text(
        encoding="utf-8"
    )

    for path in (
        "/api/context/project",
        "/api/memory/review/candidates",
        "/api/memory/core",
    ):
        assert path in project_routes
    for path in ("/api/obsidian/notes", "/api/obsidian/scan"):
        assert path in obsidian_routes
    assert "app.include_router(router)" in project_routes
    assert "app.include_router(router)" in obsidian_routes


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
