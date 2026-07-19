from __future__ import annotations

import csv
import json
import os
import platform
import shutil
from pathlib import Path
from typing import Any

from .runner import SafeRunner


def cpu_snapshot(psutil_module: Any | None) -> dict[str, Any]:
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
    model = platform.processor().strip() or os.environ.get("PROCESSOR_IDENTIFIER", "").strip() or "unknown"
    return {
        "model": model,
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


def physical_disks(runner: SafeRunner) -> list[dict[str, Any]]:
    if platform.system().lower() != "windows":
        return []
    script = (
        "Get-PhysicalDisk | Select-Object FriendlyName,MediaType,Size,HealthStatus "
        "| ConvertTo-Json -Compress"
    )
    result = runner.command(["powershell", "-NoProfile", "-Command", script], timeout=5.0)
    if result["returncode"] != 0 or not result["stdout"].strip():
        result = runner.command(["pwsh", "-NoProfile", "-Command", script], timeout=5.0)
    if result["returncode"] != 0 or not result["stdout"].strip():
        return []
    try:
        payload = json.loads(result["stdout"])
    except json.JSONDecodeError:
        return []
    rows = payload if isinstance(payload, list) else [payload]
    return [
        {
            "name": row.get("FriendlyName") or "unknown",
            "media_type": str(row.get("MediaType") or "unknown").lower(),
            "size_bytes": int(row.get("Size") or 0),
            "health_status": row.get("HealthStatus") or "unknown",
            "source": "powershell_get_physicaldisk",
        }
        for row in rows
        if isinstance(row, dict)
    ]
