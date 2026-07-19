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


def main() -> int:
    parser = argparse.ArgumentParser(description="Import an official ChatGPT ZIP/JSON export")
    parser.add_argument("path", help="Path to export ZIP, JSON, or extracted export directory")
    parser.add_argument("--project", default="", help="Optional LingJi project ID")
    parser.add_argument("--enqueue-only", action="store_true", help="Do not process the job now")
    parser.add_argument("--force", action="store_true", help="Requeue a completed/failed identical job")
    args = parser.parse_args()

    pipeline = build_extraction_pipeline(settings)
    job = pipeline.enqueue(
        "chatgpt",
        input_path=args.path,
        options={"project_id": args.project or []},
        adapter_name="chatgpt_export",
        force=args.force,
    )
    result = job if args.enqueue_only else pipeline.process_job(job["job_id"])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
