from __future__ import annotations

import hashlib
import tempfile
from tests.fixtures.workspace_paths import allow_test_workspace_root
import unittest
from pathlib import Path
from unittest.mock import patch

from src.config import Settings
from src.gateway.bootstrap import build_memory_gateway
from src.retrieval.semantic_freshness import CoverageGuardedSemanticProvider
from src.runtime import WorkspaceResolver


class FakeEmbeddingProvider:
    def __init__(self):
        self.closed = False

    def embed(self, text):
        return [1.0, 0.0]

    def embed_many(self, texts):
        return [[1.0, 0.0] for _ in texts]

    def status(self):
        return {
            "provider_id": "fake",
            "active_model": "fake-embedding",
            "dimension": 2,
            "verified": True,
            "available": True,
        }

    def reset_failures(self):
        return None

    def close(self):
        self.closed = True


class FakeSemanticProvider:
    def __init__(self, *args, fail_search=False, **kwargs):
        self.closed = False
        self.fail_search = fail_search
        self.points = {}

    def search(self, query, limit, filters=None):
        if self.fail_search:
            raise RuntimeError("semantic query unavailable")
        return []

    def upsert(self, point):
        return self.upsert_many([point])[0]

    def upsert_many(self, points):
        selected = list(points)
        for point in selected:
            self.points[point.chunk_id] = point
        return [f"point:{point.chunk_id}" for point in selected]

    def delete(self, chunk_id):
        self.points.pop(chunk_id, None)

    def delete_memory(self, memory_id):
        for chunk_id, point in list(self.points.items()):
            if point.memory_id == memory_id:
                self.points.pop(chunk_id, None)

    def status(self):
        return {"ready": True, "collection_exists": True, "vectors": len(self.points)}

    def count(self, kind=None):
        return len(self.points)

    def exists(self, chunk_id):
        return chunk_id in self.points

    def coverage(self, expected_chunk_ids):
        expected = list(expected_chunk_ids)
        indexed = sum(1 for chunk_id in expected if chunk_id in self.points)
        return {
            "expected": len(expected),
            "indexed": indexed,
            "missing": len(expected) - indexed,
        }

    def close(self):
        self.closed = True


class SemanticRuntimeWiringTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self._allow_cm = allow_test_workspace_root(root)
        self._allow_cm.__enter__()
        self.addCleanup(self._allow_cm.__exit__, None, None, None)
        self.root = root
        self.settings = Settings(
            _env_file=None,
            vault_dir=str(root / "legacy-vault"),
            storage_dir=str(root / "legacy-storage"),
            log_dir=str(root / "legacy-logs"),
            backup_dir=str(root / "backup"),
            workspace_root=str(root / "workspaces"),
            production_qdrant_collection="lingji_memory_production_test",
            acceptance_qdrant_collection="lingji_memory_acceptance_test",
            semantic_enabled=True,
            vault_auto_init=False,
            startup_min_free_gb=0,
        )
        self.context = WorkspaceResolver.resolve(
            self.settings,
            "acceptance",
            environ={},
            project_root=root,
        )
        self.context.vault_path.mkdir(parents=True, exist_ok=True)
        self.context.storage_path.mkdir(parents=True, exist_ok=True)

    def test_enabled_runtime_injects_guarded_reader_and_direct_writer_provider(self):
        embedding = FakeEmbeddingProvider()
        semantic = FakeSemanticProvider()
        with patch("src.gateway.bootstrap.build_embedding_provider", return_value=embedding), patch(
            "src.gateway.bootstrap.QdrantSemanticProvider", return_value=semantic
        ):
            gateway = build_memory_gateway(
                self.settings,
                rebuild_if_empty=False,
                workspace=self.context,
            )

        guarded = gateway.retriever.semantic_provider
        self.assertIsInstance(guarded, CoverageGuardedSemanticProvider)
        self.assertIs(guarded.provider, semantic)
        self.assertIs(guarded.database, gateway.database)
        self.assertIs(gateway.index_coordinator.semantic_provider, semantic)
        self.assertIsNot(guarded, gateway.index_coordinator.semantic_provider)
        self.assertEqual(gateway.runtime_warnings, [])
        self.assertIs(gateway.workspace, self.context)

        gateway.close()
        self.assertTrue(semantic.closed)
        self.assertTrue(embedding.closed)

    def test_semantic_disabled_preserves_explicit_lexical_only_mode(self):
        with patch("src.gateway.bootstrap.build_embedding_provider") as embedding_factory, patch(
            "src.gateway.bootstrap.QdrantSemanticProvider"
        ) as semantic_factory:
            gateway = build_memory_gateway(
                self.settings,
                rebuild_if_empty=False,
                workspace=self.context,
                runtime_values={"semantic_enabled": False},
            )

        self.assertIsNone(gateway.retriever.semantic_provider)
        self.assertIsNone(gateway.index_coordinator.semantic_provider)
        self.assertEqual(gateway.runtime_warnings, [])
        embedding_factory.assert_not_called()
        semantic_factory.assert_not_called()

    def test_semantic_initialization_failure_returns_lexical_gateway_with_warning(self):
        with patch(
            "src.gateway.bootstrap.build_embedding_provider",
            side_effect=RuntimeError("embedding configuration failed"),
        ):
            gateway = build_memory_gateway(
                self.settings,
                rebuild_if_empty=False,
                workspace=self.context,
            )

        self.assertIsNone(gateway.retriever.semantic_provider)
        self.assertIsNone(gateway.index_coordinator.semantic_provider)
        self.assertEqual(
            gateway.runtime_warnings[0]["code"],
            "semantic_runtime_initialization_failed",
        )
        self.assertIn("embedding configuration failed", gateway.runtime_warnings[0]["message"])

    def test_invalid_runtime_value_does_not_break_lexical_startup(self):
        gateway = build_memory_gateway(
            self.settings,
            rebuild_if_empty=False,
            workspace=self.context,
            runtime_values={"semantic_enabled": "not-a-boolean"},
        )

        self.assertIsNone(gateway.retriever.semantic_provider)
        self.assertTrue(gateway.runtime_warnings)
        self.assertIn("Invalid boolean value", gateway.runtime_warnings[0]["message"])

    def test_no_explicit_workspace_keeps_existing_production_vault_and_sqlite_paths(self):
        self.settings.vault_path.mkdir(parents=True, exist_ok=True)
        gateway = build_memory_gateway(
            self.settings,
            rebuild_if_empty=False,
            runtime_values={"semantic_enabled": False},
        )

        self.assertEqual(gateway.database.path, self.settings.memory_db_path)
        self.assertEqual(
            gateway.workspace.vault_path,
            self.settings.vault_path.resolve(strict=False),
        )
        self.assertEqual(
            gateway.workspace.memory_db_path,
            self.settings.memory_db_path.resolve(strict=False),
        )

    def test_semantic_query_failure_falls_back_to_lexical_results(self):
        embedding = FakeEmbeddingProvider()
        semantic = FakeSemanticProvider(fail_search=True)
        with patch("src.gateway.bootstrap.build_embedding_provider", return_value=embedding), patch(
            "src.gateway.bootstrap.QdrantSemanticProvider", return_value=semantic
        ):
            gateway = build_memory_gateway(
                self.settings,
                rebuild_if_empty=False,
                workspace=self.context,
            )

        relative_path = "03-Knowledge/runtime.md"
        path = self.context.vault_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        text = (
            "---\n"
            "id: MEM-RUNTIME\n"
            "memory_type: knowledge\n"
            "privacy: private\n"
            "agent_scope: [all]\n"
            "---\n"
            "# Runtime\n\nLexicalFallbackNeedle remains searchable.\n"
        )
        path.write_text(text, encoding="utf-8")
        entry = {
            "id": "MEM-RUNTIME",
            "relative_path": relative_path,
            "title": "Runtime fallback",
            "memory_type": "knowledge",
            "status": "active",
            "privacy": "private",
            "agent_scope": ["all"],
            "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }
        rebuild = gateway.rebuild([entry], self.context.vault_path, force=True)
        self.assertFalse(rebuild["degraded"])

        result = gateway.search_memory("lingji-local", "LexicalFallbackNeedle")
        self.assertTrue(result["results"])
        self.assertIn("lexical", result["results"][0]["retrieval_channels"])


if __name__ == "__main__":
    unittest.main()
