"""Preserved Task 4R1 round-5 rejection facts.

Round-5 automatic-activation behavior was rejected and is intentionally not a
current PASS contract. These tests keep that history visible while the reset
runner remains quarantined before Task 4R2.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.automatic_memory.quality_gate import run_quality_gate, temporary_acceptance_roots

CORPUS = Path(__file__).parent / "fixtures" / "automatic_memory_corpus.jsonl"
QUESTIONS = Path(__file__).parent / "fixtures" / "automatic_memory_questions.jsonl"


def test_round5_rejected_activation_is_not_current_truth(tmp_path: Path) -> None:
    with temporary_acceptance_roots(base_directory=tmp_path) as roots:
        envelope = run_quality_gate(CORPUS, QUESTIONS, output_path=roots.output_root / "quality.json", acceptance_roots=roots)
        assert envelope.functional_status == envelope.phase_status == "NOT_EVALUATED"
        assert envelope.evaluation_report is None


def test_round5_report_keeps_unmeasured_4r2_fields_explicit(tmp_path: Path) -> None:
    with temporary_acceptance_roots(base_directory=tmp_path) as roots:
        run_quality_gate(CORPUS, QUESTIONS, output_path=roots.output_root / "quality.json", acceptance_roots=roots)
        payload = json.loads((roots.output_root / "quality.json").read_text(encoding="utf-8"))
        assert payload["mcp_parity"]["status"] == "NOT_MEASURED"
        assert payload["semantic_degradation"]["status"] == "NOT_MEASURED"
        assert payload["phase_status"] == "NOT_EVALUATED"
