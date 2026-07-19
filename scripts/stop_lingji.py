#!/usr/bin/env python3
"""Stop only the LingJi service process recorded in storage/lingji.pid."""
import os
import signal
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import settings


def main():
    pid_file = settings.storage_path / "lingji.pid"
    if not pid_file.exists():
        print("LingJi PID file does not exist; the service may already be stopped.")
        return 0
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
    except ValueError:
        print(f"Invalid PID file: {pid_file}")
        return 1

    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Stop signal sent to LingJi process {pid}.")
    except ProcessLookupError:
        print(f"LingJi process {pid} is no longer running.")
    except PermissionError:
        print(f"Permission denied while stopping LingJi process {pid}.")
        return 1
    finally:
        try:
            pid_file.unlink(missing_ok=True)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
