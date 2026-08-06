from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .connectors import AiMemoryConnectorService as ConnectorCore
from .connectors import ConnectorError, Runner
from .executable_resolution import (
    ExecutableResolution,
    executable_invocation,
    resolve_launchable_executable,
)


class _ExplicitEnvironment(dict[str, str]):
    """Keep an explicitly supplied empty environment distinct from ``None``."""

    def __bool__(self) -> bool:
        return True


class AiMemoryConnectorService(ConnectorCore):
    """Owner-governed connector service with one derived readiness contract.

    Configuration presence, executable discovery, command execution and live MCP
    verification are separate facts. ``status_state`` is derived from those facts
    and never upgrades a connector merely because a config file or executable path
    exists. On Windows every deterministic Codex PATH/npm candidate is probed, so
    a blocked WindowsApps alias cannot hide a launchable ``codex.cmd`` later in PATH.
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
        isolated_env = None if env is None else _ExplicitEnvironment(env)
        super().__init__(
            storage_path=storage_path,
            home=home,
            env=isolated_env,
            runner=runner,
            timeout_seconds=timeout_seconds,
        )
        self._codex_resolution: ExecutableResolution | None = None

    def preview(self, connector_id: str) -> dict[str, Any]:
        payload = super().preview(connector_id)
        payload.pop("copy_payload", None)
        return payload

    def test(self, connector_id: str) -> dict[str, Any]:
        connector_id = self._connector_id(connector_id)
        if connector_id == "codex":
            payload = self._test_codex()
        else:
            try:
                payload = super().test(connector_id)
            except ConnectorError as exc:
                payload = self._blocked_test_payload(
                    connector_id,
                    code=exc.code,
                    detail=exc.message,
                )
        self._record_test_result(connector_id, payload)
        return payload

    def _resolve_codex(self, *, refresh: bool = False) -> ExecutableResolution:
        if self._codex_resolution is not None and not refresh:
            return self._codex_resolution
        preferred = shutil.which("codex", path=self.env.get("PATH"))
        self._codex_resolution = resolve_launchable_executable(
            "codex",
            env=self.env,
            runner=self.runner,
            timeout_seconds=self.timeout_seconds,
            preferred_candidates=[preferred] if preferred else [],
        )
        return self._codex_resolution

    @staticmethod
    def _resolution_detail(resolution: ExecutableResolution) -> str:
        if not resolution.attempts:
            return ""
        last = resolution.attempts[-1]
        return f"{last.path}: {last.detail}"

    def _test_codex(self) -> dict[str, Any]:
        runtime_ready = self._runtime_ready()
        config_present = self._managed_block(self._read_text(self._codex_config_path())) is not None
        resolution = self._resolve_codex(refresh=True)
        executable = resolution.selected
        if not resolution.launchable:
            all_denied = bool(resolution.attempts) and all(
                attempt.state == "access_denied" for attempt in resolution.attempts
            )
            if resolution.state == "not_found":
                code = "CLIENT_NOT_FOUND"
                detail = (
                    "Codex 配置目录已检查，但系统找不到 codex 命令。"
                    "配置存在不等于连接可用。"
                )
            else:
                code = "CLIENT_ACCESS_DENIED" if all_denied else "CLIENT_LAUNCH_BLOCKED"
                attempt_detail = self._resolution_detail(resolution)
                detail = (
                    f"发现 {len(resolution.candidates)} 个 Codex 命令候选，但都无法启动。"
                    + (f" 最后一次：{attempt_detail}" if attempt_detail else "")
                )
            return self._blocked_test_payload(
                "codex",
                code=code,
                detail=detail,
                runtime_ready=runtime_ready,
                config_present=config_present,
                executable=resolution.candidates[0] if resolution.candidates else "",
                resolution=resolution,
            )

        command = executable_invocation(
            executable,
            ["mcp", "list"],
            env=self.env,
        )
        try:
            completed = self.runner(command, self.timeout_seconds)
        except subprocess.TimeoutExpired:
            return self._blocked_test_payload(
                "codex",
                code="CLIENT_COMMAND_TIMEOUT",
                detail="codex 命令启动成功，但 MCP 列表验证超时。",
                runtime_ready=runtime_ready,
                config_present=config_present,
                executable=executable,
                resolution=resolution,
            )
        except OSError as exc:
            detail = str(exc).strip() or type(exc).__name__
            code = "CLIENT_ACCESS_DENIED" if isinstance(exc, PermissionError) or "denied" in detail.lower() else "CLIENT_COMMAND_FAILED"
            return self._blocked_test_payload(
                "codex",
                code=code,
                detail=f"已验证的 codex 命令在 MCP 检查时无法启动：{detail}",
                runtime_ready=runtime_ready,
                config_present=config_present,
                executable=executable,
                resolution=resolution,
            )

        output = f"{completed.stdout or ''}\n{completed.stderr or ''}"
        registration_visible = completed.returncode == 0 and "lingji-memory" in output
        ok = bool(runtime_ready and config_present and registration_visible)
        if completed.returncode != 0:
            detail = self._command_detail(completed)
            code = "CLIENT_COMMAND_REJECTED"
        elif not registration_visible:
            detail = "Codex 命令可运行，但未列出 lingji-memory MCP。"
            code = "MCP_REGISTRATION_NOT_VISIBLE"
        elif not runtime_ready:
            detail = "Codex 已列出 lingji-memory，但 LingJi MCP Runtime 当前不可用。"
            code = "MCP_RUNTIME_UNAVAILABLE"
        elif not config_present:
            detail = "Codex 命令可运行，但未发现 LingJi 管理的配置区块。"
            code = "CONFIGURATION_MISSING"
        else:
            detail = "Codex 命令已运行并列出 lingji-memory；客户端注册验证通过。"
            code = "VERIFIED"
        return {
            "connector_id": "codex",
            "state": "connected" if ok else "failed",
            "ok": ok,
            "code": code,
            "mcp_runtime_ready": runtime_ready,
            "config_present": config_present,
            "client_available": True,
            "client_launchable": True,
            "client_verified": registration_visible,
            "client_command": executable,
            "client_resolution": resolution.as_dict(),
            "message": detail,
        }

    def _blocked_test_payload(
        self,
        connector_id: str,
        *,
        code: str,
        detail: str,
        runtime_ready: bool | None = None,
        config_present: bool | None = None,
        executable: str = "",
        resolution: ExecutableResolution | None = None,
    ) -> dict[str, Any]:
        return {
            "connector_id": connector_id,
            "state": "blocked",
            "ok": False,
            "code": code,
            "mcp_runtime_ready": self._runtime_ready() if runtime_ready is None else runtime_ready,
            "config_present": bool(config_present),
            "client_available": bool(executable),
            "client_launchable": False,
            "client_verified": False,
            "client_command": executable,
            "client_resolution": resolution.as_dict() if resolution is not None else {},
            "message": detail,
        }

    def _codex_status(self, state: Mapping[str, Any], *, live: bool) -> dict[str, Any]:
        payload = super()._codex_status(state, live=False)
        path = self._codex_config_path()
        resolution = self._resolve_codex(refresh=live)
        executable = resolution.selected or (resolution.candidates[0] if resolution.candidates else "")
        managed = bool(payload.get("managed_by_lingji"))
        conflict = payload.get("configuration_state") == "conflict"
        record = self._state_connector(self._read_state(), "codex")

        if live and managed and resolution.launchable and not conflict:
            self.test("codex")
            resolution = self._resolve_codex(refresh=False)
            executable = resolution.selected or (resolution.candidates[0] if resolution.candidates else "")
            record = self._state_connector(self._read_state(), "codex")

        last_ok = record.get("last_test_ok") is True
        last_code = str(record.get("last_test_code") or "")
        last_detail = str(record.get("last_test_detail") or "")
        last_at = record.get("last_test_at")

        configuration_state = (
            "conflict" if conflict else "configured" if managed else "not_configured"
        )
        client_state = (
            "available"
            if resolution.launchable
            else "not_found"
            if resolution.state == "not_found"
            else "launch_blocked"
        )
        connection_state = (
            "verified"
            if last_ok
            else "blocked"
            if conflict or client_state in {"not_found", "launch_blocked"}
            else "failed"
            if last_at
            else "not_verified"
        )

        if conflict:
            status_state = "conflict"
            blocking_reason = "存在非灵机管理的同名 lingji-memory 配置，灵机不会覆盖。"
            next_action = "先处理配置冲突"
        elif client_state == "not_found":
            status_state = "client_not_found"
            blocking_reason = "检测到 Codex 数据目录不等于找到 codex 命令。"
            next_action = "修复 Codex 安装或 PATH"
        elif client_state == "launch_blocked":
            status_state = "client_launch_blocked"
            blocking_reason = self._resolution_detail(resolution) or last_detail or "发现 Codex 命令路径，但所有候选均无法启动。"
            next_action = "修复命令权限后重新验证"
        elif not managed:
            status_state = "configuration_required"
            blocking_reason = "已找到可启动的 Codex 命令，但尚未写入 LingJi MCP 配置。"
            next_action = "预览并连接"
        elif connection_state == "verified":
            status_state = "ready"
            blocking_reason = ""
            next_action = "连接已验证"
        elif connection_state == "failed":
            status_state = "verification_failed"
            blocking_reason = last_detail or "真实 Codex 客户端验证失败。"
            next_action = "查看原因并重新验证"
        else:
            status_state = "verification_required"
            blocking_reason = "配置已写入，但尚未通过真实 codex 命令验证。"
            next_action = "验证 Codex 连接"

        payload.update(
            {
                "configuration_state": configuration_state,
                "client_available": bool(resolution.candidates),
                "client_launchable": resolution.launchable,
                "client_command": executable,
                "client_resolution": resolution.as_dict(),
                "live_test": last_ok,
                "status_state": status_state,
                "blocking_reason": blocking_reason,
                "last_test_code": last_code,
                "last_test_detail": last_detail,
                "last_test_at": last_at,
                "next_action": next_action,
                "readiness": {
                    "configuration": {
                        "state": configuration_state,
                        "managed": managed,
                        "target": self._display_path(path),
                    },
                    "client": {
                        "state": client_state,
                        "command": executable,
                        "launchable": resolution.launchable,
                        "candidate_count": len(resolution.candidates),
                        "attempts": [
                            {
                                "state": attempt.state,
                                "detail": attempt.detail,
                            }
                            for attempt in resolution.attempts
                        ],
                        "last_error_code": last_code if client_state == "launch_blocked" else "",
                        "detail": blocking_reason if client_state == "launch_blocked" else "",
                    },
                    "real_connection": {
                        "state": connection_state,
                        "method": "codex mcp list",
                        "verified": last_ok,
                        "last_checked_at": last_at,
                        "detail": last_detail,
                    },
                },
            }
        )
        return payload

    def _claude_status(self, state: Mapping[str, Any], *, live: bool) -> dict[str, Any]:
        payload = super()._claude_status(state, live=live)
        executable = shutil.which("claude", path=self.env.get("PATH"))
        managed = bool(payload.get("managed_by_lingji"))
        verified = payload.get("live_test") is True
        record = self._state_connector(self._read_state(), "claude_code")

        if managed and not executable:
            status_state = "blocked"
            blocking_reason = "连接记录存在，但系统找不到 claude 命令，无法验证或安全回滚。"
            next_action = "恢复 Claude Code 命令后重新检测"
            verified = False
        elif managed and verified:
            status_state = "ready"
            blocking_reason = ""
            next_action = "连接已验证"
        elif managed:
            status_state = "verification_required"
            blocking_reason = "配置已写入，但尚未通过真实 Claude Code 客户端测试。"
            next_action = "测试连接"
        elif executable:
            status_state = "configuration_required"
            blocking_reason = "已找到 Claude Code 命令，但尚未添加 LingJi MCP。"
            next_action = "预览并连接"
        else:
            status_state = "client_not_found"
            blocking_reason = "发现历史目录不等于客户端命令可用。"
            next_action = "先安装或修复 Claude Code 命令"

        payload.update(
            {
                "client_available": bool(executable),
                "client_command": executable or "",
                "live_test": verified,
                "status_state": status_state,
                "blocking_reason": blocking_reason,
                "last_test_code": str(record.get("last_test_code") or ""),
                "last_test_detail": str(record.get("last_test_detail") or ""),
                "last_test_at": record.get("last_test_at"),
                "next_action": next_action,
            }
        )
        return payload

    def _workbuddy_status(self, state: Mapping[str, Any]) -> dict[str, Any]:
        payload = super()._workbuddy_status(state)
        payload.update(
            {
                "client_available": None,
                "client_command": "",
                "status_state": "manual_action_required",
                "blocking_reason": "WorkBuddy 未公开稳定的本地配置接口，需要在官方页面手动粘贴并测试。",
                "last_test_code": "",
                "last_test_detail": "",
                "last_test_at": None,
                "next_action": "复制配置并在 WorkBuddy 内测试",
            }
        )
        return payload

    def _record_test_result(self, connector_id: str, payload: Mapping[str, Any]) -> None:
        state = self._read_state()
        connectors = state.setdefault("connectors", {})
        existing = connectors.get(connector_id) if isinstance(connectors, dict) else None
        record = dict(existing) if isinstance(existing, Mapping) else {}
        record.update(
            {
                "last_test_ok": bool(payload.get("ok")),
                "last_test_state": str(payload.get("state") or "unknown"),
                "last_test_code": str(payload.get("code") or ""),
                "last_test_detail": str(payload.get("message") or "")[:500],
                "last_test_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        resolution = payload.get("client_resolution")
        if isinstance(resolution, Mapping):
            record["last_client_resolution"] = dict(resolution)
        connectors[connector_id] = record
        state["schema_version"] = 2
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_text_atomic(
            self.state_path,
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        )
