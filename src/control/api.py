from __future__ import annotations

import hmac
import logging
import sqlite3
from typing import Any

from pydantic import BaseModel, Field

from src.gateway.memory_inspector import ReadModelUnavailableError
from src.runtime import mcp_runtime_status

from .memory_inspector import build_memory_inspector
from .obsidian_api import register_obsidian_routes
from .service import LocalControlService
from .capture_api import (
    CaptureCommonRequest,
    CaptureFileRequest,
    CaptureMediaRequest,
    CaptureShareRequest,
    CaptureTextRequest,
    CaptureWebRequest,
    register_capture_routes,
)
from .automatic_memory_api import register_automatic_memory_routes
from .work_routes import register_work_routes
from .work_service import WorkControlService

logger = logging.getLogger("lingji.control.read_model")
READ_MODEL_ERROR_CODE = "READ_MODEL_UNAVAILABLE"
READ_MODEL_ERROR_MESSAGE = "Structured read model is unavailable"


class SettingsPatch(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


class SettingsReset(BaseModel):
    keys: list[str] | None = None


class ComputePolicyPatch(BaseModel):
    mode: str


class StoragePlanRequest(BaseModel):
    policy: dict[str, Any] | None = None


class ConfirmationRequest(BaseModel):
    confirmation: str


class BackupRequest(BaseModel):
    profile: str | None = None
    include_raw: bool = False
    include_derived: bool = False


class BackupVerifyRequest(BaseModel):
    backup: str


class RestoreStageRequest(BaseModel):
    backup: str
    confirmation: str


class MediaAnalyzeRequest(BaseModel):
    media_path: str
    keyframe_directory: str | None = None
    overrides: dict[str, Any] = Field(default_factory=dict)


class AcceptanceRunRequest(BaseModel):
    vault: str | None = None
    chatgpt_export: str | None = None
    media: str | None = None
    deep_zip_check: bool = True
    hash_inputs: bool = True


class ShareRequest(BaseModel):
    source_type: str = "web"
    platform: str = ""
    input_path: str = ""
    adapter_name: str = ""
    title: str = ""
    url: str = ""
    source_url: str = ""
    author: str = ""
    account_name: str = ""
    description: str = ""
    published_at: str = ""
    duration_seconds: str | float = ""
    cover_url: str = ""
    media_url: str = ""
    text: str = ""
    selected_text: str = ""
    html: str = ""
    transcript: str = ""
    ocr_text: str = ""
    capture_method: str = "local_control_share"
    payload: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)


def create_control_app(
    settings: Any,
    *,
    service: LocalControlService | None = None,
    token: str = "",
):
    """Create the loopback-only FastAPI app used by Tauri and browser helpers."""

    try:
        from fastapi import Depends, FastAPI, Header, HTTPException, Query
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError as exc:
        raise RuntimeError("Install requirements-ui.txt to run the local control API") from exc

    control = service or LocalControlService(settings)
    work_control = WorkControlService(control.state_db) if getattr(control, "state_db", None) is not None else None
    inspector = None
    app = FastAPI(title="LingJi Local Control API", version="0.7.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://tauri.localhost",
            "https://tauri.localhost",
            "tauri://localhost",
        ],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "X-LingJi-Token"],
    )

    def authorize(x_lingji_token: str | None = Header(default=None)) -> None:
        if token and not hmac.compare_digest(str(x_lingji_token or ""), token):
            raise HTTPException(status_code=401, detail="Invalid local control token")

    def translate_error(exc: Exception) -> HTTPException:
        if isinstance(exc, (ReadModelUnavailableError, sqlite3.Error)):
            logger.error(
                "Structured read model request failed",
                exc_info=(type(exc), exc, exc.__traceback__),
            )
            return HTTPException(
                status_code=503,
                detail={
                    "code": READ_MODEL_ERROR_CODE,
                    "message": READ_MODEL_ERROR_MESSAGE,
                },
            )
        if isinstance(exc, LookupError):
            return HTTPException(status_code=404, detail=str(exc))
        if isinstance(exc, PermissionError):
            return HTTPException(status_code=403, detail=str(exc))
        if isinstance(exc, FileExistsError):
            return HTTPException(status_code=409, detail=str(exc))
        if isinstance(exc, FileNotFoundError):
            return HTTPException(status_code=404, detail=str(exc))
        return HTTPException(status_code=422, detail=str(exc))

    def memory_inspector():
        nonlocal inspector
        if inspector is None:
            try:
                inspector = build_memory_inspector(settings, control)
            except Exception as exc:
                raise ReadModelUnavailableError(READ_MODEL_ERROR_MESSAGE) from exc
        return inspector

    secured = [Depends(authorize)]

    @app.get("/api/health", dependencies=secured)
    def health() -> dict[str, Any]:
        return control.health()

    @app.get("/api/runtime/ping", dependencies=secured)
    def runtime_ping() -> dict[str, Any]:
        return {"status": "ok"}

    @app.get("/api/overview", dependencies=secured)
    def overview() -> dict[str, Any]:
        return control.overview()

    @app.get("/api/brain/status", dependencies=secured)
    def brain_status() -> dict[str, Any]:
        return control.brain_status()

    @app.get("/api/memory/status", dependencies=secured)
    def memory_status() -> dict[str, Any]:
        return control.memory_status()

    @app.get("/api/vector/status", dependencies=secured)
    def vector_status() -> dict[str, Any]:
        return control.vector_status()

    @app.get("/api/vector/coverage", dependencies=secured)
    def vector_coverage() -> dict[str, Any]:
        return control.vector_coverage()

    @app.get("/api/memory/inspector/status", dependencies=secured)
    def inspector_status() -> dict[str, Any]:
        try:
            return memory_inspector().status()
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get("/api/memory/inspector/cards", dependencies=secured)
    def inspector_cards(
        state: str | None = Query(default=None),
        action: str | None = Query(default=None),
        source: str | None = Query(default=None),
        source_id: str | None = Query(default=None),
        limit: int = Query(default=20, ge=1, le=50),
        offset: int = Query(default=0, ge=0),
        include_evidence: bool = Query(default=False),
        expand: bool = Query(default=False),
    ) -> dict[str, Any]:
        try:
            return memory_inspector().list_cards(
                state=state,
                action=action,
                source=source or source_id,
                limit=limit,
                offset=offset,
                include_evidence=include_evidence or expand,
            )
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get("/api/memory/inspector/cards-summary", dependencies=secured)
    def inspector_cards_summary() -> dict[str, Any]:
        try:
            return memory_inspector().card_summary()
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get("/api/memory/inspector/cards/{memory_id}", dependencies=secured)
    def inspector_card(
        memory_id: str,
        expand: bool = Query(default=True),
    ) -> dict[str, Any]:
        try:
            return memory_inspector().get_card(memory_id, include_evidence=expand)
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get("/api/memory/inspector/sources", dependencies=secured)
    def inspector_sources(
        source_type: str | None = Query(default=None),
        privacy: str | None = Query(default=None),
        project: str | None = Query(default=None),
        status: str | None = Query(default=None),
        q: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        try:
            return memory_inspector().list_sources(
                source_type=source_type,
                privacy=privacy,
                project=project,
                status=status,
                q=q,
                limit=limit,
                offset=offset,
            )
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get("/api/memory/inspector/sources/{source_id}", dependencies=secured)
    def inspector_source(source_id: str) -> dict[str, Any]:
        try:
            return memory_inspector().get_source(source_id)
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get("/api/memory/inspector/conversations", dependencies=secured)
    def inspector_conversations(
        source_id: str | None = Query(default=None),
        source_type: str | None = Query(default=None),
        privacy: str | None = Query(default=None),
        project: str | None = Query(default=None),
        from_time: str | None = Query(default=None),
        to_time: str | None = Query(default=None),
        q: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        try:
            return memory_inspector().list_conversations(
                source_id=source_id,
                source_type=source_type,
                privacy=privacy,
                project=project,
                from_time=from_time,
                to_time=to_time,
                q=q,
                limit=limit,
                offset=offset,
            )
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get(
        "/api/memory/inspector/conversations/{conversation_id}/messages",
        dependencies=secured,
    )
    def inspector_conversation_messages(
        conversation_id: str,
        role: str | None = Query(default=None),
        from_time: str | None = Query(default=None),
        to_time: str | None = Query(default=None),
        q: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        try:
            return memory_inspector().list_messages(
                conversation_id=conversation_id,
                role=role,
                from_time=from_time,
                to_time=to_time,
                q=q,
                limit=limit,
                offset=offset,
            )
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get(
        "/api/memory/inspector/conversations/{conversation_id}",
        dependencies=secured,
    )
    def inspector_conversation(conversation_id: str) -> dict[str, Any]:
        try:
            return memory_inspector().get_conversation(conversation_id)
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get("/api/memory/inspector/messages", dependencies=secured)
    def inspector_messages(
        conversation_id: str | None = Query(default=None),
        source_id: str | None = Query(default=None),
        role: str | None = Query(default=None),
        from_time: str | None = Query(default=None),
        to_time: str | None = Query(default=None),
        q: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        try:
            return memory_inspector().list_messages(
                conversation_id=conversation_id,
                source_id=source_id,
                role=role,
                from_time=from_time,
                to_time=to_time,
                q=q,
                limit=limit,
                offset=offset,
            )
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get("/api/memory/inspector/messages/{message_id}", dependencies=secured)
    def inspector_message(message_id: str) -> dict[str, Any]:
        try:
            return memory_inspector().get_message(message_id)
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get("/api/memory/inspector/memories", dependencies=secured)
    def inspector_memories(
        memory_type: str | None = Query(default=None),
        status: str | None = Query(default=None),
        privacy: str | None = Query(default=None),
        project: str | None = Query(default=None),
        q: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        try:
            return memory_inspector().list_memories(
                memory_type=memory_type,
                status=status,
                privacy=privacy,
                project=project,
                q=q,
                limit=limit,
                offset=offset,
            )
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get(
        "/api/memory/inspector/memories/{memory_id}/source",
        dependencies=secured,
    )
    def inspector_memory_source(memory_id: str) -> dict[str, Any]:
        try:
            return memory_inspector().memory_source(memory_id)
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get(
        "/api/memory/inspector/memories/{memory_id}/vector",
        dependencies=secured,
    )
    def inspector_memory_vector(memory_id: str) -> dict[str, Any]:
        try:
            return memory_inspector().memory_vector(memory_id)
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get(
        "/api/memory/inspector/memories/{memory_id}/evidence",
        dependencies=secured,
    )
    def inspector_memory_evidence(
        memory_id: str,
        limit: int = Query(default=20, ge=1, le=50),
        offset: int = Query(default=0, ge=0),
        include_content: bool = Query(default=True),
    ) -> dict[str, Any]:
        try:
            return memory_inspector().list_memory_evidence(
                memory_id,
                limit=limit,
                offset=offset,
                include_content=include_content,
            ).to_dict()
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get("/api/memory/inspector/memories/{memory_id}", dependencies=secured)
    def inspector_memory(
        memory_id: str,
        chunk_limit: int | None = Query(default=None, ge=1, le=50),
        max_chars: int | None = Query(default=None, ge=1, le=24000),
        cursor: str | None = Query(default=None, max_length=200),
    ) -> dict[str, Any]:
        try:
            return memory_inspector().get_memory(
                memory_id,
                chunk_limit=chunk_limit,
                max_chars=max_chars,
                cursor=cursor,
            )
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get("/api/mcp/status", dependencies=secured)
    def mcp_status() -> dict[str, Any]:
        runtime_values = control.get_settings().get("values", {})
        return mcp_runtime_status(settings, runtime_values)

    @app.get("/api/settings", dependencies=secured)
    def get_settings() -> dict[str, Any]:
        payload = control.get_settings()
        payload["runtime_contracts"] = {
            "mcp": mcp_runtime_status(settings, payload.get("values", {})),
            "memory": control.memory_status(),
            "vector": control.vector_status(),
        }
        return payload

    @app.patch("/api/settings", dependencies=secured)
    def update_settings(request: SettingsPatch) -> dict[str, Any]:
        try:
            return control.update_settings(request.values, actor="local_ui")
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.post("/api/settings/reset", dependencies=secured)
    def reset_settings(request: SettingsReset) -> dict[str, Any]:
        try:
            return control.reset_settings(request.keys, actor="local_ui")
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get("/api/hardware/capabilities", dependencies=secured)
    def hardware_capabilities() -> dict[str, Any]:
        return control.hardware_capabilities()

    @app.get("/api/hardware/telemetry", dependencies=secured)
    def hardware_telemetry() -> dict[str, Any]:
        return control.hardware_telemetry()

    @app.post("/api/hardware/refresh", dependencies=secured)
    def refresh_hardware() -> dict[str, Any]:
        return control.refresh_hardware()

    @app.get("/api/compute/policy", dependencies=secured)
    def compute_policy() -> dict[str, Any]:
        return control.compute_policy()

    @app.patch("/api/compute/policy", dependencies=secured)
    def update_compute_policy(request: ComputePolicyPatch) -> dict[str, Any]:
        try:
            return control.update_compute_policy(request.mode, actor="local_ui")
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get("/api/models/registry", dependencies=secured)
    def model_registry() -> dict[str, Any]:
        return control.model_registry()

    @app.get("/api/models", dependencies=secured)
    def models() -> dict[str, Any]:
        return control.models()

    @app.post("/api/models/refresh", dependencies=secured)
    def refresh_models() -> dict[str, Any]:
        return control.refresh_models()

    @app.get("/api/jobs", dependencies=secured)
    def jobs(
        status: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=1000),
    ) -> dict[str, Any]:
        return control.jobs(status=status, limit=limit)

    @app.get("/api/jobs/{job_id}", dependencies=secured)
    def job(job_id: str) -> dict[str, Any]:
        try:
            return control.job(job_id)
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get("/api/events", dependencies=secured)
    def events(limit: int = Query(default=100, ge=1, le=1000)) -> list[dict[str, Any]]:
        return control.recent_events(limit=limit)

    @app.get("/api/logs", dependencies=secured)
    def logs(lines: int = Query(default=300, ge=1, le=5000)) -> dict[str, Any]:
        return control.logs(lines=lines)

    @app.get("/api/providers", dependencies=secured)
    def providers() -> dict[str, Any]:
        return control.provider_status()

    @app.get("/api/acceptance/reports", dependencies=secured)
    def acceptance_reports(
        limit: int = Query(default=100, ge=1, le=1000),
    ) -> list[dict[str, Any]]:
        return control.list_acceptance_reports(limit=limit)

    @app.post("/api/acceptance/run", dependencies=secured)
    def run_acceptance(request: AcceptanceRunRequest) -> dict[str, Any]:
        try:
            return control.run_acceptance(
                vault=request.vault,
                chatgpt_export=request.chatgpt_export,
                media=request.media,
                deep_zip_check=request.deep_zip_check,
                hash_inputs=request.hash_inputs,
            )
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get("/api/storage", dependencies=secured)
    def storage_inventory() -> dict[str, Any]:
        return control.storage_inventory()

    @app.get("/api/storage/plans", dependencies=secured)
    def storage_plans(limit: int = Query(default=50, ge=1, le=500)) -> list[dict[str, Any]]:
        return control.list_storage_plans(limit=limit)

    @app.get("/api/storage/plans/{plan_id}", dependencies=secured)
    def storage_plan(plan_id: str) -> dict[str, Any]:
        try:
            return control.get_storage_plan(plan_id)
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.post("/api/storage/plans", dependencies=secured)
    def create_storage_plan(request: StoragePlanRequest) -> dict[str, Any]:
        try:
            return control.create_storage_plan(request.policy)
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.post("/api/storage/plans/{plan_id}/execute", dependencies=secured)
    def execute_storage_plan(plan_id: str, request: ConfirmationRequest) -> dict[str, Any]:
        try:
            return control.execute_storage_plan(plan_id, request.confirmation)
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.post("/api/storage/plans/{plan_id}/restore", dependencies=secured)
    def restore_storage_plan(plan_id: str, request: ConfirmationRequest) -> dict[str, Any]:
        try:
            return control.restore_storage_plan(plan_id, request.confirmation)
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get("/api/backups", dependencies=secured)
    def backups(limit: int = Query(default=100, ge=1, le=500)) -> list[dict[str, Any]]:
        return control.list_backups(limit=limit)

    @app.post("/api/backups", dependencies=secured)
    def create_backup(request: BackupRequest) -> dict[str, Any]:
        try:
            return control.create_backup(
                profile=request.profile,
                include_raw=request.include_raw,
                include_derived=request.include_derived,
            )
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.post("/api/backups/verify", dependencies=secured)
    def verify_backup(request: BackupVerifyRequest) -> dict[str, Any]:
        try:
            return control.verify_backup(request.backup)
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.post("/api/backups/stage-restore", dependencies=secured)
    def stage_restore(request: RestoreStageRequest) -> dict[str, Any]:
        try:
            return control.stage_restore(request.backup, request.confirmation)
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.post("/api/media/analyze", dependencies=secured)
    def analyze_media(request: MediaAnalyzeRequest) -> dict[str, Any]:
        try:
            return control.analyze_media(
                request.media_path,
                request.overrides,
                keyframe_directory=request.keyframe_directory,
            )
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.post("/api/share", dependencies=secured)
    def capture_share(request: ShareRequest) -> dict[str, Any]:
        try:
            return control.capture_share(request.model_dump())
        except Exception as exc:
            raise translate_error(exc) from exc

    register_obsidian_routes(
        app, control, dependencies=secured, translate_error=translate_error
    )
    register_automatic_memory_routes(app, control, secured)
    register_capture_routes(app, settings, control, token=token)
    if work_control is not None:
        register_work_routes(app, work_control, secured)
    return app
