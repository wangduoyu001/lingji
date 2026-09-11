"""Single read-only manifest of locally installed AI software (owner intake plan Task 4).

The manifest combines three metadata-only probes — whitelisted application bundles,
whitelisted editor extension directory names, and whitelisted running process
names — and never opens chat bodies, databases, credentials or configuration.
Detected software without a safe session adapter is reported as "已发现，暂不支持
自动读取"; it must never be presented as importable.
"""

from __future__ import annotations

import os
import plistlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

MAX_APP_ENTRIES = 500
MAX_PLIST_BYTES = 1_000_000
MAX_EXTENSION_NAMES = 2000
MAX_PROCESS_ROWS = 1000


@dataclass(frozen=True)
class AppCatalogEntry:
    kind: str
    display_name: str
    app_names: tuple[str, ...] = ()
    process_names: tuple[str, ...] = ()
    extension_dirs: tuple[str, ...] = ()
    extension_prefixes: tuple[str, ...] = ()
    capabilities: Mapping[str, bool] = field(default_factory=dict)
    supported: bool = False
    detail: str = "已发现，暂不支持自动读取。"

    def row_capabilities(self) -> dict[str, bool]:
        return {key: bool(self.capabilities.get(key, False)) for key in sorted(CAPABILITY_KEYS)}


CAPABILITY_KEYS = (
    "auto_discovery",
    "requires_authorization",
    "official_export_inbox",
    "session_read",
    "message_body_view",
    "model_process_status",
)

_READ_VIA_OFFICIAL_EXPORT = "需要主人提供官方导出文件后才能读取。"

APP_CATALOG: Mapping[str, AppCatalogEntry] = {
    entry.kind: entry
    for entry in (
        AppCatalogEntry(
            "chatgpt_official", "ChatGPT",
            app_names=("ChatGPT.app",),
            process_names=("ChatGPT",),
            capabilities={
                "auto_discovery": True, "requires_authorization": True,
                "official_export_inbox": True, "session_read": True,
                "message_body_view": True, "model_process_status": True,
            },
            supported=True,
            detail="官方导出导入受支持；灵机会自动准备接收文件夹并给出放入步骤。",
        ),
        AppCatalogEntry(
            "codex_rollout", "Codex",
            app_names=("Codex.app",),
            process_names=("Codex",),
            capabilities={
                "auto_discovery": True, "requires_authorization": True,
                "official_export_inbox": False, "session_read": True,
                "message_body_view": True, "model_process_status": True,
            },
            supported=True,
            detail="可自动发现本机 rollout 记录；主人授权后自动读取。",
        ),
        AppCatalogEntry(
            "workbuddy", "WorkBuddy",
            app_names=("WorkBuddy.app",),
            process_names=("WorkBuddy", "workbuddy"),
            extension_dirs=("$HOME/.workbuddy",),
            capabilities={
                "auto_discovery": True, "requires_authorization": False,
                "official_export_inbox": False, "session_read": False,
                "message_body_view": False, "model_process_status": True,
            },
            supported=False,
            detail="已发现，暂不支持自动读取；适配器开发中，接入前不会读取它的任何数据。",
        ),
        AppCatalogEntry(
            "claude_desktop", "Claude",
            app_names=("Claude.app",),
            process_names=("Claude",),
            capabilities={
                "auto_discovery": True, "requires_authorization": False,
                "official_export_inbox": False, "session_read": False,
                "message_body_view": False, "model_process_status": True,
            },
            supported=False,
            detail="已发现，暂不支持自动读取；灵机不会读取它的内部数据库。",
        ),
        AppCatalogEntry(
            "cursor", "Cursor",
            app_names=("Cursor.app",),
            process_names=("Cursor", "Cursor Helper"),
            extension_dirs=(".cursor/extensions",),
            capabilities={
                "auto_discovery": True, "requires_authorization": False,
                "official_export_inbox": False, "session_read": False,
                "message_body_view": False, "model_process_status": True,
            },
            supported=False,
        ),
        AppCatalogEntry(
            "windsurf", "Windsurf",
            app_names=("Windsurf.app",),
            process_names=("Windsurf",),
            extension_dirs=(".windsurf/extensions",),
            capabilities={
                "auto_discovery": True, "requires_authorization": False,
                "official_export_inbox": False, "session_read": False,
                "message_body_view": False, "model_process_status": True,
            },
            supported=False,
        ),
        AppCatalogEntry(
            "opencode", "OpenCode",
            process_names=("opencode",),
            capabilities={
                "auto_discovery": True, "requires_authorization": False,
                "official_export_inbox": False, "session_read": False,
                "message_body_view": False, "model_process_status": True,
            },
            supported=False,
        ),
        AppCatalogEntry(
            "zcode", "ZCode",
            process_names=("zcode",),
            capabilities={
                "auto_discovery": True, "requires_authorization": False,
                "official_export_inbox": False, "session_read": False,
                "message_body_view": False, "model_process_status": True,
            },
            supported=False,
        ),
        AppCatalogEntry(
            "vscode", "VS Code",
            app_names=("Visual Studio Code.app", "Code - Insiders.app"),
            process_names=("Code", "Code Helper"),
            capabilities={
                "auto_discovery": True, "requires_authorization": False,
                "official_export_inbox": False, "session_read": False,
                "message_body_view": False, "model_process_status": True,
            },
            supported=False,
        ),
        AppCatalogEntry(
            "cline", "Cline（VS Code 代理）",
            extension_dirs=(".vscode/extensions", ".cursor/extensions"),
            extension_prefixes=("saoudrizwan.claude-dev",),
            capabilities={
                "auto_discovery": True, "requires_authorization": False,
                "official_export_inbox": False, "session_read": False,
                "message_body_view": False, "model_process_status": False,
            },
            supported=False,
        ),
        AppCatalogEntry(
            "roo_code", "Roo Code（VS Code 代理）",
            extension_dirs=(".vscode/extensions", ".cursor/extensions"),
            extension_prefixes=("rooveterinaryinc.roo-cline",),
            capabilities={
                "auto_discovery": True, "requires_authorization": False,
                "official_export_inbox": False, "session_read": False,
                "message_body_view": False, "model_process_status": False,
            },
            supported=False,
        ),
        AppCatalogEntry(
            "continue", "Continue（VS Code 代理）",
            extension_dirs=(".vscode/extensions", ".cursor/extensions"),
            extension_prefixes=("continue.continue",),
            capabilities={
                "auto_discovery": True, "requires_authorization": False,
                "official_export_inbox": False, "session_read": False,
                "message_body_view": False, "model_process_status": False,
            },
            supported=False,
        ),
        AppCatalogEntry(
            "ollama", "Ollama",
            app_names=("Ollama.app",),
            process_names=("Ollama", "ollama"),
            capabilities={
                "auto_discovery": True, "requires_authorization": False,
                "official_export_inbox": False, "session_read": False,
                "message_body_view": False, "model_process_status": True,
            },
            supported=False,
            detail="已发现，暂不支持自动读取；本地模型状态见“模型与进程”。",
        ),
        AppCatalogEntry(
            "lm_studio", "LM Studio",
            app_names=("LM Studio.app",),
            process_names=("LM Studio",),
            capabilities={
                "auto_discovery": True, "requires_authorization": False,
                "official_export_inbox": False, "session_read": False,
                "message_body_view": False, "model_process_status": True,
            },
            supported=False,
            detail="已发现，暂不支持自动读取；本地模型状态见“模型与进程”。",
        ),
    )
}


def _default_process_provider() -> list[tuple[str, int]]:
    try:
        import psutil
    except ImportError:  # pragma: no cover - optional UI dependency
        return []
    processes: list[tuple[str, int]] = []
    for info in psutil.process_iter(attrs=["pid", "name"]):
        name = str((info.info or {}).get("name") or "").strip()
        if name:
            processes.append((name, int((info.info or {}).get("pid") or 0)))
    return processes


def _app_roots(settings: object) -> tuple[Path, ...]:
    supplied = getattr(settings, "app_manifest_app_roots", None)
    if supplied:
        return tuple(Path(item) for item in supplied)
    home = _home(settings)
    return (Path("/Applications"), home / "Applications")


def _home(settings: object) -> Path:
    environ = getattr(settings, "environ", None) or os.environ
    home = environ.get("HOME") if isinstance(environ, Mapping) else None
    if home:
        return Path(home).expanduser()
    return Path.home()


def _extension_base(settings: object) -> Path:
    supplied = getattr(settings, "app_manifest_extension_base", None)
    return Path(supplied) if supplied else _home(settings)


def _process_provider(settings: object) -> Callable[[], list[tuple[str, int]]]:
    supplied = getattr(settings, "app_manifest_process_provider", None)
    return supplied if supplied is not None else _default_process_provider


def _read_bundle_metadata(bundle: Path) -> tuple[str | None, str | None]:
    """Read the two whitelisted Info.plist fields; never anything else."""
    import stat as stat_module

    info = bundle / "Contents" / "Info.plist"
    try:
        stat = info.lstat()
    except OSError:
        return None, None
    if not stat_module.S_ISREG(stat.st_mode) or stat.st_size > MAX_PLIST_BYTES:
        return None, None
    try:
        with info.open("rb") as handle:
            payload = plistlib.load(handle)
    except (OSError, plistlib.InvalidFileException):
        return None, None
    if not isinstance(payload, dict):
        return None, None
    bundle_id = payload.get("CFBundleIdentifier")
    version = payload.get("CFBundleShortVersionString") or payload.get("CFBundleVersion")
    return (str(bundle_id) if bundle_id else None, str(version) if version else None)


def discover_app_manifest(settings: object) -> list[dict[str, Any]]:
    """Project the detected AI software manifest with safe owner-facing rows."""
    roots = _app_roots(settings)
    extension_base = _extension_base(settings)
    processes = _process_provider(settings)()
    lowered_processes = {name.strip().casefold() for name, _pid in processes}

    detected: dict[str, dict[str, Any]] = {}

    def ensure(kind: str) -> dict[str, Any]:
        row = detected.get(kind)
        if row is None:
            entry = APP_CATALOG[kind]
            row = {
                "kind": kind,
                "display_name": entry.display_name,
                "install_status": "detected",
                "running": None,
                "bundle_id": None,
                "version": None,
                "capabilities": entry.row_capabilities(),
                "supported": entry.supported,
                "detail": entry.detail,
            }
            detected[kind] = row
        return row

    scanned = 0
    for root in roots:
        try:
            entries = list(root.iterdir())
        except OSError:
            continue
        for node in entries:
            scanned += 1
            if scanned > MAX_APP_ENTRIES:
                break
            if node.name.casefold() == ".ds_store":
                continue
            try:
                if node.is_symlink() or not node.is_dir() or node.suffix.casefold() != ".app":
                    continue
            except OSError:
                continue
            entry = next(
                (candidate for candidate in APP_CATALOG.values() if node.name in candidate.app_names),
                None,
            )
            if entry is None:
                continue
            bundle_id, version = _read_bundle_metadata(node)
            row = ensure(entry.kind)
            row["install_status"] = "installed"
            row["bundle_id"] = bundle_id if entry.supported else None
            row["version"] = version if entry.supported else None
        if scanned > MAX_APP_ENTRIES:
            break

    for entry in APP_CATALOG.values():
        if not entry.extension_dirs or not entry.extension_prefixes:
            continue
        for relative in entry.extension_dirs:
            directory = extension_base / relative
            try:
                names = list(directory.iterdir())
            except OSError:
                continue
            if len(names) > MAX_EXTENSION_NAMES:
                names = names[:MAX_EXTENSION_NAMES]
            matched = any(
                not node.is_symlink()
                and node.name.casefold().startswith(
                    tuple(prefix.casefold() for prefix in entry.extension_prefixes)
                )
                for node in names
            )
            if matched:
                ensure(entry.kind)
                break

    matched_processes = {name.strip().casefold() for name, _pid in processes} & {
        process_name.casefold()
        for candidate in APP_CATALOG.values()
        for process_name in candidate.process_names
    }
    for kind, candidate in APP_CATALOG.items():
        hits = {name.casefold() for name in candidate.process_names} & matched_processes
        if not hits:
            continue
        row = ensure(kind)
        row["running"] = True

    for kind, entry in APP_CATALOG.items():
        if entry.process_names and kind in detected and detected[kind]["running"] is None:
            detected[kind]["running"] = False

    return sorted(detected.values(), key=lambda row: row["display_name"])


def discover_running_processes(settings: object) -> list[dict[str, Any]]:
    """Whitelisted running AI processes with owner-safe fields only.

    Only the process display name (mapped through the catalog), the pid for
    collapsed advanced diagnostics, a running state and the read time are
    exposed. Raw command lines, environment, paths, ports and credentials are
    never collected.
    """
    provider = _process_provider(settings)()
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    lowered_catalog = {
        process_name.casefold(): (kind, candidate)
        for kind, candidate in APP_CATALOG.items()
        for process_name in candidate.process_names
    }
    for name, pid in provider:
        if len(rows) >= MAX_PROCESS_ROWS:
            break
        match = lowered_catalog.get(str(name).strip().casefold())
        if match is None:
            continue
        key = (match[0], int(pid))
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "kind": match[0],
                "display_name": match[1].display_name,
                "pid": int(pid),
                "state": "running",
                "updated_at": _now_iso(),
            }
        )
    return sorted(rows, key=lambda row: (row["display_name"], row["pid"]))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


__all__ = ["APP_CATALOG", "CAPABILITY_KEYS", "discover_app_manifest", "discover_running_processes"]
