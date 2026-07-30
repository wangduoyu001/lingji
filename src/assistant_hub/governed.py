from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .connectors import AiMemoryConnectorService as ConnectorCore
from .connectors import Runner


class _ExplicitEnvironment(dict[str, str]):
    """Keep an explicitly supplied empty environment distinct from ``None``.

    The connector core preserves legacy behaviour by inheriting ``os.environ``
    when no environment is supplied. A caller that deliberately passes an empty
    mapping must remain isolated from machine-level variables such as
    ``CODEX_HOME``. Making the temporary mapping truthy lets the core copy it
    without falling back to the process environment.
    """

    def __bool__(self) -> bool:
        return True


class AiMemoryConnectorService(ConnectorCore):
    """Public owner-governed connector service.

    This boundary removes secret-bearing preview fields, preserves explicit test
    isolation, and exposes one truthful connector state. A configuration file is
    not treated as a working client connection until the real client command can
    be found and the MCP entry can be verified.
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

    def preview(self, connector_id: str) -> dict[str, Any]:
        payload = super().preview(connector_id)
        payload.pop("copy_payload", None)
        return payload

    def test(self, connector_id: str) -> dict[str, Any]:
        connector_id = self._connector_id(connector_id)
        payload = super().test(connector_id)
        if connector_id == "codex" and payload.get("client_verified") is None:
            payload.update(
                {
                    "state": "blocked",
                    "ok": False,
                    "message": (
                        "Codex 配置文件已检查，但系统找不到 codex 命令。"
                        "配置存在不等于连接可用，请先恢复 Codex 可执行命令后重新测试。"
                    ),
                }
            )
        self._record_test_result(connector_id, payload)
        return payload

    def _codex_status(self, state: Mapping[str, Any], *, live: bool) -> dict[str, Any]:
        payload = super()._codex_status(state, live=live)
        executable = shutil.which("codex", path=self.env.get("PATH"))
        managed = bool(payload.get("managed_by_lingji"))
        conflict = payload.get("configuration_state") == "conflict"
        verified = payload.get("live_test") is True
        record = self._state_connector(self._read_state(), "codex")

        if conflict:
            status_state = "conflict"
            blocking_reason = "存在非灵机管理的同名 lingji-memory 配置，灵机不会覆盖。"
            next_action = "先处理配置冲突"
        elif managed and not executable:
            status_state = "blocked"
            blocking_reason = "配置文件已写入，但系统找不到 codex 命令，无法完成真实客户端验证。"
            next_action = "恢复 Codex 命令后重新测试"
            verified = False
        elif managed and verified:
            status_state = "ready"
            blocking_reason = ""
            next_action = "连接已验证"
        elif managed:
            status_state = "verification_required"
            blocking_reason = "配置已写入，但尚未通过真实 Codex 客户端测试。"
            next_action = "测试连接"
        elif executable:
            status_state = "configuration_required"
            blocking_reason = "已找到 Codex 命令，但尚未写入 LingJi MCP 配置。"
            next_action = "预览并连接"
        else:
            status_state = "client_not_found"
            blocking_reason = "检测到 Codex 数据目录不代表找到 Codex 可执行命令。"
            next_action = "先修复 Codex 安装或 PATH"

        payload.update(
            {
                "client_available": bool(executable),
                "client_command": "codex" if executable else "",
                "live_test": verified,
                "status_state": status_state,
                "blocking_reason": blocking_reason,
                "last_test_detail": str(record.get("last_test_detail") or ""),
                "next_action": next_action,
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
                "client_command": "claude" if executable else "",
                "live_test": verified,
                "status_state": status_state,
                "blocking_reason": blocking_reason,
                "last_test_detail": str(record.get("last_test_detail") or ""),
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
                "last_test_detail": "",
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
                "last_test_detail": str(payload.get("message") or "")[:500],
                "last_test_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        connectors[connector_id] = record
        state["schema_version"] = 1
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_text_atomic(self.state_path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")
