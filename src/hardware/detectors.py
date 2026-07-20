from __future__ import annotations

from typing import Any, Callable

from .runner import SafeRunner
from .system_detectors import cpu_snapshot, disk_snapshot, gpu_snapshot, memory_snapshot, physical_disks
from .tool_detectors import cuda_snapshot, ollama_status, qdrant_status, version_command


class HardwareDetectors:
    def __init__(
        self,
        settings: Any,
        *,
        command_runner: Callable[..., Any] | None = None,
        url_reader: Callable[..., Any] | None = None,
        psutil_module: Any | None = None,
    ):
        self.settings = settings
        self.psutil = psutil_module
        self.runner = SafeRunner(command_runner=command_runner, url_reader=url_reader)

    def cpu(self) -> dict[str, Any]:
        return cpu_snapshot(self.psutil, runner=self.runner)

    def memory(self) -> dict[str, Any]:
        return memory_snapshot(self.psutil)

    def disks(self) -> list[dict[str, Any]]:
        return disk_snapshot(self.settings, self.psutil)

    def physical_disks(self) -> list[dict[str, Any]]:
        return physical_disks(self.runner)

    def gpus(self) -> list[dict[str, Any]]:
        return gpu_snapshot(self.runner)

    def cuda(self, driver_available: bool) -> dict[str, Any]:
        return cuda_snapshot(self.runner, driver_available)

    def toolchains(self) -> dict[str, Any]:
        return {
            "ollama": ollama_status(self.settings, self.runner),
            "ffmpeg": version_command("ffmpeg", self.runner),
            "ffprobe": version_command("ffprobe", self.runner),
            "qdrant": qdrant_status(self.settings),
        }
