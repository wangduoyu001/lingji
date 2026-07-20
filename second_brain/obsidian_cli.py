"""
============================================
Obsidian CLI 统一操作层
============================================

本模块封装 Obsidian 官方 CLI (Obsidian.com) 的所有操作，
提供类型安全、编码兼容、超时控制的统一接口。

环境变量:
  OBSIDIAN_CLI_PATH      Obsidian.com 可执行文件路径
  OBSIDIAN_VAULT_PATH    Vault 目录路径
  OBSIDIAN_VAULT_NAME    Vault 名称
  OBSIDIAN_CLI_TIMEOUT   命令超时秒数 (默认 15)
  OBSIDIAN_CLI_DRY_RUN   设为 "1" 启用 dry-run 模式

异常类型:
  ObsidianCliError        通用 CLI 错误
  ObsidianCliNotFound     CLI 未找到
  ObsidianCliTimeout      命令超时
  ObsidianCliErrorResult  CLI 返回非零退出码

安全规则:
  - 禁止任意命令拼接
  - 不允许外部输入直接成为 Shell 命令
  - Windows 下用 subprocess.run(list) 不需要 shell 引用，直接传参
  - 写操作后自动验证
"""

from __future__ import annotations

import json as _json
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CLI_PATHS: list[str] = [
    r"D:\Program Files (x86)\Obsidian\Obsidian.com",
    r"C:\Program Files\Obsidian\Obsidian.com",
    r"C:\Program Files (x86)\Obsidian\Obsidian.com",
]


class ObsidianCliError(Exception):
    """Obsidian CLI 通用错误"""
    def __init__(self, message: str, command: str = "", rc: int = -1, err: str = ""):
        super().__init__(message)
        self.command = command
        self.returncode = rc
        self.stderr = err


class ObsidianCliNotFound(ObsidianCliError):
    """Obsidian CLI 可执行文件未找到"""
    pass


class ObsidianCliTimeout(ObsidianCliError):
    """Obsidian CLI 命令超时"""
    pass


class ObsidianCliErrorResult(ObsidianCliError):
    """Obsidian CLI 返回非零退出码"""
    pass


@dataclass
class ObsidianNote:
    """表示一篇 Obsidian 笔记"""
    path: str = ""
    content: str = ""
    vault: str = ""
    title: str = ""
    tags: list[str] = field(default_factory=list)
    frontmatter: dict[str, Any] = field(default_factory=dict)
    modified_at: str = ""


@dataclass
class ObsidianVaultInfo:
    """Vault 信息"""
    name: str = ""
    path: str = ""
    file_count: int = 0
    folder_count: int = 0
    size: str = ""


@dataclass
class ObsidianCliConfig:
    """Obsidian CLI 配置，从环境变量读取"""

    cli_path: str = ""
    vault_path: str = ""
    vault_name: str = ""
    timeout: int = 15
    dry_run: bool = False

    @classmethod
    def from_env(cls) -> ObsidianCliConfig:
        """从环境变量加载配置"""
        cp = os.getenv("OBSIDIAN_CLI_PATH", "") or cls._detect()
        vp = os.getenv("OBSIDIAN_VAULT_PATH", "") or os.getenv("SECOND_BRAIN_OBSIDIAN_DIR", "")
        vn = os.getenv("OBSIDIAN_VAULT_NAME", "\u672c\u5730\u77e5\u8bc6\u5e93")
        ts = os.getenv("OBSIDIAN_CLI_TIMEOUT", "15")
        dr = os.getenv("OBSIDIAN_CLI_DRY_RUN", "0") == "1"
        try:
            to = int(ts)
        except (ValueError, TypeError):
            to = 15
        return cls(cli_path=cp, vault_path=vp, vault_name=vn, timeout=to, dry_run=dr)

    @classmethod
    def _detect(cls) -> str:
        """自动探测 Obsidian.com 路径"""
        for p in DEFAULT_CLI_PATHS:
            if os.path.isfile(p):
                return p
        for d in os.environ.get("PATH", "").split(os.pathsep):
            c = os.path.join(d, "Obsidian.com")
            if os.path.isfile(c):
                return c
        return ""

    def validate(self) -> list[str]:
        """验证配置，返回所有问题列表"""
        issues: list[str] = []
        if not self.cli_path or not os.path.isfile(self.cli_path):
            issues.append(f"CLI \u672a\u627e\u5230: {self.cli_path}")
        if not self.vault_path or not os.path.isdir(self.vault_path):
            issues.append(f"Vault \u8def\u5f84\u4e0d\u5b58\u5728: {self.vault_path}")
        if not self.vault_name:
            issues.append("Vault \u540d\u79f0\u672a\u8bbe\u7f6e")
        return issues

    def ok(self) -> bool:
        """CLI \u662f\u5426\u53ef\u7528"""
        return bool(self.cli_path) and os.path.isfile(self.cli_path)


class ObsidianCli:
    """Obsidian \u5b98\u65b9 CLI \u64cd\u4f5c\u5c01\u88c5"""

    def __init__(self, config: ObsidianCliConfig | None = None):
        self.config = config or ObsidianCliConfig.from_env()
        self._log: list[dict[str, Any]] = []

    # ---------- \u5e95\u5c42\u547d\u4ee4\u6267\u884c ----------

    def _run(self, args: list[str], timeout: int | None = None,
             check: bool = True) -> tuple[int, str, str]:
        """\u6267\u884c Obsidian CLI \u547d\u4ee4\n\n        \u53c2\u6570:\n            args: \u547d\u4ee4\u53c2\u6570\u5217\u8868\n            timeout: \u8d85\u65f6\u79d2\u6570\n            check: \u662f\u5426\u68c0\u67e5\u8fd4\u56de\u7801\n\n        \u8fd4\u56de:\n            (returncode, stdout, stderr)\n\n        \u5f02\u5e38:\n            ObsidianCliNotFound: CLI \u4e0d\u5b58\u5728\n            ObsidianCliTimeout: \u547d\u4ee4\u8d85\u65f6\n            ObsidianCliErrorResult: \u547d\u4ee4\u8fd4\u56de\u975e\u96f6\u9000\u51fa\u7801\n        """
        if not self.config.cli_path or not os.path.isfile(self.config.cli_path):
            raise ObsidianCliNotFound(
                "CLI \u672a\u627e\u5230\uff0c\u8bf7\u5b89\u88c5 Obsidian \u5e76\u5728\u8bbe\u7f6e\u4e2d\u542f\u7528\u547d\u4ee4\u884c\u63a5\u53e3",
                command=self.config.cli_path,
            )

        cmd = [self.config.cli_path]
        if self.config.vault_name:
            cmd.append(f"vault={self.config.vault_name}")
        cmd.extend(args)

        cmd_str = " ".join(cmd)
        t = timeout if timeout is not None else self.config.timeout

        self._log.append({
            "time": datetime.now(timezone.utc).isoformat(),
            "command": cmd_str,
            "dry_run": self.config.dry_run,
        })

        if self.config.dry_run:
            print(f"[DRY-RUN] obsidian {' '.join(args)}")
            return 0, "", ""

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=False, timeout=t,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except subprocess.TimeoutExpired:
            self._log[-1]["error"] = "timeout"
            raise ObsidianCliTimeout(f"\u547d\u4ee4\u8d85\u65f6", command=cmd_str)

        stdout = proc.stdout.decode('utf-8', errors='replace').strip()
        stderr = proc.stderr.decode('utf-8', errors='replace').strip()

        if check and proc.returncode != 0:
            self._log[-1]["error"] = stderr
            raise ObsidianCliErrorResult(
                f"CLI \u8fd4\u56de\u975e\u96f6\u7801: {proc.returncode}",
                command=cmd_str, rc=proc.returncode, err=stderr,
            )

        return proc.returncode, stdout, stderr

    # ---------- \u67e5\u8be2 ----------

    def get_version(self) -> str:
        """\u83b7\u53d6 Obsidian \u7248\u672c\u53f7"""
        _, out, _ = self._run(["version"])
        return out.strip()

    def get_help(self) -> str:
        """\u83b7\u53d6 CLI \u5e2e\u52a9\u4fe1\u606f"""
        _, out, _ = self._run(["help"])
        return out

    def get_vault_info(self) -> ObsidianVaultInfo:
        """\u83b7\u53d6\u5f53\u524d Vault \u4fe1\u606f"""
        _, name_out, _ = self._run(["vault", "info=name"])
        _, path_out, _ = self._run(["vault", "info=path"])
        return ObsidianVaultInfo(name=name_out.strip(), path=path_out.strip())

    def list_vaults(self) -> list[dict[str, str]]:
        """\u5217\u51fa\u6240\u6709\u5df2\u77e5 Vault"""
        _, out, _ = self._run(["vaults", "verbose"])
        result: list[dict[str, str]] = []
        for line in out.splitlines():
            line = line.strip()
            if line and "\t" in line:
                parts = line.split("\t", 1)
                result.append({"name": parts[0], "path": parts[1]})
        return result

    # ---------- \u641c\u7d22\u548c\u8bfb\u53d6 ----------

    def search(self, query: str, limit: int = 20, path_filter: str | None = None) -> list[str]:
        """\u641c\u7d22\u7b14\u8bb0"""
        args = ["search", f"query={query}",
                f"limit={limit}"]
        if path_filter:
            args.append(f"path={path_filter}")
        _, out, _ = self._run(args)
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        # 过滤 "No matches found" 类提示
        return [l for l in lines if not l.lower().startswith('no match')]

    def read(self, path: str) -> str:
        """\u8bfb\u53d6\u7b14\u8bb0\u5185\u5bb9"""
        _, out, _ = self._run(["read", f"path={path}"])
        if out.strip().startswith("Error:"):
            raise ObsidianCliError(f"笔记不存在: {path}", command=f"read {path}")
        return out

    def create(self, path: str, content: str, overwrite: bool = False) -> str:
        """\u521b\u5efa\u65b0\u7b14\u8bb0"""
        args = ["create", f"path={path}",
                f"content={content}"]
        if overwrite:
            args.append("overwrite")
        _, out, _ = self._run(args)
        # dry-run 模式不需要验证
        if not self.config.dry_run:
            self._verify_write(path, content)
        return out

    def append(self, path: str, content: str, inline: bool = False) -> str:
        """\u8ffd\u52a0\u5185\u5bb9\u5230\u7b14\u8bb0"""
        args = ["append", f"path={path}",
                f"content={content}"]
        if inline:
            args.append("inline")
        _, out, _ = self._run(args)
        read_back = self.read(path)
        if content not in read_back:
            raise ObsidianCliError("\u8ffd\u52a0\u9a8c\u8bc1\u5931\u8d25\uff1a\u5185\u5bb9\u672a\u51fa\u73b0\u5728\u7b14\u8bb0\u4e2d")
        return out

    # ---------- \u4efb\u52a1\u548c\u6807\u7b7e ----------

    def list_tags(self, file_path: str | None = None) -> list[str]:
        """\u5217\u51fa\u6807\u7b7e"""
        args = ["tags"]
        if file_path:
            args.append(f"path={file_path}")
        _, out, _ = self._run(args)
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        # 过滤 "No matches found" 类提示
        return [l for l in lines if not l.lower().startswith('no match')]

    def list_tasks(self, done: bool | None = None) -> list[str]:
        """\u5217\u51fa\u4efb\u52a1"""
        args = ["tasks"]
        if done is True:
            args.append("done")
        elif done is False:
            args.append("todo")
        _, out, _ = self._run(args)
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        # 过滤 "No matches found" 类提示
        return [l for l in lines if not l.lower().startswith('no match')]

    # ---------- Daily Note ----------

    def read_daily(self) -> str:
        """\u8bfb\u53d6\u4eca\u65e5 Daily Note"""
        _, out, _ = self._run(["daily:read"])
        return out

    def append_daily(self, content: str) -> str:
        """\u8ffd\u52a0\u5185\u5bb9\u5230\u4eca\u65e5 Daily Note"""
        _, out, _ = self._run(["daily:append", f"content={content}"])
        return out

    def get_daily_path(self) -> str:
        """\u83b7\u53d6\u4eca\u65e5 Daily Note \u8def\u5f84"""
        _, out, _ = self._run(["daily:path"])
        return out.strip()

    # ---------- \u6587\u4ef6\u64cd\u4f5c ----------

    def list_files(self, folder: str | None = None,
                   ext: str | None = None) -> list[str]:
        """\u5217\u51fa Vault \u4e2d\u7684\u6587\u4ef6"""
        args = ["files"]
        if folder:
            args.append(f"folder={folder}")
        if ext:
            args.append(f"ext={ext}")
        _, out, _ = self._run(args)
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        # 过滤 "No matches found" 类提示
        return [l for l in lines if not l.lower().startswith('no match')]

    def file_count(self, folder: str | None = None,
                   ext: str | None = None) -> int:
        """\u83b7\u53d6\u6587\u4ef6\u6570\u91cf"""
        args = ["files", "total"]
        if folder:
            args.append(f"folder={folder}")
        if ext:
            args.append(f"ext={ext}")
        _, out, _ = self._run(args)
        try:
            return int(out.strip())
        except (ValueError, TypeError):
            return 0

    # ---------- \u9a8c\u8bc1 ----------

    def _verify_write(self, path: str, expected_content: str) -> None:
        """\u5199\u5165\u540e\u9a8c\u8bc1"""
        try:
            read_back = self.read(path)
            key_lines = [
                l for l in expected_content.split("\n")
                if l.strip() and not l.startswith("---")
            ]
            if key_lines:
                found = sum(1 for l in key_lines if l in read_back)
                if found < 1:
                    raise ObsidianCliError(f"\u5199\u5165\u9a8c\u8bc1\u5931\u8d25\uff1a{path}")
        except ObsidianCliError:
            raise
        except Exception as e:
            raise ObsidianCliError(f"\u5199\u5165\u9a8c\u8bc1\u5f02\u5e38: {e}")

    # ---------- \u65e5\u5fd7\u548c\u72b6\u6001 ----------

    @property
    def operation_log(self) -> list[dict[str, Any]]:
        """\u83b7\u53d6\u64cd\u4f5c\u65e5\u5fd7"""
        return list(self._log)

    def health(self) -> dict[str, Any]:
        """CLI \u5065\u5eb7\u68c0\u67e5"""
        issues = self.config.validate()
        result: dict[str, Any] = {
            "available": self.config.ok(),
            "version": "\u672a\u77e5",
            "vault_name": self.config.vault_name,
            "vault_path": self.config.vault_path,
            "cli_path": self.config.cli_path,
            "issues": issues,
            "dry_run": self.config.dry_run,
        }
        if self.config.ok():
            try:
                result["version"] = self.get_version()
            except ObsidianCliError as e:
                result["issues"].append(f"\u7248\u672c\u67e5\u8be2\u5931\u8d25: {e}")
        return result

    # ---------- \u5b89\u5168\u5de5\u5177 ----------

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """\u5b89\u5168\u5316\u6587\u4ef6\u540d\uff1a\u79fb\u9664 Windows \u975e\u6cd5\u5b57\u7b26"""
        return re.sub(r'[\\\\/:*?"<>|]', "_", name).strip()

    @staticmethod
    def validate_path(path: str) -> bool:
        """\u9a8c\u8bc1\u8def\u5f84\u662f\u5426\u5b89\u5168\uff08\u4e0d\u5305\u542b\u8def\u5f84\u904d\u5386\u653b\u51fb\uff09"""
        normalized = Path(path).as_posix()
        return ".." not in normalized
