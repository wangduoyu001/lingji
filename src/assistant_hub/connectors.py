from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

_CONNECTOR_IDS = {"codex", "claude_code", "workbuddy"}
_SERVER_NAME = "lingji-memory"
_MCP_HOST = "127.0.0.1"
_MCP_PORT = 8767
_MCP_URL = f"http://{_MCP_HOST}:{_MCP_PORT}/mcp"
_MANAGED_BEGIN = "# BEGIN LINGJI MANAGED MCP: lingji-memory"
_MANAGED_END = "# END LINGJI MANAGED MCP: lingji-memory"
_CODEX_TABLE = re.compile(r'^\s*\[mcp_servers\.(?:"lingji-memory"|lingji-memory)\]\s*$', re.MULTILINE)


class ConnectorError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


Runner = Callable[[Sequence[str], float], subprocess.CompletedProcess[str]]


def _default_runner(command: Sequence[str], timeout: float) -> subprocess.CompletedProcess[str]:
    creationflags = 0
    startupinfo = None
    if os.name == "nt":
        creationflags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
    return subprocess.run(
        list(command),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        creationflags=creationflags,
        startupinfo=startupinfo,
    )


class AiMemoryConnectorService:
    """Preview, apply, test and roll back supported local AI MCP connectors.

    The service never accepts arbitrary commands or arbitrary target paths. It owns
    one managed Codex TOML block, delegates Claude changes to the official CLI, and
    only emits a copyable WorkBuddy configuration because no stable local config
    file is part of WorkBuddy's public contract.
    """

    def __init__(
        self,
        *,
        storage_path: Path | str,
        home: Path | str | None = None,
        env: Mapping[str, str] | None = None,
        runner: Runner | None = None,
        timeout_seconds: float = 12.0,
    ) -> None:
        self.storage_path = Path(storage_path).expanduser().resolve(strict=False)
        self.home = Path(home or Path.home()).expanduser().resolve(strict=False)
        self.env = dict(os.environ) if env is None else dict(env)
        self.runner = runner or _default_runner
        self.timeout_seconds = max(1.0, float(timeout_seconds))
        self.backup_root = self.storage_path / "assistant_hub" / "connector_backups"
        self.state_path = self.storage_path / "assistant_hub" / "connector_state.json"
        self.token_path = self.storage_path / "mcp_http_token"

    @property
    def mcp_url(self) -> str:
        return _MCP_URL

    def status(self, *, live: bool = False) -> dict[str, Any]:
        state = self._read_state()
        runtime_ready = self._runtime_ready()
        connectors = [
            self._codex_status(state, live=live),
            self._claude_status(state, live=live),
            self._workbuddy_status(state),
        ]
        return {
            "schema_version": 1,
            "as_of": datetime.now(timezone.utc).isoformat(),
            "mcp_runtime": {
                "state": "ready" if runtime_ready else "unavailable",
                "ready": runtime_ready,
                "host": _MCP_HOST,
                "port": _MCP_PORT,
                "url": _MCP_URL,
                "authentication": "bearer_token",
                "loopback_only": True,
            },
            "shared_memory_policy": {
                "owner_approved_memory_only": True,
                "automatic_core_memory_write": False,
                "candidate_write_available": True,
                "agent_scope": "shared_owner_memory_v1",
            },
            "connectors": connectors,
        }

    def preview(self, connector_id: str) -> dict[str, Any]:
        connector_id = self._connector_id(connector_id)
        token = self._token()
        if connector_id == "codex":
            path = self._codex_config_path()
            current = self._read_text(path)
            conflict = self._codex_conflict(current)
            proposed = self._codex_managed_block(token)
            return self._preview_payload(
                connector_id,
                mode="managed_file_update",
                target=self._display_path(path),
                supported=not conflict,
                conflict=conflict,
                changes=[
                    "备份现有 ~/.codex/config.toml（如果存在）",
                    "只新增或替换 LingJi 管理的 MCP 区块",
                    "连接本机 127.0.0.1:8767，不改模型、账号或沙箱设置",
                ],
                preview=proposed.replace(token, "<本机令牌已隐藏>"),
                confirmation="CONNECT_CODEX_TO_LINGJI",
            )
        if connector_id == "claude_code":
            executable = shutil.which("claude", path=self.env.get("PATH"))
            command = self._claude_add_command(token, executable or "claude")
            return self._preview_payload(
                connector_id,
                mode="official_cli",
                target="Claude Code user-scope MCP configuration",
                supported=bool(executable),
                conflict=False,
                changes=[
                    "备份 ~/.claude.json（如果存在）",
                    "调用官方 claude mcp add --scope user",
                    "仅新增名为 lingji-memory 的 HTTP MCP Server",
                ],
                preview=" ".join(command).replace(token, "<本机令牌已隐藏>"),
                confirmation="CONNECT_CLAUDE_TO_LINGJI",
                unavailable_reason="未找到 claude 命令" if not executable else "",
            )
        config = self._workbuddy_config(token)
        return self._preview_payload(
            connector_id,
            mode="copy_configuration",
            target="WorkBuddy / CodeBuddy 自定义 MCP 连接器",
            supported=True,
            conflict=False,
            changes=[
                "不修改 WorkBuddy 本地文件",
                "复制配置到官方自定义连接器/MCP 页面",
                "由 WorkBuddy 自己保存并验证连接",
            ],
            preview=json.dumps(self._redact_token(config), ensure_ascii=False, indent=2),
            confirmation="COPY_WORKBUDDY_LINGJI_CONFIG",
            copy_payload=json.dumps(config, ensure_ascii=False, indent=2),
        )

    def apply(self, connector_id: str, confirmation: str) -> dict[str, Any]:
        connector_id = self._connector_id(connector_id)
        expected = {
            "codex": "CONNECT_CODEX_TO_LINGJI",
            "claude_code": "CONNECT_CLAUDE_TO_LINGJI",
            "workbuddy": "COPY_WORKBUDDY_LINGJI_CONFIG",
        }[connector_id]
        if confirmation != expected:
            raise ConnectorError("CONFIRMATION_REQUIRED", "连接操作需要明确确认", status_code=403)
        token = self._token()
        if connector_id == "codex":
            result = self._apply_codex(token)
        elif connector_id == "claude_code":
            result = self._apply_claude(token)
        else:
            result = {
                "connector_id": connector_id,
                "state": "manual_action_required",
                "message": "WorkBuddy 未公开稳定本地配置文件。配置已生成，请粘贴到官方自定义连接器页面。",
                "copy_payload": json.dumps(self._workbuddy_config(token), ensure_ascii=False, indent=2),
            }
        return {**result, "mcp_runtime_ready": self._runtime_ready()}

    def test(self, connector_id: str) -> dict[str, Any]:
        connector_id = self._connector_id(connector_id)
        runtime_ready = self._runtime_ready()
        if connector_id == "codex":
            config_present = self._managed_block(self._read_text(self._codex_config_path())) is not None
            executable = shutil.which("codex", path=self.env.get("PATH"))
            cli_ok = None
            detail = "未找到 codex 命令；已完成配置文件检查"
            if executable:
                completed = self._run([executable, "mcp", "list"])
                cli_ok = completed.returncode == 0 and _SERVER_NAME in (completed.stdout + completed.stderr)
                detail = self._command_detail(completed, success="Codex 已列出 lingji-memory")
            ok = bool(runtime_ready and config_present and (cli_ok is not False))
            return self._test_payload(connector_id, ok, runtime_ready, config_present, cli_ok, detail)
        if connector_id == "claude_code":
            executable = shutil.which("claude", path=self.env.get("PATH"))
            if not executable:
                return self._test_payload(connector_id, False, runtime_ready, False, False, "未找到 claude 命令")
            completed = self._run([executable, "mcp", "get", _SERVER_NAME])
            cli_ok = completed.returncode == 0
            detail = self._command_detail(completed, success="Claude Code 已读取 lingji-memory 配置")
            return self._test_payload(connector_id, bool(runtime_ready and cli_ok), runtime_ready, cli_ok, cli_ok, detail)
        return {
            "connector_id": connector_id,
            "state": "manual_test_required",
            "ok": False,
            "mcp_runtime_ready": runtime_ready,
            "message": "请在 WorkBuddy 连接器页面运行官方连接测试。",
        }

    def rollback(self, connector_id: str, confirmation: str) -> dict[str, Any]:
        connector_id = self._connector_id(connector_id)
        if confirmation != f"DISCONNECT_{connector_id.upper()}_FROM_LINGJI":
            raise ConnectorError("CONFIRMATION_REQUIRED", "断开操作需要明确确认", status_code=403)
        if connector_id == "codex":
            path = self._codex_config_path()
            current = self._read_text(path)
            updated = self._remove_managed_block(current)
            if updated != current:
                self._backup(path, "codex")
                self._write_text_atomic(path, updated)
            self._set_managed(connector_id, False)
            return {"connector_id": connector_id, "state": "disconnected", "message": "已移除 LingJi 管理的 Codex MCP 区块。"}
        if connector_id == "claude_code":
            executable = shutil.which("claude", path=self.env.get("PATH"))
            if not executable:
                raise ConnectorError("CLIENT_NOT_FOUND", "未找到 claude 命令", status_code=409)
            completed = self._run([executable, "mcp", "remove", "--scope", "user", _SERVER_NAME])
            if completed.returncode != 0:
                raise ConnectorError("CLIENT_COMMAND_FAILED", self._command_detail(completed), status_code=409)
            self._set_managed(connector_id, False)
            return {"connector_id": connector_id, "state": "disconnected", "message": "已通过 Claude Code 官方 CLI 移除 lingji-memory。"}
        return {"connector_id": connector_id, "state": "manual_action_required", "message": "请在 WorkBuddy 连接器页面解绑 lingji-memory。"}

    def _codex_status(self, state: Mapping[str, Any], *, live: bool) -> dict[str, Any]:
        path = self._codex_config_path()
        current = self._read_text(path)
        managed = self._managed_block(current) is not None
        conflict = self._codex_conflict(current)
        verified = self._state_connector(state, "codex").get("last_test_ok")
        if live and managed and shutil.which("codex", path=self.env.get("PATH")):
            verified = self.test("codex")["ok"]
        return {
            "id": "codex",
            "label": "Codex",
            "configuration_state": "conflict" if conflict else "configured" if managed else "not_configured",
            "managed_by_lingji": managed,
            "live_test": verified,
            "one_click_supported": not conflict,
            "target": self._display_path(path),
            "next_action": "测试连接" if managed else "预览并连接",
        }

    def _claude_status(self, state: Mapping[str, Any], *, live: bool) -> dict[str, Any]:
        executable = shutil.which("claude", path=self.env.get("PATH"))
        managed = bool(self._state_connector(state, "claude_code").get("managed"))
        verified = self._state_connector(state, "claude_code").get("last_test_ok")
        if live and executable and managed:
            verified = self.test("claude_code")["ok"]
        return {
            "id": "claude_code",
            "label": "Claude Code",
            "configuration_state": "configured" if managed else "not_configured" if executable else "client_not_found",
            "managed_by_lingji": managed,
            "live_test": verified,
            "one_click_supported": bool(executable),
            "target": "Claude Code user scope",
            "next_action": "测试连接" if managed else "预览并连接" if executable else "先安装 Claude Code",
        }

    def _workbuddy_status(self, state: Mapping[str, Any]) -> dict[str, Any]:
        managed = bool(self._state_connector(state, "workbuddy").get("managed"))
        return {
            "id": "workbuddy",
            "label": "WorkBuddy / CodeBuddy",
            "configuration_state": "manual_configuration",
            "managed_by_lingji": managed,
            "live_test": None,
            "one_click_supported": False,
            "target": "官方自定义连接器页面",
            "next_action": "复制配置",
        }

    def _apply_codex(self, token: str) -> dict[str, Any]:
        path = self._codex_config_path()
        current = self._read_text(path)
        if self._codex_conflict(current):
            raise ConnectorError("CONFIG_CONFLICT", "Codex 已有非 LingJi 管理的同名 MCP 配置，请先手动处理。", status_code=409)
        updated = self._replace_managed_block(current, self._codex_managed_block(token))
        try:
            tomllib.loads(updated or "")
        except tomllib.TOMLDecodeError as exc:
            raise ConnectorError("INVALID_EXISTING_CONFIG", "现有 Codex config.toml 无法安全解析，未写入。", status_code=409) from exc
        backup = self._backup(path, "codex")
        self._write_text_atomic(path, updated)
        self._set_managed("codex", True, backup=backup)
        return {
            "connector_id": "codex",
            "state": "configured",
            "message": "已写入 LingJi 管理的 Codex MCP 配置。重启 Codex 或新建会话后生效。",
            "target": self._display_path(path),
            "backup_created": bool(backup),
        }

    def _apply_claude(self, token: str) -> dict[str, Any]:
        executable = shutil.which("claude", path=self.env.get("PATH"))
        if not executable:
            raise ConnectorError("CLIENT_NOT_FOUND", "未找到 claude 命令", status_code=409)
        state = self._read_state()
        managed = bool(self._state_connector(state, "claude_code").get("managed"))
        existing = self._run([executable, "mcp", "get", _SERVER_NAME])
        if existing.returncode == 0 and not managed:
            raise ConnectorError("CONFIG_CONFLICT", "Claude Code 已有非 LingJi 管理的同名 MCP 配置。", status_code=409)
        config_path = self.home / ".claude.json"
        backup = self._backup(config_path, "claude_code")
        if existing.returncode == 0:
            removed = self._run([executable, "mcp", "remove", "--scope", "user", _SERVER_NAME])
            if removed.returncode != 0:
                raise ConnectorError("CLIENT_COMMAND_FAILED", self._command_detail(removed), status_code=409)
        completed = self._run(self._claude_add_command(token, executable))
        if completed.returncode != 0:
            self._restore_latest_backup(config_path, backup)
            raise ConnectorError("CLIENT_COMMAND_FAILED", self._command_detail(completed), status_code=409)
        self._set_managed("claude_code", True, backup=backup)
        return {
            "connector_id": "claude_code",
            "state": "configured",
            "message": "已通过 Claude Code 官方 CLI 添加 user-scope lingji-memory。新建会话后生效。",
            "target": "Claude Code user scope",
            "backup_created": bool(backup),
        }

    def _claude_add_command(self, token: str, executable: str) -> list[str]:
        return [
            executable,
            "mcp",
            "add",
            "--transport",
            "http",
            "--scope",
            "user",
            "--header",
            f"Authorization: Bearer {token}",
            _SERVER_NAME,
            _MCP_URL,
        ]

    def _codex_managed_block(self, token: str) -> str:
        return (
            f"{_MANAGED_BEGIN}\n"
            f"[mcp_servers.{_SERVER_NAME}]\n"
            f'url = "{_MCP_URL}"\n'
            f'http_headers = {{ Authorization = "Bearer {token}" }}\n'
            "enabled = true\n"
            "startup_timeout_sec = 15.0\n"
            "tool_timeout_sec = 120.0\n"
            f"{_MANAGED_END}"
        )

    def _workbuddy_config(self, token: str) -> dict[str, Any]:
        return {
            "mcpServers": {
                _SERVER_NAME: {
                    "type": "http",
                    "url": _MCP_URL,
                    "headers": {"Authorization": f"Bearer {token}"},
                    "description": "LingJi owner-approved shared memory gateway",
                }
            }
        }

    @staticmethod
    def _redact_token(payload: Mapping[str, Any]) -> dict[str, Any]:
        copied = json.loads(json.dumps(payload))
        copied["mcpServers"][_SERVER_NAME]["headers"]["Authorization"] = "Bearer <本机令牌已隐藏>"
        return copied

    @staticmethod
    def _preview_payload(
        connector_id: str,
        *,
        mode: str,
        target: str,
        supported: bool,
        conflict: bool,
        changes: list[str],
        preview: str,
        confirmation: str,
        unavailable_reason: str = "",
        copy_payload: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "connector_id": connector_id,
            "mode": mode,
            "target": target,
            "supported": supported,
            "conflict": conflict,
            "changes": changes,
            "preview": preview,
            "confirmation": confirmation,
            "unavailable_reason": unavailable_reason,
        }
        if copy_payload is not None:
            payload["copy_payload"] = copy_payload
        return payload

    @staticmethod
    def _test_payload(
        connector_id: str,
        ok: bool,
        runtime_ready: bool,
        config_present: bool,
        client_verified: bool | None,
        detail: str,
    ) -> dict[str, Any]:
        return {
            "connector_id": connector_id,
            "state": "connected" if ok else "failed",
            "ok": ok,
            "mcp_runtime_ready": runtime_ready,
            "config_present": config_present,
            "client_verified": client_verified,
            "message": detail,
        }

    def _run(self, command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        try:
            return self.runner(command, self.timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            raise ConnectorError("CLIENT_COMMAND_TIMEOUT", "客户端配置命令超时", status_code=504) from exc
        except OSError as exc:
            raise ConnectorError("CLIENT_COMMAND_FAILED", "无法启动客户端配置命令", status_code=409) from exc

    @staticmethod
    def _command_detail(completed: subprocess.CompletedProcess[str], *, success: str = "命令执行成功") -> str:
        if completed.returncode == 0:
            return success
        output = (completed.stderr or completed.stdout or "").strip().splitlines()
        return output[-1][:300] if output else f"客户端命令失败，退出码 {completed.returncode}"

    def _runtime_ready(self) -> bool:
        try:
            with socket.create_connection((_MCP_HOST, _MCP_PORT), timeout=0.35):
                return True
        except OSError:
            return False

    def _token(self) -> str:
        try:
            existing = self.token_path.read_text(encoding="utf-8").strip()
        except OSError:
            existing = ""
        if existing:
            return existing
        token = secrets.token_urlsafe(32)
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_text_atomic(self.token_path, token + "\n")
        try:
            self.token_path.chmod(0o600)
        except OSError:
            pass
        return token

    def _codex_config_path(self) -> Path:
        configured = str(self.env.get("CODEX_HOME") or "").strip()
        root = Path(configured).expanduser() if configured else self.home / ".codex"
        return root.resolve(strict=False) / "config.toml"

    def _display_path(self, path: Path) -> str:
        try:
            relative = path.resolve(strict=False).relative_to(self.home)
            return f"~/{relative.as_posix()}"
        except (OSError, ValueError):
            return f"<local>/{path.name}"

    @staticmethod
    def _read_text(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8-sig")
        except FileNotFoundError:
            return ""
        except OSError as exc:
            raise ConnectorError("CONFIG_READ_FAILED", "无法读取客户端配置", status_code=409) from exc

    @staticmethod
    def _write_text_atomic(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".lingji.tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)

    def _backup(self, path: Path, connector_id: str) -> str:
        if not path.is_file():
            return ""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target_dir = self.backup_root / connector_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{timestamp}-{path.name}.bak"
        shutil.copy2(path, target)
        return str(target)

    @staticmethod
    def _restore_latest_backup(path: Path, backup: str) -> None:
        if not backup:
            return
        source = Path(backup)
        if source.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, path)

    @staticmethod
    def _managed_block(content: str) -> str | None:
        start = content.find(_MANAGED_BEGIN)
        end = content.find(_MANAGED_END)
        if start < 0 or end < start:
            return None
        return content[start : end + len(_MANAGED_END)]

    def _codex_conflict(self, content: str) -> bool:
        without_managed = self._remove_managed_block(content)
        return bool(_CODEX_TABLE.search(without_managed))

    def _replace_managed_block(self, content: str, block: str) -> str:
        cleaned = self._remove_managed_block(content).rstrip()
        return f"{cleaned}\n\n{block}\n" if cleaned else f"{block}\n"

    @staticmethod
    def _remove_managed_block(content: str) -> str:
        start = content.find(_MANAGED_BEGIN)
        if start < 0:
            return content
        end = content.find(_MANAGED_END, start)
        if end < 0:
            return content
        end += len(_MANAGED_END)
        return (content[:start] + content[end:]).strip() + ("\n" if content[:start] + content[end:] else "")

    def _read_state(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return {"schema_version": 1, "connectors": {}}
        return payload if isinstance(payload, dict) else {"schema_version": 1, "connectors": {}}

    @staticmethod
    def _state_connector(state: Mapping[str, Any], connector_id: str) -> dict[str, Any]:
        connectors = state.get("connectors") if isinstance(state, Mapping) else None
        value = connectors.get(connector_id) if isinstance(connectors, Mapping) else None
        return dict(value) if isinstance(value, Mapping) else {}

    def _set_managed(self, connector_id: str, managed: bool, *, backup: str = "") -> None:
        state = self._read_state()
        connectors = state.setdefault("connectors", {})
        existing = connectors.get(connector_id) if isinstance(connectors, dict) else None
        record = dict(existing) if isinstance(existing, dict) else {}
        record.update(
            {
                "managed": managed,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "last_backup": backup or record.get("last_backup", ""),
            }
        )
        connectors[connector_id] = record
        state["schema_version"] = 1
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_text_atomic(self.state_path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")

    @staticmethod
    def _connector_id(value: str) -> str:
        connector_id = str(value or "").strip().lower()
        if connector_id not in _CONNECTOR_IDS:
            raise ConnectorError("UNSUPPORTED_CONNECTOR", "不支持的 AI 连接器", status_code=404)
        return connector_id
