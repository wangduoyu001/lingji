from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.retrieval.collection_migration import (
    VectorCollectionMigrationError,
    VectorCollectionMigrationService,
)
from src.retrieval.index_coordinator import MemoryIndexCoordinator
from src.retrieval.memory_db import MemoryDatabase


class FakeEmbeddingProvider:
    def __init__(self, model: str = "bge-m3:latest", *, available: bool = True):
        self.model = model
        self.available = available

    def status(self):
        return {
            "provider_id": "fake",
            "configured_model": self.model,
            "active_model": self.model,
            "dimension": 1024,
            "verified": self.available,
            "available": self.available,
            "failure_count": 0,
        }


class FakeTargetProvider:
    def __init__(
        self,
        collection: str = "lingji_memory_production_bge_m3_1024_v1",
        *,
        model: str = "bge-m3:latest",
    ):
        self.collection = collection
        self.embedding_provider = FakeEmbeddingProvider(model)
        self.points = {}
        self.short_result = False
        self.partial_coverage = False
        self.extra_vectors = 0
        self.ready = True
        self.collection_exists = True
        self.rebuild_required = False

    def upsert_many(self, points):
        selected = list(points)
        for point in selected:
            self.points[point.chunk_id] = point
        ids = [f"point:{point.chunk_id}" for point in selected]
        return ids[:-1] if self.short_result and ids else ids

    def coverage(self, expected_chunk_ids):
        expected = list(expected_chunk_ids)
        found = [chunk_id for chunk_id in expected if chunk_id in self.points]
        if self.partial_coverage and found:
            found = found[:-1]
        missing = [chunk_id for chunk_id in expected if chunk_id not in set(found)]
        return {
            "expected": len(expected),
            "indexed": len(found),
            "missing": len(missing),
            "coverage": round(len(found) / len(expected), 6) if expected else 1.0,
            "missing_chunk_ids": missing,
        }

    def status(self):
        return {
            "ready": self.ready,
            "collection_exists": self.collection_exists,
            "collection": self.collection,
            "mode": "memory",
            "vectors": len(self.points) + self.extra_vectors,
            "dimension": 1024,
            "rebuild_required": self.rebuild_required,
            "last_error": None,
        }


class FakeStateDatabase:
    def __init__(self):
        self.events = []

    def append_event(self, event_type, entity_type, entity_id, payload):
        self.events.append((event_type, entity_type, entity_id, payload))


class VectorCollectionMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.vault = self.root / "vault"
        self.vault.mkdir(parents=True)
        self.database = MemoryDatabase(self.root / "storage" / "lingji_memory.db")
        self.state_db = FakeStateDatabase()
        self._seed_memory()
        self.manifest_dir = self.root / "reports"
        self.service = VectorCollectionMigrationService(
            self.database,
            workspace_name="production",
            source_collection="lingji_memory_production",
            source_model="nomic-embed-text",
            source_fallback_model="nomic-embed-text",
            state_db=self.state_db,
            batch_size=1,
            manifest_dir=self.manifest_dir,
        )

    def _entry(self, relative_path: str, memory_id: str, body: str):
        path = self.vault / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        text = (
            "---\n"
            f"id: {memory_id}\n"
            "memory_type: knowledge\n"
            "memory_tier: archival\n"
            "status: active\n"
            "review_status: approved\n"
            "privacy: private\n"
            "project: [lingji]\n"
            "tags: [migration]\n"
            "agent_scope: [all]\n"
            "---\n"
            f"{body}\n"
        )
        path.write_text(text, encoding="utf-8")
        return {
            "id": memory_id,
            "relative_path": relative_path,
            "title": memory_id,
            "memory_type": "knowledge",
            "memory_tier": "archival",
            "status": "active",
            "review_status": "approved",
            "privacy": "private",
            "project": ["lingji"],
            "tags": ["migration"],
            "agent_scope": ["all"],
            "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }

    def _seed_memory(self):
        first = self._entry(
            "03-Knowledge/first.md",
            "MEM-FIRST",
            "# 第一条\n\n用于迁移验证的中文正文。",
        )
        second = self._entry(
            "03-Knowledge/second.md",
            "MEM-SECOND",
            "# Second\n\nEnglish migration validation body.",
        )
        MemoryIndexCoordinator(self.database).sync([first, second], self.vault, force=True)

    def test_plan_rejects_active_collection(self):
        with self.assertRaises(VectorCollectionMigrationError):
            self.service.plan(
                target_collection="lingji_memory_production",
                target_model="bge-m3",
            )

    def test_plan_rejects_empty_canonical_index(self):
        empty = MemoryDatabase(self.root / "empty" / "memory.db")
        service = VectorCollectionMigrationService(
            empty,
            workspace_name="production",
            source_collection="lingji_memory_production",
            source_model="nomic-embed-text",
        )
        with self.assertRaisesRegex(VectorCollectionMigrationError, "no chunks"):
            service.plan(
                target_collection="lingji_memory_production_bge_m3",
                target_model="bge-m3",
            )

    def test_validated_candidate_writes_manifest_and_switch_contract(self):
        provider = FakeTargetProvider()

        result = self.service.build_candidate(provider, target_model="bge-m3")

        self.assertTrue(result.validated)
        self.assertEqual(result.coverage["coverage"], 1.0)
        self.assertEqual(result.vector_status["vectors"], result.plan.expected_chunks)
        self.assertEqual(
            result.activation_settings,
            {
                "embed_model": "bge-m3",
                "fallback_embed_model": "bge-m3",
                "production_qdrant_collection": provider.collection,
            },
        )
        self.assertEqual(
            result.rollback_settings["production_qdrant_collection"],
            "lingji_memory_production",
        )
        manifest = Path(result.manifest_path or "")
        self.assertTrue(manifest.is_file())
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertTrue(payload["validated"])
        self.assertNotIn("用于迁移验证的中文正文", manifest.read_text(encoding="utf-8"))
        self.assertEqual(self.state_db.events[-1][0], "vector_collection_candidate_validated")

    def test_partial_coverage_is_rejected_and_failure_manifest_is_written(self):
        provider = FakeTargetProvider()
        provider.partial_coverage = True

        with self.assertRaisesRegex(VectorCollectionMigrationError, "coverage"):
            self.service.build_candidate(provider, target_model="bge-m3")

        manifests = list(self.manifest_dir.glob("*.json"))
        self.assertEqual(len(manifests), 1)
        payload = json.loads(manifests[0].read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["activation_settings"], {})
        self.assertEqual(self.state_db.events[-1][0], "vector_collection_candidate_failed")

    def test_extra_target_vectors_are_rejected(self):
        provider = FakeTargetProvider()
        provider.extra_vectors = 1

        with self.assertRaisesRegex(VectorCollectionMigrationError, "expected exactly"):
            self.service.build_candidate(provider, target_model="bge-m3")

    def test_wrong_active_model_is_rejected(self):
        provider = FakeTargetProvider(model="nomic-embed-text")

        with self.assertRaisesRegex(VectorCollectionMigrationError, "does not match target"):
            self.service.build_candidate(provider, target_model="bge-m3")

    def test_short_upsert_result_is_rejected(self):
        provider = FakeTargetProvider()
        provider.short_result = True

        with self.assertRaisesRegex(VectorCollectionMigrationError, "indexed 0 of 1"):
            self.service.build_candidate(provider, target_model="bge-m3")

    def test_model_latest_tag_is_considered_same_model(self):
        provider = FakeTargetProvider(model="bge-m3:latest")

        result = self.service.build_candidate(provider, target_model="bge-m3")

        self.assertTrue(result.validated)


if __name__ == "__main__":
    unittest.main()
