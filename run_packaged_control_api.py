from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Mapping, MutableMapping, Sequence

_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _absolute_owner_root(value: str | Path) -> Path:
    root = Path(value).expanduser().resolve(strict=False)
    if not root.is_absolute():
        raise ValueError("Packaged LingJi data root must be absolute")
    if root == Path(root.anchor):
        raise ValueError("Packaged LingJi data root cannot be a filesystem root")
    return root


def configure_packaged_environment(
    data_root: str | Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8766,
    environ: MutableMapping[str, str] | None = None,
) -> dict[str, str]:
    """Configure explicit owner-local paths before importing ``src.config``.

    The normal repository runtime may use relative defaults. A packaged process
    must never inherit its data authority from the install or current directory,
    so every mutable root is made absolute here.
    """

    normalized_host = str(host or "").strip().lower()
    if normalized_host not in _LOOPBACK_HOSTS:
        raise ValueError("Packaged LingJi control API may only bind to loopback")
    if not 1024 <= int(port) <= 65535:
        raise ValueError("Packaged LingJi control API port is out of range")

    root = _absolute_owner_root(data_root)
    values = {
        "STORAGE_DIR": str(root / "storage"),
        "LOG_DIR": str(root / "logs"),
        "SNAPSHOT_DIR": str(root / "snapshots"),
        "BACKUP_DIR": str(root / "backups"),
        "VAULT_DIR": str(root / "vault"),
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
    target.update(values)
    for directory in ("storage", "logs", "snapshots", "backups", "workspaces"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    return values


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
    return {
        "schema_version": 1,
        "mode": "packaged_sidecar",
        "host": values["CONTROL_API_HOST"],
        "port": int(values["CONTROL_API_PORT"]),
        "data_root": str(root),
        "storage_dir": values["STORAGE_DIR"],
        "log_dir": values["LOG_DIR"],
        "workspace_root": values["WORKSPACE_ROOT"],
        "token_file": str(Path(values["STORAGE_DIR"]) / "control_api_token"),
        "owner_data_outside_install_dir": True,
        "automatic_model_download": False,
        "automatic_qdrant_rebuild": False,
    }


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
    from run_control_api import main as run_control_api

    run_control_api()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
