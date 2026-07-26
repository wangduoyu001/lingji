from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.extraction.adapters.web import WebCaptureAdapter
from src.extraction.pipeline import ExtractionPipeline
from src.extraction.queue import SQLiteExtractionQueue
from src.extraction.registry import AdapterRegistry
from src.extraction.requests import ExtractionRequestInbox
from src.extraction.sink import VaultExtractionSink
from src.memory import VaultLayout
from src.obsidian import LingJiSystemUI
from src.skills import SkillRegistry


class SystemUITests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.layout = VaultLayout(root / "vault")
        self.layout.ensure()
        registry = AdapterRegistry()
        registry.register(WebCaptureAdapter())
        self.pipeline = ExtractionPipeline(
            SQLiteExtractionQueue(root / "storage" / "state.db"),
            registry,
            VaultExtractionSink(self.layout, root / "storage"),
        )
        self.skills = SkillRegistry(self.layout)
        self.requests = ExtractionRequestInbox(self.layout, self.pipeline, self.skills)
        self.ui = LingJiSystemUI(self.layout, self.pipeline, self.skills, self.requests)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_ensure_creates_bases_templates_and_centers(self):
        result = self.ui.ensure()
        self.assertTrue(result["created"])
        expected = [
            "00-System/Extraction-Center.md",
            "00-System/Skills-Center.md",
            "00-System/Bases/Extraction Sources.base",
            "00-System/Bases/Skills.base",
            "00-System/Bases/Extraction Requests.base",
            "00-System/Templates/ChatGPT导入请求.md",
            "00-System/Templates/网页与视频号采集请求.md",
        ]
        for relative in expected:
            self.assertTrue((self.layout.root / relative).exists(), relative)
        center = (self.layout.root / "00-System/Extraction-Center.md").read_text(encoding="utf-8")
        self.assertIn("视频号", center)
        self.assertIn("web_capture", center)

    def test_request_inbox_captures_video_channel_note(self):
        path = self.requests.queue_dir / "video.md"
        path.write_text(
            """---
memory_type: extraction_request
request_type: web_capture
status: queued
source_type: video_channel
platform: video_channel
source_url: https://channels.weixin.qq.com/example
title: 视频号测试
account_name: 测试账号
---

这里是人工补充的简介。
""",
            encoding="utf-8",
        )
        result = self.requests.process_pending()
        self.assertEqual(result["succeeded"], 1)
        self.assertIn("status: done", path.read_text(encoding="utf-8"))
        captures = list((self.layout.root / "02-Sources/Web/Video-Channels").rglob("*.md"))
        self.assertEqual(len(captures), 1)


if __name__ == "__main__":
    unittest.main()
