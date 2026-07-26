from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.extraction.adapters.codex import CodexWorkReportAdapter
from src.extraction.pipeline import ExtractionPipeline
from src.extraction.queue import SQLiteExtractionQueue
from src.extraction.registry import AdapterRegistry
from src.extraction.sink import VaultExtractionSink
from src.memory import VaultLayout
from src.storage import StateDatabase


class CodexWritebackTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.vault = root / "vault"
        self.storage = root / "storage"
        layout = VaultLayout(self.vault)
        layout.ensure()
        queue = SQLiteExtractionQueue(self.storage / "state.db")
        registry = AdapterRegistry()
        registry.register(CodexWorkReportAdapter())
        sink = VaultExtractionSink(
            layout,
            self.storage,
            state_db=StateDatabase(self.storage / "state.db"),
        )
        self.pipeline = ExtractionPipeline(queue, registry, sink)

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def _report():
        return {
            "task_id": "task-001",
            "project_id": "LingJi",
            "title": "统一提取框架第一阶段",
            "repository": "wangduoyu001/lingji",
            "branch": "feature/single-vault-memory-foundation",
            "summary": "完成SQLite队列、ChatGPT导入器和Codex写回。",
            "status": "completed",
            "started_at": "2026-07-19T10:00:00",
            "completed_at": "2026-07-19T11:00:00",
            "changed_files": ["src/extraction/queue.py", "src/extraction/pipeline.py"],
            "tests": ["python -m unittest discover -s tests -v"],
            "test_result": "全部通过",
            "commits": ["abc123"],
            "pull_requests": ["https://github.com/example/repo/pull/1"],
            "errors": [{"title": "导出文件缺失", "message": "没有conversations.json"}],
            "decisions": [{"title": "复用状态数据库", "reason": "避免双数据库"}],
            "remaining_tasks": [{"title": "增加浏览器扩展", "priority": "medium"}],
        }

    def test_writes_report_and_candidates(self):
        result = self.pipeline.execute("codex", payload=self._report())
        self.assertEqual(result["documents"], 4)
        self.assertEqual(len(result["created"]), 4)
        paths = [Path(item["path"]) for item in result["created"]]
        self.assertTrue(any("Work-Reports" in path.as_posix() for path in paths))
        self.assertTrue(any("Errors" in path.as_posix() for path in paths))
        self.assertTrue(any("Decisions/Candidates" in path.as_posix() for path in paths))
        self.assertTrue(any("Tasks/Inbox" in path.as_posix() for path in paths))
        report = next(path for path in paths if "Work-Reports" in path.as_posix())
        text = report.read_text(encoding="utf-8")
        self.assertIn("完成SQLite队列", text)
        self.assertIn("abc123", text)
        self.assertIn("执行ID", text)

    def test_repeated_write_is_idempotent(self):
        first = self.pipeline.execute("codex", payload=self._report())
        second = self.pipeline.execute("codex", payload=self._report())
        self.assertEqual(len(first["created"]), 4)
        self.assertEqual(len(second["skipped"]), 4)

    def test_new_execution_keeps_previous_report(self):
        first_report = self._report()
        first_report["execution_id"] = "run-001"
        second_report = self._report()
        second_report["execution_id"] = "run-002"
        second_report["completed_at"] = "2026-07-19T12:00:00"
        second_report["summary"] = "第二次执行完成兼容性修复。"
        first = self.pipeline.execute("codex", payload=first_report)
        second = self.pipeline.execute("codex", payload=second_report)
        self.assertEqual(len(first["created"]), 4)
        self.assertGreaterEqual(len(second["created"]), 1)
        reports = list((self.vault / "05-Operations/Work-Reports/LingJi").rglob("*.md"))
        self.assertEqual(len(reports), 2)
        contents = "\n".join(path.read_text(encoding="utf-8") for path in reports)
        self.assertIn("run-001", contents)
        self.assertIn("run-002", contents)


if __name__ == "__main__":
    unittest.main()
