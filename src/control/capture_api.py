from __future__ import annotations

import hmac
import logging
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.assistant_hub import (
    AiAssistantDiscoveryService,
    AiMemoryConnectorService,
    AssistantImportPlanner,
    ConnectorError,
)

from .capture import (
    CAPTURE_SERVICE_UNAVAILABLE,
    CaptureControlError,
    CaptureControlService,
    CaptureRuntimeSettingsStore,
)

logger = logging.getLogger("lingji.control.capture_api")


class CaptureCommonRequest(BaseModel):
    capture_id: str = ""
    title: str = ""
    project_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    privacy: str = "private"
    priority: int = Field(default=100, ge=0, le=10000)
    process_later: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    adapter_name: str = ""


class CaptureTextRequest(CaptureCommonRequest):
    text: str = Field(min_length=1)
    source_type: str = "web"


class CaptureWebRequest(CaptureCommonRequest):
    url: str = ""
    text: str = ""
    html: str = ""
    author: str = ""
    account_name: str = ""
    published_at: str = ""
    platform: str = ""
    description: str = ""
    external_id: str = ""
    source_type: str = "web"


class CaptureFileRequest(CaptureCommonRequest):
    input_path: str = Field(min_length=1)
    source_type: str = "web"


class CaptureMediaRequest(CaptureCommonRequest):
    input_path: str = Field(min_length=1)
    allow_ocr: bool = False
    allow_transcription: bool = False
    extract_keyframes: bool = False
    extract_audio: bool = False


class CaptureShareRequest(BaseModel):
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
    project_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    privacy: str = "private"
    priority: int = Field(default=100, ge=0, le=10000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorActionRequest(BaseModel):
    confirmation: str = ""


class AssistantCandidateImportRequest(BaseModel):
    confirmation: str = ""


class AssistantSelectedFileImportRequest(BaseModel):
    input_path: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    confirmation: str = ""


def register_capture_routes(app: Any, settings: Any, control: Any, *, token: str) -> None:
    from fastapi import Depends, Header, HTTPException, Query
    from fastapi.responses import JSONResponse

    capture: CaptureControlService | None = None
    connectors: AiMemoryConnectorService | None = None
    imports: AssistantImportPlanner | None = None

    def authorize(x_lingji_token: str | None = Header(default=None)) -> None:
        if token and not hmac.compare_digest(str(x_lingji_token or ""), token):
            raise HTTPException(status_code=401, detail="Invalid local control token")

    def capture_control() -> CaptureControlService:
        nonlocal capture
        if capture is not None:
            return capture
        existing = getattr(control, "capture_control", None)
        if existing is not None:
            capture = existing
            return capture
        try:
            from src.extraction.bootstrap import build_extraction_pipeline

            state_db = getattr(control, "state_db", None)
            runtime_settings = CaptureRuntimeSettingsStore(settings, state_db=state_db)
            pipeline = getattr(control, "pipeline", None)
            if pipeline is None:
                pipeline = build_extraction_pipeline(settings, runtime_settings=runtime_settings)
                try:
                    control.pipeline = pipeline
                except Exception:
                    pass
            queue = getattr(pipeline, "queue", None) or getattr(control, "queue", None)
            capture = CaptureControlService(
                settings,
                pipeline=pipeline,
                queue=queue,
                runtime_settings=runtime_settings,
                state_db=state_db,
            )
            try:
                control.capture_control = capture
                control.queue = capture.queue
            except Exception:
                pass
            return capture
        except CaptureControlError:
            raise
        except Exception as exc:
            logger.exception("Capture control initialization failed")
            raise CaptureControlError(
                CAPTURE_SERVICE_UNAVAILABLE,
                "Capture service unavailable; see local logs",
                status_code=503,
            ) from exc

    def connector_control() -> AiMemoryConnectorService:
        nonlocal connectors
        if connectors is None:
            connectors = AiMemoryConnectorService(storage_path=settings.storage_path)
        return connectors

    def import_control() -> AssistantImportPlanner:
        nonlocal imports
        if imports is None:
            imports = AssistantImportPlanner(storage_path=settings.storage_path)
        return imports

    def translate(exc: Exception) -> HTTPException:
        if isinstance(exc, ConnectorError):
            return HTTPException(
                status_code=exc.status_code,
                detail={"code": exc.code, "message": exc.message},
            )
        if isinstance(exc, CaptureControlError):
            return HTTPException(
                status_code=exc.status_code,
                detail={"code": exc.code, "message": exc.message},
            )
        if isinstance(exc, ValueError):
            return HTTPException(
                status_code=409,
                detail={"code": "IMPORT_CANDIDATE_INVALID", "message": str(exc)},
            )
        logger.exception("Capture API request failed")
        return HTTPException(
            status_code=503,
            detail={
                "code": CAPTURE_SERVICE_UNAVAILABLE,
                "message": "Capture service unavailable; see local logs",
            },
        )

    def response(payload: dict[str, Any]) -> JSONResponse:
        return JSONResponse(status_code=200 if payload.get("duplicate") else 202, content=payload)

    def assistant_scan() -> dict[str, Any]:
        workspace = str(getattr(settings, "workspace", "") or "")
        payload = AiAssistantDiscoveryService(workspace=workspace).scan()
        payload["import_plan"] = import_control().plan()
        return payload

    def selected_file_payload(request: AssistantSelectedFileImportRequest) -> dict[str, Any]:
        if request.confirmation != "AUTHORIZE_SELECTED_ASSISTANT_IMPORT":
            raise HTTPException(
                status_code=403,
                detail={"code": "CONFIRMATION_REQUIRED", "message": "读取选中文件需要明确授权"},
            )
        source_id = request.source_id.strip().lower()
        mapping = {
            "chatgpt": ("chatgpt_export", "chatgpt_export", {".zip", ".json"}),
            "codex": ("codex_report", "codex_work_report", {".json"}),
        }
        if source_id not in mapping:
            raise HTTPException(
                status_code=422,
                detail={"code": "UNSUPPORTED_IMPORT_SOURCE", "message": "当前来源没有正式导入适配器"},
            )
        source_type, adapter_name, suffixes = mapping[source_id]
        path = Path(request.input_path).expanduser().resolve(strict=False)
        if not path.is_file() or path.is_symlink() or path.suffix.lower() not in suffixes:
            raise HTTPException(
                status_code=409,
                detail={"code": "INVALID_IMPORT_FILE", "message": "所选文件不存在或格式不受支持"},
            )
        return {
            "input_path": str(path),
            "source_type": source_type,
            "adapter_name": adapter_name,
            "privacy": "private",
            "process_later": True,
            "metadata": {
                "origin": "assistant_hub_selected_file",
                "owner_authorized": True,
                "source_id": source_id,
            },
        }

    def runtime_identity() -> dict[str, Any]:
        workspace = str(
            os.environ.get("LINGJI_WORKSPACE")
            or getattr(settings, "workspace", "")
            or getattr(settings, "workspace_name", "")
            or "unknown"
        ).strip().lower()
        configured_root = str(os.environ.get("LINGJI_OWNER_DATA_ROOT") or "").strip()
        if configured_root:
            root = Path(configured_root).expanduser().resolve(strict=False)
        else:
            storage = Path(
                str(
                    getattr(settings, "storage_path", "")
                    or getattr(settings, "storage_dir", "")
                    or ""
                )
            ).expanduser().resolve(strict=False)
            root = storage.parent if storage.name.lower() == "storage" else storage
        return {
            "status": "ok",
            "binding_contract_version": 1,
            "data_root": str(root),
            "workspace": workspace,
        }

    replaced_routes = {
        ("/api/share", "POST"),
        ("/api/runtime/ping", "GET"),
    }
    app.router.routes[:] = [
        route
        for route in app.router.routes
        if not any(
            getattr(route, "path", None) == path
            and method in (getattr(route, "methods", set()) or set())
            for path, method in replaced_routes
        )
    ]
    secured = [Depends(authorize)]

    @app.get("/api/runtime/ping", dependencies=secured)
    def runtime_ping() -> dict[str, Any]:
        return runtime_identity()

    @app.post("/api/capture/text", dependencies=secured)
    def capture_text(request: CaptureTextRequest):
        try:
            return response(capture_control().submit_text(request.model_dump()))
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/api/capture/web", dependencies=secured)
    def capture_web(request: CaptureWebRequest):
        try:
            return response(capture_control().submit_web(request.model_dump()))
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/api/capture/file", dependencies=secured)
    def capture_file(request: CaptureFileRequest):
        try:
            return response(capture_control().submit_file(request.model_dump()))
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/api/capture/media", dependencies=secured)
    def capture_media(request: CaptureMediaRequest):
        try:
            return response(capture_control().submit_media(request.model_dump()))
        except Exception as exc:
            raise translate(exc) from exc

    @app.get("/api/capture/status", dependencies=secured)
    def capture_status() -> dict[str, Any]:
        try:
            return capture_control().status()
        except Exception as exc:
            raise translate(exc) from exc

    @app.get("/api/capture/capabilities", dependencies=secured)
    def capture_capabilities() -> dict[str, Any]:
        try:
            return capture_control().capabilities()
        except Exception as exc:
            raise translate(exc) from exc

    @app.get("/api/capture/jobs", dependencies=secured)
    def capture_jobs(
        status: str | None = Query(default=None),
        source_type: str | None = Query(default=None),
        q: str | None = Query(default=None),
        limit: int = Query(default=30, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        try:
            return capture_control().list_jobs(
                status=status,
                source_type=source_type,
                q=q,
                limit=limit,
                offset=offset,
            )
        except Exception as exc:
            raise translate(exc) from exc

    @app.get("/api/capture/jobs/{job_id}", dependencies=secured)
    def capture_job(job_id: str) -> dict[str, Any]:
        try:
            return capture_control().get_job(job_id)
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/api/capture/jobs/{job_id}/retry", dependencies=secured)
    def capture_job_retry(job_id: str) -> dict[str, Any]:
        try:
            return capture_control().retry_job(job_id)
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/api/capture/jobs/{job_id}/cancel", dependencies=secured)
    def capture_job_cancel(job_id: str) -> dict[str, Any]:
        try:
            return capture_control().cancel_job(job_id)
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/api/capture/pause", dependencies=secured)
    def capture_pause() -> dict[str, Any]:
        try:
            return capture_control().pause()
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/api/capture/resume", dependencies=secured)
    def capture_resume() -> dict[str, Any]:
        try:
            return capture_control().resume()
        except Exception as exc:
            raise translate(exc) from exc

    @app.get("/api/assistant-hub/status", dependencies=secured)
    def assistant_hub_status() -> dict[str, Any]:
        return assistant_scan()

    @app.post("/api/assistant-hub/scan", dependencies=secured)
    def assistant_hub_scan() -> dict[str, Any]:
        return assistant_scan()

    @app.get("/api/assistant-hub/import-plan", dependencies=secured)
    def assistant_hub_import_plan() -> dict[str, Any]:
        return import_control().plan()

    @app.post("/api/assistant-hub/import-candidates/{candidate_id}/authorize", dependencies=secured)
    def assistant_hub_authorize_candidate(
        candidate_id: str,
        request: AssistantCandidateImportRequest,
    ):
        expected = import_control().expected_confirmation(candidate_id)
        if request.confirmation != expected:
            raise HTTPException(
                status_code=403,
                detail={"code": "CONFIRMATION_REQUIRED", "message": "读取候选导出包需要明确授权"},
            )
        try:
            selected = import_control().resolve_authorized_candidate(candidate_id)
            payload = {
                "input_path": selected["input_path"],
                "source_type": selected["source_type"],
                "adapter_name": selected["adapter_name"],
                "privacy": "private",
                "process_later": True,
                "metadata": {
                    "origin": "assistant_hub_discovered_candidate",
                    "owner_authorized": True,
                    "source_id": selected["source_id"],
                    "display_name": selected["display_name"],
                },
            }
            return response(capture_control().submit_file(payload))
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/api/assistant-hub/import-selected-file", dependencies=secured)
    def assistant_hub_import_selected_file(request: AssistantSelectedFileImportRequest):
        try:
            return response(capture_control().submit_file(selected_file_payload(request)))
        except HTTPException:
            raise
        except Exception as exc:
            raise translate(exc) from exc

    @app.get("/api/assistant-hub/connections", dependencies=secured)
    def assistant_hub_connections(live: bool = Query(default=False)) -> dict[str, Any]:
        try:
            return connector_control().status(live=live)
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/api/assistant-hub/connections/{connector_id}/preview", dependencies=secured)
    def assistant_hub_connection_preview(connector_id: str) -> dict[str, Any]:
        try:
            return connector_control().preview(connector_id)
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/api/assistant-hub/connections/{connector_id}/apply", dependencies=secured)
    def assistant_hub_connection_apply(
        connector_id: str,
        request: ConnectorActionRequest,
    ) -> dict[str, Any]:
        try:
            return connector_control().apply(connector_id, request.confirmation)
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/api/assistant-hub/connections/{connector_id}/test", dependencies=secured)
    def assistant_hub_connection_test(connector_id: str) -> dict[str, Any]:
        try:
            return connector_control().test(connector_id)
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/api/assistant-hub/connections/{connector_id}/rollback", dependencies=secured)
    def assistant_hub_connection_rollback(
        connector_id: str,
        request: ConnectorActionRequest,
    ) -> dict[str, Any]:
        try:
            return connector_control().rollback(connector_id, request.confirmation)
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/api/share", dependencies=secured)
    def capture_share(request: CaptureShareRequest):
        try:
            return response(capture_control().submit_share(request.model_dump()))
        except Exception as exc:
            raise translate(exc) from exc
