from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.retrieval import MemoryDatabase
from src.sources import SourceReadModel


class SourceReadModelTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.database = MemoryDatabase(Path(self.temp_dir.name) / "lingji_memory.db")
        self.read_model = SourceReadModel(self.database)

    def _bundle(self):
        return {
            "source": {
                "source_type": "chatgpt",
                "external_id": "export-1",
                "display_name": "ChatGPT Export",
                "privacy": "private",
                "projects": ["LingJi"],
                "raw_reference": "chatgpt/export.zip",
            },
            "conversations": [
                {
                    "external_id": "conversation-1",
                    "title": "Structured read model",
                    "started_at": "2026-07-20T10:00:00+00:00",
                    "messages": [
                        {
                            "external_id": "message-1",
                            "role": "user",
                            "sequence": 1,
                            "occurred_at": "2026-07-20T10:01:00+00:00",
                            "content": "Build the read model",
                        },
                        {
                            "external_id": "message-2",
                            "role": "assistant",
                            "sequence": 2,
                            "occurred_at": "2026-07-20T10:01:00+00:00",
                            "content": "Implemented safely",
                        },
                    ],
                }
            ],
        }

    def test_schema_migration_is_idempotent_and_indexes_exist(self):
        SourceReadModel(self.database)
        with self.database._connection() as connection:
            tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            indexes = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                ).fetchall()
            }
        self.assertTrue(
            {
                "source_records",
                "conversation_records",
                "message_records",
                "message_memory_links",
                "source_read_model_meta",
            }.issubset(tables)
        )
        self.assertIn("idx_message_conversation_time", indexes)
        self.assertEqual(self.read_model.schema_version(), "1")

    def test_stable_ids_and_repeated_upsert_do_not_duplicate(self):
        first = self.read_model.upsert_bundle(self._bundle())
        first_items = self.read_model.list_messages()["items"]
        second = self.read_model.upsert_bundle(self._bundle())
        second_items = self.read_model.list_messages()["items"]
        self.assertEqual(first["source_id"], second["source_id"])
        self.assertEqual(
            [item["message_id"] for item in first_items],
            [item["message_id"] for item in second_items],
        )
        self.assertEqual(self.read_model.stats()["sources"], 1)
        self.assertEqual(self.read_model.stats()["conversations"], 1)
        self.assertEqual(self.read_model.stats()["messages"], 2)

    def test_pagination_and_same_time_sort_are_stable(self):
        self.read_model.upsert_bundle(self._bundle())
        first = self.read_model.list_messages(limit=1, offset=0)
        second = self.read_model.list_messages(limit=1, offset=1)
        self.assertEqual(first["pagination"]["total"], 2)
        self.assertTrue(first["pagination"]["has_more"])
        self.assertEqual(first["items"][0]["sequence"], 2)
        self.assertEqual(second["items"][0]["sequence"], 1)
        with self.assertRaises(ValueError):
            self.read_model.list_messages(limit=201)
        with self.assertRaises(ValueError):
            self.read_model.list_messages(offset=-1)

    def test_filters_and_list_rows_do_not_return_full_content(self):
        self.read_model.upsert_bundle(self._bundle())
        page = self.read_model.list_messages(role="user", q="read model")
        self.assertEqual(page["pagination"]["total"], 1)
        self.assertNotIn("content", page["items"][0])
        self.assertEqual(page["items"][0]["content_preview"], "Build the read model")
        self.assertEqual(
            self.read_model.list_sources(project="LingJi")["pagination"]["total"], 1
        )
        self.assertEqual(
            self.read_model.list_conversations(source_type="chatgpt")["pagination"]["total"],
            1,
        )

    def test_foreign_keys_protect_links(self):
        self.read_model.upsert_bundle(self._bundle())
        message_id = self.read_model.list_messages()["items"][0]["message_id"]
        with self.assertRaises(sqlite3.IntegrityError):
            self.read_model.link_message_memory(message_id, "missing-memory")
        with self.database._connection() as connection:
            connection.execute(
                """
                INSERT INTO memory_documents(
                    memory_id, relative_path, title, content_hash, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                ("MEM-1", "memory.md", "Memory", "hash", "2026-07-20T10:00:00+00:00"),
            )
        self.read_model.link_message_memory(message_id, "MEM-1", confidence=0.9)
        self.assertEqual(self.read_model.memory_links("MEM-1")[0]["message_id"], message_id)


if __name__ == "__main__":
    unittest.main()
