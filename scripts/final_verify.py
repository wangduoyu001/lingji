from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import requests


root = Path(__file__).resolve().parents[1]
with sqlite3.connect(root / "data" / "second_brain.sqlite3") as connection:
    tables = [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
    ]

response = requests.post("http://127.0.0.1:8765/memory/rebuild-qdrant", timeout=180)
response.raise_for_status()
health = requests.get("http://127.0.0.1:8765/health", timeout=10)
health.raise_for_status()

print(
    json.dumps(
        {"tables": tables, "rebuild": response.json(), "health": health.json()},
        ensure_ascii=False,
        indent=2,
    )
)
