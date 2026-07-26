from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.extraction.adapters.web import WebCaptureAdapter
from src.extraction.pipeline import ExtractionPipeline
from src.extraction.queue import SQLiteExtractionQueue
from src.extraction.registry import AdapterRegistry
from src.extraction.sink import VaultExtractionSink
from src.memory import VaultLayout


class WebCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.vault = root / "vault"
        self.storage = root / "storage"
        layout = VaultLayout(self.vault)
        layout.ensure()
        registry = AdapterRegistry()
        registry.register(WebCaptureAdapter())
        self.pipeline = ExtractionPipeline(
            SQLiteExtractionQueue(self.storage / "state.db"),
            registry,
            VaultExtractionSink(layout, self.storage),
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_video_channel_payload_is_routed_and_indexed(self):
        result = self.pipeline.execute(
            "video_channel",
            payload={
                "url": "https://channels.weixin.qq.com/example",
                "title": "视频号案例",
                "account_name": "灵机研究所",
                "description": "介绍一个新的AI工作流。",
                "duration_seconds": 95,
                "transcript": "这是一段视频转写内容。",
                "platform": "video_channel",
            },
            adapter_name="web_capture",
        )
        self.assertEqual(result["documents"], 1)
        path = Path(result["created"][0]["path"])
        self.assertIn("Video-Channels", path.as_posix())
        text = path.read_text(encoding="utf-8")
        self.assertIn("灵机研究所", text)
        self.assertIn("视频/音频转写", text)
        self.assertEqual(result["summary"]["content_completeness"], "content")

    def test_metadata_only_capture_requests_review(self):
        result = self.pipeline.execute(
            "xiaohongshu",
            payload={
                "url": "https://www.xiaohongshu.com/explore/example",
                "title": "只有分享链接",
                "platform": "xiaohongshu",
            },
            adapter_name="web_capture",
        )
        self.assertEqual(result["summary"]["content_completeness"], "metadata_only")
        self.assertTrue(result["warnings"])
        text = Path(result["created"][0]["path"]).read_text(encoding="utf-8")
        self.assertIn("status: needs_review", text)

    def test_sensitive_web_capture_goes_to_private_imports(self):
        result = self.pipeline.execute(
            "web",
            payload={
                "url": "https://example.com/private",
                "title": "敏感页面",
                "text": "api_key = sk-example-secret-1234567890",
            },
            adapter_name="web_capture",
        )
        path = Path(result["created"][0]["path"])
        self.assertIn("08-Private/Imports", path.as_posix())
        self.assertEqual(result["created"][0]["privacy"], "restricted")

    def test_html_metadata_and_text_extraction(self):
        html = """
        <html><head><title>测试文章</title>
        <meta name="author" content="作者甲">
        <meta property="og:description" content="摘要">
        </head><body><article><h1>标题</h1><p>正文第一段。</p></article></body></html>
        """
        result = self.pipeline.execute(
            "web",
            payload={"url": "https://example.com/a", "html": html},
            adapter_name="web_capture",
        )
        text = Path(result["created"][0]["path"]).read_text(encoding="utf-8")
        self.assertIn("测试文章", text)
        self.assertIn("作者甲", text)
        self.assertIn("正文第一段", text)


if __name__ == "__main__":
    unittest.main()
