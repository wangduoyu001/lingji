from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .config import ObsidianCliConfig
from .models import (
    OBSIDIAN_WRITE_VERIFICATION_FAILED,
    ObsidianCliError,
    ObsidianCliErrorResult,
    ObsidianCliNotFound,
    ObsidianCliTimeout,
    ObsidianVaultInfo,
)


class ObsidianCliClient:
    """Typed Obsidian CLI client. It never invokes a shell string."""

    def __init__(self, config: ObsidianCliConfig | None = None):
        self.config = config or ObsidianCliConfig.from_env()
        self._log: list[dict[str, Any]] = []

    def _run(
        self,
        args: list[str],
        timeout: int | None = None,
        check: bool = True,
    ) -> tuple[int, str, str]:
        if not self.config.enabled:
            raise ObsidianCliNotFound(
                "Obsidian CLI 已禁用",
                public_message="Obsidian CLI is disabled",
            )
        if not self.config.cli_path or not os.path.isfile(self.config.cli_path):
            raise ObsidianCliNotFound(
                "CLI 未找到，请安装 Obsidian 并在设置中启用命令行接口",
                command=self.config.cli_path,
                public_message="Obsidian CLI is not configured",
            )

        command = [self.config.cli_path]
        if self.config.vault_name:
            command.append(f"vault={self.config.vault_name}")
        command.extend(str(arg) for arg in args)
        command_text = " ".join(command)
        command_timeout = timeout if timeout is not None else self.config.timeout
        self._log.append(
            {
                "time": datetime.now(timezone.utc).isoformat(),
                "command": command_text,
                "dry_run": self.config.dry_run,
            }
        )

        if self.config.dry_run:
            return 0, "", ""

        kwargs: dict[str, Any] = {
            "capture_output": True,
            "text": False,
            "timeout": command_timeout,
            "check": False,
        }
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            process = subprocess.run(command, **kwargs)
        except subprocess.TimeoutExpired as exc:
            self._log[-1]["error"] = "timeout"
            raise ObsidianCliTimeout(
                "命令超时",
                command=command_text,
                public_message="Obsidian CLI request timed out",
            ) from exc
        except OSError as exc:
            self._log[-1]["error"] = type(exc).__name__
            raise ObsidianCliErrorResult(
                "CLI 启动失败",
                command=command_text,
                err=str(exc),
                public_message="Obsidian CLI could not be started",
            ) from exc

        stdout = self._decode(process.stdout)
        stderr = self._decode(process.stderr)
        if check and process.returncode != 0:
            self._log[-1]["error"] = stderr or f"exit_{process.returncode}"
            raise ObsidianCliErrorResult(
                f"CLI 返回非零码: {process.returncode}",
                command=command_text,
                rc=process.returncode,
                err=stderr,
                public_message="Obsidian CLI request failed",
            )
        return process.returncode, stdout, stderr

    def get_version(self) -> str:
        return self._run(["version"])[1].strip()

    def get_help(self) -> str:
        return self._run(["help"])[1]

    def get_vault_info(self) -> ObsidianVaultInfo:
        name = self._run(["vault", "info=name"])[1].strip()
        path = self._run(["vault", "info=path"])[1].strip()
        return ObsidianVaultInfo(name=name, path=path)

    def list_vaults(self) -> list[dict[str, str]]:
        output = self._run(["vaults", "verbose"])[1]
        result: list[dict[str, str]] = []
        for line in output.splitlines():
            normalized = line.strip()
            if normalized and "\t" in normalized:
                name, path = normalized.split("\t", 1)
                result.append({"name": name, "path": path})
        return result

    def search(
        self,
        query: str,
        limit: int = 20,
        path_filter: str | None = None,
    ) -> list[str]:
        normalized_limit = max(min(int(limit), 1000), 1)
        args = ["search", f"query={query}", f"limit={normalized_limit}"]
        if path_filter:
            self._require_relative_path(path_filter)
            args.append(f"path={path_filter}")
        return self._lines(self._run(args)[1])

    def read(self, path: str) -> str:
        self._require_relative_path(path)
        output = self._run(["read", f"path={path}"])[1]
        if output.strip().startswith("Error:"):
            raise ObsidianCliError(
                f"笔记不存在: {path}",
                command=f"read {path}",
                public_message="Obsidian note was not found",
            )
        return output

    def create(self, path: str, content: str, overwrite: bool = False) -> str:
        self._require_relative_path(path)
        args = ["create", f"path={path}", f"content={content}"]
        if overwrite:
            args.append("overwrite")
        output = self._run(args)[1]
        if not self.config.dry_run:
            self._verify_write(path, content)
        return output

    def append(self, path: str, content: str, inline: bool = False) -> str:
        self._require_relative_path(path)
        args = ["append", f"path={path}", f"content={content}"]
        if inline:
            args.append("inline")
        output = self._run(args)[1]
        if not self.config.dry_run:
            read_back = self.read(path)
            if content not in read_back:
                error = ObsidianCliError("追加验证失败：内容未出现在笔记中")
                error.code = OBSIDIAN_WRITE_VERIFICATION_FAILED
                raise error
        return output

    def list_tags(self, file_path: str | None = None) -> list[str]:
        args = ["tags"]
        if file_path:
            self._require_relative_path(file_path)
            args.append(f"path={file_path}")
        return self._lines(self._run(args)[1])

    def list_tasks(self, done: bool | None = None) -> list[str]:
        args = ["tasks"]
        if done is True:
            args.append("done")
        elif done is False:
            args.append("todo")
        return self._lines(self._run(args)[1])

    def read_daily(self) -> str:
        return self._run(["daily:read"])[1]

    def append_daily(self, content: str) -> str:
        return self._run(["daily:append", f"content={content}"])[1]

    def get_daily_path(self) -> str:
        return self._run(["daily:path"])[1].strip()

    def list_files(
        self,
        folder: str | None = None,
        ext: str | None = None,
    ) -> list[str]:
        args = ["files"]
        if folder:
            self._require_relative_path(folder)
            args.append(f"folder={folder}")
        if ext:
            args.append(f"ext={str(ext).lstrip('.')}")
        return self._lines(self._run(args)[1])

    def file_count(self, folder: str | None = None, ext: str | None = None) -> int:
        args = ["files", "total"]
        if folder:
            self._require_relative_path(folder)
            args.append(f"folder={folder}")
        if ext:
            args.append(f"ext={str(ext).lstrip('.')}")
        output = self._run(args)[1]
        try:
            return int(output.strip())
        except (TypeError, ValueError):
            return 0

    def _verify_write(self, path: str, expected_content: str) -> None:
        try:
            read_back = self.read(path)
            key_lines = [
                line
                for line in expected_content.split("\n")
                if line.strip() and not line.startswith("---")
            ]
            if key_lines and not any(line in read_back for line in key_lines):
                error = ObsidianCliError(f"写入验证失败：{path}")
                error.code = OBSIDIAN_WRITE_VERIFICATION_FAILED
                raise error
        except ObsidianCliError:
            raise
        except Exception as exc:
            error = ObsidianCliError("写入验证异常")
            error.code = OBSIDIAN_WRITE_VERIFICATION_FAILED
            raise error from exc

    @property
    def operation_log(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._log]

    def health(self) -> dict[str, Any]:
        issues = self.config.validate()
        result: dict[str, Any] = {
            "available": self.config.ok(),
            "version": "未知",
            "vault_name": self.config.vault_name,
            "vault_path": self.config.vault_path,
            "vault_discovery_source": self.config.vault_discovery_source,
            "cli_path": self.config.cli_path,
            "cli_discovery_source": self.config.cli_discovery_source,
            "issues": issues,
            "dry_run": self.config.dry_run,
        }
        if self.config.ok():
            try:
                result["version"] = self.get_version()
            except ObsidianCliError as exc:
                result["issues"].append(f"版本查询失败: {exc}")
        return result

    @staticmethod
    def sanitize_filename(name: str) -> str:
        return re.sub(r'[\\/:*?"<>|]', "_", name).strip()

    @staticmethod
    def validate_path(path: str) -> bool:
        text = str(path or "").strip()
        if not text or "\x00" in text:
            return False
        windows = PureWindowsPath(text)
        posix = PurePosixPath(text.replace("\\", "/"))
        if windows.is_absolute() or posix.is_absolute() or windows.drive:
            return False
        return ".." not in posix.parts

    @classmethod
    def _require_relative_path(cls, path: str) -> None:
        if not cls.validate_path(path):
            raise ValueError("Obsidian path must stay inside the configured Vault")

    @staticmethod
    def _decode(value: bytes | str | None) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return value.decode("utf-8-sig", errors="replace").strip()

    @staticmethod
    def _lines(output: str) -> list[str]:
        return [
            line.strip()
            for line in output.splitlines()
            if line.strip() and not line.lower().startswith("no match")
        ]


ObsidianCli = ObsidianCliClient
