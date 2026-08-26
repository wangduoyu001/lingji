"""Task 4 opt-in 100k-message scale tests."""

import os

import pytest


def test_100k_scale_gate_is_explicitly_opt_in(tmp_path):
    if os.environ.get("LINGJI_RUN_100K") != "1":
        pytest.skip("set LINGJI_RUN_100K=1 to run the 100k Acceptance benchmark")

    from src.automatic_memory.quality_gate import run_100k_benchmark

    report = run_100k_benchmark(output_path=tmp_path / "scale.json")
    assert report["messages"] == 100_000
    assert report["imported_messages"] == 100_000
    assert report["cleanup_result"] == "cleaned"
