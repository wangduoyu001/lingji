#!/usr/bin/env python3
"""Create and safely remove task-scoped LingJi acceptance workspaces.

The cleanup path is deliberately conservative:

- the target must be a direct child of the configured acceptance root;
- a task marker must match the requested task ID, unless a narrowly scoped legacy
  cleanup is explicitly requested;
- symlinks and Windows junctions are refused;
- files are removed one by one and directories only after they are empty;
- recursive deletion helpers such as shutil.rmtree are intentionally not used.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

MARKER_NAME = ".lingji-acceptance-workspace.json"
DEFAULT_ALLOWED_ROOT = Path(r"D:\codex\LingJiAcceptance")
LEGACY_ALLOWED_ENTRIES = {
    "repo",
    "artifact",
    "logs",
    "evidence-private",
    "evidence-public",
    "fixtures",
    "checkpoint",
    "temp-config-backup",
    "report",
    "product-worktree",
    "report-worktree",
}


class CleanupError(ValueError):
    """Raised when a cleanup request violates the safety contract."""


@dataclass(frozen=True)
class CleanupSummary:
    action: str
    target: str
    task_id: str
    executed: bool
    files: int = 0
    directories: int = 0
    bytes: int = 0


def _resolved(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(_resolved(left))) == os.path.normcase(str(_resolved(right)))


def validate_target(target: Path, allowed_root: Path) -> tuple[Path, Path]:
    root = _resolved(allowed_root)
    resolved = _resolved(target)
    if _same_path(resolved, root):
        raise CleanupError("target must be a task directory, not the acceptance root")
    if not _same_path(resolved.parent, root):
        raise CleanupError("target must be a direct child of the configured acceptance root")
    if resolved.name in {"", ".", ".."}:
        raise CleanupError("target directory name is invalid")
    return resolved, root


def _is_link_or_junction(path: Path) -> bool:
    if path.is_symlink():
        return True
    isjunction = getattr(os.path, "isjunction", None)
    return bool(isjunction and isjunction(path))


def _write_marker(target: Path, task_id: str) -> None:
    marker = target / MARKER_NAME
    payload = {
        "schema_version": 1,
        "task_id": task_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target_name": target.name,
    }
    marker.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def initialize_workspace(target: Path, allowed_root: Path, task_id: str) -> CleanupSummary:
    target, root = validate_target(target, allowed_root)
    root.mkdir(parents=True, exist_ok=True)
    if _is_link_or_junction(root):
        raise CleanupError("acceptance root cannot be a symlink or junction")
    if target.exists():
        if _is_link_or_junction(target):
            raise CleanupError("target cannot be a symlink or junction")
        if any(target.iterdir()):
            raise CleanupError("target already exists and is not empty; clean it before initialization")
    else:
        target.mkdir(parents=False)
    _write_marker(target, task_id)
    return CleanupSummary("initialize", str(target), task_id, True, directories=1)


def _read_marker(target: Path) -> dict[str, object]:
    marker = target / MARKER_NAME
    if not marker.is_file():
        raise CleanupError(f"missing workspace marker: {MARKER_NAME}")
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CleanupError("workspace marker is unreadable") from exc
    if not isinstance(payload, dict):
        raise CleanupError("workspace marker must contain a JSON object")
    return payload


def _validate_legacy_entries(target: Path) -> None:
    unknown = sorted(entry.name for entry in target.iterdir() if entry.name not in LEGACY_ALLOWED_ENTRIES)
    if unknown:
        raise CleanupError("unmarked legacy workspace contains unexpected entries: " + ", ".join(unknown))


def _scan_tree(target: Path) -> tuple[list[Path], list[Path], int]:
    files: list[Path] = []
    directories: list[Path] = []
    total_bytes = 0

    def visit(directory: Path) -> None:
        nonlocal total_bytes
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda item: item.name.casefold())
        for entry in entries:
            path = Path(entry.path)
            if entry.is_symlink() or _is_link_or_junction(path):
                raise CleanupError(f"refusing symlink or junction inside workspace: {path.name}")
            if entry.is_dir(follow_symlinks=False):
                visit(path)
                directories.append(path)
                continue
            if not entry.is_file(follow_symlinks=False):
                raise CleanupError(f"unsupported filesystem entry inside workspace: {path.name}")
            files.append(path)
            try:
                total_bytes += entry.stat(follow_symlinks=False).st_size
            except OSError as exc:
                raise CleanupError(f"cannot stat workspace file: {path.name}") from exc

    visit(target)
    return files, directories, total_bytes


def _unlink_file(path: Path) -> None:
    try:
        path.unlink()
    except PermissionError:
        path.chmod(path.stat().st_mode | stat.S_IWRITE)
        path.unlink()


def cleanup_workspace(
    target: Path,
    allowed_root: Path,
    task_id: str,
    *,
    execute: bool,
    allow_unmarked_legacy: bool = False,
) -> CleanupSummary:
    target, _ = validate_target(target, allowed_root)
    if not target.is_dir():
        raise CleanupError("target workspace does not exist")
    if _is_link_or_junction(target):
        raise CleanupError("target cannot be a symlink or junction")

    marker = target / MARKER_NAME
    if marker.is_file():
        payload = _read_marker(target)
        if payload.get("task_id") != task_id:
            raise CleanupError("workspace marker task_id does not match the requested task")
    elif allow_unmarked_legacy:
        if target.name not in {
            "PR60-MEMORY-TRIAL-1c514877",
            "PR60-1c514877",
        }:
            raise CleanupError("legacy cleanup is allowed only for registered historical PR60 roots")
        _validate_legacy_entries(target)
    else:
        raise CleanupError("unmarked workspace cleanup requires explicit legacy mode")

    files, directories, total_bytes = _scan_tree(target)
    summary = CleanupSummary(
        "cleanup",
        str(target),
        task_id,
        execute,
        files=len(files),
        directories=len(directories) + 1,
        bytes=total_bytes,
    )
    if not execute:
        return summary

    for path in files:
        _unlink_file(path)
    for directory in directories:
        directory.rmdir()
    target.rmdir()
    return summary


def _print(summary: CleanupSummary) -> None:
    print(json.dumps(asdict(summary), ensure_ascii=False, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allowed-root", type=Path, default=DEFAULT_ALLOWED_ROOT)
    subparsers = parser.add_subparsers(dest="action", required=True)

    initialize = subparsers.add_parser("initialize")
    initialize.add_argument("--target", type=Path, required=True)
    initialize.add_argument("--task-id", required=True)

    cleanup = subparsers.add_parser("cleanup")
    cleanup.add_argument("--target", type=Path, required=True)
    cleanup.add_argument("--task-id", required=True)
    cleanup.add_argument("--execute", action="store_true")
    cleanup.add_argument("--allow-unmarked-legacy", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        if args.action == "initialize":
            summary = initialize_workspace(args.target, args.allowed_root, args.task_id)
        else:
            summary = cleanup_workspace(
                args.target,
                args.allowed_root,
                args.task_id,
                execute=args.execute,
                allow_unmarked_legacy=args.allow_unmarked_legacy,
            )
    except CleanupError as exc:
        print(f"ACCEPTANCE_WORKSPACE_CLEANUP: FAIL\n{exc}", file=sys.stderr)
        return 1
    _print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
