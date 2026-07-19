from __future__ import annotations

import hashlib
import json
import platform
import shutil
import sqlite3
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from src.health import StartupHealthChecker


class AcceptanceChecker:
    """Inspect real LingJi inputs and prove that the inspection did not change them."""

    def __init__(
        self,
        settings: Any,
        *,
        chatgpt_export: Path | None = None,
        media_path: Path | None = None,
        deep_zip_check: bool = True,
        hash_inputs: bool = True,
    ):
        self.settings = settings
        self.chatgpt_export = Path(chatgpt_export).expanduser() if chatgpt_export else None
        self.media_path = Path(media_path).expanduser() if media_path else None
        self.deep_zip_check = bool(deep_zip_check)
        self.hash_inputs = bool(hash_inputs)
        self.checks: list[dict[str, Any]] = []

    def run(self) -> dict[str, Any]:
        before = self._capture_inputs()
        for check in (
            self._check_health,
            self._check_vault,
            self._check_index,
            self._check_databases,
            self._check_runtime_settings,
            self._check_chatgpt_export,
            self._check_media,
        ):
            check()
        after = self._capture_inputs()
        unchanged = before == after
        self._add(
            "input_immutability",
            "ok" if unchanged else "error",
            "验收前后输入指纹一致" if unchanged else "验收期间检测到输入变化",
            before=before,
            after=after,
        )
        errors = sum(item["status"] == "error" for item in self.checks)
        warnings = sum(item["status"] == "warning" for item in self.checks)
        return {
            "schema_version": 2,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "read_only": True,
            "inputs_unchanged": unchanged,
            "status": "failed" if errors else "passed_with_warnings" if warnings else "passed",
            "error_count": errors,
            "warning_count": warnings,
            "environment": {
                "platform": platform.platform(),
                "python": sys.version.split()[0],
                "python_executable": sys.executable,
                "ffmpeg": shutil.which("ffmpeg"),
                "ffprobe": shutil.which("ffprobe"),
            },
            "settings": {
                "vault": str(self.settings.vault_path),
                "storage": str(self.settings.storage_path),
                "backup": str(self.settings.backup_path),
                "ollama": self.settings.ollama_base_url,
                "chatgpt_export": str(self.chatgpt_export) if self.chatgpt_export else None,
                "media": str(self.media_path) if self.media_path else None,
                "deep_zip_check": self.deep_zip_check,
                "hash_inputs": self.hash_inputs,
            },
            "checks": self.checks,
        }

    def _add(self, name: str, status: str, message: str, **details: Any) -> None:
        self.checks.append({"name": name, "status": status, "message": message, "details": details})

    def _check_health(self) -> None:
        for item in StartupHealthChecker(self.settings, read_only=True).run().get("checks", []):
            details = {
                key: value
                for key, value in item.items()
                if key not in {"name", "status", "message"}
            }
            self._add(
                f"health:{item.get('name')}",
                str(item.get("status") or "warning"),
                str(item.get("message") or ""),
                **details,
            )

    def _check_vault(self) -> None:
        root = self.settings.vault_path
        if not root.is_dir():
            self._add("vault", "error", "Vault 目录不存在", path=str(root))
            return
        try:
            files = [path for path in root.rglob("*.md") if path.is_file() and not path.is_symlink()]
            total = sum(path.stat().st_size for path in files)
            largest = sorted(
                ((path.stat().st_size, path.relative_to(root).as_posix()) for path in files),
                reverse=True,
            )[:20]
            self._add(
                "vault",
                "ok",
                f"发现 {len(files)} 个 Markdown 文件",
                path=str(root),
                markdown_files=len(files),
                markdown_bytes=total,
                largest=[{"path": path, "bytes": size} for size, path in largest],
            )
        except OSError as exc:
            self._add("vault", "error", f"扫描 Vault 失败：{exc}", path=str(root))

    def _check_index(self) -> None:
        path = self.settings.storage_path / "pemis_index.json"
        if not path.is_file():
            self._add("file_index", "warning", "文件索引不存在；首次启动会建立索引", path=str(path))
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            entries = payload.get("entries") or {}
            self._add(
                "file_index",
                "ok",
                f"现有文件索引包含 {len(entries)} 条记录",
                path=str(path),
                entries=len(entries),
            )
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            self._add("file_index", "error", f"读取文件索引失败：{exc}", path=str(path))

    def _check_databases(self) -> None:
        for name, path in (
            ("state_db", self.settings.state_db_path),
            ("memory_db", self.settings.memory_db_path),
        ):
            if not path.exists():
                self._add(name, "warning", "数据库尚未创建", path=str(path))
                continue
            try:
                uri = f"{path.resolve().as_uri()}?mode=ro"
                connection = sqlite3.connect(uri, uri=True, timeout=10)
                try:
                    result = connection.execute("PRAGMA quick_check").fetchone()
                finally:
                    connection.close()
                healthy = bool(result and str(result[0]).lower() == "ok")
                self._add(
                    name,
                    "ok" if healthy else "error",
                    "SQLite 只读 quick_check 通过" if healthy else f"SQLite quick_check 失败：{result}",
                    path=str(path),
                    bytes=path.stat().st_size,
                    open_mode="ro",
                )
            except (sqlite3.Error, OSError) as exc:
                self._add(name, "error", f"SQLite 只读检查失败：{exc}", path=str(path))

    def _check_runtime_settings(self) -> None:
        path = self.settings.runtime_settings_path
        if not path.is_file():
            self._add("runtime_settings", "warning", "运行时设置文件尚未创建", path=str(path))
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            overrides = payload.get("overrides") or {}
            if not isinstance(overrides, dict):
                raise ValueError("overrides must be an object")
            self._add(
                "runtime_settings",
                "ok",
                f"发现 {len(overrides)} 项用户覆盖",
                path=str(path),
                override_keys=sorted(overrides),
            )
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            self._add("runtime_settings", "error", f"运行时设置损坏：{exc}", path=str(path))

    def _check_chatgpt_export(self) -> None:
        path = self.chatgpt_export
        if path is None:
            self._add("chatgpt_export", "warning", "未指定 ChatGPT 导出文件")
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
                "ChatGPT 解压目录可识别" if recognized else "未发现标准文件",
                path=str(path),
                sample_files=names,
            )
            return
        if path.suffix.lower() == ".json":
            self._add(
                "chatgpt_export",
                "ok",
                "ChatGPT JSON 文件可访问",
                path=str(path),
                bytes=path.stat().st_size,
                sha256=self._sha256(path) if self.hash_inputs else None,
            )
            return
        if path.suffix.lower() != ".zip":
            self._add("chatgpt_export", "error", "ChatGPT 导出必须是 ZIP、JSON 或解压目录", path=str(path))
            return
        try:
            with zipfile.ZipFile(path) as archive:
                members = archive.infolist()
                recognized = any(
                    Path(item.filename).name in {"conversations.json", "chat.html"}
                    for item in members
                )
                encrypted = any(item.flag_bits & 0x1 for item in members)
                bad_member = archive.testzip() if self.deep_zip_check and not encrypted else None
                total = sum(item.file_size for item in members)
            if encrypted:
                status, message = "error", "ZIP 包含加密成员"
            elif bad_member:
                status, message = "error", f"ZIP CRC 检查失败：{bad_member}"
            elif recognized:
                status, message = "ok", "ChatGPT ZIP 结构和 CRC 可识别"
            else:
                status, message = "warning", "ZIP 可读取，但未发现标准 ChatGPT 文件"
            self._add(
                "chatgpt_export",
                status,
                message,
                path=str(path),
                members=len(members),
                uncompressed_bytes=total,
                archive_bytes=path.stat().st_size,
                deep_zip_check=self.deep_zip_check,
                sha256=self._sha256(path) if self.hash_inputs else None,
            )
        except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
            self._add("chatgpt_export", "error", f"ChatGPT ZIP/CRC 检查失败：{exc}", path=str(path))

    def _check_media(self) -> None:
        path = self.media_path
        if path is None:
            self._add("media_sample", "warning", "未指定样例媒体")
            return
        if not path.is_file():
            self._add("media_sample", "error", "样例媒体不存在", path=str(path))
            return
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            self._add("media_sample", "warning", "ffprobe 未安装", path=str(path))
            return
        try:
            result = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    str(path),
                ],
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
                sha256=self._sha256(path) if self.hash_inputs else None,
                format=(probe.get("format") or {}).get("format_name"),
                duration=(probe.get("format") or {}).get("duration"),
                streams=len(probe.get("streams") or []),
            )
        except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
            self._add("media_sample", "error", f"样例媒体检查失败：{exc}", path=str(path))

    def _capture_inputs(self) -> dict[str, Any]:
        return {
            "vault": self._fingerprint(self.settings.vault_path),
            "state_db": self._sqlite_fingerprint(self.settings.state_db_path),
            "memory_db": self._sqlite_fingerprint(self.settings.memory_db_path),
            "runtime_settings": self._fingerprint(self.settings.runtime_settings_path),
            "chatgpt_export": self._fingerprint(self.chatgpt_export) if self.chatgpt_export else None,
            "media": self._fingerprint(self.media_path) if self.media_path else None,
        }

    def _sqlite_fingerprint(self, path: Path) -> dict[str, Any]:
        return {
            "database": self._fingerprint(path),
            "wal": self._fingerprint(Path(f"{path}-wal")),
            "shm": self._fingerprint(Path(f"{path}-shm")),
        }

    def _fingerprint(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {"exists": False, "path": str(path)}
        if path.is_file():
            stat = path.stat()
            return {
                "exists": True,
                "kind": "file",
                "path": str(path),
                "bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "sha256": self._sha256(path) if self.hash_inputs else None,
            }
        digest = hashlib.sha256()
        count = total = 0
        iterator: Iterable[Path] = path.rglob("*")
        files = sorted(
            (item for item in iterator if item.is_file() and not item.is_symlink()),
            key=lambda item: item.as_posix(),
        )
        for item in files:
            stat = item.stat()
            count += 1
            total += stat.st_size
            digest.update(item.relative_to(path).as_posix().encode("utf-8", errors="surrogatepass"))
            digest.update(f"{stat.st_size}:{stat.st_mtime_ns}".encode())
            if self.hash_inputs:
                digest.update(self._sha256(item).encode())
        return {
            "exists": True,
            "kind": "directory",
            "path": str(path),
            "files": count,
            "bytes": total,
            "digest": digest.hexdigest(),
            "content_hashed": self.hash_inputs,
        }

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
