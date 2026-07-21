from __future__ import annotations

from types import SimpleNamespace

from src.config import Settings
from src.control.service import LocalControlService


class _Inventory:
    def inventory(self, *, force: bool = False):
        return {
            "assignments": [
                {"role": "chat_primary", "model": "qwen3:8b"},
                {"role": "embedding_primary", "model": "bge-m3"},
            ],
            "summary": {"installed_models": 2},
        }


class _Statistics:
    def snapshot(self):
        return {
            "state": "healthy",
            "workspace": "production",
            "source": "live",
            "stale": False,
            "as_of": "2026-07-22T00:00:00+00:00",
            "memory": {
                "state": "healthy",
                "documents": 4,
                "chunks": 8,
                "database_bytes": 1024,
                "revision": 3,
            },
            "embedding": {
                "state": "healthy",
                "active_model": "bge-m3",
                "configured_model": "bge-m3",
            },
            "vector": {
                "state": "healthy",
                "vectors": 8,
                "collection": "lingji_memory_production",
                "dimension": 1024,
                "rebuild_required": False,
            },
            "warnings": [],
        }


class _Queue:
    def list(self, *, limit: int):
        return []


def _service(*, telemetry):
    service = LocalControlService.__new__(LocalControlService)
    service.overview = lambda: {"health": {"status": "healthy"}}
    service.hardware_capabilities = lambda force=False: {
        "gpus": [
            {
                "gpu_id": "0",
                "name": "RTX 4060",
                "total_vram_bytes": 8 * 1024**3,
            }
        ],
        "cuda": {"driver_cuda_version": "12.4"},
    }
    service.hardware_telemetry = lambda force=False: telemetry
    service.model_inventory = _Inventory()
    service.memory_statistics = _Statistics()
    service.compute_policy = lambda: {"requested_mode": "auto"}
    service.queue = _Queue()
    return service


def test_embedding_defaults_use_distinct_primary_and_fallback():
    settings = Settings(_env_file=None)
    assert settings.embed_model == "bge-m3"
    assert settings.fallback_embed_model == "nomic-embed-text"
    assert settings.embed_model != settings.fallback_embed_model


def test_brain_status_preserves_real_zero_gpu_utilization():
    service = _service(
        telemetry={
            "collected_at": "2026-07-22T00:00:00+00:00",
            "source": "nvidia-smi",
            "stale": False,
            "errors": [],
            "gpus": [
                {
                    "gpu_id": "0",
                    "name": "RTX 4060",
                    "utilization_percent": 0.0,
                    "temperature_c": 41.0,
                    "total_vram_bytes": 8 * 1024**3,
                    "free_vram_bytes": 7 * 1024**3,
                    "used_vram_bytes": 1 * 1024**3,
                    "source": "nvidia-smi",
                }
            ],
        }
    )

    status = service.brain_status()

    assert status["gpus"][0]["utilization_percent"] == 0.0
    assert status["gpus"][0]["status"] == "available"
    assert status["gpus"][0]["stale"] is False
    assert status["embed_model"] == "bge-m3"


def test_brain_status_does_not_turn_missing_gpu_telemetry_into_zero():
    service = _service(
        telemetry={
            "collected_at": None,
            "source": "unavailable",
            "stale": True,
            "errors": ["nvidia-smi unavailable"],
            "gpus": [],
        }
    )

    status = service.brain_status()

    assert status["gpus"][0]["status"] == "unavailable"
    assert status["gpus"][0]["utilization_percent"] is None
    assert status["gpus"][0]["temperature_c"] is None
    assert status["gpus"][0]["used_vram_bytes"] is None
    assert status["status_stale"] is True
    assert any(item["code"] == "hardware_telemetry_errors" for item in status["warnings"])


def test_brain_status_uses_null_for_unknown_inventory_values():
    service = _service(
        telemetry={
            "collected_at": None,
            "source": "unavailable",
            "stale": True,
            "errors": [],
            "gpus": [],
        }
    )
    service.model_inventory = SimpleNamespace(inventory=lambda **_: {})

    status = service.brain_status()

    assert status["chat_model"] is None
    assert status["installed_models"] is None
