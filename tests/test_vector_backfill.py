"""Full-auto vector backfill: messages -> local qdrant collection (Task: 向量化全自动)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.storage import StateDatabase

try:
    from src.retrieval.vector_backfill import VectorBackfill, close_shared_client
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
            # 稳定字节和种子：跨进程确定（hash() 有进程盐），且不同内容几乎不碰撞。
            seed = sum(t.encode("utf-8")) % 997
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
    close_shared_client()
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


def test_backfill_payload_carries_content_for_recall(tmp_path: Path):
    """向量 payload 必须带 content/conversation_id，否则语义召回搜到也显示不出。"""
    from types import SimpleNamespace

    from qdrant_client import QdrantClient

    state = StateDatabase(tmp_path / "lingji_state.db")
    mem = tmp_path / "lingji_memory.db"
    conn = sqlite3.connect(mem)
    conn.execute("CREATE TABLE message_records (message_id TEXT PRIMARY KEY, conversation_id TEXT, role TEXT, content TEXT, occurred_at TEXT, content_hash TEXT)")
    conn.execute("INSERT INTO message_records VALUES ('m-0', 'conv-1', 'user', 'Gmail 晨间简报内容', '2026-09-01T00:00:00Z', 'h0')")
    conn.commit(); conn.close()
    settings = SimpleNamespace(storage_path=tmp_path, memory_db_path=mem,
        embedding_provider="ollama", ollama_base_url="http://127.0.0.1:11434",
        embed_model="fake-primary", fallback_embed_model="fake-fallback", embedding_batch_size=8)
    backfill = VectorBackfill(settings, provider=FakeProvider())
    backfill.run_once(limit=10)
    close_shared_client()
    client = QdrantClient(path=str(tmp_path / "qdrant"))
    points, _ = client.scroll(collection_name="lingji_automatic_memory", limit=10, with_payload=True)
    client.close()
    payload = points[0].payload or {}
    assert payload.get("content") == "Gmail 晨间简报内容"
    assert payload.get("conversation_id") == "conv-1"
    assert payload.get("occurred_at") == "2026-09-01T00:00:00Z"


def test_legacy_points_without_content_are_self_healed(tmp_path: Path):
    """旧格式向量（payload 缺 content）视为待修复：自动重写而不是跳过。"""
    from types import SimpleNamespace

    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, VectorParams

    state = StateDatabase(tmp_path / "lingji_state.db")
    mem = tmp_path / "lingji_memory.db"
    conn = sqlite3.connect(mem)
    conn.execute("CREATE TABLE message_records (message_id TEXT PRIMARY KEY, conversation_id TEXT, role TEXT, content TEXT, occurred_at TEXT, content_hash TEXT)")
    conn.execute("INSERT INTO message_records VALUES ('m-0', 'conv-1', 'user', '内容 0', '2026-09-01T00:00:00Z', 'h0')")
    conn.commit(); conn.close()
    settings = SimpleNamespace(storage_path=tmp_path, memory_db_path=mem,
        embedding_provider="ollama", ollama_base_url="http://127.0.0.1:11434",
        embed_model="fake-primary", fallback_embed_model="fake-fallback", embedding_batch_size=8)
    # 预置一个旧格式点（payload 只有 message_id/role）
    close_shared_client()
    client = QdrantClient(path=str(tmp_path / "qdrant"))
    client.create_collection(collection_name="lingji_automatic_memory", vectors_config=VectorParams(size=4, distance="Cosine"))
    from src.retrieval.vector_backfill import _point_id
    client.upsert(collection_name="lingji_automatic_memory", points=[PointStruct(id=_point_id("m-0"), vector=[0.25, 0.25, 0.75, 0.25], payload={"message_id": "m-0", "role": "user"})])
    client.close()
    backfill = VectorBackfill(settings, provider=FakeProvider())
    result = backfill.run_once(limit=10)
    assert result["embedded"] == 1, "legacy point without content must be re-upserted"
    close_shared_client()
    client = QdrantClient(path=str(tmp_path / "qdrant"))
    points, _ = client.scroll(collection_name="lingji_automatic_memory", limit=10, with_payload=True)
    client.close()
    assert (points[0].payload or {}).get("content") == "内容 0"
    close_shared_client()


def test_search_returns_displayable_recall_results(tmp_path: Path):
    """search() 走 query_points 并返回 content/conversation_id（回归旧 search() 移除故障）。"""
    from types import SimpleNamespace

    state = StateDatabase(tmp_path / "lingji_state.db")
    mem = tmp_path / "lingji_memory.db"
    conn = sqlite3.connect(mem)
    conn.execute("CREATE TABLE message_records (message_id TEXT PRIMARY KEY, conversation_id TEXT, role TEXT, content TEXT, occurred_at TEXT, content_hash TEXT)")
    conn.execute("INSERT INTO message_records VALUES ('m-0', 'conv-1', 'user', '晨间简报内容', '2026-09-01T00:00:00Z', 'h0')")
    conn.commit(); conn.close()
    settings = SimpleNamespace(storage_path=tmp_path, memory_db_path=mem,
        embedding_provider="ollama", ollama_base_url="http://127.0.0.1:11434",
        embed_model="fake-primary", fallback_embed_model="fake-fallback", embedding_batch_size=8)
    provider = FakeProvider()
    backfill = VectorBackfill(settings, provider=provider)
    backfill.run_once(limit=10)
    embedding = provider.embed_many(["晨间简报"])[0]
    hits = backfill.search(embedding, limit=5)
    assert hits, "search must return hits"
    assert hits[0]["content"] == "晨间简报内容"
    assert hits[0]["conversation_id"] == "conv-1"
    assert hits[0]["score"] > 0
    close_shared_client()


def test_backfill_removes_degenerate_and_duplicate_vectors(tmp_path: Path):
    """WorkBuddy 2026-09-16 复检 P0-2 根因之一：退化向量冒充实命中。

    零范数向量与跨点重复向量（不同内容嵌出同一向量）在余弦检索里会无条件
    回填高分（实测无关查询得 1.0），提供方级坍缩也无法靠重嵌修复：契约是
    直接出索引（词法层仍在），且同轮不再重嵌入同批点。
    """
    from types import SimpleNamespace

    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, VectorParams

    from src.retrieval.vector_backfill import _point_id

    state = StateDatabase(tmp_path / "lingji_state.db")
    mem = tmp_path / "lingji_memory.db"
    conn = sqlite3.connect(mem)
    conn.execute("CREATE TABLE message_records (message_id TEXT PRIMARY KEY, conversation_id TEXT, role TEXT, content TEXT, occurred_at TEXT, content_hash TEXT)")
    conn.execute("INSERT INTO message_records VALUES ('d-0', 'conv-1', 'user', '桃花源记内容', '2026-09-01T00:00:00Z', 'hd0')")
    conn.execute("INSERT INTO message_records VALUES ('d-1', 'conv-1', 'user', '什么情况', '2026-09-01T00:01:00Z', 'hd1')")
    conn.execute("INSERT INTO message_records VALUES ('d-2', 'conv-1', 'user', '登陆了啊', '2026-09-01T00:02:00Z', 'hd2')")
    conn.commit(); conn.close()
    settings = SimpleNamespace(storage_path=tmp_path, memory_db_path=mem,
        embedding_provider="ollama", ollama_base_url="http://127.0.0.1:11434",
        embed_model="fake-primary", fallback_embed_model="fake-fallback", embedding_batch_size=8)
    close_shared_client()
    client = QdrantClient(path=str(tmp_path / "qdrant"))
    client.create_collection(collection_name="lingji_automatic_memory", vectors_config=VectorParams(size=4, distance="Cosine"))
    client.upsert(collection_name="lingji_automatic_memory", points=[
        PointStruct(id=_point_id("d-0"), vector=[0.0, 0.0, 0.0, 0.0], payload={"message_id": "d-0", "role": "user", "content": "桃花源记内容"}),
        PointStruct(id=_point_id("d-1"), vector=[0.5, 0.5, 0.5, 0.5], payload={"message_id": "d-1", "role": "user", "content": "什么情况"}),
        PointStruct(id=_point_id("d-2"), vector=[0.5, 0.5, 0.5, 0.5], payload={"message_id": "d-2", "role": "user", "content": "登陆了啊"}),
    ])
    client.close()
    backfill = VectorBackfill(settings, provider=FakeProvider())
    backfill.run_once(limit=10)
    close_shared_client()
    client = QdrantClient(path=str(tmp_path / "qdrant"))
    points, _ = client.scroll(collection_name="lingji_automatic_memory", limit=10, with_vectors=True, with_payload=True)
    client.close()
    remaining = {(p.payload or {}).get("message_id") for p in points}
    assert remaining == set(), "degenerate points must be removed from the recall index"
    again = backfill.run_once(limit=10)
    assert again["embedded"] == 0, "give-up list must stop re-embedding removed degenerate points"
    close_shared_client()
