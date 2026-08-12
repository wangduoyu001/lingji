from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from src.health import StartupHealthChecker


class AutopilotEngine:
    """Bounded coordinator for diagnosis, safe repair, verification and escalation."""

    _OWNER_CHECKS = {"data_root_policy", "state_db", "memory_db"}

    def __init__(
        self,
        settings: Any,
        *,
        state_db: Any,
        queue: Any,
        memory_statistics: Any,
        auth_status_provider: Callable[[], Mapping[str, Any]] | None = None,
        health_factory: Callable[..., Any] = StartupHealthChecker,
        interval_seconds: float | None = None,
    ) -> None:
        self.settings = settings
        self.state_db = state_db
        self.queue = queue
        self.memory_statistics = memory_statistics
        self.auth_status_provider = auth_status_provider
        self.health_factory = health_factory
        configured_interval = (
            float(interval_seconds)
            if interval_seconds is not None
            else float(getattr(settings, "scheduler_poll_seconds", 60.0))
        )
        self.interval_seconds = max(
            configured_interval,
            0.05 if interval_seconds is not None else 5.0,
        )
        self.stale_after_seconds = max(
            int(getattr(settings, "extraction_stale_after_seconds", 1800)),
            60,
        )
        self.enabled = bool(getattr(settings, "watchdog_enabled", True))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()
        self._cycle_count = 0
        self._automatic_repair_count = 0
        self._last_cycle_at: str | None = None
        self._last_success_at: str | None = None
        self._last_error: str | None = None
        self._recent_actions: list[dict[str, Any]] = []
        self._background_issues: list[dict[str, Any]] = []
        self._owner_actions: list[dict[str, Any]] = []
        self._state = "disabled" if not self.enabled else "idle"
        self._summary = "自动维护已关闭" if not self.enabled else "自动维护等待首次巡检"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        if not self.enabled or self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="lingji-autopilot", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 3.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=max(float(timeout), 0.0))
        with self._lock:
            if self.enabled and self._state == "checking":
                self._state = "stopped"
                self._summary = "自动维护已停止"

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "enabled": self.enabled,
                "running": self.running,
                "state": self._state,
                "summary": self._summary,
                "cycle_count": self._cycle_count,
                "automatic_repair_count": self._automatic_repair_count,
                "last_cycle_at": self._last_cycle_at,
                "last_success_at": self._last_success_at,
                "recent_actions": [dict(item) for item in self._recent_actions],
                "background_issue_count": len(self._background_issues),
                "background_issues": [dict(item) for item in self._background_issues],
                "owner_action_count": len(self._owner_actions),
                "owner_actions": [dict(item) for item in self._owner_actions],
                "last_error": self._last_error,
            }

    def run_once(self) -> dict[str, Any]:
        if not self.enabled:
            return self.status()
        with self._lock:
            self._state = "checking"
            self._summary = "正在巡检并自动处理可安全修复的问题"
            self._last_cycle_at = self._now()
            self._last_error = None
        try:
            before = self.health_factory(self.settings, read_only=True).run()
            repairs = self._safe_repairs(before)
            after = self.health_factory(self.settings, read_only=True).run()
            memory = self._memory_snapshot()
            background, owner = self._classify(after, memory, self._queue_stats(), self._auth_status())
            if repairs:
                self._record_repairs(repairs, after)
            with self._lock:
                self._cycle_count += 1
                self._last_success_at = self._now()
                self._background_issues = background
                self._owner_actions = owner
                if owner:
                    self._state = "owner_attention"
                    self._summary = f"{len(owner)} 件事需要主人确认，其余维护继续后台进行"
                elif background:
                    self._state = "degraded"
                    self._summary = f"正在后台处理或降级 {len(background)} 类问题，无需主人操作"
                else:
                    self._state = "healthy"
                    self._summary = "系统正常，自动维护持续运行"
                return self.status()
        except Exception as exc:
            with self._lock:
                self._cycle_count += 1
                self._state = "degraded"
                self._summary = "自动巡检遇到异常，稍后会自行重试"
                self._last_error = f"{type(exc).__name__}: {exc}"[:500]
                self._background_issues = [{
                    "code": "autopilot_cycle_failed",
                    "title": "自动巡检暂时失败",
                    "summary": "灵机会在下一轮自动重试，当前不需要主人处理。",
                }]
            self._append_event(
                "autopilot_cycle_failed",
                {"code": "autopilot_cycle_failed", "error_type": type(exc).__name__},
            )
            return self.status()

    def _loop(self) -> None:
        self.run_once()
        while not self._stop.wait(self.interval_seconds):
            self.run_once()

    def _safe_repairs(self, report: Mapping[str, Any]) -> list[dict[str, Any]]:
        repairs: list[dict[str, Any]] = []
        checks = {
            str(item.get("name") or ""): item
            for item in report.get("checks", [])
            if isinstance(item, Mapping)
        }
        if any(
            str(checks.get(name, {}).get("status") or "") == "error"
            for name in self._OWNER_CHECKS
        ):
            return []

        directory_targets = [
            ("storage", Path(self.settings.storage_path), True),
            ("logs", Path(self.settings.log_path), True),
            ("backup", Path(self.settings.backup_path), True),
            ("vault", Path(self.settings.vault_path), bool(getattr(self.settings, "vault_auto_init", False))),
        ]
        for name, path, allowed in directory_targets:
            check = checks.get(name)
            if (
                not allowed
                or not check
                or str(check.get("status")) not in {"warning", "error"}
                or path.exists()
            ):
                continue
            path.mkdir(parents=True, exist_ok=True)
            repairs.append({
                "code": f"create_{name}_directory",
                "title": f"已自动准备{name}目录",
                "summary": "缺失的灵机运行目录已创建，并将在本轮重新验证。",
            })

        released = int(self.queue.release_stale(self.stale_after_seconds))
        if released > 0:
            repairs.append({
                "code": "release_stale_extraction_leases",
                "title": f"已恢复 {released} 个中断任务",
                "summary": "失去心跳的任务已安全回到自动重试队列。",
            })
        return repairs

    def _memory_snapshot(self) -> dict[str, Any]:
        try:
            snapshot = self.memory_statistics.snapshot()
            return dict(snapshot) if isinstance(snapshot, Mapping) else {}
        except Exception as exc:
            return {
                "state": "configuration_required",
                "warnings": [{
                    "code": "memory_statistics_unavailable",
                    "severity": "warning",
                    "message": f"{type(exc).__name__}: {exc}"[:300],
                }],
            }

    def _queue_stats(self) -> dict[str, int]:
        try:
            return {str(key): int(value) for key, value in self.queue.stats().items()}
        except Exception:
            return {}

    def _auth_status(self) -> dict[str, Any]:
        if self.auth_status_provider is None:
            return {"providers": []}
        try:
            payload = self.auth_status_provider()
            return dict(payload) if isinstance(payload, Mapping) else {"providers": []}
        except Exception:
            return {"providers": []}

    def _classify(
        self,
        health: Mapping[str, Any],
        memory: Mapping[str, Any],
        queue_stats: Mapping[str, int],
        auth_status: Mapping[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        background: list[dict[str, Any]] = []
        owner: list[dict[str, Any]] = []
        for raw in health.get("checks", []):
            if not isinstance(raw, Mapping):
                continue
            name = str(raw.get("name") or "")
            status = str(raw.get("status") or "")
            if status == "ok":
                continue
            issue = {
                "code": f"health_{name or 'unknown'}",
                "title": self._health_title(name),
                "summary": self._health_summary(name, status),
            }
            (owner if name in self._OWNER_CHECKS else background).append(issue)

        vector = memory.get("vector") if isinstance(memory.get("vector"), Mapping) else {}
        if bool(vector.get("rebuild_required")):
            owner.append({
                "code": "vector_rebuild_required",
                "title": "向量索引需要重建确认",
                "summary": "重建可能替换派生索引，灵机不会自动执行不可逆操作。",
            })
        elif str(vector.get("state") or "healthy") not in {"healthy", "ready", "available"}:
            background.append({
                "code": "vector_degraded",
                "title": "语义检索正在降级",
                "summary": "全文检索仍可继续；灵机会保持状态监控，不会擅自重建向量索引。",
            })

        embedding = memory.get("embedding") if isinstance(memory.get("embedding"), Mapping) else {}
        if str(embedding.get("state") or "healthy") not in {"healthy", "ready", "available"}:
            background.append({
                "code": "embedding_degraded",
                "title": "Embedding 能力暂时降级",
                "summary": "灵机会继续使用可用检索能力，并等待模型恢复。",
            })

        failed = int(queue_stats.get("failed", 0))
        if failed:
            background.append({
                "code": "extraction_jobs_exhausted",
                "title": f"{failed} 个任务已停止自动重试",
                "summary": "任务已达到自动重试上限并保留失败原因，不会无限循环。",
            })
        for provider in (auth_status or {}).get("providers", []):
            if not isinstance(provider, Mapping):
                continue
            state = str(provider.get("state") or "not_configured")
            if state == "permission_insufficient":
                background.append({"code": "auth_permission_insufficient", "title": "连接权限不足", "summary": "灵机会保持当前安全边界，等待权限恢复。"})
            elif state in {"expired", "invalid"}:
                background.append({"code": "auth_reauthentication_required", "title": "连接需要重新认证", "summary": "灵机会继续处理不依赖该连接的工作。"})
        return self._dedupe(background), self._dedupe(owner)

    @staticmethod
    def _health_title(name: str) -> str:
        return {
            "data_root_policy": "数据根策略需要确认",
            "state_db": "运行状态数据库需要检查",
            "memory_db": "记忆数据库需要检查",
            "vault": "知识库目录暂不可用",
            "storage": "运行存储暂不可用",
            "logs": "日志目录暂不可用",
            "backup": "备份能力正在准备",
            "disk": "可用磁盘空间偏低",
            "ffmpeg": "媒体处理组件未就绪",
            "ffprobe": "媒体探测组件未就绪",
            "ollama": "本地模型服务暂不可用",
        }.get(name, "系统能力正在降级处理")

    @staticmethod
    def _health_summary(name: str, status: str) -> str:
        if name in {"data_root_policy", "state_db", "memory_db"}:
            return "涉及数据安全或完整性，灵机只诊断和保留证据，不会自行改写。"
        if name in {"ffmpeg", "ffprobe", "ollama"}:
            return "这是可选能力，核心功能继续运行；灵机会持续复查。"
        if name == "disk":
            return "当前先保持运行并持续观察，不会自动删除主人数据。"
        if name in {"storage", "logs", "backup", "vault"}:
            return "已尝试安全准备目录；如果仍不可用会继续保留为后台异常。"
        return f"检测到 {status} 状态，灵机会继续自动复查。"

    @staticmethod
    def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in items:
            code = str(item.get("code") or "")
            if code and code not in seen:
                seen.add(code)
                output.append(item)
        return output

    def _record_repairs(self, repairs: list[dict[str, Any]], verification: Mapping[str, Any]) -> None:
        status_by_name = {
            str(item.get("name") or ""): str(item.get("status") or "")
            for item in verification.get("checks", [])
            if isinstance(item, Mapping)
        }
        now = self._now()
        recorded: list[dict[str, Any]] = []
        for repair in repairs:
            code = str(repair["code"])
            verified = True
            if code.startswith("create_") and code.endswith("_directory"):
                check_name = code.removeprefix("create_").removesuffix("_directory")
                verified = status_by_name.get(check_name) == "ok"
            item = {**repair, "completed_at": now, "verified": verified}
            recorded.append(item)
            self._append_event("autopilot_repair", {"code": code, "verified": verified})
        with self._lock:
            self._automatic_repair_count += sum(1 for item in recorded if item["verified"])
            self._recent_actions = (recorded + self._recent_actions)[:8]

    def _append_event(self, event_type: str, payload: Mapping[str, Any]) -> None:
        try:
            self.state_db.append_event(
                event_type,
                "autopilot",
                str(payload.get("code") or event_type),
                dict(payload),
            )
        except Exception:
            pass
