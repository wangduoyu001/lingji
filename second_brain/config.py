from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"'))


_load_env(ROOT / ".env.second-brain")


def _path(name: str, default: str) -> Path:
    value = os.getenv(name, default)
    path = Path(value)
    return path if path.is_absolute() else (ROOT / path).resolve()


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("SECOND_BRAIN_HOST", "127.0.0.1")
    port: int = int(os.getenv("SECOND_BRAIN_PORT", "8765"))
    database_path: Path = _path("SECOND_BRAIN_DB", "data/second_brain.sqlite3")
    raw_archive_dir: Path = _path("SECOND_BRAIN_RAW_DIR", "data/raw/ai_chat")
    ai_inbox_dir: Path = _path("SECOND_BRAIN_AI_INBOX", "data/inbox/ai_chat")
    codex_inbox_dir: Path = _path("SECOND_BRAIN_CODEX_INBOX", "data/inbox/codex_tasks")
    qdrant_path: Path = _path("SECOND_BRAIN_QDRANT_PATH", "data/qdrant")
    qdrant_url: str = os.getenv("SECOND_BRAIN_QDRANT_URL", "").strip()
    qdrant_collection: str = os.getenv("SECOND_BRAIN_QDRANT_COLLECTION", "lingji_memories_v1")
    ollama_url: str = os.getenv("SECOND_BRAIN_OLLAMA_URL", "http://127.0.0.1:11434")
    embed_model: str = os.getenv("SECOND_BRAIN_EMBED_MODEL", "bge-m3")
    fallback_embed_model: str = os.getenv("SECOND_BRAIN_FALLBACK_EMBED_MODEL", "nomic-embed-text")
    obsidian_knowledge_dir: Path | None = (
        _path("SECOND_BRAIN_OBSIDIAN_DIR", os.getenv("SECOND_BRAIN_OBSIDIAN_DIR", ""))
        if os.getenv("SECOND_BRAIN_OBSIDIAN_DIR", "").strip()
        else None
    )
    poll_seconds: float = float(os.getenv("SECOND_BRAIN_POLL_SECONDS", "5"))
    log_dir: Path = _path("SECOND_BRAIN_LOG_DIR", "logs/second_brain")
    runtime_dir: Path = _path("SECOND_BRAIN_RUNTIME_DIR", "data/runtime")

    def ensure_directories(self) -> None:
        paths = (
            self.database_path.parent,
            self.raw_archive_dir,
            self.ai_inbox_dir,
            self.codex_inbox_dir,
            self.log_dir,
            self.runtime_dir,
        )
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)
        if str(self.qdrant_path) != ":memory:":
            self.qdrant_path.mkdir(parents=True, exist_ok=True)


settings = Settings()
