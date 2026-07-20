from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.gateway import MemoryInspectorFacade
from src.gateway.profiles import AIProfileRegistry
from src.retrieval import MemoryDatabase
from src.sources import SourceQueryService, SourceReadModel


class FakeStatistics:
    def __init__(self, workspace="acceptance", rebuild_required=False):
        self.workspace = workspace
        self.rebuild_required = rebuild_required

    def memory_status(self):
        return {
            "state": "healthy",
            "workspace": self.workspace,
            "documents": 1,
            "chunks": 1,
            "revision": 1,
        }

    def vector_status(self):
        return {
            "state": "healthy",
            "source": "live",
            "workspace": self.workspace,
            "collection": "acceptance_vectors",
            "dimension": 1024,
            "rebuild_required": self.rebuild_required,
            "last_error": None,
        }


class FakeSemantic:
    def __init__(self, existing=True, error=None):
        self.existing = existing
        self.error = error

    def exists(self, chunk_id):
        if self.error:
            raise RuntimeError(self.error)
        return self.existing


class MemoryInspectorFacadeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self.database = MemoryDatabase(root / "acceptance" / "lingji_memory.db")
        with self.database._connection() as connection:
            connection.execute(
                """
                INSERT INTO memory_documents(
                    memory_id, relative_path, title, memory_type, privacy,
                    project_json, agent_scope_json, content_hash, modified_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "MEM-1",
                    "03-Knowledge/test.md",
                    "Test memory",
                    "knowledge",
                    "private",
                    '["LingJi"]',
                    '["all"]',
                    "doc-hash",
                    "2026-07-20T10:00:00+00:00",
                    "2026-07-20T10:00:00+00:00",
                ),
            )
            connection.execute(
                """
                INSERT INTO memory_chunks(
                    chunk_id, memory_id, ordinal, heading, text, start_line,
                    end_line, char_count, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "CHUNK-1",
                    "MEM-1",
                    0,
                    "Heading",
                    "Canonical memory text",
                    3,
                    5,
                    21,
                    "chunk-hash",
                ),
            )
        self.read_model = SourceReadModel(self.database)
        self.read_model.upsert_bundle(
            {
                "source": {
                    "source_type": "chatgpt",
                    "external_id": "export-1",
                    "display_name": "ChatGPT",
                },
                "conversations": [
                    {
                        "external_id": "conversation-1",
                        "title": "Conversation",
                        "messages": [
                            {
                                "external_id": "message-1",
                                "role": "user",
                                "sequence": 1,
                                "content": "Source message",
                                "memory_links": [{"memory_id": "MEM-1"}],
                            }
                        ],
                    }
                ],
            }
        )
        source_service = SourceQueryService(
            self.read_model,
            workspace="acceptance",
            vault_path=root / "vault",
            raw_path=root / "raw",
            profiles=AIProfileRegistry(),
        )
        gateway = SimpleNamespace(
            retriever=SimpleNamespace(semantic_provider=FakeSemantic(existing=True))
        )
        self.facade = MemoryInspectorFacade(
            self.database,
            source_service,
            FakeStatistics(),
            gateway=gateway,
            workspace="acceptance",
        )

    def test_memory_list_reuses_canonical_database_and_filters(self):
        response = self.facade.list_memories(
            memory_type="knowledge", project="LingJi", q="Test"
        )
        self.assertEqual(response["workspace"], "acceptance")
        self.assertEqual(response["pagination"]["total"], 1)
        self.assertEqual(response["items"][0]["memory_id"], "MEM-1")

    def test_memory_detail_contains_chunks_and_citations(self):
        response = self.facade.get_memory("MEM-1")
        self.assertEqual(response["item"]["chunks"][0]["chunk_id"], "CHUNK-1")
        self.assertEqual(response["item"]["citations"][0]["start_line"], 3)
        with self.assertRaises(LookupError):
            self.facade.get_memory("missing")

    def test_message_memory_linkage_is_read_only(self):
        response = self.facade.memory_source("MEM-1")
        self.assertEqual(len(response["links"]), 1)
        self.assertNotIn("content", response["links"][0])
        self.assertEqual(response["links"][0]["content_preview"], "Source message")

    def test_live_vector_linkage_returns_boolean_without_raw_vector(self):
        response = self.facade.memory_vector("MEM-1")
        chunk = response["vector"]["chunks"][0]
        self.assertTrue(chunk["exists"])
        self.assertEqual(chunk["source"], "live")
        self.assertNotIn("vector", chunk)
        self.assertNotIn("payload", chunk)

    def test_missing_live_provider_returns_unknown_not_false(self):
        facade = MemoryInspectorFacade(
            self.database,
            self.facade.source_service,
            FakeStatistics(),
            gateway=None,
            workspace="acceptance",
        )
        chunk = facade.memory_vector("MEM-1")["vector"]["chunks"][0]
        self.assertIsNone(chunk["exists"])
        self.assertEqual(chunk["source"], "unavailable")

    def test_rebuild_required_none_remains_unknown_at_all_levels(self):
        facade = MemoryInspectorFacade(
            self.database,
            self.facade.source_service,
            FakeStatistics(rebuild_required=None),
            gateway=None,
            workspace="acceptance",
        )
        response = facade.memory_vector("MEM-1")
        self.assertIsNone(response["vector"]["rebuild_required"])
        self.assertIsNone(response["vector"]["chunks"][0]["rebuild_required"])

    def test_production_and_acceptance_database_are_isolated(self):
        root = Path(self.temp_dir.name)
        production_db = MemoryDatabase(root / "production" / "lingji_memory.db")
        production_model = SourceReadModel(production_db)
        self.assertEqual(production_model.stats()["sources"], 0)
        self.assertEqual(self.read_model.stats()["sources"], 1)


if __name__ == "__main__":
    unittest.main()
