"""Regression tests for PERF_RESOURCE_ROOT_CAUSE_20260927 (A1).

Covers the incremental watermark sync, the rel_* generated-column identity
index, and supersede semantics across batched provenance prefetch. The sync
itself is owned by the memory gateway, so every test boots the gateway the
same way the production pipeline does.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from src.extraction.bootstrap import build_extraction_pipeline
from src.gateway.bootstrap import build_memory_gateway
from src.retrieval.memory_db import MemoryDatabase
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
