"""Regression tests for structured evidence sync performance work.

Covers the content-addressed two-phase sync (PERF_RESOURCE_CLOSEOUT_20260927B),
the rel_* generated-column identity index from the earlier root-cause batch,
and supersede semantics across batched provenance prefetch. The sync itself
is owned by the memory gateway, so every test boots the gateway the same way
the production pipeline does.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from src.extraction.bootstrap import build_extraction_pipeline
from src.gateway.bootstrap import build_memory_gateway
from src.retrieval.memory_db import MemoryDatabase
from src.sources.read_model import SourceReadModel
from tests.test_structured_evidence_lexical import _settings

_TEST_SEQ = iter(range(1000))


def _history(path: Path, messages: list[str], *, batch: str) -> None:
    """Each batch gets its own conversation/message ids so that ingesting a
    second file models genuinely new content instead of re-parenting the same
    message row to a new source (which legitimately re-syncs that row)."""
    seq = next(_TEST_SEQ)
    path.write_text(
        json.dumps(
            {
                "schema": "lingji.history.inbox",
                "schema_version": "1",
                "conversations": [
                    {
                        "conversation_id": f"conversation-perf-{batch}-{seq}",
                        "title": "Perf regression conversation",
                        "messages": [
                            {
                                "message_id": f"message-perf-{batch}-{seq}-{index}",
                                "role": "assistant",
                                "content": content,
                                "timestamp": "2026-08-27T00:00:00Z",
                            }
                            for index, content in enumerate(messages)
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _ingest(settings, source: Path, messages: list[str], execution_id: str, batch: str) -> None:
    _history(source, messages, batch=batch)
    pipeline = build_extraction_pipeline(settings)
    pipeline.execute("generic_ai_history", input_path=source, execution_id=execution_id)
    gateway = build_memory_gateway(settings, rebuild_if_empty=False)
    gateway.close()


def test_watermark_makes_replay_a_noop(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _ingest(
        settings,
        tmp_path / "history.json",
        ["watermark noop replay 9a3f"],
        "exec-wm-0",
        "a",
    )

    db = MemoryDatabase(settings.memory_db_path)
    # The gateway already synced everything and advanced the watermark; a
    # replay with no new rows must touch zero documents.
    replay = db.sync_structured_evidence()
    assert replay["documents"] == 0
    assert replay["added"] == 0
    assert replay["updated"] == 0
    assert replay["removed"] == 0


def test_resync_dedupes_unchanged_rows(tmp_path: Path, monkeypatch) -> None:
    """A re-ingested read model must only add genuinely new evidence.

    The read model rebuilds all rows per ingestion, so every sync rescans
    them, but content addressing keeps unchanged rows from producing new
    documents: only the genuinely new message is added.
    """
    settings = _settings(tmp_path)
    calls: list[dict] = []
    original = MemoryDatabase.sync_structured_evidence

    def spy(self, **kwargs):
        result = original(self, **kwargs)
        calls.append(result)
        return result

    monkeypatch.setattr(MemoryDatabase, "sync_structured_evidence", spy)

    _ingest(
        settings,
        tmp_path / "history-1.json",
        ["watermark first batch alpha 41c2", "watermark first batch beta 42c3"],
        "exec-wm-1",
        "a",
    )
    assert calls[-1]["added"] == 2

    _ingest(
        settings,
        tmp_path / "history-2.json",
        ["watermark second batch gamma 77d9"],
        "exec-wm-2",
        "b",
    )
    assert calls[-1]["added"] == 1

    with sqlite3.connect(settings.memory_db_path) as conn:
        active = conn.execute(
            "SELECT COUNT(*) FROM memory_documents WHERE memory_type = 'structured_evidence' AND status = 'active'"
        ).fetchone()[0]
    assert active == 3


def test_identity_index_serves_provenance_lookup(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _ingest(
        settings,
        tmp_path / "history.json",
        ["identity index plan probe 5b7e"],
        "exec-idx",
        "a",
    )

    with sqlite3.connect(settings.memory_db_path) as conn:
        # Generated columns are hidden from table_info; table_xinfo sees them.
        columns = {row[1] for row in conn.execute("PRAGMA table_xinfo(memory_documents)")}
        assert {"rel_source_id", "rel_conversation_id", "rel_message_id"} <= columns
        plan = " ".join(
            str(row[-1])
            for row in conn.execute(
                """
                EXPLAIN QUERY PLAN
                SELECT memory_id FROM memory_documents
                WHERE memory_type = 'structured_evidence'
                  AND rel_source_id = 's'
                  AND rel_conversation_id = 'c'
                  AND rel_message_id = 'm'
                """
            ).fetchall()
        )
    assert "idx_memory_documents_identity" in plan


def test_identity_removal_archives_prior_active_row(tmp_path: Path) -> None:
    """A message row that leaves the read model must archive its projection."""
    settings = _settings(tmp_path)
    _ingest(
        settings,
        tmp_path / "history.json",
        ["archive semantics original a1d4"],
        "exec-arch-1",
        "a",
    )

    db = MemoryDatabase(settings.memory_db_path)
    with sqlite3.connect(settings.memory_db_path) as conn:
        message_id = conn.execute(
            "SELECT message_id FROM message_records LIMIT 1"
        ).fetchone()[0]
        # Simulate the read model removing the message identity.
        conn.execute("DELETE FROM message_records WHERE message_id = ?", (message_id,))
        conn.commit()

    result = db.sync_structured_evidence()
    assert result["removed"] == 1

    with sqlite3.connect(settings.memory_db_path) as conn:
        active = conn.execute(
            "SELECT COUNT(*) FROM memory_documents WHERE memory_type = 'structured_evidence' AND status = 'active'"
        ).fetchone()[0]
        archived = conn.execute(
            "SELECT COUNT(*) FROM memory_documents WHERE memory_type = 'structured_evidence' AND status = 'archived'"
        ).fetchone()[0]
    assert active == 0
    assert archived == 1


def test_content_addressed_replay_skips_chunking(tmp_path: Path) -> None:
    """A second sync over unchanged rows must not read content or chunk.

    PERF_RESOURCE_CLOSEOUT_20260927B: content addressing replaces the
    watermark. The chunker stub proves phase two never runs for identical
    rows, so a full read-model rewrite no longer re-chunks the corpus.
    """
    settings = _settings(tmp_path)
    _ingest(
        settings,
        tmp_path / "history.json",
        ["content addressed replay 3d5f"],
        "exec-ca-0",
        "a",
    )

    db = MemoryDatabase(settings.memory_db_path)
    chunk_calls: list[tuple] = []

    class CountingChunker:
        def chunk(self, *args, **kwargs):
            chunk_calls.append(args)
            return []

    replay = db.sync_structured_evidence(chunker=CountingChunker())
    assert chunk_calls == []
    assert replay["added"] == 0
    assert replay["updated"] == 0
    assert replay["removed"] == 0
    assert replay["documents"] == 0
    assert replay["unchanged"] == 1
    assert replay["full_rebuild"] is False


def test_conversation_title_drift_propagates_to_projection(tmp_path: Path) -> None:
    """Retitling a conversation must repair the projection document in place.

    This is the defect the watermark sync never fixed: the projection title
    was frozen at first materialization. The fix rewrites title on the same
    memory_id without producing a new version.
    """
    settings = _settings(tmp_path)
    _ingest(
        settings,
        tmp_path / "history.json",
        ["title drift evidence 7c2a"],
        "exec-title-0",
        "a",
    )

    db = MemoryDatabase(settings.memory_db_path)
    memory_id_before = next(
        item["memory_id"]
        for item in db.list_documents()
        if item["memory_type"] == "structured_evidence"
    )
    with sqlite3.connect(settings.memory_db_path) as conn:
        conn.execute("UPDATE conversation_records SET title = 'Renamed conversation title'")
        conn.commit()

    before = db.revision
    result = db.sync_structured_evidence()
    assert result["updated"] == 1
    assert result["added"] == 0

    docs = [item for item in db.list_documents() if item["memory_type"] == "structured_evidence"]
    assert len(docs) == 1
    doc = docs[0]
    assert doc["title"] == "Renamed conversation title"
    assert doc["status"] == "active"
    assert doc["memory_id"] == memory_id_before
    with sqlite3.connect(settings.memory_db_path) as conn:
        superseded = conn.execute(
            "SELECT COUNT(*) FROM memory_documents WHERE memory_type = 'structured_evidence' AND status = 'superseded'"
        ).fetchone()[0]
        version_count = conn.execute(
            "SELECT COUNT(*) FROM memory_documents WHERE memory_type = 'structured_evidence'"
        ).fetchone()[0]
    assert superseded == 0
    assert version_count == 1
    assert db.revision > before


def test_incremental_matches_full_rebuild_projection(tmp_path: Path) -> None:
    """The incrementally evolved projection must equal a full rebuild.

    Superseded version rows exist only in the incrementally evolved database
    because the read model keeps just the latest row per message; the
    comparison therefore covers the current projection (non-superseded
    documents plus the chunks belonging to them) and separately pins the
    superseded history count.
    """
    settings = _settings(tmp_path)
    _ingest(
        settings,
        tmp_path / "history-1.json",
        ["equivalence batch one alpha 11aa", "equivalence batch one beta 22bb"],
        "exec-eq-1",
        "a",
    )
    _ingest(
        settings,
        tmp_path / "history-2.json",
        ["equivalence batch two gamma 33cc"],
        "exec-eq-2",
        "b",
    )

    db = MemoryDatabase(settings.memory_db_path)
    revised = "equivalence batch one alpha revised 44dd"
    with sqlite3.connect(settings.memory_db_path) as conn:
        message_id = conn.execute(
            "SELECT message_id FROM message_records WHERE content LIKE '%alpha%'"
        ).fetchone()[0]
        # Content update: the read model keeps only the latest row, so the
        # next sync must supersede the old projection version.
        conn.execute(
            "UPDATE message_records SET content = ?, content_hash = ? WHERE message_id = ?",
            (revised, hashlib.sha256(revised.encode("utf-8")).hexdigest(), message_id),
        )
        # Revoke the source owning the updated conversation.
        conn.execute(
            "UPDATE source_records SET status = 'revoked' "
            "WHERE source_id = (SELECT source_id FROM message_records WHERE message_id = ?)",
            (message_id,),
        )
        conn.commit()

    drift = db.sync_structured_evidence()
    assert drift["added"] == 1
    assert drift["updated"] == 2
    assert drift["removed"] == 0

    steady = db.sync_structured_evidence()
    assert steady["documents"] == 0
    assert steady["unchanged"] == 3
    assert steady["removed"] == 0

    other_path = tmp_path / "rebuild" / "lingji_memory.db"
    other_db = MemoryDatabase(other_path)
    SourceReadModel(other_db)
    for table in ("source_records", "conversation_records", "message_records"):
        with sqlite3.connect(settings.memory_db_path) as source_conn:
            source_conn.row_factory = sqlite3.Row
            rows = source_conn.execute(f"SELECT * FROM {table}").fetchall()
            columns = rows[0].keys() if rows else []
        if not rows:
            continue
        with sqlite3.connect(other_path) as target_conn:
            target_conn.execute("PRAGMA foreign_keys = OFF")
            placeholders = ",".join("?" for _ in columns)
            target_conn.executemany(
                f"INSERT OR REPLACE INTO {table} ({','.join(columns)}) VALUES ({placeholders})",
                [tuple(row) for row in rows],
            )
            target_conn.commit()

    rebuilt = other_db.rebuild_structured_evidence()
    assert rebuilt["full_rebuild"] is False
    assert rebuilt["added"] == 3

    def snapshot(database: MemoryDatabase) -> tuple[set[tuple], set[tuple]]:
        docs = {
            (item["memory_id"], item["status"], item["title"], item["content_hash"])
            for item in database.list_documents()
            if item["memory_type"] == "structured_evidence" and item["status"] != "superseded"
        }
        doc_ids = {item[0] for item in docs}
        with sqlite3.connect(database.path) as conn:
            chunks = {
                (str(row[0]), int(row[1]), str(row[2]))
                for row in conn.execute(
                    """
                    SELECT c.memory_id, c.ordinal, c.text
                    FROM memory_chunks c
                    JOIN memory_documents d ON d.memory_id = c.memory_id
                    WHERE d.memory_type = 'structured_evidence'
                    """
                )
                if str(row[0]) in doc_ids
            }
        return docs, chunks

    incremental_docs, incremental_chunks = snapshot(db)
    rebuild_docs, rebuild_chunks = snapshot(other_db)
    assert {status for _mid, status, _title, _hash in incremental_docs} <= {"active", "archived"}
    assert incremental_docs == rebuild_docs
    assert incremental_chunks == rebuild_chunks

    with sqlite3.connect(settings.memory_db_path) as conn:
        superseded_incremental = conn.execute(
            "SELECT COUNT(*) FROM memory_documents "
            "WHERE memory_type = 'structured_evidence' AND status = 'superseded'"
        ).fetchone()[0]
    with sqlite3.connect(other_path) as conn:
        superseded_rebuild = conn.execute(
            "SELECT COUNT(*) FROM memory_documents "
            "WHERE memory_type = 'structured_evidence' AND status = 'superseded'"
        ).fetchone()[0]
    assert superseded_incremental == 1
    assert superseded_rebuild == 0


def test_content_cleared_message_archives_projection(tmp_path: Path) -> None:
    """Emptying a message's content must archive its stale projection.

    The empty content hash marks the row as content-less without reading the
    content column; the old projection is archived with an explicit
    invalidating reason and never resurrected by later syncs.
    """
    settings = _settings(tmp_path)
    _ingest(
        settings,
        tmp_path / "history.json",
        ["cleared content evidence 9b1c"],
        "exec-clear-1",
        "a",
    )

    db = MemoryDatabase(settings.memory_db_path)
    empty_hash = hashlib.sha256(b"").hexdigest()
    with sqlite3.connect(settings.memory_db_path) as conn:
        conn.execute(
            "UPDATE message_records SET content = '', content_hash = ?",
            (empty_hash,),
        )
        conn.commit()

    result = db.sync_structured_evidence()
    assert result["removed"] == 1
    assert result["documents"] == 0

    docs = [item for item in db.list_documents() if item["memory_type"] == "structured_evidence"]
    assert len(docs) == 1
    assert docs[0]["status"] == "archived"
    assert docs[0]["relationships"]["invalidating_reason"] == "structured_evidence_content_cleared"

    replay = db.sync_structured_evidence()
    assert replay["removed"] == 0
    assert replay["documents"] == 0
