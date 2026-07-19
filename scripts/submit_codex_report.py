#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import settings
from src.extraction import build_extraction_pipeline


def load_report(path: str) -> dict:
    if path == "-":
        data = json.load(sys.stdin)
    else:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("Codex report JSON must be an object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a structured Codex work report into LingJi")
    parser.add_argument("report", help="JSON report path, or - to read stdin")
    parser.add_argument("--queue", action="store_true", help="Queue instead of writing immediately")
    parser.add_argument("--force", action="store_true", help="Requeue an identical terminal job")
    args = parser.parse_args()

    report = load_report(args.report)
    pipeline = build_extraction_pipeline(settings)
    if args.queue:
        result = pipeline.enqueue(
            "codex",
            payload=report,
            adapter_name="codex_work_report",
            force=args.force,
        )
    else:
        result = pipeline.execute(
            "codex",
            payload=report,
            adapter_name="codex_work_report",
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
