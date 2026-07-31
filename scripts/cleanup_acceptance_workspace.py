#!/usr/bin/env python3
"""Safely remove one task-scoped LingJi acceptance workspace.

The command is intentionally narrow. It refuses paths outside the configured
acceptance root, refuses the root itself, never follows reparse points, and
requires both an exact task id and explicit --execute before deletion.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_ROOT = Path(r"D:\codex\LingJiAcceptance")
ALLOWED_TARGETS = {
    "PR60-MEMORY-TRIAL-1c514877",
    "PR60-1c514877",
    "PR60-MEMORY-TRIAL-d69874af",
}


class CleanupError(RuntimeError):
    """Raised when a cleanup request violates the safety contract."""


@dataclass(frozen=True)
class CleanupResult:
    root: str
    target: str
    existed: bool
    executed: bool
    files_removed: int
    directories_removed: int
    links_removed: int
    remaining: list[str]


def _norm(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(str(path))))


def validate_target(root: Path, target: Path, task_id: str) -> tuple[Path, Path]:
    root = _norm(root)
    target = _norm(target)
    if target == root:
        raise CleanupError("refusing to delete the acceptance root itself")
    try:
        relative = target.relative_to(root)
    except ValueError as exc:
        raise CleanupError("target is outside the acceptance root") from exc
    if len(relative.parts) != 1:
        raise CleanupError("target must be one direct child of the acceptance root")
    if target.name not in ALLOWED_TARGETS:
        raise CleanupError(f"target name is not allowlisted: {target.name}")
    expected_suffix = task_id.rsplit("-", 1)[-1].lower()
    if target.name.lower().endswith("d69874af") and expected_suffix != "d69874af":
        raise CleanupError("task id does not match the current target identity")
    if target.name.lower().endswith("1c514877") and expected_suffix not in {
        "d69874af",
        "1c514877",
    }:
        raise CleanupError("task id is not authorized to clean the historical target")
    return root, target


def _is_reparse_or_link(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(info.st_mode):
        return True
    attributes = getattr(info, "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _relative(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def build_manifest(root: Path, target: Path) -> list[str]:
    if not target.exists() and not _is_reparse_or_link(target):
        return []
    manifest: list[str] = []
    stack = [target]
    while stack:
        current = stack.pop()
        manifest.append(_relative(current, root))
        if _is_reparse_or_link(current) or not current.is_dir():
            continue
        try:
            children = sorted(current.iterdir(), key=lambda item: item.name.casefold())
        except PermissionError as exc:
            raise CleanupError(f"cannot inspect {_relative(current, root)}") from exc
        stack.extend(reversed(children))
    return manifest


def _make_writable(path: Path) -> None:
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    except OSError:
        pass


def cleanup(root: Path, target: Path, *, execute: bool) -> CleanupResult:
    existed = target.exists() or _is_reparse_or_link(target)
    manifest = build_manifest(root, target)
    if not execute or not existed:
        return CleanupResult(
            root=str(root),
            target=str(target),
            existed=existed,
            executed=False,
            files_removed=0,
            directories_removed=0,
            links_removed=0,
            remaining=manifest,
        )

    files_removed = 0
    directories_removed = 0
    links_removed = 0

    for item in sorted((Path(root, entry) for entry in manifest), key=lambda p: len(p.parts), reverse=True):
        if not item.exists() and not _is_reparse_or_link(item):
            continue
        try:
            if _is_reparse_or_link(item):
                if item.is_dir():
                    os.rmdir(item)
                else:
                    os.unlink(item)
                links_removed += 1
            elif item.is_dir():
                os.rmdir(item)
                directories_removed += 1
            else:
                _make_writable(item)
                os.unlink(item)
                files_removed += 1
        except OSError as exc:
            raise CleanupError(f"failed to remove {_relative(item, root)}: {exc}") from exc

    remaining = build_manifest(root, target)
    if remaining:
        raise CleanupError("cleanup completed with remaining entries")
    return CleanupResult(
        root=str(root),
        target=str(target),
        existed=existed,
        executed=True,
        files_removed=files_removed,
        directories_removed=directories_removed,
        links_removed=links_removed,
        remaining=[],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--json-output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        root, target = validate_target(args.root, args.target, args.task_id)
        result = cleanup(root, target, execute=args.execute)
    except CleanupError as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False))
        return 2

    payload = asdict(result)
    payload["status"] = "PASS" if not result.remaining else "BLOCKED"
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
