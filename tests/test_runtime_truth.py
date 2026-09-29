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

    def stats(self):
        return {"queued": 1, "retrying": 0, "running": 0, "completed": 4, "failed": 2, "cancelled": 0, "pending": 1}


class _Runtime:
    def status(self):
        return {
            "pipelines": {
                "distill": {
                    "name": "distill",
                    "consecutive_failures": 2,
                    "total_failures": 5,
                    "degraded": True,
                    "last_error": "lock timeout",
                    "last_success_at": "2026-09-29T10:00:00",
                    "last_failure_at": "2026-09-29T12:00:00",
                }
            }
        }


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
    service.runtime = None
    service.work_control = SimpleNamespace(failures=lambda limit: {"failures": [], "total": 0})
    return service


def test_brain_status_surfaces_pipelines_queue_and_failure_ledger():
    service = _service(telemetry={"collected_at": None, "source": "unavailable", "stale": True, "errors": [], "gpus": []})
    service.runtime = _Runtime()
    service.work_control = SimpleNamespace(failures=lambda limit: {
        "failures": [
            {
                "failure_key": "k1",
                "stage": "parse",
                "reason": "bad file",
                "retryable": True,
                "requires_owner": True,
                "occurrence_count": 3,
                "last_seen_at": "2026-09-29T12:00:00",
            }
        ],
        "total": 1,
    })

    status = service.brain_status()

    assert status["pipelines"]["distill"]["degraded"] is True
    assert status["extraction_queue"]["failed"] == 2
    assert status["failure_ledger"]["total"] == 1
    assert status["failure_ledger"]["failures"][0]["stage"] == "parse"


def test_brain_status_isolates_missing_status_sections_as_warnings():
    service = _service(telemetry={"collected_at": None, "source": "unavailable", "stale": True, "errors": [], "gpus": []})
    service.runtime = SimpleNamespace(status=lambda: (_ for _ in ()).throw(RuntimeError("runtime unavailable")))
    service.work_control = SimpleNamespace(failures=lambda limit: (_ for _ in ()).throw(RuntimeError("ledger unavailable")))
    service.queue = SimpleNamespace(stats=lambda: (_ for _ in ()).throw(RuntimeError("queue unavailable")))

    status = service.brain_status()

    assert status["pipelines"] == {}
    assert status["extraction_queue"] == {}
    assert status["failure_ledger"] == {}
    codes = {warning["code"] for warning in status["warnings"]}
    assert "failure_ledger_unavailable" in codes
    assert "extraction_queue_unavailable" in codes
    assert "automatic_pipelines_unavailable" in codes


def test_embedding_defaults_use_distinct_primary_and_fallback():
    settings = Settings(_env_file=None)
    assert settings.embed_model == "qwen3-embedding:0.6b"
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


def test_save_index_survives_non_json_native_values(tmp_path):
    from datetime import datetime

    from src.indexer.index import PEMISIndex

    indexer = PEMISIndex.__new__(PEMISIndex)
    indexer.vault_path = tmp_path / "vault"
    indexer.storage_dir = tmp_path / "storage"
    indexer.index_path = indexer.storage_dir / "memory_index.json"

    indexer.save_index({"meta": {"version": "2.2", "total": 1}, "entries": {"a": {"updated": datetime(2026, 9, 29, 12, 0, 0)}}})

    import json as _json

    saved = _json.loads(indexer.index_path.read_text(encoding="utf-8"))
    assert saved["entries"]["a"]["updated"] == "2026-09-29 12:00:00"


def test_overview_ttl_cache_collapses_polled_rebuilds():
    import threading
    import time as _time

    from src.control.service import LocalControlService

    service = LocalControlService.__new__(LocalControlService)
    service._overview_lock = threading.Lock()
    service._overview_cache = None
    calls = {"count": 0}

    def _build():
        calls["count"] += 1
        return {"health": {"status": "healthy"}, "tick": calls["count"]}

    service._build_overview = _build  # type: ignore[method-assign]

    first = service.overview()
    second = service.overview()
    assert calls["count"] == 1, "TTL 内的重复轮询必须命中缓存"
    assert second is first

    # 过期后重建一次
    stamp, payload = service._overview_cache
    service._overview_cache = (stamp - service._OVERVIEW_CACHE_TTL_SECONDS - 1, payload)
    service.overview()
    assert calls["count"] == 2
