"""vector_backfill 增量化回归（任务单 PERF_RESOURCE_CLOSEOUT_20260927B C 项）。

契约：
- 默认 run_once 只做 payload 层 id/content diff（scroll 不拉向量本体），
  幂等且第二轮零嵌入；
- 零范数/坍缩簇治理改为 deep_check=True 的显式深检；
- 写入侧退化向量拒绝在默认模式下依然生效；
- 集合缺失时按首个有效向量维度创建一次，已存在后不重复创建。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams

from src.retrieval.vector_backfill import (
    COLLECTION,
    VectorBackfill,
    _point_id,
    close_shared_client,
)


class ControlledProvider:
    """确定性 4 维向量替身：计数调用，可注入零范数输出与全批坍缩。"""

    provider_id = "fake"

    def __init__(self, *, zero_for: set[str] | None = None, collapse_all: bool = False):
        self.calls = 0
        self.embedded_texts = 0
        self.zero_for = set(zero_for or ())
        self.collapse_all = collapse_all

    def status(self):
        return {"available": True, "active_model": "fake-embed", "dimension": 4}

    def embed_many(self, texts):
        self.calls += 1
        self.embedded_texts += len(texts)
        out = []
        for text in texts:
            if text in self.zero_for:
                out.append([0.0, 0.0, 0.0, 0.0])
            elif self.collapse_all:
                out.append([0.5, 0.5, 0.5, 0.5])
            else:
                # 稳定字节和种子：跨进程确定（hash() 有进程盐），不同内容几乎不碰撞。
                seed = sum(text.encode("utf-8")) % 997
                out.append([((seed >> i) & 1) * 0.5 + 0.25 for i in range(4)])
        return out

    def close(self):
        pass


class RecordingClient:
    """包装真实 local 客户端：记录 scroll/create_collection 关键字参数。"""

    def __init__(self, inner):
        object.__setattr__(self, "_inner", inner)
        self.scroll_calls: list[dict] = []
        self.create_calls: list[dict] = []

    def scroll(self, **kwargs):
        self.scroll_calls.append(dict(kwargs))
        return self._inner.scroll(**kwargs)

    def create_collection(self, **kwargs):
        self.create_calls.append(dict(kwargs))
        return self._inner.create_collection(**kwargs)

    def close_inner(self):
        close = getattr(self._inner, "close", None)
        if callable(close):
            close()

    def __getattr__(self, name):
        return getattr(self._inner, name)


def _memory_db(tmp_path: Path, rows: list[tuple[str, str]]) -> Path:
    mem = tmp_path / "lingji_memory.db"
    conn = sqlite3.connect(mem)
    conn.execute(
        "CREATE TABLE message_records (message_id TEXT PRIMARY KEY, conversation_id TEXT,"
        " role TEXT, content TEXT, occurred_at TEXT, content_hash TEXT)"
    )
    for i, (mid, content) in enumerate(rows):
        conn.execute(
            "INSERT INTO message_records VALUES (?,?,?,?,?,?)",
            (mid, "conv-1", "user", content, f"2026-09-01T00:00:{i:02d}Z", f"hash-{mid}"),
        )
    conn.commit()
    conn.close()
    return mem


def _settings(tmp_path: Path, mem: Path) -> SimpleNamespace:
    return SimpleNamespace(
        storage_path=tmp_path,
        memory_db_path=mem,
        embedding_provider="ollama",
        ollama_base_url="http://127.0.0.1:11434",
        embed_model="fake-primary",
        fallback_embed_model="fake-fallback",
        embedding_batch_size=8,
    )


def _install_recording_client(tmp_path: Path, monkeypatch) -> RecordingClient:
    """绕过共享客户端池（qdrant local 同路径单客户端），注入记录型包装。"""
    import src.retrieval.vector_backfill as vb_module

    qdrant_path = tmp_path / "qdrant"
    qdrant_path.mkdir(parents=True, exist_ok=True)
    recording = RecordingClient(QdrantClient(path=str(qdrant_path)))
    monkeypatch.setattr(vb_module, "_shared_client", lambda _path: recording)
    return recording


def test_default_run_is_payload_only_and_idempotent(tmp_path, monkeypatch):
    """默认轮不拉向量本体：scroll with_vectors=False，第二轮零嵌入。"""
    close_shared_client()
    mem = _memory_db(tmp_path, [("m-0", "晨间简报内容"), ("m-1", "负载要点内容")])
    settings = _settings(tmp_path, mem)
    recording = _install_recording_client(tmp_path, monkeypatch)
    provider = ControlledProvider()
    backfill = VectorBackfill(settings, provider=provider)
    try:
        first = backfill.run_once(limit=10)
        assert first["embedded"] == 2
        assert first["status"] == "ok"
        assert provider.embedded_texts == 2, "首批应整批嵌入一次"

        second = backfill.run_once(limit=10)
        assert second["embedded"] == 0, "第二轮必须跳过已向量化消息"
        assert second["status"] == "ok"
        assert second["total_vectors"] == 2
        assert provider.embedded_texts == 2, "payload-only 轮不应产生任何重复嵌入"
        assert recording.scroll_calls, "默认轮仍需扫描存量点建立 existing_ids"
        assert all(call["with_vectors"] is False for call in recording.scroll_calls), (
            "默认轮 scroll 一律不拉向量本体（2 万点 × 1024 维不再常驻内存）"
        )

        deep = backfill.run_once(limit=10, deep_check=True)
        assert deep["embedded"] == 0, "健康存量点在深检轮也不得重嵌"
        assert recording.scroll_calls[-1]["with_vectors"] is True, (
            "deep_check=True 才允许拉向量本体"
        )
    finally:
        recording.close_inner()


def test_deep_check_removes_zero_norm_and_collapse_clusters(tmp_path):
    """deep_check=True 剔除零范数点与坍缩簇；give-up 名单阻断后续重嵌。"""
    close_shared_client()
    mem = _memory_db(tmp_path, [
        ("c-0", "桃花源记内容"),
        ("c-1", "什么情况"),
        ("c-2", "登陆了啊"),
        ("z-0", "零范数存量内容"),
    ])
    settings = _settings(tmp_path, mem)
    provider = ControlledProvider(collapse_all=True)
    backfill = VectorBackfill(settings, provider=provider)
    # 预置一个 payload 健康、向量为零范数的存量点（旧版本残留/外部写入）。
    client = QdrantClient(path=str(tmp_path / "qdrant"))
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=4, distance="Cosine"),
    )
    client.upsert(collection_name=COLLECTION, points=[PointStruct(
        id=_point_id("z-0"), vector=[0.0, 0.0, 0.0, 0.0],
        payload={"message_id": "z-0", "role": "user", "content": "零范数存量内容"},
    )])
    client.close()

    first = backfill.run_once(limit=10)  # 默认轻量轮：只补缺口，不做体检
    assert first["embedded"] == 3
    assert provider.embedded_texts == 3

    deep = backfill.run_once(limit=10, deep_check=True)
    assert deep["embedded"] == 0, "被治理的点同轮不得重嵌"
    assert deep["total_vectors"] == 0
    assert provider.embedded_texts == 3, "深检剔除后不得重嵌入同批点"
    close_shared_client()
    client = QdrantClient(path=str(tmp_path / "qdrant"))
    points, _ = client.scroll(collection_name=COLLECTION, limit=10, with_payload=True)
    client.close()
    remaining = {(p.payload or {}).get("message_id") for p in points}
    assert remaining == set(), "零范数点与坍缩簇必须全部出索引"

    again = backfill.run_once(limit=10)  # 默认轻量轮：give-up 名单同样阻断重嵌
    assert again["embedded"] == 0
    assert provider.embedded_texts == 3
    close_shared_client()


def test_default_mode_rejects_degenerate_new_embeddings(tmp_path):
    """写入侧零范数防线在默认模式下依然生效：退化向量拒绝落库。"""
    close_shared_client()
    mem = _memory_db(tmp_path, [("m-0", "健康内容"), ("m-1", "零范数内容")])
    settings = _settings(tmp_path, mem)
    provider = ControlledProvider(zero_for={"零范数内容"})
    backfill = VectorBackfill(settings, provider=provider)
    first = backfill.run_once(limit=10)
    assert first["embedded"] == 1, "退化向量拒绝落库：只有健康向量入库"
    close_shared_client()
    client = QdrantClient(path=str(tmp_path / "qdrant"))
    points, _ = client.scroll(collection_name=COLLECTION, limit=10, with_payload=True)
    client.close()
    mids = {(p.payload or {}).get("message_id") for p in points}
    assert mids == {"m-0"}

    second = backfill.run_once(limit=10)
    assert second["embedded"] == 0, "退化输出持续被拒绝，不得写假命中源"
    close_shared_client()
    client = QdrantClient(path=str(tmp_path / "qdrant"))
    points, _ = client.scroll(collection_name=COLLECTION, limit=10, with_payload=True)
    client.close()
    mids = {(p.payload or {}).get("message_id") for p in points}
    assert mids == {"m-0"}, "被拒绝的消息不得被误标为已向量化"
    close_shared_client()


def test_collection_created_once_when_missing(tmp_path, monkeypatch):
    """集合缺失时按首个有效向量维度创建一次；已存在后不重复创建。"""
    mem = _memory_db(tmp_path, [("m-0", "内容甲"), ("m-1", "内容乙")])
    settings = _settings(tmp_path, mem)
    recording = _install_recording_client(tmp_path, monkeypatch)
    backfill = VectorBackfill(settings, provider=ControlledProvider())
    try:
        first = backfill.run_once(limit=10)
        assert first["embedded"] == 2
        assert len(recording.create_calls) == 1, "集合创建必须移出逐条循环，只发生一次"
        assert recording.create_calls[0]["collection_name"] == COLLECTION
        assert recording.create_calls[0]["vectors_config"].size == 4, "维度取 provider 实际输出"

        second = backfill.run_once(limit=10)
        assert second["embedded"] == 0
        assert second["total_vectors"] == 2
        assert len(recording.create_calls) == 1, "集合已存在后不得重复创建"
    finally:
        recording.close_inner()
