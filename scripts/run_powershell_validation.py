"""Invoke the real PowerShell validation entry when a host provides it.

This is a CI/test launcher only. It never installs PowerShell and never
reimplements ``scripts/validate.ps1`` in Python.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _powershell_executable() -> str | None:
    for candidate in ("pwsh", "powershell", "powershell.exe"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("focused", "full", "release"), default="release")
    parser.add_argument("--area", default="docs")
    parser.add_argument("--python-command", default="python")
    parser.add_argument("--hook", type=Path, default=None)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="test-only validation root forwarded to the real PowerShell entry",
    )
    parser.add_argument(
        "--output-hint",
        default=None,
        help="optional bounded label for this invocation's evidence directory",
    )
    parser.add_argument(
        "--entry-only",
        action="store_true",
        help="test-only release dispatch; requires --hook and never skips normal validation by itself",
    )
    args = parser.parse_args(argv)
    if args.entry_only and (args.mode != "release" or args.hook is None):
        parser.error("--entry-only requires --mode release and --hook")
    executable = _powershell_executable()
    if executable is None:
        print("BLOCKED_POWERSHELL_RUNTIME_UNAVAILABLE", file=sys.stderr)
        return 2

    repo = Path(__file__).resolve().parents[1]
    command = [
        executable, "-NoProfile", "-File", str(repo / "scripts" / "validate.ps1"),
        "-Mode", args.mode, "-Area", args.area, "-PythonCommand", args.python_command,
    ]
    environment = os.environ.copy()
    if args.hook is not None:
        environment["LINGJI_VALIDATE_TEST_HOOK"] = str(args.hook)
    if args.output_root is not None:
        environment["LINGJI_VALIDATE_OUTPUT_ROOT"] = str(args.output_root)
    if args.output_hint is not None:
        environment["LINGJI_VALIDATE_OUTPUT_HINT"] = args.output_hint
    if args.entry_only:
        environment["LINGJI_VALIDATE_TEST_ENTRY_ONLY"] = "1"
        command.append("-TestReleaseEntryOnly")
    return subprocess.run(command, cwd=repo, env=environment, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
