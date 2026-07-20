from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

from src.retrieval.qdrant_provider import (
    QdrantSemanticProvider,
    VectorDimensionMismatchError,
)
from src.retrieval.semantic import SemanticPoint
from src.runtime.workspace import WorkspaceContext, WorkspaceName


HAS_QDRANT = importlib.util.find_spec("qdrant_client") is not None


class FakeEmbeddingProvider:
    def __init__(self, dimension: int = 2):
        self.dimension = dimension
        self.active_model = "fake-embedding"
        self.calls: list[list[str]] = []

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_many(self, texts):
        values = [str(text) for text in texts]
        self.calls.append(values)
        output = []
        for text in values:
            if self.dimension == 2:
                lowered = text.lower()
                if "alpha" in lowered:
                    output.append([1.0, 0.0])
                elif "beta" in lowered:
                    output.append([0.0, 1.0])
                else:
                    output.append([0.7, 0.7])
            else:
                output.append([1.0] + [0.0] * (self.dimension - 1))
        return output

    def status(self):
        return {
            "provider_id": "fake",
            "active_model": self.active_model,
            "dimension": self.dimension,
            "verified": True,
            "available": True,
        }

    def reset_failures(self):
        return None


def workspace(root: Path, name: WorkspaceName = WorkspaceName.ACCEPTANCE) -> WorkspaceContext:
    base = (root / name.value).resolve()
    return WorkspaceContext(
        name=name,
        vault_path=base / "vault",
        raw_path=base / "raw",
        storage_path=base,
        state_db_path=base / "state" / "lingji_state.db",
        memory_db_path=base / "index" / "lingji_memory.db",
        qdrant_mode="memory",
        qdrant_path=None,
        qdrant_url=None,
        qdrant_collection=f"lingji_memory_{name.value}",
        log_path=base / "logs",
        cache_path=base / "cache",
        runtime_settings_path=base / "runtime" / "runtime_settings.json",
        queue_db_path=base / "state" / "lingji_state.db",
        backup_path=base / "backups",
        derived_path=base / "derived",
        temp_path=base / "temp",
        reports_path=base / "reports",
    )


def point(
    chunk_id: str,
    memory_id: str,
    text: str,
    *,
    privacy: str = "private",
    kind: str = "memory_chunk",
) -> SemanticPoint:
    return SemanticPoint(
        chunk_id=chunk_id,
        memory_id=memory_id,
        text=text,
        payload={
            "kind": kind,
            "title": text,
            "status": "active",
            "privacy": privacy,
            "memory_type": "knowledge",
            "project": ["lingji"],
            "tags": ["semantic"],
            "agent_scope": ["all"],
            "relative_path": f"Memory/{memory_id}.md",
            "start_line": 1,
            "end_line": 3,
        },
    )


class QdrantProviderContractTests(unittest.TestCase):
    def test_point_id_is_stable_and_workspace_scoped(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            acceptance = QdrantSemanticProvider(
                workspace(root, WorkspaceName.ACCEPTANCE),
                FakeEmbeddingProvider(),
                client=object(),
            )
            acceptance_again = QdrantSemanticProvider(
                workspace(root, WorkspaceName.ACCEPTANCE),
                FakeEmbeddingProvider(),
                client=object(),
            )
            production = QdrantSemanticProvider(
                workspace(root, WorkspaceName.PRODUCTION),
                FakeEmbeddingProvider(),
                client=object(),
            )

            self.assertEqual(
                acceptance.point_id("LJ-CHUNK-1"),
                acceptance_again.point_id("LJ-CHUNK-1"),
            )
            self.assertNotEqual(
                acceptance.point_id("LJ-CHUNK-1"),
                production.point_id("LJ-CHUNK-1"),
            )

    def test_missing_dependency_is_reported_without_false_ready_state(self):
        if HAS_QDRANT:
            self.skipTest("qdrant-client is installed")
        with tempfile.TemporaryDirectory() as temp:
            provider = QdrantSemanticProvider(
                workspace(Path(temp)),
                FakeEmbeddingProvider(),
            )
            status = provider.status()
            self.assertFalse(status["ready"])
            self.assertIn("qdrant-client is not installed", status["last_error"])


@unittest.skipUnless(HAS_QDRANT, "qdrant-client is required for real in-memory integration")
class QdrantProviderIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.workspace = workspace(Path(self.temp_dir.name))
        self.embedding = FakeEmbeddingProvider()
        self.provider = QdrantSemanticProvider(self.workspace, self.embedding)
        self.addCleanup(self.provider.close)

    def test_upsert_search_count_exists_and_status(self):
        first_id = self.provider.upsert(point("chunk-alpha", "memory-alpha", "alpha memory"))
        self.provider.upsert(point("chunk-beta", "memory-beta", "beta memory"))

        self.assertEqual(first_id, self.provider.point_id("chunk-alpha"))
        self.assertEqual(self.provider.count(), 2)
        self.assertEqual(self.provider.count("memory_chunk"), 2)
        self.assertTrue(self.provider.exists("chunk-alpha"))

        results = self.provider.search(
            "alpha question",
            5,
            {
                "statuses": ["active"],
                "privacy": ["public", "private"],
                "memory_types": ["knowledge"],
                "project": "lingji",
                "tags": ["semantic"],
            },
        )
        self.assertEqual(results[0]["chunk_id"], "chunk-alpha")
        self.assertEqual(results[0]["memory_id"], "memory-alpha")
        self.assertNotIn("text", results[0]["payload"])

        status = self.provider.status()
        self.assertTrue(status["ready"])
        self.assertTrue(status["collection_exists"])
        self.assertEqual(status["vectors"], 2)
        self.assertEqual(status["dimension"], 2)
        self.assertEqual(status["workspace"], "acceptance")

    def test_privacy_filter_excludes_restricted_candidates(self):
        self.provider.upsert(point("chunk-private", "memory-private", "alpha private"))
        self.provider.upsert(
            point(
                "chunk-restricted",
                "memory-restricted",
                "alpha restricted",
                privacy="restricted",
            )
        )

        results = self.provider.search(
            "alpha",
            10,
            {"privacy": ["public", "private"], "statuses": ["active"]},
        )
        self.assertEqual([item["chunk_id"] for item in results], ["chunk-private"])

    def test_delete_and_delete_memory(self):
        self.provider.upsert(point("chunk-1", "memory-shared", "alpha one"))
        self.provider.upsert(point("chunk-2", "memory-shared", "alpha two"))
        self.provider.upsert(point("chunk-3", "memory-other", "beta other"))

        self.provider.delete("chunk-1")
        self.assertFalse(self.provider.exists("chunk-1"))
        self.assertEqual(self.provider.count(), 2)

        self.provider.delete_memory("memory-shared")
        self.assertFalse(self.provider.exists("chunk-2"))
        self.assertTrue(self.provider.exists("chunk-3"))
        self.assertEqual(self.provider.count(), 1)

    def test_coverage_reports_missing_chunks(self):
        self.provider.upsert(point("chunk-1", "memory-1", "alpha"))
        self.provider.upsert(point("chunk-2", "memory-2", "beta"))

        coverage = self.provider.coverage(["chunk-1", "chunk-2", "chunk-3"])
        self.assertEqual(coverage["expected"], 3)
        self.assertEqual(coverage["indexed"], 2)
        self.assertEqual(coverage["missing"], 1)
        self.assertEqual(coverage["missing_chunk_ids"], ["chunk-3"])

    def test_dimension_mismatch_requires_rebuild(self):
        self.provider.upsert(point("chunk-1", "memory-1", "alpha"))
        other = QdrantSemanticProvider(
            self.workspace,
            FakeEmbeddingProvider(dimension=3),
            client=self.provider.client,
        )

        with self.assertRaises(VectorDimensionMismatchError):
            other.upsert(point("chunk-2", "memory-2", "alpha"))
        status = other.status()
        self.assertTrue(status["rebuild_required"])
        self.assertFalse(status["ready"])


if __name__ == "__main__":
    unittest.main()
