#!/usr/bin/env python3
"""Initialize the LingJi single Obsidian vault without moving existing notes."""
import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import settings
from src.memory import VaultLayout


def main():
    parser = argparse.ArgumentParser(description="Initialize LingJi single-vault folders")
    parser.add_argument("--vault", help="Override the vault path from .env")
    args = parser.parse_args()

    root = Path(args.vault).expanduser() if args.vault else settings.vault_path
    layout = VaultLayout(root)
    created = layout.ensure()
    result = layout.status()
    result["created"] = [str(path) for path in created]
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
