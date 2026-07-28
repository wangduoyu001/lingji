from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from src.hardware.runner import SafeRunner
from src.hardware.system_detectors import cpu_snapshot, physical_disks


class _FakePsutil:
    @staticmethod
    def cpu_count(logical: bool = True):
        return 12 if logical else 6


class _RejectingRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def command(self, args: list[str], *, timeout: float = 3.0):
        self.calls.append(tuple(args))
        raise AssertionError(f"process launch is forbidden for static hardware detection: {args}")


def test_static_windows_hardware_detection_does_not_launch_shells() -> None:
    runner = _RejectingRunner()
    with mock.patch(
        "src.hardware.system_detectors._windows_cpu_model",
        return_value="Test CPU",
    ):
        cpu = cpu_snapshot(_FakePsutil, runner=runner)

    assert cpu["model"] == "Test CPU"
    assert cpu["model_source"] == "windows_registry"
    assert cpu["physical_cores"] == 6
    assert cpu["logical_threads"] == 12
    assert physical_disks(runner) == []
    assert runner.calls == []


def test_hardware_detector_source_contains_no_shell_probe() -> None:
    source = Path("src/hardware/system_detectors.py").read_text(encoding="utf-8").lower()
    for forbidden in (
        "get-ciminstance",
        "get-physicaldisk",
        'runner.command(["powershell"',
        'runner.command(["pwsh"',
        'runner.command(["cmd"',
    ):
        assert forbidden not in source


def test_safe_runner_hides_console_windows_on_windows() -> None:
    startup_info = SimpleNamespace(dwFlags=0, wShowWindow=None)
    completed = subprocess.CompletedProcess(["nvidia-smi"], 0, stdout="ok", stderr="")

    with (
        mock.patch("src.hardware.runner.os.name", "nt"),
        mock.patch.object(subprocess, "STARTUPINFO", return_value=startup_info, create=True),
        mock.patch.object(subprocess, "STARTF_USESHOWWINDOW", 1, create=True),
        mock.patch.object(subprocess, "SW_HIDE", 0, create=True),
        mock.patch.object(subprocess, "CREATE_NO_WINDOW", 0x08000000, create=True),
        mock.patch("src.hardware.runner.subprocess.run", return_value=completed) as run,
    ):
        result = SafeRunner._run_command(["nvidia-smi"], timeout=1.0)

    assert result.returncode == 0
    kwargs = run.call_args.kwargs
    assert kwargs["creationflags"] == 0x08000000
    assert kwargs["startupinfo"] is startup_info
    assert startup_info.dwFlags & 1
    assert startup_info.wShowWindow == 0
