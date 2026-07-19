from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from src.acceptance import AcceptanceChecker
from src.acceptance_reports import AcceptanceReportStore
from src.extraction.bootstrap import build_extraction_pipeline
from src.extraction.queue import SQLiteExtractionQueue
from src.hardware import HardwareCapabilityService
from src.health import StartupHealthChecker
from src.media import (
    FasterWhisperProvider,
    MediaSemanticService,
    PaddleOCRProvider,
    PySceneDetectProvider,
)
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
    ):
        self.settings = settings
        self.state_db = state_db or StateDatabase(settings.state_db_path)
        self.runtime_settings = RuntimeSettingsStore(settings, state_db=self.state_db)
        self.health_checker = StartupHealthChecker(settings)
        self.queue = SQLiteExtractionQueue(settings.state_db_path)
        self.pipeline = pipeline
        self.storage = StorageLifecycleManager(settings, state_db=self.state_db)
        self.backups = BackupManager(settings, state_db=self.state_db)
        self.media_semantic = MediaSemanticService(settings.storage_path)
        self.acceptance_reports = AcceptanceReportStore(settings.storage_path / "reports" / "acceptance")
        self.hardware = hardware or HardwareCapabilityService(settings)

    def get_settings(self) -> dict[str, Any]:
        return self.runtime_settings.snapshot()

    def update_settings(
        self,
        values: Mapping[str, Any],
        *,
        actor: str = "owner",
    ) -> dict[str, Any]:
        return self.runtime_settings.update(values, actor=actor)

    def reset_settings(
        self,
        keys: list[str] | None = None,
        *,
        actor: str = "owner",
    ) -> dict[str, Any]:
        return self.runtime_settings.reset(keys, actor=actor)

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
        self.runtime_settings.update({"compute_mode": mode}, actor=actor)
        return self.compute_policy()

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
        return {
            "health": self.health(),
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
        return {
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
        self.hardware.close()

    @staticmethod
    def _tail(path: Path, limit: int) -> list[str]:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            rows = handle.readlines()
        return [line.rstrip("\n") for line in rows[-limit:]]
