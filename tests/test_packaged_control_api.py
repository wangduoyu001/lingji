from __future__ import annotations

import json
import os
import shutil
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
