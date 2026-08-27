from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

from src.retrieval.chunker import MarkdownChunk, MarkdownChunker
from src.retrieval.temporal import ALL_LIFECYCLE_STATUSES, TemporalQuery, parse_instant, temporal_fields

SCHEMA_VERSION = "1"


class MemoryDatabase:
    """Rebuildable SQLite memory index with FTS5 chunk search.

    Obsidian remains the canonical memory store. This database contains derived
    document metadata and chunks only, so it can be deleted and rebuilt safely.
    """

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._fts_tokenizer = "trigram"
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA temp_store = MEMORY")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._lock, self._connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS memory_documents (
                    memory_id TEXT PRIMARY KEY,
                    relative_path TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    aliases_json TEXT NOT NULL DEFAULT '[]',
                    memory_type TEXT NOT NULL DEFAULT 'note',
                    memory_tier TEXT NOT NULL DEFAULT 'archival',
                    status TEXT NOT NULL DEFAULT 'active',
                    review_status TEXT,
                    privacy TEXT NOT NULL DEFAULT 'private',
                    importance TEXT,
                    confidence TEXT,
                    project_json TEXT NOT NULL DEFAULT '[]',
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    relationships_json TEXT NOT NULL DEFAULT '{}',
                    valid_from TEXT,
                    valid_to TEXT,
                    superseded_by TEXT,
                    pin_to_context INTEGER NOT NULL DEFAULT 0,
                    agent_scope_json TEXT NOT NULL DEFAULT '[]',
                    recall_weight REAL NOT NULL DEFAULT 1.0,
                    content_hash TEXT NOT NULL,
                    modified_at TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS memory_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL,
                    ordinal INTEGER NOT NULL,
                    heading TEXT NOT NULL DEFAULT '',
                    text TEXT NOT NULL,
                    start_line INTEGER NOT NULL,
                    end_line INTEGER NOT NULL,
                    char_count INTEGER NOT NULL,
                    content_hash TEXT NOT NULL,
                    FOREIGN KEY(memory_id) REFERENCES memory_documents(memory_id) ON DELETE CASCADE,
                    UNIQUE(memory_id, ordinal)
                );

                CREATE TABLE IF NOT EXISTS memory_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_memory_documents_type
                    ON memory_documents(memory_type, status, privacy);
                CREATE INDEX IF NOT EXISTS idx_memory_documents_tier
                    ON memory_documents(memory_tier, pin_to_context, recall_weight);
                CREATE INDEX IF NOT EXISTS idx_memory_documents_time
                    ON memory_documents(valid_from, valid_to);
                CREATE INDEX IF NOT EXISTS idx_memory_chunks_memory
                    ON memory_chunks(memory_id, ordinal);
                """
            )
            self._ensure_fts(connection)
            self._set_meta(connection, "schema_version", SCHEMA_VERSION)
            if self._get_meta(connection, "revision") is None:
                self._set_meta(connection, "revision", "0")

    def _ensure_fts(self, connection: sqlite3.Connection) -> None:
        existing = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='memory_fts'"
        ).fetchone()
        if existing:
            sql = str(existing["sql"] or "")
            self._fts_tokenizer = "trigram" if "trigram" in sql.lower() else "unicode61"
            self._set_meta(connection, "fts_tokenizer", self._fts_tokenizer)
            return
        try:
            connection.execute(
                """
                CREATE VIRTUAL TABLE memory_fts USING fts5(
                    chunk_id UNINDEXED,
                    memory_id UNINDEXED,
                    title,
                    heading,
                    text,
                    tags,
                    tokenize='trigram'
                )
                """
            )
            self._fts_tokenizer = "trigram"
        except sqlite3.OperationalError:
            connection.execute(
                """
                CREATE VIRTUAL TABLE memory_fts USING fts5(
                    chunk_id UNINDEXED,
                    memory_id UNINDEXED,
                    title,
                    heading,
                    text,
                    tags,
                    tokenize='unicode61 remove_diacritics 2'
                )
                """
            )
            self._fts_tokenizer = "unicode61"
        self._set_meta(connection, "fts_tokenizer", self._fts_tokenizer)

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value if value is not None else [], ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _loads(value: Any, fallback: Any) -> Any:
        if value in (None, ""):
            return fallback
        try:
            return json.loads(str(value))
        except (TypeError, ValueError, json.JSONDecodeError):
            return fallback

    @staticmethod
    def _as_list(value: Any) -> list[Any]:
        if value in (None, ""):
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, (tuple, set)):
            return list(value)
        return [value]

    @staticmethod
    def _as_float(value: Any, default: float = 1.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _as_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value or "").strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _set_meta(connection: sqlite3.Connection, key: str, value: str) -> None:
        connection.execute(
            """
            INSERT INTO memory_meta(key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, str(value)),
        )

    @staticmethod
    def _get_meta(connection: sqlite3.Connection, key: str) -> str | None:
        row = connection.execute("SELECT value FROM memory_meta WHERE key = ?", (key,)).fetchone()
        return str(row["value"]) if row else None

    def _bump_revision(self, connection: sqlite3.Connection) -> int:
        revision = int(self._get_meta(connection, "revision") or 0) + 1
        self._set_meta(connection, "revision", str(revision))
        return revision

    @property
    def revision(self) -> int:
        with self._connection() as connection:
            return int(self._get_meta(connection, "revision") or 0)

    @property
    def fts_tokenizer(self) -> str:
        return self._fts_tokenizer

    def rebuild_from_index(
        self,
        entries: Iterable[dict[str, Any]],
        vault_root: Path | str,
        chunker: MarkdownChunker | None = None,
        memory_scope: Any | None = None,
    ) -> dict[str, int]:
        root = Path(vault_root)
        chunker = chunker or MarkdownChunker()
        documents = 0
        chunks = 0
        skipped = 0
        with self._lock, self._connection() as connection:
            # Structured message evidence is sourced from the read model, not
            # the Vault. A normal Vault rebuild must leave that projection
            # intact so a later source import remains searchable.
            connection.execute(
                "DELETE FROM memory_fts WHERE memory_id IN "
                "(SELECT memory_id FROM memory_documents WHERE memory_type <> 'structured_evidence')"
            )
            connection.execute(
                "DELETE FROM memory_chunks WHERE memory_id IN "
                "(SELECT memory_id FROM memory_documents WHERE memory_type <> 'structured_evidence')"
            )
            connection.execute(
                "DELETE FROM memory_documents WHERE memory_type <> 'structured_evidence'"
            )
            for entry in entries:
                relative_path = str(entry.get("relative_path") or "")
                if not relative_path or entry.get("is_private"):
                    skipped += 1
                    continue
                path = root / relative_path
                if memory_scope is not None:
                    try:
                        if not memory_scope.classify(path).eligible:
                            skipped += 1
                            continue
                    except Exception:
                        skipped += 1
                        continue
                if not path.exists() or path.suffix.lower() != ".md":
                    skipped += 1
                    continue
                try:
                    text = path.read_text(encoding="utf-8-sig")
                except OSError:
                    skipped += 1
                    continue
                document_chunks = chunker.chunk(str(entry.get("id") or relative_path), text)
                self._upsert_document(connection, entry, document_chunks)
                documents += 1
                chunks += len(document_chunks)
            revision = self._bump_revision(connection)
            self._set_meta(connection, "last_rebuild_at", datetime.now().isoformat(timespec="seconds"))
            self._set_meta(connection, "document_count", str(documents))
            self._set_meta(connection, "chunk_count", str(chunks))
        return {"documents": documents, "chunks": chunks, "skipped": skipped, "revision": revision}

    def upsert_from_entry(
        self,
        entry: dict[str, Any],
        file_path: Path | str,
        chunker: MarkdownChunker | None = None,
    ) -> dict[str, Any]:
        path = Path(file_path)
        text = path.read_text(encoding="utf-8-sig")
        chunker = chunker or MarkdownChunker()
        chunks = chunker.chunk(str(entry.get("id") or path.stem), text)
        with self._lock, self._connection() as connection:
            self._upsert_document(connection, entry, chunks)
            revision = self._bump_revision(connection)
        return {"memory_id": str(entry.get("id")), "chunks": len(chunks), "revision": revision}

    def sync_structured_evidence(
        self,
        *,
        chunker: MarkdownChunker | None = None,
    ) -> dict[str, int | bool]:
        """Materialize structured message rows into the existing lexical index.

        Source/Conversation/Message rows remain the evidence authority.  The
        records written here are rebuildable search projections only: they have
        a distinct memory type/tier and a deterministic path derived from the
        persisted message identity, never a Vault file.  Keeping this writer on
        ``MemoryDatabase`` means the normal FTS and semantic snapshot seams can
        consume the same projection without introducing another index.
        """
        chunker = chunker or MarkdownChunker()
        with self._lock, self._connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    s.source_id, s.external_id AS source_external_id,
                    s.source_type, s.status AS source_status,
                    c.conversation_id, c.external_id AS conversation_external_id,
                    c.title AS conversation_title,
                    m.message_id, m.external_id AS message_external_id,
                    m.role, m.author, m.occurred_at, m.sequence, m.content,
                    m.content_hash, m.raw_reference, m.privacy,
                    m.projects_json, m.agent_scope_json, m.updated_at,
                    s.metadata_json AS source_metadata_json
                FROM message_records m
                JOIN conversation_records c ON c.conversation_id = m.conversation_id
                JOIN source_records s ON s.source_id = m.source_id
                ORDER BY m.message_id
                """
            ).fetchall()

            entries: list[tuple[dict[str, Any], list[MarkdownChunk]]] = []
            for row in rows:
                content = str(row["content"] or "").strip()
                if not content:
                    # Empty structured rows remain available to source APIs but
                    # must never create a useless lexical document.
                    continue
                source_status = str(row["source_status"] or "").strip().lower()
                document_status = "active" if source_status == "active" else "archived"
                source_metadata = self._loads(row["source_metadata_json"], {})
                automatic_source_id = str(source_metadata.get("automatic_memory_source_id") or "").strip()
                version_key = "|".join(
                    str(row[key] or "")
                    for key in ("source_id", "conversation_id", "message_id", "content_hash")
                )
                version_digest = hashlib.sha256(version_key.encode("utf-8")).hexdigest()[:24].upper()
                memory_id = f"LJ-EVIDENCE-{version_digest}"
                version_started = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
                entry = {
                    "id": memory_id,
                    "relative_path": f"__structured__/evidence/{memory_id}.md",
                    "title": str(row["conversation_title"] or row["message_id"]),
                    "memory_type": "structured_evidence",
                    "memory_tier": "evidence",
                    "status": document_status,
                    "review_status": "evidence",
                    "privacy": str(row["privacy"] or "private"),
                    "project": self._loads(row["projects_json"], []),
                    "tags": ["structured-evidence", str(row["source_type"] or "")],
                    "content_hash": str(row["content_hash"] or self.content_hash(content)),
                    "modified_at": str(row["updated_at"] or ""),
                    "sources": [
                        value
                        for value in (row["raw_reference"], row["source_id"])
                        if str(value or "").strip()
                    ],
                    "properties": {
                        "memory_tier": "evidence",
                        # Version validity is ingestion time, not message event
                        # time: one message may receive a changed snapshot while
                        # retaining its original occurred_at.
                        "valid_from": version_started,
                        "agent_scope": self._loads(row["agent_scope_json"], []),
                        "recall_weight": 1.0,
                    },
                    "authority": "old_chat_inference",
                    "evidence_refs": [str(row["message_id"])],
                    "memory_scope_reason": "structured_evidence_projection",
                    "structured_source_type": str(row["source_type"] or ""),
                    "source_id": str(row["source_id"] or ""),
                    "source_external_id": str(row["source_external_id"] or ""),
                    "source_status": source_status,
                    "automatic_memory_source_id": automatic_source_id,
                    "raw_reference": str(row["raw_reference"] or ""),
                    "conversation_id": str(row["conversation_id"] or ""),
                    "conversation_external_id": str(row["conversation_external_id"] or ""),
                    "message_id": str(row["message_id"] or ""),
                    "message_external_id": str(row["message_external_id"] or ""),
                    "role": str(row["role"] or ""),
                    "author": str(row["author"] or ""),
                    "sequence": int(row["sequence"] or 0),
                    "occurred_at": row["occurred_at"],
                    "content_hash": str(row["content_hash"] or self.content_hash(content)),
                    "valid_from": version_started,
                }
                body = f"[{entry['role']}] {content}"
                entries.append((entry, chunker.chunk(memory_id, body)))

            added = 0
            updated = 0
            removed = 0
            for entry, chunks in entries:
                identity = (
                    str(entry.get("source_id") or ""),
                    str(entry.get("conversation_id") or ""),
                    str(entry.get("message_id") or ""),
                )
                prior_rows = connection.execute(
                    """
                    SELECT memory_id, content_hash, status, valid_from
                    FROM memory_documents
                    WHERE memory_type = 'structured_evidence'
                      AND json_extract(relationships_json, '$.source_id') = ?
                      AND json_extract(relationships_json, '$.conversation_id') = ?
                      AND json_extract(relationships_json, '$.message_id') = ?
                    ORDER BY valid_from, memory_id
                    """,
                    identity,
                ).fetchall()
                prior = connection.execute(
                    "SELECT content_hash, status, valid_from, valid_to FROM memory_documents WHERE memory_id = ?",
                    (entry["id"],),
                ).fetchone()
                if prior is not None and str(prior["content_hash"] or "") == str(entry["content_hash"]):
                    # Byte-identical replay is a true no-op. Preserve the
                    # original validity interval and avoid rewriting FTS or
                    # updated_at; lifecycle transitions are handled by the
                    # existing StateDB projection bridge.
                    if str(prior["status"] or "") == str(entry["status"] or ""):
                        continue
                    entry["valid_from"] = prior["valid_from"]
                    entry.setdefault("properties", {})["valid_from"] = prior["valid_from"]
                    entry["valid_to"] = prior["valid_to"]
                if prior is None and prior_rows:
                    now = str(entry["valid_from"])
                    for old in prior_rows:
                        if str(old["status"] or "") != "active":
                            continue
                        old_id = str(old["memory_id"])
                        old_relationships = self._loads(
                            connection.execute(
                                "SELECT relationships_json FROM memory_documents WHERE memory_id = ?",
                                (old_id,),
                            ).fetchone()["relationships_json"],
                            {},
                        )
                        old_relationships.update({
                            "superseded_by": entry["id"],
                            "supersession_reason": "content_hash_changed",
                        })
                        connection.execute(
                            """
                            UPDATE memory_documents
                            SET status = 'superseded', valid_to = ?, superseded_by = ?,
                                relationships_json = ?, pin_to_context = 0, updated_at = ?
                            WHERE memory_id = ?
                            """,
                            (now, entry["id"], self._json(old_relationships), now, old_id),
                        )
                        updated += 1
                    entry.setdefault("properties", {})["supersedes"] = [
                        str(old["memory_id"]) for old in prior_rows if str(old["status"] or "") == "active"
                    ]
                    entry["supersedes"] = entry["properties"]["supersedes"]
                    entry["supersession_reason"] = "content_hash_changed"
                self._upsert_document(connection, entry, chunks)
                if prior is None:
                    added += 1
                elif str(prior["content_hash"] or "") != str(entry["content_hash"]):
                    updated += 1
            if added or updated or removed:
                revision = self._bump_revision(connection)
            else:
                revision = int(self._get_meta(connection, "revision") or 0)
            self._set_meta(connection, "structured_evidence_document_count", str(len(entries)))
            self._set_meta(
                connection,
                "structured_evidence_chunk_count",
                str(sum(len(chunks) for _, chunks in entries)),
            )
        return {
            "documents": len(entries),
            "chunks": sum(len(chunks) for _, chunks in entries),
            "added": added,
            "updated": updated,
            "removed": removed,
            "unchanged": len(entries) - added - updated,
            "revision": revision,
            "full_rebuild": False,
        }

    def rebuild_structured_evidence(
        self,
        *,
        chunker: MarkdownChunker | None = None,
    ) -> dict[str, int | bool]:
        """Rebuild only structured evidence projections from source rows."""
        return self.sync_structured_evidence(chunker=chunker)

    def upsert_derived_projection(
        self,
        *,
        memory_id: str,
        title: str,
        content: str,
        content_hash: str,
        evidence_refs: list[str] | tuple[str, ...],
        confidence: float | None,
        authority: str,
        source_kind: str,
        policy_version: str,
        decision_id: str,
        candidate_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Deprecated unsafe writer; promotion must use prepare/activate.

        This is deliberately a derived index write.  It never writes the
        owner's Vault or promotes a Core Memory document.  The stable virtual
        path keeps repeated promotion idempotent while retaining provenance in
        the normal relationships read model.
        """
        raise RuntimeError("derived_projection_requires_prepare_activate")

        normalized_id = str(memory_id or "").strip()
        if not normalized_id:
            raise ValueError("memory_id is required")
        body = str(content or "").strip()
        if not body:
            raise ValueError("content is required")
        metadata = dict(candidate_metadata or {})
        entry = {
            "id": normalized_id,
            "relative_path": f"__derived__/automatic-memory/{normalized_id}.md",
            "title": str(title or normalized_id),
            "memory_type": str(metadata.get("memory_type") or "knowledge"),
            "memory_tier": "derived",
            "status": "active",
            "review_status": "auto_activated",
            "privacy": str(metadata.get("privacy") or "private"),
            "importance": str(metadata.get("importance") or "medium"),
            "confidence": str(confidence) if confidence is not None else "",
            "project": metadata.get("project_ids") or metadata.get("project") or [],
            "tags": ["automatic-memory", "derived-current"],
            "content_hash": str(content_hash or ""),
            "modified_at": metadata.get("modified_at") or "",
            "people": [],
            "organizations": [],
            "tools": [],
            "models": [],
            "sources": list(evidence_refs),
            "tasks": [],
            "decisions": [],
            "related": [],
            "properties": {
                "memory_tier": "derived",
                "valid_from": metadata.get("valid_from") or "",
                "valid_to": metadata.get("valid_to") or "",
                "pin_to_context": False,
                "agent_scope": metadata.get("agent_scope") or [],
                "recall_weight": metadata.get("recall_weight") or 1.0,
            },
            "memory_scope_reason": "derived_current_projection",
        }
        # The provenance fields are stored alongside the ordinary relationships
        # so rebuilds and diagnostics use the existing MemoryDatabase schema.
        entry["sources"] = list(evidence_refs)
        entry["_promotion_relationships"] = {
            "evidence_refs": list(evidence_refs),
            "authority": str(authority or ""),
            "source_kind": str(source_kind or ""),
            "policy_version": str(policy_version),
            "decision_id": str(decision_id),
        }
        chunker = MarkdownChunker()
        chunks = chunker.chunk(normalized_id, body)
        with self._lock, self._connection() as connection:
            self._upsert_document(connection, entry, chunks)
            row = connection.execute(
                "SELECT relationships_json FROM memory_documents WHERE memory_id = ?",
                (normalized_id,),
            ).fetchone()
            relationships = self._loads(row["relationships_json"], {}) if row else {}
            relationships.update(entry["_promotion_relationships"])
            connection.execute(
                "UPDATE memory_documents SET relationships_json = ? WHERE memory_id = ?",
                (self._json(relationships), normalized_id),
            )
            revision = self._bump_revision(connection)
        return {"memory_id": normalized_id, "chunks": len(chunks), "revision": revision}

    def prepare_derived_projection(
        self, *, memory_id: str, title: str, content: str, content_hash: str,
        evidence_refs: Any, confidence: float | None, authority: str,
        source_kind: str, policy_version: str, decision_id: str,
        candidate_metadata: dict[str, Any] | None = None,
    ) -> Any:
        from src.auto_review.models import ProjectionWriteResult, PromotionProjectionState, ProvenanceRef
        from src.sources import ResolvedMessageRef
        import math
        normalized_id = str(memory_id or "").strip()
        owner = str(decision_id or "").strip()
        body = str(content or "").strip()
        if not normalized_id or not owner or not body:
            raise ValueError("memory_id, decision_id and content are required")
        if not isinstance(candidate_metadata, Mapping):
            raise ValueError("promotion_metadata_invalid")
        metadata = dict(candidate_metadata)
        allowed_metadata = {
            "memory_type", "privacy", "importance", "project_ids", "project", "agent_scope",
            "modified_at", "valid_from", "valid_to", "recall_weight", "pin_to_context",
            "direct_user_evidence", "user_authored", "owner_confirmed_evidence", "current_authoritative",
            "memory_tier",
        }
        forbidden_key = re.compile(r"token|secret|password|authorization|api[_ -]?key|fixture|path", re.I)
        if any(forbidden_key.search(str(key)) for key in metadata):
            raise ValueError("promotion_metadata_forbidden")
        if any(str(key) not in allowed_metadata for key in metadata):
            raise ValueError("promotion_metadata_invalid")

        forbidden_value = re.compile(r"(?:sk-[a-z0-9]|api[_ -]?key|token|secret|password|authorization|fixture|evaluator|exception|traceback)", re.I)

        def valid_metadata_value(value: Any) -> bool:
            if value is None or isinstance(value, (bool, int, float, str)):
                if isinstance(value, float) and not math.isfinite(value):
                    return False
                if isinstance(value, str):
                    normalized = value.replace("\\/", "/").replace("\\\\", "\\")
                    return not forbidden_value.search(value) and not normalized.startswith(("/", "\\")) and not re.match(r"^[a-z]:[\\/]", normalized, re.I)
                return True
            if isinstance(value, Mapping):
                return all(isinstance(key, str) and not forbidden_key.search(key) and valid_metadata_value(item) for key, item in value.items())
            if isinstance(value, (list, tuple, set)):
                return all(valid_metadata_value(item) for item in value)
            return False

        if not all(valid_metadata_value(value) for value in metadata.values()):
            raise ValueError("promotion_metadata_invalid")
        refs = []
        seen_refs: set[tuple[str, str, str | None]] = set()
        for item in evidence_refs or ():
            if isinstance(item, ProvenanceRef):
                ref = item.to_dict()
                if item.kind == "message" and (not isinstance(item.content_hash, str) or not item.content_hash.strip()):
                    raise ValueError("promotion_evidence_ref_invalid")
            elif isinstance(item, ResolvedMessageRef):
                ref = {"kind": "message", "value": str(item.message_id), "content_hash": item.content_hash}
            elif isinstance(item, Mapping):
                if set(item) - {"kind", "value", "content_hash"}:
                    raise ValueError("promotion_evidence_ref_invalid")
                kind, value, content_hash = item.get("kind"), item.get("value"), item.get("content_hash")
                if not isinstance(kind, str) or kind not in {"message", "event", "source", "conversation", "evidence"} or not isinstance(value, str) or not value.strip() or (content_hash is not None and (not isinstance(content_hash, str) or not content_hash.strip())) or (kind == "message" and (not isinstance(content_hash, str) or not content_hash.strip())):
                    raise ValueError("promotion_evidence_ref_invalid")
                ref = {"kind": kind, "value": value, "content_hash": content_hash}
            else:
                raise ValueError("promotion_evidence_ref_invalid")
            ref_key = (str(ref.get("kind")), str(ref.get("value")), ref.get("content_hash"))
            if ref_key in seen_refs:
                raise ValueError("promotion_evidence_ref_invalid")
            seen_refs.add(ref_key)
            refs.append(ref)
        refs.sort(key=lambda item: (str(item.get("kind") or ""), str(item.get("value") or ""), str(item.get("content_hash") or "")))
        relationships = {
            "evidence_refs": refs, "authority": str(authority or ""),
            "source_kind": str(source_kind or ""), "policy_version": str(policy_version),
            "decision_id": owner,
        }
        entry = {
            "id": normalized_id, "relative_path": f"__derived__/automatic-memory/{normalized_id}.md",
            "title": str(title or normalized_id), "memory_type": str(metadata.get("memory_type") or "knowledge"),
            "memory_tier": "derived", "status": "preparing", "review_status": "preparing",
            "privacy": str(metadata.get("privacy") or "private"), "importance": str(metadata.get("importance") or "medium"),
            "confidence": str(confidence) if confidence is not None else "", "project": metadata.get("project_ids") or metadata.get("project") or [],
            "tags": ["automatic-memory", "derived-current"], "content_hash": str(content_hash or ""),
            "modified_at": metadata.get("modified_at") or "", "sources": refs,
            "properties": {"memory_tier": "derived", "valid_from": metadata.get("valid_from") or "", "valid_to": metadata.get("valid_to") or "", "pin_to_context": False, "agent_scope": metadata.get("agent_scope") or [], "recall_weight": metadata.get("recall_weight") or 1.0},
            "_promotion_relationships": relationships,
        }
        chunks = MarkdownChunker().chunk(normalized_id, body)
        with self._lock, self._connection() as connection:
            existing = connection.execute("SELECT * FROM memory_documents WHERE memory_id=?", (normalized_id,)).fetchone()
            if existing is not None:
                prior = self._document_dict(existing)
                prior_rel = prior.get("relationships") or {}
                if (prior.get("memory_tier") != "derived" or str(prior.get("content_hash") or "") != str(content_hash or "") or str(prior_rel.get("decision_id") or "") != owner or prior_rel.get("evidence_refs") != refs or str(prior_rel.get("policy_version") or "") != str(policy_version)):
                    raise ValueError("derived_projection_conflict")
                state = PromotionProjectionState(str(prior.get("status") or "preparing"))
                return ProjectionWriteResult(normalized_id, owner, False, state)
            self._upsert_document(connection, entry, chunks)
            row = connection.execute("SELECT relationships_json FROM memory_documents WHERE memory_id=?", (normalized_id,)).fetchone()
            current = self._loads(row["relationships_json"], {}) if row else {}
            current.update(relationships)
            connection.execute("UPDATE memory_documents SET relationships_json=?, status='preparing', review_status='preparing' WHERE memory_id=?", (self._json(current), normalized_id))
            self._bump_revision(connection)
        return ProjectionWriteResult(normalized_id, owner, True, PromotionProjectionState.PREPARING)

    def activate_derived_projection(self, memory_id: str, *, decision_id: str, required_messages: Any) -> Any:
        from src.auto_review.models import ProjectionWriteResult, PromotionProjectionState
        from src.sources import ExternalMessageKey
        expected_refs = {str(item.message_id): item for item in required_messages}
        expected = {key: str(item.content_hash) for key, item in expected_refs.items()}
        owner = str(decision_id or "")
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM memory_documents WHERE memory_id=?", (str(memory_id),)).fetchone()
            if row is None:
                raise ValueError("derived_projection_missing")
            relationships = self._loads(row["relationships_json"], {})
            if row["memory_tier"] != "derived" or str(relationships.get("decision_id") or "") != owner or str(row["status"]) not in {"preparing", "active"}:
                raise ValueError("derived_projection_activation_conflict")
            links = connection.execute(
                """SELECT l.message_id,l.relation_type,l.created_by_decision_id,m.content_hash,
                          m.external_id AS message_external_id,
                          c.external_id AS conversation_external_id,
                          s.external_id AS source_external_id
                   FROM message_memory_links l
                   JOIN message_records m ON m.message_id=l.message_id
                   JOIN conversation_records c ON c.conversation_id=m.conversation_id
                   JOIN source_records s ON s.source_id=m.source_id
                   WHERE l.memory_id=?""",
                (str(memory_id),),
            ).fetchall()
            actual = {str(item["message_id"]): str(item["content_hash"] or "") for item in links}
            identity_ok = all(
                str(item["message_id"]) in expected_refs
                and str(item["created_by_decision_id"] or "") == owner
                and expected_refs[str(item["message_id"])].external_key == ExternalMessageKey(
                    str(item["source_external_id"] or ""),
                    str(item["conversation_external_id"] or ""),
                    str(item["message_external_id"] or ""),
                )
                for item in links
            )
            if any(str(item["relation_type"]) != "derived_from" for item in links) or actual != expected or not identity_ok:
                raise ValueError("derived_projection_provenance_incomplete")
            if str(row["status"]) == "active":
                return ProjectionWriteResult(str(memory_id), owner, False, PromotionProjectionState.VISIBLE_ACTIVE)
            connection.execute("UPDATE memory_documents SET status='active', review_status='auto_activated', updated_at=? WHERE memory_id=?", (datetime.now().isoformat(timespec="seconds"), str(memory_id)))
            self._bump_revision(connection)
        return ProjectionWriteResult(str(memory_id), owner, False, PromotionProjectionState.VISIBLE_ACTIVE)

    def remove_preparing_projection(self, memory_id: str, *, decision_id: str) -> bool:
        owner = str(decision_id or "")
        with self._lock, self._connection() as connection:
            row = connection.execute("SELECT status,memory_tier,relationships_json FROM memory_documents WHERE memory_id=?", (str(memory_id),)).fetchone()
            if row is None or row["memory_tier"] != "derived" or row["status"] != "preparing":
                return False
            rel = self._loads(row["relationships_json"], {})
            if str(rel.get("decision_id") or "") != owner:
                return False
            foreign = connection.execute("SELECT 1 FROM message_memory_links WHERE memory_id=? AND (created_by_decision_id IS NULL OR created_by_decision_id<>?) LIMIT 1", (str(memory_id), owner)).fetchone()
            if foreign is not None:
                return False
            connection.execute("DELETE FROM memory_fts WHERE memory_id=?", (str(memory_id),))
            cursor = connection.execute("DELETE FROM memory_documents WHERE memory_id=?", (str(memory_id),))
            if cursor.rowcount:
                self._bump_revision(connection)
                return True
        return False

    def mark_repair_required(self, memory_id: str, *, decision_id: str) -> bool:
        with self._lock, self._connection() as connection:
            row = connection.execute("SELECT relationships_json,memory_tier FROM memory_documents WHERE memory_id=?", (str(memory_id),)).fetchone()
            if row is None or row["memory_tier"] != "derived":
                return False
            relationships = self._loads(row["relationships_json"], {})
            if str(relationships.get("decision_id") or "") != str(decision_id):
                return False
            connection.execute("UPDATE memory_documents SET status='repair_required', review_status='repair_required', updated_at=? WHERE memory_id=?", (datetime.now().isoformat(timespec="seconds"), str(memory_id)))
            self._bump_revision(connection)
            return True

    def list_derived_projection_identity_rows(self) -> tuple[dict[str, Any], ...]:
        with self._connection() as connection:
            rows = connection.execute("SELECT memory_id,status,memory_tier,relationships_json,content_hash FROM memory_documents WHERE memory_tier='derived' AND status='active' ORDER BY memory_id").fetchall()
        return tuple({"memory_id": str(r["memory_id"]), "status": str(r["status"]), "memory_tier": str(r["memory_tier"]), "decision_id": str(self._loads(r["relationships_json"], {}).get("decision_id") or ""), "content_hash": str(r["content_hash"] or "")} for r in rows)

    def _upsert_document(
        self,
        connection: sqlite3.Connection,
        entry: dict[str, Any],
        chunks: list[MarkdownChunk],
    ) -> None:
        memory_id = str(entry.get("id") or entry.get("relative_path"))
        if not memory_id:
            raise ValueError("memory_id is required")
        properties = entry.get("properties") or {}
        relationships = {
            key: self._as_list(entry.get(key))
            for key in (
                "people",
                "organizations",
                "tools",
                "models",
                "sources",
                "tasks",
                "decisions",
                "related",
                "related_ids",
            )
        }
        for key in (
            "authority", "evidence_refs", "supersession_reason", "invalidating_reason", "supersedes",
            "created_by", "confirmed_by", "policy_version", "extractor_version",
            "conflict_key", "topic_key", "decision_key",
            "structured_source_type", "source_id", "source_external_id", "source_status",
            "automatic_memory_source_id",
            "conversation_id", "conversation_external_id", "message_id",
            "message_external_id", "role", "author", "sequence", "occurred_at",
            "content_hash", "raw_reference",
        ):
            value = entry.get(key)
            if value in (None, ""):
                value = properties.get(key)
            if value not in (None, ""):
                relationships[key] = value
        memory_scope_reason = str(
            entry.get("memory_scope_reason")
            or properties.get("memory_scope_reason")
            or ""
        ).strip()
        if memory_scope_reason:
            relationships["__memory_scope_reason"] = memory_scope_reason
        memory_tier = str(properties.get("memory_tier") or entry.get("memory_tier") or "archival")
        agent_scope = self._as_list(properties.get("agent_scope") or entry.get("agent_scope"))
        project = self._as_list(entry.get("project"))
        tags = self._as_list(entry.get("tags"))
        now = datetime.now().isoformat(timespec="seconds")
        connection.execute(
            """
            INSERT INTO memory_documents(
                memory_id, relative_path, title, aliases_json, memory_type, memory_tier,
                status, review_status, privacy, importance, confidence, project_json,
                tags_json, relationships_json, valid_from, valid_to, superseded_by,
                pin_to_context, agent_scope_json, recall_weight, content_hash,
                modified_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(memory_id) DO UPDATE SET
                relative_path = excluded.relative_path,
                title = excluded.title,
                aliases_json = excluded.aliases_json,
                memory_type = excluded.memory_type,
                memory_tier = excluded.memory_tier,
                status = excluded.status,
                review_status = excluded.review_status,
                privacy = excluded.privacy,
                importance = excluded.importance,
                confidence = excluded.confidence,
                project_json = excluded.project_json,
                tags_json = excluded.tags_json,
                relationships_json = excluded.relationships_json,
                valid_from = excluded.valid_from,
                valid_to = excluded.valid_to,
                superseded_by = excluded.superseded_by,
                pin_to_context = excluded.pin_to_context,
                agent_scope_json = excluded.agent_scope_json,
                recall_weight = excluded.recall_weight,
                content_hash = excluded.content_hash,
                modified_at = excluded.modified_at,
                updated_at = excluded.updated_at
            """,
            (
                memory_id,
                str(entry.get("relative_path") or ""),
                str(entry.get("title") or memory_id),
                self._json(self._as_list(entry.get("aliases"))),
                str(entry.get("memory_type") or entry.get("type") or "note"),
                memory_tier,
                str(entry.get("status") or "active"),
                str(entry.get("review_status") or ""),
                str(entry.get("privacy") or "private"),
                str(entry.get("importance") or ""),
                str(entry.get("confidence") if entry.get("confidence") is not None else ""),
                self._json(project),
                self._json(tags),
                self._json(relationships),
                properties.get("valid_from") or entry.get("valid_from"),
                properties.get("valid_to") or entry.get("valid_to"),
                properties.get("superseded_by") or entry.get("superseded_by") or "",
                int(self._as_bool(properties.get("pin_to_context") or entry.get("pin_to_context"))),
                self._json(agent_scope),
                self._as_float(properties.get("recall_weight") or entry.get("recall_weight"), 1.0),
                str(entry.get("content_hash") or ""),
                str(entry.get("modified_at") or ""),
                now,
            ),
        )
        connection.execute("DELETE FROM memory_fts WHERE memory_id = ?", (memory_id,))
        connection.execute("DELETE FROM memory_chunks WHERE memory_id = ?", (memory_id,))
        tag_text = " ".join(str(tag) for tag in tags)
        title = str(entry.get("title") or memory_id)
        for chunk in chunks:
            chunk_hash = hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
            connection.execute(
                """
                INSERT INTO memory_chunks(
                    chunk_id, memory_id, ordinal, heading, text, start_line,
                    end_line, char_count, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk.chunk_id,
                    memory_id,
                    chunk.ordinal,
                    chunk.heading,
                    chunk.text,
                    chunk.start_line,
                    chunk.end_line,
                    chunk.char_count,
                    chunk_hash,
                ),
            )
            connection.execute(
                """
                INSERT INTO memory_fts(chunk_id, memory_id, title, heading, text, tags)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (chunk.chunk_id, memory_id, title, chunk.heading, chunk.text, tag_text),
            )

    def remove_memory(self, memory_id: str) -> bool:
        with self._lock, self._connection() as connection:
            connection.execute("DELETE FROM memory_fts WHERE memory_id = ?", (memory_id,))
            cursor = connection.execute("DELETE FROM memory_documents WHERE memory_id = ?", (memory_id,))
            if cursor.rowcount:
                self._bump_revision(connection)
                return True
        return False

    def remove_by_path(self, relative_path: str) -> bool:
        with self._lock, self._connection() as connection:
            row = connection.execute(
                "SELECT memory_id FROM memory_documents WHERE relative_path = ?", (relative_path,)
            ).fetchone()
            if not row:
                return False
            memory_id = str(row["memory_id"])
            connection.execute("DELETE FROM memory_fts WHERE memory_id = ?", (memory_id,))
            connection.execute("DELETE FROM memory_documents WHERE memory_id = ?", (memory_id,))
            self._bump_revision(connection)
            return True

    def fetch_memory(self, memory_id: str, include_chunks: bool = True) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM memory_documents WHERE memory_id = ?", (memory_id,)
            ).fetchone()
            if not row:
                return None
            result = self._document_dict(row)
            if include_chunks:
                chunks = connection.execute(
                    "SELECT * FROM memory_chunks WHERE memory_id = ? ORDER BY ordinal",
                    (memory_id,),
                ).fetchall()
                result["chunks"] = [dict(chunk) for chunk in chunks]
            return result

    def fetch_by_path(self, relative_path: str, include_chunks: bool = True) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT memory_id FROM memory_documents WHERE relative_path = ?", (relative_path,)
            ).fetchone()
        return self.fetch_memory(str(row["memory_id"]), include_chunks) if row else None

    def list_documents(self, *, include_chunks: bool = False) -> list[dict[str, Any]]:
        """Return rebuildable document records for migration and diagnostics."""
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM memory_documents ORDER BY relative_path, memory_id"
            ).fetchall()
        output = []
        for row in rows:
            item = self._document_dict(row)
            if include_chunks:
                with self._connection() as connection:
                    chunks = connection.execute(
                        "SELECT * FROM memory_chunks WHERE memory_id = ? ORDER BY ordinal",
                        (item["memory_id"],),
                    ).fetchall()
                item["chunks"] = [dict(chunk) for chunk in chunks]
            output.append(item)
        return output

    def record_migration_audit(self, key: str, payload: dict[str, Any]) -> None:
        """Store a body-free migration audit marker in the derived index."""
        with self._lock, self._connection() as connection:
            self._set_meta(connection, f"obsidian_migration:{key}", json.dumps(payload, ensure_ascii=False, sort_keys=True))

    def migration_audits(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT key, value FROM memory_meta WHERE key LIKE 'obsidian_migration:%' ORDER BY key"
            ).fetchall()
        output = []
        for row in rows:
            try:
                value = json.loads(str(row["value"]))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if isinstance(value, dict):
                output.append(value)
        return output

    def list_core_memories(
        self,
        agent_id: str | None = None,
        project: str | None = None,
        privacy: tuple[str, ...] = ("public", "private"),
        limit: int = 50,
        mode: str = "current",
        as_of: str | None = None,
    ) -> list[dict[str, Any]]:
        placeholders = ",".join("?" for _ in privacy)
        temporal = TemporalQuery.from_values(mode, as_of)
        status_clause = "AND status = 'active'" if temporal.mode in {"current", "why"} else ""
        pin_clause = "AND pin_to_context = 1" if temporal.mode in {"current", "why"} else ""
        sql = f"""
            SELECT * FROM memory_documents
            WHERE memory_tier = 'core'
              {pin_clause}
              {status_clause}
              AND privacy IN ({placeholders})
            ORDER BY recall_weight DESC,
                     CASE importance WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'medium' THEN 2 ELSE 1 END DESC,
                     updated_at DESC
            LIMIT ?
        """
        with self._connection() as connection:
            rows = connection.execute(sql, (*privacy, int(limit))).fetchall()
        output = []
        for row in rows:
            item = self._document_dict(row)
            allowed, _ = temporal.allows(item)
            if not allowed:
                continue
            scopes = item["agent_scope"]
            if scopes and agent_id and agent_id not in scopes and "all" not in scopes:
                continue
            if scopes and not agent_id and "all" not in scopes:
                continue
            if project and project not in " ".join(str(value) for value in item["project"]):
                continue
            output.append(item)
        return output

    def search_fts(
        self,
        query: str,
        limit: int = 30,
        memory_types: tuple[str, ...] = (),
        statuses: tuple[str, ...] = ("active", "needs_review", "received"),
        privacy: tuple[str, ...] = ("public", "private"),
        as_of: str | None = None,
        mode: str = "current",
    ) -> list[dict[str, Any]]:
        temporal = TemporalQuery.from_values(mode, as_of)
        if not temporal.valid:
            return []
        expression = self._fts_expression(query)
        if not expression:
            return []
        where = ["memory_fts MATCH ?"]
        params: list[Any] = [expression]
        if memory_types:
            where.append("d.memory_type IN (" + ",".join("?" for _ in memory_types) + ")")
            params.extend(memory_types)
        if statuses and temporal.mode in {"current", "why"}:
            where.append("d.status IN (" + ",".join("?" for _ in statuses) + ")")
            params.extend(statuses)
        if privacy:
            where.append("d.privacy IN (" + ",".join("?" for _ in privacy) + ")")
            params.extend(privacy)
        # Temporal intervals are normalized by TemporalQuery after the row is
        # materialized.  Do not compare ISO strings in SQLite: offsets such as
        # +08:00 and Z do not have lexical ordering semantics.
        params.append(max(int(limit), 1))
        sql = f"""
            SELECT
                f.chunk_id,
                f.memory_id,
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
                d.relationships_json,
                d.valid_from,
                d.valid_to,
                d.pin_to_context,
                d.agent_scope_json,
                d.recall_weight,
                d.updated_at,
                c.heading,
                c.text,
                c.start_line,
                c.end_line,
                bm25(memory_fts, 0.0, 0.0, 8.0, 4.0, 1.0, 2.0) AS lexical_rank,
                snippet(memory_fts, 4, '[', ']', '…', 22) AS snippet
            FROM memory_fts AS f
            JOIN memory_chunks AS c ON c.chunk_id = f.chunk_id
            JOIN memory_documents AS d ON d.memory_id = f.memory_id
            WHERE {' AND '.join(where)}
            ORDER BY lexical_rank ASC
            LIMIT ?
        """
        try:
            with self._connection() as connection:
                rows = connection.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            fallback = self._fts_expression(query, quote_terms=True)
            if fallback == expression:
                return []
            params[0] = fallback
            with self._connection() as connection:
                rows = connection.execute(sql, params).fetchall()
        output = []
        for row in rows:
            item = self._search_dict(row)
            if temporal.mode in {"current", "why"} and item.get("memory_tier") == "derived" and item.get("status") != "active":
                continue
            allowed, reason = temporal.allows(item)
            if allowed:
                item["temporal_reason"] = reason
                output.append(item)
        short_cjk_query = any(
            len(term) < 3
            for term in re.findall(r"[A-Za-z0-9_.+-]+|[\u4e00-\u9fff]+", str(query or ""))
            if term
        )
        if temporal.mode == "history" and (not output or short_cjk_query):
            # FTS trigram/unicode tokenizers may return no row for short CJK
            # terms.  History/why must still inspect the same evidence set, so
            # use a bounded metadata/chunk substring fallback here.
            terms = [term.casefold() for term in re.findall(r"[A-Za-z0-9_.+-]+|[\u4e00-\u9fff]+", str(query or "")) if term]
            if terms:
                with self._connection() as connection:
                    fallback_sql = """
                        SELECT c.chunk_id, c.memory_id, d.relative_path, d.title,
                               d.memory_type, d.memory_tier, d.status, d.review_status,
                               d.privacy, d.importance, d.confidence, d.project_json,
                               d.tags_json, d.relationships_json, d.valid_from, d.valid_to,
                               d.pin_to_context, d.agent_scope_json, d.recall_weight,
                               d.updated_at, c.heading, c.text, c.start_line, c.end_line
                        FROM memory_chunks c JOIN memory_documents d ON d.memory_id = c.memory_id
                        WHERE d.privacy IN (""" + ",".join("?" for _ in privacy) + ")"
                    fallback_params: list[Any] = list(privacy)
                    if memory_types:
                        fallback_sql += " AND d.memory_type IN (" + ",".join("?" for _ in memory_types) + ")"
                        fallback_params.extend(memory_types)
                    with self._connection() as connection:
                        fallback_rows = connection.execute(fallback_sql, fallback_params).fetchall()
                seen_ids = {str(item.get("memory_id") or "") for item in output}
                for row in fallback_rows:
                    raw = dict(row)
                    haystack = " ".join(str(raw.get(key) or "") for key in ("title", "heading", "text", "tags_json")).casefold()
                    if not all(term in haystack for term in terms):
                        continue
                    item = self._search_dict(raw)
                    if temporal.mode in {"current", "why"} and item.get("memory_tier") == "derived" and item.get("status") != "active":
                        continue
                    if str(item.get("memory_id") or "") in seen_ids:
                        continue
                    allowed, reason = temporal.allows(item)
                    if allowed:
                        item["temporal_reason"] = reason
                        output.append(item)
                        seen_ids.add(str(item.get("memory_id") or ""))
                        if len(output) >= max(int(limit), 1):
                            break
        return output

    def refresh_project_decision(
        self,
        old_memory_id: str,
        new_memory_id: str,
        *,
        reason: str = "",
        invalidates: bool = False,
    ) -> dict[str, Any]:
        """Link a current project decision to its replacement without deleting evidence."""
        old_id, new_id = str(old_memory_id).strip(), str(new_memory_id).strip()
        if not old_id or not new_id or old_id == new_id:
            raise ValueError("distinct old and new memory IDs are required")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        status = "invalidated" if invalidates else "superseded"
        with self._lock, self._connection() as connection:
            old = connection.execute("SELECT * FROM memory_documents WHERE memory_id = ?", (old_id,)).fetchone()
            new = connection.execute("SELECT * FROM memory_documents WHERE memory_id = ?", (new_id,)).fetchone()
            if not old or not new:
                raise KeyError("both old and new memory records are required")
            existing = self._document_dict(old)
            if existing.get("status") == status and str(existing.get("superseded_by") or "") == new_id:
                return {"memory_id": old_id, "replacement_id": new_id, "status": status, "idempotent": True}
            old_fields = temporal_fields(existing)
            new_fields = temporal_fields(self._document_dict(new))
            if new_fields["authority_rank"] < old_fields["authority_rank"]:
                return {"memory_id": old_id, "replacement_id": new_id, "status": existing.get("status"), "conflict": True, "reason": "lower_authority_cannot_displace"}
            replacement_start = self._document_dict(new).get("valid_from")
            valid_to = replacement_start if parse_instant(replacement_start) is not None else now
            relationships = existing.get("relationships") or {}
            relationships.update({
                "superseded_by": new_id,
                "supersession_reason" if not invalidates else "invalidating_reason": str(reason or "project_refresh"),
                "replacement_at": now,
            })
            connection.execute(
                "UPDATE memory_documents SET status = ?, valid_to = ?, superseded_by = ?, pin_to_context = 0, relationships_json = ?, updated_at = ? WHERE memory_id = ?",
                (status, valid_to, new_id, self._json(relationships), now, old_id),
            )
            self._bump_revision(connection)
        return {"memory_id": old_id, "replacement_id": new_id, "status": status, "reason": str(reason or "project_refresh"), "idempotent": False}

    def list_recent(self, limit: int = 30, privacy: tuple[str, ...] = ("public", "private")) -> list[dict[str, Any]]:
        placeholders = ",".join("?" for _ in privacy)
        with self._connection() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM memory_documents
                WHERE privacy IN ({placeholders})
                ORDER BY modified_at DESC, updated_at DESC
                LIMIT ?
                """,
                (*privacy, int(limit)),
            ).fetchall()
        return [self._document_dict(row) for row in rows]

    def stats(self) -> dict[str, Any]:
        with self._connection() as connection:
            documents = connection.execute("SELECT COUNT(*) AS count FROM memory_documents").fetchone()["count"]
            chunks = connection.execute("SELECT COUNT(*) AS count FROM memory_chunks").fetchone()["count"]
            core = connection.execute(
                "SELECT COUNT(*) AS count FROM memory_documents WHERE memory_tier = 'core'"
            ).fetchone()["count"]
            return {
                "path": str(self.path),
                "schema_version": self._get_meta(connection, "schema_version") or SCHEMA_VERSION,
                "revision": int(self._get_meta(connection, "revision") or 0),
                "fts_tokenizer": self._get_meta(connection, "fts_tokenizer") or self._fts_tokenizer,
                "last_rebuild_at": self._get_meta(connection, "last_rebuild_at"),
                "documents": int(documents),
                "chunks": int(chunks),
                "core_memories": int(core),
            }

    def integrity_check(self) -> dict[str, Any]:
        with self._connection() as connection:
            quick_check = str(connection.execute("PRAGMA quick_check").fetchone()[0])
            orphan_chunks = int(
                connection.execute(
                    """
                    SELECT COUNT(*) FROM memory_chunks c
                    LEFT JOIN memory_documents d ON d.memory_id = c.memory_id
                    WHERE d.memory_id IS NULL
                    """
                ).fetchone()[0]
            )
            fts_rows = int(connection.execute("SELECT COUNT(*) FROM memory_fts").fetchone()[0])
            chunk_rows = int(connection.execute("SELECT COUNT(*) FROM memory_chunks").fetchone()[0])
        return {
            "healthy": quick_check == "ok" and orphan_chunks == 0 and fts_rows == chunk_rows,
            "quick_check": quick_check,
            "orphan_chunks": orphan_chunks,
            "fts_rows": fts_rows,
            "chunk_rows": chunk_rows,
        }

    @classmethod
    def _document_dict(cls, row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["aliases"] = cls._loads(item.pop("aliases_json", "[]"), [])
        item["project"] = cls._loads(item.pop("project_json", "[]"), [])
        item["tags"] = cls._loads(item.pop("tags_json", "[]"), [])
        item["relationships"] = cls._loads(item.pop("relationships_json", "{}"), {})
        item["agent_scope"] = cls._loads(item.pop("agent_scope_json", "[]"), [])
        item["pin_to_context"] = bool(item.get("pin_to_context"))
        return item

    @classmethod
    def _search_dict(cls, row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["project"] = cls._loads(item.pop("project_json", "[]"), [])
        item["tags"] = cls._loads(item.pop("tags_json", "[]"), [])
        item["relationships"] = cls._loads(item.pop("relationships_json", "{}"), {})
        item["agent_scope"] = cls._loads(item.pop("agent_scope_json", "[]"), [])
        item["pin_to_context"] = bool(item.get("pin_to_context"))
        rank = abs(float(item.pop("lexical_rank", 0.0)))
        item["lexical_score"] = 1.0 / (1.0 + rank)
        return item

    def _fts_expression(self, query: str, quote_terms: bool = False) -> str:
        clean = " ".join(str(query or "").strip().split())
        if not clean:
            return ""
        if self._fts_tokenizer == "trigram" and not quote_terms:
            return clean.replace('"', '""')
        terms = [term for term in clean.replace('"', " ").split() if term]
        return " AND ".join(f'"{term.replace(chr(34), chr(34) * 2)}"' for term in terms)
