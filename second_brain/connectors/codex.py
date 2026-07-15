from __future__ import annotations

import json

from second_brain.db import Database
from second_brain.memory.service import MemoryService
from second_brain.models import CodexTaskRequest
from second_brain.utils import new_id, stable_hash, utc_now


class CodexConnector:
    def __init__(self, database: Database, memories: MemoryService):
        self.database = database
        self.memories = memories

    def record(self, task: CodexTaskRequest) -> dict:
        project_id = self.memories.ensure_project(task.project)
        now = utc_now()
        task_id = task.task_id or new_id()
        source_hash = stable_hash(task.model_dump(mode="json"))
        source_id = new_id()
        with self.database.connect() as connection:
            existing = connection.execute("SELECT id FROM sources WHERE content_hash=?", (source_hash,)).fetchone()
            if existing:
                existing_task = connection.execute("SELECT id FROM tasks WHERE source_id=?", (existing["id"],)).fetchone()
                return {"task_id": existing_task["id"] if existing_task else task_id, "recorded": False, "duplicate": True}
            connection.execute(
                "INSERT INTO sources(id,source_type,source_ref,content_hash,metadata_json,created_at) VALUES(?,?,?,?,?,?)",
                (source_id, "codex_task", task_id, source_hash, "{}", now),
            )
            connection.execute(
                """INSERT INTO tasks(
                    id,project_id,request,status,result,files_json,tests_json,commit_hash,source_id,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    task_id, project_id, task.request, task.status, task.result,
                    json.dumps(task.files_changed, ensure_ascii=False), json.dumps(task.tests, ensure_ascii=False),
                    task.commit_hash, source_id, now, now,
                ),
            )
            for path in task.files_changed:
                connection.execute(
                    "INSERT INTO artifacts(id,task_id,project_id,artifact_type,path,created_at) VALUES(?,?,?,?,?,?)",
                    (new_id(), task_id, project_id, "file_change", path, now),
                )
        lessons = []
        for lesson in task.lessons:
            memory, created = self.memories.create(
                memory_type="LESSON", title=lesson[:60], content=lesson, project=task.project,
                status="pending", importance=0.7, confidence=0.85, source_id=source_id,
            )
            if created:
                lessons.append(memory["id"])
        return {"task_id": task_id, "recorded": True, "duplicate": False, "lesson_candidates": lessons}
