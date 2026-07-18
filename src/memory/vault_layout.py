from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

LAYOUT_VERSION = "1"

TOP_LEVEL_FOLDERS: tuple[str, ...] = (
    "00-System",
    "01-Inbox",
    "02-Sources",
    "03-Knowledge",
    "04-Projects",
    "05-Operations",
    "06-Entities",
    "07-Assets",
    "08-Private",
    "09-Archive",
    "Attachments",
)

REQUIRED_FOLDERS: tuple[str, ...] = (
    "00-System/Templates",
    "00-System/Schemas",
    "00-System/Rules",
    "00-System/Dashboard",
    "00-System/Logs",
    "00-System/Index-Status",
    "00-System/Backups",
    "01-Inbox/Mobile-Share",
    "01-Inbox/Browser",
    "01-Inbox/Local-Files",
    "01-Inbox/WeChat",
    "01-Inbox/ChatGPT",
    "01-Inbox/Codex",
    "01-Inbox/GitHub",
    "01-Inbox/Video",
    "01-Inbox/Audio",
    "01-Inbox/Images",
    "01-Inbox/Manual",
    "02-Sources/Conversations/ChatGPT",
    "02-Sources/Conversations/Codex",
    "02-Sources/Conversations/Kimi",
    "02-Sources/Conversations/WeChat",
    "02-Sources/Web/Douyin",
    "02-Sources/Web/Xiaohongshu",
    "02-Sources/Web/WeChat-Articles",
    "02-Sources/Web/Video-Channels",
    "02-Sources/Web/Websites",
    "02-Sources/Documents",
    "02-Sources/Videos",
    "02-Sources/Audios",
    "02-Sources/Images",
    "02-Sources/GitHub",
    "03-Knowledge/AI",
    "03-Knowledge/Self-Media",
    "03-Knowledge/Business",
    "03-Knowledge/Technology",
    "03-Knowledge/Directing",
    "03-Knowledge/ComfyUI",
    "03-Knowledge/Methods",
    "04-Projects/LingJi",
    "04-Projects/AI-Drama-System",
    "04-Projects/ComfyUI",
    "04-Projects/Self-Media",
    "04-Projects/Money-Experiments/Opportunities",
    "04-Projects/Archived",
    "05-Operations/Tasks",
    "05-Operations/Decisions",
    "05-Operations/Work-Reports",
    "05-Operations/Errors",
    "05-Operations/Reviews",
    "05-Operations/Daily",
    "06-Entities/People",
    "06-Entities/Organizations",
    "06-Entities/Tools",
    "06-Entities/Models",
    "06-Entities/Platforms",
    "06-Entities/Accounts",
    "07-Assets/Characters",
    "07-Assets/Scenes",
    "07-Assets/Props",
    "07-Assets/Prompts",
    "07-Assets/Workflows",
    "07-Assets/Media-Indexes",
    "08-Private/Personal",
    "08-Private/Finance",
    "08-Private/Identity",
    "08-Private/Private-Chats",
    "09-Archive/Superseded",
    "09-Archive/Completed-Projects",
    "09-Archive/Cold-Sources",
)

SOURCE_TO_INBOX: dict[str, str] = {
    "mobile": "01-Inbox/Mobile-Share",
    "mobile_share": "01-Inbox/Mobile-Share",
    "browser": "01-Inbox/Browser",
    "web": "01-Inbox/Browser",
    "local_file": "01-Inbox/Local-Files",
    "local_files": "01-Inbox/Local-Files",
    "wechat": "01-Inbox/WeChat",
    "chatgpt": "01-Inbox/ChatGPT",
    "codex": "01-Inbox/Codex",
    "github": "01-Inbox/GitHub",
    "video": "01-Inbox/Video",
    "audio": "01-Inbox/Audio",
    "image": "01-Inbox/Images",
    "images": "01-Inbox/Images",
    "manual": "01-Inbox/Manual",
}

SOURCE_TO_ARCHIVE: dict[str, str] = {
    "chatgpt": "02-Sources/Conversations/ChatGPT",
    "codex": "02-Sources/Conversations/Codex",
    "kimi": "02-Sources/Conversations/Kimi",
    "wechat": "02-Sources/Conversations/WeChat",
    "douyin": "02-Sources/Web/Douyin",
    "xiaohongshu": "02-Sources/Web/Xiaohongshu",
    "wechat_article": "02-Sources/Web/WeChat-Articles",
    "video_channel": "02-Sources/Web/Video-Channels",
    "web": "02-Sources/Web/Websites",
    "browser": "02-Sources/Web/Websites",
    "document": "02-Sources/Documents",
    "local_file": "02-Sources/Documents",
    "video": "02-Sources/Videos",
    "audio": "02-Sources/Audios",
    "image": "02-Sources/Images",
    "github": "02-Sources/GitHub",
}

EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".obsidian",
    ".trash",
    "node_modules",
    ".venv",
    "__pycache__",
}

INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@dataclass(frozen=True)
class VaultClassification:
    relative_path: str
    top_level: str
    category: str
    source_type: str
    privacy: str
    is_private: bool
    is_inbox: bool
    is_archive: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class VaultLayout:
    """Single-Vault folder layout and routing rules.

    The folder tree is the human-facing organization layer. Metadata and IDs remain
    the stable machine-facing layer, so notes can move without losing identity.
    """

    def __init__(self, root: Path | str):
        self.root = Path(root).expanduser()

    @property
    def dashboard_dir(self) -> Path:
        return self.root / "00-System" / "Dashboard"

    @property
    def opportunities_dir(self) -> Path:
        return self.root / "04-Projects" / "Money-Experiments" / "Opportunities"

    def ensure(self) -> list[Path]:
        self.root.mkdir(parents=True, exist_ok=True)
        created: list[Path] = []
        for relative in (*TOP_LEVEL_FOLDERS, *REQUIRED_FOLDERS):
            path = self.root / relative
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                created.append(path)
        return created

    def inbox_path(
        self,
        source_type: str,
        filename: str | None = None,
        when: datetime | None = None,
    ) -> Path:
        source_key = self._normalize_source_type(source_type)
        base = self.root / SOURCE_TO_INBOX.get(source_key, SOURCE_TO_INBOX["manual"])
        when = when or datetime.now()
        dated_dir = base / when.strftime("%Y") / when.strftime("%m")
        dated_dir.mkdir(parents=True, exist_ok=True)
        if filename is None:
            return dated_dir
        return dated_dir / self.sanitize_filename(filename)

    def archive_path(
        self,
        source_type: str,
        filename: str | None = None,
        when: datetime | None = None,
    ) -> Path:
        source_key = self._normalize_source_type(source_type)
        base = self.root / SOURCE_TO_ARCHIVE.get(source_key, "02-Sources/Documents")
        when = when or datetime.now()
        dated_dir = base / when.strftime("%Y") / when.strftime("%m")
        dated_dir.mkdir(parents=True, exist_ok=True)
        if filename is None:
            return dated_dir
        return dated_dir / self.sanitize_filename(filename)

    def classify(self, path: Path | str) -> VaultClassification:
        relative = self.relative(path)
        parts = relative.parts
        top_level = parts[0] if parts else ""
        category = top_level.split("-", 1)[-1].lower() if top_level else "unknown"
        source_type = self._source_from_parts(parts)
        is_private = top_level == "08-Private"
        return VaultClassification(
            relative_path=relative.as_posix(),
            top_level=top_level,
            category=category,
            source_type=source_type,
            privacy="restricted" if is_private else "private",
            is_private=is_private,
            is_inbox=top_level == "01-Inbox",
            is_archive=top_level == "09-Archive",
        )

    def relative(self, path: Path | str) -> Path:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = self.root / candidate
        try:
            return candidate.resolve(strict=False).relative_to(self.root.resolve(strict=False))
        except ValueError as exc:
            raise ValueError(f"Path is outside the LingJi vault: {candidate}") from exc

    def should_index(self, path: Path | str, include_private: bool = False) -> bool:
        relative = self.relative(path)
        parts = relative.parts
        if any(part in EXCLUDED_DIRECTORY_NAMES for part in parts):
            return False
        if any(part.startswith(".") for part in parts):
            return False
        if not include_private and parts and parts[0] == "08-Private":
            return False
        excluded_prefixes = (
            ("00-System", "Logs"),
            ("00-System", "Index-Status"),
            ("00-System", "Backups"),
        )
        return not any(parts[: len(prefix)] == prefix for prefix in excluded_prefixes)

    def should_analyze(self, path: Path | str) -> bool:
        if not self.should_index(path, include_private=False):
            return False
        relative = self.relative(path)
        if not relative.parts:
            return False
        return relative.parts[0] not in {
            "00-System",
            "05-Operations",
            "08-Private",
            "09-Archive",
            "Attachments",
            "PEMIS",
        }

    def status(self) -> dict[str, object]:
        existing = sum(1 for relative in REQUIRED_FOLDERS if (self.root / relative).exists())
        return {
            "version": LAYOUT_VERSION,
            "root": str(self.root),
            "required_folders": len(REQUIRED_FOLDERS),
            "existing_folders": existing,
            "complete": existing == len(REQUIRED_FOLDERS),
        }

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        cleaned = INVALID_FILENAME_CHARS.sub("_", filename).strip().rstrip(".")
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned or "untitled.md"

    @staticmethod
    def _normalize_source_type(source_type: str) -> str:
        return source_type.strip().lower().replace("-", "_").replace(" ", "_")

    @staticmethod
    def _source_from_parts(parts: Iterable[str]) -> str:
        values = tuple(parts)
        if len(values) < 2:
            return ""
        if values[0] == "01-Inbox":
            reverse = {value.split("/", 1)[1]: key for key, value in SOURCE_TO_INBOX.items()}
            return reverse.get(values[1], values[1].lower().replace("-", "_"))
        if values[0] == "02-Sources":
            return values[-3].lower().replace("-", "_") if len(values) >= 4 else values[-1].lower()
        return ""
