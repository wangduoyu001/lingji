from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


def test_release_validation_stops_before_100k_until_4r2_readiness() -> None:
    script = Path("scripts/validate.ps1").read_text(encoding="utf-8")
    release_section = script[script.index("function Invoke-ReleaseValidation"):]
    # Instrument the actual command declared by the PowerShell release entry:
    # execute the same Python preflight and assert its stable blocking result.
    command = re.search(
        r'-Command \$PythonCommand\s+`?\s*-Arguments @\("scripts/automatic_memory_quality_gate\.py", "--check-4r2"\)',
        release_section,
    )
    assert command is not None
    result = subprocess.run(
        ["./.venv/bin/python", "scripts/automatic_memory_quality_gate.py", "--check-4r2"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "BLOCKED_4R2_REQUIRED" in result.stderr
    assert "LINGJI_RUN_100K" not in release_section
    assert "automatic-memory-100k-scale" not in release_section


def test_powershell_launcher_is_truthful_when_runtime_is_unavailable() -> None:
    if any(shutil.which(candidate) for candidate in ("pwsh", "powershell", "powershell.exe")):
        return
    result = subprocess.run(
        ["./.venv/bin/python", "scripts/run_powershell_validation.py", "--mode", "release"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert result.stderr.strip() == "BLOCKED_POWERSHELL_RUNTIME_UNAVAILABLE"


def test_release_entry_exposes_opt_in_order_hook_without_scale_side_effects() -> None:
    script = Path("scripts/validate.ps1").read_text(encoding="utf-8")
    release_section = script[script.index("function Invoke-ReleaseValidation"):]
    assert "LINGJI_VALIDATE_TEST_HOOK" in release_section
    assert 'Write-ReleaseTestHook -Event "preflight"' in release_section
    assert 'Write-ReleaseTestHook -Event "scale-env"' in release_section
    assert 'Write-ReleaseTestHook -Event "scale-command"' in release_section
