from __future__ import annotations

import json
from pathlib import Path

from second_brain.config import Settings
from second_brain.db import Database
from second_brain.memory.service import MemoryService
from second_brain.models import ConversationInput
from second_brain.utils import new_id, stable_hash, utc_now


class ChatConnector:
    def __init__(self, database: Database, memories: MemoryService, settings: Settings):
        self.database = database
        self.memories = memories
        self.settings = settings

    def import_path(self, raw_path: str | Path) -> list[dict]:
        path = Path(raw_path).resolve()
        allowed = self.settings.ai_inbox_dir.resolve()
        if path != allowed and allowed not in path.parents:
            raise ValueError(f"Import path must be inside {allowed}")
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        conversations = self._normalize_export(data)
        results = [self.import_conversation(conversation, input_ref=str(path)) for conversation in conversations]
        archive = self.settings.raw_archive_dir / f"{stable_hash(data)}.json"
        if not archive.exists():
            archive.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return results

    def import_conversation(self, conversation: ConversationInput, input_ref: str = "inline") -> dict:
        payload = conversation.model_dump(mode="json")
        content_hash = stable_hash(payload)
        archive = self.settings.raw_archive_dir / f"{content_hash}.json"
        if not archive.exists():
            archive.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        now = utc_now()
        job_id = new_id()
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO import_jobs(id,source_type,input_ref,status,started_at) VALUES(?,?,?,?,?)",
                (job_id, conversation.source, input_ref, "running", now),
            )
            existing = connection.execute(
                "SELECT id FROM conversations WHERE content_hash=?", (content_hash,)
            ).fetchone()
            if existing:
                connection.execute(
                    "UPDATE import_jobs SET status='success',skipped_count=1,finished_at=? WHERE id=?",
                    (utc_now(), job_id),
                )
                return {"job_id": job_id, "conversation_id": existing["id"], "imported": False, "duplicate": True}

        source_hash = stable_hash({"source": conversation.source, "external_id": conversation.conversation_id, "payload": payload})
        source_id = new_id()
        project_id = self.memories.ensure_project(conversation.project)
        conversation_id = new_id()
        try:
            with self.database.connect() as connection:
                existing_source = connection.execute("SELECT id FROM sources WHERE content_hash=?", (source_hash,)).fetchone()
                if existing_source:
                    source_id = existing_source["id"]
                else:
                    connection.execute(
                        "INSERT INTO sources(id,source_type,source_ref,content_hash,metadata_json,created_at) VALUES(?,?,?,?,?,?)",
                        (
                            source_id, conversation.source, input_ref, source_hash,
                            json.dumps(conversation.metadata, ensure_ascii=False), now,
                        ),
                    )
                connection.execute(
                    """INSERT INTO conversations(
                        id,source_id,external_id,title,project_id,started_at,updated_at,content_hash,created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (
                        conversation_id, source_id, conversation.conversation_id, conversation.title, project_id,
                        conversation.created_at, conversation.updated_at, content_hash, now,
                    ),
                )
                for ordinal, message in enumerate(conversation.messages):
                    message_hash = stable_hash({"role": message.role, "content": message.content, "ordinal": ordinal})
                    connection.execute(
                        "INSERT INTO messages(id,conversation_id,external_id,role,content,sent_at,content_hash,ordinal) VALUES(?,?,?,?,?,?,?,?)",
                        (
                            new_id(), conversation_id, message.message_id, message.role, message.content,
                            message.timestamp, message_hash, ordinal,
                        ),
                    )
                connection.execute(
                    "UPDATE import_jobs SET status='success',imported_count=1,finished_at=? WHERE id=?",
                    (utc_now(), job_id),
                )
        except Exception as exc:
            with self.database.connect() as connection:
                connection.execute(
                    "UPDATE import_jobs SET status='failed',error=?,finished_at=? WHERE id=?",
                    (str(exc), utc_now(), job_id),
                )
            raise
        return {
            "job_id": job_id,
            "source_id": source_id,
            "conversation_id": conversation_id,
            "imported": True,
            "duplicate": False,
        }

    @staticmethod
    def _normalize_export(data: object) -> list[ConversationInput]:
        if isinstance(data, dict) and "conversations" in data:
            items = data["conversations"]
        elif isinstance(data, list):
            items = data
        else:
            items = [data]
        normalized: list[ConversationInput] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("messages"), list):
                normalized.append(ConversationInput.model_validate(item))
                continue
            mapping = item.get("mapping")
            if not isinstance(mapping, dict):
                continue
            messages = []
            for node in mapping.values():
                message = node.get("message") if isinstance(node, dict) else None
                if not isinstance(message, dict):
                    continue
                content = message.get("content", {})
                parts = content.get("parts", []) if isinstance(content, dict) else []
                text = "\n".join(str(part) for part in parts if isinstance(part, (str, int, float)))
                author = message.get("author", {})
                if text:
                    messages.append(
                        {
                            "message_id": message.get("id"),
                            "role": author.get("role", "unknown") if isinstance(author, dict) else "unknown",
                            "content": text,
                            "timestamp": str(message.get("create_time")) if message.get("create_time") else None,
                        }
                    )
            normalized.append(
                ConversationInput(
                    conversation_id=item.get("id") or item.get("conversation_id"),
                    source="chatgpt",
                    title=item.get("title") or "ChatGPT conversation",
                    project=item.get("project") or "global",
                    messages=messages,
                    metadata={"export_format": "chatgpt_mapping"},
                )
            )
        return normalized
