from __future__ import annotations

import re
import shutil
import subprocess
import sys
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
        [sys.executable, "scripts/automatic_memory_quality_gate.py", "--check-4r2"],
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
        [sys.executable, "scripts/run_powershell_validation.py", "--mode", "release"],
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


def test_windows_full_suite_collects_the_real_release_runtime_guard() -> None:
    workflow = Path(".github/workflows/p0-windows-gate.yml").read_text(encoding="utf-8")
    test_source = Path("tests/test_task4_reset_validation_guard.py").read_text(encoding="utf-8")
    assert "- name: Run full repository test suite" in workflow
    assert "python -m pytest -q --tb=short" in workflow
    assert "test_release_entry_executes_real_powershell_when_available" in test_source
    assert "scripts/run_powershell_validation.py" in test_source
    assert "sys.platform == \"win32\"" in test_source


def test_release_entry_executes_real_powershell_when_available(tmp_path: Path) -> None:
    executable = next(
        (shutil.which(candidate) for candidate in ("pwsh", "powershell", "powershell.exe") if shutil.which(candidate)),
        None,
    )
    if sys.platform == "win32":
        assert executable is not None
    if executable is None:
        return

    hook = tmp_path / "release-hook.txt"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_powershell_validation.py",
            "--mode",
            "release",
            "--entry-only",
            "--hook",
            str(hook),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "BLOCKED_4R2_REQUIRED" in (result.stdout + result.stderr)
    events = [line.strip() for line in hook.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert events == ["preflight"]


def test_release_entry_only_is_double_opt_in_and_launcher_passes_real_switch() -> None:
    validation_script = Path("scripts/validate.ps1").read_text(encoding="utf-8")
    launcher = Path("scripts/run_powershell_validation.py").read_text(encoding="utf-8")
    assert "[switch]$TestReleaseEntryOnly" in validation_script
    assert 'LINGJI_VALIDATE_TEST_ENTRY_ONLY", "Process") -eq "1"' in validation_script
    assert 'LINGJI_VALIDATE_TEST_HOOK", "Process"' in validation_script
    assert 'parser.add_argument(\n        "--entry-only"' in launcher
    assert 'command.append("-TestReleaseEntryOnly")' in launcher
