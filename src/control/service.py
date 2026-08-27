from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from src.acceptance import AcceptanceChecker
from src.acceptance_reports import AcceptanceReportStore
from src.automatic_memory import SourceRegistry
from src.extraction.bootstrap import build_extraction_pipeline
from src.extraction.queue import SQLiteExtractionQueue
from src.gateway.memory_statistics import MemoryStatisticsService
from src.hardware import HardwareCapabilityService
from src.health import StartupHealthChecker
from src.media import (
    FasterWhisperProvider,
    MediaSemanticService,
    PaddleOCRProvider,
    PySceneDetectProvider,
)
from src.model_center import LocalModelInventoryService
from src.obsidian.service import ObsidianService
from src.storage import BackupManager, StateDatabase, StorageLifecycleManager

from .runtime_settings import RuntimeSettingsStore


class LocalControlService:
    """Framework-neutral management service shared by Tauri, API and tests."""

    def __init__(
        self,
        settings: Any,
        state_db: Any | None = None,
        *,
        pipeline: Any | None = None,
        hardware: HardwareCapabilityService | None = None,
        model_inventory: LocalModelInventoryService | None = None,
        memory_gateway: Any | None = None,
        memory_statistics: MemoryStatisticsService | None = None,
        queue: Any | None = None,
        automatic_memory_registry: SourceRegistry | None = None,
        runtime: Any | None = None,
    ):
        self.settings = settings
        self.state_db = state_db or StateDatabase(settings.state_db_path)
        self.automatic_memory_registry = automatic_memory_registry or SourceRegistry(self.state_db)
        self.runtime_settings = RuntimeSettingsStore(settings, state_db=self.state_db)
        self.obsidian = ObsidianService(
            settings, runtime_settings=self.runtime_settings, state_db=self.state_db
        )
        self.health_checker = StartupHealthChecker(settings)
        self.pipeline = pipeline
        # The packaged runtime injects the pipeline's queue wrapper so service,
        # worker and scheduler all share one logical extraction queue.  Keep
        # the historical fallback for lightweight callers that have no
        # pipeline yet.
        if queue is None:
            queue = getattr(pipeline, "queue", None)
        self.queue = queue if queue is not None else SQLiteExtractionQueue(settings.state_db_path)
        self.runtime = runtime
        self.storage = StorageLifecycleManager(settings, state_db=self.state_db)
        self.backups = BackupManager(settings, state_db=self.state_db)
        self.media_semantic = MediaSemanticService(settings.storage_path)
        self.acceptance_reports = AcceptanceReportStore(settings.storage_path / "reports" / "acceptance")
        self.hardware = hardware or HardwareCapabilityService(settings)
        self.model_inventory = model_inventory or LocalModelInventoryService(
            settings,
            runtime_settings=self.runtime_settings,
        )
        self.memory_gateway = memory_gateway
        live_statistics = getattr(memory_gateway, "statistics", None)
        self.memory_statistics = memory_statistics or live_statistics or MemoryStatisticsService(
            snapshot_path=MemoryStatisticsService.snapshot_path_for(
                settings,
                getattr(memory_gateway, "workspace", None),
            )
        )
        self._sync_hardware_settings()

    def brain_status(self) -> dict:
        """Aggregate runtime facts without converting unknown values to healthy or zero."""

        warnings: list[dict[str, Any]] = []
        try:
            overview = self.overview()
        except Exception as exc:
            overview = {}
            warnings.append(self._status_warning("overview_unavailable", "overview", exc))
        try:
            hardware = self.hardware_capabilities(force=False)
        except Exception as exc:
            hardware = {}
            warnings.append(self._status_warning("hardware_capabilities_unavailable", "hardware", exc))
        try:
            telemetry = self.hardware_telemetry(force=False)
        except Exception as exc:
            telemetry = {
                "collected_at": None,
                "gpus": [],
                "errors": [f"{type(exc).__name__}: {exc}"[:500]],
                "stale": True,
                "source": "unavailable",
            }
            warnings.append(self._status_warning("hardware_telemetry_unavailable", "hardware", exc))
        try:
            inventory = self.model_inventory.inventory(force=False)
        except Exception as exc:
            inventory = {}
            warnings.append(self._status_warning("model_inventory_unavailable", "models", exc))
        try:
            memory_runtime = self.memory_statistics.snapshot()
        except Exception as exc:
            memory_runtime = {
                "state": "configuration_required",
                "workspace": None,
                "source": "unavailable",
                "stale": True,
                "as_of": None,
                "memory": {"state": "configuration_required"},
                "vector": {"state": "configuration_required"},
                "embedding": {"state": "configuration_required", "active_model": None},
                "warnings": [],
            }
            warnings.append(self._status_warning("memory_statistics_unavailable", "memory", exc))

        memory = dict(memory_runtime.get("memory") or {})
        vector = dict(memory_runtime.get("vector") or {})
        embedding = dict(memory_runtime.get("embedding") or {})
        health = dict(overview.get("health") or {})

        capability_gpus = {
            str(item.get("gpu_id", index)): dict(item)
            for index, item in enumerate(hardware.get("gpus") or [])
            if isinstance(item, Mapping)
        }
        telemetry_errors = [str(item) for item in telemetry.get("errors") or []]
        telemetry_gpus = telemetry.get("gpus") or []
        gpus: list[dict[str, Any]] = []
        seen_gpu_ids: set[str] = set()
        for index, item in enumerate(telemetry_gpus):
            if not isinstance(item, Mapping):
                continue
            gpu_id = str(item.get("gpu_id", index))
            seen_gpu_ids.add(gpu_id)
            merged = {**capability_gpus.get(gpu_id, {}), **dict(item)}
            merged.setdefault("gpu_id", gpu_id)
            merged["status"] = "available"
            merged["collected_at"] = telemetry.get("collected_at")
            merged["stale"] = bool(telemetry.get("stale"))
            merged["errors"] = telemetry_errors
            gpus.append(merged)
        for gpu_id, item in capability_gpus.items():
            if gpu_id in seen_gpu_ids:
                continue
            merged = dict(item)
            merged.update(
                {
                    "gpu_id": gpu_id,
                    "status": "unavailable",
                    "collected_at": telemetry.get("collected_at"),
                    "stale": True,
                    "utilization_percent": None,
                    "temperature_c": None,
                    "used_vram_bytes": None,
                    "errors": telemetry_errors or ["dynamic_gpu_telemetry_unavailable"],
                }
            )
            gpus.append(merged)

        if telemetry_errors:
            warnings.append(
                {
                    "code": "hardware_telemetry_errors",
                    "stage": "hardware",
                    "severity": "warning",
                    "message": "; ".join(telemetry_errors)[:500],
                    "action": "Check psutil, NVIDIA driver and nvidia-smi availability.",
                }
            )

        assignments = [item for item in inventory.get("assignments") or [] if isinstance(item, Mapping)]
        chat_model = next(
            (item.get("model") for item in assignments if item.get("role") == "chat_primary"),
            None,
        )
        inventory_embed_model = next(
            (item.get("model") for item in assignments if item.get("role") == "embedding_primary"),
            None,
        )
        embed_model = (
            embedding.get("active_model")
            or embedding.get("configured_model")
            or embedding.get("primary_model")
            or inventory_embed_model
        )

        try:
            compute_policy = self.compute_policy()
        except Exception as exc:
            compute_policy = {}
            warnings.append(self._status_warning("compute_policy_unavailable", "hardware", exc))

        try:
            recent_tasks = self.queue.list(limit=10)
        except Exception as exc:
            recent_tasks = []
            warnings.append(self._status_warning("queue_status_unavailable", "extraction", exc))
        active_states = {"queued", "leased", "running", "retrying"}
        processing_status = (
            "active"
            if any(str(item.get("status") or "").lower() in active_states for item in recent_tasks)
            else "idle"
        )

        memory_state = str(memory_runtime.get("state") or "configuration_required")
        health_state = str(health.get("status") or "unknown")
        system_status = memory_state if memory_state != "healthy" else health_state
        warnings = [
            *[dict(item) for item in memory_runtime.get("warnings") or [] if isinstance(item, Mapping)],
            *warnings,
        ]

        return {
            "memory_count": memory.get("documents"),
            "memory_chunk_count": memory.get("chunks"),
            "memory_bytes": memory.get("database_bytes"),
            "memory_revision": memory.get("revision"),
            "memory_state": memory.get("state"),
            "vector_count": vector.get("vectors"),
            "vector_state": vector.get("state"),
            "vector_collection": vector.get("collection"),
            "vector_dimension": vector.get("dimension"),
            "vector_rebuild_required": vector.get("rebuild_required"),
            "embedding_state": embedding.get("state"),
            "chat_model": chat_model,
            "embed_model": embed_model,
            "installed_models": dict(inventory.get("summary") or {}).get("installed_models"),
            "gpus": gpus,
            "compute_mode": compute_policy.get("requested_mode"),
            "cuda_version": dict(hardware.get("cuda") or {}).get("runtime_version")
            or dict(hardware.get("cuda") or {}).get("driver_cuda_version"),
            "recent_tasks": recent_tasks,
            "processing_status": processing_status,
            "system_status": system_status,
            "workspace": memory_runtime.get("workspace"),
            "status_source": memory_runtime.get("source"),
            "status_stale": bool(memory_runtime.get("stale")) or bool(telemetry.get("stale")),
            "status_as_of": memory_runtime.get("as_of") or telemetry.get("collected_at"),
            "warnings": warnings,
        }

    def memory_status(self) -> dict[str, Any]:
        return self.memory_statistics.memory_status()

    def vector_status(self) -> dict[str, Any]:
        return self.memory_statistics.vector_status()

    def vector_coverage(self) -> dict[str, Any]:
        return self.memory_statistics.vector_coverage()

    def get_settings(self) -> dict[str, Any]:
        return self.runtime_settings.snapshot()

    def update_settings(
        self,
        values: Mapping[str, Any],
        *,
        actor: str = "owner",
    ) -> dict[str, Any]:
        snapshot = self.runtime_settings.update(values, actor=actor)
        self._sync_hardware_settings()
        return snapshot

    def reset_settings(
        self,
        keys: list[str] | None = None,
        *,
        actor: str = "owner",
    ) -> dict[str, Any]:
        snapshot = self.runtime_settings.reset(keys, actor=actor)
        self._sync_hardware_settings()
        return snapshot

    def obsidian_status(self) -> dict[str, Any]:
        return self.obsidian.status()

    def validate_obsidian_settings(self, values: Mapping[str, Any]) -> dict[str, Any]:
        return self.obsidian.validate_configuration(values)

    def hardware_capabilities(self, *, force: bool = False) -> dict[str, Any]:
        return self.hardware.capabilities(force=force)

    def hardware_telemetry(self, *, force: bool = False) -> dict[str, Any]:
        return self.hardware.telemetry(force=force)

    def refresh_hardware(self) -> dict[str, Any]:
        return self.hardware.refresh()

    def compute_policy(self) -> dict[str, Any]:
        configured = self.runtime_settings.compute_policy()
        return {
            **configured,
            **self.hardware.resolve_compute_policy(
                configured["mode"],
                gpu_id=configured["preferred_gpu_id"],
            ),
        }

    def update_compute_policy(self, mode: str, *, actor: str = "owner") -> dict[str, Any]:
        self.update_settings({"compute_mode": mode}, actor=actor)
        return self.compute_policy()

    def model_registry(self) -> dict[str, Any]:
        return self.model_inventory.registry()

    def models(self, *, force: bool = False) -> dict[str, Any]:
        return self.model_inventory.inventory(force=force)

    def refresh_models(self) -> dict[str, Any]:
        return self.model_inventory.refresh()

    def health(self) -> dict[str, Any]:
        return self.health_checker.run()

    def overview(self) -> dict[str, Any]:
        inventory = self.storage.inventory()
        settings_snapshot = self.runtime_settings.snapshot()
        values = settings_snapshot["values"]
        total_bytes = int(inventory["totals"]["bytes"])
        max_bytes = int(float(values["storage_max_gb"]) * 1024**3)
        free_bytes = int(inventory["totals"]["disk_free_bytes"])
        minimum_free = int(float(values["storage_min_free_gb"]) * 1024**3)
        capabilities = self.hardware_capabilities()
        memory_runtime = self.memory_statistics.snapshot()
        return {
            "health": self.health(),
            "memory_runtime": memory_runtime,
            "memory_stats": dict(memory_runtime.get("memory") or {}),
            "embedding_status": dict(memory_runtime.get("embedding") or {}),
            "vector_status": dict(memory_runtime.get("vector") or {}),
            "vector_coverage": dict(memory_runtime.get("coverage") or {}),
            "queue": {
                "stats": self.queue.stats(),
                "recent": self.queue.list(limit=20),
            },
            "storage": {
                **inventory,
                "alerts": {
                    "over_configured_limit": bool(max_bytes and total_bytes > max_bytes),
                    "below_minimum_free": free_bytes < minimum_free,
                },
            },
            "scheduler": self.state_db.list_scheduler_jobs(),
            "events": self.recent_events(limit=30),
            "providers": self.provider_status(),
            "acceptance": self.list_acceptance_reports(limit=1),
            "hardware": {
                "cpu": capabilities["cpu"],
                "memory": capabilities["memory"],
                "gpus": capabilities["gpus"],
                "cuda": capabilities["cuda"],
                "toolchains": capabilities["toolchains"],
                "compute_policy": self.compute_policy(),
            },
            "settings_summary": {
                "overrides": settings_snapshot["overrides"],
                "groups": sorted({item["group"] for item in settings_snapshot["definitions"].values()}),
            },
        }

    def jobs(self, *, status: str | None = None, limit: int = 100) -> dict[str, Any]:
        return {"stats": self.queue.stats(), "jobs": self.queue.list(status=status, limit=limit)}

    def job(self, job_id: str) -> dict[str, Any]:
        return self.queue.get(job_id)

    def recent_events(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.state_db.recent_events(limit=max(min(int(limit), 1000), 1))
        output = []
        for row in rows:
            item = dict(row)
            raw = item.pop("payload_json", "{}")
            try:
                item["payload"] = json.loads(raw or "{}")
            except (TypeError, json.JSONDecodeError):
                item["payload"] = {}
            output.append(item)
        return output

    def logs(self, *, lines: int = 300) -> dict[str, Any]:
        limit = max(min(int(lines), 5000), 1)
        candidates = [
            self.settings.log_path / "lingji_service.log",
            Path(__file__).resolve().parents[2] / "logs" / "lingji_service.log",
        ]
        path = next((candidate for candidate in candidates if candidate.is_file()), candidates[0])
        if not path.is_file():
            return {"path": str(path), "exists": False, "lines": []}
        return {
            "path": str(path),
            "exists": True,
            "lines": self._tail(path, limit),
            "size": path.stat().st_size,
        }

    def run_acceptance(
        self,
        *,
        vault: str | None = None,
        chatgpt_export: str | None = None,
        media: str | None = None,
        deep_zip_check: bool = True,
        hash_inputs: bool = True,
    ) -> dict[str, Any]:
        checked_settings = self.settings.model_copy(
            update={
                "vault_dir": vault or self.settings.vault_dir,
                "vault_auto_init": False,
            }
        )
        report = AcceptanceChecker(
            checked_settings,
            chatgpt_export=Path(chatgpt_export).expanduser() if chatgpt_export else None,
            media_path=Path(media).expanduser() if media else None,
            deep_zip_check=deep_zip_check,
            hash_inputs=hash_inputs,
        ).run()
        saved = self.acceptance_reports.save(report)
        self.state_db.append_event(
            "real_environment_acceptance",
            "acceptance_report",
            Path(saved["json_path"]).stem,
            {
                "status": report["status"],
                "errors": report["error_count"],
                "warnings": report["warning_count"],
                "inputs_unchanged": report["inputs_unchanged"],
                "json_path": saved["json_path"],
            },
        )
        return saved

    def list_acceptance_reports(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.acceptance_reports.list_reports(limit=limit)

    def storage_inventory(self) -> dict[str, Any]:
        return self.storage.inventory()

    def create_storage_plan(self, policy: Mapping[str, Any] | None = None) -> dict[str, Any]:
        selected = dict(policy or self.runtime_settings.storage_policy())
        return self.storage.create_plan(selected)

    def list_storage_plans(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.storage.list_plans(limit=limit)

    def get_storage_plan(self, plan_id: str) -> dict[str, Any]:
        return self.storage.get_plan(plan_id)

    def execute_storage_plan(self, plan_id: str, confirmation: str) -> dict[str, Any]:
        return self.storage.execute_plan(plan_id, confirmation)

    def restore_storage_plan(self, plan_id: str, confirmation: str) -> dict[str, Any]:
        return self.storage.restore_plan(plan_id, confirmation)

    def create_backup(
        self,
        *,
        profile: str | None = None,
        include_raw: bool = False,
        include_derived: bool = False,
    ) -> dict[str, Any]:
        if not profile:
            profile = str(self.runtime_settings.snapshot()["values"]["backup_default_profile"])
        return self.backups.create_backup(
            profile=profile,
            include_raw=include_raw,
            include_derived=include_derived,
        )

    def list_backups(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.backups.list_backups(limit=limit)

    def verify_backup(self, backup: str) -> dict[str, Any]:
        return self.backups.verify_backup(backup)

    def stage_restore(self, backup: str, confirmation: str) -> dict[str, Any]:
        return self.backups.stage_restore(backup, confirmation)

    def provider_status(self) -> dict[str, Any]:
        memory_runtime = self.memory_statistics.snapshot()
        return {
            "embedding": dict(memory_runtime.get("embedding") or {}),
            "qdrant": dict(memory_runtime.get("vector") or {}),
            "faster_whisper": {
                "available": FasterWhisperProvider.available(),
                "capability": "asr",
                "optional_requirements": "requirements-media.txt",
            },
            "paddleocr": {
                "available": PaddleOCRProvider.available(),
                "capability": "ocr",
                "optional_requirements": "requirements-media.txt",
            },
            "pyscenedetect": {
                "available": PySceneDetectProvider.available(),
                "capability": "scene_detection",
                "optional_requirements": "requirements-media.txt",
            },
        }

    def analyze_media(
        self,
        media_path: str,
        overrides: Mapping[str, Any] | None = None,
        *,
        keyframe_directory: str | None = None,
    ) -> dict[str, Any]:
        path = Path(media_path).expanduser()
        options = self.runtime_settings.options_for_source("media")
        options.update(dict(overrides or {}))
        return self.media_semantic.analyze(
            path,
            options,
            keyframe_directory=keyframe_directory,
        )

    def capture_share(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        source_type = str(payload.get("source_type") or payload.get("platform") or "web")
        input_path = str(payload.get("input_path") or "").strip()
        title = str(payload.get("title") or "主动投喂").strip()
        pipeline = self.pipeline or build_extraction_pipeline(self.settings)
        if input_path:
            path = Path(input_path).expanduser()
            options = self.runtime_settings.options_for_source(source_type)
            options.update(dict(payload.get("options") or {}))
            priority = self.runtime_settings.priority_for_source(source_type)
            return {
                "mode": "queued",
                "job": pipeline.enqueue(
                    source_type,
                    input_path=path,
                    payload={"title": title, **dict(payload.get("payload") or {})},
                    options=options,
                    priority=priority,
                    adapter_name=str(payload.get("adapter_name") or "") or None,
                ),
            }
        capture_payload = {
            "url": payload.get("url") or payload.get("source_url") or "",
            "title": title,
            "author": payload.get("author") or "",
            "account_name": payload.get("account_name") or "",
            "description": payload.get("description") or "",
            "published_at": payload.get("published_at") or "",
            "duration_seconds": payload.get("duration_seconds") or "",
            "cover_url": payload.get("cover_url") or "",
            "media_url": payload.get("media_url") or "",
            "text": payload.get("text") or payload.get("selected_text") or "",
            "html": payload.get("html") or "",
            "transcript": payload.get("transcript") or "",
            "ocr_text": payload.get("ocr_text") or "",
            "platform": payload.get("platform") or source_type,
            "capture_method": payload.get("capture_method") or "local_control_share",
        }
        return {
            "mode": "immediate",
            "result": pipeline.execute(
                source_type,
                payload=capture_payload,
                options=dict(payload.get("options") or {}),
                adapter_name="web_capture",
            ),
        }

    def close(self) -> None:
        self.model_inventory.close()
        self.hardware.close()

    def _sync_hardware_settings(self) -> None:
        policy = self.runtime_settings.compute_policy()
        configure = getattr(self.hardware, "configure", None)
        if callable(configure):
            configure(
                cache_seconds=float(policy["static_refresh_seconds"]),
                telemetry_cache_seconds=float(policy["foreground_interval_seconds"]),
                gpu_cache_seconds=float(policy["nvidia_smi_min_interval_seconds"]),
            )

    @staticmethod
    def _status_warning(code: str, stage: str, exc: Exception) -> dict[str, Any]:
        return {
            "code": code,
            "stage": stage,
            "severity": "warning",
            "message": f"{type(exc).__name__}: {exc}"[:500],
            "action": "Inspect the named runtime provider and retry the status request.",
        }

    @staticmethod
    def _tail(path: Path, limit: int) -> list[str]:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            rows = handle.readlines()
        return [line.rstrip("\n") for line in rows[-limit:]]
