from __future__ import annotations

import hmac
import logging
from typing import Any

from pydantic import BaseModel, Field

from ._api_core import *  # noqa: F401,F403
from ._api_core import create_control_app as _create_control_app
from .capture import (
    CAPTURE_SERVICE_UNAVAILABLE,
    CaptureControlError,
    CaptureControlService,
    CaptureRuntimeSettingsStore,
)
from .service import LocalControlService

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


def _register_capture_routes(app: Any, settings: Any, control: Any, *, token: str) -> None:
    from fastapi import Depends, Header, HTTPException, Query
    from fastapi.responses import JSONResponse

    capture: CaptureControlService | None = None

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

    def translate(exc: Exception) -> HTTPException:
        if isinstance(exc, CaptureControlError):
            return HTTPException(
                status_code=exc.status_code,
                detail={"code": exc.code, "message": exc.message},
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

    app.router.routes[:] = [
        route
        for route in app.router.routes
        if not (
            getattr(route, "path", None) == "/api/share"
            and "POST" in (getattr(route, "methods", set()) or set())
        )
    ]
    secured = [Depends(authorize)]

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

    @app.post("/api/share", dependencies=secured)
    def capture_share(request: CaptureShareRequest):
        try:
            return response(capture_control().submit_share(request.model_dump()))
        except Exception as exc:
            raise translate(exc) from exc


def create_control_app(
    settings: Any,
    *,
    service: LocalControlService | None = None,
    token: str = "",
):
    """Create the existing Control API and attach the P2-05A capture routes."""

    control = service or LocalControlService(settings)
    app = _create_control_app(settings, service=control, token=token)
    _register_capture_routes(app, settings, control, token=token)
    return app
