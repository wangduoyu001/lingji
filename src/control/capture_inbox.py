"""手机捕获收件箱：iOS 快捷指令把内容写进 iCloud Drive/LingJiInbox，
Mac 端 watcher 轮询摄取，复用既有捕获管线（text/web/file 统一分发）。

- 不开放任何网络端口（本地优先红线）。
- 成功移入 processed/，解析或提交失败移入 failed/（绝不静默丢弃）。
"""

from __future__ import annotations

import json
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_POLL_SECONDS_DEFAULT = 15.0
_ICLOUD_CONTAINER = "~/Library/Mobile Documents/com~apple~CloudDocs"


def resolve_inbox_dir() -> Path:
    """iCloud Drive 可用则用 iCloud（跨设备同步），否则退回本机目录。"""
    icloud = Path(_ICLOUD_CONTAINER).expanduser()
    if icloud.is_dir():
        return icloud / "LingJiInbox"
    return Path.home() / "LingJiInbox"


def ensure_capture_inbox() -> Path:
    inbox = resolve_inbox_dir()
    for directory in (inbox, inbox / "processed", inbox / "failed"):
        directory.mkdir(parents=True, exist_ok=True)
    return inbox


class CaptureInboxWatcher:
    """轮询 LingJiInbox，把手机分享的条目送进捕获管线。"""

    def __init__(
        self,
        submit: Callable[[dict[str, Any]], Any],
        inbox_dir: Path | None = None,
        *,
        poll_seconds: float = _POLL_SECONDS_DEFAULT,
    ) -> None:
        self._submit = submit
        self.inbox_dir = Path(inbox_dir) if inbox_dir else ensure_capture_inbox()
        self.poll_seconds = max(float(poll_seconds), 2.0)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.last_result: dict[str, int] = {"processed": 0, "failed": 0}

    def start(self) -> None:
        if self._thread is not None:
            return
        ensure_capture_inbox()
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="lingji-capture-inbox", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

    def _loop(self) -> None:
        while not self._stop.wait(self.poll_seconds):
            try:
                self.scan_once()
            except Exception:
                # 单轮失败不影响下一轮；文件仍在原位会再次尝试。
                continue

    def scan_once(self) -> dict[str, int]:
        processed = 0
        failed = 0
        for path in sorted(self.inbox_dir.iterdir()):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".json", ".txt"}:
                continue
            try:
                payload = self._build_payload(path)
                if payload is None:
                    self._move(path, "failed")
                    failed += 1
                    continue
                self._submit(payload)
                self._move(path, "processed")
                processed += 1
            except Exception:
                self._move(path, "failed")
                failed += 1
        if processed or failed:
            self.last_result = {"processed": processed, "failed": failed}
        return {"processed": processed, "failed": failed}

    def _build_payload(self, path: Path) -> dict[str, Any] | None:
        raw = path.read_text(encoding="utf-8", errors="replace").strip()
        if not raw:
            return None
        if path.suffix.lower() == ".json":
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                return None
            if isinstance(data, str):
                return {"text": data, "title": "手机捕获"}
            if isinstance(data, dict):
                payload = {
                    "text": str(data.get("text") or data.get("note") or ""),
                    "url": str(data.get("url") or data.get("source_url") or ""),
                    "title": str(data.get("title") or "手机捕获"),
                    "platform": str(data.get("source_app") or data.get("platform") or "mobile_share"),
                    "capture_method": "mobile_inbox",
                    "captured_at": str(data.get("captured_at") or ""),
                }
                if not payload["text"] and not payload["url"]:
                    return None
                return payload
            return None
        return {"text": raw, "title": "手机捕获", "platform": "mobile_share", "capture_method": "mobile_inbox"}

    def _move(self, path: Path, sub: str) -> None:
        target_dir = self.inbox_dir / sub
        target_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        target = target_dir / f"{stamp}-{path.name}"
        try:
            shutil.move(str(path), str(target))
        except shutil.SameFileError:
            pass


__all__ = ["CaptureInboxWatcher", "ensure_capture_inbox", "resolve_inbox_dir"]
