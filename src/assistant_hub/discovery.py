from __future__ import annotations

import os
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

_MAX_DISCOVERED_FILES = 5000


class AiAssistantDiscoveryService:
    """Read-only discovery for supported AI tools.

    Discovery only checks a small allowlist of known local paths and file metadata.
    It never reads conversation contents, follows symlinks, or writes configuration.
    """

    def __init__(
        self,
        *,
        home: Path | str | None = None,
        env: Mapping[str, str] | None = None,
        platform_name: str | None = None,
        workspace: str = "",
    ) -> None:
        self.home = Path(home or Path.home()).expanduser()
        # ``env={}`` is used by isolated verification and must not discover
        # the owner's CODEX_HOME or local-app-data paths through inheritance.
        self.env = dict(os.environ) if env is None else dict(env)
        self.platform_name = str(platform_name or platform.system()).lower()
        self.workspace = workspace or str(self.env.get("LINGJI_WORKSPACE") or "unknown")

    def scan(self) -> dict[str, Any]:
        assistants = [
            self._chatgpt(),
            self._codex(),
            self._claude_code(),
            self._workbuddy(),
        ]
        return {
            "schema_version": 1,
            "workspace": self.workspace,
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "safety": {
                "read_only": True,
                "content_read": False,
                "automatic_core_memory_write": False,
                "review_required_for_permanent_memory": True,
            },
            "summary": {
                "assistant_count": len(assistants),
                "detected": sum(1 for item in assistants if item["detection_state"] == "detected"),
                "import_ready": sum(1 for item in assistants if item["import_state"] == "available"),
                "requires_manual_export": sum(
                    1 for item in assistants if item["import_state"] == "manual_export"
                ),
                "planned": sum(1 for item in assistants if item["import_state"] == "planned"),
            },
            "assistants": assistants,
        }

    def _chatgpt(self) -> dict[str, Any]:
        return self._record(
            assistant_id="chatgpt",
            label="ChatGPT",
            detection_state="manual_export",
            connection_state="configuration_required",
            import_state="manual_export",
            sync_state="unavailable",
            discovered_paths=[],
            candidate_count=0,
            latest_activity_at=None,
            import_modes=["chatgpt_export"],
            capabilities={
                "export_zip_import": True,
                "direct_account_access": False,
                "automatic_sync": False,
            },
            message="请从 ChatGPT 导出 ZIP/JSON 后导入。灵机不会读取浏览器登录态或账号凭据。",
            next_action="选择 ChatGPT 导出文件",
        )

    def _codex(self) -> dict[str, Any]:
        configured = self.env.get("CODEX_HOME", "").strip()
        roots = [Path(configured).expanduser()] if configured else []
        roots.append(self.home / ".codex")
        existing = self._existing_unique(roots)
        count, latest = self._scan_metadata(existing, suffixes={".jsonl", ".json", ".md"})
        detected = bool(existing)
        return self._record(
            assistant_id="codex",
            label="Codex",
            detection_state="detected" if detected else "not_found",
            connection_state="configuration_required" if detected else "unavailable",
            import_state="available",
            sync_state="configuration_required" if detected else "unavailable",
            discovered_paths=[self._display_path(path) for path in existing],
            candidate_count=count,
            latest_activity_at=latest,
            import_modes=["codex_report"],
            capabilities={
                "report_import": True,
                "project_session_read_model": True,
                "automatic_local_history_import": False,
                "live_session_connector": "configuration_required",
            },
            message=(
                "已检测到 Codex 本地目录。当前可直接导入 Codex Report；实时 Session 永久记忆仍需通过正式 Connector/MCP 推送。"
                if detected
                else "未检测到 Codex 本地目录；仍可手动选择 Codex Report 导入。"
            ),
            next_action="导入 Codex Report",
        )

    def _claude_code(self) -> dict[str, Any]:
        root = self.home / ".claude"
        existing = self._existing_unique([root])
        count, latest = self._scan_metadata(
            [root / "projects"] if (root / "projects").exists() else existing,
            suffixes={".jsonl", ".json", ".md"},
        )
        memory_file = root / "CLAUDE.md"
        detected = bool(existing)
        return self._record(
            assistant_id="claude_code",
            label="Claude Code",
            detection_state="detected" if detected else "not_found",
            connection_state="configuration_required" if detected else "unavailable",
            import_state="planned",
            sync_state="planned",
            discovered_paths=[self._display_path(path) for path in existing],
            candidate_count=count,
            latest_activity_at=latest,
            import_modes=[],
            capabilities={
                "user_memory_detected": memory_file.is_file(),
                "transcript_metadata_detected": count > 0,
                "content_import": False,
                "automatic_sync": False,
            },
            message=(
                "已检测到 Claude Code。本阶段只读取文件数量和时间，不读取对话正文；正式导入适配器尚未实现。"
                if detected
                else "未检测到 Claude Code 本地目录。"
            ),
            next_action="等待 Claude Code 适配器",
        )

    def _workbuddy(self) -> dict[str, Any]:
        candidates: list[Path] = []
        local_app_data = self.env.get("LOCALAPPDATA", "").strip()
        if local_app_data:
            candidates.append(Path(local_app_data) / "Programs" / "WorkBuddy")
        if "darwin" in self.platform_name or "mac" in self.platform_name:
            candidates.append(Path("/Applications/WorkBuddy.app"))
        existing = self._existing_unique(candidates)
        detected = bool(existing)
        return self._record(
            assistant_id="workbuddy",
            label="WorkBuddy",
            detection_state="detected" if detected else "not_found",
            connection_state="configuration_required" if detected else "unavailable",
            import_state="planned",
            sync_state="planned",
            discovered_paths=[self._display_path(path) for path in existing],
            candidate_count=0,
            latest_activity_at=self._latest_mtime(existing),
            import_modes=[],
            capabilities={
                "installation_detected": detected,
                "stable_export_location_known": False,
                "content_import": False,
                "automatic_sync": False,
            },
            message=(
                "已检测到 WorkBuddy 安装目录，但官方未提供稳定会话导出目录；灵机不会猜测或扫描未知数据库。"
                if detected
                else "未检测到 WorkBuddy 安装目录。"
            ),
            next_action="等待 WorkBuddy 官方导出或 Connector",
        )

    @staticmethod
    def _record(
        *,
        assistant_id: str,
        label: str,
        detection_state: str,
        connection_state: str,
        import_state: str,
        sync_state: str,
        discovered_paths: list[str],
        candidate_count: int,
        latest_activity_at: str | None,
        import_modes: list[str],
        capabilities: Mapping[str, Any],
        message: str,
        next_action: str,
    ) -> dict[str, Any]:
        return {
            "id": assistant_id,
            "label": label,
            "detection_state": detection_state,
            "connection_state": connection_state,
            "import_state": import_state,
            "sync_state": sync_state,
            "discovered_paths": discovered_paths,
            "candidate_count": candidate_count,
            "latest_activity_at": latest_activity_at,
            "import_modes": import_modes,
            "capabilities": dict(capabilities),
            "message": message,
            "next_action": next_action,
        }

    def _display_path(self, path: Path) -> str:
        path = path.expanduser()
        relative = self._relative(path, self.home)
        if relative is not None:
            return "~" if str(relative) == "." else f"~/{relative.as_posix()}"
        for key in ("LOCALAPPDATA", "APPDATA"):
            raw = self.env.get(key, "").strip()
            if not raw:
                continue
            relative = self._relative(path, Path(raw))
            if relative is not None:
                return f"%{key}%" if str(relative) == "." else f"%{key}%/{relative.as_posix()}"
        return f"<local>/{path.name}"

    @staticmethod
    def _relative(path: Path, base: Path) -> Path | None:
        try:
            return path.resolve(strict=False).relative_to(base.resolve(strict=False))
        except (OSError, ValueError):
            return None

    @staticmethod
    def _existing_unique(paths: Iterable[Path]) -> list[Path]:
        result: list[Path] = []
        seen: set[str] = set()
        for path in paths:
            try:
                normalized = path.expanduser().resolve(strict=False)
            except OSError:
                continue
            key = str(normalized).casefold()
            if key in seen or not normalized.exists():
                continue
            seen.add(key)
            result.append(normalized)
        return result

    def _scan_metadata(self, roots: Iterable[Path], *, suffixes: set[str]) -> tuple[int, str | None]:
        count = 0
        latest = 0.0
        for root in roots:
            if count >= _MAX_DISCOVERED_FILES:
                break
            if root.is_file():
                files = [root]
            elif root.is_dir():
                files = self._iter_files(root)
            else:
                continue
            for path in files:
                if path.suffix.lower() not in suffixes:
                    continue
                count += 1
                try:
                    latest = max(latest, path.stat().st_mtime)
                except OSError:
                    pass
                if count >= _MAX_DISCOVERED_FILES:
                    break
        return count, self._timestamp(latest)

    @staticmethod
    def _iter_files(root: Path):
        for current, directories, files in os.walk(root, followlinks=False):
            directories[:] = [name for name in directories if not (Path(current) / name).is_symlink()]
            for name in files:
                path = Path(current) / name
                if not path.is_symlink():
                    yield path

    def _latest_mtime(self, paths: Iterable[Path]) -> str | None:
        latest = 0.0
        for path in paths:
            try:
                latest = max(latest, path.stat().st_mtime)
            except OSError:
                pass
        return self._timestamp(latest)

    @staticmethod
    def _timestamp(value: float) -> str | None:
        if value <= 0:
            return None
        return datetime.fromtimestamp(value, timezone.utc).isoformat()
