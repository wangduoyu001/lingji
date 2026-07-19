from __future__ import annotations

import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any

import requests

from src.sqlite_snapshot import quick_check_snapshot


class StartupHealthChecker:
    """Run bounded checks without turning optional tools into hard dependencies."""

    def __init__(self, settings: Any, *, read_only: bool = False):
        self.settings = settings
        self.read_only = bool(read_only)

    def run(self) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []
        self._check_directory(checks, "vault", self.settings.vault_path, create=self.settings.vault_auto_init)
        self._check_directory(checks, "storage", self.settings.storage_path, create=True)
        self._check_directory(checks, "logs", self.settings.log_path, create=True)
        self._check_backup(checks)
        self._check_disk(checks)
        self._check_sqlite(checks, "state_db", self.settings.state_db_path)
        self._check_sqlite(checks, "memory_db", self.settings.memory_db_path)
        self._check_executable(checks, "ffmpeg", required=False)
        self._check_executable(checks, "ffprobe", required=False)
        self._check_ollama(checks)
        errors = [item for item in checks if item["status"] == "error"]
        warnings = [item for item in checks if item["status"] == "warning"]
        status = "error" if errors else "degraded" if warnings else "healthy"
        return {
            "status": status,
            "read_only": self.read_only,
            "checks": checks,
            "error_count": len(errors),
            "warning_count": len(warnings),
        }

    def ensure_startable(self, report: dict[str, Any]) -> None:
        if report.get("error_count") and self.settings.startup_health_fail_on_error:
            details = "; ".join(
                str(item.get("message") or item.get("name"))
                for item in report.get("checks", [])
                if item.get("status") == "error"
            )
            raise RuntimeError(f"Startup health check failed: {details}")

    @staticmethod
    def _append(
        checks: list[dict[str, Any]],
        name: str,
        status: str,
        message: str,
        **details: Any,
    ) -> None:
        checks.append({"name": name, "status": status, "message": message, **details})

    def _check_directory(
        self,
        checks: list[dict[str, Any]],
        name: str,
        path: Path,
        *,
        create: bool,
    ) -> None:
        try:
            if self.read_only:
                if not path.exists():
                    self._append(checks, name, "warning", f"目录不存在：{path}", path=str(path))
                    return
                if not path.is_dir():
                    self._append(checks, name, "error", f"路径不是目录：{path}", path=str(path))
                    return
                readable = os.access(path, os.R_OK)
                self._append(
                    checks,
                    name,
                    "ok" if readable else "error",
                    f"目录可读取：{path}" if readable else f"目录不可读取：{path}",
                    path=str(path),
                    writable=os.access(path, os.W_OK),
                )
                return

            if create:
                path.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                self._append(checks, name, "error", f"目录不存在：{path}", path=str(path))
                return
            if not path.is_dir():
                self._append(checks, name, "error", f"路径不是目录：{path}", path=str(path))
                return
            probe = path / ".lingji-write-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            self._append(checks, name, "ok", f"目录可写：{path}", path=str(path))
        except OSError as exc:
            action = "读取" if self.read_only else "写入"
            self._append(checks, name, "error", f"目录无法{action}：{path}（{exc}）", path=str(path))

    def _check_backup(self, checks: list[dict[str, Any]]) -> None:
        path = self.settings.backup_path
        try:
            if path.exists() and path.is_dir():
                self._append(checks, "backup", "ok", f"备份目录可用：{path}", path=str(path))
                return
            parent = path.parent
            if parent.exists():
                self._append(
                    checks,
                    "backup",
                    "warning",
                    f"备份目录尚未创建：{path}",
                    path=str(path),
                )
            else:
                self._append(
                    checks,
                    "backup",
                    "warning",
                    f"备份目录的父路径不存在：{path}",
                    path=str(path),
                )
        except OSError as exc:
            self._append(checks, "backup", "warning", f"无法检查备份目录：{exc}", path=str(path))

    @staticmethod
    def _nearest_existing(path: Path) -> Path | None:
        current = path
        while not current.exists() and current != current.parent:
            current = current.parent
        return current if current.exists() else None

    def _check_disk(self, checks: list[dict[str, Any]]) -> None:
        target = self._nearest_existing(self.settings.storage_path)
        if target is None:
            self._append(checks, "disk", "warning", "无法找到可检查的存储父目录")
            return
        try:
            usage = shutil.disk_usage(target)
            free_gb = usage.free / 1024**3
            threshold = float(self.settings.startup_min_free_gb)
            status = "warning" if free_gb < threshold else "ok"
            self._append(
                checks,
                "disk",
                status,
                f"磁盘剩余 {free_gb:.2f} GB",
                path=str(target),
                free_gb=round(free_gb, 3),
                threshold_gb=threshold,
                total_gb=round(usage.total / 1024**3, 3),
            )
        except OSError as exc:
            self._append(checks, "disk", "error", f"无法读取磁盘状态：{exc}")

    def _check_sqlite(self, checks: list[dict[str, Any]], name: str, path: Path) -> None:
        if not path.exists():
            message = "数据库尚未创建" if self.read_only else "数据库将在首次启动时创建"
            self._append(checks, name, "ok", f"{message}：{path}", path=str(path))
            return
        try:
            if self.read_only:
                value = quick_check_snapshot(path, timeout=3)
                mode = "temporary_snapshot"
            else:
                connection = sqlite3.connect(path, timeout=3)
                try:
                    result = connection.execute("PRAGMA quick_check").fetchone()
                finally:
                    connection.close()
                value = str(result[0]) if result else ""
                mode = "direct"
            if value.lower() == "ok":
                self._append(
                    checks,
                    name,
                    "ok",
                    f"SQLite quick_check 通过：{path}",
                    path=str(path),
                    check_mode=mode,
                )
            else:
                self._append(
                    checks,
                    name,
                    "error",
                    f"SQLite quick_check 异常：{value}",
                    path=str(path),
                    check_mode=mode,
                )
        except (sqlite3.Error, OSError) as exc:
            self._append(checks, name, "error", f"SQLite 无法检查：{exc}", path=str(path))

    def _check_executable(self, checks: list[dict[str, Any]], executable: str, *, required: bool) -> None:
        resolved = shutil.which(executable)
        if resolved:
            self._append(checks, executable, "ok", f"已找到 {executable}：{resolved}", path=resolved)
            return
        status = "error" if required else "warning"
        self._append(checks, executable, status, f"未找到 {executable}，相关媒体能力将降级")

    def _check_ollama(self, checks: list[dict[str, Any]]) -> None:
        url = self.settings.ollama_base_url.rstrip("/") + "/api/tags"
        try:
            response = requests.get(url, timeout=float(self.settings.startup_health_timeout_seconds))
            response.raise_for_status()
            payload = response.json() if response.content else {}
            models = []
            for item in payload.get("models") or []:
                name = item.get("name") or item.get("model")
                if name:
                    models.append(str(name))
            self._append(
                checks,
                "ollama",
                "ok",
                f"Ollama 可连接，发现 {len(models)} 个模型",
                url=url,
                models=sorted(models),
            )
        except (requests.RequestException, ValueError, TypeError) as exc:
            status = "error" if self.settings.startup_require_ollama else "warning"
            self._append(
                checks,
                "ollama",
                status,
                f"Ollama 当前不可用，模型能力将降级：{exc}",
                url=self.settings.ollama_base_url,
            )
