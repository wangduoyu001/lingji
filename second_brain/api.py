from __future__ import annotations

import json
import os
import subprocess
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import requests
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from second_brain.acceptance import AcceptanceService
from second_brain.config import ROOT
from second_brain.models import (
    CodexTaskRequest,
    ConflictResolveRequest,
    ContextRequest,
    DistillRequest,
    ImportRequest,
    KnowledgeIndexRequest,
    ReviewRequest,
    SearchRequest,
    SupersedeRequest,
)
from second_brain.runtime import Runtime
from second_brain.runtime_registry import RuntimeRegistry, WORKSPACES
from second_brain.utils import utc_now
from second_brain.watcher import BoundedWatcher


registry: RuntimeRegistry | None = None
acceptance: AcceptanceService | None = None


def get_registry() -> RuntimeRegistry:
    if registry is None:
        raise RuntimeError("Runtime registry is not initialized")
    return registry


def runtime_for_request(
    workspace: Annotated[str, Header(alias="X-LingJi-Workspace")] = "production",
) -> Runtime:
    try:
        return get_registry().get(workspace)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


CurrentRuntime = Annotated[Runtime, Depends(runtime_for_request)]


@asynccontextmanager
async def lifespan(_: FastAPI):
    global registry, acceptance
    registry = RuntimeRegistry()
    registry.initialize()
    acceptance = AcceptanceService(registry, "http://127.0.0.1:8765")
    yield
    registry.close()
    registry = None
    acceptance = None


app = FastAPI(title="LingJi Second Brain", version="0.2.0", lifespan=lifespan)


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"code": "invalid_request", "message": str(exc), "detail": None})


@app.get("/health")
def health(current: CurrentRuntime) -> dict:
    return {"status": "ok", "service": "lingji-second-brain", "qdrant": current.vectors.status()}


@app.post("/memory/import")
def import_memory(request: ImportRequest, current: CurrentRuntime) -> dict:
    if bool(request.path) == bool(request.conversation):
        raise HTTPException(400, "Provide exactly one of path or conversation")
    try:
        results = (
            current.chats.import_path(request.path)
            if request.path
            else [current.chats.import_conversation(request.conversation)]
        )
        if request.distill:
            for result in results:
                if result.get("imported"):
                    result["memory_candidates"] = current.distillation.distill(
                        conversation_id=result["conversation_id"]
                    )
        return {"results": results}
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/memory/search")
def search(request: SearchRequest, current: CurrentRuntime) -> dict:
    return {"results": current.retrieval.search(**request.model_dump())}


@app.post("/memory/context")
def context(request: ContextRequest, current: CurrentRuntime) -> dict:
    return current.retrieval.context(request.project, request.task, request.max_tokens)


@app.post("/memory/distill")
def distill(request: DistillRequest, current: CurrentRuntime) -> dict:
    return {"candidates": current.distillation.distill(request.conversation_id, request.source_id)}


@app.post("/memory/approve")
def approve(request: ReviewRequest, current: CurrentRuntime) -> dict:
    try:
        memory = current.memories.set_status(request.memory_id, "active", request.reason or "approved")
        conflicts = current.conflicts.detect_for(request.memory_id)
        return {"memory": current.memories.get(request.memory_id), "conflicts": conflicts}
    except KeyError as exc:
        raise HTTPException(404, f"Memory not found: {exc.args[0]}") from exc


@app.post("/memory/reject")
def reject(request: ReviewRequest, current: CurrentRuntime) -> dict:
    try:
        return {"memory": current.memories.set_status(request.memory_id, "rejected", request.reason or "rejected")}
    except KeyError as exc:
        raise HTTPException(404, f"Memory not found: {exc.args[0]}") from exc


@app.post("/memory/supersede")
def supersede(request: SupersedeRequest, current: CurrentRuntime) -> dict:
    try:
        return current.memories.supersede(
            request.old_memory_id, request.new_memory_id, request.new_memory, request.reason
        )
    except KeyError as exc:
        raise HTTPException(404, f"Memory not found: {exc.args[0]}") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/memory/codex-task")
def codex_task(request: CodexTaskRequest, current: CurrentRuntime) -> dict:
    return current.codex.record(request)


@app.post("/knowledge/index")
def index_knowledge(request: KnowledgeIndexRequest, current: CurrentRuntime) -> dict:
    try:
        return current.obsidian.index_file(request.path)
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


def _counts(current: Runtime) -> dict:
    with current.database.connect() as connection:
        return {
            table: connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"]
            for table in ("sources", "conversations", "messages", "memories", "knowledge_documents", "tasks")
        }


def _status(current: Runtime) -> dict:
    with current.database.connect() as connection:
        states = {
            row["status"]: row["count"]
            for row in connection.execute("SELECT status,COUNT(*) AS count FROM memories GROUP BY status").fetchall()
        }
    return {
        "counts": _counts(current),
        "memory_states": states,
        "qdrant": current.vectors.status(),
        "embedding": current.embedder.status(),
        "watch_roots": {
            "ai_chat": str(current.settings.ai_inbox_dir),
            "codex_tasks": str(current.settings.codex_inbox_dir),
            "obsidian": str(current.settings.obsidian_knowledge_dir) if current.settings.obsidian_knowledge_dir else None,
        },
        "database": str(current.settings.database_path),
    }


@app.get("/memory/status")
def status(current: CurrentRuntime) -> dict:
    return _status(current)


@app.get("/memory/conflicts")
def conflicts(current: CurrentRuntime) -> dict:
    return {"conflicts": current.conflicts.list_open()}


@app.get("/memory/pending")
def pending(current: CurrentRuntime) -> dict:
    return {"memories": current.memories.pending()}


@app.get("/memory/projects")
def projects(current: CurrentRuntime) -> dict:
    with current.database.connect() as connection:
        rows = connection.execute(
            """SELECT p.*,
            (SELECT COUNT(*) FROM memories m WHERE m.project_id=p.id) AS memory_count,
            (SELECT COUNT(*) FROM knowledge_documents k WHERE k.project_id=p.id) AS knowledge_count,
            (SELECT COUNT(*) FROM tasks t WHERE t.project_id=p.id) AS task_count
            FROM projects p ORDER BY p.name"""
        ).fetchall()
    return {"projects": [dict(row) for row in rows]}


@app.get("/memory/timeline")
def timeline(current: CurrentRuntime, limit: int = Query(100, ge=1, le=500)) -> dict:
    with current.database.connect() as connection:
        rows = connection.execute(
            """SELECT 'memory' AS kind,id,title AS summary,created_at FROM memories
            UNION ALL SELECT 'task',id,request,created_at FROM tasks
            UNION ALL SELECT 'import',id,source_type || ':' || status,started_at FROM import_jobs
            ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return {"events": [dict(row) for row in rows]}


@app.get("/memory/list")
def memory_list(
    current: CurrentRuntime,
    status_filter: str | None = Query(None, alias="status"),
    memory_type: str | None = None,
    project: str | None = None,
    query: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    clauses = ["1=1"]
    params: list[object] = []
    if status_filter:
        clauses.append("m.status=?")
        params.append(status_filter)
    if memory_type:
        clauses.append("m.memory_type=?")
        params.append(memory_type.upper())
    if project:
        clauses.append("p.name=?")
        params.append(project)
    if query:
        clauses.append("(m.title LIKE ? OR m.content LIKE ?)")
        params.extend((f"%{query}%", f"%{query}%"))
    with current.database.connect() as connection:
        total = connection.execute(
            f"SELECT COUNT(*) FROM memories m LEFT JOIN projects p ON p.id=m.project_id WHERE {' AND '.join(clauses)}",
            params,
        ).fetchone()[0]
        rows = connection.execute(
            f"""SELECT m.*,p.name AS project FROM memories m LEFT JOIN projects p ON p.id=m.project_id
            WHERE {' AND '.join(clauses)} ORDER BY m.updated_at DESC LIMIT ? OFFSET ?""",
            (*params, limit, offset),
        ).fetchall()
    return {"total": total, "items": [dict(row) for row in rows]}


@app.get("/memory/tasks")
def tasks(current: CurrentRuntime, limit: int = Query(100, ge=1, le=500)) -> dict:
    with current.database.connect() as connection:
        rows = connection.execute(
            "SELECT t.*,p.name AS project FROM tasks t LEFT JOIN projects p ON p.id=t.project_id ORDER BY t.created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return {"tasks": [dict(row) for row in rows]}


@app.get("/memory/source/{source_id}")
def source(source_id: str, current: CurrentRuntime) -> dict:
    with current.database.connect() as connection:
        row = connection.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Source not found")
        conversations = connection.execute("SELECT * FROM conversations WHERE source_id=?", (source_id,)).fetchall()
        messages = connection.execute(
            "SELECT msg.* FROM messages msg JOIN conversations c ON c.id=msg.conversation_id WHERE c.source_id=? ORDER BY msg.ordinal",
            (source_id,),
        ).fetchall()
    return {"source": dict(row), "conversations": [dict(item) for item in conversations], "messages": [dict(item) for item in messages]}


@app.get("/memory/{memory_id}")
def memory_detail(memory_id: str, current: CurrentRuntime) -> dict:
    try:
        memory = current.memories.get(memory_id)
    except KeyError as exc:
        raise HTTPException(404, "Memory not found") from exc
    with current.database.connect() as connection:
        versions = connection.execute("SELECT * FROM memory_versions WHERE memory_id=? ORDER BY version DESC", (memory_id,)).fetchall()
        relations = connection.execute("SELECT * FROM memory_relations WHERE from_memory_id=? OR to_memory_id=?", (memory_id, memory_id)).fetchall()
        conflict_rows = connection.execute("SELECT * FROM conflicts WHERE memory_id=? OR conflicting_memory_id=?", (memory_id, memory_id)).fetchall()
    return {"memory": memory, "versions": [dict(row) for row in versions], "relations": [dict(row) for row in relations], "conflicts": [dict(row) for row in conflict_rows]}


@app.post("/memory/conflicts/{conflict_id}/resolve")
def resolve_conflict(conflict_id: str, request: ConflictResolveRequest, current: CurrentRuntime) -> dict:
    with current.database.connect() as connection:
        conflict = connection.execute("SELECT * FROM conflicts WHERE id=?", (conflict_id,)).fetchone()
    if not conflict:
        raise HTTPException(404, "Conflict not found")
    old_id = conflict["conflicting_memory_id"]
    new_id = conflict["memory_id"]
    if request.action == "keep_old":
        current.memories.set_status(old_id, "active", request.reason)
        current.memories.set_status(new_id, "rejected", request.reason)
    elif request.action == "use_new":
        current.memories.supersede(old_id, new_id, None, request.reason)
    elif request.action == "keep_both":
        current.memories.set_status(old_id, "active", request.reason)
        current.memories.set_status(new_id, "active", request.reason)
        if request.target_project:
            project_id = current.memories.ensure_project(request.target_project)
            with current.database.connect() as connection:
                connection.execute("UPDATE memories SET project_id=?,updated_at=? WHERE id=?", (project_id, utc_now(), new_id))
    with current.database.connect() as connection:
        connection.execute("UPDATE conflicts SET status='resolved',resolved_at=? WHERE id=?", (utc_now(), conflict_id))
    return {"conflict_id": conflict_id, "status": "resolved", "action": request.action}


@app.get("/knowledge/documents")
def knowledge_documents(current: CurrentRuntime, limit: int = Query(100, ge=1, le=500)) -> dict:
    with current.database.connect() as connection:
        rows = connection.execute(
            "SELECT k.*,p.name AS project FROM knowledge_documents k LEFT JOIN projects p ON p.id=k.project_id ORDER BY k.updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["chunk_count"] = len(current.vectors.document_chunks(item["id"]))
        items.append(item)
    return {"documents": items}


@app.get("/knowledge/documents/{document_id}")
def knowledge_document(document_id: str, current: CurrentRuntime) -> dict:
    with current.database.connect() as connection:
        row = connection.execute(
            "SELECT k.*,p.name AS project FROM knowledge_documents k LEFT JOIN projects p ON p.id=k.project_id WHERE k.id=?",
            (document_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Knowledge document not found")
    return {"document": dict(row), "chunks": current.vectors.document_chunks(document_id)}


@app.post("/memory/rebuild-qdrant")
def rebuild_qdrant(current: CurrentRuntime) -> dict:
    return {"rebuilt": current.memories.rebuild_vectors()}


def _pid_running(pid: int) -> bool:
    result = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True, check=False)
    return str(pid) in result.stdout


def _watcher_status() -> dict:
    runtime = get_registry().get("production")
    pid_file = runtime.settings.runtime_dir / "watcher.pid"
    pid = None
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text(encoding="ascii").strip())
        except ValueError:
            pid = None
    workspace_file = runtime.settings.runtime_dir / "watcher.workspace"
    workspace = workspace_file.read_text(encoding="ascii").strip() if workspace_file.exists() else None
    return {
        "running": bool(pid and _pid_running(pid)),
        "pid": pid,
        "workspace": workspace,
        "pid_file": str(pid_file),
    }


@app.get("/system/status")
def system_status() -> dict:
    production = get_registry().get("production")
    acceptance_runtime = get_registry().get("acceptance")
    try:
        ollama = requests.get(f"{production.settings.ollama_url}/api/tags", timeout=3).ok
    except requests.RequestException:
        ollama = False
    return {
        "api": "ok",
        "ollama": ollama,
        "watcher": _watcher_status(),
        "production": _status(production),
        "acceptance": _status(acceptance_runtime),
    }


def _run_script(name: str, workspace: str | None = None) -> dict:
    script = ROOT / "scripts" / "second_brain" / name
    command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)]
    if workspace:
        command.extend(["-Workspace", workspace])
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )
    if result.returncode != 0:
        raise HTTPException(500, result.stderr.strip() or result.stdout.strip())
    return {"ok": True, "output": result.stdout.strip(), "status": _watcher_status()}


@app.get("/system/watcher/status")
def watcher_status() -> dict:
    return _watcher_status()


@app.post("/system/watcher/start")
def watcher_start(request: Request) -> dict:
    workspace = request.headers.get("X-LingJi-Workspace", "production").lower()
    if workspace not in WORKSPACES:
        raise HTTPException(400, f"Unknown workspace: {workspace}")
    current = _watcher_status()
    if current["running"]:
        return {"ok": True, "output": "Watcher already running", "status": current}
    script = ROOT / "scripts" / "second_brain" / "start-watcher.ps1"
    subprocess.Popen(
        [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(script), "-Workspace", workspace,
        ],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    for _ in range(20):
        time.sleep(0.25)
        current = _watcher_status()
        if current["running"]:
            return {"ok": True, "output": "Watcher started", "status": current}
    raise HTTPException(500, "Watcher did not start within five seconds")


@app.post("/system/watcher/stop")
def watcher_stop() -> dict:
    return _run_script("stop-watcher.ps1")


@app.post("/system/watcher/scan-once")
def watcher_scan_once(current: CurrentRuntime, request: Request) -> dict:
    workspace = request.headers.get("X-LingJi-Workspace", "production").lower()
    if _watcher_status()["running"]:
        raise HTTPException(409, "Stop the resident watcher before a manual scan")
    watcher = BoundedWatcher("http://127.0.0.1:8765", current.settings, workspace)
    return watcher.scan_once()


@app.get("/system/logs")
def system_logs(component: str = Query("api", pattern="^(api|watcher)$"), lines: int = Query(200, ge=1, le=2000)) -> dict:
    allowed = {
        "api": ROOT / "logs" / "second_brain" / "api.stderr.log",
        "watcher": ROOT / "logs" / "second_brain" / "watcher.log",
    }
    path = allowed[component].resolve()
    if not path.exists():
        return {"component": component, "path": str(path), "lines": []}
    content = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    return {"component": component, "path": str(path), "lines": content[-lines:]}


@app.post("/acceptance/reset")
def acceptance_reset() -> dict:
    if acceptance is None:
        raise HTTPException(503, "Acceptance service unavailable")
    return acceptance.reset()


@app.post("/acceptance/seed")
def acceptance_seed() -> dict:
    runtime = get_registry().get("acceptance")
    note = runtime.settings.obsidian_knowledge_dir / "sample" / "seed.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text("# 验收知识\n\n#seed\n\n这是验收库人工知识。", encoding="utf-8")
    return {"seeded": True, "obsidian": str(note)}


@app.post("/acceptance/run-all")
def acceptance_run_all() -> dict:
    if acceptance is None:
        raise HTTPException(503, "Acceptance service unavailable")
    return acceptance.run_all()


@app.post("/acceptance/run/{scenario}")
def acceptance_run_scenario(scenario: str) -> dict:
    if acceptance is None:
        raise HTTPException(503, "Acceptance service unavailable")
    report = acceptance.run_all()
    result = next((item for item in report["results"] if item["name"] == scenario), None)
    if result is None:
        raise HTTPException(404, f"Unknown scenario: {scenario}")
    return result


@app.get("/acceptance/results/latest")
def acceptance_latest() -> dict:
    if acceptance is None:
        raise HTTPException(503, "Acceptance service unavailable")
    return acceptance.latest()
