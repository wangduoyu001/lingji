from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from run_packaged_control_api import (
    _ensure_standard_streams,
    configure_packaged_environment,
    install_runtime_lifecycle,
    main,
    packaged_runtime_contract,
    runtime_state_path,
    runtime_stop_request_path,
)


@pytest.fixture
def runtime_tmp_path(tmp_path: Path):
    """Use the repository drive on Windows so C-drive rejection remains real."""

    if os.name != "nt":
        yield tmp_path
        return

    parent = Path.cwd() / "output" / "test-runtime"
    parent.mkdir(parents=True, exist_ok=True)
    root = parent / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=False)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_packaged_environment_uses_absolute_workspace_paths(runtime_tmp_path: Path):
    environ: dict[str, str] = {}

    values = configure_packaged_environment(
        runtime_tmp_path / "LingJi" / "acceptance",
        workspace="acceptance",
        environ=environ,
    )

    root = (runtime_tmp_path / "LingJi" / "acceptance").resolve()
    base = root.parent
    assert values["LINGJI_OWNER_DATA_ROOT"] == str(root)
    assert values["LINGJI_WORKSPACE"] == "acceptance"
    assert values["WORKSPACE_NAME"] == "acceptance"
    assert values["STORAGE_DIR"] == str(root / "storage")
    assert values["LOG_DIR"] == str(root / "logs")
    assert values["WORKSPACE_ROOT"] == str(base)
    assert values["LINGJI_WORKSPACE_ROOT"] == str(base)
    assert values["PRODUCTION_STORAGE_DIR"] == str(base / "production" / "storage")
    assert values["ACCEPTANCE_STORAGE_DIR"] == str(root / "storage")
    assert values["CONTROL_API_HOST"] == "127.0.0.1"
    assert values["CONTROL_API_PORT"] == "8766"
    assert all(
        Path(values[key]).is_absolute()
        for key in (
            "STORAGE_DIR",
            "LOG_DIR",
            "SNAPSHOT_DIR",
            "BACKUP_DIR",
            "VAULT_DIR",
            "WORKSPACE_ROOT",
        )
    )
    assert (root / "storage").is_dir()
    assert (root / "logs").is_dir()
    assert (root / "runtime").is_dir()
    assert (root / "raw").is_dir()
    assert (root / "qdrant").is_dir()


def test_packaged_environment_keeps_production_and_acceptance_separate(runtime_tmp_path: Path):
    base = runtime_tmp_path / "LingJiData"
    production = configure_packaged_environment(
        base / "production",
        workspace="production",
        environ={},
    )
    acceptance = configure_packaged_environment(
        base / "acceptance",
        workspace="acceptance",
        environ={},
    )

    assert production["STORAGE_DIR"] != acceptance["STORAGE_DIR"]
    assert production["PRODUCTION_STORAGE_DIR"] == production["STORAGE_DIR"]
    assert acceptance["ACCEPTANCE_STORAGE_DIR"] == acceptance["STORAGE_DIR"]
    assert Path(production["STORAGE_DIR"]).is_relative_to(base / "production")
    assert Path(acceptance["STORAGE_DIR"]).is_relative_to(base / "acceptance")


def test_packaged_environment_preserves_explicit_owner_vault(runtime_tmp_path: Path):
    explicit_vault = (runtime_tmp_path / "My Obsidian Vault").resolve()
    environ = {"VAULT_DIR": str(explicit_vault)}

    values = configure_packaged_environment(
        runtime_tmp_path / "LingJi" / "production",
        workspace="production",
        environ=environ,
    )

    assert values["VAULT_DIR"] == str(explicit_vault)
    assert environ["VAULT_DIR"] == str(explicit_vault)
    contract = packaged_runtime_contract(
        runtime_tmp_path / "LingJi" / "production",
        workspace="production",
        environ=environ,
    )
    assert contract["vault_dir"] == str(explicit_vault)
    assert contract["vault_uses_owner_local_default"] is False


def test_packaged_environment_rejects_non_loopback_host(runtime_tmp_path: Path):
    with pytest.raises(ValueError, match="loopback"):
        configure_packaged_environment(runtime_tmp_path / "LingJi", host="0.0.0.0", environ={})


def test_packaged_environment_rejects_filesystem_root():
    with pytest.raises(ValueError, match="filesystem root"):
        configure_packaged_environment(Path(Path.cwd().anchor), environ={})


def test_packaged_environment_rejects_windows_system_drive_without_touching_it():
    with pytest.raises(ValueError, match="C: drive"):
        configure_packaged_environment(r"C:\LingJiData\acceptance", workspace="acceptance", environ={})


def test_packaged_environment_rejects_unknown_workspace(runtime_tmp_path: Path):
    with pytest.raises(ValueError, match="production or acceptance"):
        configure_packaged_environment(runtime_tmp_path / "LingJi", workspace="shared", environ={})


def test_packaged_contract_is_explicit_about_safety_boundaries(runtime_tmp_path: Path):
    contract = packaged_runtime_contract(
        runtime_tmp_path / "LingJi" / "acceptance",
        workspace="acceptance",
    )

    assert contract["mode"] == "packaged_sidecar"
    assert contract["workspace"] == "acceptance"
    assert contract["owner_data_outside_install_dir"] is True
    assert contract["system_drive_runtime_data_allowed"] is False
    assert contract["vault_uses_owner_local_default"] is True
    assert contract["automatic_model_download"] is False
    assert contract["automatic_qdrant_rebuild"] is False
    assert str(contract["token_file"]).endswith("storage/control_api_token") or str(
        contract["token_file"]
    ).endswith(r"storage\control_api_token")
    assert str(contract["state_file"]).endswith("runtime/sidecar-state.json") or str(
        contract["state_file"]
    ).endswith(r"runtime\sidecar-state.json")


def test_runtime_lifecycle_writes_identity_and_accepts_matching_stop_request(
    runtime_tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = runtime_tmp_path / "LingJi" / "acceptance"
    killed: list[tuple[int, int]] = []
    monkeypatch.setattr("run_packaged_control_api.os.kill", lambda pid, sig: killed.append((pid, sig)))

    state = install_runtime_lifecycle(
        root,
        host="127.0.0.1",
        port=8766,
        workspace="acceptance",
        poll_seconds=0.01,
    )

    persisted = json.loads(runtime_state_path(root).read_text(encoding="utf-8"))
    assert persisted["mode"] == "packaged_sidecar"
    assert persisted["workspace"] == "acceptance"
    assert persisted["pid"] == state["pid"]
    assert persisted["instance_id"] == state["instance_id"]

    runtime_stop_request_path(root).write_text(
        json.dumps({"instance_id": state["instance_id"]}),
        encoding="utf-8",
    )
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline and not killed:
        time.sleep(0.01)

    assert killed
    assert not runtime_state_path(root).exists()
    assert not runtime_stop_request_path(root).exists()


def test_runtime_lifecycle_ignores_mismatched_stop_request(
    runtime_tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = runtime_tmp_path / "LingJi" / "production"
    killed: list[tuple[int, int]] = []
    monkeypatch.setattr("run_packaged_control_api.os.kill", lambda pid, sig: killed.append((pid, sig)))

    state = install_runtime_lifecycle(
        root,
        host="127.0.0.1",
        port=8766,
        workspace="production",
        poll_seconds=0.01,
    )
    runtime_stop_request_path(root).write_text(
        json.dumps({"instance_id": "different-instance"}),
        encoding="utf-8",
    )
    time.sleep(0.08)

    assert killed == []
    assert runtime_state_path(root).exists()
    runtime_state_path(root).unlink(missing_ok=True)
    runtime_stop_request_path(root).unlink(missing_ok=True)
    assert state["instance_id"]


def test_check_config_prints_json_without_starting_server(runtime_tmp_path: Path, capsys):
    exit_code = main([
        "--data-root",
        str(runtime_tmp_path / "LingJi" / "acceptance"),
        "--workspace",
        "acceptance",
        "--check-config",
    ])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["host"] == "127.0.0.1"
    assert payload["port"] == 8766
    assert payload["mode"] == "packaged_sidecar"
    assert payload["workspace"] == "acceptance"


def test_check_config_writes_json_for_windowed_executable(runtime_tmp_path: Path):
    output_path = runtime_tmp_path / "contract.json"

    exit_code = main([
        "--data-root",
        str(runtime_tmp_path / "LingJi" / "production"),
        "--workspace",
        "production",
        "--check-config",
        "--check-config-output",
        str(output_path),
    ])

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["host"] == "127.0.0.1"
    assert payload["port"] == 8766
    assert payload["mode"] == "packaged_sidecar"
    assert payload["workspace"] == "production"


def test_windowed_runtime_receives_devnull_standard_streams():
    streams = SimpleNamespace(stdout=None, stderr=None)

    _ensure_standard_streams(streams)

    assert streams.stdout is not None
    assert streams.stderr is not None
    streams.stdout.close()
    streams.stderr.close()


def test_control_main_composes_runtime_and_shutdown_order(
    runtime_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import run_control_api
    from src.config import Settings

    settings = Settings(
        storage_dir=str(runtime_tmp_path / "storage"),
        vault_dir=str(runtime_tmp_path / "vault"),
        snapshot_dir=str(runtime_tmp_path / "snapshot"),
        log_dir=str(runtime_tmp_path / "logs"),
    )
    events: list[str] = []

    class App:
        def on_event(self, event: str):
            assert event == "shutdown"

            def register(callback):
                self.shutdown = callback
                return callback

            return register

    app = App()
    pipeline = SimpleNamespace(queue=SimpleNamespace(path=settings.state_db_path))

    class Service:
        automatic_memory_registry = object()

        def __init__(self, *_args, **_kwargs):
            pass

        def close(self):
            events.append("service.close")

    class Runtime:
        def __init__(self, *_args, **_kwargs):
            pass

        def start(self):
            events.append("runtime.start")

        def stop(self):
            events.append("runtime.stop")

    monkeypatch.setattr(run_control_api, "settings", settings)
    monkeypatch.setattr(run_control_api, "GovernedLocalControlService", Service)
    monkeypatch.setattr(run_control_api, "AutomaticMemoryRuntime", Runtime)
    monkeypatch.setattr(run_control_api, "build_extraction_pipeline", lambda *_args: pipeline)
    monkeypatch.setattr(run_control_api, "create_control_app", lambda *_args, **_kwargs: app)
    monkeypatch.setattr(run_control_api, "register_p2_07_routes", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(run_control_api, "register_auto_review_routes", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(run_control_api, "register_settings_governance_routes", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("uvicorn.run", lambda *_args, **_kwargs: None)

    run_control_api.main()

    assert events == ["runtime.start", "runtime.stop", "service.close"]


def test_real_control_main_composes_and_cleans_real_runtime(
    runtime_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Exercise packaged composition with only uvicorn's network boundary replaced."""
    import run_control_api
    from src.config import Settings

    root = runtime_tmp_path / "real-runtime"
    settings = Settings(
        storage_dir=str(root / "storage"),
        vault_dir=str(root / "vault"),
        snapshot_dir=str(root / "snapshot"),
        log_dir=str(root / "logs"),
        scheduler_poll_seconds=0.02,
        extraction_poll_seconds=0.2,
    )
    uvicorn_calls: list[dict[str, object]] = []

    def fake_uvicorn(app, **kwargs):
        uvicorn_calls.append({"app": app, **kwargs})

    monkeypatch.setattr(run_control_api, "settings", settings)
    monkeypatch.setattr("uvicorn.run", fake_uvicorn)

    run_control_api.main()

    assert len(uvicorn_calls) == 1
    assert uvicorn_calls[0]["host"] == "127.0.0.1"
    assert uvicorn_calls[0]["port"] == 8766
    storage_files = {path.name for path in (root / "storage").glob("*.db")}
    assert storage_files == {"lingji_state.db", "lingji_memory.db"}
    assert not list(root.rglob("automatic_memory.db"))


def test_real_control_main_cleans_runtime_when_scheduler_start_fails(
    runtime_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import run_control_api
    from src.automatic_memory.scheduler import AutomaticMemoryScheduler
    from src.config import Settings

    root = runtime_tmp_path / "real-start-failure"
    settings = Settings(
        storage_dir=str(root / "storage"),
        vault_dir=str(root / "vault"),
        snapshot_dir=str(root / "snapshot"),
        log_dir=str(root / "logs"),
        scheduler_poll_seconds=0.02,
        extraction_poll_seconds=0.2,
    )
    original_start = AutomaticMemoryScheduler.start

    def start_then_fail(scheduler):
        original_start(scheduler)
        raise RuntimeError("injected scheduler startup failure")

    monkeypatch.setattr(run_control_api, "settings", settings)
    monkeypatch.setattr(AutomaticMemoryScheduler, "start", start_then_fail)
    monkeypatch.setattr("uvicorn.run", lambda *_args, **_kwargs: None)

    with pytest.raises(RuntimeError, match="injected scheduler startup failure"):
        run_control_api.main()

    names = {thread.name for thread in threading.enumerate()}
    assert "lingji-scheduler" not in names
    assert "lingji-extraction-worker" not in names


def _run_packaged_wrapper_subprocess(root: Path, *, fail_start: bool = False):
    script = r'''
import json
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
fail_start = sys.argv[2] == "fail"
import run_control_api
from src.config import Settings
from src.automatic_memory.models import AuthorizationScope
from src.automatic_memory.source_registry import SourceRegistry
from src.storage import StateDatabase

settings = Settings(
    storage_dir=str(root / "storage"),
    vault_dir=str(root / "vault"),
    snapshot_dir=str(root / "snapshots"),
    log_dir=str(root / "logs"),
    scheduler_poll_seconds=0.02,
    extraction_poll_seconds=0.2,
)
run_control_api.settings = settings
state = StateDatabase(settings.state_db_path)
registry = SourceRegistry(state)
registry.register(
    AuthorizationScope(
        "wrapper-grant", ("generic_ai_history",), (str(root),),
        __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        None, True,
    ),
    "generic_ai_history", str(root),
)
if fail_start:
    from src.automatic_memory.scheduler import AutomaticMemoryScheduler
    original_start = AutomaticMemoryScheduler.start
    def start_then_fail(scheduler):
        original_start(scheduler)
        raise RuntimeError("wrapper startup failure")
    AutomaticMemoryScheduler.start = start_then_fail

import uvicorn
def fake_uvicorn(app, **kwargs):
    import gc
    from src.automatic_memory.runtime import AutomaticMemoryRuntime
    runtime = next(
        value for value in gc.get_objects()
        if isinstance(value, AutomaticMemoryRuntime)
    )
    owned = [
        thread.name for thread in __import__("threading").enumerate()
        if thread.name.startswith(("lingji-",))
    ]
    print("WRAPPER_UVICORN " + json.dumps({
        "host": kwargs["host"], "port": kwargs["port"],
        "db_path": str(state.path),
        "queue_path": str(runtime.queue.path),
        "pipeline_queue_path": str(runtime.pipeline.queue.path),
        "registry_db_path": str(runtime.registry.state_db.path),
        "scheduler_db_path": str(runtime.scheduler.state_db.path),
        "jobs": len(state.list_scheduler_jobs()),
        "owned_threads": sorted(owned),
    }))
uvicorn.run = fake_uvicorn
try:
    import run_packaged_control_api
    run_packaged_control_api.main([
        "--data-root", str(root), "--workspace", "acceptance",
    ])
except RuntimeError as exc:
    if not fail_start or "wrapper startup failure" not in str(exc):
        raise
    owned = [
        thread.name for thread in __import__("threading").enumerate()
        if thread.name.startswith(("lingji-scheduler", "lingji-extraction-worker", "lingji-memory-watch"))
    ]
    print("WRAPPER_FAILURE " + json.dumps({"message": str(exc), "owned_threads": sorted(owned)}))
'''
    return subprocess.run(
        [sys.executable, "-c", script, str(root), "fail" if fail_start else "ok"],
        cwd=str(Path(__file__).parents[1]),
        capture_output=True,
        text=True,
        check=False,
    )


def test_packaged_wrapper_main_runs_real_composition_and_cleans_subprocess(
    runtime_tmp_path: Path,
):
    root = runtime_tmp_path / "wrapper-runtime"
    result = _run_packaged_wrapper_subprocess(root)
    assert result.returncode == 0, result.stderr
    marker = next(line for line in result.stdout.splitlines() if line.startswith("WRAPPER_UVICORN "))
    payload = json.loads(marker.removeprefix("WRAPPER_UVICORN "))
    assert payload["port"] == 8766
    assert payload["jobs"] == 2
    assert len({
        payload["db_path"], payload["queue_path"],
        payload["pipeline_queue_path"], payload["registry_db_path"],
        payload["scheduler_db_path"],
    }) == 1
    assert any(name == "lingji-scheduler" for name in payload["owned_threads"])
    assert any(name == "lingji-extraction-worker" for name in payload["owned_threads"])
    db_files = {path.name for path in (root / "storage").glob("*.db")}
    assert db_files == {"lingji_state.db", "lingji_memory.db"}
    assert not (root / "runtime" / "sidecar-state.json").exists()
    assert not (root / "runtime" / "sidecar-stop-request.json").exists()


def test_packaged_wrapper_main_failure_cleans_real_subprocess(
    runtime_tmp_path: Path,
):
    root = runtime_tmp_path / "wrapper-start-failure"
    result = _run_packaged_wrapper_subprocess(root, fail_start=True)
    assert result.returncode == 0, result.stderr
    marker = next(line for line in result.stdout.splitlines() if line.startswith("WRAPPER_FAILURE "))
    payload = json.loads(marker.removeprefix("WRAPPER_FAILURE "))
    assert "wrapper startup failure" in payload["message"]
    assert payload["owned_threads"] == []
    assert not (root / "runtime" / "sidecar-state.json").exists()
    assert not (root / "runtime" / "sidecar-stop-request.json").exists()
