from __future__ import annotations

import argparse
import atexit
import json
import os
import secrets
import signal
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence

_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
_RUNTIME_SCHEMA_VERSION = 1


def _absolute_owner_root(value: str | Path) -> Path:
    root = Path(value).expanduser().resolve(strict=False)
    if not root.is_absolute():
        raise ValueError("Packaged LingJi data root must be absolute")
    if root == Path(root.anchor):
        raise ValueError("Packaged LingJi data root cannot be a filesystem root")
    return root


def _runtime_dir(root: Path) -> Path:
    return root / "runtime"


def runtime_state_path(root: str | Path) -> Path:
    return _runtime_dir(_absolute_owner_root(root)) / "sidecar-state.json"


def runtime_stop_request_path(root: str | Path) -> Path:
    return _runtime_dir(_absolute_owner_root(root)) / "sidecar-stop-request.json"


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(payload), ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def configure_packaged_environment(
    data_root: str | Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8766,
    environ: MutableMapping[str, str] | None = None,
) -> dict[str, str]:
    """Configure explicit owner-local paths before importing ``src.config``.

    Mutable runtime and derived stores must never inherit their location from the
    installation/current directory. Vault configuration is different: an owner
    may explicitly keep the Obsidian Vault elsewhere, so an existing VAULT_DIR
    is preserved and only receives an owner-local default when absent.
    """

    normalized_host = str(host or "").strip().lower()
    if normalized_host not in _LOOPBACK_HOSTS:
        raise ValueError("Packaged LingJi control API may only bind to loopback")
    if not 1024 <= int(port) <= 65535:
        raise ValueError("Packaged LingJi control API port is out of range")

    root = _absolute_owner_root(data_root)
    required_values = {
        "STORAGE_DIR": str(root / "storage"),
        "LOG_DIR": str(root / "logs"),
        "SNAPSHOT_DIR": str(root / "snapshots"),
        "BACKUP_DIR": str(root / "backups"),
        "WORKSPACE_ROOT": str(root / "workspaces"),
        "LINGJI_WORKSPACE_ROOT": str(root / "workspaces"),
        "PRODUCTION_STORAGE_DIR": str(root / "workspaces" / "production"),
        "ACCEPTANCE_STORAGE_DIR": str(root / "workspaces" / "acceptance"),
        "CONTROL_API_HOST": normalized_host,
        "CONTROL_API_PORT": str(int(port)),
        "LINGJI_PACKAGED_RUNTIME": "1",
        "LINGJI_OWNER_DATA_ROOT": str(root),
    }
    target = os.environ if environ is None else environ
    target.update(required_values)
    target.setdefault("VAULT_DIR", str(root / "vault"))

    for directory in (
        "storage",
        "logs",
        "runtime",
        "snapshots",
        "backups",
        "workspaces",
    ):
        (root / directory).mkdir(parents=True, exist_ok=True)

    return {
        **required_values,
        "VAULT_DIR": target["VAULT_DIR"],
    }


def packaged_runtime_contract(
    data_root: str | Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8766,
    environ: Mapping[str, str] | None = None,
) -> dict[str, object]:
    scratch: dict[str, str] = dict(environ or {})
    values = configure_packaged_environment(
        data_root,
        host=host,
        port=port,
        environ=scratch,
    )
    root = Path(values["LINGJI_OWNER_DATA_ROOT"])
    default_vault = root / "vault"
    configured_vault = Path(values["VAULT_DIR"]).expanduser().resolve(strict=False)
    return {
        "schema_version": 1,
        "mode": "packaged_sidecar",
        "host": values["CONTROL_API_HOST"],
        "port": int(values["CONTROL_API_PORT"]),
        "data_root": str(root),
        "storage_dir": values["STORAGE_DIR"],
        "log_dir": values["LOG_DIR"],
        "runtime_dir": str(_runtime_dir(root)),
        "workspace_root": values["WORKSPACE_ROOT"],
        "token_file": str(Path(values["STORAGE_DIR"]) / "control_api_token"),
        "state_file": str(runtime_state_path(root)),
        "stop_request_file": str(runtime_stop_request_path(root)),
        "vault_dir": str(configured_vault),
        "vault_uses_owner_local_default": configured_vault == default_vault,
        "owner_data_outside_install_dir": True,
        "automatic_model_download": False,
        "automatic_qdrant_rebuild": False,
    }


def install_runtime_lifecycle(
    data_root: str | Path,
    *,
    host: str,
    port: int,
    poll_seconds: float = 0.25,
) -> dict[str, Any]:
    """Write the packaged-process identity and monitor authenticated stop requests."""

    root = _absolute_owner_root(data_root)
    state_path = runtime_state_path(root)
    stop_path = runtime_stop_request_path(root)
    instance_id = secrets.token_urlsafe(24)
    state = {
        "schema_version": _RUNTIME_SCHEMA_VERSION,
        "mode": "packaged_sidecar",
        "pid": os.getpid(),
        "instance_id": instance_id,
        "started_at_ms": int(time.time() * 1000),
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": host,
        "port": int(port),
    }
    try:
        stop_path.unlink(missing_ok=True)
    except OSError:
        pass
    _write_json_atomic(state_path, state)

    def cleanup() -> None:
        existing = _read_json(state_path)
        if existing and existing.get("instance_id") == instance_id:
            try:
                state_path.unlink(missing_ok=True)
            except OSError:
                pass

    def monitor() -> None:
        while True:
            request = _read_json(stop_path)
            if request and request.get("instance_id") == instance_id:
                try:
                    stop_path.unlink(missing_ok=True)
                except OSError:
                    pass
                cleanup()
                os.kill(os.getpid(), signal.SIGTERM)
                return
            time.sleep(max(0.05, float(poll_seconds)))

    atexit.register(cleanup)
    thread = threading.Thread(
        target=monitor,
        name="lingji-sidecar-stop-monitor",
        daemon=True,
    )
    thread.start()
    return state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LingJi packaged local control runtime")
    parser.add_argument("--data-root", required=True, help="Absolute owner-local LingJi data root")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Print the packaged runtime contract and exit without starting 8766",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    contract = packaged_runtime_contract(args.data_root, host=args.host, port=args.port)
    if args.check_config:
        print(json.dumps(contract, ensure_ascii=False, sort_keys=True))
        return 0

    configure_packaged_environment(args.data_root, host=args.host, port=args.port)
    install_runtime_lifecycle(args.data_root, host=args.host, port=args.port)
    from run_control_api import main as run_control_api

    run_control_api()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
