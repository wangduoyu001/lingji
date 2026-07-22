from __future__ import annotations

import json
from pathlib import Path

import pytest

from run_packaged_control_api import (
    configure_packaged_environment,
    main,
    packaged_runtime_contract,
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
    assert contract["automatic_model_download"] is False
    assert contract["automatic_qdrant_rebuild"] is False
    assert str(contract["token_file"]).endswith("storage/control_api_token") or str(
        contract["token_file"]
    ).endswith("storage\\control_api_token")


def test_check_config_prints_json_without_starting_server(tmp_path: Path, capsys):
    exit_code = main(["--data-root", str(tmp_path / "LingJi"), "--check-config"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["host"] == "127.0.0.1"
    assert payload["port"] == 8766
    assert payload["mode"] == "packaged_sidecar"
