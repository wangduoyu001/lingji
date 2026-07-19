#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.acceptance import AcceptanceChecker
from src.acceptance_reports import AcceptanceReportStore, render_markdown
from src.config import Settings

__all__ = ["AcceptanceChecker", "AcceptanceReportStore", "render_markdown"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only LingJi real environment acceptance checks")
    parser.add_argument("--vault", help="Override Vault path for this check")
    parser.add_argument("--storage", help="Override storage path for reports and existing databases")
    parser.add_argument("--backup", help="Override backup path for this check")
    parser.add_argument("--chatgpt-export", help="Optional ChatGPT ZIP/JSON/directory")
    parser.add_argument("--media", help="Optional real media sample")
    parser.add_argument("--output", help="Report directory; defaults to storage/reports/acceptance")
    parser.add_argument("--no-deep-zip-check", action="store_true", help="Skip full ZIP CRC scan")
    parser.add_argument("--no-input-hash", action="store_true", help="Use metadata fingerprints without file SHA-256")
    args = parser.parse_args()

    values: dict[str, Any] = {"vault_auto_init": False}
    if args.vault:
        values["vault_dir"] = args.vault
    if args.storage:
        values["storage_dir"] = args.storage
    if args.backup:
        values["backup_dir"] = args.backup
    settings = Settings(**values)
    checker = AcceptanceChecker(
        settings,
        chatgpt_export=Path(args.chatgpt_export).expanduser() if args.chatgpt_export else None,
        media_path=Path(args.media).expanduser() if args.media else None,
        deep_zip_check=not args.no_deep_zip_check,
        hash_inputs=not args.no_input_hash,
    )
    report = checker.run()
    output = Path(args.output).expanduser() if args.output else settings.storage_path / "reports" / "acceptance"
    saved = AcceptanceReportStore(output).save(report)
    print(json.dumps(saved, ensure_ascii=False, indent=2, default=str))
    return 1 if report["error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
