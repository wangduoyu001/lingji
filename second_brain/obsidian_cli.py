"""Compatibility wrapper for the Obsidian CLI.

P0 keeps the command surface in ``second_brain`` while making executable and
Vault discovery portable. The future formal implementation belongs in
``src/obsidian``.
"""
from __future__ import annotations

import json as _json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any, Mapping


DISCOVERY_ENVIRONMENT = "environment"
DISCOVERY_PATH = "path"
DISCOVERY_PLATFORM_LOCATION = "platform_location"
DISCOVERY_NOT_FOUND = "not_found"


@dataclass(frozen=True)
class ObsidianCliDiscovery:
    path: str = ""
    source: str = DISCOVERY_NOT_FOUND


class ObsidianCliError(Exception):
    def __init__(self, message: str, command: str = "", rc: int = -1, err: str = ""):
        super().__init__(message)
        self.command = command
        self.returncode = rc
        self.stderr = err


class ObsidianCliNotFound(ObsidianCliError):
    pass


class ObsidianCliTimeout(ObsidianCliError):
    pass


class ObsidianCliErrorResult(ObsidianCliError):
    pass


@dataclass
class ObsidianNote:
    path: str = ""
    content: str = ""
    vault: str = ""
    title: str = ""
    tags: list[str] = field(default_factory=list)
    frontmatter: dict[str, Any] = field(default_factory=dict)
    modified_at: str = ""


@dataclass
class ObsidianVaultInfo:
    name: str = ""
    path: str = ""
    file_count: int = 0
    folder_count: int = 0
    size: str = ""


def _platform_cli_candidates(
    *,
    platform: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> tuple[Path, ...]:
    """Return standard installation candidates without machine-specific paths."""
    env = os.environ if environ is None else environ
    current = (platform or sys.platform).lower()
    candidates: list[Path] = []

    if current.startswith("win"):
        for variable in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)"):
            root = str(env.get(variable, "") or "").strip()
            if root:
                if variable == "LOCALAPPDATA":
                    candidates.append(Path(root).expanduser() / "Programs" / "Obsidian" / "Obsidian.com")
                candidates.append(Path(root).expanduser() / "Obsidian" / "Obsidian.com")
    elif current == "darwin":
        candidates.extend(
            [
                Path("/Applications/Obsidian.app/Contents/MacOS/Obsidian"),
                Path.home() / "Applications/Obsidian.app/Contents/MacOS/Obsidian",
            ]
        )
    else:
        candidates.extend(
            [
                Path.home() / ".local/bin/obsidian",
                Path("/usr/local/bin/obsidian"),
                Path("/usr/bin/obsidian"),
            ]
        )

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate).casefold()
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return tuple(unique)


# Compatibility export. Values are generated from platform/environment instead
# of encoding a developer drive or user directory.
DEFAULT_CLI_PATHS: list[str] = [str(path) for path in _platform_cli_candidates()]


@dataclass
class ObsidianCliConfig:
    cli_path: str = ""
    vault_path: str = ""
    vault_name: str = ""
    timeout: int = 15
    dry_run: bool = False
    cli_discovery_source: str = DISCOVERY_NOT_FOUND
    vault_discovery_source: str = DISCOVERY_NOT_FOUND

    @classmethod
    def from_env(
        cls,
        *,
        workspace_vault_path: str | Path | None = None,
        runtime_vault_path: str | Path | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> "ObsidianCliConfig":
        env = os.environ if environ is None else environ
        explicit_cli = str(env.get("OBSIDIAN_CLI_PATH", "") or "").strip()
        discovery = (
            ObsidianCliDiscovery(explicit_cli, DISCOVERY_ENVIRONMENT)
            if explicit_cli
            else cls.discover(environ=env)
        )

        vault_path, vault_source = cls._resolve_vault_path(
            workspace_vault_path=workspace_vault_path,
            runtime_vault_path=runtime_vault_path,
            environ=env,
        )
        timeout_value = str(env.get("OBSIDIAN_CLI_TIMEOUT", "15") or "15")
        try:
            timeout = int(timeout_value)
        except (TypeError, ValueError):
            timeout = 15
        if timeout <= 0:
            timeout = 15

        return cls(
            cli_path=discovery.path,
            vault_path=vault_path,
            vault_name=cls._resolve_vault_name(vault_path=vault_path, environ=env),
            timeout=timeout,
            dry_run=str(env.get("OBSIDIAN_CLI_DRY_RUN", "0") or "0") == "1",
            cli_discovery_source=discovery.source,
            vault_discovery_source=vault_source,
        )

    @classmethod
    def discover(
        cls,
        *,
        environ: Mapping[str, str] | None = None,
        platform: str | None = None,
    ) -> ObsidianCliDiscovery:
        env = os.environ if environ is None else environ
        explicit = str(env.get("OBSIDIAN_CLI_PATH", "") or "").strip()
        if explicit:
            return ObsidianCliDiscovery(explicit, DISCOVERY_ENVIRONMENT)

        search_path = str(env.get("PATH", "") or "")
        for executable in ("Obsidian.com", "obsidian"):
            resolved = shutil.which(executable, path=search_path)
            if resolved:
                return ObsidianCliDiscovery(str(Path(resolved).expanduser()), DISCOVERY_PATH)

        for candidate in _platform_cli_candidates(platform=platform, environ=env):
            if candidate.is_file():
                return ObsidianCliDiscovery(str(candidate), DISCOVERY_PLATFORM_LOCATION)
        return ObsidianCliDiscovery()

    @classmethod
    def _detect(cls) -> str:
        """Compatibility method returning only the discovered path."""
        return cls.discover().path

    @staticmethod
    def _resolve_vault_path(
        *,
        workspace_vault_path: str | Path | None,
        runtime_vault_path: str | Path | None,
        environ: Mapping[str, str],
    ) -> tuple[str, str]:
        for value, source in (
            (workspace_vault_path, "workspace"),
            (runtime_vault_path, "runtime_settings"),
            (environ.get("OBSIDIAN_VAULT_PATH"), DISCOVERY_ENVIRONMENT),
            (environ.get("SECOND_BRAIN_OBSIDIAN_DIR"), DISCOVERY_ENVIRONMENT),
        ):
            text = str(value or "").strip()
            if text:
                return str(Path(text).expanduser()), source
        return "", DISCOVERY_NOT_FOUND


    @staticmethod
    def _resolve_vault_name(
        *,
        vault_path: str,
        environ: Mapping[str, str] | None = None,
    ) -> str:
        env = os.environ if environ is None else environ
        explicit = str(env.get("OBSIDIAN_VAULT_NAME", "") or "").strip()
        if explicit:
            return explicit
        if vault_path:
            name = PureWindowsPath(vault_path).name if "\\" in vault_path else Path(vault_path).name
            if name:
                return name
        return "本地知识库"

    def validate(self) -> list[str]:
        issues: list[str] = []
        if not self.cli_path or not os.path.isfile(self.cli_path):
            issues.append(f"CLI 未找到: {self.cli_path}")
        if not self.vault_path or not os.path.isdir(self.vault_path):
            issues.append(f"Vault 路径不存在: {self.vault_path}")
        if not self.vault_name:
            issues.append("Vault 名称未设置")
        return issues

    def ok(self) -> bool:
        return bool(self.cli_path) and os.path.isfile(self.cli_path)


class ObsidianCli:
    def __init__(self, config: ObsidianCliConfig | None = None):
        self.config = config or ObsidianCliConfig.from_env()
        self._log: list[dict[str, Any]] = []

    def _run(self, args: list[str], timeout: int | None = None,
             check: bool = True) -> tuple[int, str, str]:
        if not self.config.cli_path or not os.path.isfile(self.config.cli_path):
            raise ObsidianCliNotFound(
                "CLI 未找到，请安装 Obsidian 并在设置中启用命令行接口",
                command=self.config.cli_path,
            )

        cmd = [self.config.cli_path]
        if self.config.vault_name:
            cmd.append(f"vault={self.config.vault_name}")
        cmd.extend(args)
        cmd_str = " ".join(cmd)
        command_timeout = timeout if timeout is not None else self.config.timeout
        self._log.append({
            "time": datetime.now(timezone.utc).isoformat(),
            "command": cmd_str,
            "dry_run": self.config.dry_run,
        })

        if self.config.dry_run:
            print(f"[DRY-RUN] obsidian {' '.join(args)}")
            return 0, "", ""

        kwargs: dict[str, Any] = {
            "capture_output": True,
            "text": False,
            "timeout": command_timeout,
        }
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            proc = subprocess.run(cmd, **kwargs)
        except subprocess.TimeoutExpired as exc:
            self._log[-1]["error"] = "timeout"
            raise ObsidianCliTimeout("命令超时", command=cmd_str) from exc

        stdout = proc.stdout.decode("utf-8", errors="replace").strip()
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        if check and proc.returncode != 0:
            self._log[-1]["error"] = stderr
            raise ObsidianCliErrorResult(
                f"CLI 返回非零码: {proc.returncode}",
                command=cmd_str,
                rc=proc.returncode,
                err=stderr,
            )
        return proc.returncode, stdout, stderr

    def get_version(self) -> str:
        _, out, _ = self._run(["version"])
        return out.strip()

    def get_help(self) -> str:
        _, out, _ = self._run(["help"])
        return out

    def get_vault_info(self) -> ObsidianVaultInfo:
        _, name_out, _ = self._run(["vault", "info=name"])
        _, path_out, _ = self._run(["vault", "info=path"])
        return ObsidianVaultInfo(name=name_out.strip(), path=path_out.strip())

    def list_vaults(self) -> list[dict[str, str]]:
        _, out, _ = self._run(["vaults", "verbose"])
        result: list[dict[str, str]] = []
        for line in out.splitlines():
            line = line.strip()
            if line and "\t" in line:
                name, path = line.split("\t", 1)
                result.append({"name": name, "path": path})
        return result

    def search(self, query: str, limit: int = 20,
               path_filter: str | None = None) -> list[str]:
        args = ["search", f"query={query}", f"limit={limit}"]
        if path_filter:
            args.append(f"path={path_filter}")
        _, out, _ = self._run(args)
        return [line.strip() for line in out.splitlines()
                if line.strip() and not line.lower().startswith("no match")]

    def read(self, path: str) -> str:
        _, out, _ = self._run(["read", f"path={path}"])
        if out.strip().startswith("Error:"):
            raise ObsidianCliError(f"笔记不存在: {path}", command=f"read {path}")
        return out

    def create(self, path: str, content: str, overwrite: bool = False) -> str:
        args = ["create", f"path={path}", f"content={content}"]
        if overwrite:
            args.append("overwrite")
        _, out, _ = self._run(args)
        if not self.config.dry_run:
            self._verify_write(path, content)
        return out

    def append(self, path: str, content: str, inline: bool = False) -> str:
        args = ["append", f"path={path}", f"content={content}"]
        if inline:
            args.append("inline")
        _, out, _ = self._run(args)
        read_back = self.read(path)
        if content not in read_back:
            raise ObsidianCliError("追加验证失败：内容未出现在笔记中")
        return out

    def list_tags(self, file_path: str | None = None) -> list[str]:
        args = ["tags"]
        if file_path:
            args.append(f"path={file_path}")
        _, out, _ = self._run(args)
        return [line.strip() for line in out.splitlines()
                if line.strip() and not line.lower().startswith("no match")]

    def list_tasks(self, done: bool | None = None) -> list[str]:
        args = ["tasks"]
        if done is True:
            args.append("done")
        elif done is False:
            args.append("todo")
        _, out, _ = self._run(args)
        return [line.strip() for line in out.splitlines()
                if line.strip() and not line.lower().startswith("no match")]

    def read_daily(self) -> str:
        _, out, _ = self._run(["daily:read"])
        return out

    def append_daily(self, content: str) -> str:
        _, out, _ = self._run(["daily:append", f"content={content}"])
        return out

    def get_daily_path(self) -> str:
        _, out, _ = self._run(["daily:path"])
        return out.strip()

    def list_files(self, folder: str | None = None,
                   ext: str | None = None) -> list[str]:
        args = ["files"]
        if folder:
            args.append(f"folder={folder}")
        if ext:
            args.append(f"ext={ext}")
        _, out, _ = self._run(args)
        return [line.strip() for line in out.splitlines()
                if line.strip() and not line.lower().startswith("no match")]

    def file_count(self, folder: str | None = None,
                   ext: str | None = None) -> int:
        args = ["files", "total"]
        if folder:
            args.append(f"folder={folder}")
        if ext:
            args.append(f"ext={ext}")
        _, out, _ = self._run(args)
        try:
            return int(out.strip())
        except (TypeError, ValueError):
            return 0

    def _verify_write(self, path: str, expected_content: str) -> None:
        try:
            read_back = self.read(path)
            key_lines = [line for line in expected_content.split("\n")
                         if line.strip() and not line.startswith("---")]
            if key_lines and not any(line in read_back for line in key_lines):
                raise ObsidianCliError(f"写入验证失败：{path}")
        except ObsidianCliError:
            raise
        except Exception as exc:
            raise ObsidianCliError(f"写入验证异常: {exc}") from exc

    @property
    def operation_log(self) -> list[dict[str, Any]]:
        return list(self._log)

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
        normalized = Path(path).as_posix()
        return ".." not in normalized
