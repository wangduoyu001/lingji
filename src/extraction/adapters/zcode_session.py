"""Bounded reader for the local ZCode session database.

ZCode keeps every conversation in a single SQLite database
(``~/.zcode/cli/db/db.sqlite``): ``session`` rows carry identity and
timing, ``message`` rows carry role metadata, and ``part`` rows carry the
actual content — only ``type="text"`` parts are conversation transcript.
The adapter opens the snapshot read-only and projects it into the same
structured model the Codex adapters emit; unknown shapes fail closed.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from ..base import ExtractionAdapter
from ..models import (
    ExtractionBatch,
    ExtractionRequest,
    StructuredConversation,
    StructuredMessage,
    StructuredSource,
)

_MAX_INPUT_BYTES = 512 * 1024 * 1024
_MAX_MESSAGE_CHARS = 8000
_MAX_CONVERSATIONS = 500
_MAX_MESSAGES_PER_CONVERSATION = 2000
_AGENT_SCOPE = ("zcode", "lingji-local")


def _millis_to_iso(value: Any) -> str:
    try:
        millis = int(value)
    except (TypeError, ValueError):
        return ""
    if millis <= 0:
        return ""
    return datetime.fromtimestamp(millis / 1000, tz=timezone.utc).isoformat(timespec="seconds")


class ZcodeSessionAdapter(ExtractionAdapter):
    name = "zcode_session"
    version = "1.0.1"
    source_types = ("zcode_session",)

    def can_handle(
        self,
        source_type: str,
        input_path: Path | None,
        payload: Mapping[str, Any],
    ) -> bool:
        del payload
        if source_type not in self.source_types:
            return False
        if not input_path:
            return False
        path = Path(input_path)
        if not path.exists():
            return False
        # 快照产物以内容哈希命名（无后缀），用 SQLite 魔数识别而不是扩展名。
        try:
            with path.open("rb") as handle:
                return handle.read(16).startswith(b"SQLite format 3\x00")
        except OSError:
            return False

    def extract(self, request: ExtractionRequest) -> ExtractionBatch:
        path = Path(request.input_path) if request.input_path else None
        if path is None or not path.exists():
            raise ValueError("ZCode session database snapshot is required")
        if path.stat().st_size > _MAX_INPUT_BYTES:
            raise ValueError("ZCode session database exceeds size limit")
        conversations = tuple(self._conversations(path))
        if not conversations:
            raise ValueError("ZCode session database contains no conversations")
        source = StructuredSource(
            source_type="zcode_session",
            external_id="zcode:cli",
            display_name="ZCode · 本机会话",
            conversations=conversations,
            privacy="private",
            projects=tuple(sorted({project for item in conversations for project in item.projects})),
            agent_scope=_AGENT_SCOPE,
            status="active",
            metadata={
                "raw_reference": f"raw:zcode/cli/db/db.sqlite",
                "adapter_name": self.name,
                "adapter_version": self.version,
                "conversation_count": len(conversations),
            },
        )
        return ExtractionBatch(
            documents=(),
            structured_sources=(source,),
            summary={
                "conversations": len(conversations),
                "messages": sum(len(item.messages) for item in conversations),
            },
        )

    # ------------------------------------------------------------ internals
    def _conversations(self, path: Path) -> list[StructuredConversation]:
        uri = f"file:{path.as_uri()[len('file:'):]}?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=15)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA quick_check").fetchone()
            sessions = connection.execute(
                """
                SELECT id, title, directory, time_created, time_updated
                FROM session
                ORDER BY time_updated DESC, id ASC
                LIMIT ?
                """,
                (_MAX_CONVERSATIONS,),
            ).fetchall()
        except sqlite3.DatabaseError as exc:
            # 结构不符（不是 ZCode 的库）必须 fail-closed 且可归类。
            raise ValueError(f"ZCode session database schema is not recognized: {exc}") from exc
        try:
            output: list[StructuredConversation] = []
            for session_row in sessions:
                conversation = self._conversation(connection, session_row)
                if conversation is not None and conversation.messages:
                    output.append(conversation)
            return output
        except sqlite3.DatabaseError as exc:
            raise ValueError(f"ZCode session database is not readable: {exc}") from exc
        finally:
            connection.close()

    def _conversation(self, connection: sqlite3.Connection, session_row: sqlite3.Row) -> StructuredConversation | None:
        session_id = str(session_row["id"] or "")
        if not session_id:
            return None
        directory = str(session_row["directory"] or "")
        project_id = self._project_id(directory)
        rows = connection.execute(
            """
            SELECT m.id AS message_id, m.data AS message_data, m.time_created AS message_time,
                   p.data AS part_data, p.sequence AS part_sequence
            FROM message m
            JOIN part p ON p.message_id = m.id
            WHERE m.session_id = ? AND json_extract(p.data, '$.type') = 'text'
            ORDER BY m.time_created ASC, p.sequence ASC, p.id ASC
            LIMIT ?
            """,
            (session_id, _MAX_MESSAGES_PER_CONVERSATION * 4),
        ).fetchall()
        messages: list[StructuredMessage] = []
        for row in rows:
            message = self._message(session_id, project_id, row)
            if message is None:
                continue
            # 同一条消息的多个 text part 合并为一条（LLM 分段输出）。
            if messages and messages[-1].external_id == message.external_id:
                previous = messages[-1]
                merged = StructuredMessage(
                    external_id=previous.external_id,
                    role=previous.role,
                    author=previous.author,
                    occurred_at=previous.occurred_at,
                    sequence=previous.sequence,
                    content=f"{previous.content}\n{message.content}".strip()[:_MAX_MESSAGE_CHARS],
                    projects=previous.projects,
                    agent_scope=previous.agent_scope,
                    raw_reference=previous.raw_reference,
                    metadata=previous.metadata,
                )
                messages[-1] = merged
                continue
            messages.append(message)
        if not messages:
            return None
        # sequence 必须会话内唯一（read model 唯一约束含 sequence）；part.sequence
        # 是每条消息内部从 1 重新计数的，直接用会撞唯一键。
        messages = [
            StructuredMessage(
                external_id=item.external_id,
                role=item.role,
                author=item.author,
                occurred_at=item.occurred_at,
                sequence=index + 1,
                content=item.content,
                projects=item.projects,
                agent_scope=item.agent_scope,
                raw_reference=item.raw_reference,
                metadata=item.metadata,
            )
            for index, item in enumerate(messages)
        ]
        if not messages:
            return None
        title = str(session_row["title"] or "").strip() or "ZCode 会话"
        started = messages[0].occurred_at
        ended = messages[-1].occurred_at
        return StructuredConversation(
            external_id=session_id,
            title=title,
            messages=tuple(messages[:_MAX_MESSAGES_PER_CONVERSATION]),
            started_at=started,
            ended_at=ended,
            participants=("owner", "zcode"),
            privacy="private",
            projects=(project_id,),
            agent_scope=_AGENT_SCOPE,
            metadata={
                "directory": directory,
                "message_count": len(messages),
                "session_updated_at": _millis_to_iso(session_row["time_updated"]),
            },
        )

    def _message(
        self,
        session_id: str,
        project_id: str,
        row: sqlite3.Row,
    ) -> StructuredMessage | None:
        try:
            message_data = json.loads(str(row["message_data"] or "{}"))
            part_data = json.loads(str(row["part_data"] or "{}"))
        except (TypeError, ValueError):
            return None
        if not isinstance(message_data, Mapping) or not isinstance(part_data, Mapping):
            return None
        role = str(message_data.get("role") or "").strip().lower()
        if role not in {"user", "assistant"}:
            return None
        text = str(part_data.get("text") or "").strip()
        if not text:
            return None
        if self._is_injected_context(message_data, text):
            return None
        message_id = str(row["message_id"] or "")
        occurred = _millis_to_iso(row["message_time"]) or _millis_to_iso(part_data.get("time", {}).get("start"))
        content = text[:_MAX_MESSAGE_CHARS]
        return StructuredMessage(
            external_id=message_id,
            role="owner" if role == "user" else "assistant",
            author="zcode",
            occurred_at=occurred,
            sequence=int(row["part_sequence"] or 0),
            content=content,
            projects=(project_id,),
            agent_scope=_AGENT_SCOPE,
            raw_reference=f"raw:zcode/cli/db/db.sqlite#{session_id}/{message_id}",
            metadata={
                "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "model_id": str(message_data.get("modelID") or ""),
            },
        )

    @staticmethod
    def _is_injected_context(message_data: Mapping[str, Any], text: str) -> bool:
        # 注入型上下文（AGENTS.md、环境快照等）不是主人说的话，不入记忆流。
        semantics = message_data.get("semantics")
        if isinstance(semantics, Mapping) and str(semantics.get("origin") or "") in {"system", "context"}:
            return True
        return text.startswith("<") and len(text) > 2000 and "environment_context" in text[:500]

    @staticmethod
    def _project_id(directory: str) -> str:
        # 与 Codex 的 project 口径一致：路径 slug（去分隔符）。
        normalized = str(directory or "").strip("/").replace("\\", "/")
        slug = normalized.replace("/", "-").replace("_", "-").lower()
        return f"users-{slug}" if slug else "zcode-local"
