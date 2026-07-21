from __future__ import annotations

import hmac
import threading
from dataclasses import dataclass
from typing import Any, Callable

from src.control.codex_api import register_codex_routes
from src.control.obsidian_notes_api import (
    SafeObsidianNotesService,
    register_obsidian_note_routes,
)
from src.control.project_memory_api import register_project_memory_routes
from src.extraction.bootstrap import build_extraction_pipeline
from src.gateway.bootstrap import build_memory_gateway
from src.obsidian.management import DocumentManager
from src.project_memory.runtime import CodexMemoryLoopServices, build_codex_memory_loop


@dataclass(frozen=True)
class P207ControlRuntime:
    loop: CodexMemoryLoopServices
    notes: SafeObsidianNotesService


class _LazyProxy:
    def __init__(self, getter: Callable[[], Any], attribute: str):
        self._getter = getter
        self._attribute = attribute

    def __getattr__(self, name: str) -> Any:
        service = getattr(self._getter(), self._attribute)
        return getattr(service, name)


def register_p2_07_routes(app: Any, settings: Any, control: Any, *, token: str) -> None:
    """Register the Codex-first local loop without making Control API startup fragile."""

    lock = threading.RLock()
    cached: P207ControlRuntime | None = None

    def runtime() -> P207ControlRuntime:
        nonlocal cached
        if cached is not None:
            return cached
        with lock:
            if cached is not None:
                return cached
            gateway = getattr(control, "memory_gateway", None)
            if gateway is None:
                gateway = build_memory_gateway(settings)
                control.memory_gateway = gateway
            pipeline = getattr(control, "pipeline", None)
            if pipeline is None:
                pipeline = build_extraction_pipeline(
                    settings,
                    runtime_settings=getattr(control, "runtime_settings", None),
                )
                control.pipeline = pipeline
                control.queue = pipeline.queue
            loop = build_codex_memory_loop(
                settings,
                gateway=gateway,
                pipeline=pipeline,
                state_db=getattr(control, "state_db", None),
            )
            notes = SafeObsidianNotesService(
                control.obsidian,
                document_manager=DocumentManager(gateway.lifecycle.layout),
                state_db=getattr(control, "state_db", None),
            )
            cached = P207ControlRuntime(loop=loop, notes=notes)
            control.p2_07_runtime = cached
            return cached

    def token_valid(provided: str) -> bool:
        return not token or hmac.compare_digest(str(provided or ""), token)

    register_codex_routes(
        app,
        _LazyProxy(lambda: runtime().loop, "codex_sessions"),
        _header_authorizer(token),
    )
    register_project_memory_routes(
        app,
        _LazyProxy(lambda: runtime().loop, "project_context"),
        _LazyProxy(lambda: runtime().loop, "memory_review"),
        token_validator=token_valid,
    )
    register_obsidian_note_routes(
        app,
        _LazyProxy(runtime, "notes"),
        token_validator=token_valid,
    )


def _header_authorizer(token: str):
    from fastapi import Header, HTTPException

    def authorize(x_lingji_token: str | None = Header(default=None)) -> None:
        if token and not hmac.compare_digest(str(x_lingji_token or ""), token):
            raise HTTPException(status_code=401, detail="Invalid local control token")

    return authorize
