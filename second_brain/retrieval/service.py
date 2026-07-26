from __future__ import annotations

import json

from second_brain.db import Database
from second_brain.embedding import OllamaEmbedder
from second_brain.utils import new_id, utc_now
from second_brain.vector_store import VectorStore


class RetrievalService:
    def __init__(self, database: Database, embedder: OllamaEmbedder, vectors: VectorStore):
        self.database = database
        self.embedder = embedder
        self.vectors = vectors

    def search(
        self,
        query: str,
        project: str | None = None,
        memory_types: list[str] | None = None,
        active_only: bool = True,
        top_k: int = 10,
        include_knowledge: bool = True,
    ) -> list[dict]:
        project_names = {"global", project} if project else set()
        memory_types = [item.upper() for item in (memory_types or [])]
        like = f"%{query}%"
        status_clause = "AND m.status='active'" if active_only else ""
        type_clause = ""
        params: list[object] = [like, like]
        if memory_types:
            placeholders = ",".join("?" for _ in memory_types)
            type_clause = f"AND m.memory_type IN ({placeholders})"
            params.extend(memory_types)
        project_clause = ""
        if project_names:
            placeholders = ",".join("?" for _ in project_names)
            project_clause = f"AND p.name IN ({placeholders})"
            params.extend(sorted(project_names))
        with self.database.connect() as connection:
            memory_rows = connection.execute(
                f"""SELECT m.*, p.name AS project FROM memories m
                LEFT JOIN projects p ON p.id=m.project_id
                WHERE (m.title LIKE ? OR m.content LIKE ?) {status_clause} {type_clause} {project_clause}
                ORDER BY m.importance DESC, m.updated_at DESC LIMIT ?""",
                (*params, top_k * 2),
            ).fetchall()
            knowledge_rows = []
            if include_knowledge:
                knowledge_params: list[object] = [like, like]
                knowledge_project = ""
                if project_names:
                    placeholders = ",".join("?" for _ in project_names)
                    knowledge_project = f"AND p.name IN ({placeholders})"
                    knowledge_params.extend(sorted(project_names))
                knowledge_rows = connection.execute(
                    f"""SELECT k.*, p.name AS project FROM knowledge_documents k
                    LEFT JOIN projects p ON p.id=k.project_id
                    WHERE (k.title LIKE ? OR k.content LIKE ?) {knowledge_project}
                    ORDER BY k.updated_at DESC LIMIT ?""",
                    (*knowledge_params, top_k),
                ).fetchall()

        ranked: dict[str, dict] = {}
        for row in memory_rows:
            item = dict(row)
            item.update({"kind": "memory", "score": 0.55})
            ranked[item["id"]] = item
        for row in knowledge_rows:
            item = dict(row)
            item.update({"kind": "knowledge", "score": 0.65})
            ranked[item["id"]] = item

        try:
            vector = self.embedder.embed(query)
            for result in self.vectors.search(vector, limit=top_k * 4):
                payload = result["payload"]
                if project_names and payload.get("project", "global") not in project_names:
                    continue
                if payload.get("kind") == "knowledge" and not include_knowledge:
                    continue
                if payload.get("kind") == "memory" and active_only and payload.get("status") != "active":
                    continue
                if memory_types and payload.get("kind") == "memory" and payload.get("memory_type") not in memory_types:
                    continue
                item = ranked.get(result["id"], {"id": result["id"], **payload})
                item["score"] = max(float(item.get("score", 0)), 0.7 * result["score"])
                item.setdefault("kind", payload.get("kind", "memory"))
                ranked[result["id"]] = item
        except Exception as exc:
            ranked["vector-warning"] = {"id": "vector-warning", "kind": "warning", "score": 0, "content": str(exc)}

        results = sorted(ranked.values(), key=lambda item: item.get("score", 0), reverse=True)[:top_k]
        result_ids = [item["id"] for item in results if item["id"] != "vector-warning"]
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO retrieval_logs(id,query,project_id,result_ids_json,created_at) VALUES(?,?,?,?,?)",
                (new_id(), query, project, json.dumps(result_ids), utc_now()),
            )
        return results

    def context(self, project: str, task: str, max_tokens: int) -> dict:
        results = self.search(task, project=project, top_k=20, include_knowledge=True)
        budget_chars = max_tokens * 3
        selected = []
        used = 0
        for item in results:
            content = str(item.get("content", ""))
            if used + len(content) > budget_chars:
                continue
            selected.append(item)
            used += len(content)
        return {
            "project": project,
            "task": task,
            "formal_knowledge": [item for item in selected if item.get("kind") == "knowledge"],
            "active_rules": [item for item in selected if item.get("memory_type") == "RULE"],
            "recent_decisions": [item for item in selected if item.get("memory_type") == "DECISION"],
            "known_failures": [item for item in selected if item.get("memory_type") == "LESSON"],
            "preferences": [item for item in selected if item.get("memory_type") == "PREFERENCE"],
            "source_refs": [item.get("source_path") or item.get("source_id") for item in selected],
            "approx_tokens": used // 3,
        }
