#!/usr/bin/env python3
"""Validate P0 dependency, lock, frontend and portable-path contracts.

This offline validator complements, but does not replace, clean virtual
 environment installation and the full repository test/build gates.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REQUIREMENT_FILES = {
    "core": Path("requirements.txt"),
    "ui": Path("requirements-ui.txt"),
    "media": Path("requirements-media.txt"),
    "mcp": Path("requirements-mcp.txt"),
    "test": Path("requirements-test.txt"),
}
CONSTRAINT_FILES = (
    Path("constraints/python-3.13-linux.txt"),
    Path("constraints/python-3.12-windows.txt"),
)
FORBIDDEN_DEPENDENCY_PATTERNS = (
    re.compile(r"^\s*-e(?:\s|$)", re.IGNORECASE),
    re.compile(r"^\s*(?:file|git\+file)://", re.IGNORECASE),
    re.compile(r"^\s*[A-Za-z]:[\\/]"),
    re.compile(r"^\s*(?:\.\.?[\\/]|/)(?!requirements)", re.IGNORECASE),
    re.compile(r"(?:token|password|secret|credential)=", re.IGNORECASE),
    re.compile(r"://[^/\s]+@", re.IGNORECASE),
    re.compile(r"^\s*--(?:extra-)?index-url\b", re.IGNORECASE),
)
MACHINE_PATH_PATTERNS = (
    re.compile(r"[A-Za-z]:[\\/]Users[\\/]", re.IGNORECASE),
    re.compile(r"D:[\\/]codex[\\/]", re.IGNORECASE),
)
CORE_FORBIDDEN_PACKAGES = {
    "pytest",
    "fastapi",
    "uvicorn",
    "httpx",
    "mcp",
    "paddleocr",
    "faster-whisper",
    "scenedetect",
}


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


def _meaningful_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _package_name(line: str) -> str:
    candidate = line.split(";", 1)[0].strip()
    if candidate.startswith("-r ") or candidate.startswith("--requirement "):
        return ""
    match = re.match(r"([A-Za-z0-9_.-]+)", candidate)
    return match.group(1).replace("_", "-").lower() if match else ""


def _unsafe_dependency_line(line: str) -> bool:
    return any(pattern.search(line) for pattern in FORBIDDEN_DEPENDENCY_PATTERNS)


def validate_requirements(root: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    lines_by_owner: dict[str, list[str]] = {}
    for owner, relative_path in REQUIREMENT_FILES.items():
        path = root / relative_path
        if not path.is_file():
            issues.append(
                ValidationIssue(
                    "missing_requirement_file",
                    str(relative_path),
                    f"Missing {owner} requirements file",
                )
            )
            continue
        lines = _meaningful_lines(path)
        lines_by_owner[owner] = lines
        for line in lines:
            if _unsafe_dependency_line(line):
                issues.append(
                    ValidationIssue(
                        "unsafe_requirement",
                        str(relative_path),
                        f"Unsafe or machine-local requirement: {line}",
                    )
                )

    core_packages = {_package_name(line) for line in lines_by_owner.get("core", [])}
    for package in sorted(CORE_FORBIDDEN_PACKAGES & core_packages):
        issues.append(
            ValidationIssue(
                "dependency_ownership",
                "requirements.txt",
                f"{package} does not belong to core requirements",
            )
        )

    for owner in ("ui", "media", "mcp"):
        lines = lines_by_owner.get(owner, [])
        if lines and not any(
            line in {"-r requirements.txt", "--requirement requirements.txt"}
            for line in lines
        ):
            issues.append(
                ValidationIssue(
                    "dependency_ownership",
                    str(REQUIREMENT_FILES[owner]),
                    f"{owner} requirements must include requirements.txt",
                )
            )

    test_packages = {_package_name(line) for line in lines_by_owner.get("test", [])}
    if lines_by_owner.get("test") is not None and "pytest" not in test_packages:
        issues.append(
            ValidationIssue(
                "dependency_ownership",
                "requirements-test.txt",
                "Test requirements must declare pytest",
            )
        )
    return issues


def validate_constraints(root: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for relative_path in CONSTRAINT_FILES:
        path = root / relative_path
        if not path.is_file():
            issues.append(
                ValidationIssue(
                    "missing_constraint_file",
                    str(relative_path),
                    "Generated dependency constraint file is missing",
                )
            )
            continue
        for line in _meaningful_lines(path):
            if _unsafe_dependency_line(line):
                issues.append(
                    ValidationIssue(
                        "unsafe_constraint",
                        str(relative_path),
                        f"Unsafe or credential-bearing constraint: {line}",
                    )
                )
                continue
            if "==" not in line:
                issues.append(
                    ValidationIssue(
                        "unpinned_constraint",
                        str(relative_path),
                        f"Constraint is not exactly pinned: {line}",
                    )
                )
    return issues


def validate_frontend_lock(root: Path) -> list[ValidationIssue]:
    package_path = root / "desktop/lingji-control/package.json"
    lock_path = root / "desktop/lingji-control/package-lock.json"
    missing = [path for path in (package_path, lock_path) if not path.is_file()]
    if missing:
        return [
            ValidationIssue(
                "missing_frontend_file",
                str(path.relative_to(root)),
                "Frontend dependency file is missing",
            )
            for path in missing
        ]

    package = json.loads(package_path.read_text(encoding="utf-8-sig"))
    lock = json.loads(lock_path.read_text(encoding="utf-8-sig"))
    root_package = lock.get("packages", {}).get("", {})
    issues: list[ValidationIssue] = []
    for key in ("name", "version", "dependencies", "devDependencies"):
        if package.get(key, {}) != root_package.get(key, {}):
            issues.append(
                ValidationIssue(
                    "frontend_lock_mismatch",
                    str(lock_path.relative_to(root)),
                    f"package-lock root field {key!r} does not match package.json",
                )
            )
    return issues


def validate_machine_paths(root: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    targets: Iterable[Path] = (
        root / "src/config.py",
        root / "src/runtime/workspace.py",
        root / "src/control/runtime_settings.py",
        root / "second_brain/obsidian_cli.py",
        root / "main.py",
        root / "run_service.py",
        root / "run_control_api.py",
        root / "run_mcp_server.py",
        root / "run_extraction_worker.py",
    )
    for path in targets:
        if not path.is_file():
            issues.append(
                ValidationIssue(
                    "missing_contract_file",
                    str(path.relative_to(root)),
                    "Required P0 contract file is missing",
                )
            )
            continue
        text = path.read_text(encoding="utf-8-sig")
        for pattern in MACHINE_PATH_PATTERNS:
            match = pattern.search(text)
            if match:
                issues.append(
                    ValidationIssue(
                        "machine_specific_path",
                        str(path.relative_to(root)),
                        f"Machine-specific path found: {match.group(0)}",
                    )
                )
    return issues


def validate_imports() -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for module in (
        "src",
        "src.config",
        "src.control.api",
        "second_brain.obsidian_cli",
    ):
        try:
            __import__(module)
        except Exception as exc:  # pragma: no cover - clean-env dependent
            issues.append(
                ValidationIssue(
                    "import_failed",
                    module,
                    f"{type(exc).__name__}: {exc}",
                )
            )
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate LingJi P0 clean-install contracts"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument(
        "--import-check",
        action="store_true",
        help="Import installed runtime modules after dependency installation",
    )
    args = parser.parse_args()
    root = args.root.expanduser().resolve(strict=False)

    issues = validate_requirements(root)
    issues.extend(validate_constraints(root))
    issues.extend(validate_frontend_lock(root))
    issues.extend(validate_machine_paths(root))
    if args.import_check:
        sys.path.insert(0, str(root))
        issues.extend(validate_imports())

    payload = {
        "ok": not issues,
        "root": str(root),
        "checks": [
            "requirements",
            "constraints",
            "frontend_lock",
            "machine_paths",
        ]
        + (["imports"] if args.import_check else []),
        "issues": [issue.as_dict() for issue in issues],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
