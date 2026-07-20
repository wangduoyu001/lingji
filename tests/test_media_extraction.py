from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.extraction.adapters.media import MediaExtractionAdapter
from src.extraction.pipeline import ExtractionPipeline
from src.extraction.queue import SQLiteExtractionQueue
from src.extraction.registry import AdapterRegistry
from src.extraction.sink import VaultExtractionSink
from src.memory import VaultLayout


class _ProcessResult:
    def __init__(self, stdout: str = ""):
        self.stdout = stdout
        self.stderr = ""
        self.returncode = 0


class MediaExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.vault = root / "vault"
        self.storage = root / "storage"
        self.video = root / "sample.mp4"
        self.video.write_bytes(b"fake-video-data")
        layout = VaultLayout(self.vault)
        layout.ensure()
        registry = AdapterRegistry()
        registry.register(MediaExtractionAdapter(self.storage))
        self.pipeline = ExtractionPipeline(
            SQLiteExtractionQueue(self.storage / "state.db"),
            registry,
            VaultExtractionSink(layout, self.storage),
        )
        self.probe = {
            "format": {"duration": "12.5", "format_name": "mov,mp4", "bit_rate": "800000"},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "avg_frame_rate": "25/1",
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": "48000",
                    "channels": 2,
                },
            ],
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def _run(self, payload=None, options=None):
        with patch("src.extraction.adapters.media.shutil.which", return_value="ffprobe"), patch(
            "src.extraction.adapters.media.subprocess.run",
            return_value=_ProcessResult(json.dumps(self.probe)),
        ):
            return self.pipeline.execute(
                "media",
                input_path=self.video,
                payload=payload or {},
                options=options or {},
                adapter_name="media_local",
            )

    def test_video_metadata_and_transcript_are_written(self):
        result = self._run(payload={"title": "示例视频", "transcript": "这是完整转写。"})
        path = Path(result["created"][0]["path"])
        self.assertIn("02-Sources/Videos", path.as_posix())
        text = path.read_text(encoding="utf-8")
        self.assertIn("示例视频", text)
        self.assertIn("12.5", text)
        self.assertIn("1920", text)
        self.assertIn("这是完整转写", text)
        self.assertEqual(result["summary"]["semantic_status"], "provided")

    def test_metadata_only_media_requires_review(self):
        result = self._run()
        text = Path(result["created"][0]["path"]).read_text(encoding="utf-8")
        self.assertIn("status: needs_review", text)
        self.assertIn("当前只完成媒体元数据提取", text)
        self.assertEqual(result["summary"]["semantic_status"], "metadata_only")

    def test_sensitive_transcript_is_routed_private(self):
        result = self._run(payload={"transcript": "password: super-secret-password"})
        path = Path(result["created"][0]["path"])
        self.assertIn("08-Private/Imports/video", path.as_posix())
        self.assertTrue(result["summary"]["restricted"])

    def test_ffmpeg_command_uses_owner_configured_threads_and_dimension(self):
        calls = []

        def fake_run(command, **kwargs):
            calls.append(command)
            if "-show_format" in command:
                return _ProcessResult(json.dumps(self.probe))
            return _ProcessResult("")

        with patch("src.extraction.adapters.media.shutil.which", return_value="ffmpeg"), patch(
            "src.extraction.adapters.media.subprocess.run",
            side_effect=fake_run,
        ):
            self.pipeline.execute(
                "media",
                input_path=self.video,
                options={
                    "extract_keyframes": True,
                    "max_keyframes": 9,
                    "keyframe_max_dimension": 2048,
                    "ffmpeg_threads": 3,
                    "ffmpeg_max_concurrency": 2,
                },
                adapter_name="media_local",
            )
        ffmpeg_call = next(command for command in calls if "-frames:v" in command)
        self.assertIn("-threads", ffmpeg_call)
        self.assertEqual(ffmpeg_call[ffmpeg_call.index("-threads") + 1], "3")
        self.assertEqual(ffmpeg_call[ffmpeg_call.index("-frames:v") + 1], "9")
        filter_value = ffmpeg_call[ffmpeg_call.index("-vf") + 1]
        self.assertIn("scale=2048:2048", filter_value)

    def test_input_size_limit_rejects_before_processing(self):
        with self.assertRaisesRegex(ValueError, "超过当前限制"):
            self.pipeline.execute(
                "media",
                input_path=self.video,
                options={"max_input_bytes": 1},
                adapter_name="media_local",
            )

    def test_duration_limit_rejects_after_probe(self):
        with patch("src.extraction.adapters.media.shutil.which", return_value="ffprobe"), patch(
            "src.extraction.adapters.media.subprocess.run",
            return_value=_ProcessResult(json.dumps(self.probe)),
        ):
            with self.assertRaisesRegex(ValueError, "媒体时长"):
                self.pipeline.execute(
                    "media",
                    input_path=self.video,
                    options={"max_duration_seconds": 10},
                    adapter_name="media_local",
                )


if __name__ == "__main__":
    unittest.main()
