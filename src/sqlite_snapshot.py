from __future__ import annotations

import shutil
import sqlite3
import tempfile
from pathlib import Path


def quick_check_snapshot(source: Path, *, timeout: float = 10.0) -> str:
    """Copy a SQLite database and WAL to a temporary directory, then check the copy.

    Opening a WAL database read-only can still create a shared-memory sidecar. The
    temporary snapshot keeps those coordination writes away from the inspected input.
    """

    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(source)

    with tempfile.TemporaryDirectory(prefix="lingji-sqlite-check-") as directory:
        target = Path(directory) / source.name
        shutil.copyfile(source, target)
        source_wal = Path(f"{source}-wal")
        if source_wal.is_file():
            shutil.copyfile(source_wal, Path(f"{target}-wal"))

        uri = f"{target.resolve().as_uri()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=float(timeout))
        try:
            result = connection.execute("PRAGMA quick_check").fetchone()
        finally:
            connection.close()
        return str(result[0]) if result else ""
