from __future__ import annotations

import shutil
import threading
from dataclasses import replace
from pathlib import Path

from second_brain.config import ROOT, Settings, settings
from second_brain.runtime import Runtime, build_runtime


WORKSPACES = {"production", "acceptance"}


def acceptance_settings(base: Settings = settings) -> Settings:
    root = (ROOT / "data" / "acceptance").resolve()
    return replace(
        base,
        database_path=root / "second_brain.sqlite3",
        raw_archive_dir=root / "raw" / "ai_chat",
        ai_inbox_dir=root / "inbox" / "ai_chat",
        codex_inbox_dir=root / "inbox" / "codex_tasks",
        qdrant_path=root / "qdrant",
        qdrant_url="",
        qdrant_collection="lingji_acceptance_v1",
        obsidian_knowledge_dir=root / "fixtures" / "obsidian",
        log_dir=root / "logs",
        runtime_dir=root / "runtime",
    )


class RuntimeRegistry:
    def __init__(self, production_settings: Settings = settings):
        self.production_settings = production_settings
        self.acceptance_settings = acceptance_settings(production_settings)
        self.acceptance_root = self.acceptance_settings.database_path.parent.resolve()
        self._lock = threading.RLock()
        self._runtimes: dict[str, Runtime] = {}

    def initialize(self) -> None:
        with self._lock:
            self._runtimes["production"] = build_runtime(self.production_settings)
            self._runtimes["acceptance"] = build_runtime(self.acceptance_settings)

    def get(self, workspace: str = "production") -> Runtime:
        normalized = workspace.strip().lower()
        if normalized not in WORKSPACES:
            raise ValueError(f"Unknown workspace: {workspace}")
        with self._lock:
            runtime = self._runtimes.get(normalized)
            if runtime is None:
                raise RuntimeError("Runtime registry is not initialized")
            return runtime

    def reset_acceptance(self) -> Runtime:
        with self._lock:
            runtime = self._runtimes.pop("acceptance", None)
            if runtime:
                runtime.close()
            expected_parent = (ROOT / "data").resolve()
            if self.acceptance_root.parent != expected_parent or self.acceptance_root.name != "acceptance":
                raise RuntimeError(f"Unsafe acceptance path: {self.acceptance_root}")
            if self.acceptance_root.exists():
                shutil.rmtree(self.acceptance_root)
            runtime = build_runtime(self.acceptance_settings)
            self._runtimes["acceptance"] = runtime
            return runtime

    def close(self) -> None:
        with self._lock:
            for runtime in self._runtimes.values():
                runtime.close()
            self._runtimes.clear()

