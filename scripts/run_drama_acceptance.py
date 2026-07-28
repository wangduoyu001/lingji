from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from src.config import settings
from src.plugins.drama_intelligence.acceptance import (
    DramaAcceptanceError,
    load_acceptance_questions,
    run_acceptance,
    write_acceptance_report,
)
from src.plugins.drama_intelligence.batch import import_directory
from src.plugins.drama_intelligence.service import DramaService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run source-traceable Drama Memory owner-data acceptance."
    )
    parser.add_argument("--questions", required=True, help="UTF-8 JSONL acceptance dataset")
    parser.add_argument("--scripts", help="Optional directory of real scripts to import first")
    parser.add_argument("--recursive", action="store_true", help="Recursively scan --scripts")
    parser.add_argument("--force-import", action="store_true", help="Force script re-import")
    parser.add_argument("--import-limit", type=int, default=100)
    parser.add_argument(
        "--output-dir",
        default="output/drama-acceptance",
        help="Directory for JSON and Markdown evidence",
    )
    parser.add_argument("--minimum-dramas", type=int, default=10)
    parser.add_argument("--minimum-questions", type=int, default=100)
    parser.add_argument("--retrieval-target", type=float, default=0.85)
    parser.add_argument("--character-target", type=float, default=0.90)
    parser.add_argument("--episode-target", type=float, default=0.85)
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Explicitly allow a non-acceptance workspace. Not recommended.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    service = DramaService(settings)
    try:
        if service.workspace != "acceptance" and not args.allow_production:
            raise DramaAcceptanceError(
                "Owner-data acceptance must run in the acceptance workspace. "
                f"Resolved workspace: {service.workspace!r}"
            )

        import_result = None
        if args.scripts:
            import_result = import_directory(
                service,
                Path(args.scripts),
                recursive=bool(args.recursive),
                limit=int(args.import_limit),
                force=bool(args.force_import),
            )

        questions = load_acceptance_questions(args.questions)
        report = run_acceptance(
            service,
            questions,
            minimum_dramas=args.minimum_dramas,
            minimum_questions=args.minimum_questions,
            retrieval_target=args.retrieval_target,
            character_target=args.character_target,
            episode_target=args.episode_target,
        )
        if import_result is not None:
            report["import"] = import_result
        paths = write_acceptance_report(report, args.output_dir)
        print(
            json.dumps(
                {
                    "overall_pass": report["overall_pass"],
                    "workspace": report["workspace"],
                    "drama_count": report["corpus"]["drama_count"],
                    "question_count": report["dataset"]["question_count"],
                    "metrics": report["metrics"],
                    "gates": report["gates"],
                    "reports": paths,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if report["overall_pass"] else 2
    except (DramaAcceptanceError, OSError, ValueError) as exc:
        print(json.dumps({"overall_pass": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    finally:
        service.close()


if __name__ == "__main__":
    raise SystemExit(main())
