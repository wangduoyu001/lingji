from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

from .identities import ExternalMessageKey, ResolvedMessageRef

SOURCE_READ_MODEL_SCHEMA_VERSION = "2"
_SOURCE_READ_MODEL_MIGRATION_VERSION = "1"
_ID_PREFIXES = {"source": "LJ-SRC", "conversation": "LJ-CONV", "message": "LJ-MSG"}
_INHERITED_COLUMNS = (
    ("privacy_inherited", "INTEGER NOT NULL DEFAULT 1"),
    ("projects_inherited", "INTEGER NOT NULL DEFAULT 1"),
    ("agent_scope_inherited", "INTEGER NOT NULL DEFAULT 1"),
)


class SourceReadModelError(RuntimeError):
    """Raised when the rebuildable source read model cannot be queried safely."""


class SourceReadModel:
    """Rebuildable Source/Conversation/Message index stored in lingji_memory.db."""

    def __init__(self, database: Any | Path | str):
        self.database = database if hasattr(database, "_connection") else None
        self.path = Path(getattr(database, "path", database))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        if self.database is not None:
            with self.database._connection() as connection:
                yield connection
            return
        connection = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA foreign_keys = ON")
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
            connection.execute("BEGIN")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS source_read_model_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            version_row = connection.execute(
                "SELECT value FROM source_read_model_meta WHERE key = 'schema_version'"
            ).fetchone()
            version = str(version_row["value"]) if version_row is not None else None
            if version not in (None, _SOURCE_READ_MODEL_MIGRATION_VERSION, SOURCE_READ_MODEL_SCHEMA_VERSION):
                raise SourceReadModelError(
                    "Unsupported structured read model schema version: "
                    f"{version}; expected 1 or {SOURCE_READ_MODEL_SCHEMA_VERSION}"
                )
            if version is None:
                connection.execute(
                    "INSERT INTO source_read_model_meta(key, value) VALUES ('schema_version', ?)",
                    (SOURCE_READ_MODEL_SCHEMA_VERSION,),
                )

            schema_script = """
                CREATE TABLE IF NOT EXISTS source_records (
                    source_id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    external_id TEXT,
                    raw_reference TEXT,
                    vault_reference TEXT,
                    privacy TEXT NOT NULL DEFAULT 'private',
                    projects_json TEXT NOT NULL DEFAULT '[]',
                    agent_scope_json TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'active',
                    content_hash TEXT NOT NULL,
                    created_at TEXT,
                    updated_at TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS conversation_records (
                    conversation_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    external_id TEXT,
                    title TEXT NOT NULL,
                    participants_json TEXT NOT NULL DEFAULT '[]',
                    started_at TEXT,
                    ended_at TEXT,
                    message_count INTEGER NOT NULL DEFAULT 0,
                    privacy TEXT NOT NULL DEFAULT 'private',
                    projects_json TEXT NOT NULL DEFAULT '[]',
                    agent_scope_json TEXT NOT NULL DEFAULT '[]',
                    privacy_inherited INTEGER NOT NULL DEFAULT 1,
                    projects_inherited INTEGER NOT NULL DEFAULT 1,
                    agent_scope_inherited INTEGER NOT NULL DEFAULT 1,
                    content_hash TEXT NOT NULL,
                    created_at TEXT,
                    updated_at TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY(source_id) REFERENCES source_records(source_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS message_records (
                    message_id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    external_id TEXT,
                    role TEXT NOT NULL,
                    author TEXT,
                    occurred_at TEXT,
                    sequence INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    raw_reference TEXT,
                    privacy TEXT NOT NULL DEFAULT 'private',
                    projects_json TEXT NOT NULL DEFAULT '[]',
                    agent_scope_json TEXT NOT NULL DEFAULT '[]',
                    privacy_inherited INTEGER NOT NULL DEFAULT 1,
                    projects_inherited INTEGER NOT NULL DEFAULT 1,
                    agent_scope_inherited INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT,
                    updated_at TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    ingestion_batch_id TEXT NULL,
                    ingestion_ordinal INTEGER NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversation_records(conversation_id) ON DELETE CASCADE,
                    FOREIGN KEY(source_id) REFERENCES source_records(source_id) ON DELETE CASCADE,
                    UNIQUE(conversation_id, sequence, role, content_hash)
                );

                CREATE TABLE IF NOT EXISTS message_memory_links (
                    message_id TEXT NOT NULL,
                    memory_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL DEFAULT 'derived_from',
                    confidence REAL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(message_id, memory_id, relation_type),
                    FOREIGN KEY(message_id) REFERENCES message_records(message_id) ON DELETE CASCADE,
                    FOREIGN KEY(memory_id) REFERENCES memory_documents(memory_id) ON DELETE CASCADE
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_source_external
                    ON source_records(source_type, external_id)
                    WHERE external_id IS NOT NULL AND external_id <> '';
                CREATE INDEX IF NOT EXISTS idx_source_filter
                    ON source_records(source_type, privacy, status, updated_at, source_id);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_conversation_external
                    ON conversation_records(source_id, external_id)
                    WHERE external_id IS NOT NULL AND external_id <> '';
                CREATE INDEX IF NOT EXISTS idx_conversation_source_time
                    ON conversation_records(source_id, started_at, ended_at, conversation_id);
                CREATE INDEX IF NOT EXISTS idx_conversation_filter
                    ON conversation_records(privacy, updated_at, conversation_id);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_message_external
                    ON message_records(conversation_id, external_id)
                    WHERE external_id IS NOT NULL AND external_id <> '';
                CREATE INDEX IF NOT EXISTS idx_message_conversation_time
                    ON message_records(conversation_id, occurred_at, sequence, message_id);
                CREATE INDEX IF NOT EXISTS idx_message_source_role
                    ON message_records(source_id, role, occurred_at, message_id);
                CREATE INDEX IF NOT EXISTS idx_message_memory_memory
                    ON message_memory_links(memory_id, message_id);
                """
            for statement in schema_script.split(";"):
                if statement.strip():
                    connection.execute(statement)
            conversation_added = self._ensure_inheritance_columns(
                connection, "conversation_records"
            )
            self._ensure_ingestion_columns(connection)
            message_added = self._ensure_inheritance_columns(connection, "message_records")
            self._ensure_promotion_columns(connection)
            if conversation_added:
                self._backfill_conversation_inheritance(connection)
            if message_added:
                self._backfill_message_inheritance(connection)
            if version == _SOURCE_READ_MODEL_MIGRATION_VERSION:
                connection.execute(
                    "UPDATE source_read_model_meta SET value = ? WHERE key = 'schema_version'",
                    (SOURCE_READ_MODEL_SCHEMA_VERSION,),
                )

    @staticmethod
    def _ensure_ingestion_columns(connection: sqlite3.Connection) -> None:
        savepoint = "source_read_model_ingestion_migration"
        connection.execute(f"SAVEPOINT {savepoint}")
        try:
            existing = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(message_records)").fetchall()
            }
            if "ingestion_batch_id" not in existing:
                connection.execute("ALTER TABLE message_records ADD COLUMN ingestion_batch_id TEXT NULL")
            if "ingestion_ordinal" not in existing:
                connection.execute("ALTER TABLE message_records ADD COLUMN ingestion_ordinal INTEGER NULL")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_message_ingestion_order "
                "ON message_records(ingestion_batch_id, ingestion_ordinal, message_id)"
            )
        except BaseException:
            connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            raise
        else:
            connection.execute(f"RELEASE SAVEPOINT {savepoint}")

    @staticmethod
    def _ensure_promotion_columns(connection: sqlite3.Connection) -> None:
        columns = {str(row["name"]) for row in connection.execute("PRAGMA table_info(message_memory_links)").fetchall()}
        if "created_by_decision_id" not in columns:
            connection.execute("ALTER TABLE message_memory_links ADD COLUMN created_by_decision_id TEXT NULL")

    def _ensure_inheritance_columns(
        self, connection: sqlite3.Connection, table: str
    ) -> bool:
        existing = {
            str(row["name"])
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        added = False
        for column, definition in _INHERITED_COLUMNS:
            if column not in existing:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                added = True
        return added

    @staticmethod
    def _backfill_conversation_inheritance(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            UPDATE conversation_records
            SET privacy_inherited = CASE WHEN privacy = (
                    SELECT s.privacy FROM source_records s
                    WHERE s.source_id = conversation_records.source_id
                ) THEN 1 ELSE 0 END,
                projects_inherited = CASE WHEN projects_json = (
                    SELECT s.projects_json FROM source_records s
                    WHERE s.source_id = conversation_records.source_id
                ) THEN 1 ELSE 0 END,
                agent_scope_inherited = CASE WHEN agent_scope_json = (
                    SELECT s.agent_scope_json FROM source_records s
                    WHERE s.source_id = conversation_records.source_id
                ) THEN 1 ELSE 0 END
            """
        )

    @staticmethod
    def _backfill_message_inheritance(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            UPDATE message_records
            SET privacy_inherited = CASE WHEN privacy = (
                    SELECT c.privacy FROM conversation_records c
                    WHERE c.conversation_id = message_records.conversation_id
                ) THEN 1 ELSE 0 END,
                projects_inherited = CASE WHEN projects_json = (
                    SELECT c.projects_json FROM conversation_records c
                    WHERE c.conversation_id = message_records.conversation_id
                ) THEN 1 ELSE 0 END,
                agent_scope_inherited = CASE WHEN agent_scope_json = (
                    SELECT c.agent_scope_json FROM conversation_records c
                    WHERE c.conversation_id = message_records.conversation_id
                ) THEN 1 ELSE 0 END
            """
        )

    @staticmethod
    def stable_id(kind: str, *parts: Any) -> str:
        if kind not in _ID_PREFIXES:
            raise ValueError(f"Unsupported stable ID kind: {kind}")
        normalized = "\x1f".join(
            " ".join(str(part or "").strip().split()).casefold() for part in parts
        )
        if not normalized.replace("\x1f", ""):
            raise ValueError(f"{kind} stable ID requires identity material")
        digest = hashlib.sha256(f"lingji:{kind}:{normalized}".encode("utf-8")).hexdigest()
        return f"{_ID_PREFIXES[kind]}-{digest[:32].upper()}"

    @staticmethod
    def content_hash(content: Any) -> str:
        return hashlib.sha256(str(content or "").encode("utf-8")).hexdigest()

    def schema_version(self) -> str:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT value FROM source_read_model_meta WHERE key = 'schema_version'"
            ).fetchone()
        return str(row["value"]) if row else SOURCE_READ_MODEL_SCHEMA_VERSION

    def upsert_source(self, record: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            source_id = self._upsert_source(connection, record)
        return self.get_source(source_id) or {}

    def upsert_conversation(self, record: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            conversation_id = self._upsert_conversation(connection, record)
        return self.get_conversation(conversation_id) or {}

    def upsert_message(self, record: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            message_id = self._upsert_message(connection, record)
        return self.get_message(message_id, include_content=True) or {}

    def sync_automatic_source_lifecycle(
        self,
        automatic_source_id: str,
        status: str,
        *,
        updated_at: str | None = None,
    ) -> dict[str, int | str]:
        """Project an existing StateDB authorization transition into read/index rows.

        Automatic source IDs are already persisted in structured source metadata.
        This keeps the lifecycle bridge on the existing read model and its
        ``memory_documents`` projection; it does not create another state store.
        Unknown/non-authorized states fail closed as archived evidence.
        """
        source_key = str(automatic_source_id or "").strip()
        if not source_key:
            raise SourceReadModelError("automatic source identity is required")
        source_status = str(status or "").strip().lower()
        projected_status = "active" if source_status == "authorized" else "archived"
        timestamp = str(updated_at or self._now())
        with self._lock, self._connection() as connection:
            source_rows = connection.execute(
                """
                SELECT source_id FROM source_records
                WHERE json_extract(metadata_json, '$.automatic_memory_source_id') = ?
                """,
                (source_key,),
            ).fetchall()
            source_ids = tuple(str(row["source_id"]) for row in source_rows)
            if not source_ids:
                return {"sources": 0, "documents": 0, "status": projected_status}
            connection.execute(
                """
                UPDATE source_records
                SET status = ?, updated_at = ?
                WHERE json_extract(metadata_json, '$.automatic_memory_source_id') = ?
                """,
                (projected_status, timestamp, source_key),
            )
            documents = 0
            for source_id in source_ids:
                rows = connection.execute(
                    """
                    SELECT memory_id FROM memory_documents
                    WHERE memory_type = 'structured_evidence'
                      AND json_extract(relationships_json, '$.source_id') = ?
                    """,
                    (source_id,),
                ).fetchall()
                documents += len(rows)
                lifecycle_filter = (
                    "AND status IN ('active', 'archived')"
                    if projected_status == "active"
                    else "AND status NOT IN ('superseded', 'invalidated')"
                )
                connection.execute(
                    f"""
                    UPDATE memory_documents
                    SET status = ?, review_status = 'evidence', updated_at = ?
                    WHERE memory_type = 'structured_evidence'
                      AND json_extract(relationships_json, '$.source_id') = ?
                      {lifecycle_filter}
                    """,
                    (projected_status, timestamp, source_id),
                )
                # FTS stores only searchable text; status is read from the
                # joined document row, so no second FTS index update is needed.
            # MemoryDatabase.revision is part of the existing Hybrid cache key;
            # bump it so a cached current result cannot outlive authorization.
            connection.execute(
                "UPDATE memory_meta SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT) WHERE key = 'revision'"
            )
            return {"sources": len(source_ids), "documents": documents, "status": projected_status}

    def link_message_memory(
        self,
        message_id: str,
        memory_id: str,
        *,
        relation_type: str = "derived_from",
        confidence: float | None = None,
        created_at: str | None = None,
    ) -> None:
        with self._lock, self._connection() as connection:
            self._link_message_memory(
                connection,
                message_id,
                memory_id,
                relation_type=relation_type,
                confidence=confidence,
                created_at=created_at,
            )

    def resolve_exact_message_ref(
        self, reference: str | ResolvedMessageRef, *, content_hash: str | None = None
    ) -> ResolvedMessageRef:
        value = reference.message_id if isinstance(reference, ResolvedMessageRef) else str(reference or "").strip()
        expected_hash = content_hash or (reference.content_hash if isinstance(reference, ResolvedMessageRef) else None)
        if not value:
            raise SourceReadModelError("provenance_unknown_message")
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT m.message_id, m.external_id AS message_external_id, m.content_hash,
                          c.external_id AS conversation_external_id, s.external_id AS source_external_id
                   FROM message_records m JOIN conversation_records c ON c.conversation_id=m.conversation_id
                   JOIN source_records s ON s.source_id=m.source_id
                   WHERE m.message_id=? OR m.external_id=? ORDER BY m.message_id""",
                (value, value),
            ).fetchall()
        if len(rows) != 1:
            raise SourceReadModelError("provenance_ambiguous_message" if rows else "provenance_unknown_message")
        row = rows[0]
        actual_hash = str(row["content_hash"] or "")
        if expected_hash is not None and str(expected_hash) != actual_hash:
            raise SourceReadModelError("provenance_content_hash_mismatch")
        return ResolvedMessageRef(
            str(row["message_id"]),
            ExternalMessageKey(str(row["source_external_id"] or ""), str(row["conversation_external_id"] or ""), str(row["message_external_id"] or "")),
            actual_hash,
        )

    @staticmethod
    def _message_ref_values(message: Any) -> tuple[str, str | None]:
        if isinstance(message, ResolvedMessageRef):
            return message.message_id, message.content_hash
        if isinstance(message, Mapping):
            return str(message.get("message_id") or message.get("value") or "").strip(), message.get("content_hash")
        return str(message or "").strip(), None

    def link_message_memory_batch(
        self, messages: Iterable[ResolvedMessageRef | Mapping[str, Any] | str], memory_id: str,
        *, decision_id: str, relation_type: str = "derived_from", confidence: float | None = None,
    ) -> Any:
        from src.auto_review.models import BatchLinkResult
        selected = tuple(messages)
        if not selected:
            raise SourceReadModelError("provenance_messages_required")
        if relation_type != "derived_from":
            raise SourceReadModelError("unsupported_promotion_relation")
        normalized_id = self._required(memory_id, "memory_id")
        owner = self._required(decision_id, "decision_id")
        with self._lock, self._connection() as connection:
            resolved: list[ResolvedMessageRef] = []
            seen: set[str] = set()
            for item in selected:
                raw_id, supplied_hash = self._message_ref_values(item)
                if raw_id in seen:
                    raise SourceReadModelError("duplicate_message_provenance")
                seen.add(raw_id)
                rows = connection.execute(
                    """SELECT m.message_id, m.external_id AS message_external_id, m.content_hash,
                              c.external_id AS conversation_external_id, s.external_id AS source_external_id
                       FROM message_records m JOIN conversation_records c ON c.conversation_id=m.conversation_id
                       JOIN source_records s ON s.source_id=m.source_id
                       WHERE m.message_id=? OR m.external_id=?""", (raw_id, raw_id)
                ).fetchall()
                if len(rows) != 1:
                    raise SourceReadModelError("provenance_ambiguous_message" if rows else "provenance_unknown_message")
                row = rows[0]
                actual_hash = str(row["content_hash"] or "")
                if supplied_hash is not None and str(supplied_hash) != actual_hash:
                    raise SourceReadModelError("provenance_content_hash_mismatch")
                resolved_ref = ResolvedMessageRef(
                    str(row["message_id"]),
                    ExternalMessageKey(str(row["source_external_id"] or ""), str(row["conversation_external_id"] or ""), str(row["message_external_id"] or "")),
                    actual_hash,
                )
                if isinstance(item, ResolvedMessageRef) and item.external_key != resolved_ref.external_key:
                    raise SourceReadModelError("provenance_external_identity_mismatch")
                resolved.append(resolved_ref)
            created: list[ResolvedMessageRef] = []
            reused: list[ResolvedMessageRef] = []
            for ref in resolved:
                existing = connection.execute(
                    "SELECT 1 FROM message_memory_links WHERE message_id=? AND memory_id=? AND relation_type=?",
                    (ref.message_id, normalized_id, relation_type),
                ).fetchone()
                if existing is not None:
                    reused.append(ref)
                    continue
                connection.execute(
                    "INSERT INTO message_memory_links(message_id,memory_id,relation_type,confidence,created_at,created_by_decision_id) VALUES (?,?,?,?,?,?)",
                    (ref.message_id, normalized_id, relation_type, confidence, self._now(), owner),
                )
                created.append(ref)
        return BatchLinkResult(tuple(created), tuple(reused))

    def verify_message_memory_links(
        self, messages: Iterable[ResolvedMessageRef], memory_id: str, *, relation_type: str = "derived_from",
        decision_id: str | None = None,
    ) -> bool:
        selected = tuple(messages)
        message_ids = [str(ref.message_id) for ref in selected]
        if len(message_ids) != len(set(message_ids)):
            return False
        expected_refs = {ref.message_id: ref for ref in selected}
        expected = {ref.message_id: ref.content_hash for ref in selected}
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT l.message_id,l.relation_type,m.content_hash,m.external_id AS message_external_id,
                          c.external_id AS conversation_external_id,s.external_id AS source_external_id,
                          l.created_by_decision_id
                   FROM message_memory_links l JOIN message_records m ON m.message_id=l.message_id
                   JOIN conversation_records c ON c.conversation_id=m.conversation_id
                   JOIN source_records s ON s.source_id=m.source_id WHERE l.memory_id=?""",
                (str(memory_id),),
            ).fetchall()
        if any(str(row["relation_type"]) != relation_type for row in rows):
            return False
        actual = {str(row["message_id"]): str(row["content_hash"] or "") for row in rows}
        if actual != expected:
            return False
        for row in rows:
            wanted = expected_refs.get(str(row["message_id"]))
            if wanted is None or wanted.external_key != ExternalMessageKey(str(row["source_external_id"] or ""), str(row["conversation_external_id"] or ""), str(row["message_external_id"] or "")):
                return False
            if decision_id is not None and str(row["created_by_decision_id"] or "") != str(decision_id):
                return False
        return True

    def unlink_message_memory_batch(
        self, messages: Iterable[ResolvedMessageRef], memory_id: str, *, decision_id: str,
        relation_type: str = "derived_from",
    ) -> tuple[ResolvedMessageRef, ...]:
        owner = self._required(decision_id, "decision_id")
        removed: list[ResolvedMessageRef] = []
        with self._lock, self._connection() as connection:
            for ref in messages:
                cursor = connection.execute(
                    "DELETE FROM message_memory_links WHERE message_id=? AND memory_id=? AND relation_type=? AND created_by_decision_id=?",
                    (ref.message_id, str(memory_id), relation_type, owner),
                )
                if cursor.rowcount:
                    removed.append(ref)
        return tuple(removed)

    def upsert_bundle(
        self,
        bundle: Mapping[str, Any],
        *,
        ingestion_batch_id: str | None = None,
        ingestion_ordinal_start: int = 0,
    ) -> dict[str, int | str]:
        if ingestion_batch_id is not None:
            ingestion_batch_id = self._required(ingestion_batch_id, "ingestion_batch_id")
        if type(ingestion_ordinal_start) is not int or ingestion_ordinal_start < 0:
            raise SourceReadModelError(
                "ingestion_ordinal_start must be a non-negative integer"
            )
        next_ordinal = ingestion_ordinal_start
        source = dict(bundle.get("source") or {})
        conversations = list(bundle.get("conversations") or [])
        with self._lock, self._connection() as connection:
            source_id = self._upsert_source(connection, source)
            counts = {"conversations": 0, "messages": 0, "links": 0}
            for conversation_value in conversations:
                conversation = dict(conversation_value or {})
                conversation.setdefault("source_id", source_id)
                conversation_id = self._upsert_conversation(connection, conversation)
                counts["conversations"] += 1
                for message_value in conversation.get("messages") or []:
                    message = dict(message_value or {})
                    message.setdefault("source_id", source_id)
                    message.setdefault("conversation_id", conversation_id)
                    message_id = self._upsert_message(
                        connection,
                        message,
                        ingestion_batch_id=ingestion_batch_id,
                        ingestion_ordinal=next_ordinal if ingestion_batch_id is not None else None,
                    )
                    counts["messages"] += 1
                    if ingestion_batch_id is not None:
                        next_ordinal += 1
                    for link_value in message.get("memory_links") or []:
                        link = dict(link_value or {})
                        self._link_message_memory(
                            connection,
                            message_id,
                            self._required(link.get("memory_id"), "memory_id"),
                            relation_type=str(link.get("relation_type") or "derived_from"),
                            confidence=link.get("confidence"),
                            created_at=link.get("created_at"),
                        )
                        counts["links"] += 1
        return {"source_id": source_id, "sources": 1, **counts, "next_ingestion_ordinal": next_ordinal}

    def rebuild(self, bundles: Iterable[Mapping[str, Any]]) -> dict[str, int]:
        selected = list(bundles)
        totals = {"sources": 0, "conversations": 0, "messages": 0, "links": 0}
        with self._lock, self._connection() as connection:
            connection.execute("DELETE FROM message_memory_links")
            connection.execute("DELETE FROM message_records")
            connection.execute("DELETE FROM conversation_records")
            connection.execute("DELETE FROM source_records")
            for bundle in selected:
                source = dict(bundle.get("source") or {})
                source_id = self._upsert_source(connection, source)
                totals["sources"] += 1
                for conversation_value in bundle.get("conversations") or []:
                    conversation = dict(conversation_value or {})
                    conversation.setdefault("source_id", source_id)
                    conversation_id = self._upsert_conversation(connection, conversation)
                    totals["conversations"] += 1
                    for message_value in conversation.get("messages") or []:
                        message = dict(message_value or {})
                        message.setdefault("source_id", source_id)
                        message.setdefault("conversation_id", conversation_id)
                        message_id = self._upsert_message(connection, message)
                        totals["messages"] += 1
                        for link_value in message.get("memory_links") or []:
                            link = dict(link_value or {})
                            self._link_message_memory(
                                connection,
                                message_id,
                                self._required(link.get("memory_id"), "memory_id"),
                                relation_type=str(link.get("relation_type") or "derived_from"),
                                confidence=link.get("confidence"),
                                created_at=link.get("created_at"),
                            )
                            totals["links"] += 1
            connection.execute(
                """
                INSERT INTO source_read_model_meta(key, value) VALUES ('last_rebuild_at', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (self._now(),),
            )
        return totals

    def get_source(self, source_id: str) -> dict[str, Any] | None:
        return self._get_one("source_records", "source_id", source_id, self._source_dict)

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        return self._get_one(
            "conversation_records", "conversation_id", conversation_id, self._conversation_dict
        )

    def get_message(self, message_id: str, *, include_content: bool) -> dict[str, Any] | None:
        with self._connection() as connection:
            if include_content:
                query = "SELECT * FROM message_records WHERE message_id = ?"
            else:
                # Keep metadata reads genuinely body-free.  In particular,
                # do not SELECT the potentially very large content column;
                # only a bounded preview and its length are projected.
                query = """
                    SELECT message_id, conversation_id, source_id, external_id,
                           role, author, occurred_at, sequence,
                           length(content) AS content_length,
                           substr(replace(replace(content, char(13), ' '), char(10), ' '), 1, 200)
                               AS content_preview,
                           content_hash, raw_reference, privacy, projects_json,
                           agent_scope_json, privacy_inherited, projects_inherited,
                           agent_scope_inherited, created_at, updated_at, metadata_json
                    FROM message_records
                    WHERE message_id = ?
                """
            row = connection.execute(query, (message_id,)).fetchone()
        return self._message_dict(row, include_content=include_content) if row else None

    def list_sources(
        self,
        *,
        source_type: str | None = None,
        privacy: tuple[str, ...] = (),
        project: str | None = None,
        status: str | None = None,
        q: str | None = None,
        agent_id: str | None = None,
        owner: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        where: list[str] = []
        params: list[Any] = []
        self._add_equal(where, params, "source_type", source_type)
        self._add_in(where, params, "privacy", privacy)
        self._add_equal(where, params, "status", status)
        self._add_project(where, params, "projects_json", project)
        self._add_scope(where, params, "agent_scope_json", agent_id, owner)
        self._add_like(where, params, q, ("display_name", "external_id", "metadata_json"))
        return self._paged(
            "source_records",
            where,
            params,
            "COALESCE(updated_at, created_at, '') DESC, source_id DESC",
            self._source_dict,
            limit,
            offset,
        )

    def list_conversations(
        self,
        *,
        source_id: str | None = None,
        source_type: str | None = None,
        privacy: tuple[str, ...] = (),
        project: str | None = None,
        from_time: str | None = None,
        to_time: str | None = None,
        q: str | None = None,
        agent_id: str | None = None,
        owner: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        where: list[str] = []
        params: list[Any] = []
        self._add_equal(where, params, "c.source_id", source_id)
        self._add_equal(where, params, "s.source_type", source_type)
        self._add_in(where, params, "c.privacy", privacy)
        self._add_project(where, params, "c.projects_json", project)
        self._add_scope(where, params, "c.agent_scope_json", agent_id, owner)
        self._add_time(where, params, "c.started_at", from_time, to_time)
        self._add_like(where, params, q, ("c.title", "c.external_id", "c.metadata_json"))
        where_sql = " WHERE " + " AND ".join(where) if where else ""
        selected_limit, selected_offset = self._page_values(limit, offset)
        with self._connection() as connection:
            total = int(
                connection.execute(
                    f"""
                    SELECT COUNT(*) AS count
                    FROM conversation_records c
                    JOIN source_records s ON s.source_id = c.source_id
                    {where_sql}
                    """,
                    params,
                ).fetchone()["count"]
            )
            rows = connection.execute(
                f"""
                SELECT c.*, s.source_type, s.display_name AS source_display_name
                FROM conversation_records c
                JOIN source_records s ON s.source_id = c.source_id
                {where_sql}
                ORDER BY COALESCE(c.started_at, c.updated_at, c.created_at, '') DESC,
                         c.conversation_id DESC
                LIMIT ? OFFSET ?
                """,
                [*params, selected_limit, selected_offset],
            ).fetchall()
        return self._page_result(
            [self._conversation_dict(row) for row in rows],
            total,
            selected_limit,
            selected_offset,
        )

    def list_messages(
        self,
        *,
        conversation_id: str | None = None,
        source_id: str | None = None,
        role: str | None = None,
        privacy: tuple[str, ...] = (),
        from_time: str | None = None,
        to_time: str | None = None,
        q: str | None = None,
        agent_id: str | None = None,
        owner: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        where: list[str] = []
        params: list[Any] = []
        self._add_equal(where, params, "m.conversation_id", conversation_id)
        self._add_equal(where, params, "m.source_id", source_id)
        self._add_equal(where, params, "m.role", role)
        self._add_in(where, params, "m.privacy", privacy)
        self._add_scope(where, params, "m.agent_scope_json", agent_id, owner)
        self._add_time(where, params, "m.occurred_at", from_time, to_time)
        self._add_like(where, params, q, ("m.content", "m.author", "m.external_id"))
        where_sql = " WHERE " + " AND ".join(where) if where else ""
        selected_limit, selected_offset = self._page_values(limit, offset)
        with self._connection() as connection:
            total = int(
                connection.execute(
                    f"SELECT COUNT(*) AS count FROM message_records m {where_sql}", params
                ).fetchone()["count"]
            )
            rows = connection.execute(
                f"""
                SELECT m.*, s.external_id AS source_external_id,
                       c.external_id AS conversation_external_id
                FROM message_records m
                JOIN source_records s ON s.source_id = m.source_id
                JOIN conversation_records c ON c.conversation_id = m.conversation_id
                {where_sql}
                ORDER BY COALESCE(m.occurred_at, m.updated_at, m.created_at, '') DESC,
                         m.sequence DESC, m.message_id DESC
                LIMIT ? OFFSET ?
                """,
                [*params, selected_limit, selected_offset],
            ).fetchall()
        return self._page_result(
            [self._message_dict(row, include_content=False) for row in rows],
            total,
            selected_limit,
            selected_offset,
        )

    def list_ingestion_messages(
        self,
        ingestion_batch_id: str,
        *,
        limit: int = 200,
        offset: int = 0,
    ) -> dict[str, Any]:
        selected_limit, selected_offset = self._page_values(limit, offset)
        batch_id = self._required(ingestion_batch_id, "ingestion_batch_id")
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    m.source_id,
                    s.external_id AS source_external_id,
                    m.conversation_id,
                    c.external_id AS conversation_external_id,
                    m.message_id,
                    m.external_id AS message_external_id,
                    m.ingestion_batch_id,
                    m.ingestion_ordinal,
                    typeof(m.ingestion_ordinal) AS ingestion_ordinal_type,
                    m.sequence,
                    m.role,
                    m.occurred_at,
                    m.content_hash
                FROM message_records m
                JOIN source_records s ON s.source_id = m.source_id
                JOIN conversation_records c ON c.conversation_id = m.conversation_id
                WHERE m.ingestion_batch_id = ?
                ORDER BY m.ingestion_ordinal ASC, m.message_id ASC
                """,
                (batch_id,),
            ).fetchall()
            if not rows:
                return self._page_result([], 0, selected_limit, selected_offset)
            ordinals = [row["ingestion_ordinal"] for row in rows]
            if any(ordinal is None for ordinal in ordinals):
                raise SourceReadModelError(
                    f"ingestion batch contains NULL ordinal: {batch_id}"
                )
            if any(
                row["ingestion_ordinal_type"] != "integer"
                or type(row["ingestion_ordinal"]) is not int
                for row in rows
            ):
                raise SourceReadModelError(
                    f"ingestion batch contains malformed ordinal: {batch_id}"
                )
            numeric_ordinals = [row["ingestion_ordinal"] for row in rows]
            if numeric_ordinals != list(
                range(0, len(numeric_ordinals))
            ):
                raise SourceReadModelError(
                    f"ingestion batch ordinals are duplicate or non-contiguous: {batch_id}"
                )
            total = len(rows)
            page_rows = rows[selected_offset : selected_offset + selected_limit]
        items = [
            {
                "source_id": row["source_id"],
                "source_external_id": row["source_external_id"],
                "conversation_id": row["conversation_id"],
                "conversation_external_id": row["conversation_external_id"],
                "message_id": row["message_id"],
                "message_external_id": row["message_external_id"],
                "ingestion_batch_id": row["ingestion_batch_id"],
                "ingestion_ordinal": row["ingestion_ordinal"],
                "sequence": row["sequence"],
                "role": row["role"],
                "occurred_at": row["occurred_at"],
                "content_hash": row["content_hash"],
            }
            for row in page_rows
        ]
        return self._page_result(items, total, selected_limit, selected_offset)

    def message_links(self, message_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT message_id, memory_id, relation_type, confidence, created_at, created_by_decision_id
                FROM message_memory_links
                WHERE message_id = ?
                ORDER BY created_at DESC, memory_id
                """,
                (message_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def memory_links(self, memory_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    l.message_id, l.memory_id, l.relation_type, l.confidence, l.created_at, l.created_by_decision_id,
                    m.conversation_id, m.source_id, m.role, m.author, m.occurred_at,
                    substr(replace(replace(m.content, char(13), ' '), char(10), ' '), 1, 200)
                        AS content_preview
                FROM message_memory_links l
                JOIN message_records m ON m.message_id = l.message_id
                WHERE l.memory_id = ?
                ORDER BY COALESCE(m.occurred_at, l.created_at, '') DESC, l.message_id DESC
                """,
                (memory_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def resolve_message_refs(self, refs: Iterable[str]) -> tuple[str, ...]:
        """Resolve explicit message/source/conversation/evidence refs fail-closed."""
        values = tuple(dict.fromkeys(str(item).strip() for item in refs if str(item).strip()))
        resolved: list[str] = []
        with self._connection() as connection:
            for reference in values:
                rows = connection.execute(
                    """
                    SELECT DISTINCT m.message_id
                    FROM message_records m
                    JOIN conversation_records c ON c.conversation_id = m.conversation_id
                    JOIN source_records s ON s.source_id = m.source_id
                    WHERE m.message_id = ? OR m.external_id = ?
                       OR c.conversation_id = ? OR c.external_id = ?
                       OR s.source_id = ? OR s.external_id = ?
                       OR m.raw_reference = ? OR m.metadata_json LIKE ?
                    ORDER BY m.message_id
                    """,
                    (reference, reference, reference, reference, reference, reference,
                     reference, f'%"{reference}"%'),
                ).fetchall()
                if len(rows) != 1:
                    if not rows:
                        raise SourceReadModelError(f"unresolved message provenance reference: {reference}")
                    raise SourceReadModelError(f"ambiguous message provenance reference: {reference}")
                resolved.append(str(rows[0]["message_id"]))
        return tuple(dict.fromkeys(resolved))

    def unlink_message_memory(self, message_id: str, memory_id: str, *, relation_type: str = "derived_from") -> None:
        with self._lock, self._connection() as connection:
            connection.execute(
                "DELETE FROM message_memory_links WHERE message_id = ? AND memory_id = ? AND relation_type = ?",
                (self._required(message_id, "message_id"), self._required(memory_id, "memory_id"), self._required(relation_type, "relation_type")),
            )

    def stats(self) -> dict[str, Any]:
        with self._connection() as connection:
            counts = {
                table: int(
                    connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()[
                        "count"
                    ]
                )
                for table in (
                    "source_records",
                    "conversation_records",
                    "message_records",
                    "message_memory_links",
                )
            }
            row = connection.execute(
                "SELECT value FROM source_read_model_meta WHERE key = 'last_rebuild_at'"
            ).fetchone()
        return {
            "schema_version": self.schema_version(),
            "sources": counts["source_records"],
            "conversations": counts["conversation_records"],
            "messages": counts["message_records"],
            "message_memory_links": counts["message_memory_links"],
            "last_rebuild_at": str(row["value"]) if row else None,
        }

    def _upsert_source(self, connection: sqlite3.Connection, record: Mapping[str, Any]) -> str:
        source_type = self._required(record.get("source_type"), "source_type")
        external_id = self._optional(record.get("external_id"))
        raw_reference = self._optional(record.get("raw_reference"))
        vault_reference = self._optional(record.get("vault_reference"))
        content_hash = str(record.get("content_hash") or "").strip() or self.content_hash(
            record.get("display_name") or external_id or raw_reference or vault_reference
        )
        existing = (
            connection.execute(
                "SELECT * FROM source_records WHERE source_type = ? AND external_id = ?",
                (source_type, external_id),
            ).fetchone()
            if external_id
            else None
        )
        source_id = (
            str(existing["source_id"])
            if existing
            else str(record.get("source_id") or "").strip()
            or self.stable_id(
                "source",
                source_type,
                external_id or raw_reference or vault_reference or content_hash,
            )
        )
        now = self._now()
        privacy = str(
            record.get("privacy")
            if "privacy" in record and record.get("privacy") not in (None, "")
            else (existing["privacy"] if existing else "private")
        )
        projects = (
            self._as_list(record.get("projects") if "projects" in record else record.get("project"))
            if "projects" in record or "project" in record
            else self._loads(existing["projects_json"], []) if existing else []
        )
        agent_scope = (
            self._as_list(record.get("agent_scope"))
            if "agent_scope" in record
            else self._loads(existing["agent_scope_json"], []) if existing else []
        )
        connection.execute(
            """
            INSERT INTO source_records(
                source_id, source_type, display_name, external_id, raw_reference,
                vault_reference, privacy, projects_json, agent_scope_json, status,
                content_hash, created_at, updated_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                source_type = excluded.source_type,
                display_name = excluded.display_name,
                external_id = excluded.external_id,
                raw_reference = excluded.raw_reference,
                vault_reference = excluded.vault_reference,
                privacy = excluded.privacy,
                projects_json = excluded.projects_json,
                agent_scope_json = excluded.agent_scope_json,
                status = excluded.status,
                content_hash = excluded.content_hash,
                created_at = COALESCE(source_records.created_at, excluded.created_at),
                updated_at = excluded.updated_at,
                metadata_json = excluded.metadata_json
            """,
            (
                source_id,
                source_type,
                str(record.get("display_name") or record.get("title") or external_id or source_id),
                external_id,
                raw_reference,
                vault_reference,
                privacy,
                self._json(projects),
                self._json(agent_scope),
                str(record.get("status") or (existing["status"] if existing else "active")),
                content_hash,
                str(record.get("created_at") or (existing["created_at"] if existing else now)),
                str(record.get("updated_at") or now),
                self._json(
                    dict(record.get("metadata") or {})
                    if "metadata" in record
                    else self._loads(existing["metadata_json"], {})
                    if existing
                    else {}
                ),
            ),
        )
        self._sync_source_descendants(connection, source_id)
        return source_id

    def _upsert_conversation(
        self, connection: sqlite3.Connection, record: Mapping[str, Any]
    ) -> str:
        source_id = self._required(record.get("source_id"), "source_id")
        source_row = connection.execute(
            "SELECT privacy, projects_json, agent_scope_json FROM source_records WHERE source_id = ?",
            (source_id,),
        ).fetchone()
        if source_row is None:
            raise LookupError(f"source not found: {source_id}")
        external_id = self._optional(record.get("external_id"))
        existing = self._find_existing_conversation(connection, record, source_id)
        title = str(record.get("title") or (existing["title"] if existing else "Untitled conversation")).strip()
        privacy, privacy_inherited = self._resolve_scalar(
            record,
            "privacy",
            str(source_row["privacy"] or "private"),
            existing,
            "privacy",
            "privacy_inherited",
        )
        projects, projects_inherited = self._resolve_list(
            record,
            ("projects", "project"),
            self._loads(source_row["projects_json"], []),
            existing,
            "projects_json",
            "projects_inherited",
        )
        agent_scope, agent_scope_inherited = self._resolve_list(
            record,
            ("agent_scope",),
            self._loads(source_row["agent_scope_json"], []),
            existing,
            "agent_scope_json",
            "agent_scope_inherited",
        )
        content_hash = str(record.get("content_hash") or "").strip() or self.content_hash(
            json.dumps(
                {
                    "source_id": source_id,
                    "external_id": external_id,
                    "title": title,
                    "started_at": record.get("started_at"),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        conversation_id = (
            str(existing["conversation_id"])
            if existing
            else str(record.get("conversation_id") or "").strip()
            or self.stable_id("conversation", source_id, external_id or content_hash)
        )
        now = self._now()
        connection.execute(
            """
            INSERT INTO conversation_records(
                conversation_id, source_id, external_id, title, participants_json,
                started_at, ended_at, message_count, privacy, projects_json,
                agent_scope_json, privacy_inherited, projects_inherited,
                agent_scope_inherited, content_hash, created_at, updated_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(conversation_id) DO UPDATE SET
                source_id = excluded.source_id,
                external_id = excluded.external_id,
                title = excluded.title,
                participants_json = excluded.participants_json,
                started_at = excluded.started_at,
                ended_at = excluded.ended_at,
                message_count = excluded.message_count,
                privacy = excluded.privacy,
                projects_json = excluded.projects_json,
                agent_scope_json = excluded.agent_scope_json,
                privacy_inherited = excluded.privacy_inherited,
                projects_inherited = excluded.projects_inherited,
                agent_scope_inherited = excluded.agent_scope_inherited,
                content_hash = excluded.content_hash,
                created_at = COALESCE(conversation_records.created_at, excluded.created_at),
                updated_at = excluded.updated_at,
                metadata_json = excluded.metadata_json
            """,
            (
                conversation_id,
                source_id,
                external_id,
                title,
                self._json(
                    self._as_list(record.get("participants"))
                    if "participants" in record
                    else self._loads(existing["participants_json"], []) if existing else []
                ),
                self._optional(
                    record.get("started_at")
                    if "started_at" in record
                    else existing["started_at"] if existing else None
                ),
                self._optional(
                    record.get("ended_at")
                    if "ended_at" in record
                    else existing["ended_at"] if existing else None
                ),
                int(
                    record.get("message_count")
                    if record.get("message_count") is not None
                    else len(record.get("messages") or [])
                    if "messages" in record
                    else existing["message_count"] if existing else 0
                ),
                privacy,
                self._json(projects),
                self._json(agent_scope),
                privacy_inherited,
                projects_inherited,
                agent_scope_inherited,
                content_hash,
                str(record.get("created_at") or (existing["created_at"] if existing else now)),
                str(record.get("updated_at") or now),
                self._json(
                    dict(record.get("metadata") or {})
                    if "metadata" in record
                    else self._loads(existing["metadata_json"], {})
                    if existing
                    else {}
                ),
            ),
        )
        self._sync_conversation_messages(connection, conversation_id)
        return conversation_id

    def _upsert_message(
        self,
        connection: sqlite3.Connection,
        record: Mapping[str, Any],
        *,
        ingestion_batch_id: str | None = None,
        ingestion_ordinal: int | None = None,
    ) -> str:
        conversation_id = self._required(record.get("conversation_id"), "conversation_id")
        source_id = self._required(record.get("source_id"), "source_id")
        conversation_row = connection.execute(
            """
            SELECT source_id, privacy, projects_json, agent_scope_json
            FROM conversation_records WHERE conversation_id = ?
            """,
            (conversation_id,),
        ).fetchone()
        if conversation_row is None:
            raise LookupError(f"conversation not found: {conversation_id}")
        if str(conversation_row["source_id"]) != source_id:
            raise ValueError("message source_id does not match conversation source_id")
        role = self._required(record.get("role"), "role")
        external_id = self._optional(record.get("external_id"))
        existing = self._find_existing_message(connection, record, conversation_id)
        privacy, privacy_inherited = self._resolve_scalar(
            record,
            "privacy",
            str(conversation_row["privacy"] or "private"),
            existing,
            "privacy",
            "privacy_inherited",
        )
        projects, projects_inherited = self._resolve_list(
            record,
            ("projects", "project"),
            self._loads(conversation_row["projects_json"], []),
            existing,
            "projects_json",
            "projects_inherited",
        )
        agent_scope, agent_scope_inherited = self._resolve_list(
            record,
            ("agent_scope",),
            self._loads(conversation_row["agent_scope_json"], []),
            existing,
            "agent_scope_json",
            "agent_scope_inherited",
        )
        content = str(record.get("content") if "content" in record else existing["content"] if existing else "")
        content_hash = str(record.get("content_hash") or "").strip() or self.content_hash(content)
        sequence = int(
            record.get("sequence")
            if record.get("sequence") is not None
            else existing["sequence"] if existing else 0
        )
        message_id = (
            str(existing["message_id"])
            if existing
            else str(record.get("message_id") or "").strip()
            or self.stable_id(
                "message",
                conversation_id,
                external_id or f"{sequence}:{role}:{content_hash}",
            )
        )
        stored_ingestion_batch_id = (
            ingestion_batch_id
            if ingestion_batch_id is not None
            else existing["ingestion_batch_id"] if existing is not None else None
        )
        stored_ingestion_ordinal = (
            ingestion_ordinal
            if ingestion_batch_id is not None
            else existing["ingestion_ordinal"] if existing is not None else None
        )
        now = self._now()
        connection.execute(
            """
            INSERT INTO message_records(
                message_id, conversation_id, source_id, external_id, role, author,
                occurred_at, sequence, content, content_hash, raw_reference, privacy,
                projects_json, agent_scope_json, privacy_inherited, projects_inherited,
                agent_scope_inherited, created_at, updated_at, metadata_json
                , ingestion_batch_id, ingestion_ordinal
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(message_id) DO UPDATE SET
                conversation_id = excluded.conversation_id,
                source_id = excluded.source_id,
                external_id = excluded.external_id,
                role = excluded.role,
                author = excluded.author,
                occurred_at = excluded.occurred_at,
                sequence = excluded.sequence,
                content = excluded.content,
                content_hash = excluded.content_hash,
                raw_reference = excluded.raw_reference,
                privacy = excluded.privacy,
                projects_json = excluded.projects_json,
                agent_scope_json = excluded.agent_scope_json,
                privacy_inherited = excluded.privacy_inherited,
                projects_inherited = excluded.projects_inherited,
                agent_scope_inherited = excluded.agent_scope_inherited,
                created_at = COALESCE(message_records.created_at, excluded.created_at),
                updated_at = excluded.updated_at,
                metadata_json = excluded.metadata_json,
                ingestion_batch_id = excluded.ingestion_batch_id,
                ingestion_ordinal = excluded.ingestion_ordinal
            """,
            (
                message_id,
                conversation_id,
                source_id,
                external_id,
                role,
                self._optional(
                    record.get("author") if "author" in record else existing["author"] if existing else None
                ),
                self._optional(
                    record.get("occurred_at")
                    if "occurred_at" in record
                    else existing["occurred_at"] if existing else None
                ),
                sequence,
                content,
                content_hash,
                self._optional(
                    record.get("raw_reference")
                    if "raw_reference" in record
                    else existing["raw_reference"] if existing else None
                ),
                privacy,
                self._json(projects),
                self._json(agent_scope),
                privacy_inherited,
                projects_inherited,
                agent_scope_inherited,
                str(record.get("created_at") or (existing["created_at"] if existing else now)),
                str(record.get("updated_at") or now),
                self._json(
                    dict(record.get("metadata") or {})
                    if "metadata" in record
                    else self._loads(existing["metadata_json"], {})
                    if existing
                    else {}
                ),
                stored_ingestion_batch_id,
                stored_ingestion_ordinal,
            ),
        )
        connection.execute(
            """
            UPDATE conversation_records
            SET message_count = (
                SELECT COUNT(*) FROM message_records WHERE conversation_id = ?
            ), updated_at = ?
            WHERE conversation_id = ?
            """,
            (conversation_id, now, conversation_id),
        )
        return message_id

    def _sync_source_descendants(self, connection: sqlite3.Connection, source_id: str) -> None:
        source = connection.execute(
            "SELECT privacy, projects_json, agent_scope_json FROM source_records WHERE source_id = ?",
            (source_id,),
        ).fetchone()
        if source is None:
            return
        connection.execute(
            """
            UPDATE conversation_records
            SET privacy = CASE WHEN privacy_inherited = 1 THEN ? ELSE privacy END,
                projects_json = CASE WHEN projects_inherited = 1 THEN ? ELSE projects_json END,
                agent_scope_json = CASE WHEN agent_scope_inherited = 1 THEN ? ELSE agent_scope_json END
            WHERE source_id = ?
            """,
            (
                source["privacy"],
                source["projects_json"],
                source["agent_scope_json"],
                source_id,
            ),
        )
        connection.execute(
            """
            UPDATE message_records
            SET privacy = CASE WHEN privacy_inherited = 1 THEN (
                    SELECT c.privacy FROM conversation_records c
                    WHERE c.conversation_id = message_records.conversation_id
                ) ELSE privacy END,
                projects_json = CASE WHEN projects_inherited = 1 THEN (
                    SELECT c.projects_json FROM conversation_records c
                    WHERE c.conversation_id = message_records.conversation_id
                ) ELSE projects_json END,
                agent_scope_json = CASE WHEN agent_scope_inherited = 1 THEN (
                    SELECT c.agent_scope_json FROM conversation_records c
                    WHERE c.conversation_id = message_records.conversation_id
                ) ELSE agent_scope_json END
            WHERE source_id = ?
            """,
            (source_id,),
        )

    def _sync_conversation_messages(
        self, connection: sqlite3.Connection, conversation_id: str
    ) -> None:
        parent = connection.execute(
            """
            SELECT privacy, projects_json, agent_scope_json
            FROM conversation_records WHERE conversation_id = ?
            """,
            (conversation_id,),
        ).fetchone()
        if parent is None:
            return
        connection.execute(
            """
            UPDATE message_records
            SET privacy = CASE WHEN privacy_inherited = 1 THEN ? ELSE privacy END,
                projects_json = CASE WHEN projects_inherited = 1 THEN ? ELSE projects_json END,
                agent_scope_json = CASE WHEN agent_scope_inherited = 1 THEN ? ELSE agent_scope_json END
            WHERE conversation_id = ?
            """,
            (
                parent["privacy"],
                parent["projects_json"],
                parent["agent_scope_json"],
                conversation_id,
            ),
        )

    def _find_existing_conversation(
        self, connection: sqlite3.Connection, record: Mapping[str, Any], source_id: str
    ) -> sqlite3.Row | None:
        external_id = self._optional(record.get("external_id"))
        if external_id:
            row = connection.execute(
                "SELECT * FROM conversation_records WHERE source_id = ? AND external_id = ?",
                (source_id, external_id),
            ).fetchone()
            if row is not None:
                return row
        conversation_id = str(record.get("conversation_id") or "").strip()
        if conversation_id:
            return connection.execute(
                "SELECT * FROM conversation_records WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
        return None

    def _find_existing_message(
        self, connection: sqlite3.Connection, record: Mapping[str, Any], conversation_id: str
    ) -> sqlite3.Row | None:
        external_id = self._optional(record.get("external_id"))
        if external_id:
            row = connection.execute(
                "SELECT * FROM message_records WHERE conversation_id = ? AND external_id = ?",
                (conversation_id, external_id),
            ).fetchone()
            if row is not None:
                return row
        message_id = str(record.get("message_id") or "").strip()
        if message_id:
            return connection.execute(
                "SELECT * FROM message_records WHERE message_id = ?", (message_id,)
            ).fetchone()
        return None

    @staticmethod
    def _resolve_scalar(
        record: Mapping[str, Any],
        key: str,
        parent_value: str,
        existing: sqlite3.Row | None,
        value_column: str,
        inherited_column: str,
    ) -> tuple[str, int]:
        if key in record and record.get(key) not in (None, ""):
            return str(record.get(key)), 0
        if existing is not None:
            return str(existing[value_column]), int(existing[inherited_column])
        return parent_value, 1

    @classmethod
    def _resolve_list(
        cls,
        record: Mapping[str, Any],
        keys: tuple[str, ...],
        parent_value: list[Any],
        existing: sqlite3.Row | None,
        value_column: str,
        inherited_column: str,
    ) -> tuple[list[Any], int]:
        for key in keys:
            if key in record:
                return cls._as_list(record.get(key)), 0
        if existing is not None:
            return cls._loads(existing[value_column], []), int(existing[inherited_column])
        return list(parent_value), 1

    def _link_message_memory(
        self,
        connection: sqlite3.Connection,
        message_id: str,
        memory_id: str,
        *,
        relation_type: str,
        confidence: float | None,
        created_at: Any,
    ) -> None:
        connection.execute(
            """
            INSERT INTO message_memory_links(
                message_id, memory_id, relation_type, confidence, created_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(message_id, memory_id, relation_type) DO UPDATE SET
                confidence = excluded.confidence,
                created_at = excluded.created_at
            """,
            (
                self._required(message_id, "message_id"),
                self._required(memory_id, "memory_id"),
                self._required(relation_type, "relation_type"),
                confidence,
                str(created_at or self._now()),
            ),
        )

    def _get_one(self, table: str, key: str, value: str, mapper) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                f"SELECT * FROM {table} WHERE {key} = ?", (value,)
            ).fetchone()
        return mapper(row) if row else None

    def _paged(
        self,
        table: str,
        where: list[str],
        params: list[Any],
        order_by: str,
        mapper,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        where_sql = " WHERE " + " AND ".join(where) if where else ""
        selected_limit, selected_offset = self._page_values(limit, offset)
        with self._connection() as connection:
            total = int(
                connection.execute(
                    f"SELECT COUNT(*) AS count FROM {table}{where_sql}", params
                ).fetchone()["count"]
            )
            rows = connection.execute(
                f"SELECT * FROM {table}{where_sql} ORDER BY {order_by} LIMIT ? OFFSET ?",
                [*params, selected_limit, selected_offset],
            ).fetchall()
        return self._page_result(
            [mapper(row) for row in rows], total, selected_limit, selected_offset
        )

    @staticmethod
    def _page_values(limit: int, offset: int) -> tuple[int, int]:
        selected_limit = int(limit)
        selected_offset = int(offset)
        if selected_limit < 1 or selected_limit > 200:
            raise ValueError("limit must be between 1 and 200")
        if selected_offset < 0:
            raise ValueError("offset must be greater than or equal to zero")
        return selected_limit, selected_offset

    @staticmethod
    def _page_result(
        items: list[dict[str, Any]], total: int, limit: int, offset: int
    ) -> dict[str, Any]:
        return {
            "items": items,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total,
                "has_more": offset + len(items) < total,
            },
        }

    @staticmethod
    def _add_equal(where: list[str], params: list[Any], column: str, value: Any) -> None:
        if value not in (None, ""):
            where.append(f"{column} = ?")
            params.append(str(value))

    @staticmethod
    def _add_in(
        where: list[str], params: list[Any], column: str, values: tuple[str, ...]
    ) -> None:
        selected = tuple(str(value) for value in values if str(value))
        if selected:
            where.append(f"{column} IN ({','.join('?' for _ in selected)})")
            params.extend(selected)

    @staticmethod
    def _add_project(
        where: list[str], params: list[Any], column: str, project: str | None
    ) -> None:
        if project:
            where.append(f"EXISTS (SELECT 1 FROM json_each({column}) WHERE value = ?)")
            params.append(project)

    @staticmethod
    def _add_scope(
        where: list[str],
        params: list[Any],
        column: str,
        agent_id: str | None,
        owner: bool,
    ) -> None:
        if owner:
            return
        if not agent_id:
            where.append(f"json_array_length({column}) = 0")
            return
        where.append(
            f"""(
                json_array_length({column}) = 0 OR
                EXISTS (
                    SELECT 1 FROM json_each({column})
                    WHERE value IN (?, 'all')
                )
            )"""
        )
        params.append(agent_id)

    @staticmethod
    def _add_time(
        where: list[str],
        params: list[Any],
        column: str,
        from_time: str | None,
        to_time: str | None,
    ) -> None:
        if from_time:
            where.append(f"({column} IS NOT NULL AND {column} >= ?)")
            params.append(from_time)
        if to_time:
            where.append(f"({column} IS NOT NULL AND {column} <= ?)")
            params.append(to_time)

    @classmethod
    def _add_like(
        cls,
        where: list[str],
        params: list[Any],
        query: str | None,
        columns: tuple[str, ...],
    ) -> None:
        clean = " ".join(str(query or "").strip().split())
        if not clean:
            return
        escaped = clean.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where.append(
            "(" + " OR ".join(f"{column} LIKE ? ESCAPE '\\'" for column in columns) + ")"
        )
        params.extend([f"%{escaped}%"] * len(columns))

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _loads(value: Any, fallback: Any) -> Any:
        if value in (None, ""):
            return fallback
        try:
            return json.loads(str(value))
        except (TypeError, ValueError, json.JSONDecodeError):
            return fallback

    @classmethod
    def _source_dict(cls, row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["projects"] = cls._loads(item.pop("projects_json", "[]"), [])
        item["agent_scope"] = cls._loads(item.pop("agent_scope_json", "[]"), [])
        item["metadata"] = cls._loads(item.pop("metadata_json", "{}"), {})
        return item

    @classmethod
    def _conversation_dict(cls, row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["participants"] = cls._loads(item.pop("participants_json", "[]"), [])
        item["projects"] = cls._loads(item.pop("projects_json", "[]"), [])
        item["agent_scope"] = cls._loads(item.pop("agent_scope_json", "[]"), [])
        item["privacy_inherited"] = bool(item.get("privacy_inherited"))
        item["projects_inherited"] = bool(item.get("projects_inherited"))
        item["agent_scope_inherited"] = bool(item.get("agent_scope_inherited"))
        item["metadata"] = cls._loads(item.pop("metadata_json", "{}"), {})
        return item

    @classmethod
    def _message_dict(cls, row: sqlite3.Row, *, include_content: bool) -> dict[str, Any]:
        item = dict(row)
        item.pop("ingestion_batch_id", None)
        item.pop("ingestion_ordinal", None)
        has_content = "content" in item
        content = str(item.pop("content", "") or "")
        if has_content:
            item["content_length"] = len(content)
            item["content_preview"] = " ".join(content.split())[:200]
        else:
            item["content_length"] = int(item.get("content_length") or 0)
            item["content_preview"] = " ".join(
                str(item.get("content_preview") or "").split()
            )[:200]
        if include_content:
            item["content"] = content
        item["projects"] = cls._loads(item.pop("projects_json", "[]"), [])
        item["agent_scope"] = cls._loads(item.pop("agent_scope_json", "[]"), [])
        item["privacy_inherited"] = bool(item.get("privacy_inherited"))
        item["projects_inherited"] = bool(item.get("projects_inherited"))
        item["agent_scope_inherited"] = bool(item.get("agent_scope_inherited"))
        item["metadata"] = cls._loads(item.pop("metadata_json", "{}"), {})
        return item

    @staticmethod
    def _as_list(value: Any) -> list[Any]:
        if value in (None, "", []):
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, (tuple, set)):
            return list(value)
        return [value]

    @staticmethod
    def _required(value: Any, label: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError(f"{label} is required")
        return text

    @staticmethod
    def _optional(value: Any) -> str | None:
        text = str(value or "").strip()
        return text or None

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
