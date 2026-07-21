from __future__ import annotations

from typing import Any

from ._capture_api_core import *  # noqa: F401,F403
from ._capture_api_core import create_control_app as _create_control_app
from .capture import CaptureControlService, CaptureRuntimeSettingsStore
from .service import LocalControlService


def create_control_app(
    settings: Any,
    *,
    service: LocalControlService | None = None,
    token: str = "",
):
    """Create the Control API with one long-lived capture service."""

    control = service or LocalControlService(settings)
    existing = getattr(control, "capture_control", None)
    state_db = getattr(control, "state_db", None)
    if existing is None and state_db is not None:
        from src.extraction.bootstrap import build_extraction_pipeline

        shared_settings = CaptureRuntimeSettingsStore(settings, state_db=state_db)
        if hasattr(control, "runtime_settings"):
            control.runtime_settings = shared_settings
        pipeline = getattr(control, "pipeline", None)
        if pipeline is None:
            pipeline = build_extraction_pipeline(settings, runtime_settings=shared_settings)
            control.pipeline = pipeline
        control.queue = getattr(pipeline, "queue", control.queue)
        control.capture_control = CaptureControlService(
            settings,
            pipeline=pipeline,
            queue=control.queue,
            runtime_settings=CaptureRuntimeSettingsStore(settings, state_db=None),
            state_db=state_db,
        )
    return _create_control_app(settings, service=control, token=token)
