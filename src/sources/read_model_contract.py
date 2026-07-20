from __future__ import annotations

import sqlite3
from typing import Any, Mapping

from .read_model import (
    SOURCE_READ_MODEL_SCHEMA_VERSION,
    SourceReadModel as _BaseSourceReadModel,
    SourceReadModelError,
)


class SourceReadModel(_BaseSourceReadModel):
    """P2-03 read model with version validation and explicit inheritance markers.

    Conversation and message privacy/projects/agent_scope values may inherit from
    their parent. Only rows marked as inherited are synchronized when a parent
    changes; explicit child values remain untouched.
    """

    _INHERITED_COLUMNS = (
        ("privacy_inherited", "INTEGER NOT NULL DEFAULT 1"),
        ("projects_inherited", "INTEGER NOT NULL DEFAULT 1"),
        ("agent_scope_inherited", "INTEGER NOT NULL DEFAULT 1"),
    )

    def _initialize(self) -> None:
        # Validate before the base initializer can write metadata. Unknown/newer
        # versions must remain untouched rather than being silently downgraded.
        with self._lock, self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS source_read_model_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            row = connection.execute(
                "SELECT value FROM source_read_model_meta WHERE key = 'schema_version'"
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO source_read_model_meta(key, value) VALUES ('schema_version', ?)",
                    (SOURCE_READ_MODEL_SCHEMA_VERSION,),
                )
            elif str(row["value"]) != SOURCE_READ_MODEL_SCHEMA_VERSION:
                raise SourceReadModelError(
                    "Unsupported structured read model schema version: "
                    f"{row['value']}; expected {SOURCE_READ_MODEL_SCHEMA_VERSION}"
                )

        super()._initialize()
        with self._lock, self._connection() as connection:
            self._ensure_inheritance_columns(connection, "conversation_records")
            self._ensure_inheritance_columns(connection, "message_records")

    def _ensure_inheritance_columns(self, connection: sqlite3.Connection, table: str) -> None:
        existing = {
            str(row["name"])
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        for column, definition in self._INHERITED_COLUMNS:
            if column not in existing:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _upsert_source(self, connection: sqlite3.Connection, record: Mapping[str, Any]) -> str:
        source_id = super()._upsert_source(connection, record)
        self._sync_source_descendants(connection, source_id)
        return source_id

    def _upsert_conversation(
        self, connection: sqlite3.Connection, record: Mapping[str, Any]
    ) -> str:
        source_id = self._required(record.get("source_id"), "source_id")
        parent = connection.execute(
            "SELECT privacy, projects_json, agent_scope_json FROM source_records WHERE source_id = ?",
            (source_id,),
        ).fetchone()
        if parent is None:
            raise LookupError(f"source not found: {source_id}")
        existing = self._find_existing_conversation(connection, record, source_id)

        privacy, privacy_inherited = self._resolve_scalar(
            record,
            "privacy",
            str(parent["privacy"] or "private"),
            existing,
            "privacy",
            "privacy_inherited",
        )
        projects, projects_inherited = self._resolve_list(
            record,
            ("projects", "project"),
            self._loads(parent["projects_json"], []),
            existing,
            "projects_json",
            "projects_inherited",
        )
        agent_scope, agent_scope_inherited = self._resolve_list(
            record,
            ("agent_scope",),
            self._loads(parent["agent_scope_json"], []),
            existing,
            "agent_scope_json",
            "agent_scope_inherited",
        )

        conversation_id = super()._upsert_conversation(connection, record)
        connection.execute(
            """
            UPDATE conversation_records
            SET privacy = ?, privacy_inherited = ?,
                projects_json = ?, projects_inherited = ?,
                agent_scope_json = ?, agent_scope_inherited = ?
            WHERE conversation_id = ?
            """,
            (
                privacy,
                privacy_inherited,
                self._json(projects),
                projects_inherited,
                self._json(agent_scope),
                agent_scope_inherited,
                conversation_id,
            ),
        )
        self._sync_conversation_messages(connection, conversation_id)
        return conversation_id

    def _upsert_message(self, connection: sqlite3.Connection, record: Mapping[str, Any]) -> str:
        conversation_id = self._required(record.get("conversation_id"), "conversation_id")
        parent = connection.execute(
            """
            SELECT privacy, projects_json, agent_scope_json
            FROM conversation_records WHERE conversation_id = ?
            """,
            (conversation_id,),
        ).fetchone()
        if parent is None:
            raise LookupError(f"conversation not found: {conversation_id}")
        existing = self._find_existing_message(connection, record, conversation_id)

        privacy, privacy_inherited = self._resolve_scalar(
            record,
            "privacy",
            str(parent["privacy"] or "private"),
            existing,
            "privacy",
            "privacy_inherited",
        )
        projects, projects_inherited = self._resolve_list(
            record,
            ("projects", "project"),
            self._loads(parent["projects_json"], []),
            existing,
            "projects_json",
            "projects_inherited",
        )
        agent_scope, agent_scope_inherited = self._resolve_list(
            record,
            ("agent_scope",),
            self._loads(parent["agent_scope_json"], []),
            existing,
            "agent_scope_json",
            "agent_scope_inherited",
        )

        message_id = super()._upsert_message(connection, record)
        connection.execute(
            """
            UPDATE message_records
            SET privacy = ?, privacy_inherited = ?,
                projects_json = ?, projects_inherited = ?,
                agent_scope_json = ?, agent_scope_inherited = ?
            WHERE message_id = ?
            """,
            (
                privacy,
                privacy_inherited,
                self._json(projects),
                projects_inherited,
                self._json(agent_scope),
                agent_scope_inherited,
                message_id,
            ),
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
                "SELECT * FROM message_records WHERE message_id = ?",
                (message_id,),
            ).fetchone()
        return None

    def _resolve_scalar(
        self,
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

    def _resolve_list(
        self,
        record: Mapping[str, Any],
        keys: tuple[str, ...],
        parent_value: list[Any],
        existing: sqlite3.Row | None,
        value_column: str,
        inherited_column: str,
    ) -> tuple[list[Any], int]:
        for key in keys:
            if key in record:
                return self._as_list(record.get(key)), 0
        if existing is not None:
            return self._loads(existing[value_column], []), int(existing[inherited_column])
        return list(parent_value), 1
