from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

from second_brain.config import Settings
from second_brain.models import ChatMessage, ConversationInput
from second_brain.runtime import build_runtime
from second_brain.api import app


ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = ROOT / "data" / "test-runtime"


class FakeEmbedder:
    active_model = "fake"

    @staticmethod
    def embed(text: str) -> list[float]:
        base = float((sum(text.encode("utf-8")) % 100) + 1)
        return [base / 100.0, 0.25, 0.5, 0.75]

    @staticmethod
    def status() -> dict:
        return {"active_model": "fake"}


class SecondBrainTests(unittest.TestCase):
    def setUp(self) -> None:
        if TEST_ROOT.exists():
            shutil.rmtree(TEST_ROOT)
        obsidian_root = TEST_ROOT / "obsidian"
        obsidian_root.mkdir(parents=True, exist_ok=True)
        config = Settings(
            database_path=TEST_ROOT / "memory.sqlite3",
            raw_archive_dir=TEST_ROOT / "raw",
            ai_inbox_dir=TEST_ROOT / "ai",
            codex_inbox_dir=TEST_ROOT / "codex",
            qdrant_path=Path(":memory:"),
            qdrant_url="",
            qdrant_collection="test_memories",
            obsidian_knowledge_dir=obsidian_root,
            log_dir=TEST_ROOT / "logs",
            runtime_dir=TEST_ROOT / "runtime",
        )
        self.runtime = build_runtime(config)
        self.runtime.embedder = FakeEmbedder()
        self.runtime.memories.embedder = self.runtime.embedder
        self.runtime.retrieval.embedder = self.runtime.embedder
        self.runtime.obsidian.embedder = self.runtime.embedder

    def tearDown(self) -> None:
        self.runtime.close()
        if TEST_ROOT.exists():
            shutil.rmtree(TEST_ROOT)

    def test_duplicate_chat_import_is_idempotent(self) -> None:
        conversation = ConversationInput(
            conversation_id="chat-1",
            source="chatgpt",
            title="Rules",
            project="lingji",
            messages=[ChatMessage(role="user", content="以后必须先备份再升级。")],
        )
        first = self.runtime.chats.import_conversation(conversation)
        second = self.runtime.chats.import_conversation(conversation)
        self.assertTrue(first["imported"])
        self.assertTrue(second["duplicate"])
        with self.runtime.database.connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM conversations").fetchone()[0], 1)

    def test_new_rule_supersedes_old_rule(self) -> None:
        old, _ = self.runtime.memories.create("RULE", "镜头规则", "15秒最多一个动作", "ai-director", "active")
        result = self.runtime.memories.supersede(
            old["id"], None,
            {"memory_type": "RULE", "title": "镜头规则", "content": "动作数量根据剧情灵活调整", "project": "ai-director"},
            "user confirmed newer rule",
        )
        self.assertEqual(result["old"]["status"], "superseded")
        self.assertEqual(result["new"]["status"], "active")
        self.assertEqual(result["new"]["supersedes_id"], old["id"])

    def test_qdrant_rebuild_from_sqlite(self) -> None:
        memory, _ = self.runtime.memories.create("DECISION", "Vector store", "Use isolated Qdrant", "lingji", "active")
        stale, _ = self.runtime.memories.create("RULE", "Stale rule", "Do not retain", "lingji", "active")
        self.runtime.memories.set_status(stale["id"], "conflicted", "test conflict")
        rebuilt = self.runtime.memories.rebuild_vectors()
        self.assertEqual(rebuilt, 1)
        self.assertEqual(self.runtime.vectors.status()["vectors"], 1)
        hits = self.runtime.vectors.search(self.runtime.embedder.embed(memory["content"]), limit=3)
        self.assertEqual(hits[0]["id"], memory["id"])

    def test_obsidian_is_chunked_without_memory_distillation(self) -> None:
        note = self.runtime.settings.obsidian_knowledge_dir / "project" / "long-note.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text("# Formal Knowledge\n\n#manual\n\n" + ("人工确认的知识段落。" * 400), encoding="utf-8")
        result = self.runtime.obsidian.index_file(note)
        self.assertGreater(result["chunks"], 1)
        with self.runtime.database.connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM knowledge_documents").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0], 0)
        self.assertEqual(self.runtime.vectors.status()["vectors"], result["chunks"])
        self.runtime.vectors.client.delete_collection(self.runtime.vectors.collection)
        self.assertEqual(self.runtime.memories.rebuild_vectors(), result["chunks"])

    def test_second_brain_is_not_in_original_start_chain(self) -> None:
        startup = "\n".join((ROOT / name).read_text(encoding="utf-8-sig") for name in ("start_lingji.py", "run_service.py"))
        self.assertNotIn("second_brain", startup)
        result = subprocess.run(
            ["python", "-c", "from main import PEMISCore; PEMISCore(); print('ORIGINAL_INIT_OK')"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertIn("ORIGINAL_INIT_OK", result.stdout)

    def test_required_api_routes_exist(self) -> None:
        required = {
            ("POST", "/memory/import"), ("POST", "/memory/search"),
            ("POST", "/memory/context"), ("POST", "/memory/distill"),
            ("POST", "/memory/approve"), ("POST", "/memory/reject"),
            ("POST", "/memory/supersede"), ("POST", "/memory/codex-task"),
            ("GET", "/memory/status"), ("GET", "/memory/conflicts"),
            ("GET", "/memory/pending"), ("GET", "/memory/projects"),
            ("GET", "/memory/timeline"), ("GET", "/memory/source/{source_id}"),
            ("GET", "/system/status"), ("GET", "/system/watcher/status"),
            ("POST", "/system/watcher/start"), ("POST", "/system/watcher/stop"),
            ("POST", "/system/watcher/scan-once"), ("GET", "/system/logs"),
            ("GET", "/memory/list"), ("GET", "/memory/{memory_id}"),
            ("GET", "/memory/tasks"), ("POST", "/memory/conflicts/{conflict_id}/resolve"),
            ("GET", "/knowledge/documents"), ("GET", "/knowledge/documents/{document_id}"),
            ("POST", "/acceptance/reset"), ("POST", "/acceptance/seed"),
            ("POST", "/acceptance/run-all"), ("POST", "/acceptance/run/{scenario}"),
            ("GET", "/acceptance/results/latest"),
        }
        actual = {(method, route.path) for route in app.routes for method in getattr(route, "methods", set())}
        self.assertTrue(required.issubset(actual))


if __name__ == "__main__":
    unittest.main()
