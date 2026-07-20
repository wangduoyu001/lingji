#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Install the local LingJi Control Obsidian plugin")
    parser.add_argument("--vault", help="Override VAULT_DIR")
    args = parser.parse_args()

    vault = Path(args.vault).expanduser() if args.vault else settings.vault_path
    source = BASE_DIR / "obsidian-plugin" / "lingji-control"
    target = vault / ".obsidian" / "plugins" / "lingji-control"
    if not source.exists():
        raise FileNotFoundError(source)
    target.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in ("manifest.json", "main.js", "styles.css"):
        source_file = source / name
        target_file = target / name
        temporary = target_file.with_suffix(target_file.suffix + ".tmp")
        shutil.copy2(source_file, temporary)
        temporary.replace(target_file)
        copied.append(str(target_file))
    print("LingJi Control installed:")
    for path in copied:
        print("-", path)
    print("Open Obsidian Settings > Community plugins and enable LingJi Control.")


if __name__ == "__main__":
    main()
