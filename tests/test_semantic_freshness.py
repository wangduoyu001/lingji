from __future__ import annotations

from pathlib import Path

from src.retrieval.chunker import MarkdownChunker
from src.retrieval.memory_db import MemoryDatabase
from src.retrieval.semantic_freshness import CoverageGuardedSemanticProvider


class FakeSemanticProvider:
    def __init__(self):
        self.indexed_ids: set[str] = set()
        self.search_calls = 0

    def count(self, **_kwargs):
        return len(self.indexed_ids)

    def coverage(self, expected_chunk_ids):
        expected = set(expected_chunk_ids)
        indexed = expected & self.indexed_ids
        missing = expected - self.indexed_ids
        return {
            "expected": len(expected),
            "indexed": len(indexed),
            "missing": len(missing),
        }

    def search(self, query, limit, filters=None):
        self.search_calls += 1
        return [{"memory_id": "MEM-1", "chunk_id": next(iter(self.indexed_ids), ""), "score": 0.9}]

    def status(self):
        return {"ready": True}


def _indexed_database(tmp_path: Path) -> tuple[MemoryDatabase, list[str]]:
    database = MemoryDatabase(tmp_path / "memory.db")
    vault = tmp_path / "vault"
    vault.mkdir()
    path = vault / "memory.md"
    path.write_text("# Owner Fact\n\nsemantic freshness guard evidence\n", encoding="utf-8")
    database.upsert_from_entry(
        {
            "id": "MEM-1",
            "type": "knowledge",
            "title": "Owner Fact",
            "relative_path": "memory.md",
            "privacy": "private",
            "status": "active",
            "tags": [],
            "project": [],
            "properties": {},
        },
        path,
        MarkdownChunker(max_chars=800, overlap_chars=0),
    )
    with database._connection() as connection:  # test-only inspection of derived schema
        rows = connection.execute("SELECT chunk_id FROM memory_chunks ORDER BY chunk_id").fetchall()
    return database, [str(row[0]) for row in rows]


def test_stale_semantic_provider_is_blocked_until_exact_coverage_catches_up(tmp_path: Path):
    database, chunk_ids = _indexed_database(tmp_path)
    provider = FakeSemanticProvider()
    guarded = CoverageGuardedSemanticProvider(database, provider)

    assert guarded.search("fact", 5) == []
    assert provider.search_calls == 0
    stale = guarded.freshness_status()
    assert stale["ready"] is False
    assert stale["reason"] == "point_count_mismatch"
    assert stale["expected_chunks"] == len(chunk_ids)

    provider.indexed_ids = set(chunk_ids)
    results = guarded.search("fact", 5)
    assert len(results) == 1
    assert provider.search_calls == 1
    assert guarded.freshness_status()["ready"] is True


def test_extra_orphan_vector_blocks_semantic_even_when_current_chunks_are_covered(tmp_path: Path):
    database, chunk_ids = _indexed_database(tmp_path)
    provider = FakeSemanticProvider()
    provider.indexed_ids = {*chunk_ids, "ORPHAN-OLD-CHUNK"}
    guarded = CoverageGuardedSemanticProvider(database, provider)

    assert guarded.search("fact", 5) == []
    assert provider.search_calls == 0
    status = guarded.freshness_status()
    assert status["ready"] is False
    assert status["reason"] == "point_count_mismatch"
