from __future__ import annotations

import hmac
from typing import Any

from pydantic import BaseModel, Field

from .service import LocalControlService


class SettingsPatch(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


class SettingsReset(BaseModel):
    keys: list[str] | None = None


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
    app = FastAPI(title="LingJi Local Control API", version="0.2.0")
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
        if isinstance(exc, LookupError):
            return HTTPException(status_code=404, detail=str(exc))
        if isinstance(exc, PermissionError):
            return HTTPException(status_code=403, detail=str(exc))
        if isinstance(exc, FileExistsError):
            return HTTPException(status_code=409, detail=str(exc))
        if isinstance(exc, FileNotFoundError):
            return HTTPException(status_code=404, detail=str(exc))
        return HTTPException(status_code=422, detail=str(exc))

    secured = [Depends(authorize)]

    @app.get("/api/health", dependencies=secured)
    def health() -> dict[str, Any]:
        return control.health()

    @app.get("/api/overview", dependencies=secured)
    def overview() -> dict[str, Any]:
        return control.overview()

    @app.get("/api/settings", dependencies=secured)
    def get_settings() -> dict[str, Any]:
        return control.get_settings()

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

    return app
