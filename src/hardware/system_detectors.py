from __future__ import annotations

import csv
import os
import platform
import shutil
from pathlib import Path
from typing import Any

from .runner import SafeRunner


def _windows_cpu_model() -> str:
    """Read the Windows CPU display name without spawning a shell or WMI process."""

    if platform.system().lower() != "windows":
        return ""
    try:
        import winreg  # type: ignore[attr-defined]

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        ) as key:
            value, _value_type = winreg.QueryValueEx(key, "ProcessorNameString")
    except (ImportError, OSError, TypeError, ValueError):
        return ""
    return " ".join(str(value or "").split())


def cpu_snapshot(psutil_module: Any | None, runner: Any | None = None) -> dict[str, Any]:
    del runner  # CPU detection must remain process-free in the installed runtime.
    logical = os.cpu_count()
    physical = None
    source = "stdlib"
    if psutil_module is not None:
        try:
            logical = psutil_module.cpu_count(logical=True) or logical
            physical = psutil_module.cpu_count(logical=False)
            source = "psutil"
        except Exception:
            pass

    registry_model = _windows_cpu_model()
    platform_model = platform.processor().strip()
    environment_model = os.environ.get("PROCESSOR_IDENTIFIER", "").strip()
    model = registry_model or platform_model or environment_model or "unknown"
    if registry_model:
        model_source = "windows_registry"
    elif platform_model:
        model_source = "platform.processor"
    elif environment_model:
        model_source = "environment"
    else:
        model_source = "unknown"
    return {
        "model": model,
        "model_source": model_source,
        "physical_cores": int(physical) if physical is not None else None,
        "logical_threads": int(logical) if logical is not None else None,
        "source": source,
    }


def memory_snapshot(psutil_module: Any | None) -> dict[str, Any]:
    if psutil_module is None:
        return {
            "total_bytes": None,
            "available_bytes": None,
            "used_percent": None,
            "status": "unavailable",
            "source": "psutil_not_installed",
        }
    try:
        memory = psutil_module.virtual_memory()
        return {
            "total_bytes": int(memory.total),
            "available_bytes": int(memory.available),
            "used_percent": float(memory.percent),
            "status": "available",
            "source": "psutil",
        }
    except Exception as exc:
        return {
            "total_bytes": None,
            "available_bytes": None,
            "used_percent": None,
            "status": "unavailable",
            "source": "psutil_error",
            "error": SafeRunner.safe_error(exc),
        }


def disk_snapshot(settings: Any, psutil_module: Any | None) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    if psutil_module is not None:
        try:
            for partition in psutil_module.disk_partitions(all=False):
                mount = str(partition.mountpoint)
                if mount in seen:
                    continue
                try:
                    usage = psutil_module.disk_usage(mount)
                except Exception:
                    continue
                seen.add(mount)
                options = {item.strip().lower() for item in str(getattr(partition, "opts", "")).split(",")}
                output.append(
                    {
                        "mount": mount,
                        "device": str(getattr(partition, "device", "")),
                        "filesystem": str(getattr(partition, "fstype", "")) or "unknown",
                        "media_type": "unknown",
                        "total_bytes": int(usage.total),
                        "free_bytes": int(usage.free),
                        "used_percent": float(usage.percent),
                        "read_only": "ro" in options,
                        "source": "psutil",
                    }
                )
        except Exception:
            output = []

    if output:
        return output

    candidates = [settings.storage_path, settings.vault_path, settings.backup_path, settings.log_path]
    for path in candidates:
        target = Path(path)
        try:
            target = target if target.exists() else target.parent
            usage = shutil.disk_usage(target)
        except (FileNotFoundError, OSError):
            continue
        mount = str(target.anchor or target)
        if mount in seen:
            continue
        seen.add(mount)
        output.append(
            {
                "mount": mount,
                "device": "unknown",
                "filesystem": "unknown",
                "media_type": "unknown",
                "total_bytes": int(usage.total),
                "free_bytes": int(usage.free),
                "used_percent": round((usage.used / usage.total * 100.0) if usage.total else 0.0, 2),
                "read_only": False,
                "source": "shutil.disk_usage",
            }
        )
    return output


def gpu_snapshot(runner: SafeRunner) -> list[dict[str, Any]]:
    result = runner.command(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.free,utilization.gpu,temperature.gpu,driver_version",
            "--format=csv,noheader,nounits",
        ]
    )
    if result["returncode"] != 0:
        return []

    output: list[dict[str, Any]] = []
    rows = csv.reader(line for line in result["stdout"].splitlines() if line.strip())
    for index, row in enumerate(rows):
        if len(row) < 6:
            continue
        try:
            total_mib = float(row[1].strip())
            free_mib = float(row[2].strip())
            utilization = float(row[3].strip())
            temperature = float(row[4].strip())
        except ValueError:
            continue
        output.append(
            {
                "gpu_id": str(index),
                "vendor": "nvidia",
                "name": row[0].strip(),
                "total_vram_bytes": int(total_mib * 1024**2),
                "free_vram_bytes": int(free_mib * 1024**2),
                "used_vram_bytes": int((total_mib - free_mib) * 1024**2),
                "utilization_percent": utilization,
                "temperature_c": temperature,
                "driver_version": row[5].strip(),
                "source": "nvidia-smi",
            }
        )
    return output


def physical_disks(_runner: SafeRunner) -> list[dict[str, Any]]:
    """Return no physical-disk guess rather than launching PowerShell/WMI.

    Logical disk capacity remains available through ``disk_snapshot``. A future
    native Windows implementation may restore media type and health without
    weakening the installed runtime's zero-Shell contract.
    """

    return []
