"""Fail-closed adapter for owner-selected Generic AI History Inbox files.

This module deliberately has no directory discovery.  A caller must provide one
selected JSON, JSONL, or marked Markdown file; the file itself declares the
versioned History Inbox contract before it is parsed.
"""

from __future__ import annotations

import hashlib
import json
import re
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Mapping

from ..base import ExtractionAdapter
from ..models import (
    ExtractedDocument,
    ExtractionBatch,
    ExtractionRequest,
    StructuredConversation,
    StructuredMessage,
    StructuredSource,
)


HISTORY_SCHEMA = "lingji.history.inbox"
HISTORY_VERSION = "1"
ROLES = frozenset({"user", "assistant", "system", "tool"})
_MARKDOWN_MESSAGE = re.compile(
    r"^##\s+(user|assistant|system|tool)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*$"
)


@dataclass(frozen=True)
class DetectionResult:
    source_kind: str
    schema: str | None
    supported: bool
    reason: str


@dataclass(frozen=True)
class SchemaDetection:
    schema_name: str | None
    schema_version: str | None
    supported: bool
    reason: str


@dataclass(frozen=True)
class CapabilityStatus:
    source_kind: str
    status: Literal["supported", "unsupported", "consent_required"]
    detail: str


class GenericAIHistoryAdapter(ExtractionAdapter):
    name = "generic_ai_history"
    version = "1.0.0"
    approved = True
    source_types = ("generic_ai_history", "history_inbox")
    MAX_INPUT_BYTES = 32 * 1024 * 1024

    def can_handle(
        self,
        source_type: str,
        input_path: Path | None,
        payload: Mapping[str, Any],
    ) -> bool:
        del payload
        return source_type in self.source_types and self.detect(input_path).supported if input_path else False

    def detect(self, path: Path) -> DetectionResult:
        if not path or path.is_dir() or path.is_symlink():
            return DetectionResult("generic_ai_history", None, False, "History Inbox requires one regular selected file")
        try:
            if not stat.S_ISREG(path.stat().st_mode):
                return DetectionResult("generic_ai_history", None, False, "History Inbox requires one regular selected file")
        except OSError as exc:
            return DetectionResult("generic_ai_history", None, False, f"History Inbox file is unavailable: {exc}")
        if path.suffix.lower() not in {".json", ".jsonl", ".md", ".markdown"}:
            return DetectionResult("generic_ai_history", None, False, "History Inbox supports JSON, JSONL, or Markdown only")
        try:
            if path.stat().st_size > self.MAX_INPUT_BYTES:
                raise ValueError("History Inbox file exceeds size limit")
            conversations = self._load(path)
            if not conversations:
                raise ValueError("History Inbox contains no conversations")
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            return DetectionResult("generic_ai_history", None, False, str(exc))
        return DetectionResult("generic_ai_history", HISTORY_SCHEMA, True, "supported History Inbox schema v1")

    def extract(self, request: ExtractionRequest) -> ExtractionBatch:
        path = request.input_path
        if not path:
            raise ValueError("History Inbox path is required")
        detection = self.detect(path)
        if not detection.supported:
            raise ValueError(f"unsupported History Inbox: {detection.reason}")
        raw_input = path.read_bytes()
        source_scope = self._digest(raw_input.hex())
        automatic_source_id = ""
        if request.options.get("automatic_memory"):
            automatic_source_id = str(request.payload.get("source_id") or "").strip()
            if automatic_source_id:
                # Automatic snapshots of one authorized source must retain a
                # stable identity when the export bytes change. The raw
                # snapshot hash remains provenance, while source/conversation/
                # message rows are upserted by their stable external IDs.
                source_scope = self._digest(f"automatic-memory:{automatic_source_id}")
        provenance = {"source_scope": source_scope}
        if automatic_source_id:
            provenance["automatic_memory_source_id"] = automatic_source_id
        conversations = self._load(path)
        documents: list[ExtractedDocument] = []
        structured: list[StructuredConversation] = []
        for conversation in conversations:
            conversation_id = conversation["conversation_id"]
            stable = f"LJ-GENERIC-HISTORY-{source_scope}-{self._digest(conversation_id)}"
            messages = tuple(
                StructuredMessage(
                    external_id=f"generic-history:{source_scope}:message:{item['message_id']}",
                    role=item["role"],
                    content=item["content"],
                    sequence=index,
                    occurred_at=item["timestamp"],
                    metadata={"conversation_id": conversation_id, "message_id": item["message_id"], **provenance},
                )
                for index, item in enumerate(conversation["messages"])
            )
            body_lines = [
                f"# {conversation['title']}",
                "",
                f"> History Inbox conversation ID: `{conversation_id}`",
                "",
            ]
            for index, item in enumerate(conversation["messages"], 1):
                body_lines.extend(
                    [
                        f"## {index}. {item['role']} · {item['timestamp']}",
                        "",
                        item["content"],
                        "",
                    ]
                )
            documents.append(
                ExtractedDocument(
                    stable_id=stable,
                    title=conversation["title"],
                    body="\n".join(body_lines),
                    source_type="generic_ai_history",
                    destination="source_archive",
                    external_id=f"generic-history:{source_scope}:conversation:{conversation_id}",
                    created_at=conversation["messages"][0]["timestamp"],
                    updated_at=conversation["messages"][-1]["timestamp"],
                    metadata={
                        "conversation_id": conversation_id,
                        **provenance,
                        "message_ids": [item["message_id"] for item in conversation["messages"]],
                        "schema": HISTORY_SCHEMA,
                        "schema_version": HISTORY_VERSION,
                        "history_inbox": True,
                    },
                )
            )
            structured.append(
                StructuredConversation(
                    external_id=f"generic-history:{source_scope}:conversation:{conversation_id}",
                    title=conversation["title"],
                    messages=messages,
                    started_at=messages[0].occurred_at,
                    ended_at=messages[-1].occurred_at,
                    participants=tuple(dict.fromkeys(item.role for item in messages)),
                    metadata={"schema": HISTORY_SCHEMA, "schema_version": HISTORY_VERSION, **provenance},
                )
            )
        return ExtractionBatch(
            documents=tuple(documents),
            structured_sources=(
                StructuredSource(
                    source_type="generic_ai_history",
                    external_id="generic-history-source-" + source_scope,
                    display_name="Generic AI History Inbox",
                    conversations=tuple(structured),
                    metadata={"schema": HISTORY_SCHEMA, "schema_version": HISTORY_VERSION, **provenance},
                ),
            ),
            summary={"conversations_found": len(documents), "documents_created": len(documents)},
        )

    def _load(self, path: Path) -> list[dict[str, Any]]:
        suffix = path.suffix.lower()
        if suffix == ".json":
            return self._json_conversations(json.loads(path.read_text(encoding="utf-8-sig")))
        if suffix == ".jsonl":
            return self._jsonl_conversations(path.read_text(encoding="utf-8-sig"))
        return self._markdown_conversations(path.read_text(encoding="utf-8-sig"))

    def _json_conversations(self, payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, dict) or not self._header(payload):
            raise ValueError("unsupported History Inbox JSON header")
        raw = payload.get("conversations")
        if not isinstance(raw, list):
            raise ValueError("History Inbox JSON requires conversations")
        conversations = [self._conversation(item) for item in raw]
        self._validate_unique(conversations)
        return conversations

    def _jsonl_conversations(self, text: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for line_number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid History Inbox JSONL at line {line_number}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"History Inbox JSONL line {line_number} is not an object")
            rows.append(row)
        if not rows or not self._header(rows[0]):
            raise ValueError("unsupported History Inbox JSONL header")
        current: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        for row in rows[1:]:
            kind = row.get("type")
            if kind == "conversation":
                conversation_id = self._text(row.get("conversation_id"), "conversation_id")
                if conversation_id in current:
                    raise ValueError("duplicate History Inbox conversation")
                current[conversation_id] = {"conversation_id": conversation_id, "title": self._text(row.get("title"), "title"), "messages": []}
                order.append(conversation_id)
            elif kind == "message":
                conversation_id = self._text(row.get("conversation_id"), "conversation_id")
                if conversation_id not in current:
                    raise ValueError("History Inbox message has no preceding conversation")
                current[conversation_id]["messages"].append(self._message(row))
            else:
                raise ValueError("unknown History Inbox JSONL record type")
        conversations = [self._conversation(current[key]) for key in order]
        self._validate_unique(conversations)
        return conversations

    def _markdown_conversations(self, text: str) -> list[dict[str, Any]]:
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            raise ValueError("History Inbox Markdown requires a marked frontmatter header")
        try:
            end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
        except StopIteration as exc:
            raise ValueError("History Inbox Markdown frontmatter is incomplete") from exc
        header: dict[str, str] = {}
        for line in lines[1:end]:
            if ":" not in line:
                raise ValueError("invalid History Inbox Markdown frontmatter")
            key, value = line.split(":", 1)
            header[key.strip()] = value.strip().strip('"\'')
        if header.get("history_inbox", "").lower() != "true" or not self._header(header):
            raise ValueError("unsupported History Inbox Markdown header")
        conversation_id = self._text(header.get("conversation_id"), "conversation_id")
        title = self._text(header.get("title"), "title")
        messages: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        for line in lines[end + 1 :]:
            match = _MARKDOWN_MESSAGE.match(line.strip())
            if match:
                if current is not None:
                    current["content"] = "\n".join(current.pop("_lines")).strip()
                    messages.append(self._message(current))
                current = {
                    "role": match.group(1),
                    "timestamp": match.group(2),
                    "message_id": match.group(3),
                    "_lines": [],
                }
            elif current is not None:
                if line.strip().startswith("#"):
                    raise ValueError("History Inbox Markdown contains an unknown message boundary")
                current["_lines"].append(line)
            elif line.strip():
                raise ValueError("History Inbox Markdown content precedes first message")
        if current is not None:
            current["content"] = "\n".join(current.pop("_lines")).strip()
            messages.append(self._message(current))
        conversations = [self._conversation({"conversation_id": conversation_id, "title": title, "messages": messages})]
        self._validate_unique(conversations)
        return conversations

    @staticmethod
    def _header(value: Mapping[str, Any]) -> bool:
        schema = str(value.get("schema") or "")
        version = str(value.get("schema_version") or "")
        return schema == HISTORY_SCHEMA and version == HISTORY_VERSION

    def _conversation(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("History Inbox conversation is not an object")
        conversation_id = self._text(value.get("conversation_id"), "conversation_id")
        title = self._text(value.get("title"), "title")
        messages = value.get("messages")
        if not isinstance(messages, list) or not messages:
            raise ValueError("History Inbox conversation requires messages")
        normalized = [self._message(item) for item in messages]
        timestamps = [datetime.fromisoformat(item["timestamp"]) for item in normalized]
        if timestamps != sorted(timestamps):
            raise ValueError("History Inbox message order is not chronological")
        return {"conversation_id": conversation_id, "title": title, "messages": normalized}

    @staticmethod
    def _message(value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            raise ValueError("History Inbox message is not an object")
        message_id = GenericAIHistoryAdapter._text(value.get("message_id"), "message_id")
        role = GenericAIHistoryAdapter._text(value.get("role"), "role").lower()
        if role not in ROLES:
            raise ValueError("History Inbox message role is unsupported")
        content = GenericAIHistoryAdapter._text(value.get("content"), "content")
        timestamp = GenericAIHistoryAdapter._text(value.get("timestamp"), "timestamp")
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("History Inbox message timestamp is invalid") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("History Inbox message timestamp must be timezone-aware")
        normalized_timestamp = parsed.astimezone(timezone.utc).isoformat(timespec="seconds")
        return {"message_id": message_id, "role": role, "content": content, "timestamp": normalized_timestamp}

    @staticmethod
    def _validate_unique(conversations: list[dict[str, Any]]) -> None:
        conversation_ids: set[str] = set()
        message_ids: set[str] = set()
        for conversation in conversations:
            conversation_id = conversation["conversation_id"]
            if conversation_id in conversation_ids:
                raise ValueError(f"Duplicate History Inbox conversation ID: {conversation_id}")
            conversation_ids.add(conversation_id)
            for message in conversation["messages"]:
                message_id = message["message_id"]
                if message_id in message_ids:
                    raise ValueError(f"Duplicate History Inbox message ID: {message_id}")
                message_ids.add(message_id)

    @staticmethod
    def _text(value: Any, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"History Inbox {field} is required")
        return value.strip()

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24].upper()


__all__ = [
    "CapabilityStatus",
    "DetectionResult",
    "GenericAIHistoryAdapter",
    "SchemaDetection",
]
