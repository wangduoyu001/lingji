from __future__ import annotations

import json
import sqlite3

from second_brain.chunking import chunk_text
from second_brain.db import Database, rows_to_dicts
from second_brain.embedding import OllamaEmbedder
from second_brain.utils import deterministic_id, new_id, stable_hash, utc_now
from second_brain.vector_store import VectorStore


VALID_STATUSES = {"pending", "active", "superseded", "conflicted", "rejected", "archived", "deleted"}


class MemoryService:
    def __init__(self, database: Database, embedder: OllamaEmbedder, vectors: VectorStore):
        self.database = database
        self.embedder = embedder
        self.vectors = vectors

    def ensure_project(self, name: str) -> str:
        clean_name = name.strip() or "global"
        with self.database.connect() as connection:
            row = connection.execute("SELECT id FROM projects WHERE name=?", (clean_name,)).fetchone()
            if row:
                return str(row["id"])
            project_id = new_id()
            now = utc_now()
            connection.execute(
                "INSERT INTO projects(id,name,created_at,updated_at) VALUES(?,?,?,?)",
                (project_id, clean_name, now, now),
            )
            return project_id

    def create(
        self,
        memory_type: str,
        title: str,
        content: str,
        project: str = "global",
        status: str = "pending",
        importance: float = 0.5,
        confidence: float = 0.5,
        source_id: str | None = None,
        source_excerpt: str | None = None,
        valid_from: str | None = None,
    ) -> tuple[dict, bool]:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid memory status: {status}")
        project_id = self.ensure_project(project)
        content_hash = stable_hash({"type": memory_type, "title": title, "content": content})
        now = utc_now()
        memory_id = new_id()
        try:
            with self.database.connect() as connection:
                connection.execute(
                    """INSERT INTO memories(
                        id,memory_type,title,content,project_id,status,importance,confidence,
                        valid_from,source_id,source_excerpt,content_hash,created_at,updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        memory_id, memory_type.upper(), title, content, project_id, status,
                        importance, confidence, valid_from or now, source_id, source_excerpt,
                        content_hash, now, now,
                    ),
                )
                connection.execute(
                    "INSERT INTO memory_versions(id,memory_id,version,content,status,changed_at,change_reason) VALUES(?,?,?,?,?,?,?)",
                    (new_id(), memory_id, 1, content, status, now, "created"),
                )
        except sqlite3.IntegrityError:
            with self.database.connect() as connection:
                row = connection.execute(
                    "SELECT m.*, p.name AS project FROM memories m LEFT JOIN projects p ON p.id=m.project_id WHERE m.content_hash=? AND m.project_id=?",
                    (content_hash, project_id),
                ).fetchone()
            return dict(row), False
        memory = self.get(memory_id)
        if status == "active":
            self._index(memory)
        return memory, True

    def get(self, memory_id: str) -> dict:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT m.*, p.name AS project FROM memories m LEFT JOIN projects p ON p.id=m.project_id WHERE m.id=?",
                (memory_id,),
            ).fetchone()
        if not row:
            raise KeyError(memory_id)
        return dict(row)

    def set_status(self, memory_id: str, status: str, reason: str | None = None) -> dict:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid memory status: {status}")
        memory = self.get(memory_id)
        now = utc_now()
        with self.database.connect() as connection:
            version = connection.execute(
                "SELECT COALESCE(MAX(version),0)+1 AS version FROM memory_versions WHERE memory_id=?",
                (memory_id,),
            ).fetchone()["version"]
            connection.execute("UPDATE memories SET status=?, updated_at=? WHERE id=?", (status, now, memory_id))
            connection.execute(
                "INSERT INTO memory_versions(id,memory_id,version,content,status,changed_at,change_reason) VALUES(?,?,?,?,?,?,?)",
                (new_id(), memory_id, version, memory["content"], status, now, reason),
            )
        updated = self.get(memory_id)
        if status == "active":
            self._index(updated)
        else:
            self.vectors.delete(memory_id)
        return updated

    def supersede(
        self,
        old_memory_id: str,
        new_memory_id: str | None,
        new_memory: dict | None,
        reason: str,
    ) -> dict:
        old = self.get(old_memory_id)
        if new_memory_id is None:
            if not new_memory:
                raise ValueError("new_memory_id or new_memory is required")
            created, _ = self.create(
                memory_type=new_memory.get("memory_type", old["memory_type"]),
                title=new_memory.get("title", old["title"]),
                content=new_memory["content"],
                project=new_memory.get("project", old["project"]),
                status="active",
                importance=float(new_memory.get("importance", old["importance"])),
                confidence=float(new_memory.get("confidence", old["confidence"])),
                source_id=new_memory.get("source_id"),
            )
            new_memory_id = created["id"]
        newer = self.get(new_memory_id)
        if newer["status"] != "active":
            newer = self.set_status(new_memory_id, "active", reason)
        now = utc_now()
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE memories SET status='superseded', valid_to=?, updated_at=? WHERE id=?",
                (now, now, old_memory_id),
            )
            connection.execute(
                "UPDATE memories SET supersedes_id=?, updated_at=? WHERE id=?",
                (old_memory_id, now, new_memory_id),
            )
            connection.execute(
                "INSERT OR IGNORE INTO memory_relations(id,from_memory_id,to_memory_id,relation_type,created_at) VALUES(?,?,?,?,?)",
                (new_id(), new_memory_id, old_memory_id, "supersedes", now),
            )
            old_version = connection.execute(
                "SELECT COALESCE(MAX(version),0)+1 AS version FROM memory_versions WHERE memory_id=?",
                (old_memory_id,),
            ).fetchone()["version"]
            connection.execute(
                "INSERT INTO memory_versions(id,memory_id,version,content,status,changed_at,change_reason) VALUES(?,?,?,?,?,?,?)",
                (new_id(), old_memory_id, old_version, old["content"], "superseded", now, reason),
            )
        self.vectors.delete(old_memory_id)
        self._index(newer)
        return {"old": self.get(old_memory_id), "new": self.get(new_memory_id)}

    def pending(self) -> list[dict]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT m.*, p.name AS project FROM memories m LEFT JOIN projects p ON p.id=m.project_id WHERE m.status='pending' ORDER BY m.created_at DESC"
            ).fetchall()
        return rows_to_dicts(rows)

    def _index(self, memory: dict) -> None:
        vector = self.embedder.embed(f"{memory['title']}\n{memory['content']}")
        self.vectors.upsert(
            memory["id"],
            vector,
            {
                "kind": "memory",
                "title": memory["title"],
                "content": memory["content"],
                "memory_type": memory["memory_type"],
                "project": memory.get("project") or "global",
                "status": memory["status"],
            },
        )

    def rebuild_vectors(self) -> int:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT m.*, p.name AS project FROM memories m LEFT JOIN projects p ON p.id=m.project_id WHERE m.status='active'"
            ).fetchall()
            knowledge_rows = connection.execute(
                "SELECT k.*, p.name AS project FROM knowledge_documents k LEFT JOIN projects p ON p.id=k.project_id"
            ).fetchall()
        items = []
        for row in rows:
            memory = dict(row)
            vector = self.embedder.embed(f"{memory['title']}\n{memory['content']}")
            payload = {
                "kind": "memory", "title": memory["title"], "content": memory["content"],
                "memory_type": memory["memory_type"], "project": memory.get("project") or "global",
                "status": "active",
            }
            items.append((memory["id"], vector, payload))
        for row in knowledge_rows:
            document = dict(row)
            for index, chunk in enumerate(chunk_text(document["content"])):
                vector = self.embedder.embed(f"{document['title']}\n{chunk}")
                payload = {
                    "kind": "knowledge", "document_id": document["id"], "chunk_index": index,
                    "title": document["title"], "content": chunk,
                    "project": document.get("project") or "global", "source_path": document["source_path"],
                }
                items.append((deterministic_id(document["id"], str(index)), vector, payload))
        return self.vectors.recreate(items)
