"""chunk 回填自动化：drain 线程并用网关 semantic_provider 补齐正式语义集合。

缺口根因（2026-09-23）：chunks 层只有手动 /api/observability/vectorize 会补，
自动 drain 只跑消息层——/api/vector/coverage 的 missing 长期不收敛。
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.automatic_memory import AutomaticMemoryRuntime, SourceRegistry
from src.extraction.bootstrap import build_extraction_pipeline
from src.storage import StateDatabase

try:
    from src.retrieval.chunk_backfill import ChunkVectorBackfill
    from src.retrieval.memory_db import MemoryDatabase
    from src.retrieval.vector_backfill import VectorBackfill, close_shared_client
    from src.retrieval import MarkdownChunker
    from src.indexer.index import PEMISIndex
except ModuleNotFoundError:  # pragma: no cover
    ChunkVectorBackfill = None  # type: ignore[assignment]


class FakeEmbedProvider:
    provider_id = "fake"

    def status(self):
        return {"available": True, "active_model": "fake-embed", "dimension": 4}

    def embed_many(self, texts):
        return [[0.25, 0.5, 0.25, 0.5] for _ in texts]

    def close(self):
        pass


class FakeSemanticProvider:
    """进程内语义集合替身：记录 upsert 的 payload 供断言。"""

    def __init__(self):
        self.points: dict[str, dict] = {}

    def coverage(self, expected_chunk_ids):
        missing = [cid for cid in expected_chunk_ids if cid not in self.points]
        return {"missing_chunk_ids": missing}

    def upsert_many(self, points):
        ids = []
        for point in points:
            self.points[str(point.chunk_id)] = {
                "text": point.text,
                "payload": dict(point.payload or {}),
            }
            ids.append(str(point.chunk_id))
        return ids

    def delete(self, chunk_id):
        self.points.pop(str(chunk_id), None)


def _settings(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        storage_path=tmp_path / "storage",
        state_db_path=tmp_path / "storage" / "lingji_state.db",
        memory_db_path=tmp_path / "storage" / "lingji_memory.db",
        vault_path=tmp_path / "vault",
        runtime_settings_file="runtime_settings.json",
        scheduler_poll_seconds=0.05,
        automatic_memory_debounce_seconds=1,
        automatic_memory_reconciliation_seconds=60,
        automatic_memory_integrity_seconds=3600,
        extraction_poll_seconds=0.05,
        extraction_batch_size=1,
        extraction_max_attempts=1,
        extraction_lease_heartbeat_seconds=2,
        extraction_stale_after_seconds=30,
        embedding_enabled=False,
        semantic_enabled=False,
    )


def _memory_db_with_one_chunk(settings: SimpleNamespace) -> MemoryDatabase:
    vault = Path(settings.vault_path)
    note_dir = vault / "03-Knowledge" / "General"
    note_dir.mkdir(parents=True, exist_ok=True)
    (note_dir / "chunk-backfill.md").write_text(
        "---\n"
        "schema_version: 1\nid: LJ-MEM-CHUNK-1\ntitle: 回填验证\n"
        "memory_type: knowledge\nmemory_tier: archival\nstatus: active\n"
        "privacy: private\nimportance: medium\nreview_status: approved\n"
        "---\n自动 chunk 回填验证正文。\n",
        encoding="utf-8",
    )
    database = MemoryDatabase(settings.memory_db_path)
    indexer = PEMISIndex(vault, Path(settings.storage_path))
    indexer.build_index()
    database.rebuild_from_index(
        indexer.get_all(), vault, MarkdownChunker(max_chars=200, overlap_chars=20)
    )
    return database


@pytest.mark.skipif(ChunkVectorBackfill is None, reason="chunk backfill module absent")
def test_drain_runs_chunk_backfill_through_gateway_provider(tmp_path, monkeypatch):
    close_shared_client()
    settings = _settings(tmp_path)
    _memory_db_with_one_chunk(settings)
    semantic = FakeSemanticProvider()
    monkeypatch.setattr(
        "src.model_center.build_embedding_provider",
        lambda *_args, **_kwargs: FakeEmbedProvider(),
    )
    state = StateDatabase(settings.state_db_path)
    registry = SourceRegistry(state)
    pipeline = build_extraction_pipeline(settings)
    runtime = AutomaticMemoryRuntime(
        state_db=state, pipeline=pipeline, settings=settings,
        registry=registry, semantic_provider=semantic,
    )
    assert runtime._backfill_drain is not None
    result = runtime._backfill_drain()
    assert int(result["chunk_embedded"]) >= 1, "drain must fill the formal chunk collection"
    assert len(semantic.points) == 1
    (point,) = semantic.points.values()
    # chunk 层 embedding_model 由真实 QdrantSemanticProvider.upsert_many 在 embed
    # 成功后补记（active_model 必已就绪）；fake 替身不经过该层，只验内容与来源。
    assert "回填验证" in point["text"] or "chunk" in point["text"]
    # 幂等：再跑一轮不再写入
    again = runtime._backfill_drain()
    assert int(again["chunk_embedded"]) == 0


@pytest.mark.skipif(ChunkVectorBackfill is None, reason="chunk backfill module absent")
def test_drain_without_gateway_provider_keeps_message_only(tmp_path, monkeypatch):
    close_shared_client()
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        "src.model_center.build_embedding_provider",
        lambda *_args, **_kwargs: FakeEmbedProvider(),
    )
    state = StateDatabase(settings.state_db_path)
    registry = SourceRegistry(state)
    pipeline = build_extraction_pipeline(settings)
    runtime = AutomaticMemoryRuntime(
        state_db=state, pipeline=pipeline, settings=settings, registry=registry,
    )
    assert runtime._build_chunk_backfill(settings) is None
    result = runtime._backfill_drain()
    assert result is not None
    assert int(result["chunk_embedded"]) == 0


@pytest.mark.skipif(ChunkVectorBackfill is None, reason="chunk backfill module absent")
def test_message_payload_records_embedding_model(tmp_path):
    """消息层点补记 embedding_model：同维度换模型后指纹守卫才有据可查。"""
    import sqlite3

    close_shared_client()
    mem = tmp_path / "lingji_memory.db"
    conn = sqlite3.connect(mem)
    conn.execute(
        "CREATE TABLE message_records (message_id TEXT PRIMARY KEY, conversation_id TEXT,"
        " role TEXT, content TEXT, occurred_at TEXT, content_hash TEXT)"
    )
    conn.execute(
        "INSERT INTO message_records VALUES ('m-1','c1','user','负载要点','2026-09-23T00:00:00Z','h1')"
    )
    conn.commit()
    conn.close()
    settings = SimpleNamespace(storage_path=tmp_path, memory_db_path=mem)
    backfill = VectorBackfill(settings, provider=FakeEmbedProvider())
    result = backfill.run_once(limit=10)
    assert result["embedded"] == 1
    from src.retrieval.vector_backfill import COLLECTION, _point_id, _shared_client

    client = _shared_client(Path(str(tmp_path)) / "qdrant")
    points, _ = client.scroll(
        collection_name=COLLECTION, limit=10, with_payload=True, with_vectors=False
    )
    payloads = {p.payload.get("message_id"): p.payload for p in points}
    assert payloads["m-1"].get("embedding_model") == "fake-embed"
    assert _point_id("m-1") > 0
