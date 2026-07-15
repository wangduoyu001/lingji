from __future__ import annotations

import json
import re
from pathlib import Path

from second_brain.chunking import chunk_text
from second_brain.db import Database
from second_brain.embedding import OllamaEmbedder
from second_brain.memory.service import MemoryService
from second_brain.utils import deterministic_id, new_id, stable_hash, utc_now
from second_brain.vector_store import VectorStore


class ObsidianConnector:
    """Indexes user-authored Markdown without distilling it into memories."""

    def __init__(
        self,
        database: Database,
        memories: MemoryService,
        embedder: OllamaEmbedder,
        vectors: VectorStore,
        root: Path | None,
    ):
        self.database = database
        self.memories = memories
        self.embedder = embedder
        self.vectors = vectors
        self.root = root.resolve() if root else None

    def index_file(self, raw_path: str | Path) -> dict:
        if self.root is None:
            raise ValueError("Obsidian knowledge directory is not configured")
        path = Path(raw_path).resolve()
        if path.suffix.lower() != ".md" or self.root not in path.parents:
            raise ValueError(f"Only Markdown under {self.root} can be indexed")
        content = path.read_text(encoding="utf-8-sig")
        content_hash = stable_hash(content)
        relative = path.relative_to(self.root).as_posix()
        title = self._title(content, path.stem)
        tags = sorted(set(re.findall(r"(?<!\w)#([\w\u4e00-\u9fff/-]+)", content)))
        project = relative.split("/", 1)[0] if "/" in relative else "global"
        project_id = self.memories.ensure_project(project)
        now = utc_now()
        with self.database.connect() as connection:
            existing = connection.execute(
                "SELECT id,version,content_hash FROM knowledge_documents WHERE source_path=?", (str(path),)
            ).fetchone()
            if existing and existing["content_hash"] == content_hash:
                return {"document_id": existing["id"], "indexed": False, "duplicate": True}
            document_id = existing["id"] if existing else new_id()
            version = int(existing["version"]) + 1 if existing else 1
            connection.execute(
                """INSERT INTO knowledge_documents(
                    id,source_path,project_id,title,content,tags_json,version,content_hash,indexed_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(source_path) DO UPDATE SET
                    project_id=excluded.project_id,title=excluded.title,content=excluded.content,
                    tags_json=excluded.tags_json,version=excluded.version,content_hash=excluded.content_hash,
                    indexed_at=excluded.indexed_at,updated_at=excluded.updated_at""",
                (
                    document_id, str(path), project_id, title, content,
                    json.dumps(tags, ensure_ascii=False), version, content_hash, now, now,
                ),
            )
        self.vectors.delete_document(document_id)
        chunks = chunk_text(content)
        for index, chunk in enumerate(chunks):
            vector = self.embedder.embed(f"{title}\n{chunk}")
            self.vectors.upsert(
                deterministic_id(document_id, str(index)),
                vector,
                {
                    "kind": "knowledge", "document_id": document_id, "chunk_index": index,
                    "title": title, "content": chunk, "project": project, "source_path": str(path),
                },
            )
        return {
            "document_id": document_id, "indexed": True, "duplicate": False,
            "version": version, "chunks": len(chunks),
        }

    def index_all(self) -> dict:
        if self.root is None:
            return {"configured": False, "indexed": 0, "skipped": 0}
        indexed = skipped = 0
        for path in self.root.rglob("*.md"):
            if ".obsidian" in path.parts or ".git" in path.parts:
                continue
            result = self.index_file(path)
            indexed += int(result["indexed"])
            skipped += int(not result["indexed"])
        return {"configured": True, "indexed": indexed, "skipped": skipped}

    @staticmethod
    def _title(content: str, fallback: str) -> str:
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        return match.group(1).strip() if match else fallback
