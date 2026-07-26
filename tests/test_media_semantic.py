from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.media import MediaSemanticService, ProviderUnavailableError


class MediaSemanticTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.storage = root / "storage"
        self.media = root / "sample.mp4"
        self.media.write_bytes(b"sample-video")
        self.frames = root / "frames"
        self.frames.mkdir()
        (self.frames / "frame-00001.jpg").write_bytes(b"image")
        self.service = MediaSemanticService(self.storage)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_all_enabled_providers_are_persisted(self):
        with patch(
            "src.media.semantic.FasterWhisperProvider.transcribe",
            return_value={
                "provider": "faster_whisper",
                "model": "small",
                "language": "zh",
                "text": "测试转写",
                "segments": [{"start": 0.0, "end": 1.0, "text": "测试转写"}],
            },
        ), patch(
            "src.media.semantic.PaddleOCRProvider.recognize",
            return_value={
                "provider": "paddleocr",
                "language": "ch",
                "text": "画面文字",
                "images": [{"image": "frame.jpg", "text": "画面文字", "lines": []}],
            },
        ), patch(
            "src.media.semantic.PySceneDetectProvider.detect",
            return_value={
                "provider": "pyscenedetect",
                "scene_count": 1,
                "scenes": [{"index": 1, "start_seconds": 0.0, "end_seconds": 2.0}],
            },
        ):
            result = self.service.analyze(
                self.media,
                {
                    "auto_transcribe": True,
                    "asr_provider": "faster_whisper",
                    "auto_ocr": True,
                    "ocr_provider": "paddleocr",
                    "detect_scenes": True,
                    "scene_provider": "pyscenedetect",
                },
                keyframe_directory=self.frames,
            )
        self.assertEqual(result["semantic_status"], "provided")
        self.assertIn("asr", result["providers"])
        self.assertIn("ocr", result["providers"])
        self.assertIn("scenes", result["providers"])
        target = Path(result["target_directory"])
        self.assertTrue((target / "transcript.md").exists())
        self.assertTrue((target / "ocr.txt").exists())
        self.assertTrue((target / "scenes.json").exists())
        self.assertTrue((target / "summary.json").exists())

    def test_missing_optional_provider_becomes_warning(self):
        with patch(
            "src.media.semantic.FasterWhisperProvider.transcribe",
            side_effect=ProviderUnavailableError("missing faster-whisper"),
        ):
            result = self.service.analyze(
                self.media,
                {"auto_transcribe": True, "asr_provider": "faster_whisper"},
            )
        self.assertEqual(result["semantic_status"], "metadata_only")
        self.assertIn("missing faster-whisper", result["warnings"])

    def test_ocr_without_keyframes_does_not_fail_task(self):
        result = self.service.analyze(
            self.media,
            {"auto_ocr": True, "ocr_provider": "paddleocr"},
        )
        self.assertEqual(result["semantic_status"], "metadata_only")
        self.assertTrue(any("没有可用关键帧" in warning for warning in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
