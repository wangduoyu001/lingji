from __future__ import annotations

import argparse
import atexit
import json
import os
import re
import secrets
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence

_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
_WORKSPACES = {"production", "acceptance"}
_SERVICES = {"control", "mcp"}
_WINDOWS_SYSTEM_DRIVE = re.compile(r"^c:[\\/]", re.IGNORECASE)
_RUNTIME_SCHEMA_VERSION = 1
_MCP_HOST = "127.0.0.1"
_MCP_PORT = 8767


def _absolute_owner_root(value: str | Path) -> Path:
    text = str(value).strip()
    if _WINDOWS_SYSTEM_DRIVE.match(text):
        raise ValueError("Packaged LingJi data root may not use the Windows C: drive")
    root = Path(text).expanduser().resolve(strict=False)
    if not root.is_absolute():
        raise ValueError("Packaged LingJi data root must be absolute")
    if root == Path(root.anchor):
        raise ValueError("Packaged LingJi data root cannot be a filesystem root")
    return root


def _workspace_name(value: str | None) -> str:
    workspace = str(value or "production").strip().lower()
    if workspace not in _WORKSPACES:
        raise ValueError("Packaged LingJi workspace must be production or acceptance")
    return workspace


def _runtime_dir(root: Path) -> Path:
    return root / "runtime"


def runtime_state_path(root: str | Path) -> Path:
    return _runtime_dir(_absolute_owner_root(root)) / "sidecar-state.json"


def runtime_stop_request_path(root: str | Path) -> Path:
    return _runtime_dir(_absolute_owner_root(root)) / "sidecar-stop-request.json"


def mcp_state_path(root: str | Path) -> Path:
    return _runtime_dir(_absolute_owner_root(root)) / "mcp-state.json"


def mcp_token_path(root: str | Path) -> Path:
    return _absolute_owner_root(root) / "storage" / "mcp_http_token"


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


def _write_text_atomic(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
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


def _ensure_standard_streams(streams: Any = sys) -> None:
    """Give Uvicorn writable streams when a windowed executable has none."""

    for name in ("stdout", "stderr"):
        if getattr(streams, name, None) is None:
            setattr(streams, name, open(os.devnull, "w", encoding="utf-8"))


def configure_packaged_environment(
    data_root: str | Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8766,
    workspace: str | None = None,
    environ: MutableMapping[str, str] | None = None,
) -> dict[str, str]:
    """Configure explicit paths before importing ``src.config``."""

    normalized_host = str(host or "").strip().lower()
    if normalized_host not in _LOOPBACK_HOSTS:
        raise ValueError("Packaged LingJi control API may only bind to loopback")
    if not 1024 <= int(port) <= 65535:
        raise ValueError("Packaged LingJi control API port is out of range")

    target = os.environ if environ is None else environ
    workspace_name = _workspace_name(
        workspace or target.get("LINGJI_WORKSPACE") or target.get("WORKSPACE_NAME")
    )
    root = _absolute_owner_root(data_root)
    base_root = root.parent
    production_root = root if workspace_name == "production" else base_root / "production"
    acceptance_root = root if workspace_name == "acceptance" else base_root / "acceptance"

    required_values = {
        "STORAGE_DIR": str(root / "storage"),
        "LOG_DIR": str(root / "logs"),
        "SNAPSHOT_DIR": str(root / "snapshots"),
        "BACKUP_DIR": str(root / "backups"),
        "WORKSPACE_NAME": workspace_name,
        "WORKSPACE_ROOT": str(base_root),
        "LINGJI_WORKSPACE": workspace_name,
        "LINGJI_WORKSPACE_ROOT": str(base_root),
        "PRODUCTION_STORAGE_DIR": str(production_root / "storage"),
        "PRODUCTION_RAW_DIR": str(production_root / "raw"),
        "PRODUCTION_QDRANT_PATH": str(production_root / "qdrant"),
        "ACCEPTANCE_STORAGE_DIR": str(acceptance_root / "storage"),
        "ACCEPTANCE_RAW_DIR": str(acceptance_root / "raw"),
        "ACCEPTANCE_QDRANT_PATH": str(acceptance_root / "qdrant"),
        "CONTROL_API_HOST": normalized_host,
        "CONTROL_API_PORT": str(int(port)),
        "MCP_HOST": _MCP_HOST,
        "MCP_PORT": str(_MCP_PORT),
        "MCP_TRANSPORT": "streamable-http",
        "LINGJI_PACKAGED_RUNTIME": "1",
        "LINGJI_OWNER_DATA_ROOT": str(root),
    }
    target.update(required_values)
    target.setdefault("VAULT_DIR", str(root / "vault"))

    for directory in (
        "storage",
        "logs",
        "runtime",
        "snapshots",
        "backups",
        "raw",
        "qdrant",
    ):
        (root / directory).mkdir(parents=True, exist_ok=True)

    return {**required_values, "VAULT_DIR": target["VAULT_DIR"]}


def packaged_runtime_contract(
    data_root: str | Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8766,
    workspace: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, object]:
    scratch: dict[str, str] = dict(environ or {})
    values = configure_packaged_environment(
        data_root,
        host=host,
        port=port,
        workspace=workspace,
        environ=scratch,
    )
    root = Path(values["LINGJI_OWNER_DATA_ROOT"])
    default_vault = root / "vault"
    configured_vault = Path(values["VAULT_DIR"]).expanduser().resolve(strict=False)
    return {
        "schema_version": 3,
        "mode": "packaged_sidecar",
        "workspace": values["LINGJI_WORKSPACE"],
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
        "system_drive_runtime_data_allowed": False,
        "automatic_model_download": False,
        "automatic_qdrant_rebuild": False,
        "mcp": {
            "managed": True,
            "host": _MCP_HOST,
            "port": _MCP_PORT,
            "url": f"http://{_MCP_HOST}:{_MCP_PORT}/mcp",
            "transport": "streamable-http",
            "authentication": "bearer_token",
            "token_file": str(mcp_token_path(root)),
            "state_file": str(mcp_state_path(root)),
            "loopback_only": True,
            "automatic_core_memory_write": False,
        },
    }


def install_runtime_lifecycle(
    data_root: str | Path,
    *,
    host: str,
    port: int,
    workspace: str | None = None,
    poll_seconds: float = 0.25,
) -> dict[str, Any]:
    """Write the packaged-process identity and monitor authenticated stop requests."""

    root = _absolute_owner_root(data_root)
    workspace_name = _workspace_name(workspace or os.environ.get("LINGJI_WORKSPACE"))
    state_path = runtime_state_path(root)
    stop_path = runtime_stop_request_path(root)
    instance_id = secrets.token_urlsafe(24)
    state = {
        "schema_version": _RUNTIME_SCHEMA_VERSION,
        "mode": "packaged_sidecar",
        "workspace": workspace_name,
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
    threading.Thread(
        target=monitor,
        name="lingji-sidecar-stop-monitor",
        daemon=True,
    ).start()
    return state


def _ensure_mcp_token(root: Path) -> str:
    path = mcp_token_path(root)
    try:
        token = path.read_text(encoding="utf-8").strip()
    except OSError:
        token = ""
    if token:
        return token
    token = secrets.token_urlsafe(32)
    _write_text_atomic(path, token + "\n")
    return token


def _runtime_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, str(Path(__file__).resolve(strict=False))]


def _hidden_process_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        kwargs["startupinfo"] = startupinfo
    return kwargs


def _start_managed_mcp_process(root: Path, workspace: str) -> subprocess.Popen[Any]:
    command = _runtime_command() + [
        "--data-root",
        str(root),
        "--workspace",
        workspace,
        "--service",
        "mcp",
        "--parent-pid",
        str(os.getpid()),
    ]
    process = subprocess.Popen(command, **_hidden_process_kwargs())

    def cleanup() -> None:
        if process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass

    atexit.register(cleanup)
    return process


def _install_parent_watch(parent_pid: int, *, poll_seconds: float = 0.5) -> None:
    if parent_pid <= 0:
        return

    def monitor() -> None:
        try:
            import psutil
        except ImportError:
            return
        while psutil.pid_exists(parent_pid):
            time.sleep(max(0.1, poll_seconds))
        os._exit(0)

    threading.Thread(target=monitor, name="lingji-mcp-parent-monitor", daemon=True).start()


def _install_mcp_state(root: Path, *, parent_pid: int, workspace: str) -> None:
    path = mcp_state_path(root)
    instance_id = secrets.token_urlsafe(24)
    _write_json_atomic(
        path,
        {
            "schema_version": 1,
            "mode": "packaged_mcp_http",
            "workspace": workspace,
            "pid": os.getpid(),
            "parent_pid": parent_pid,
            "instance_id": instance_id,
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "host": _MCP_HOST,
            "port": _MCP_PORT,
            "url": f"http://{_MCP_HOST}:{_MCP_PORT}/mcp",
            "authenticated": True,
        },
    )

    def cleanup() -> None:
        existing = _read_json(path)
        if existing and existing.get("instance_id") == instance_id:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    atexit.register(cleanup)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LingJi packaged local runtime")
    parser.add_argument("--data-root", required=True, help="Absolute active-workspace data root")
    parser.add_argument("--workspace", choices=sorted(_WORKSPACES), default=None)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--service", choices=sorted(_SERVICES), default="control")
    parser.add_argument("--parent-pid", type=int, default=0)
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Print the packaged runtime contract and exit without starting 8766",
    )
    parser.add_argument(
        "--check-config-output",
        help="Optional JSON output path for --check-config, used by windowed build validation",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workspace = _workspace_name(args.workspace or os.environ.get("LINGJI_WORKSPACE"))
    contract = packaged_runtime_contract(
        args.data_root,
        host=args.host,
        port=args.port,
        workspace=workspace,
    )
    if args.check_config:
        contract_json = json.dumps(contract, ensure_ascii=False, sort_keys=True)
        if args.check_config_output:
            output_path = Path(args.check_config_output).expanduser().resolve(strict=False)
            _write_json_atomic(output_path, contract)
        else:
            print(contract_json)
        return 0

    values = configure_packaged_environment(
        args.data_root,
        host=args.host,
        port=args.port,
        workspace=workspace,
    )
    root = Path(values["LINGJI_OWNER_DATA_ROOT"])
    _ensure_standard_streams()

    if args.service == "mcp":
        token = _ensure_mcp_token(root)
        _install_parent_watch(int(args.parent_pid))
        _install_mcp_state(root, parent_pid=int(args.parent_pid), workspace=workspace)
        from src.mcp_http import run_authenticated_mcp_http

        run_authenticated_mcp_http(
            token=token,
            host=_MCP_HOST,
            port=_MCP_PORT,
            agent_id="lingji-local",
        )
        return 0

    install_runtime_lifecycle(
        args.data_root,
        host=args.host,
        port=args.port,
        workspace=workspace,
    )
    _ensure_mcp_token(root)
    mcp_process = _start_managed_mcp_process(root, workspace)
    try:
        from run_control_api import main as run_control_api

        run_control_api()
    finally:
        if mcp_process.poll() is None:
            try:
                mcp_process.terminate()
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
