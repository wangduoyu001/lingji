from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from src.extraction.adapters.chatgpt import ChatGPTExportAdapter
from src.extraction.pipeline import ExtractionPipeline
from src.extraction.queue import SQLiteExtractionQueue
from src.extraction.registry import AdapterRegistry
from src.extraction.sink import VaultExtractionSink
from src.memory import VaultLayout
from src.storage import StateDatabase


class ChatGPTImporterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.vault = root / "vault"
        self.storage = root / "storage"
        self.layout = VaultLayout(self.vault)
        self.layout.ensure()
        self.queue = SQLiteExtractionQueue(self.storage / "state.db")
        registry = AdapterRegistry()
        registry.register(ChatGPTExportAdapter())
        sink = VaultExtractionSink(
            self.layout,
            self.storage,
            state_db=StateDatabase(self.storage / "state.db"),
        )
        self.pipeline = ExtractionPipeline(self.queue, registry, sink)

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def _conversation():
        return {
            "id": "conv-123",
            "title": "灵机架构讨论",
            "create_time": 1700000000,
            "update_time": 1700000030,
            "current_node": "a-main",
            "mapping": {
                "u1": {
                    "id": "u1",
                    "parent": None,
                    "children": ["a-main", "a-branch"],
                    "message": {
                        "id": "m1",
                        "author": {"role": "user"},
                        "create_time": 1700000001,
                        "content": {"content_type": "text", "parts": ["设计统一提取框架"]},
                        "metadata": {},
                    },
                },
                "a-main": {
                    "id": "a-main",
                    "parent": "u1",
                    "children": [],
                    "message": {
                        "id": "m2",
                        "author": {"role": "assistant"},
                        "create_time": 1700000002,
                        "content": {"content_type": "text", "parts": ["采用适配器与队列。"]},
                        "metadata": {"model_slug": "gpt-test"},
                    },
                },
                "a-branch": {
                    "id": "a-branch",
                    "parent": "u1",
                    "children": [],
                    "message": {
                        "id": "m3",
                        "author": {"role": "assistant"},
                        "create_time": 1700000003,
                        "content": {"content_type": "text", "parts": ["这是另一条分支。"]},
                        "metadata": {},
                    },
                },
            },
        }

    def test_import_json_through_queue(self):
        export = Path(self.temp_dir.name) / "conversations.json"
        export.write_text(json.dumps([self._conversation()], ensure_ascii=False), encoding="utf-8")
        job = self.pipeline.enqueue("chatgpt", input_path=export, adapter_name="chatgpt_export")
        outcome = self.pipeline.process_job(job["job_id"])
        self.assertEqual(outcome["job"]["status"], "completed")
        created = outcome["result"]["created"]
        self.assertEqual(len(created), 1)
        note = Path(created[0]["path"])
        self.assertTrue(note.exists())
        text = note.read_text(encoding="utf-8")
        self.assertIn("灵机架构讨论", text)
        self.assertIn("分支消息", text)
        self.assertIn("gpt-test", text)
        self.assertIn("02-Sources/Conversations/ChatGPT", note.as_posix())
        self.assertTrue(Path(outcome["result"]["raw_snapshot"]["raw_path"]).exists())

    def test_import_zip_and_deduplicate_enqueue(self):
        archive = Path(self.temp_dir.name) / "export.zip"
        with zipfile.ZipFile(archive, "w") as zip_file:
            zip_file.writestr(
                "conversations.json",
                json.dumps([self._conversation()], ensure_ascii=False),
            )
        first = self.pipeline.enqueue("chatgpt", input_path=archive)
        second = self.pipeline.enqueue("chatgpt", input_path=archive)
        self.assertEqual(first["job_id"], second["job_id"])
        outcome = self.pipeline.process_job(first["job_id"])
        self.assertEqual(outcome["result"]["summary"]["documents_created"], 1)

    def test_same_export_with_different_project_is_distinct(self):
        export = Path(self.temp_dir.name) / "conversations.json"
        export.write_text(json.dumps([self._conversation()], ensure_ascii=False), encoding="utf-8")
        first = self.pipeline.enqueue(
            "chatgpt",
            input_path=export,
            options={"project_id": "LingJi"},
        )
        second = self.pipeline.enqueue(
            "chatgpt",
            input_path=export,
            options={"project_id": "Drama"},
        )
        self.assertNotEqual(first["job_id"], second["job_id"])

    def test_sensitive_conversation_goes_to_private_imports(self):
        conversation = self._conversation()
        conversation["mapping"]["u1"]["message"]["content"]["parts"] = [
            "api_key = sk-example-secret-1234567890"
        ]
        export = Path(self.temp_dir.name) / "conversations.json"
        export.write_text(json.dumps([conversation], ensure_ascii=False), encoding="utf-8")
        result = self.pipeline.execute("chatgpt", input_path=export)
        note = Path(result["created"][0]["path"])
        self.assertIn("08-Private/Imports/chatgpt", note.as_posix())
        self.assertEqual(result["summary"]["restricted_documents"], 1)

    def test_conversation_limit_is_enforced_for_zip_exports(self):
        archive = Path(self.temp_dir.name) / "limited.zip"
        with zipfile.ZipFile(archive, "w") as zip_file:
            zip_file.writestr(
                "conversations.json",
                json.dumps([self._conversation()], ensure_ascii=False),
            )
        with self.assertRaises(ValueError):
            self.pipeline.execute(
                "chatgpt",
                input_path=archive,
                options={"max_conversations": 0},
            )

    def test_single_json_size_limit_is_enforced(self):
        export = Path(self.temp_dir.name) / "conversations.json"
        export.write_text(json.dumps([self._conversation()], ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.pipeline.execute(
                "chatgpt",
                input_path=export,
                options={"max_zip_member_bytes": 1},
            )


if __name__ == "__main__":
    unittest.main()
