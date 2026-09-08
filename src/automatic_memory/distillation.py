"""Full-auto knowledge distillation for the automatic memory layer.

全自动知识提炼：把每段对话交给本机 Ollama 模型，提炼成一句话总结 + 要点 +
分类，存进 lingji_memory.db（可重建派生层，原始消息始终是权威）。

- 无需任何人工点击：daemon 循环有界推进（每轮 limit 段对话）。
- 幂等：以对话消息内容摘要为键；消息变化（新消息追加）时自动重提炼并递增
  revision，旧结论可由 revision/updated_at 体现。
- 失败隔离：Ollama 不可用、模型缺失、JSON 解析失败都只记录状态，绝不影响
  扫描与向量化。
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any

TRANSCRIPT_CHAR_BUDGET = 6000
TRANSCRIPT_MESSAGE_CAP = 80
_CHAT_TIMEOUT_SECONDS = 300.0
_TAGS_TIMEOUT_SECONDS = 5.0
_EMBEDDING_MODEL_HINTS = ("embed", "bge", "minilm", "e5")
_NON_FINITE_JSON = re.compile(r",\s*([\]}])")


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _parse_model_json(raw: str) -> dict[str, Any] | None:
    """Best-effort parse of the model's JSON answer (handles fences/prose)."""
    text = str(raw or "").strip()
    if not text:
        return None
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    candidate = text[start : end + 1]
    candidate = _NON_FINITE_JSON.sub(r"\1", candidate)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


class KnowledgeDistiller:
    """把记忆层对话提炼成结构化知识要点（本机模型、幂等、有界、全自动）。"""

    def __init__(self, settings: Any, *, base_url: str | None = None, model: str | None = None):
        self.settings = settings
        self.base_url = str(base_url or getattr(settings, "ollama_base_url", "http://127.0.0.1:11434")).rstrip("/")
        configured = str(model if model is not None else getattr(settings, "distill_model", "") or "").strip()
        self.configured_model = configured
        self._model: str | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ db
    def _memory_db(self) -> Path | None:
        # 注意：Path("") 会规范化为 "."，必须先判断原始字符串。
        raw = str(getattr(self.settings, "memory_db_path", "") or "").strip()
        return Path(raw) if raw else None

    def _db_available(self) -> bool:
        path = self._memory_db()
        return path is not None and path.exists()

    def _connect(self) -> sqlite3.Connection:
        path = self._memory_db()
        assert path is not None, "memory db path must be available before connect"
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS distilled_knowledge (
                conversation_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                key_points_json TEXT NOT NULL,
                category TEXT NOT NULL,
                model TEXT NOT NULL,
                messages_digest TEXT NOT NULL,
                message_count INTEGER NOT NULL DEFAULT 0,
                revision INTEGER NOT NULL DEFAULT 1,
                occurred_at TEXT,
                status TEXT NOT NULL DEFAULT 'ready',
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()

    # ------------------------------------------------------------ model io
    def _available_models(self) -> list[tuple[str, int]]:
        """返回 [(模型名, 体积字节)]；体积用于优先选小模型（提炼无需大模型）。"""
        try:
            import urllib.request

            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=_TAGS_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
            models = []
            for item in payload.get("models", []):
                name = str(item.get("name") or "")
                if name:
                    try:
                        size = int(item.get("size") or 0)
                    except (TypeError, ValueError):
                        size = 0
                    models.append((name, size))
            return models
        except Exception:
            return []

    def _designed_defaults(self) -> list[str]:
        """原设计的默认提炼模型（小模型）：llm_model → fallback_llm。"""
        defaults = []
        for attr in ("llm_model", "fallback_llm"):
            value = str(getattr(self.settings, attr, "") or "").strip()
            if value:
                defaults.append(value)
        return defaults

    def _resolve_model(self) -> str | None:
        if self._model:
            return self._model
        installed = self._available_models()
        if not installed:
            return None
        names = [name for name, _size in installed]

        def match(name: str) -> str | None:
            if name in names:
                return name
            base = name.split(":")[0]
            return next((candidate for candidate in names if candidate.split(":")[0] == base), None)

        # 1) 显式配置的提炼模型
        if self.configured_model:
            found = match(self.configured_model)
            if found:
                self._model = found
                return self._model
        # 2) 原设计默认（小模型优先于大模型）
        for default in self._designed_defaults():
            found = match(default)
            if found:
                self._model = found
                return self._model
        # 3) 兜底：已安装的 chat 模型里选体积最小的（摘要任务不需要大模型）
        chat = [(name, size) for name, size in installed if not any(hint in name.lower() for hint in _EMBEDDING_MODEL_HINTS)]
        if not chat:
            return None
        chat.sort(key=lambda entry: (entry[1], entry[0]))
        self._model = chat[0][0]
        return self._model

    def _build_prompt(self, title: str, transcript: str) -> list[dict[str, str]]:
        system = (
            "你是记忆提炼器。阅读一段用户与AI的对话，提炼成知识要点。"
            '只返回 JSON 对象：{"summary": "一句话总结这段对话产出了什么结论/决定/事实", '
            '"key_points": ["要点1", "要点2", "要点3"], "category": "项目|技术|决策|问题|其他"}。'
            "key_points 用短句，每条不超过40字，只保留有信息量的事实，不要寒暄。"
        )
        user = f"对话标题：{title}\n\n对话内容：\n{transcript}"
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def _chat(self, model: str, messages: list[dict[str, str]]) -> str:
        import urllib.request

        payload = json.dumps(
            {
                "model": model,
                "messages": messages,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.2, "num_ctx": 8192},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=_CHAT_TIMEOUT_SECONDS) as response:
            body = json.loads(response.read().decode("utf-8"))
        return str((body.get("message") or {}).get("content") or "")

    # ------------------------------------------------------------- rows
    def _pending_conversations(self, conn: sqlite3.Connection, limit: int) -> list[dict[str, Any]]:
        # 导入是 append-only：消息数变化即代表对话有新内容，需要重提炼。
        rows = conn.execute(
            """
            SELECT c.conversation_id, c.source_id, c.title, c.started_at, c.message_count
            FROM conversation_records c
            LEFT JOIN distilled_knowledge d ON d.conversation_id = c.conversation_id
            WHERE d.conversation_id IS NULL
               OR d.status != 'ready'
               OR d.message_count != (
                   SELECT COUNT(*) FROM message_records m WHERE m.conversation_id = c.conversation_id
               )
            ORDER BY c.started_at DESC, c.conversation_id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def _conversation_digest(self, conn: sqlite3.Connection, conversation_id: str) -> str | None:
        rows = conn.execute(
            "SELECT content_hash FROM message_records WHERE conversation_id = ? ORDER BY occurred_at ASC, sequence ASC",
            (conversation_id,),
        ).fetchall()
        if not rows:
            return None
        return hashlib.sha256("\n".join(str(row["content_hash"]) for row in rows).encode("utf-8")).hexdigest()

    # ------------------------------------------------------------- public
    def stats(self) -> dict[str, Any]:
        if not self._db_available():
            return {"total": 0, "ready": 0, "pending": 0, "by_category": {}, "model": None, "available": False}
        with self._connect() as conn:
            self._ensure_schema(conn)
            total_convs = int(conn.execute("SELECT COUNT(*) FROM conversation_records").fetchone()[0])
            ready = int(conn.execute("SELECT COUNT(*) FROM distilled_knowledge WHERE status = 'ready'").fetchone()[0])
            by_category: dict[str, int] = {}
            for row in conn.execute(
                "SELECT category, COUNT(*) AS n FROM distilled_knowledge WHERE status = 'ready' GROUP BY category"
            ):
                by_category[str(row["category"])] = int(row["n"])
        return {
            "total": total_convs,
            "ready": ready,
            "pending": max(0, total_convs - ready),
            "by_category": by_category,
            "model": self._model or self._resolve_model(),
            "available": self._model is not None or self._resolve_model() is not None,
        }

    def list_entries(
        self,
        *,
        limit: int = 30,
        offset: int = 0,
        category: str | None = None,
        query: str | None = None,
        order: str = "occurred",
    ) -> dict[str, Any]:
        if not self._db_available():
            return {"items": [], "pagination": {"total": 0, "has_more": False}}
        clauses: list[str] = ["status = 'ready'"]
        params: list[Any] = []
        if category:
            clauses.append("category = ?")
            params.append(category)
        if query and query.strip():
            like = f"%{query.strip()}%"
            clauses.append("(title LIKE ? OR summary LIKE ? OR key_points_json LIKE ?)")
            params.extend([like, like, like])
        where = " AND ".join(clauses)
        order_sql = (
            "ORDER BY updated_at DESC, conversation_id ASC"
            if order == "updated"
            else "ORDER BY COALESCE(occurred_at, created_at) DESC, conversation_id ASC"
        )
        with self._connect() as conn:
            self._ensure_schema(conn)
            total = int(conn.execute(f"SELECT COUNT(*) FROM distilled_knowledge WHERE {where}", params).fetchone()[0])
            rows = conn.execute(
                f"""
                SELECT conversation_id, source_id, title, summary, key_points_json, category,
                       model, revision, occurred_at, created_at, updated_at
                FROM distilled_knowledge
                WHERE {where}
                {order_sql}
                LIMIT ? OFFSET ?
                """,
                [*params, int(limit), int(offset)],
            ).fetchall()
        items = []
        for row in rows:
            try:
                key_points = json.loads(str(row["key_points_json"]))
            except json.JSONDecodeError:
                key_points = []
            items.append(
                {
                    "conversation_id": row["conversation_id"],
                    "title": row["title"],
                    "summary": row["summary"],
                    "key_points": [str(point) for point in key_points if str(point).strip()],
                    "category": row["category"],
                    "model": row["model"],
                    "revision": int(row["revision"]),
                    "occurred_at": row["occurred_at"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )
        return {"items": items, "pagination": {"total": total, "has_more": offset + len(items) < total}}

    def run_once(self, limit: int = 2) -> dict[str, Any]:
        """提炼至多 limit 段对话；返回进度统计。全自动、可重复调用。"""
        with self._lock:
            return self._run_once_locked(limit)

    def _run_once_locked(self, limit: int) -> dict[str, Any]:
        if not self._db_available():
            return {"status": "empty", "distilled": 0, "failed": 0, **self.stats()}
        model = self._resolve_model()
        if model is None:
            return {"status": "model_unavailable", "distilled": 0, "failed": 0, **self.stats()}
        distilled = 0
        failed = 0
        with self._connect() as conn:
            self._ensure_schema(conn)
            pending = self._pending_conversations(conn, max(1, int(limit)))
            for conversation in pending:
                conversation_id = str(conversation["conversation_id"])
                try:
                    outcome = self._distill_one(conn, model, conversation)
                except Exception as exc:  # 单段失败不阻塞本轮其余对话
                    self._record_failure(conn, conversation_id, str(exc))
                    failed += 1
                    continue
                if outcome:
                    distilled += 1
                else:
                    failed += 1
        return {"status": "ok", "distilled": distilled, "failed": failed, **self.stats()}

    def _distill_one(self, conn: sqlite3.Connection, model: str, conversation: dict[str, Any]) -> bool:
        conversation_id = str(conversation["conversation_id"])
        title = str(conversation["title"] or "未命名对话")
        existing = conn.execute(
            "SELECT messages_digest, revision FROM distilled_knowledge WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        digest = self._conversation_digest(conn, conversation_id)
        if digest is None:
            return False
        if existing is not None and str(existing["messages_digest"]) == digest and str(existing["status"] if "status" in existing.keys() else "ready") == "ready":
            return True  # 已是最新，视为成功
        messages, _digest_used, message_count = self._transcript_payload(conn, conversation_id)
        answer = self._chat(model, self._build_prompt(title, self._render_transcript(messages)))
        parsed = _parse_model_json(answer)
        if parsed is None or not str(parsed.get("summary") or "").strip():
            self._record_failure(conn, conversation_id, "模型输出无法解析为知识要点")
            return False
        summary = str(parsed.get("summary")).strip()
        raw_points = parsed.get("key_points")
        if isinstance(raw_points, str):
            key_points = [segment.strip() for segment in re.split(r"[;；\n]", raw_points) if segment.strip()]
        elif isinstance(raw_points, list):
            key_points = [str(point).strip() for point in raw_points if str(point).strip()]
        else:
            key_points = []
        category = str(parsed.get("category") or "其他").strip() or "其他"
        now = _now()
        revision = 1 if existing is None else int(existing["revision"]) + 1
        conn.execute(
            """
            INSERT INTO distilled_knowledge (
                conversation_id, source_id, title, summary, key_points_json, category,
                model, messages_digest, message_count, revision, occurred_at,
                status, last_error, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ready', NULL, ?, ?)
            ON CONFLICT(conversation_id) DO UPDATE SET
                title = excluded.title,
                summary = excluded.summary,
                key_points_json = excluded.key_points_json,
                category = excluded.category,
                model = excluded.model,
                messages_digest = excluded.messages_digest,
                message_count = excluded.message_count,
                revision = excluded.revision,
                occurred_at = excluded.occurred_at,
                status = 'ready',
                last_error = NULL,
                updated_at = excluded.updated_at
            """,
            (
                conversation_id,
                str(conversation["source_id"] or ""),
                title,
                summary,
                json.dumps(key_points, ensure_ascii=False),
                category,
                model,
                digest,
                message_count,
                revision,
                str(conversation["started_at"] or now),
                now if existing is None else now,
                now,
            ),
        )
        conn.commit()
        return True

    def _transcript_payload(self, conn: sqlite3.Connection, conversation_id: str) -> tuple[list[dict[str, str]], str, int]:
        rows = conn.execute(
            """
            SELECT role, content, content_hash
            FROM message_records
            WHERE conversation_id = ?
            ORDER BY occurred_at ASC, sequence ASC
            """,
            (conversation_id,),
        ).fetchall()
        digest = hashlib.sha256("\n".join(str(row["content_hash"]) for row in rows).encode("utf-8")).hexdigest()
        chosen = rows[:TRANSCRIPT_MESSAGE_CAP]
        return [
            {"role": str(row["role"]), "content": str(row["content"] or "")}
            for row in chosen
        ], digest, len(rows)

    def _render_transcript(self, messages: list[dict[str, str]]) -> str:
        parts: list[str] = []
        budget = TRANSCRIPT_CHAR_BUDGET
        for message in messages:
            role = "用户" if message["role"] == "user" else "AI"
            piece = f"{role}: {message['content'].strip()}"
            if len(piece) > budget:
                piece = piece[:budget] + "…"
            if not piece.strip():
                continue
            parts.append(piece)
            budget -= len(piece)
            if budget <= 0:
                parts.append("……（中间内容过长已省略）")
                break
        return "\n".join(parts)

    def _record_failure(self, conn: sqlite3.Connection, conversation_id: str, error: str) -> None:
        row = conn.execute(
            "SELECT source_id, title, started_at FROM conversation_records WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        if row is None:
            return
        now = _now()
        conn.execute(
            """
            INSERT INTO distilled_knowledge (
                conversation_id, source_id, title, summary, key_points_json, category,
                model, messages_digest, message_count, revision, occurred_at,
                status, last_error, created_at, updated_at
            ) VALUES (?, ?, ?, '', '[]', '其他', '', '', 0, 0, ?, 'failed', ?, ?, ?)
            ON CONFLICT(conversation_id) DO UPDATE SET
                status = 'failed',
                last_error = excluded.last_error,
                updated_at = excluded.updated_at
            """,
            (
                conversation_id,
                str(row["source_id"] or ""),
                str(row["title"] or "未命名对话"),
                str(row["started_at"] or now),
                error[:500],
                now,
                now,
            ),
        )
        conn.commit()


__all__ = ["KnowledgeDistiller"]
