#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import settings
from src.memory import VaultLayout
from src.skills import SkillRegistry
from src.storage import StateDatabase


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync SKILL.md manifests into LingJi's Obsidian Skill registry"
    )
    parser.add_argument("paths", nargs="*", help="Directories containing SKILL.md files")
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()

    roots = [Path(value).expanduser() for value in args.paths] or settings.skill_sync_paths
    if not roots:
        raise ValueError("Provide at least one Skill directory or set SKILL_AUTO_SYNC_ROOTS")

    layout = VaultLayout(settings.vault_path)
    layout.ensure()
    registry = SkillRegistry(layout, StateDatabase(settings.state_db_path))
    results = []
    for root in roots:
        results.append(registry.sync_directory(root, limit=args.limit))
    print(
        json.dumps(
            {"roots": [str(root) for root in roots], "results": results, "status": registry.status()},
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
