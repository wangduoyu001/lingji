from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.codex_sessions import (
    CODEX_SESSION_ALREADY_CLOSED,
    CodexSessionArchive,
    CodexSessionError,
    CodexSessionService,
)
from src.project_context import ProjectResolution, ProjectState


class StaticResolver:
    def __init__(self, root: Path):
        self.root = root

    def resolve(self, workspace_path):
        return ProjectResolution(
            project_id="LJ-PROJ-LINGJI",
            name="LingJi",
            repository="wangduoyu001/lingji",
            branch="work/p2-07a",
            worktree_name="lingji-p2-07",
            path_display="D:/…/lingji-p2-07",
            resolution_source="manifest",
            state=ProjectState.RESOLVED,
            workspace_root=self.root,
            worktree_root=self.root,
        )

    def list_projects(self):
        return []


class FakePipeline:
    def __init__(self):
        self.calls = []

    def execute(self, source_type, **kwargs):
        self.calls.append((source_type, kwargs))
        return {"structured_read_model": {
            "state": "written", "sources": 1, "conversations": 1,
            "messages": len(kwargs["payload"]["events"]),
        }}


class FakeStateDB:
    def __init__(self, fail=False):
        self.rows = []
        self.fail = fail

    def append_event(self, event_type, entity_type, entity_id, payload):
        if self.fail:
            raise RuntimeError("audit unavailable")
        row = {
            "event_id": len(self.rows) + 1,
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "payload_json": json.dumps(payload),
            "created_at": "2026-07-21T00:00:00",
        }
        self.rows.append(row)
        return row["event_id"]

    def recent_events(self, limit=50):
        return list(reversed(self.rows[-limit:]))


def service(tmp_path: Path, state_db=None):
    pipeline = FakePipeline()
    result = CodexSessionService(
        StaticResolver(tmp_path),
        CodexSessionArchive(tmp_path / "storage"),
        pipeline,
        state_db=state_db or FakeStateDB(),
    )
    return result, pipeline


def test_start_checkpoint_close_and_idempotent_event_archive(tmp_path: Path):
    state = FakeStateDB()
    svc, pipeline = service(tmp_path, state)
    started = svc.start_session(
        workspace_path=tmp_path,
        external_session_id="codex-123",
        title="P2-07A",
        task="Build project resolver",
    )
    session_id = started["session_id"]
    assert session_id.startswith("LJ-CODEX-SESSION-")
    assert started["raw_reference"].startswith("raw:codex/sessions/")
    first = svc.checkpoint(
        session_id, event_id="checkpoint-1", kind="checkpoint",
        summary="Implemented service with token=abc123 and Bearer secret-value",
        changed_files=[r"D:\private\repo\src\service.py"],
        tests=[{"status": "passed", "api_key": "sk-supersecret"}],
    )
    duplicate = svc.checkpoint(
        session_id, event_id="checkpoint-1", kind="checkpoint",
        summary="Implemented service with token=abc123 and Bearer secret-value",
        changed_files=[r"D:\private\repo\src\service.py"],
        tests=[{"status": "passed", "api_key": "sk-supersecret"}],
    )
    assert first["duplicate"] is False
    assert duplicate["duplicate"] is True
    same_content = svc.checkpoint(
        session_id, event_id="checkpoint-2", kind="checkpoint",
        summary="Implemented service with token=abc123 and Bearer secret-value",
        changed_files=[r"D:\private\repo\src\service.py"],
        tests=[{"status": "passed", "api_key": "sk-supersecret"}],
    )
    assert same_content["duplicate"] is False
    assert same_content["duplicate_content_event_id"] == "checkpoint-1"
    closed = svc.close_session(
        session_id, event_id="close-1", summary="Done", status="completed",
        remaining_tasks=["integration review"],
    )
    assert closed["status"] == "completed"
    assert closed["remaining_tasks"] == ["integration review"]
    assert closed["memory_candidates_suggested"] == []
    with pytest.raises(CodexSessionError) as error:
        svc.checkpoint(
            session_id, event_id="checkpoint-after-close", kind="checkpoint", summary="Too late"
        )
    assert error.value.code == CODEX_SESSION_ALREADY_CLOSED
    detail = svc.get_session(session_id)
    assert len(detail["events"]) == 4
    serialized = json.dumps(detail, ensure_ascii=False)
    assert "abc123" not in serialized
    assert "secret-value" not in serialized
    assert "sk-supersecret" not in serialized
    assert "D:\\private" not in serialized
    assert pipeline.calls
    assert all(call[0] == "codex_session" for call in pipeline.calls)
    assert all(call[1]["payload"]["session"]["raw_reference"].startswith("raw:") for call in pipeline.calls)
    event_types = [row["event_type"] for row in state.rows]
    assert "PROJECT_RESOLVED" in event_types
    assert event_types.index("SOURCE_ARCHIVED") < event_types.index("CONVERSATION_INDEXED")


def test_jsonl_crash_tail_is_ignored_and_activity_is_incremental(tmp_path: Path):
    state = FakeStateDB()
    svc, _ = service(tmp_path, state)
    session = svc.start_session(workspace_path=tmp_path, external_session_id="tail")
    session_id = session["session_id"]
    archive_path = tmp_path / "storage" / "raw" / "codex" / "sessions" / "LJ-PROJ-LINGJI" / f"{session_id}.jsonl"
    with archive_path.open("a", encoding="utf-8") as stream:
        stream.write('{"incomplete":')
    detail = svc.get_session(session_id)
    assert detail["event_count"] == 1
    first = svc.activity(after_id=0, limit=2, project_id="LJ-PROJ-LINGJI")
    assert first["items"]
    second = svc.activity(after_id=first["after_id"], limit=100)
    assert all(item["event_id"] > first["after_id"] for item in second["items"])


def test_audit_failure_does_not_rollback_raw_or_structured_work(tmp_path: Path):
    svc, pipeline = service(tmp_path, FakeStateDB(fail=True))
    result = svc.start_session(workspace_path=tmp_path, external_session_id="audit-fail")
    assert result["status"] == "active"
    assert pipeline.calls


def test_external_session_id_is_stable_and_does_not_duplicate_raw_start(tmp_path: Path):
    svc, _ = service(tmp_path)
    first = svc.start_session(workspace_path=tmp_path, external_session_id="codex-stable", title="Stable")
    second = svc.start_session(workspace_path=tmp_path, external_session_id="codex-stable", title="Stable")
    assert first["session_id"] == second["session_id"]
    detail = svc.get_session(first["session_id"])
    assert detail["event_count"] == 1
    raw_files = list((tmp_path / "storage" / "raw" / "codex" / "sessions").glob("*/*.jsonl"))
    assert len(raw_files) == 1
