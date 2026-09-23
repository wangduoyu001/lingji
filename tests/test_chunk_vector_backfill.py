"""chunk 级语义向量回填：把正式语义集合按 memory_chunks 幂等补齐（WorkBuddy R1-B/R5）。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.retrieval.chunk_backfill import ChunkVectorBackfill
from src.retrieval.qdrant_provider import QdrantSemanticProvider
from src.retrieval import MemoryDatabase, MarkdownChunker
from src.indexer.index import PEMISIndex
from src.runtime.workspace import WorkspaceContext, WorkspaceName

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))


class FakeEmbeddingProvider:
    def __init__(self, dimension: int = 8):
        self.dimension = dimension
        self.active_model = "bge-m3"

    def embed(self, text):
        return self.embed_many([text])[0]

    def embed_many(self, texts):
        return [[1.0] + [0.0] * (self.dimension - 1) for _ in texts]

    def status(self):
        return {"provider_id": "fake", "active_model": self.active_model,
                "dimension": self.dimension, "available": True}


def workspace(root: Path) -> WorkspaceContext:
    base = (root / "acceptance").resolve()
    return WorkspaceContext(
        name=WorkspaceName.ACCEPTANCE, vault_path=base / "vault", raw_path=base / "raw",
        storage_path=base, state_db_path=base / "state" / "lingji_state.db",
        memory_db_path=base / "index" / "lingji_memory.db", qdrant_mode="memory",
        qdrant_path=None, qdrant_url=None, qdrant_collection="lingji_memory_acceptance",
        log_path=base / "logs", cache_path=base / "cache",
        runtime_settings_path=base / "runtime" / "runtime_settings.json",
        queue_db_path=base / "state" / "lingji_state.db", backup_path=base / "backups",
        derived_path=base / "derived", temp_path=base / "temp", reports_path=base / "reports",
    )


def _note(vault: Path, relative, memory_id, title, body):
    path = vault / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        f"schema_version: 1\nid: {memory_id}\ntitle: {title}\n"
        "memory_type: knowledge\nmemory_tier: archival\nstatus: active\n"
        "privacy: private\nimportance: medium\nreview_status: approved\n"
        "---\n" + body,
        encoding="utf-8",
    )
    return path


class ChunkVectorBackfillTest(unittest.TestCase):
    def test_backfill_fills_formal_collection_and_is_idempotent(self):
        import tempfile
        
        temp_dir = tempfile.TemporaryDirectory()
        self.addCallback = temp_dir.cleanup
        root = Path(temp_dir.name)
        vault = root / "vault"
        storage = root / "storage"
        database = MemoryDatabase(storage / "lingji_memory.db")
        indexer = PEMISIndex(vault, storage)
        vault.mkdir(parents=True, exist_ok=True)
        _note(vault, "03-Knowledge/A/jianli.md", "LJ-MEM-A", "简历要点", "# 简历\n\n薏仁采购与简历内容并存。\n")
        indexer.build_index()
        database.rebuild_from_index(indexer.get_all(), vault, MarkdownChunker(max_chars=200, overlap_chars=20))

        ws = workspace(root)
        provider = QdrantSemanticProvider(ws, FakeEmbeddingProvider())

        backfill = ChunkVectorBackfill(database, provider)
        result = backfill.run_once(limit=100)
        self.assertGreater(result["embedded"], 0, "empty collection must be filled by backfill")

        cov = provider.coverage([c["chunk_id"] for c in database.semantic_chunk_rows()])
        self.assertGreaterEqual(cov["coverage"], 0.99, "backfill must reach full chunk coverage")

        again = backfill.run_once(limit=100)
        self.assertEqual(again["embedded"], 0, "second pass must be idempotent")


if __name__ == "__main__":
    unittest.main()


class EmbeddingFingerprintGuardTests(unittest.TestCase):
    """同维度换嵌入模型必须被指纹校验拦截（防静默混库，9-23 主人拍板换 Qwen3 前置安全网）。"""

    def _provider(self, ws, model: str, client=None) -> QdrantSemanticProvider:
        provider_model = {"active_model": model}

        class _ModelProvider(FakeEmbeddingProvider):
            def status(self_inner):
                return {"provider_id": "fake", "active_model": provider_model["active_model"],
                        "dimension": self_inner.dimension, "available": True}

        return QdrantSemanticProvider(ws, _ModelProvider(), client=client)

    def _point(self, chunk_id: str) -> "SemanticPoint":
        from src.retrieval.semantic import SemanticPoint

        return SemanticPoint(chunk_id=chunk_id, memory_id="mem-x", text="部署方案定稿", payload={})

    def test_same_dimension_model_swap_is_blocked_with_rebuild_required(self):
        import tempfile

        from src.retrieval.qdrant_provider import VectorDimensionMismatchError

        with tempfile.TemporaryDirectory() as tmp:
            ws = workspace(Path(tmp))
            from qdrant_client import QdrantClient

            client = QdrantClient(":memory:")
            old = self._provider(ws, "bge-m3", client=client)
            old.upsert(self._point("chunk-1"))
            old.status()  # 正常

            new = self._provider(ws, "qwen3-embedding:0.6b", client=client)
            with self.assertRaises(VectorDimensionMismatchError):
                new.upsert(self._point("chunk-2"))
            self.assertTrue(new.status()["rebuild_required"])
            self.assertIn("bge-m3", new.status()["last_error"] or "")

    def test_same_model_continues_to_work(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            ws = workspace(Path(tmp))
            from qdrant_client import QdrantClient

            client = QdrantClient(":memory:")
            provider = self._provider(ws, "bge-m3", client=client)
            provider.upsert(self._point("chunk-1"))
            again = self._provider(ws, "bge-m3", client=client)
            again.upsert(self._point("chunk-2"))
            self.assertFalse(again.status()["rebuild_required"])


if __name__ == "__main__":
    unittest.main()
