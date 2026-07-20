from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .chunker import MarkdownChunker
from .incremental_sync import IncrementalMemorySynchronizer
from .memory_db import MemoryDatabase
from .semantic import SemanticIndexProvider, SemanticPoint


@dataclass(frozen=True)
class SemanticSyncWarning:
    code: str
    stage: str
    message: str
    chunk_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SemanticSyncResult:
    status: str
    upserted: int = 0
    deleted: int = 0
    failed: int = 0
    added: int = 0
    updated: int = 0
    removed: int = 0
    warnings: list[SemanticSyncWarning] = field(default_factory=list)

    @property
    def degraded(self) -> bool:
        return self.status == "degraded"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "degraded": self.degraded,
            "upserted": self.upserted,
            "deleted": self.deleted,
            "failed": self.failed,
            "added": self.added,
            "updated": self.updated,
            "removed": self.removed,
            "warnings": [warning.to_dict() for warning in self.warnings],
        }


@dataclass(frozen=True)
class _SemanticSnapshot:
    point: SemanticPoint
    fingerprint: str


class MemoryIndexCoordinator:
    """Synchronize the canonical lexical index and an optional semantic index.

    The lexical index is committed first and remains usable when embedding or
    Qdrant fails. Semantic failures are returned as structured degradation
    warnings rather than rolling back the rebuildable SQLite index.
    """

    def __init__(
        self,
        database: MemoryDatabase,
        semantic_provider: SemanticIndexProvider | None = None,
        *,
        state_db: Any | None = None,
        semantic_batch_size: int = 64,
    ):
        batch_size = int(semantic_batch_size)
        if batch_size <= 0:
            raise ValueError("semantic_batch_size must be greater than zero")
        self.database = database
        self.semantic_provider = semantic_provider
        self.state_db = state_db
        self.semantic_batch_size = batch_size

    def sync(
        self,
        entries: Iterable[dict[str, Any]],
        vault_root: Path | str,
        chunker: MarkdownChunker | None = None,
        *,
        force: bool = False,
    ) -> dict[str, Any]:
        selected_entries = list(entries)
        before = self._snapshot()
        integrity = self.database.integrity_check()
        full_rebuild = bool(force or not integrity.get("healthy", False))

        if full_rebuild:
            lexical: dict[str, Any] = self.database.rebuild_from_index(
                selected_entries,
                vault_root,
                chunker,
            )
            lexical["full_rebuild"] = True
        else:
            lexical = IncrementalMemorySynchronizer(self.database).sync(
                selected_entries,
                vault_root,
                chunker,
            )

        after = self._snapshot()
        semantic = self._sync_semantic(before, after, full_rebuild=full_rebuild)
        result = {
            **lexical,
            "semantic": semantic.to_dict(),
            "degraded": semantic.degraded,
            "warnings": [warning.to_dict() for warning in semantic.warnings],
        }
        self._record_event(
            "memory_index_sync_degraded" if semantic.degraded else "memory_index_coordinated",
            result,
        )
        return result

    def _sync_semantic(
        self,
        before: dict[str, _SemanticSnapshot],
        after: dict[str, _SemanticSnapshot],
        *,
        full_rebuild: bool,
    ) -> SemanticSyncResult:
        if self.semantic_provider is None:
            return SemanticSyncResult(status="disabled")

        before_ids = set(before)
        after_ids = set(after)
        removed_ids = sorted(before_ids - after_ids)
        added_ids = sorted(after_ids - before_ids)
        updated_ids = sorted(
            chunk_id
            for chunk_id in before_ids & after_ids
            if before[chunk_id].fingerprint != after[chunk_id].fingerprint
        )
        upsert_ids = sorted(after_ids) if full_rebuild else [*added_ids, *updated_ids]
        sync = SemanticSyncResult(
            status="healthy",
            added=len(added_ids),
            updated=len(updated_ids),
            removed=len(removed_ids),
        )

        for chunk_id in removed_ids:
            try:
                self.semantic_provider.delete(chunk_id)
                sync.deleted += 1
            except Exception as exc:
                sync.status = "degraded"
                sync.failed += 1
                sync.warnings.append(
                    SemanticSyncWarning(
                        code="semantic_delete_failed",
                        stage="delete",
                        chunk_id=chunk_id,
                        message=self._safe_error(exc),
                    )
                )

        for start in range(0, len(upsert_ids), self.semantic_batch_size):
            batch_ids = upsert_ids[start : start + self.semantic_batch_size]
            points = [after[chunk_id].point for chunk_id in batch_ids]
            try:
                indexed_ids = self.semantic_provider.upsert_many(points)
                if len(indexed_ids) != len(points):
                    raise RuntimeError(
                        f"Semantic provider indexed {len(indexed_ids)} of {len(points)} points"
                    )
                sync.upserted += len(points)
            except Exception as exc:
                sync.status = "degraded"
                sync.failed += len(points)
                sync.warnings.append(
                    SemanticSyncWarning(
                        code="semantic_upsert_failed",
                        stage="upsert",
                        message=self._safe_error(exc),
                    )
                )

        return sync

    def _snapshot(self) -> dict[str, _SemanticSnapshot]:
        with self.database._connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    c.chunk_id,
                    c.memory_id,
                    c.heading,
                    c.text,
                    c.start_line,
                    c.end_line,
                    c.content_hash AS chunk_content_hash,
                    d.relative_path,
                    d.title,
                    d.memory_type,
                    d.memory_tier,
                    d.status,
                    d.review_status,
                    d.privacy,
                    d.importance,
                    d.confidence,
                    d.project_json,
                    d.tags_json,
                    d.valid_from,
                    d.valid_to,
                    d.superseded_by,
                    d.pin_to_context,
                    d.agent_scope_json,
                    d.recall_weight,
                    d.content_hash AS document_content_hash,
                    d.modified_at,
                    d.updated_at
                FROM memory_chunks c
                JOIN memory_documents d ON d.memory_id = c.memory_id
                ORDER BY c.memory_id, c.ordinal
                """
            ).fetchall()

        output: dict[str, _SemanticSnapshot] = {}
        for row in rows:
            item = dict(row)
            chunk_id = str(item["chunk_id"])
            memory_id = str(item["memory_id"])
            payload = {
                "kind": "memory_chunk",
                "memory_id": memory_id,
                "chunk_id": chunk_id,
                "title": str(item.get("title") or memory_id),
                "heading": str(item.get("heading") or ""),
                "relative_path": str(item.get("relative_path") or ""),
                "memory_type": str(item.get("memory_type") or "note"),
                "memory_tier": str(item.get("memory_tier") or "archival"),
                "status": str(item.get("status") or "active"),
                "review_status": str(item.get("review_status") or ""),
                "privacy": str(item.get("privacy") or "private"),
                "importance": str(item.get("importance") or ""),
                "confidence": str(item.get("confidence") or ""),
                "project": self._loads(item.get("project_json"), []),
                "tags": self._loads(item.get("tags_json"), []),
                "agent_scope": self._loads(item.get("agent_scope_json"), []),
                "valid_from": item.get("valid_from"),
                "valid_to": item.get("valid_to"),
                "superseded_by": str(item.get("superseded_by") or ""),
                "pin_to_context": bool(item.get("pin_to_context")),
                "recall_weight": float(item.get("recall_weight") or 1.0),
                "start_line": int(item.get("start_line") or 0),
                "end_line": int(item.get("end_line") or 0),
                "content_hash": str(item.get("chunk_content_hash") or ""),
                "document_content_hash": str(item.get("document_content_hash") or ""),
                "modified_at": str(item.get("modified_at") or ""),
                "updated_at": str(item.get("updated_at") or ""),
            }
            text = str(item.get("text") or "")
            point = SemanticPoint(
                chunk_id=chunk_id,
                memory_id=memory_id,
                text=text,
                payload=payload,
            )
            output[chunk_id] = _SemanticSnapshot(
                point=point,
                fingerprint=self._fingerprint(text, payload),
            )
        return output

    @staticmethod
    def _fingerprint(text: str, payload: dict[str, Any]) -> str:
        encoded = json.dumps(
            {"text": text, "payload": payload},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _loads(value: Any, fallback: Any) -> Any:
        if value in (None, ""):
            return fallback
        try:
            return json.loads(str(value))
        except (TypeError, ValueError, json.JSONDecodeError):
            return fallback

    def _record_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.state_db is None:
            return
        try:
            self.state_db.append_event(
                event_type,
                "memory_index",
                "coordinator",
                payload,
            )
        except Exception:
            return

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        return f"{type(exc).__name__}: {exc}"[:500]
