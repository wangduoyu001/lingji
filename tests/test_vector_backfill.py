"""Full-auto vector backfill: messages -> local qdrant collection (Task: 向量化全自动)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.storage import StateDatabase

try:
    from src.retrieval.vector_backfill import VectorBackfill
except ModuleNotFoundError:
    VectorBackfill = None  # type: ignore[assignment]


class FakeProvider:
    """确定性 4 维向量：内容 hash → 稳定向量，无需真实模型。"""

    provider_id = "fake"

    def __init__(self):
        self.calls = 0

    def status(self):
        return {"available": True, "active_model": "fake-embed", "dimension": 4}

    def embed_many(self, texts):
        self.calls += len(texts)
        out = []
        for t in texts:
            seed = abs(hash(t)) % 997
            out.append([((seed >> i) & 1) * 0.5 + 0.25 for i in range(4)])
        return out

    def close(self):
        pass


def _fixture(tmp_path: Path, n: int = 3):
    db = StateDatabase(tmp_path / "lingji_state.db")
    mem = tmp_path / "lingji_memory.db"
    conn = sqlite3.connect(mem)
    conn.execute("CREATE TABLE message_records (message_id TEXT PRIMARY KEY, conversation_id TEXT, role TEXT, content TEXT, occurred_at TEXT, content_hash TEXT)")
    for i in range(n):
        conn.execute(
            "INSERT INTO message_records VALUES (?,?,?,?,?,?)",
            (f"m-{i}", "conv-1", "user" if i % 2 == 0 else "assistant", f"内容 {i}", f"2026-09-0{i+1}T00:00:00Z", f"hash-{i}"),
        )
    conn.commit()
    conn.close()
    settings = SimpleNamespace(
        storage_path=tmp_path,
        memory_db_path=mem,
        embedding_provider="ollama",
        ollama_base_url="http://127.0.0.1:11434",
        embed_model="fake-primary",
        fallback_embed_model="fake-fallback",
        embedding_batch_size=8,
    )
    return db, settings


def test_backfill_embeds_all_messages_once_and_is_idempotent(tmp_path: Path):
    if VectorBackfill is None:
        pytest.fail("vector backfill production module is absent")
    import sqlite3
    from types import SimpleNamespace

    state = StateDatabase(tmp_path / "lingji_state.db")
    mem = tmp_path / "lingji_memory.db"
    conn = sqlite3.connect(mem)
    conn.execute("CREATE TABLE message_records (message_id TEXT PRIMARY KEY, conversation_id TEXT, role TEXT, content TEXT, occurred_at TEXT, content_hash TEXT)")
    for i in range(3):
        conn.execute("INSERT INTO message_records VALUES (?,?,?,?,?,?)", (f"m-{i}", "conv-1", "user" if i % 2 == 0 else "assistant", f"内容 {i}", f"2026-09-0{i+1}T00:00:00Z", f"hash-{i}"))
    conn.commit(); conn.close()
    settings = SimpleNamespace(storage_path=tmp_path, memory_db_path=mem,
        embedding_provider="ollama", ollama_base_url="http://127.0.0.1:11434",
        embed_model="fake-primary", fallback_embed_model="fake-fallback", embedding_batch_size=8)
    provider = FakeProvider()
    backfill = VectorBackfill(settings, provider=provider)
    result = backfill.run_once(limit=100)
    assert result["embedded"] == 3
    again = backfill.run_once(limit=100)
    assert again["embedded"] == 0, "second pass must skip already-vectorized messages"
