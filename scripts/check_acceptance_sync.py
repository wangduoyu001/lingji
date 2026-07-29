from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Sequence

ACCEPTANCE_LOG = "docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md"
ACCEPTANCE_PREFIX = "docs/ACCEPTANCE/"

PRODUCT_PREFIXES = (
    "src/",
    "second_brain/",
    "desktop/lingji-control/src/",
    "desktop/lingji-control/src-tauri/",
    "desktop/lingji-control/scripts/",
    "browser-extension/",
    "obsidian-plugin/",
    "scripts/",
    ".github/workflows/",
    "constraints/",
)

PRODUCT_ROOT_FILES = {
    "main.py",
    "start_lingji.py",
    "start_lingji.bat",
    "pyproject.toml",
    "requirements.txt",
    "requirements-ui.txt",
    "requirements-test.txt",
    "requirements-mcp.txt",
    "requirements-sidecar-build.txt",
}

PRODUCT_ROOT_PREFIXES = (
    "run_",
    "requirements-",
)

ZERO_SHA = "0" * 40


class GitCommandError(RuntimeError):
    """Raised when a required git command fails."""


def normalize_path(path: str) -> str:
    return path.strip().replace("\\", "/").lstrip("./")


def is_product_change(path: str) -> bool:
    normalized = normalize_path(path)
    if normalized in PRODUCT_ROOT_FILES:
        return True
    if any(normalized.startswith(prefix) for prefix in PRODUCT_PREFIXES):
        return True
    if "/" not in normalized and any(
        normalized.startswith(prefix) for prefix in PRODUCT_ROOT_PREFIXES
    ):
        return True
    return False


def is_acceptance_change(path: str) -> bool:
    return normalize_path(path).startswith(ACCEPTANCE_PREFIX)


def validate_changed_paths(paths: Iterable[str]) -> tuple[bool, list[str], list[str]]:
    normalized = sorted({normalize_path(path) for path in paths if path.strip()})
    product_changes = [path for path in normalized if is_product_change(path)]
    acceptance_changes = [path for path in normalized if is_acceptance_change(path)]

    if not product_changes:
        return True, product_changes, acceptance_changes

    if ACCEPTANCE_LOG not in acceptance_changes:
        return False, product_changes, acceptance_changes

    return True, product_changes, acceptance_changes


def run_git(repo_root: Path, arguments: Sequence[str]) -> list[str]:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise GitCommandError(
            f"git {' '.join(arguments)} failed with {result.returncode}: "
            f"{result.stderr.strip()}"
        )
    return [line for line in result.stdout.splitlines() if line.strip()]


def resolve_changed_paths(
    repo_root: Path,
    base: str | None,
    head: str | None,
) -> list[str]:
    if base and base != ZERO_SHA:
        resolved_head = head or "HEAD"
        return run_git(repo_root, ["diff", "--name-only", f"{base}...{resolved_head}"])

    working_tree = run_git(repo_root, ["diff", "--name-only", "HEAD"])
    untracked = run_git(repo_root, ["ls-files", "--others", "--exclude-standard"])
    changed = sorted(set(working_tree + untracked))
    if changed:
        return changed

    try:
        return run_git(repo_root, ["diff", "--name-only", "HEAD^...HEAD"])
    except GitCommandError:
        return []


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fail when product-affecting changes are not accompanied by an "
            "update to docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md."
        )
    )
    parser.add_argument("--base", default=os.getenv("ACCEPTANCE_BASE_SHA"))
    parser.add_argument("--head", default=os.getenv("ACCEPTANCE_HEAD_SHA"))
    parser.add_argument("--repo-root", default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = (
        Path(args.repo_root).resolve()
        if args.repo_root
        else Path(__file__).resolve().parents[1]
    )

    try:
        changed_paths = resolve_changed_paths(repo_root, args.base, args.head)
    except GitCommandError as exc:
        print(f"[acceptance-sync] BLOCKED: {exc}", file=sys.stderr)
        return 2

    valid, product_changes, acceptance_changes = validate_changed_paths(changed_paths)

    print(f"[acceptance-sync] changed files: {len(changed_paths)}")
    print(f"[acceptance-sync] product-impacting files: {len(product_changes)}")

    if not product_changes:
        print("[acceptance-sync] PASS: no product-impacting changes detected.")
        return 0

    if valid:
        print(
            "[acceptance-sync] PASS: product changes are accompanied by "
            f"{ACCEPTANCE_LOG}."
        )
        return 0

    print(
        "[acceptance-sync] FAIL: product-impacting changes require an update to "
        f"{ACCEPTANCE_LOG} in the same change.",
        file=sys.stderr,
    )
    print("[acceptance-sync] product-impacting files:", file=sys.stderr)
    for path in product_changes:
        print(f"  - {path}", file=sys.stderr)
    if acceptance_changes:
        print(
            "[acceptance-sync] acceptance files changed, but the mandatory change "
            "log was not updated:",
            file=sys.stderr,
        )
        for path in acceptance_changes:
            print(f"  - {path}", file=sys.stderr)
    print(
        "[acceptance-sync] add the change-specific automatic tests, real-machine "
        "steps, owner observations, regressions, cleanup and report path before "
        "requesting merge.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
