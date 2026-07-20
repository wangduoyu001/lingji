from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from src.gateway.memory_statistics import MemoryStatisticsService
from src.retrieval.memory_db import MemoryDatabase


class FakeEmbeddingProvider:
    def status(self):
        return {
            "provider_id": "fake",
            "available": True,
            "verified": True,
            "primary_model": "bge-m3",
            "active_model": "bge-m3",
            "dimension": 1024,
        }


class FakeSemanticProvider:
    def __init__(self, expected_ids):
        self.embedding_provider = FakeEmbeddingProvider()
        self.expected_ids = list(expected_ids)
        self.collection = "lingji_memory_acceptance_test"
        self.workspace = SimpleNamespace(qdrant_mode="memory")

    def status(self):
        return {
            "ready": True,
            "collection_exists": True,
            "vectors": len(self.expected_ids),
            "dimension": 1024,
            "collection": self.collection,
            "mode": "memory",
            "rebuild_required": False,
            "last_error": None,
        }

    def coverage(self, expected_ids):
        expected = list(expected_ids)
        indexed = sum(1 for chunk_id in expected if chunk_id in self.expected_ids)
        missing = [chunk_id for chunk_id in expected if chunk_id not in self.expected_ids]
        return {
            "expected": len(expected),
            "indexed": indexed,
            "missing": len(missing),
            "coverage": indexed / len(expected) if expected else 1.0,
            "missing_chunk_ids": missing,
        }


class MemoryStatisticsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.vault = self.root / "vault"
        self.vault.mkdir(parents=True)
        self.database = MemoryDatabase(self.root / "storage" / "lingji_memory.db")

    def _index_one_memory(self):
        relative_path = "03-Knowledge/status.md"
        path = self.vault / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        text = "# 状态\n\nMemoryStatusNeedle 应产生真实统计。\n"
        path.write_text(text, encoding="utf-8")
        entry = {
            "id": "MEM-STATUS",
            "relative_path": relative_path,
            "title": "状态合同",
            "memory_type": "knowledge",
            "status": "active",
            "privacy": "private",
            "agent_scope": ["all"],
            "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }
        self.database.rebuild_from_index([entry], self.vault)
        with self.database._connection() as connection:
            rows = connection.execute("SELECT chunk_id FROM memory_chunks ORDER BY chunk_id").fetchall()
        return [str(row["chunk_id"]) for row in rows]

    def _gateway(self, semantic, warnings=None):
        workspace = SimpleNamespace(
            name=SimpleNamespace(value="acceptance"),
            storage_path=self.root / "storage",
            qdrant_mode="memory",
            qdrant_collection="lingji_memory_acceptance_test",
        )
        return SimpleNamespace(
            database=self.database,
            retriever=SimpleNamespace(semantic_provider=semantic),
            workspace=workspace,
            runtime_warnings=list(warnings or []),
        )

    def test_live_snapshot_reports_real_counts_and_persists(self):
        chunk_ids = self._index_one_memory()
        snapshot_path = self.root / "storage" / "memory_status.json"
        service = MemoryStatisticsService(
            self._gateway(FakeSemanticProvider(chunk_ids)),
            snapshot_path=snapshot_path,
        )

        payload = service.publish()

        self.assertEqual(payload["source"], "live")
        self.assertEqual(payload["state"], "healthy")
        self.assertEqual(payload["memory"]["documents"], 1)
        self.assertEqual(payload["memory"]["chunks"], len(chunk_ids))
        self.assertEqual(payload["vector"]["vectors"], len(chunk_ids))
        self.assertEqual(payload["coverage"]["coverage"], 1.0)
        self.assertEqual(payload["embedding"]["active_model"], "bge-m3")
        self.assertTrue(snapshot_path.is_file())

        reader = MemoryStatisticsService(snapshot_path=snapshot_path)
        cached = reader.snapshot()
        self.assertEqual(cached["source"], "snapshot")
        self.assertFalse(cached["stale"])
        self.assertEqual(cached["memory"]["documents"], 1)

    def test_missing_snapshot_returns_unknown_values_not_fake_zero(self):
        reader = MemoryStatisticsService(snapshot_path=self.root / "missing.json")

        payload = reader.snapshot()

        self.assertEqual(payload["state"], "configuration_required")
        self.assertIsNone(payload["memory"]["documents"])
        self.assertIsNone(payload["memory"]["chunks"])
        self.assertIsNone(payload["vector"]["vectors"])
        self.assertTrue(payload["stale"])

    def test_stale_snapshot_is_explicitly_degraded(self):
        snapshot_path = self.root / "memory_status.json"
        old = datetime.now(timezone.utc) - timedelta(hours=1)
        snapshot_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "as_of": old.isoformat().replace("+00:00", "Z"),
                    "source": "live",
                    "stale": False,
                    "state": "healthy",
                    "workspace": "production",
                    "memory": {"state": "healthy", "documents": 2, "chunks": 4},
                    "embedding": {"state": "healthy", "available": True},
                    "vector": {"state": "healthy", "vectors": 4},
                    "coverage": {"state": "healthy", "expected": 4, "indexed": 4},
                    "warnings": [],
                }
            ),
            encoding="utf-8",
        )
        reader = MemoryStatisticsService(
            snapshot_path=snapshot_path,
            stale_after_seconds=10,
        )

        payload = reader.snapshot()

        self.assertTrue(payload["stale"])
        self.assertEqual(payload["state"], "degraded")
        self.assertGreater(payload["age_seconds"], 10)

    def test_lexical_only_mode_is_disabled_not_zero_vector_success(self):
        self._index_one_memory()
        service = MemoryStatisticsService(self._gateway(None))

        payload = service.snapshot()

        self.assertEqual(payload["memory"]["state"], "healthy")
        self.assertEqual(payload["vector"]["state"], "disabled")
        self.assertIsNone(payload["vector"]["vectors"])
        self.assertEqual(payload["coverage"]["state"], "disabled")

    def test_semantic_bootstrap_failure_is_degraded(self):
        self._index_one_memory()
        service = MemoryStatisticsService(
            self._gateway(
                None,
                warnings=[
                    {
                        "code": "semantic_runtime_initialization_failed",
                        "stage": "bootstrap",
                        "message": "Ollama unavailable",
                    }
                ],
            )
        )

        payload = service.snapshot()

        self.assertEqual(payload["state"], "degraded")
        self.assertEqual(payload["vector"]["state"], "degraded")
        self.assertIsNone(payload["vector"]["vectors"])
        self.assertIn("Ollama unavailable", payload["vector"]["last_error"])


if __name__ == "__main__":
    unittest.main()
