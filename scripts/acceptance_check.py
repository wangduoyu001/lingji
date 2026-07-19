#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import Settings
from src.control.runtime_settings import RuntimeSettingsStore
from src.health import StartupHealthChecker
from src.indexer.index import PEMISIndex
from src.retrieval import MemoryDatabase


class AcceptanceChecker:
    """Read-only acceptance checks for the owner's real Windows environment."""

    def __init__(
        self,
        settings: Settings,
        *,
        chatgpt_export: Path | None = None,
        media_path: Path | None = None,
    ):
        self.settings = settings
        self.chatgpt_export = chatgpt_export
        self.media_path = media_path
        self.checks: list[dict[str, Any]] = []

    def run(self) -> dict[str, Any]:
        self._check_health()
        self._check_vault()
        self._check_index()
        self._check_databases()
        self._check_runtime_settings()
        self._check_chatgpt_export()
        self._check_media()
        errors = sum(1 for item in self.checks if item["status"] == "error")
        warnings = sum(1 for item in self.checks if item["status"] == "warning")
        return {
            "schema_version": 1,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "read_only": True,
            "status": "failed" if errors else "passed_with_warnings" if warnings else "passed",
            "error_count": errors,
            "warning_count": warnings,
            "settings": {
                "vault": str(self.settings.vault_path),
                "storage": str(self.settings.storage_path),
                "backup": str(self.settings.backup_path),
                "ollama": self.settings.ollama_base_url,
            },
            "checks": self.checks,
        }

    def _add(self, name: str, status: str, message: str, **details: Any) -> None:
        self.checks.append({"name": name, "status": status, "message": message, "details": details})

    def _check_health(self) -> None:
        report = StartupHealthChecker(self.settings).run()
        for item in report.get("checks") or []:
            self._add(
                f"health:{item.get('name')}",
                str(item.get("status") or "warning"),
                str(item.get("message") or ""),
                **dict(item.get("details") or {}),
            )

    def _check_vault(self) -> None:
        root = self.settings.vault_path
        if not root.is_dir():
            self._add("vault", "error", "Vault 目录不存在", path=str(root))
            return
        markdown = []
        total_bytes = 0
        largest: list[tuple[int, str]] = []
        try:
            for path in root.rglob("*.md"):
                if not path.is_file() or path.is_symlink():
                    continue
                size = path.stat().st_size
                markdown.append(path)
                total_bytes += size
                largest.append((size, path.relative_to(root).as_posix()))
        except OSError as exc:
            self._add("vault", "error", f"扫描 Vault 失败：{exc}", path=str(root))
            return
        largest.sort(reverse=True)
        self._add(
            "vault",
            "ok",
            f"发现 {len(markdown)} 个 Markdown 文件",
            path=str(root),
            markdown_files=len(markdown),
            markdown_bytes=total_bytes,
            largest=[{"path": path, "bytes": size} for size, path in largest[:20]],
        )

    def _check_index(self) -> None:
        if not self.settings.vault_path.is_dir():
            return
        try:
            indexer = PEMISIndex(
                self.settings.vault_path,
                self.settings.storage_path,
                include_private=self.settings.index_private,
            )
            existing = indexer.get_all()
            self._add(
                "file_index",
                "ok" if existing else "warning",
                f"现有文件索引包含 {len(existing)} 条记录" if existing else "文件索引为空；首次启动会建立索引",
                index_path=str(indexer.index_path),
                entries=len(existing),
            )
        except Exception as exc:
            self._add("file_index", "error", f"读取文件索引失败：{exc}")

    def _check_databases(self) -> None:
        for name, path in (
            ("state_db", self.settings.state_db_path),
            ("memory_db", self.settings.memory_db_path),
        ):
            if not path.exists():
                self._add(name, "warning", "数据库尚未创建；首次启动会初始化", path=str(path))
                continue
            try:
                connection = sqlite3.connect(path, timeout=10)
                try:
                    result = connection.execute("PRAGMA quick_check").fetchone()
                finally:
                    connection.close()
                healthy = bool(result and str(result[0]).lower() == "ok")
                self._add(
                    name,
                    "ok" if healthy else "error",
                    "SQLite quick_check 通过" if healthy else f"SQLite quick_check 失败：{result}",
                    path=str(path),
                    bytes=path.stat().st_size,
                )
            except sqlite3.Error as exc:
                self._add(name, "error", f"SQLite 检查失败：{exc}", path=str(path))

    def _check_runtime_settings(self) -> None:
        try:
            snapshot = RuntimeSettingsStore(self.settings).snapshot()
            self._add(
                "runtime_settings",
                "ok",
                f"运行时设置可读取，当前有 {len(snapshot['overrides'])} 项用户覆盖",
                path=snapshot["path"],
                override_keys=sorted(snapshot["overrides"]),
            )
        except Exception as exc:
            self._add("runtime_settings", "error", f"运行时设置损坏：{exc}")

    def _check_chatgpt_export(self) -> None:
        path = self.chatgpt_export
        if path is None:
            self._add("chatgpt_export", "warning", "未指定 ChatGPT 导出文件，跳过真实导入源验收")
            return
        if not path.exists():
            self._add("chatgpt_export", "error", "ChatGPT 导出路径不存在", path=str(path))
            return
        if path.is_dir():
            names = sorted(item.name for item in path.iterdir() if item.is_file())[:100]
            recognized = any(name in {"conversations.json", "chat.html"} for name in names)
            self._add(
                "chatgpt_export",
                "ok" if recognized else "warning",
                "发现可识别的 ChatGPT 解压目录" if recognized else "目录存在，但未发现 conversations.json 或 chat.html",
                path=str(path),
                sample_files=names,
            )
            return
        if path.suffix.lower() == ".json":
            self._add(
                "chatgpt_export",
                "ok" if path.name == "conversations.json" else "warning",
                "ChatGPT JSON 文件可访问",
                path=str(path),
                bytes=path.stat().st_size,
            )
            return
        if path.suffix.lower() != ".zip":
            self._add("chatgpt_export", "error", "ChatGPT 导出必须是 ZIP、JSON 或解压目录", path=str(path))
            return
        try:
            with zipfile.ZipFile(path) as archive:
                members = archive.infolist()
                total = sum(item.file_size for item in members)
                recognized = any(Path(item.filename).name in {"conversations.json", "chat.html"} for item in members)
                encrypted = any(item.flag_bits & 0x1 for item in members)
            status = "error" if encrypted else "ok" if recognized else "warning"
            message = "ZIP 包含加密成员，无法安全导入" if encrypted else "ChatGPT ZIP 结构可识别" if recognized else "ZIP 可读取，但未发现标准 ChatGPT 文件"
            self._add(
                "chatgpt_export",
                status,
                message,
                path=str(path),
                members=len(members),
                uncompressed_bytes=total,
                archive_bytes=path.stat().st_size,
            )
        except (OSError, zipfile.BadZipFile) as exc:
            self._add("chatgpt_export", "error", f"ChatGPT ZIP 无法读取：{exc}", path=str(path))

    def _check_media(self) -> None:
        path = self.media_path
        if path is None:
            self._add("media_sample", "warning", "未指定样例媒体，跳过真实 FFprobe 验收")
            return
        if not path.is_file():
            self._add("media_sample", "error", "样例媒体不存在", path=str(path))
            return
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            self._add("media_sample", "warning", "ffprobe 未安装，无法读取真实媒体参数", path=str(path))
            return
        try:
            result = subprocess.run(
                [ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )
            probe = json.loads(result.stdout or "{}")
            self._add(
                "media_sample",
                "ok",
                "样例媒体 FFprobe 读取成功",
                path=str(path),
                bytes=path.stat().st_size,
                format=(probe.get("format") or {}).get("format_name"),
                duration=(probe.get("format") or {}).get("duration"),
                streams=len(probe.get("streams") or []),
            )
        except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
            self._add("media_sample", "error", f"样例媒体检查失败：{exc}", path=str(path))


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# 灵机真实环境验收报告",
        "",
        f"- 生成时间：{report['generated_at']}",
        f"- 总状态：**{report['status']}**",
        f"- 错误：{report['error_count']}",
        f"- 警告：{report['warning_count']}",
        "- 模式：只读，不迁移、不删除、不覆盖",
        "",
        "## 检查结果",
        "",
    ]
    for item in report["checks"]:
        lines.extend(
            [
                f"### {item['name']} · {item['status']}",
                "",
                item["message"],
                "",
                "```json",
                json.dumps(item.get("details") or {}, ensure_ascii=False, indent=2, default=str),
                "```",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only LingJi real environment acceptance checks")
    parser.add_argument("--vault", help="Override Vault path for this check")
    parser.add_argument("--storage", help="Override storage path for this check")
    parser.add_argument("--backup", help="Override backup path for this check")
    parser.add_argument("--chatgpt-export", help="Optional ChatGPT ZIP/JSON/directory")
    parser.add_argument("--media", help="Optional real media sample")
    parser.add_argument("--output", help="Output directory; defaults to storage/reports/acceptance")
    args = parser.parse_args()

    values: dict[str, Any] = {}
    if args.vault:
        values["vault_dir"] = args.vault
    if args.storage:
        values["storage_dir"] = args.storage
    if args.backup:
        values["backup_dir"] = args.backup
    settings = Settings(**values)
    checker = AcceptanceChecker(
        settings,
        chatgpt_export=Path(args.chatgpt_export).expanduser() if args.chatgpt_export else None,
        media_path=Path(args.media).expanduser() if args.media else None,
    )
    report = checker.run()
    output = Path(args.output).expanduser() if args.output else settings.storage_path / "reports" / "acceptance"
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = output / f"acceptance-{stamp}.json"
    md_path = output / f"acceptance-{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"report": report, "json_path": str(json_path), "markdown_path": str(md_path)}, ensure_ascii=False, indent=2, default=str))
    return 1 if report["error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
