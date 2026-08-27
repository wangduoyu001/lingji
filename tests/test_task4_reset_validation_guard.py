from __future__ import annotations

from pathlib import Path


def test_release_validation_stops_before_100k_until_4r2_readiness() -> None:
    script = Path("scripts/validate.ps1").read_text(encoding="utf-8")
    release_section = script[script.index("function Invoke-ReleaseValidation"):]
    assert "BLOCKED_4R2_REQUIRED" in release_section
    assert "LINGJI_RUN_100K" not in release_section
    assert "automatic-memory-100k-scale" not in release_section
