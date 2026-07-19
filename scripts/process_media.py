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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract local media metadata and optionally create audio/keyframe derivatives"
    )
    parser.add_argument("path", help="Local video or audio file")
    parser.add_argument("--title", default="")
    parser.add_argument("--project")
    parser.add_argument("--transcript")
    parser.add_argument("--ocr")
    parser.add_argument("--visual-notes")
    parser.add_argument("--extract-audio", action="store_true")
    parser.add_argument("--extract-keyframes", action="store_true")
    parser.add_argument("--keyframe-interval", type=float, default=30.0)
    parser.add_argument("--max-keyframes", type=int, default=120)
    parser.add_argument("--queue", action="store_true")
    args = parser.parse_args()

    media_path = Path(args.path).expanduser()
    if not media_path.exists():
        raise FileNotFoundError(media_path)
    payload = {"title": args.title or media_path.stem}
    options = {
        "project_id": args.project or [],
        "transcript_path": args.transcript or "",
        "ocr_path": args.ocr or "",
        "visual_notes_path": args.visual_notes or "",
        "extract_audio": args.extract_audio,
        "extract_keyframes": args.extract_keyframes,
        "keyframe_interval_seconds": args.keyframe_interval,
        "max_keyframes": args.max_keyframes,
    }
    pipeline = build_extraction_pipeline(settings)
    if args.queue:
        result = pipeline.enqueue(
            "media",
            input_path=media_path,
            payload=payload,
            options=options,
            adapter_name="media_local",
        )
    else:
        result = pipeline.execute(
            "media",
            input_path=media_path,
            payload=payload,
            options=options,
            adapter_name="media_local",
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
