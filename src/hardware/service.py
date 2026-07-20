from __future__ import annotations

import platform
import time
from datetime import datetime, timezone
from typing import Any, Callable

from .detectors import HardwareDetectors


_AUTO = object()
_MODES = {"auto", "gpu_preferred", "cpu_only"}


class HardwareCapabilityService:
    """Read-only hardware snapshot, telemetry and candidate compute policy."""

    def __init__(
        self,
        settings: Any,
        *,
        command_runner: Callable[..., Any] | None = None,
        url_reader: Callable[..., Any] | None = None,
        psutil_module: Any = _AUTO,
        cache_seconds: float = 30.0,
        telemetry_cache_seconds: float = 1.0,
        gpu_cache_seconds: float = 10.0,
    ):
        self.settings = settings
        self.psutil = self._load_psutil() if psutil_module is _AUTO else psutil_module
        self.detectors = HardwareDetectors(
            settings,
            command_runner=command_runner,
            url_reader=url_reader,
            psutil_module=self.psutil,
        )
        self.cache_seconds = max(float(cache_seconds), 0.0)
        self.telemetry_cache_seconds = max(float(telemetry_cache_seconds), 0.0)
        self.gpu_cache_seconds = max(float(gpu_cache_seconds), 0.0)
        self._capabilities: dict[str, Any] | None = None
        self._capabilities_at = 0.0
        self._telemetry: dict[str, Any] | None = None
        self._telemetry_at = 0.0
        self._gpus: list[dict[str, Any]] | None = None
        self._gpus_at = 0.0

    def configure(
        self,
        *,
        cache_seconds: float | None = None,
        telemetry_cache_seconds: float | None = None,
        gpu_cache_seconds: float | None = None,
    ) -> None:
        """Apply owner settings without recreating the service."""

        if cache_seconds is not None:
            self.cache_seconds = max(float(cache_seconds), 0.0)
        if telemetry_cache_seconds is not None:
            self.telemetry_cache_seconds = max(float(telemetry_cache_seconds), 0.0)
        if gpu_cache_seconds is not None:
            self.gpu_cache_seconds = max(float(gpu_cache_seconds), 0.0)
        self._capabilities = None
        self._telemetry = None

    def cache_policy(self) -> dict[str, float]:
        return {
            "static_seconds": self.cache_seconds,
            "telemetry_seconds": self.telemetry_cache_seconds,
            "gpu_probe_seconds": self.gpu_cache_seconds,
        }

    def capabilities(self, *, force: bool = False) -> dict[str, Any]:
        now = time.monotonic()
        if not force and self._capabilities and now - self._capabilities_at < self.cache_seconds:
            return self._capabilities

        memory = self.detectors.memory()
        snapshot = {
            "collected_at": self._timestamp(),
            "system": {
                "os_name": platform.system() or "unknown",
                "os_version": platform.version() or "unknown",
                "os_release": platform.release() or "unknown",
                "architecture": platform.machine() or "unknown",
                "python_version": platform.python_version(),
                "hostname": platform.node() or "unknown",
            },
            "cpu": self.detectors.cpu(),
            "memory": memory,
            "gpus": self._gpu_snapshot(force=force),
            "disks": self.detectors.disks(),
            "physical_disks": self.detectors.physical_disks(),
            "toolchains": self.detectors.toolchains(),
            "cache_policy": self.cache_policy(),
            "warnings": [] if memory["status"] == "available" else ["memory_telemetry_unavailable"],
            "compatibility_requires_load_test": True,
            "compatibility_process": [
                "static_specification",
                "dependency_check",
                "small_load_test",
                "short_benchmark",
                "measured_conclusion",
            ],
        }
        snapshot["cuda"] = self.detectors.cuda(bool(snapshot["gpus"]))
        self._capabilities = snapshot
        self._capabilities_at = now
        return snapshot

    def telemetry(self, *, force: bool = False) -> dict[str, Any]:
        now = time.monotonic()
        if not force and self._telemetry and now - self._telemetry_at < self.telemetry_cache_seconds:
            return self._telemetry

        cpu_percent = None
        memory_percent = None
        available_bytes = None
        source = "unavailable"
        errors: list[str] = []
        if self.psutil is not None:
            try:
                memory = self.psutil.virtual_memory()
                cpu_percent = float(self.psutil.cpu_percent(interval=None))
                memory_percent = float(memory.percent)
                available_bytes = int(memory.available)
                source = "psutil"
            except Exception as exc:
                errors.append(f"{exc.__class__.__name__}: {exc}"[:500])

        self._telemetry = {
            "collected_at": self._timestamp(),
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "memory_available_bytes": available_bytes,
            "gpus": self._gpu_snapshot(force=force),
            "cache_policy": self.cache_policy(),
            "source": source,
            "errors": errors,
            "stale": False,
        }
        self._telemetry_at = now
        return self._telemetry

    def refresh(self) -> dict[str, Any]:
        self._capabilities = None
        self._telemetry = None
        self._gpus = None
        return self.capabilities(force=True)

    def resolve_compute_policy(self, requested_mode: str, *, gpu_id: str | None = None) -> dict[str, Any]:
        mode = str(requested_mode or "auto").strip().lower()
        if mode not in _MODES:
            raise ValueError(f"Unknown compute mode: {requested_mode}")
        gpus = self.capabilities()["gpus"]
        selected = next((gpu for gpu in gpus if str(gpu["gpu_id"]) == str(gpu_id)), None) if gpu_id else None
        if selected is None and gpus:
            selected = max(gpus, key=lambda item: int(item.get("free_vram_bytes") or 0))

        if mode == "cpu_only":
            candidate, reason = "cpu", "owner_selected_cpu_only"
        elif selected:
            candidate, reason = "gpu", None
        else:
            candidate, reason = "cpu", "gpu_unavailable"

        return {
            "requested_mode": mode,
            "candidate_device": candidate,
            "gpu_id": selected["gpu_id"] if selected else None,
            "gpu_name": selected["name"] if selected else None,
            "fallback_allowed": mode != "cpu_only",
            "fallback_reason": reason,
            "basic_retrieval_available": True,
            "final_device_requires_model_probe": candidate == "gpu",
            "explanation": (
                "这是候选设备，不代表具体模型一定能运行；模型仍需加载测试和短基准。"
                if candidate == "gpu"
                else "基础检索、Memory Gateway 和 MCP 继续使用 CPU。"
            ),
        }

    def close(self) -> None:
        self._capabilities = None
        self._telemetry = None
        self._gpus = None

    def _gpu_snapshot(self, *, force: bool = False) -> list[dict[str, Any]]:
        now = time.monotonic()
        if not force and self._gpus is not None and now - self._gpus_at < self.gpu_cache_seconds:
            return self._gpus
        self._gpus = self.detectors.gpus()
        self._gpus_at = now
        return self._gpus

    @staticmethod
    def _load_psutil() -> Any | None:
        try:
            import psutil  # type: ignore
        except ImportError:
            return None
        return psutil

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()
