from __future__ import annotations

import argparse
import atexit
import json
import os
import re
import secrets
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence

_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
_WORKSPACES = {"production", "acceptance"}
_WINDOWS_SYSTEM_DRIVE = re.compile(r"^c:[\\/]", re.IGNORECASE)
_RUNTIME_SCHEMA_VERSION = 1


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
    """Configure explicit paths before importing ``src.config``.

    ``data_root`` is the active workspace root. The Desktop derives it from a
    user-selected non-system-drive base directory plus ``production`` or
    ``acceptance``. The two workspace profiles therefore remain physically
    separate while the small bootstrap pointer may stay under LocalAppData.
    """

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
        "LINGJI_PACKAGED_RUNTIME": "1",
        "LINGJI_OWNER_DATA_ROOT": str(root),
    }
    target.update(required_values)
    # 数据根 .env 是部署配置面：白名单键读入进程环境（进程环境已设置时仍以
    # 环境优先）。VAULT_DIR（2026-09-24）与 VALUE_GATE_EVIDENCE_ENABLED
    # （2026-09-28 证据层价值门）先后加入。
    env_file = root / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            if key == "VAULT_DIR" and "VAULT_DIR" not in target:
                if value.strip():
                    target["VAULT_DIR"] = str(Path(value.strip().strip('"').strip("'")).expanduser())
            elif key.upper() == "VALUE_GATE_EVIDENCE_ENABLED":
                target.setdefault("VALUE_GATE_EVIDENCE_ENABLED", value.strip())
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

    return {
        **required_values,
        "VAULT_DIR": target["VAULT_DIR"],
    }


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
        "schema_version": 2,
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

    def health_watchdog() -> None:
        """带升级的进程内健康看门狗（2026-09-27 事故）。

        多线程卡死在系统调用（DNS/文件打开/目录列举）时，端口仍在听但 HTTP
        零响应，且 SIGTERM 的优雅停机会被卡死线程拖住、进程"杀不掉"。
        探活绕过环境代理直连 loopback（任何 HTTP 响应——含 401——都算活着）；
        连续超时先 SIGTERM，宽限期内未恢复则 SIGKILL，把不可用时长约束在
        阈值 × 间隔 + 宽限之内。
        """
        if str(os.environ.get("LINGJI_WATCHDOG_ENABLED", "1")).strip().lower() in {"0", "false", "off"}:
            return
        interval = 20.0
        threshold = 3
        grace_seconds = 30.0
        boot_deadline_seconds = 600.0  # 启动期：索引重建/大集合打开可慢，给足死限
        started_at = time.monotonic()
        import urllib.request

        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        failures = 0
        armed = False  # 首次探活成功后才武装：启动慢≠挂死（2026-09-27 夜误杀教训）
        while True:
            time.sleep(interval)
            request = _read_json(stop_path)
            if request and request.get("instance_id") == instance_id:
                failures = 0  # 有意停机在途，看门狗不插手
                continue
            alive = False
            try:
                with opener.open(
                    f"http://127.0.0.1:{int(port)}/api/runtime/ping", timeout=5.0
                ) as response:
                    alive = 200 <= int(getattr(response, "status", 0) or 0) < 500
            except Exception:
                alive = False
            if alive:
                armed = True
                failures = 0
                continue
            if not armed:
                if time.monotonic() - started_at < boot_deadline_seconds:
                    continue  # 启动期不判死，只等
                # 启动超过死限仍无一次成功探活：升级一次，给 Tauri 重启机会
            elif failures < threshold:
                failures += 1
                continue
            try:
                os.kill(os.getpid(), signal.SIGTERM)
            except Exception:
                pass
            deadline = time.monotonic() + grace_seconds
            while time.monotonic() < deadline:
                time.sleep(1.0)
                request = _read_json(stop_path)
                if request and request.get("instance_id") == instance_id:
                    return  # 有意停机接手，放弃强杀
            os.kill(os.getpid(), signal.SIGKILL)
            return

    atexit.register(cleanup)
    thread = threading.Thread(
        target=monitor,
        name="lingji-sidecar-stop-monitor",
        daemon=True,
    )
    thread.start()
    watchdog = threading.Thread(
        target=health_watchdog,
        name="lingji-sidecar-health-watchdog",
        daemon=True,
    )
    watchdog.start()
    return state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LingJi packaged local control runtime")
    parser.add_argument("--data-root", required=True, help="Absolute active-workspace data root")
    parser.add_argument("--workspace", choices=sorted(_WORKSPACES), default=None)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
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

    configure_packaged_environment(
        args.data_root,
        host=args.host,
        port=args.port,
        workspace=workspace,
    )
    install_runtime_lifecycle(
        args.data_root,
        host=args.host,
        port=args.port,
        workspace=workspace,
    )
    _ensure_standard_streams()
    from run_control_api import main as run_control_api

    run_control_api()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
