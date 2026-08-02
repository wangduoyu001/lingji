#!/usr/bin/env python3
"""Safely remove one task-scoped LingJi acceptance or validation workspace.

The command is intentionally narrow. It refuses paths outside the configured
root, refuses the root itself, never follows reparse points, and requires an
exact supported task identity plus explicit --execute before deletion.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_ROOT = Path(r"D:\codex\LingJiAcceptance")
_CODE_VALIDATION_TASK = re.compile(
    r"^PR(?P<pr>\d+)-CODE-RELEASE-VALIDATION-(?P<sha>[0-9A-F]{8})$",
    flags=re.IGNORECASE,
)
_MEMORY_TRIAL_TASK = re.compile(
    r"^PR(?P<pr>\d+)-MEMORY-QUALITY-TRIAL-(?P<sha>[0-9A-F]{8})$",
    flags=re.IGNORECASE,
)
_LEGACY_TARGETS_BY_TASK = {
    "PR60-MEMORY-QUALITY-TRIAL-1860FA17": frozenset(
        {
            "PR60-MEMORY-TRIAL-4161807c",
        }
    ),
    "PR60-MEMORY-QUALITY-TRIAL-D69874AF": frozenset(
        {
            "PR60-MEMORY-TRIAL-1c514877",
            "PR60-1c514877",
        }
    ),
}


class CleanupError(RuntimeError):
    """Raised when a cleanup request violates the safety contract."""


@dataclass(frozen=True)
class CleanupPolicy:
    root_name: str
    current_target: str
    extra_targets: frozenset[str] = frozenset()

    @property
    def allowed_targets(self) -> frozenset[str]:
        return frozenset({self.current_target, *self.extra_targets})


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


def resolve_policy(task_id: str) -> CleanupPolicy:
    normalized_task_id = task_id.strip().upper()

    match = _CODE_VALIDATION_TASK.fullmatch(normalized_task_id)
    if match:
        return CleanupPolicy(
            root_name="LingJiValidation",
            current_target=f"PR{match.group('pr')}-CODE-{match.group('sha').lower()}",
        )

    match = _MEMORY_TRIAL_TASK.fullmatch(normalized_task_id)
    if match:
        return CleanupPolicy(
            root_name="LingJiAcceptance",
            current_target=(
                f"PR{match.group('pr')}-MEMORY-TRIAL-{match.group('sha').lower()}"
            ),
            extra_targets=_LEGACY_TARGETS_BY_TASK.get(
                normalized_task_id,
                frozenset(),
            ),
        )

    raise CleanupError(f"unsupported cleanup task id: {task_id}")


def _norm(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(str(path))))


def validate_target(root: Path, target: Path, task_id: str) -> tuple[Path, Path]:
    root = _norm(root)
    target = _norm(target)
    policy = resolve_policy(task_id)

    if root.name.casefold() != policy.root_name.casefold():
        raise CleanupError(
            f"task requires cleanup root {policy.root_name}, got {root.name}"
        )
    if target == root:
        raise CleanupError("refusing to delete the cleanup root itself")
    try:
        relative = target.relative_to(root)
    except ValueError as exc:
        raise CleanupError("target is outside the cleanup root") from exc
    if len(relative.parts) != 1:
        raise CleanupError("target must be one direct child of the cleanup root")

    allowed_by_casefold = {
        candidate.casefold(): candidate for candidate in policy.allowed_targets
    }
    if target.name.casefold() not in allowed_by_casefold:
        allowed = ", ".join(sorted(policy.allowed_targets))
        raise CleanupError(
            f"target name is not authorized for {task_id}: {target.name}; "
            f"expected one of: {allowed}"
        )
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

    items = (Path(root, entry) for entry in manifest)
    for item in sorted(items, key=lambda path: len(path.parts), reverse=True):
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


def result_payload(result: CleanupResult, *, execute_requested: bool) -> dict[str, object]:
    payload: dict[str, object] = asdict(result)
    payload["authorized"] = True
    payload["execute_requested"] = bool(execute_requested)
    payload["planned_entries"] = len(result.remaining) if not result.executed else 0
    if result.executed:
        payload["status"] = "PASS"
        payload["next_action"] = "cleanup_complete"
    elif result.existed:
        payload["status"] = "DRY_RUN_READY"
        payload["next_action"] = "rerun_with_execute"
    else:
        payload["status"] = "PASS"
        payload["next_action"] = "nothing_to_remove"
    return payload


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
        print(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "authorized": False,
                    "execute_requested": bool(args.execute),
                    "error": str(exc),
                },
                ensure_ascii=False,
            )
        )
        return 2

    payload = result_payload(result, execute_requested=args.execute)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
