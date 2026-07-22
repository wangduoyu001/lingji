from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from run_packaged_control_api import (
    configure_packaged_environment,
    install_runtime_lifecycle,
    main,
    packaged_runtime_contract,
    runtime_state_path,
    runtime_stop_request_path,
)


def test_packaged_environment_uses_absolute_owner_local_paths(tmp_path: Path):
    environ: dict[str, str] = {}

    values = configure_packaged_environment(tmp_path / "LingJi", environ=environ)

    root = (tmp_path / "LingJi").resolve()
    assert values["LINGJI_OWNER_DATA_ROOT"] == str(root)
    assert values["STORAGE_DIR"] == str(root / "storage")
    assert values["LOG_DIR"] == str(root / "logs")
    assert values["WORKSPACE_ROOT"] == str(root / "workspaces")
    assert values["LINGJI_WORKSPACE_ROOT"] == str(root / "workspaces")
    assert values["CONTROL_API_HOST"] == "127.0.0.1"
    assert values["CONTROL_API_PORT"] == "8766"
    assert all(Path(values[key]).is_absolute() for key in (
        "STORAGE_DIR",
        "LOG_DIR",
        "SNAPSHOT_DIR",
        "BACKUP_DIR",
        "VAULT_DIR",
        "WORKSPACE_ROOT",
    ))
    assert (root / "storage").is_dir()
    assert (root / "logs").is_dir()
    assert (root / "runtime").is_dir()


def test_packaged_environment_preserves_explicit_owner_vault(tmp_path: Path):
    explicit_vault = (tmp_path / "My Obsidian Vault").resolve()
    environ = {"VAULT_DIR": str(explicit_vault)}

    values = configure_packaged_environment(tmp_path / "LingJi", environ=environ)

    assert values["VAULT_DIR"] == str(explicit_vault)
    assert environ["VAULT_DIR"] == str(explicit_vault)
    contract = packaged_runtime_contract(tmp_path / "LingJi", environ=environ)
    assert contract["vault_dir"] == str(explicit_vault)
    assert contract["vault_uses_owner_local_default"] is False


def test_packaged_environment_rejects_non_loopback_host(tmp_path: Path):
    with pytest.raises(ValueError, match="loopback"):
        configure_packaged_environment(tmp_path / "LingJi", host="0.0.0.0", environ={})


def test_packaged_environment_rejects_filesystem_root():
    with pytest.raises(ValueError, match="filesystem root"):
        configure_packaged_environment(Path(Path.cwd().anchor), environ={})


def test_packaged_contract_is_explicit_about_safety_boundaries(tmp_path: Path):
    contract = packaged_runtime_contract(tmp_path / "LingJi")

    assert contract["mode"] == "packaged_sidecar"
    assert contract["owner_data_outside_install_dir"] is True
    assert contract["vault_uses_owner_local_default"] is True
    assert contract["automatic_model_download"] is False
    assert contract["automatic_qdrant_rebuild"] is False
    assert str(contract["token_file"]).endswith("storage/control_api_token") or str(
        contract["token_file"]
    ).endswith("storage\\control_api_token")
    assert str(contract["state_file"]).endswith("runtime/sidecar-state.json") or str(
        contract["state_file"]
    ).endswith("runtime\\sidecar-state.json")


def test_runtime_lifecycle_writes_identity_and_accepts_matching_stop_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path / "LingJi"
    killed: list[tuple[int, int]] = []
    monkeypatch.setattr("run_packaged_control_api.os.kill", lambda pid, sig: killed.append((pid, sig)))

    state = install_runtime_lifecycle(
        root,
        host="127.0.0.1",
        port=8766,
        poll_seconds=0.01,
    )

    persisted = json.loads(runtime_state_path(root).read_text(encoding="utf-8"))
    assert persisted["mode"] == "packaged_sidecar"
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
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path / "LingJi"
    killed: list[tuple[int, int]] = []
    monkeypatch.setattr("run_packaged_control_api.os.kill", lambda pid, sig: killed.append((pid, sig)))

    state = install_runtime_lifecycle(
        root,
        host="127.0.0.1",
        port=8766,
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


def test_check_config_prints_json_without_starting_server(tmp_path: Path, capsys):
    exit_code = main(["--data-root", str(tmp_path / "LingJi"), "--check-config"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["host"] == "127.0.0.1"
    assert payload["port"] == 8766
    assert payload["mode"] == "packaged_sidecar"
