from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from second_brain.models import (
    CodexTaskRequest,
    ContextRequest,
    DistillRequest,
    ImportRequest,
    KnowledgeIndexRequest,
    ReviewRequest,
    SearchRequest,
    SupersedeRequest,
)
from second_brain.runtime import Runtime, build_runtime


logger = logging.getLogger("second_brain.api")
runtime: Runtime | None = None


def get_runtime() -> Runtime:
    if runtime is None:
        raise RuntimeError("Second-brain runtime is not initialized")
    return runtime


@asynccontextmanager
async def lifespan(_: FastAPI):
    global runtime
    runtime = build_runtime()
    yield
    runtime.close()
    runtime = None


app = FastAPI(title="LingJi Second Brain", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    current = get_runtime()
    return {"status": "ok", "service": "lingji-second-brain", "qdrant": current.vectors.status()}


@app.post("/memory/import")
def import_memory(request: ImportRequest) -> dict:
    current = get_runtime()
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
def search(request: SearchRequest) -> dict:
    return {"results": get_runtime().retrieval.search(**request.model_dump())}


@app.post("/memory/context")
def context(request: ContextRequest) -> dict:
    return get_runtime().retrieval.context(request.project, request.task, request.max_tokens)


@app.post("/memory/distill")
def distill(request: DistillRequest) -> dict:
    return {"candidates": get_runtime().distillation.distill(request.conversation_id, request.source_id)}


@app.post("/memory/approve")
def approve(request: ReviewRequest) -> dict:
    try:
        memory = get_runtime().memories.set_status(request.memory_id, "active", request.reason or "approved")
        conflicts = get_runtime().conflicts.detect_for(request.memory_id)
        return {"memory": memory, "conflicts": conflicts}
    except KeyError as exc:
        raise HTTPException(404, f"Memory not found: {exc.args[0]}") from exc


@app.post("/memory/reject")
def reject(request: ReviewRequest) -> dict:
    try:
        return {"memory": get_runtime().memories.set_status(request.memory_id, "rejected", request.reason or "rejected")}
    except KeyError as exc:
        raise HTTPException(404, f"Memory not found: {exc.args[0]}") from exc


@app.post("/memory/supersede")
def supersede(request: SupersedeRequest) -> dict:
    try:
        return get_runtime().memories.supersede(
            request.old_memory_id, request.new_memory_id, request.new_memory, request.reason
        )
    except KeyError as exc:
        raise HTTPException(404, f"Memory not found: {exc.args[0]}") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/memory/codex-task")
def codex_task(request: CodexTaskRequest) -> dict:
    return get_runtime().codex.record(request)


@app.post("/knowledge/index")
def index_knowledge(request: KnowledgeIndexRequest) -> dict:
    try:
        return get_runtime().obsidian.index_file(request.path)
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/memory/status")
def status() -> dict:
    current = get_runtime()
    with current.database.connect() as connection:
        counts = {
            table: connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"]
            for table in ("sources", "conversations", "messages", "memories", "knowledge_documents", "tasks")
        }
        states = {
            row["status"]: row["count"]
            for row in connection.execute("SELECT status,COUNT(*) AS count FROM memories GROUP BY status").fetchall()
        }
    return {
        "counts": counts,
        "memory_states": states,
        "qdrant": current.vectors.status(),
        "embedding": current.embedder.status(),
        "watch_roots": {
            "ai_chat": str(current.settings.ai_inbox_dir),
            "codex_tasks": str(current.settings.codex_inbox_dir),
            "obsidian": str(current.settings.obsidian_knowledge_dir) if current.settings.obsidian_knowledge_dir else None,
        },
    }


@app.get("/memory/conflicts")
def conflicts() -> dict:
    return {"conflicts": get_runtime().conflicts.list_open()}


@app.get("/memory/pending")
def pending() -> dict:
    return {"memories": get_runtime().memories.pending()}


@app.get("/memory/projects")
def projects() -> dict:
    current = get_runtime()
    with current.database.connect() as connection:
        rows = connection.execute("SELECT * FROM projects ORDER BY name").fetchall()
    return {"projects": [dict(row) for row in rows]}


@app.get("/memory/timeline")
def timeline(limit: int = 100) -> dict:
    current = get_runtime()
    safe_limit = max(1, min(limit, 500))
    with current.database.connect() as connection:
        rows = connection.execute(
            """SELECT 'memory' AS kind,id,title AS summary,created_at FROM memories
            UNION ALL SELECT 'task',id,request,created_at FROM tasks
            ORDER BY created_at DESC LIMIT ?""",
            (safe_limit,),
        ).fetchall()
    return {"events": [dict(row) for row in rows]}


@app.get("/memory/source/{source_id}")
def source(source_id: str) -> dict:
    current = get_runtime()
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


@app.post("/memory/rebuild-qdrant")
def rebuild_qdrant() -> dict:
    return {"rebuilt": get_runtime().memories.rebuild_vectors()}
