"""Run the deterministic automatic-memory quality or opt-in scale gate."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.automatic_memory.quality_gate import (
    AcceptanceCleanupError,
    cleanup_failure_envelope,
    publish_quality_envelope,
    run_100k_benchmark,
    run_quality_gate,
    temporary_acceptance_roots,
    run_release_preflight,
    verify_acceptance_cleanup,
    QualityScaleBlockedError,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", action="store_true")
    parser.add_argument("--check-4r2", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    output_root = repo / "output" / "validation"
    output_root.mkdir(parents=True, exist_ok=True)
    if args.check_4r2:
        try:
            run_release_preflight(None)
        except QualityScaleBlockedError as exc:
            raise SystemExit(str(exc)) from exc
        return 0
    if args.scale:
        if os.environ.get("LINGJI_RUN_100K") != "1":
            raise SystemExit("LINGJI_RUN_100K=1 is required for the opt-in 100k scale gate")
        output = args.output or output_root / "automatic-memory-100k.json"
        report = run_100k_benchmark(output_path=output)
        print(f"100k scale report: {output}")
        print(f"messages={report['messages']} imported={report['imported_messages']} cleanup={report['cleanup_result']}")
        return 0 if report.get("imported_messages") == 100_000 and report.get("cleanup_result") == "cleaned" else 1
    fixtures = repo / "tests" / "evaluation" / "fixtures"
    output = (args.output or output_root / "automatic-memory-quality.json").expanduser().resolve()
    try:
        output.relative_to(output_root.resolve())
    except ValueError as exc:
        raise SystemExit("quality output must remain beneath repository output/validation") from exc
    envelope = None
    roots = None
    try:
        with temporary_acceptance_roots() as roots:
            envelope = run_quality_gate(
                fixtures / "automatic_memory_corpus.jsonl",
                fixtures / "automatic_memory_questions.jsonl",
                output_path=roots.output_root / "automatic-memory-quality.json",
                acceptance_roots=roots,
            )
        verify_acceptance_cleanup(roots)
    except AcceptanceCleanupError as exc:
        envelope = cleanup_failure_envelope(envelope, exc)
    if envelope is None:
        raise SystemExit("quality runner did not produce an envelope")
    publish_quality_envelope(envelope, repository_output_path=output)
    print(f"functional quality report: {output}")
    print(f"functional_status={envelope.functional_status}")
    return 0 if envelope.functional_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
