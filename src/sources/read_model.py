from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

SOURCE_READ_MODEL_SCHEMA_VERSION = "1"
_ID_PREFIXES = {"source": "LJ-SRC", "conversation": "LJ-CONV", "message": "LJ-MSG"}


class SourceReadModelError(RuntimeError):
    """Raised when the rebuildable source read model cannot be queried."""


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
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS source_read_model_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

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
                    created_at TEXT,
                    updated_at TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
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
            )
            connection.execute(
                """
                INSERT INTO source_read_model_meta(key, value) VALUES ('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (SOURCE_READ_MODEL_SCHEMA_VERSION,),
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

    def upsert_bundle(self, bundle: Mapping[str, Any]) -> dict[str, int | str]:
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
                    message_id = self._upsert_message(connection, message)
                    counts["messages"] += 1
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
        return {"source_id": source_id, "sources": 1, **counts}

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
            row = connection.execute(
                "SELECT * FROM message_records WHERE message_id = ?", (message_id,)
            ).fetchone()
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
                SELECT m.* FROM message_records m {where_sql}
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

    def message_links(self, message_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT message_id, memory_id, relation_type, confidence, created_at
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
                    l.message_id, l.memory_id, l.relation_type, l.confidence, l.created_at,
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

    def stats(self) -> dict[str, Any]:
        with self._connection() as connection:
            counts = {
                table: int(
                    connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"]
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
                "SELECT source_id FROM source_records WHERE source_type = ? AND external_id = ?",
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
                str(record.get("privacy") or "private"),
                self._json(self._as_list(record.get("projects") or record.get("project"))),
                self._json(self._as_list(record.get("agent_scope"))),
                str(record.get("status") or "active"),
                content_hash,
                str(record.get("created_at") or now),
                str(record.get("updated_at") or now),
                self._json(dict(record.get("metadata") or {})),
            ),
        )
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
        title = str(record.get("title") or "Untitled conversation").strip()
        privacy = str(record.get("privacy") or source_row["privacy"] or "private")
        projects = self._as_list(record.get("projects") or record.get("project"))
        if not projects:
            projects = self._loads(source_row["projects_json"], [])
        agent_scope = self._as_list(record.get("agent_scope"))
        if not agent_scope:
            agent_scope = self._loads(source_row["agent_scope_json"], [])
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
        existing = (
            connection.execute(
                "SELECT conversation_id FROM conversation_records WHERE source_id = ? AND external_id = ?",
                (source_id, external_id),
            ).fetchone()
            if external_id
            else None
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
                agent_scope_json, content_hash, created_at, updated_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                self._json(self._as_list(record.get("participants"))),
                self._optional(record.get("started_at")),
                self._optional(record.get("ended_at")),
                int(record.get("message_count") or len(record.get("messages") or [])),
                privacy,
                self._json(projects),
                self._json(agent_scope),
                content_hash,
                str(record.get("created_at") or now),
                str(record.get("updated_at") or now),
                self._json(dict(record.get("metadata") or {})),
            ),
        )
        return conversation_id

    def _upsert_message(self, connection: sqlite3.Connection, record: Mapping[str, Any]) -> str:
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
        privacy = str(record.get("privacy") or conversation_row["privacy"] or "private")
        projects = self._as_list(record.get("projects") or record.get("project"))
        if not projects:
            projects = self._loads(conversation_row["projects_json"], [])
        agent_scope = self._as_list(record.get("agent_scope"))
        if not agent_scope:
            agent_scope = self._loads(conversation_row["agent_scope_json"], [])
        content = str(record.get("content") or "")
        content_hash = str(record.get("content_hash") or "").strip() or self.content_hash(content)
        external_id = self._optional(record.get("external_id"))
        sequence = int(record.get("sequence") if record.get("sequence") is not None else 0)
        existing = (
            connection.execute(
                "SELECT message_id FROM message_records WHERE conversation_id = ? AND external_id = ?",
                (conversation_id, external_id),
            ).fetchone()
            if external_id
            else None
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
        now = self._now()
        connection.execute(
            """
            INSERT INTO message_records(
                message_id, conversation_id, source_id, external_id, role, author,
                occurred_at, sequence, content, content_hash, raw_reference, privacy,
                projects_json, agent_scope_json, created_at, updated_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                created_at = COALESCE(message_records.created_at, excluded.created_at),
                updated_at = excluded.updated_at,
                metadata_json = excluded.metadata_json
            """,
            (
                message_id,
                conversation_id,
                source_id,
                external_id,
                role,
                self._optional(record.get("author")),
                self._optional(record.get("occurred_at")),
                sequence,
                content,
                content_hash,
                self._optional(record.get("raw_reference")),
                privacy,
                self._json(projects),
                self._json(agent_scope),
                str(record.get("created_at") or now),
                str(record.get("updated_at") or now),
                self._json(dict(record.get("metadata") or {})),
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
        item["metadata"] = cls._loads(item.pop("metadata_json", "{}"), {})
        return item

    @classmethod
    def _message_dict(cls, row: sqlite3.Row, *, include_content: bool) -> dict[str, Any]:
        item = dict(row)
        content = str(item.pop("content", "") or "")
        item["content_length"] = len(content)
        item["content_preview"] = " ".join(content.split())[:200]
        if include_content:
            item["content"] = content
        item["projects"] = cls._loads(item.pop("projects_json", "[]"), [])
        item["agent_scope"] = cls._loads(item.pop("agent_scope_json", "[]"), [])
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
