from __future__ import annotations

from second_brain.db import Database, rows_to_dicts
from second_brain.utils import new_id, utc_now


class ConflictService:
    def __init__(self, database: Database):
        self.database = database

    def detect_for(self, memory_id: str) -> list[dict]:
        with self.database.connect() as connection:
            memory = connection.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
            if not memory:
                raise KeyError(memory_id)
            candidates = connection.execute(
                """SELECT * FROM memories WHERE id<>? AND project_id=? AND memory_type=?
                AND status IN ('active','pending') AND title=?""",
                (memory_id, memory["project_id"], memory["memory_type"], memory["title"]),
            ).fetchall()
            created = []
            for candidate in candidates:
                if candidate["content_hash"] == memory["content_hash"]:
                    continue
                conflict_id = new_id()
                connection.execute(
                    "INSERT INTO conflicts(id,memory_id,conflicting_memory_id,reason,created_at) VALUES(?,?,?,?,?)",
                    (conflict_id, memory_id, candidate["id"], "Same project/type/title with different content", utc_now()),
                )
                created.append({"id": conflict_id, "conflicting_memory_id": candidate["id"]})
            if created:
                connection.execute("UPDATE memories SET status='conflicted',updated_at=? WHERE id=?", (utc_now(), memory_id))
        return created

    def list_open(self) -> list[dict]:
        with self.database.connect() as connection:
            rows = connection.execute("SELECT * FROM conflicts WHERE status='open' ORDER BY created_at DESC").fetchall()
        return rows_to_dicts(rows)
