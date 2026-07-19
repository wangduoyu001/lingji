from __future__ import annotations

import sys
import tempfile
import threading
from pathlib import Path

from src.retrieval.memory_db import MemoryDatabase
from src.scheduler.cron import CronScheduler
from src.storage.state_db import StateDatabase


def delete_sqlite_files(path: Path) -> None:
    for candidate in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
        if candidate.exists():
            candidate.unlink()


def main() -> int:
    try:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_path = root / "memory.db"
            for _ in range(20):
                database = MemoryDatabase(memory_path)
                result = database.integrity_check()
                if not result.get("healthy"):
                    raise RuntimeError(f"Memory database integrity failed: {result}")
                delete_sqlite_files(memory_path)

            state_path = root / "state.db"
            state_db = StateDatabase(state_path)
            started = threading.Event()
            release = threading.Event()

            def runner(_name: str) -> None:
                started.set()
                release.wait(timeout=2)

            scheduler = CronScheduler(state_db, poll_seconds=0.05, max_workers=1)
            scheduler.add_job("startup", 1, run_on_start=True)
            scheduler.start(runner)
            if not started.wait(timeout=2):
                raise RuntimeError("Scheduled lifecycle demo job did not start")
            release.set()
            scheduler.stop()
            delete_sqlite_files(state_path)

        print("Lifecycle test passed - 20 database cycles and scheduler shutdown are file-deletable")
        return 0
    except Exception as exc:
        print(f"Lifecycle test failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
