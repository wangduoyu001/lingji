from __future__ import annotations

import re
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
