"""嵌入式 Qdrant 客户端池回归：同一存储路径在一个进程内只能有一个客户端。

复现的原始故障（2026-09-17）：网关侧 ``QdrantSemanticProvider`` 自建客户端
（``gateway/bootstrap.py`` 不传 ``client=``）后，同进程 ``vector_backfill._shared_client()``
拿不到 flock，报::

    RuntimeError: Storage folder ... is already accessed by another instance
    of Qdrant client.

后果：``/api/observability/vectorize`` 的语义通道整段消失（``semantic_provider = None``），
chunk 向量回填间歇整轮失败、``remaining`` 长时间不动。

flock 绑定的是 open file description 而非进程，所以**同一进程第二次 open + 加锁
同样会被拒** —— 下面两条顺序测试就是这条性质的回归。
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.retrieval.qdrant_client_pool import (
    close_all,
    pooled_paths,
    shared_embedded_client,
)
from src.retrieval.qdrant_provider import QdrantSemanticProvider
from src.retrieval.vector_backfill import _shared_client
from src.runtime.workspace import WorkspaceContext, WorkspaceName


class FakeEmbeddingProvider:
    def __init__(self, dimension: int = 4):
        self.dimension = dimension

    def embed(self, text):
        return self.embed_many([text])[0]

    def embed_many(self, texts):
        return [[1.0] + [0.0] * (self.dimension - 1) for _ in texts]

    def status(self):
        return {
            "provider_id": "fake",
            "active_model": "fake",
            "dimension": self.dimension,
            "available": True,
        }


def embedded_workspace(root: Path) -> WorkspaceContext:
    base = (root / "acceptance").resolve()
    return WorkspaceContext(
        name=WorkspaceName.ACCEPTANCE,
        vault_path=base / "vault",
        raw_path=base / "raw",
        storage_path=base,
        state_db_path=base / "state" / "lingji_state.db",
        memory_db_path=base / "index" / "lingji_memory.db",
        qdrant_mode="embedded",
        qdrant_path=base / "qdrant",
        qdrant_url=None,
        qdrant_collection="lingji_memory_acceptance",
        log_path=base / "logs",
        cache_path=base / "cache",
        runtime_settings_path=base / "runtime" / "runtime_settings.json",
        queue_db_path=base / "state" / "lingji_state.db",
        backup_path=base / "backups",
        derived_path=base / "derived",
        temp_path=base / "temp",
        reports_path=base / "reports",
    )


class QdrantClientPoolTest(unittest.TestCase):
    def tearDown(self) -> None:
        close_all()

    def test_pool_reuses_client_across_path_spellings(self) -> None:
        """str / Path / 结尾斜杠 必须命中同一个键，不能各建一个客户端。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = shared_embedded_client(root / "qdrant")
            self.assertIs(first, shared_embedded_client(root / "qdrant"))
            self.assertIs(first, shared_embedded_client(str(root / "qdrant")))
            self.assertIs(first, shared_embedded_client(str(root / "qdrant") + "/"))
            self.assertEqual(len(pooled_paths()), 1, "同一路径不得产生第二个客户端")

    def test_provider_reuses_client_held_by_backfill(self) -> None:
        """回填先持锁时，provider 不得再开第二个客户端（旧代码在此抛错）。"""
        with tempfile.TemporaryDirectory() as tmp:
            workspace = embedded_workspace(Path(tmp))
            held_by_backfill = _shared_client(workspace.qdrant_path)

            provider = QdrantSemanticProvider(workspace, FakeEmbeddingProvider())
            self.assertIs(provider.client, held_by_backfill)
            self.assertFalse(provider._owns_client, "池化客户端不归 provider 独占所有")

    def test_backfill_reuses_client_held_by_provider(self) -> None:
        """真实生产顺序：网关先建 provider 持锁，回填随后必须复用而不是撞锁。"""
        with tempfile.TemporaryDirectory() as tmp:
            workspace = embedded_workspace(Path(tmp))
            provider = QdrantSemanticProvider(workspace, FakeEmbeddingProvider())

            self.assertIs(_shared_client(workspace.qdrant_path), provider.client)

    def test_provider_close_keeps_pooled_client_usable(self) -> None:
        """provider 关闭不得连带关掉进程共享的客户端，否则其他持有者拿到死对象。"""
        with tempfile.TemporaryDirectory() as tmp:
            workspace = embedded_workspace(Path(tmp))
            provider = QdrantSemanticProvider(workspace, FakeEmbeddingProvider())
            shared = provider.client

            provider.close()

            self.assertIs(_shared_client(workspace.qdrant_path), shared)
            self.assertTrue(shared.get_collections())


if __name__ == "__main__":
    unittest.main()
