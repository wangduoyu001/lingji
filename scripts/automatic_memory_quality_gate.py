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
    load_quality_readiness,
    verify_acceptance_cleanup,
    QualityScaleBlockedError,
    QualityPublicationError,
    runner_failure_envelope,
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
            readiness = load_quality_readiness(output_root / "automatic-memory-quality.json")
            run_release_preflight(readiness)
        except QualityScaleBlockedError as exc:
            raise SystemExit(str(exc)) from exc
        return 0
    if args.scale:
        if os.environ.get("LINGJI_RUN_100K") != "1":
            raise SystemExit("LINGJI_RUN_100K=1 is required for the opt-in 100k scale gate")
        output = args.output or output_root / "automatic-memory-100k.json"
        report = run_100k_benchmark(output_path=output, readiness_path=output_root / "automatic-memory-quality.json")
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
        if envelope is not None:
            from dataclasses import replace
            envelope = replace(envelope, cleanup_inventory=dict(roots.cleanup_inventory or {}))
    except AcceptanceCleanupError as exc:
        envelope = cleanup_failure_envelope(envelope, exc, roots=roots)
    except Exception:
        # Setup failures occur before a tracker exists; runner failures are
        # already normalized by run_quality_gate. Keep this outer boundary
        # sanitized so no traceback or stale PASS is presented.
        envelope = runner_failure_envelope("root" if roots is None else "cleanup", roots=roots)
    if envelope is None:
        print("QUALITY_RUNNER_FAILED", file=sys.stderr)
        return 1
    try:
        publish_quality_envelope(envelope, repository_output_path=output)
    except QualityPublicationError as exc:
        print(f"QUALITY_PUBLICATION_{exc.code}", file=sys.stderr)
        return 1
    except Exception:
        print("QUALITY_PUBLICATION_FAILED", file=sys.stderr)
        return 1
    print(f"functional quality report: {output}")
    print(f"functional_status={envelope.functional_status}")
    print(
        "frozen_questions="
        f"{len(envelope.question_diagnostics)} "
        f"categories={len(envelope.grouped_question_metrics)}"
    )
    return 0 if envelope.functional_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
