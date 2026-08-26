"""Run the deterministic automatic-memory quality or opt-in scale gate."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.automatic_memory.quality_gate import (
    AutomaticMemoryFunctionalGate,
    run_100k_benchmark,
    run_quality_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    output_root = repo / "output" / "validation"
    output_root.mkdir(parents=True, exist_ok=True)
    if args.scale:
        if os.environ.get("LINGJI_RUN_100K") != "1":
            raise SystemExit("LINGJI_RUN_100K=1 is required for the opt-in 100k scale gate")
        output = args.output or output_root / "automatic-memory-100k.json"
        report = run_100k_benchmark(output_path=output)
        print(f"100k scale report: {output}")
        print(f"messages={report['messages']} imported={report['imported_messages']} cleanup={report['cleanup_result']}")
        return 0 if report.get("imported_messages") == 100_000 and report.get("cleanup_result") == "cleaned" else 1
    fixtures = repo / "tests" / "evaluation" / "fixtures"
    output = args.output or output_root / "automatic-memory-quality.json"
    report = run_quality_gate(
        fixtures / "automatic_memory_corpus.jsonl",
        fixtures / "automatic_memory_questions.jsonl",
        output_path=output,
    )
    status = AutomaticMemoryFunctionalGate.evaluate(report)
    print(f"functional quality report: {output}")
    print(f"recall={report.valid_fact_recall:.2f}% citation={report.citation_accuracy:.2f}% mcp={report.mcp_success_rate:.2f}%")
    print(f"functional_status={status}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
