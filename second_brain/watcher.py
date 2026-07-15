from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import requests

from second_brain.config import settings


logger = logging.getLogger("second_brain.watcher")


class BoundedWatcher:
    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip("/")
        self.state_path = settings.runtime_dir / "watcher_state.json"
        self.state = self._load_state()

    def _load_state(self) -> dict[str, int]:
        if not self.state_path.exists():
            return {}
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_state(self) -> None:
        self.state_path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def scan_once(self) -> dict:
        counts = {"ai_chat": 0, "codex_tasks": 0, "obsidian": 0, "failed": 0}
        roots: list[tuple[str, Path, str, str]] = [
            ("ai_chat", settings.ai_inbox_dir, "*.json", "/memory/import"),
            ("codex_tasks", settings.codex_inbox_dir, "*.json", "/memory/codex-task"),
        ]
        if settings.obsidian_knowledge_dir:
            roots.append(("obsidian", settings.obsidian_knowledge_dir, "*.md", "/knowledge/index"))
        for kind, root, pattern, endpoint in roots:
            if not root.exists():
                continue
            for path in root.rglob(pattern):
                if ".git" in path.parts or ".obsidian" in path.parts:
                    continue
                key = str(path.resolve())
                stamp = path.stat().st_mtime_ns
                if self.state.get(key) == stamp:
                    continue
                try:
                    self._submit(kind, endpoint, path)
                    self.state[key] = stamp
                    counts[kind] += 1
                except Exception as exc:
                    counts["failed"] += 1
                    logger.error("Failed to process %s: %s", path, exc)
        self._save_state()
        return counts

    def _submit(self, kind: str, endpoint: str, path: Path) -> None:
        if kind == "ai_chat":
            payload = {"path": str(path), "distill": True}
        elif kind == "codex_tasks":
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        else:
            payload = {"path": str(path)}
        response = requests.post(f"{self.api_url}{endpoint}", json=payload, timeout=120)
        response.raise_for_status()

    def run(self) -> None:
        logger.info(
            "Watching only ai=%s codex=%s obsidian=%s",
            settings.ai_inbox_dir,
            settings.codex_inbox_dir,
            settings.obsidian_knowledge_dir,
        )
        while True:
            counts = self.scan_once()
            if any(counts.values()):
                logger.info("Watcher scan: %s", counts)
            time.sleep(settings.poll_seconds)


def main() -> None:
    settings.ensure_directories()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler(settings.log_dir / "watcher.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    BoundedWatcher(f"http://{settings.host}:{settings.port}").run()


if __name__ == "__main__":
    main()
