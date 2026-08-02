from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("powershell") is None, reason="Windows PowerShell required")
def test_validation_git_identity_ignores_stale_native_exit_code() -> None:
    helper = REPO_ROOT / "scripts" / "validation_git.ps1"
    command = (
        "$global:LASTEXITCODE = -1; "
        f". '{helper}'; "
        "$commit = Get-GitValue -Arguments @('rev-parse', 'HEAD') -Fallback 'unknown'; "
        "$global:LASTEXITCODE = -1; "
        "$branch = Get-GitValue -Arguments @('rev-parse', '--abbrev-ref', 'HEAD') -Fallback 'unknown'; "
        "@{ commit = $commit; branch = $branch } | ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout.strip())

    expected_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
    ).strip()
    expected_branch = subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO_ROOT, text=True
    ).strip()

    assert payload == {"commit": expected_commit, "branch": expected_branch}
