from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from .models import DramaChunk, DramaParseResult

_SCHEMA_VERSION = 2


class DramaRepository:
    """Rebuildable Drama structured read model and lexical index for one workspace."""

    def __init__(self, database_path: Path | str):
        self.database_path = Path(database_path).expanduser().resolve(strict=False)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @property
    def revision(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM drama_meta WHERE key = 'revision'"
            ).fetchone()
        return int(row[0]) if row else 0

    def save(
        self,
        result: DramaParseResult,
        *,
        raw_path: Path,
        normalized_path: Path,
        force: bool = False,
    ) -> dict[str, Any]:
        existing = self.find_by_sha256(result.source.sha256)
        if existing and not force:
            return {**existing, "duplicate": True}
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if existing:
                drama_id = str(existing["drama_id"])
                self._delete_children(connection, drama_id)
            else:
                drama_id = result.drama_id
            connection.execute(
                """
                INSERT INTO dramas (
                    drama_id, title, source_path, raw_path, normalized_path, source_format,
                    source_sha256, status, character_count, episode_count, scene_count,
                    chunk_count, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'ready', ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(drama_id) DO UPDATE SET
                    title=excluded.title,
                    source_path=excluded.source_path,
                    raw_path=excluded.raw_path,
                    normalized_path=excluded.normalized_path,
                    source_format=excluded.source_format,
                    source_sha256=excluded.source_sha256,
                    status='ready',
                    character_count=excluded.character_count,
                    episode_count=excluded.episode_count,
                    scene_count=excluded.scene_count,
                    chunk_count=excluded.chunk_count,
                    metadata_json=excluded.metadata_json,
                    updated_at=excluded.updated_at
                """,
                (
                    drama_id,
                    result.title,
                    str(result.source.source_path),
                    str(raw_path),
                    str(normalized_path),
                    result.source.source_format,
                    result.source.sha256,
                    len(result.characters),
                    len(result.episodes),
                    len(result.scenes),
                    len(result.chunks),
                    json.dumps(result.metadata, ensure_ascii=False, sort_keys=True),
                    now,
                    now,
                ),
            )
            connection.executemany(
                """
                INSERT INTO episodes (
                    episode_id, drama_id, number, title, start_offset, end_offset, text
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        item.episode_id.replace(result.drama_id, drama_id, 1),
                        drama_id,
                        item.number,
                        item.title,
                        item.start_offset,
                        item.end_offset,
                        item.text,
                    )
                    for item in result.episodes
                ],
            )
            connection.executemany(
                """
                INSERT INTO scenes (
                    scene_id, drama_id, episode_number, scene_number, heading,
                    start_offset, end_offset, characters_json, text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        item.scene_id.replace(result.drama_id, drama_id, 1),
                        drama_id,
                        item.episode_number,
                        item.scene_number,
                        item.heading,
                        item.start_offset,
                        item.end_offset,
                        json.dumps(list(item.characters), ensure_ascii=False),
                        item.text,
                    )
                    for item in result.scenes
                ],
            )
            connection.executemany(
                """
                INSERT INTO characters (drama_id, name, mention_count, first_episode)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (drama_id, item.name, item.mention_count, item.first_episode)
                    for item in result.characters
                ],
            )
            chunks = [
                DramaChunk(
                    chunk_id=item.chunk_id,
                    drama_id=drama_id,
                    chunk_type=item.chunk_type,
                    text=item.text,
                    source_ref=item.source_ref.replace(result.drama_id, drama_id, 1),
                    start_offset=item.start_offset,
                    end_offset=item.end_offset,
                    episode_number=item.episode_number,
                    scene_number=item.scene_number,
                    heading=item.heading,
                    characters=item.characters,
                    tags=item.tags,
                    source_locator=item.source_locator,
                )
                for item in result.chunks
            ]
            self._insert_chunks(connection, chunks)
            self._increment_revision(connection)
        return {**self.get_drama(drama_id), "duplicate": False}

    def list_dramas(self, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        bounded = min(max(int(limit), 1), 500)
        start = max(int(offset), 0)
        with self._connect() as connection:
            total = int(connection.execute("SELECT COUNT(*) FROM dramas").fetchone()[0])
            rows = connection.execute(
                """
                SELECT drama_id, title, source_format, status, character_count,
                       episode_count, scene_count, chunk_count, updated_at
                FROM dramas ORDER BY updated_at DESC LIMIT ? OFFSET ?
                """,
                (bounded, start),
            ).fetchall()
        return {
            "items": [dict(row) for row in rows],
            "total": total,
            "limit": bounded,
            "offset": start,
            "revision": self.revision,
        }

    def get_drama(self, drama_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM dramas WHERE drama_id = ?", (drama_id,)
            ).fetchone()
            if row is None:
                raise LookupError(f"Drama not found: {drama_id}")
            episodes = connection.execute(
                """
                SELECT episode_id, number, title, start_offset, end_offset
                FROM episodes WHERE drama_id = ? ORDER BY number, episode_id
                """,
                (drama_id,),
            ).fetchall()
            characters = connection.execute(
                """
                SELECT name, mention_count, first_episode
                FROM characters WHERE drama_id = ? ORDER BY mention_count DESC, name
                """,
                (drama_id,),
            ).fetchall()
        payload = dict(row)
        payload["metadata"] = json.loads(str(payload.pop("metadata_json") or "{}"))
        payload["episodes"] = [dict(item) for item in episodes]
        payload["characters"] = [dict(item) for item in characters]
        payload["revision"] = self.revision
        return payload

    def find_by_sha256(self, source_sha256: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT drama_id FROM dramas WHERE source_sha256 = ?", (source_sha256,)
            ).fetchone()
        return self.get_drama(str(row["drama_id"])) if row else None

    def search_lexical(
        self,
        query: str,
        *,
        limit: int = 20,
        drama_id: str | None = None,
        chunk_type: str | None = None,
    ) -> list[dict[str, Any]]:
        clean = " ".join(str(query or "").split())
        if not clean:
            return []
        bounded = min(max(int(limit), 1), 100)
        candidate_limit = min(max(bounded * 8, 80), 600)
        terms = self._query_terms(clean)
        results: dict[str, dict[str, Any]] = {}

        with self._connect() as connection:
            if self._fts_available(connection) and terms:
                fts_query = " OR ".join(f'"{item.replace(chr(34), "")}"' for item in terms[:32])
                sql = """
                    SELECT c.*, bm25(chunks_fts) AS rank
                    FROM chunks_fts
                    JOIN chunks c ON c.chunk_id = chunks_fts.chunk_id
                    WHERE chunks_fts MATCH ?
                """
                args: list[Any] = [fts_query]
                sql, args = self._apply_filters(sql, args, drama_id, chunk_type)
                sql += " ORDER BY rank LIMIT ?"
                args.append(candidate_limit)
                try:
                    for row in connection.execute(sql, args).fetchall():
                        item = self._chunk_payload(row)
                        item["lexical_score"] = self._lexical_score(clean, terms, item)
                        results[item["chunk_id"]] = item
                except sqlite3.OperationalError:
                    pass

            fallback_terms = terms[:32] or [clean]
            conditions: list[str] = []
            args = []
            for term in fallback_terms:
                conditions.append(
                    "(instr(lower(c.text), lower(?)) > 0 OR "
                    "instr(lower(c.heading), lower(?)) > 0 OR "
                    "instr(lower(c.characters_json), lower(?)) > 0 OR "
                    "instr(lower(c.tags_json), lower(?)) > 0)"
                )
                args.extend([term, term, term, term])
            sql = "SELECT c.*, 0.0 AS rank FROM chunks c WHERE (" + " OR ".join(conditions) + ")"
            sql, args = self._apply_filters(sql, args, drama_id, chunk_type, has_where=True)
            sql += " ORDER BY length(c.text) ASC LIMIT ?"
            args.append(candidate_limit)
            for row in connection.execute(sql, args).fetchall():
                item = self._chunk_payload(row)
                item["lexical_score"] = self._lexical_score(clean, terms, item)
                previous = results.get(item["chunk_id"])
                if previous is None or float(item["lexical_score"]) > float(previous.get("lexical_score") or 0.0):
                    results[item["chunk_id"]] = item

        return sorted(
            results.values(),
            key=lambda item: (
                float(item.get("lexical_score") or 0.0),
                -len(str(item.get("text") or "")),
            ),
            reverse=True,
        )[:bounded]

    def chunks(self, drama_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM chunks WHERE drama_id = ? ORDER BY episode_number, scene_number, start_offset",
                (drama_id,),
            ).fetchall()
        return [self._chunk_payload(row) for row in rows]

    def chunks_by_ids(self, chunk_ids: Sequence[str]) -> dict[str, dict[str, Any]]:
        selected = list(dict.fromkeys(str(value) for value in chunk_ids if str(value)))
        if not selected:
            return {}
        output: dict[str, dict[str, Any]] = {}
        with self._connect() as connection:
            for start in range(0, len(selected), 300):
                batch = selected[start : start + 300]
                placeholders = ",".join("?" for _ in batch)
                rows = connection.execute(
                    f"SELECT * FROM chunks WHERE chunk_id IN ({placeholders})", batch
                ).fetchall()
                for row in rows:
                    payload = self._chunk_payload(row)
                    output[str(payload["chunk_id"])] = payload
        return output

    def status(self) -> dict[str, Any]:
        with self._connect() as connection:
            counts = {
                "dramas": int(connection.execute("SELECT COUNT(*) FROM dramas").fetchone()[0]),
                "episodes": int(connection.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]),
                "scenes": int(connection.execute("SELECT COUNT(*) FROM scenes").fetchone()[0]),
                "characters": int(connection.execute("SELECT COUNT(*) FROM characters").fetchone()[0]),
                "chunks": int(connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]),
            }
            fts = self._fts_available(connection)
        return {
            "state": "ready",
            "schema_version": _SCHEMA_VERSION,
            "revision": self.revision,
            "database_path": str(self.database_path),
            "database_bytes": self.database_path.stat().st_size if self.database_path.exists() else 0,
            "fts_available": fts,
            **counts,
        }

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA foreign_keys=ON;
                CREATE TABLE IF NOT EXISTS drama_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                INSERT OR IGNORE INTO drama_meta(key, value) VALUES ('revision', '0');
                CREATE TABLE IF NOT EXISTS dramas (
                    drama_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    raw_path TEXT NOT NULL,
                    normalized_path TEXT NOT NULL,
                    source_format TEXT NOT NULL,
                    source_sha256 TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    character_count INTEGER NOT NULL DEFAULT 0,
                    episode_count INTEGER NOT NULL DEFAULT 0,
                    scene_count INTEGER NOT NULL DEFAULT 0,
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS episodes (
                    episode_id TEXT PRIMARY KEY,
                    drama_id TEXT NOT NULL REFERENCES dramas(drama_id) ON DELETE CASCADE,
                    number INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    start_offset INTEGER NOT NULL,
                    end_offset INTEGER NOT NULL,
                    text TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_episodes_drama_number ON episodes(drama_id, number);
                CREATE TABLE IF NOT EXISTS scenes (
                    scene_id TEXT PRIMARY KEY,
                    drama_id TEXT NOT NULL REFERENCES dramas(drama_id) ON DELETE CASCADE,
                    episode_number INTEGER NOT NULL,
                    scene_number INTEGER NOT NULL,
                    heading TEXT NOT NULL,
                    start_offset INTEGER NOT NULL,
                    end_offset INTEGER NOT NULL,
                    characters_json TEXT NOT NULL DEFAULT '[]',
                    text TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_scenes_drama_episode ON scenes(drama_id, episode_number, scene_number);
                CREATE TABLE IF NOT EXISTS characters (
                    drama_id TEXT NOT NULL REFERENCES dramas(drama_id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    mention_count INTEGER NOT NULL,
                    first_episode INTEGER,
                    PRIMARY KEY (drama_id, name)
                );
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    drama_id TEXT NOT NULL REFERENCES dramas(drama_id) ON DELETE CASCADE,
                    chunk_type TEXT NOT NULL,
                    heading TEXT NOT NULL DEFAULT '',
                    text TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    source_locator_json TEXT NOT NULL DEFAULT '{}',
                    start_offset INTEGER NOT NULL,
                    end_offset INTEGER NOT NULL,
                    episode_number INTEGER,
                    scene_number INTEGER,
                    characters_json TEXT NOT NULL DEFAULT '[]',
                    tags_json TEXT NOT NULL DEFAULT '[]'
                );
                CREATE INDEX IF NOT EXISTS idx_chunks_drama_type ON chunks(drama_id, chunk_type);
                """
            )
            self._migrate_chunks(connection)
            self._ensure_fts(connection)

    def _migrate_chunks(self, connection: sqlite3.Connection) -> None:
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(chunks)").fetchall()
        }
        if "heading" not in columns:
            connection.execute("ALTER TABLE chunks ADD COLUMN heading TEXT NOT NULL DEFAULT ''")
        if "source_locator_json" not in columns:
            connection.execute(
                "ALTER TABLE chunks ADD COLUMN source_locator_json TEXT NOT NULL DEFAULT '{}'"
            )

    def _ensure_fts(self, connection: sqlite3.Connection) -> None:
        try:
            columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(chunks_fts)").fetchall()
            }
            if columns and "heading" not in columns:
                connection.execute("DROP TABLE chunks_fts")
            connection.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    chunk_id UNINDEXED, text, heading, characters, tags, tokenize='unicode61'
                )
                """
            )
            count = int(connection.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0])
            chunk_count = int(connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
            if count != chunk_count:
                connection.execute("DELETE FROM chunks_fts")
                connection.execute(
                    """
                    INSERT INTO chunks_fts(chunk_id, text, heading, characters, tags)
                    SELECT chunk_id, text, heading, characters_json, tags_json FROM chunks
                    """
                )
        except sqlite3.OperationalError:
            return

    def _insert_chunks(self, connection: sqlite3.Connection, chunks: Iterable[DramaChunk]) -> None:
        selected = list(chunks)
        connection.executemany(
            """
            INSERT INTO chunks (
                chunk_id, drama_id, chunk_type, heading, text, source_ref,
                source_locator_json, start_offset, end_offset, episode_number,
                scene_number, characters_json, tags_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.chunk_id,
                    item.drama_id,
                    item.chunk_type,
                    item.heading,
                    item.text,
                    item.source_ref,
                    json.dumps(item.source_locator, ensure_ascii=False, sort_keys=True),
                    item.start_offset,
                    item.end_offset,
                    item.episode_number,
                    item.scene_number,
                    json.dumps(list(item.characters), ensure_ascii=False),
                    json.dumps(list(item.tags), ensure_ascii=False),
                )
                for item in selected
            ],
        )
        if self._fts_available(connection):
            connection.executemany(
                "INSERT INTO chunks_fts (chunk_id, text, heading, characters, tags) VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        item.chunk_id,
                        item.text,
                        item.heading,
                        " ".join(item.characters),
                        " ".join(item.tags),
                    )
                    for item in selected
                ],
            )

    def _delete_children(self, connection: sqlite3.Connection, drama_id: str) -> None:
        chunk_ids = [
            str(row[0])
            for row in connection.execute(
                "SELECT chunk_id FROM chunks WHERE drama_id = ?", (drama_id,)
            ).fetchall()
        ]
        if chunk_ids and self._fts_available(connection):
            connection.executemany(
                "DELETE FROM chunks_fts WHERE chunk_id = ?", [(value,) for value in chunk_ids]
            )
        for table in ("chunks", "characters", "scenes", "episodes"):
            connection.execute(f"DELETE FROM {table} WHERE drama_id = ?", (drama_id,))

    @staticmethod
    def _apply_filters(
        sql: str,
        args: list[Any],
        drama_id: str | None,
        chunk_type: str | None,
        *,
        has_where: bool = True,
    ) -> tuple[str, list[Any]]:
        joiner = " AND " if has_where else " WHERE "
        if drama_id:
            sql += f"{joiner} c.drama_id = ?"
            args.append(drama_id)
            joiner = " AND "
        if chunk_type:
            sql += f"{joiner} c.chunk_type = ?"
            args.append(chunk_type)
        return sql, args

    @staticmethod
    def _chunk_payload(row: sqlite3.Row) -> dict[str, Any]:
        payload = dict(row)
        payload.pop("rank", None)
        payload["characters"] = json.loads(str(payload.pop("characters_json") or "[]"))
        payload["tags"] = json.loads(str(payload.pop("tags_json") or "[]"))
        payload["source_locator"] = json.loads(
            str(payload.pop("source_locator_json", "{}") or "{}")
        )
        return payload

    @staticmethod
    def _fts_available(connection: sqlite3.Connection) -> bool:
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='chunks_fts'"
        ).fetchone()
        return row is not None

    @staticmethod
    def _query_terms(query: str) -> list[str]:
        values: list[str] = []
        for token in re.findall(r"[A-Za-z0-9_]{2,}|[\u4e00-\u9fff]{2,}", query.lower()):
            if token not in values:
                values.append(token)
            if re.fullmatch(r"[\u4e00-\u9fff]+", token) and len(token) > 4:
                for size in (3, 4, 2):
                    for index in range(0, len(token) - size + 1):
                        value = token[index : index + size]
                        if value not in values:
                            values.append(value)
                        if len(values) >= 32:
                            return values
        return values[:32]

    @staticmethod
    def _lexical_score(query: str, terms: Sequence[str], item: dict[str, Any]) -> float:
        text = " ".join(
            [
                str(item.get("heading") or ""),
                str(item.get("text") or ""),
                " ".join(str(value) for value in item.get("characters") or []),
                " ".join(str(value) for value in item.get("tags") or []),
            ]
        ).lower()
        score = 1.0 if query.lower() in text else 0.0
        total_weight = sum(max(len(term), 1) for term in terms) or 1
        matched_weight = sum(len(term) for term in terms if term in text)
        score += matched_weight / total_weight
        if str(item.get("heading") or "").lower() in query.lower():
            score += 0.1
        return round(min(score, 2.0), 6)

    @staticmethod
    def _increment_revision(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            INSERT INTO drama_meta(key, value) VALUES ('revision', '1')
            ON CONFLICT(key) DO UPDATE SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT)
            """
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection
