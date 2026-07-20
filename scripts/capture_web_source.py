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
        description="Capture a webpage, article, video-channel share or social post into LingJi"
    )
    parser.add_argument("url", nargs="?", default="", help="Source URL")
    parser.add_argument(
        "--platform",
        default="web",
        choices=["web", "wechat_article", "video_channel", "douyin", "xiaohongshu"],
    )
    parser.add_argument("--title", default="")
    parser.add_argument("--author", default="")
    parser.add_argument("--account-name", default="")
    parser.add_argument("--description", default="")
    parser.add_argument("--published-at", default="")
    parser.add_argument("--duration-seconds", default="")
    parser.add_argument("--cover-url", default="")
    parser.add_argument("--media-url", default="")
    parser.add_argument("--text", default="")
    parser.add_argument("--text-file")
    parser.add_argument("--html-file")
    parser.add_argument("--transcript-file")
    parser.add_argument("--ocr-file")
    parser.add_argument("--json", dest="json_path", help="Read the complete capture payload from JSON")
    parser.add_argument("--project")
    parser.add_argument("--allow-network-fetch", action="store_true")
    parser.add_argument("--queue", action="store_true")
    args = parser.parse_args()

    payload = {}
    if args.json_path:
        loaded = json.loads(Path(args.json_path).expanduser().read_text(encoding="utf-8-sig"))
        if not isinstance(loaded, dict):
            raise ValueError("Capture JSON must contain an object")
        payload.update(loaded)

    def read_optional(path_value: str | None) -> str:
        if not path_value:
            return ""
        return Path(path_value).expanduser().read_text(encoding="utf-8-sig")

    payload.update(
        {
            "url": args.url or payload.get("url", ""),
            "platform": args.platform or payload.get("platform", "web"),
            "title": args.title or payload.get("title", ""),
            "author": args.author or payload.get("author", ""),
            "account_name": args.account_name or payload.get("account_name", ""),
            "description": args.description or payload.get("description", ""),
            "published_at": args.published_at or payload.get("published_at", ""),
            "duration_seconds": args.duration_seconds or payload.get("duration_seconds", ""),
            "cover_url": args.cover_url or payload.get("cover_url", ""),
            "media_url": args.media_url or payload.get("media_url", ""),
            "text": read_optional(args.text_file) or args.text or payload.get("text", ""),
            "html": read_optional(args.html_file) or payload.get("html", ""),
            "transcript": read_optional(args.transcript_file) or payload.get("transcript", ""),
            "ocr_text": read_optional(args.ocr_file) or payload.get("ocr_text", ""),
            "capture_method": "cli",
        }
    )
    if not payload.get("url") and not payload.get("text") and not payload.get("html"):
        raise ValueError("Provide a URL, text, HTML or JSON capture payload")

    source_type = args.platform if args.platform != "web" else "web"
    options = {
        "project_id": args.project or [],
        "allow_network_fetch": bool(args.allow_network_fetch and settings.web_network_fetch_enabled),
        "network_timeout_seconds": settings.web_network_timeout_seconds,
        "max_response_bytes": settings.web_max_response_bytes,
    }
    pipeline = build_extraction_pipeline(settings)
    if args.queue:
        result = pipeline.enqueue(
            source_type,
            payload=payload,
            options=options,
            adapter_name="web_capture",
        )
    else:
        result = pipeline.execute(
            source_type,
            payload=payload,
            options=options,
            adapter_name="web_capture",
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
