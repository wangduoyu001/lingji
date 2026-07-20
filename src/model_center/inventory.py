from __future__ import annotations

import importlib.util
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from .contracts import first_model_info, mapped_capabilities, model_name, unverified_compatibility
from .registry import registry_snapshot
from .transport import OllamaInventoryTransport


class LocalModelInventoryService:
    """Read installed and configured local model state without mutating providers."""

    def __init__(
        self,
        settings: Any,
        *,
        runtime_settings: Any | None = None,
        transport: Any | None = None,
        package_finder: Callable[[str], bool] | None = None,
        environment: Mapping[str, str] | None = None,
        cache_seconds: float = 60.0,
    ):
        self.settings = settings
        self.runtime_settings = runtime_settings
        self.transport = transport or OllamaInventoryTransport()
        self.package_finder = package_finder or self._package_available
        self.environment = dict(os.environ if environment is None else environment)
        self.cache_seconds = max(float(cache_seconds), 0.0)
        self._cache: dict[str, Any] | None = None
        self._cache_at = 0.0

    def registry(self) -> dict[str, Any]:
        return registry_snapshot()

    def inventory(self, *, force: bool = False) -> dict[str, Any]:
        now = time.monotonic()
        if not force and self._cache is not None and now - self._cache_at < self.cache_seconds:
            return self._cache

        ollama_models, ollama_status = self._ollama_models()
        installed_names: set[str] = set()
        for item in ollama_models:
            if item.get("installed"):
                name = item["name"]
                installed_names.add(name)
                if name.endswith(":latest"):
                    installed_names.add(name[: -len(":latest")])
        providers = [
            self._faster_whisper_provider(),
            self._paddleocr_provider(),
            {
                "provider_id": "not_configured_reranker",
                "label": "未配置 Reranker",
                "capabilities": ["reranker"],
                "package_available": False,
                "installation_status": "not_configured",
                "configured_model": None,
                "model_root": None,
                "last_error": None,
            },
        ]
        assignments = self._configured_assignments(installed_names)
        warnings = []
        if not ollama_status["available"]:
            warnings.append("ollama_unavailable")
        if any(not item["installed"] for item in assignments):
            warnings.append("configured_model_missing")

        self._cache = {
            "collected_at": self._timestamp(),
            "models": ollama_models,
            "providers": providers,
            "provider_status": {"ollama": ollama_status},
            "assignments": assignments,
            "summary": {
                "installed_models": len(ollama_models),
                "running_models": sum(1 for item in ollama_models if item["running"]),
                "unverified_models": len(ollama_models),
                "missing_assignments": sum(1 for item in assignments if not item["installed"]),
            },
            "warnings": sorted(set(warnings)),
            "mutating_operations_enabled": False,
            "compatibility_process": self.registry()["compatibility_process"],
        }
        self._cache_at = now
        return self._cache

    def refresh(self) -> dict[str, Any]:
        self._cache = None
        return self.inventory(force=True)

    def configure(self, *, cache_seconds: float | None = None) -> None:
        if cache_seconds is not None:
            self.cache_seconds = max(float(cache_seconds), 0.0)
        self._cache = None

    def close(self) -> None:
        self._cache = None
        close = getattr(self.transport, "close", None)
        if callable(close):
            close()

    def _ollama_models(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        base_url = str(getattr(self.settings, "ollama_base_url", "http://127.0.0.1:11434")).rstrip("/")
        try:
            tags_payload = self.transport.get_json(f"{base_url}/api/tags", timeout=3.0)
            tag_rows = tags_payload.get("models", []) if isinstance(tags_payload, dict) else []
        except Exception as exc:
            return [], {
                "available": False,
                "base_url": base_url,
                "source": "ollama_api",
                "last_error": self._safe_error(exc),
            }

        running_rows: list[dict[str, Any]] = []
        running_error = None
        try:
            running_payload = self.transport.get_json(f"{base_url}/api/ps", timeout=3.0)
            running_rows = running_payload.get("models", []) if isinstance(running_payload, dict) else []
        except Exception as exc:
            running_error = self._safe_error(exc)

        running_by_name = {model_name(item): item for item in running_rows if model_name(item)}
        running_by_digest = {
            str(item.get("digest") or ""): item
            for item in running_rows
            if str(item.get("digest") or "")
        }
        models = []
        show_errors = 0
        for tag in tag_rows:
            if not isinstance(tag, dict):
                continue
            name = model_name(tag)
            if not name:
                continue
            show, show_error = self._show_model(base_url, name)
            if show_error:
                show_errors += 1
            details = {**dict(tag.get("details") or {}), **dict(show.get("details") or {})}
            model_info = dict(show.get("model_info") or {})
            running = running_by_name.get(name) or running_by_digest.get(str(tag.get("digest") or ""))
            raw_capabilities = list(show.get("capabilities") or [])
            models.append(
                {
                    "model_id": f"ollama:{name}",
                    "name": name,
                    "display_name": name,
                    "provider_id": "ollama",
                    "capabilities": mapped_capabilities(raw_capabilities),
                    "provider_capabilities": raw_capabilities,
                    "installed": True,
                    "installation_status": "installed",
                    "size_bytes": int(tag.get("size") or 0),
                    "digest": tag.get("digest"),
                    "modified_at": tag.get("modified_at"),
                    "format": details.get("format"),
                    "family": details.get("family"),
                    "parameter_size": details.get("parameter_size"),
                    "quantization": details.get("quantization_level"),
                    "embedding_dimension": first_model_info(model_info, ".embedding_length"),
                    "context_length": first_model_info(model_info, ".context_length"),
                    "license": self._license_summary(show.get("license")),
                    "running": running is not None,
                    "runtime": {
                        "vram_bytes": int((running or {}).get("size_vram") or 0),
                        "memory_bytes": int((running or {}).get("size") or 0),
                        "context_length": (running or {}).get("context_length"),
                        "expires_at": (running or {}).get("expires_at"),
                        "device_evidence": "gpu_or_mixed" if int((running or {}).get("size_vram") or 0) else "unknown",
                    },
                    "estimated_ram_bytes": None,
                    "estimated_vram_bytes": None,
                    "compatibility": unverified_compatibility(),
                    "last_benchmark": None,
                    "last_error": show_error,
                    "current_task": None,
                    "source": ["ollama_tags", "ollama_ps", "ollama_show"],
                }
            )

        return models, {
            "available": True,
            "base_url": base_url,
            "installed_count": len(models),
            "running_count": sum(1 for item in models if item["running"]),
            "source": "ollama_api",
            "last_error": running_error,
            "detail_errors": show_errors,
        }

    def _show_model(self, base_url: str, name: str) -> tuple[dict[str, Any], str | None]:
        try:
            payload = self.transport.post_json(
                f"{base_url}/api/show",
                {"model": name, "verbose": False},
                timeout=3.0,
            )
            return (payload if isinstance(payload, dict) else {}), None
        except Exception as exc:
            return {}, self._safe_error(exc)

    def _configured_assignments(self, installed_names: set[str]) -> list[dict[str, Any]]:
        rows = [
            ("chat_primary", str(getattr(self.settings, "llm_model", "") or ""), "chat_reasoning"),
            ("chat_fallback", str(getattr(self.settings, "fallback_llm", "") or ""), "chat_reasoning"),
            ("embedding_primary", str(getattr(self.settings, "embed_model", "") or ""), "embedding"),
            ("embedding_fallback", str(getattr(self.settings, "fallback_embed_model", "") or ""), "embedding"),
        ]
        return [
            {
                "role": role,
                "model": model,
                "provider_id": "ollama",
                "capability": capability,
                "installed": model in installed_names,
                "status": "available" if model in installed_names else "missing",
                "compatibility": unverified_compatibility("assignment_not_benchmarked"),
            }
            for role, model, capability in rows
            if model
        ]

    def _faster_whisper_provider(self) -> dict[str, Any]:
        package_available = bool(self.package_finder("faster_whisper"))
        configured = str(self._runtime_value("media_asr_model", getattr(self.settings, "media_asr_model", "small")) or "small")
        candidate = Path(configured).expanduser()
        local_path = candidate.exists()
        if local_path:
            installation_status = "local_path_present"
        elif package_available:
            installation_status = "provider_managed_cache_unknown"
        else:
            installation_status = "package_not_installed"
        return {
            "provider_id": "faster_whisper",
            "label": "faster-whisper",
            "capabilities": ["asr"],
            "package_available": package_available,
            "installation_status": installation_status,
            "configured_model": configured,
            "model_root": str(candidate) if local_path else None,
            "last_error": None,
        }

    def _paddleocr_provider(self) -> dict[str, Any]:
        package_available = bool(self.package_finder("paddleocr"))
        model_root = str(self.environment.get("PADDLE_OCR_BASE_DIR") or "").strip() or None
        return {
            "provider_id": "paddleocr",
            "label": "PaddleOCR",
            "capabilities": ["ocr"],
            "package_available": package_available,
            "installation_status": "model_cache_not_verified" if package_available else "package_not_installed",
            "configured_model": None,
            "model_root": model_root,
            "last_error": None,
        }

    def _runtime_value(self, key: str, fallback: Any) -> Any:
        if self.runtime_settings is None:
            return fallback
        try:
            return self.runtime_settings.snapshot()["values"].get(key, fallback)
        except Exception:
            return fallback

    @staticmethod
    def _package_available(name: str) -> bool:
        try:
            return importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):
            return False

    @staticmethod
    def _license_summary(value: Any) -> str | None:
        text = str(value or "").strip()
        if not text:
            return None
        return text.splitlines()[0][:200]

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        return f"{exc.__class__.__name__}: {exc}"[:500]

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()
