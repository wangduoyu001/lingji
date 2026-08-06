from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.gateway.memory_statistics import MemoryStatisticsService
from src.retrieval.memory_db import MemoryDatabase


class Embedding:
    def status(self):
        return {
            "available": True,
            "active_model": "bge-m3",
            "dimension": 1024,
        }


class UnavailableEmbedding:
    def status(self):
        return {
            "available": False,
            "active_model": None,
            "dimension": None,
        }


class Semantic:
    def __init__(self, status, *, embedding=None):
        self.embedding_provider = embedding or Embedding()
        self.collection = "lingji_memory_acceptance_test"
        self.workspace = SimpleNamespace(qdrant_mode="embedded")
        self._status = status

    def status(self):
        return dict(self._status)

    def coverage(self, expected_ids):
        expected = list(expected_ids)
        return {
            "expected": len(expected),
            "indexed": 0,
            "missing": len(expected),
            "coverage": 1.0 if not expected else 0.0,
            "missing_chunk_ids": expected,
        }


class VectorTruthContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = MemoryDatabase(self.root / "storage" / "lingji_memory.db")
        self.workspace = SimpleNamespace(
            name=SimpleNamespace(value="acceptance"),
            storage_path=self.root / "storage",
            qdrant_mode="embedded",
            qdrant_collection="lingji_memory_acceptance_test",
        )

    def _snapshot(self, semantic):
        gateway = SimpleNamespace(
            database=self.database,
            retriever=SimpleNamespace(semantic_provider=semantic),
            workspace=self.workspace,
            runtime_warnings=[],
        )
        return MemoryStatisticsService(gateway).snapshot()

    def test_ready_service_with_no_collection_is_empty_not_healthy(self):
        payload = self._snapshot(
            Semantic(
                {
                    "ready": True,
                    "collection_exists": False,
                    "vectors": 0,
                    "dimension": None,
                    "rebuild_required": False,
                    "last_error": None,
                }
            )
        )

        vector = payload["vector"]
        self.assertEqual(vector["state"], "empty")
        self.assertEqual(vector["reason_code"], "collection_empty")
        self.assertTrue(vector["service_ready"])
        self.assertFalse(vector["semantic_search_available"])
        self.assertTrue(vector["lexical_search_available"])
        self.assertEqual(payload["state"], "degraded")

    def test_empty_collection_precedes_unverified_embedding_state(self):
        payload = self._snapshot(
            Semantic(
                {
                    "ready": True,
                    "collection_exists": False,
                    "vectors": 0,
                    "dimension": None,
                    "rebuild_required": False,
                    "last_error": None,
                },
                embedding=UnavailableEmbedding(),
            )
        )

        vector = payload["vector"]
        self.assertEqual(vector["state"], "empty")
        self.assertEqual(vector["reason_code"], "collection_empty")
        self.assertFalse(vector["semantic_search_available"])
        self.assertTrue(vector["lexical_search_available"])
        self.assertFalse(payload["embedding"]["available"])

    def test_embedded_lock_is_unavailable_with_single_owner_recovery(self):
        payload = self._snapshot(
            Semantic(
                {
                    "ready": False,
                    "collection_exists": False,
                    "vectors": None,
                    "dimension": None,
                    "rebuild_required": False,
                    "last_error": "Storage folder is already accessed by another instance of Qdrant client",
                }
            )
        )

        vector = payload["vector"]
        self.assertEqual(vector["state"], "unavailable")
        self.assertEqual(vector["reason_code"], "embedded_store_locked")
        self.assertFalse(vector["semantic_search_available"])
        self.assertTrue(vector["lexical_search_available"])
        self.assertEqual(vector["recovery"]["state"], "waiting_for_single_owner")
        self.assertIn("唯一 MCP Runtime", vector["recovery"]["action"])

    def test_rebuild_required_precedes_empty_collection(self):
        payload = self._snapshot(
            Semantic(
                {
                    "ready": True,
                    "collection_exists": False,
                    "vectors": 0,
                    "dimension": None,
                    "rebuild_required": True,
                    "last_error": None,
                },
                embedding=UnavailableEmbedding(),
            )
        )

        vector = payload["vector"]
        self.assertEqual(vector["state"], "degraded")
        self.assertEqual(vector["reason_code"], "vector_rebuild_required")

    def test_service_unavailable_precedes_empty_collection(self):
        payload = self._snapshot(
            Semantic(
                {
                    "ready": False,
                    "collection_exists": False,
                    "vectors": 0,
                    "dimension": None,
                    "rebuild_required": False,
                    "last_error": "connection refused",
                },
                embedding=UnavailableEmbedding(),
            )
        )

        vector = payload["vector"]
        self.assertEqual(vector["state"], "unavailable")
        self.assertEqual(vector["reason_code"], "vector_service_unavailable")

    def test_nonempty_index_still_requires_available_embedding(self):
        payload = self._snapshot(
            Semantic(
                {
                    "ready": True,
                    "collection_exists": True,
                    "vectors": 2,
                    "dimension": 1024,
                    "rebuild_required": False,
                    "last_error": None,
                },
                embedding=UnavailableEmbedding(),
            )
        )

        vector = payload["vector"]
        self.assertEqual(vector["state"], "degraded")
        self.assertEqual(vector["reason_code"], "embedding_unavailable")
        self.assertFalse(vector["semantic_search_available"])

    def test_nonzero_index_reports_semantic_search_available(self):
        semantic = Semantic(
            {
                "ready": True,
                "collection_exists": True,
                "vectors": 2,
                "dimension": 1024,
                "rebuild_required": False,
                "last_error": None,
            }
        )
        semantic.coverage = lambda expected_ids: {
            "expected": len(list(expected_ids)),
            "indexed": len(list(expected_ids)),
            "missing": 0,
            "coverage": 1.0,
            "missing_chunk_ids": [],
        }
        payload = self._snapshot(semantic)

        vector = payload["vector"]
        self.assertEqual(vector["state"], "healthy")
        self.assertEqual(vector["reason_code"], "ready")
        self.assertTrue(vector["semantic_search_available"])


if __name__ == "__main__":
    unittest.main()
