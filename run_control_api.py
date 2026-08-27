from __future__ import annotations

import secrets
from pathlib import Path

from src.config import settings
from src.control.api import create_control_app
from src.control.auto_review_api import register_auto_review_routes
from src.control.governed_service import GovernedLocalControlService
from src.control.p2_07_api import register_p2_07_routes
from src.control.settings_api import register_settings_governance_routes
from src.automatic_memory.runtime import AutomaticMemoryRuntime
from src.extraction.bootstrap import build_extraction_pipeline
from src.storage import StateDatabase


def load_or_create_token(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        token = path.read_text(encoding="utf-8-sig").strip()
        if token:
            return token
    token = secrets.token_urlsafe(32)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(token + "\n", encoding="utf-8")
    temporary.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return token


def main() -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError("Install requirements-ui.txt before starting the control API") from exc
    if settings.control_api_host not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("Local control API may only bind to loopback addresses")
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    token_path = settings.storage_path / settings.control_api_token_file
    token = load_or_create_token(token_path)
    state_db = StateDatabase(settings.state_db_path)
    pipeline = build_extraction_pipeline(settings)
    service = GovernedLocalControlService(
        settings,
        state_db=state_db,
        pipeline=pipeline,
        queue=pipeline.queue,
    )
    runtime = AutomaticMemoryRuntime(
        state_db=state_db,
        queue=pipeline.queue,
        pipeline=pipeline,
        settings=settings,
        registry=service.automatic_memory_registry,
    )
    service.runtime = runtime
    app = create_control_app(settings, service=service, token=token)
    register_p2_07_routes(app, settings, service, token=token)
    register_auto_review_routes(app, settings, service, token=token)
    register_settings_governance_routes(app, service, token=token)
    shutdown_done = False

    def shutdown_runtime() -> None:
        nonlocal shutdown_done
        if shutdown_done:
            return
        shutdown_done = True
        # Runtime owns the background worker/scheduler.  Close the service
        # only after those components have released their resources.
        runtime.stop()
        service.close()

    app.on_event("shutdown")(shutdown_runtime)
    runtime.start()
    try:
        uvicorn.run(
            app,
            host=settings.control_api_host,
            port=settings.control_api_port,
            log_level="info",
        )
    finally:
        shutdown_runtime()


if __name__ == "__main__":
    main()
