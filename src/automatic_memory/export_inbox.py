"""LingJi-owned receiving folders for official exports (owner intake plan Task 5).

Folders live only inside the LingJi data area (`<storage>/exports/<kind>/`), are
created idempotently with restrictive permissions, and never touch a source AI
application's own directories. Status is derived live from the filesystem; the
absolute path is returned solely so the Desktop can reveal the folder, and it
must never be rendered on the owner surface.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

MAX_INBOX_ENTRIES = 10_000

EXPORT_INBOX_KINDS: Mapping[str, Mapping[str, str]] = {
    "chatgpt_export": {
        "purpose": "ChatGPT 官方导出接收文件夹",
        "next_step": "把官方导出的 ZIP 原样放进这个文件夹，然后回到来源页选择该文件夹开始记忆。",
    },
}


def export_inbox_dir(settings: object, kind: str) -> Path:
    if kind not in EXPORT_INBOX_KINDS:
        raise LookupError(f"no export inbox is defined for source kind: {kind}")
    storage = Path(str(getattr(settings, "storage_path"))).expanduser()
    return storage / "exports" / kind


def ensure_export_inbox(settings: object, kind: str) -> dict[str, Any]:
    """Create the LingJi-owned inbox when missing and return its live status."""
    meta = EXPORT_INBOX_KINDS[kind]
    directory = export_inbox_dir(settings, kind)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    file_count = 0
    try:
        for node in directory.iterdir():
            file_count += 1
            if file_count >= MAX_INBOX_ENTRIES:
                break
    except OSError:
        file_count = 0
    return {
        "kind": kind,
        "purpose": meta["purpose"],
        "next_step": meta["next_step"],
        "exists": directory.is_dir(),
        "file_count": int(file_count),
        "last_checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "inbox_path": str(directory),
    }


def ensure_all_export_inboxes(settings: object) -> list[dict[str, Any]]:
    return [ensure_export_inbox(settings, kind) for kind in sorted(EXPORT_INBOX_KINDS)]


__all__ = [
    "EXPORT_INBOX_KINDS",
    "ensure_all_export_inboxes",
    "ensure_export_inbox",
    "export_inbox_dir",
]
