from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import Any

from .runner import SafeRunner


def cuda_snapshot(runner: SafeRunner, driver_available: bool) -> dict[str, Any]:
    result = runner.command(["nvcc", "--version"])
    nvcc_match = re.search(r"release\s+([0-9.]+)", result["stdout"], flags=re.IGNORECASE)
    runtime_version = nvcc_match.group(1) if nvcc_match else None
    runtime_available = result["returncode"] == 0
    source = "nvcc" if result["returncode"] == 0 else "not_available"
    # Fallback: try nvidia-smi for driver-level CUDA version when nvcc is absent
    smi_cuda_version = None
    if not runtime_available and driver_available:
        try:
            smi_result = runner.command(["nvidia-smi"], timeout=3.0)
            smi_match = re.search(r"CUDA Version:\s+([0-9.]+)", smi_result["stdout"], flags=re.IGNORECASE)
            if smi_match:
                smi_cuda_version = smi_match.group(1)
        except Exception:
            pass
    return {
        "driver_available": driver_available,
        "runtime_available": runtime_available,
        "runtime_version": runtime_version,
        "source": source,
        "driver_cuda_version": smi_cuda_version,
    }


def ollama_status(settings: Any, runner: SafeRunner) -> dict[str, Any]:
    base_url = str(getattr(settings, "ollama_base_url", "http://127.0.0.1:11434")).rstrip("/")
    try:
        payload = runner.json_url(f"{base_url}/api/tags", timeout=3.0)
        models = payload.get("models", []) if isinstance(payload, dict) else []
        return {
            "available": True,
            "base_url": base_url,
            "model_count": len(models),
            "models": [
                {
                    "name": item.get("name") or item.get("model"),
                    "size_bytes": item.get("size"),
                    "parameter_size": (item.get("details") or {}).get("parameter_size"),
                    "quantization": (item.get("details") or {}).get("quantization_level"),
                }
                for item in models
            ],
            "source": "ollama_api_tags",
        }
    except Exception as exc:
        return {
            "available": False,
            "base_url": base_url,
            "model_count": 0,
            "models": [],
            "source": "ollama_api_tags",
            "error": runner.safe_error(exc),
        }


def version_command(command: str, runner: SafeRunner) -> dict[str, Any]:
    result = runner.command([command, "-version"])
    first_line = next((line.strip() for line in result["stdout"].splitlines() if line.strip()), "")
    return {
        "available": result["returncode"] == 0,
        "version": first_line or None,
        "source": "command",
        "error": result["stderr"][:300] if result["returncode"] != 0 else None,
    }


def qdrant_status(settings: Any) -> dict[str, Any]:
    storage_path = Path(settings.storage_path) / "qdrant"
    try:
        client_available = importlib.util.find_spec("qdrant_client") is not None
    except (ImportError, ValueError):
        client_available = False
    return {
        "available": client_available,
        "mode": "local",
        "storage_path": str(storage_path),
        "storage_exists": storage_path.exists(),
        "source": "python_import_and_path",
        "status": "ready" if client_available else "client_not_installed",
    }
