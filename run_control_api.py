from __future__ import annotations

import os
import secrets
import threading
from pathlib import Path

from src.autopilot import AutopilotEngine
from src.config import settings
from src.control.api import create_control_app
from src.control.autopilot_api import register_autopilot_routes
from src.control.auto_review_api import register_auto_review_routes
from src.control.governed_service import GovernedLocalControlService
from src.control.p2_07_api import register_p2_07_routes
from src.control.settings_api import register_settings_governance_routes
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


def _run_server(app, shutdown_event: threading.Event | None = None) -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError("Install requirements-ui.txt before starting the control API") from exc

    if shutdown_event is None:
        uvicorn.run(
            app,
            host=settings.control_api_host,
            port=settings.control_api_port,
            log_level="info",
        )
        return

    config = uvicorn.Config(
        app,
        host=settings.control_api_host,
        port=settings.control_api_port,
        log_level="info",
    )
    server = uvicorn.Server(config)

    def request_shutdown() -> None:
        shutdown_event.wait()
        server.should_exit = True

    watcher = threading.Thread(
        target=request_shutdown,
        name="lingji-control-shutdown-bridge",
        daemon=True,
    )
    watcher.start()
    server.run()


def _packaged_capture_processor(service, state_db):
    if os.environ.get("LINGJI_PACKAGED_RUNTIME") != "1":
        return None
    from src.control.capture_processing import PackagedCaptureProcessingRuntime

    processor = PackagedCaptureProcessingRuntime(
        settings,
        state_db=state_db,
        runtime_settings=service.runtime_settings,
    )
    # Capture API reuses these exact queue/pipeline objects. The packaged control
    # process therefore owns queue consumption but never opens Qdrant.
    service.pipeline = processor.pipeline
    service.queue = processor.pipeline.queue
    service.capture_processing_runtime = processor
    return processor


def main(shutdown_event: threading.Event | None = None) -> None:
    if settings.control_api_host not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("Local control API may only bind to loopback addresses")
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    token_path = settings.storage_path / settings.control_api_token_file
    token = load_or_create_token(token_path)
    state_db = StateDatabase(settings.state_db_path)
    service = GovernedLocalControlService(settings, state_db=state_db)
    capture_processor = _packaged_capture_processor(service, state_db)
    autopilot = AutopilotEngine(
        settings,
        state_db=state_db,
        queue=service.queue,
        memory_statistics=service.memory_statistics,
        auth_status_provider=service.auth_statuses,
    )
    app = create_control_app(settings, service=service, token=token)
    register_autopilot_routes(app, autopilot, token=token)
    register_p2_07_routes(app, settings, service, token=token)
    register_auto_review_routes(app, settings, service, token=token)
    register_settings_governance_routes(app, service, token=token)
    if capture_processor is not None:
        capture_processor.start()
    autopilot.start()
    try:
        _run_server(app, shutdown_event=shutdown_event)
    finally:
        autopilot.stop()
        if capture_processor is not None:
            capture_processor.stop()
        service.close()


if __name__ == "__main__":
    main()
