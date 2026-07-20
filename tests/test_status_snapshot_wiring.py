from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.config import Settings
from src.gateway.bootstrap import build_memory_gateway
from src.gateway.memory_statistics import MemoryStatisticsService
from src.runtime import WorkspaceResolver


class StatusSnapshotWiringTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.settings = Settings(
            _env_file=None,
            workspace_root=str(self.root / "workspaces"),
            production_qdrant_collection="lingji_memory_production_test",
            acceptance_qdrant_collection="lingji_memory_acceptance_test",
            semantic_enabled=False,
            vault_auto_init=False,
            startup_min_free_gb=0,
        )
        self.workspace = WorkspaceResolver.resolve(
            self.settings,
            "acceptance",
            environ={},
            project_root=self.root,
        )
        self.workspace.vault_path.mkdir(parents=True, exist_ok=True)
        self.workspace.storage_path.mkdir(parents=True, exist_ok=True)

    def test_gateway_publishes_on_startup_and_after_rebuild(self):
        gateway = build_memory_gateway(
            self.settings,
            rebuild_if_empty=False,
            workspace=self.workspace,
        )
        snapshot_path = MemoryStatisticsService.snapshot_path_for(
            self.settings,
            self.workspace,
        )

        self.assertTrue(snapshot_path.is_file())
        initial = json.loads(snapshot_path.read_text(encoding="utf-8"))
        self.assertEqual(initial["workspace"], "acceptance")
        self.assertEqual(initial["memory"]["documents"], 0)
        self.assertEqual(initial["vector"]["state"], "disabled")
        self.assertIsNone(initial["vector"]["vectors"])

        relative_path = "03-Knowledge/status-wiring.md"
        path = self.workspace.vault_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        text = "# 状态接线\n\nStatusSnapshotWiringNeedle。\n"
        path.write_text(text, encoding="utf-8")
        entry = {
            "id": "MEM-STATUS-WIRING",
            "relative_path": relative_path,
            "title": "状态接线",
            "memory_type": "knowledge",
            "status": "active",
            "privacy": "private",
            "agent_scope": ["all"],
            "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }

        gateway.rebuild([entry], self.workspace.vault_path, force=True)

        updated = json.loads(snapshot_path.read_text(encoding="utf-8"))
        self.assertEqual(updated["memory"]["documents"], 1)
        self.assertGreater(updated["memory"]["chunks"], 0)
        self.assertEqual(updated["memory"]["revision"], gateway.database.revision)
        gateway.close()


if __name__ == "__main__":
    unittest.main()
