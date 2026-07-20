from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.config import Settings
from src.control import RuntimeSettingsStore
from src.extraction.adapters.media import MediaExtractionAdapter
from src.extraction.pipeline import ExtractionPipeline
from src.extraction.queue import SQLiteExtractionQueue
from src.extraction.registry import AdapterRegistry
from src.extraction.sink import VaultExtractionSink
from src.memory import VaultLayout


class RuntimeSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.settings = Settings(
            _env_file=None,
            vault_dir=str(root / "vault"),
            storage_dir=str(root / "storage"),
            log_dir=str(root / "logs"),
            backup_dir=str(root / "backup"),
        )
        self.store = RuntimeSettingsStore(self.settings)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_defaults_are_exposed_for_local_ui(self):
        snapshot = self.store.snapshot()
        self.assertEqual(snapshot["values"]["media_max_keyframes"], 500)
        self.assertEqual(snapshot["values"]["media_keyframe_max_dimension"], 1280)
        self.assertIn("definitions", snapshot)
        self.assertFalse(
            snapshot["definitions"]["media_ffmpeg_threads"]["restart_required"]
        )

    def test_owner_overrides_persist_and_convert_to_adapter_options(self):
        self.store.update(
            {
                "media_max_keyframes": 777,
                "media_keyframe_max_dimension": 1920,
                "media_ffmpeg_threads": 4,
                "media_ffmpeg_max_concurrency": 2,
                "media_max_input_gb": 3.5,
                "media_max_duration_minutes": 90,
                "media_default_priority": 25,
            }
        )
        reloaded = RuntimeSettingsStore(self.settings)
        options = reloaded.options_for_source("video")
        self.assertEqual(options["max_keyframes"], 777)
        self.assertEqual(options["keyframe_max_dimension"], 1920)
        self.assertEqual(options["ffmpeg_threads"], 4)
        self.assertEqual(options["ffmpeg_max_concurrency"], 2)
        self.assertEqual(options["max_input_bytes"], int(3.5 * 1024**3))
        self.assertEqual(options["max_duration_seconds"], 5400)
        self.assertEqual(reloaded.priority_for_source("media"), 25)

    def test_invalid_override_is_rejected(self):
        with self.assertRaises(ValueError):
            self.store.update({"media_ffmpeg_max_concurrency": 0})
        with self.assertRaises(KeyError):
            self.store.update({"unknown_setting": 1})

    def test_pipeline_uses_live_defaults_but_allows_task_override(self):
        layout = VaultLayout(self.settings.vault_path)
        layout.ensure()
        registry = AdapterRegistry()
        registry.register(MediaExtractionAdapter(self.settings.storage_path))
        pipeline = ExtractionPipeline(
            SQLiteExtractionQueue(self.settings.state_db_path),
            registry,
            VaultExtractionSink(layout, self.settings.storage_path),
            default_options_provider=self.store.options_for_source,
            default_priority_provider=self.store.priority_for_source,
        )
        video = Path(self.temp_dir.name) / "video.mp4"
        video.write_bytes(b"video")
        self.store.update({"media_max_keyframes": 650, "media_default_priority": 30})
        default_job = pipeline.enqueue("media", input_path=video, adapter_name="media_local")
        self.assertEqual(default_job["options"]["max_keyframes"], 650)
        self.assertEqual(default_job["priority"], 30)
        override_job = pipeline.enqueue(
            "media",
            input_path=video,
            options={"max_keyframes": 12},
            adapter_name="media_local",
            force=True,
        )
        self.assertEqual(override_job["options"]["max_keyframes"], 12)


if __name__ == "__main__":
    unittest.main()
