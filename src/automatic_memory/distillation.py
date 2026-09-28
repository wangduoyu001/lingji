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
import time
from pathlib import Path
from typing import Any, Callable

TRANSCRIPT_CHAR_BUDGET = 3500
TRANSCRIPT_MESSAGE_CAP = 60
_CHAT_TIMEOUT_SECONDS = 300.0


# 模型列表探针（2026-09-27 事故修复）：单守护线程串行拉取 /api/tags，
# 结果带时间戳缓存。urllib timeout 覆盖不了 socket.getaddrinfo——解析器
# 卡死时探针线程至多卡死一个，调用方限时等待，拿不到就用最近结果或空。
_MODEL_LIST_FRESH_SECONDS = 300.0
_MODEL_LIST_DEADLINE_SECONDS = 8.0
_PROBE_STATES: dict[str, "_ModelListProbe"] = {}
_PROBE_STATES_LOCK = threading.Lock()


class _ModelListProbe:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url
        self._wake = threading.Event()
        self._done = threading.Event()
        self._lock = threading.Lock()
        self._fetched_at = 0.0
        self._models: list[tuple[str, int]] = []
        threading.Thread(target=self._loop, name="lingji-model-list-probe", daemon=True).start()

    def fetch(self) -> list[tuple[str, int]] | None:
        """新鲜缓存直接返回；否则唤醒探针限时等待，超时返回 None（不缓存）。"""
        with self._lock:
            if time.monotonic() - self._fetched_at < _MODEL_LIST_FRESH_SECONDS:
                return self._models
        self._done.clear()
        self._wake.set()
        self._done.wait(_MODEL_LIST_DEADLINE_SECONDS)
        with self._lock:
            if time.monotonic() - self._fetched_at < _MODEL_LIST_FRESH_SECONDS:
                return self._models
        return None

    def _loop(self) -> None:
        import urllib.request

        while True:
            self._wake.wait()
            self._wake.clear()
            models: list[tuple[str, int]] = []
            try:
                with urllib.request.urlopen(
                    f"{self._base_url}/api/tags", timeout=_TAGS_TIMEOUT_SECONDS
                ) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                for item in payload.get("models", []):
                    name = str(item.get("name") or "")
                    if name:
                        try:
                            size = int(item.get("size") or 0)
                        except (TypeError, ValueError):
                            size = 0
                        models.append((name, size))
            except Exception:
                models = []
            with self._lock:
                self._models = models
                self._fetched_at = time.monotonic()
            self._done.set()
_TAGS_TIMEOUT_SECONDS = 5.0
_EMBEDDING_MODEL_HINTS = ("embed", "bge", "minilm", "e5")
_NON_FINITE_JSON = re.compile(r",\s*([\]}])")


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _clamp_confidence(value: Any) -> float | None:
    """模型自评置信度裁剪到 [0,1]；缺失或非法返回 None（不自动晋升）。"""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN
        return None
    return max(0.0, min(1.0, number))


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

    def __init__(self, settings: Any, *, base_url: str | None = None, model: str | None = None,
                 model_override: Callable[[], str] | None = None,
                 provider_override: Callable[[], str] | None = None,
                 api_key_override: Callable[[], str] | None = None):
        self.settings = settings
        self.base_url = str(base_url or getattr(settings, "ollama_base_url", "http://127.0.0.1:11434")).rstrip("/")
        configured = str(model if model is not None else getattr(settings, "distill_model", "") or "").strip()
        self._configured_static = configured
        self._model_override = model_override
        self._provider_override = provider_override
        self._api_key_override = api_key_override
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
        # 默认 5s 超时在向量重建/同步高负载下会持续撞 "database is locked"，
        # 提炼循环把异常静默吞掉后表现为整条管线无声冻结（2026-09-23 真机复发）。
        # 30s 与 MemoryDatabase 对齐：等锁而不是秒败。
        conn = sqlite3.connect(str(path), timeout=30)
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
        try:
            conn.execute("ALTER TABLE distilled_knowledge ADD COLUMN superseded_by TEXT")
        except Exception:
            pass
        try:
            # 自动晋升门槛的原料字段；旧行无值视为"未评定"，不自动晋升。
            conn.execute("ALTER TABLE distilled_knowledge ADD COLUMN confidence REAL")
        except Exception:
            pass
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS distilled_knowledge_history (
                conversation_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                key_points_json TEXT NOT NULL,
                category TEXT NOT NULL,
                model TEXT NOT NULL,
                superseded_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS distill_progress (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                current_conversation_id TEXT,
                current_title TEXT,
                current_started_at TEXT,
                active_model TEXT,
                finished_json TEXT NOT NULL DEFAULT '[]',
                cumulative_distilled INTEGER NOT NULL DEFAULT 0,
                cumulative_failed INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()

    # ------------------------------------------------------------ model io
    def _available_models(self) -> list[tuple[str, int]]:
        """返回 [(模型名, 体积字节)]；体积用于优先选小模型（提炼无需大模型）。

        走进程级单线程探针：urllib 的 timeout 只约束连接/读，管不住
        socket.getaddrinfo（DNS 解析）阶段——2026-09-27 事故中提炼线程被
        解析器卡死 100+ 分钟并拖住优雅停机。探针至多卡死一个线程，调用方
        按截止时间拿最近一次结果；探不动时返回空（本轮退避，绝不无限阻塞）。
        """
        with _PROBE_STATES_LOCK:
            probe = _PROBE_STATES.get(self.base_url)
            if probe is None:
                probe = _ModelListProbe(self.base_url)
                _PROBE_STATES[self.base_url] = probe
        models = probe.fetch()
        return list(models) if models else []

    @property
    def configured_model(self) -> str:
        """每轮实时读取覆盖值：主人在 UI 切换模型后下一轮立即生效。"""
        if self._model_override is not None:
            try:
                override = str(self._model_override() or "").strip()
            except Exception:
                override = ""
            if override:
                return override
        return self._configured_static

    def _designed_defaults(self) -> list[str]:
        """原设计的默认提炼模型（小模型）：llm_model → fallback_llm。"""
        defaults = []
        for attr in ("llm_model", "fallback_llm"):
            value = str(getattr(self.settings, attr, "") or "").strip()
            if value:
                defaults.append(value)
        return defaults

    def installed_models(self) -> list[dict[str, Any]]:
        """已安装的 chat 模型（供主人在 UI 选择）；标注当前生效的一个。"""
        active = self._resolve_model()
        chat = [
            {"name": name, "size_bytes": size}
            for name, size in self._available_models()
            if not any(hint in name.lower() for hint in _EMBEDDING_MODEL_HINTS)
        ]
        chat.sort(key=lambda entry: (entry["size_bytes"], entry["name"]))
        for entry in chat:
            entry["active"] = entry["name"] == active
        return chat

    def _resolve_model(self) -> str | None:
        installed = self._available_models()
        if not installed:
            return None
        names = [name for name, _size in installed]

        def match(name: str) -> str | None:
            if name in names:
                return name
            base = name.split(":")[0]
            return next((candidate for candidate in names if candidate.split(":")[0] == base), None)

        # 1) 主人显式选择的提炼模型（UI 切换后立即生效，不用旧缓存）
        configured = self.configured_model
        if configured:
            found = match(configured)
            if found:
                self._model = found
                return self._model
        # 2) 无覆盖时可用已解析缓存；该模型被卸载则重新解析
        cached = self._model
        if cached and cached in names:
            return cached
        # 3) 原设计默认（小模型优先于大模型）
        for default in self._designed_defaults():
            found = match(default)
            if found:
                self._model = found
                return self._model
        # 4) 兜底：已安装的 chat 模型里选体积最小的（摘要任务不需要大模型）
        chat = [(name, size) for name, size in installed if not any(hint in name.lower() for hint in _EMBEDDING_MODEL_HINTS)]
        if not chat:
            return None
        chat.sort(key=lambda entry: (entry[1], entry[0]))
        self._model = chat[0][0]
        return self._model

    def _build_prompt(self, title: str, transcript: str) -> list[dict[str, str]]:
        system = (
            "你是记忆提炼器。阅读一段用户与AI的对话，只提取真正值得长期保留的关键节点。"
            "只记四类内容：①关键决策或拍板（定了什么方案、为什么）；②结论及其推导过程或根因"
            "（查明了什么、为什么是这样）；③关键状态变化（完成/上线/迁移/回滚/修好了什么）；"
            "④不可复得的关键步骤（之后无法从别处得知的操作序列）。"
            '只返回 JSON 对象：{"short_title": "给这段对话起一个不超过16字的具体标题", '
            '"summary": "一句话说明关键结论/决定/变化（没有关键内容时留空字符串）", '
            '"key_points": ["要点1", "要点2"], '
            '"confidence": 0.0到1.0的小数表示这段结论作为长期事实的把握'
            '（确定且被验证给高分，推测或临时状态给低分）, '
            '"category": "项目|技术|决策|问题|其他"}。'
            "红线：宁缺毋滥。纯操作过程、寒暄、例行检查、中间调试流水、没有结论的讨论，"
            "一律返回 \"key_points\": [] 且 \"summary\": \"\"——没有关键节点就不产出，"
            "绝不为凑数把流水账包装成要点。key_points 用短句，每条不超过40字。"
            "category 必须五选一：改代码/修Bug/搭环境=技术；定了方案或拍板=决策；"
            "遇到故障或报错=问题；启动或推进某个项目=项目；闲聊或无结论=其他。"
            "如果这段对话推翻或升级了近期某个旧结论（旧标题见下），"
            "额外返回 \"supersedes\": \"<被取代的旧标题>\"；否则不要返回该字段。"
        )
        user = f"对话标题：{title}\n\n对话内容：\n{transcript}"
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    @property
    def provider(self) -> str:
        """提炼服务：local（本机 Ollama）或 zhipu（GLM-4-Flash 云端）。"""
        if self._provider_override is not None:
            try:
                value = str(self._provider_override() or "").strip().lower()
            except Exception:
                value = ""
            if value:
                return value
        return "local"

    @property
    def api_key(self) -> str:
        if self._api_key_override is not None:
            try:
                return str(self._api_key_override() or "").strip()
            except Exception:
                return ""
        return ""

    _ZHIPU_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    _ZHIPU_MODEL = "glm-4-flash"

    def _chat_zhipu(self, api_key: str, messages: list[dict[str, str]]) -> str:
        import ssl
        import urllib.request

        payload = json.dumps(
            {"model": self._ZHIPU_MODEL, "messages": messages, "temperature": 0.2, "stream": False}
        ).encode("utf-8")
        request = urllib.request.Request(
            self._ZHIPU_URL,
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            method="POST",
        )
        # 系统根证书 + certifi 叠加：冻结环境里两边都可能缺某一环。
        context = ssl.create_default_context()
        try:
            import certifi

            context.load_verify_locations(cafile=certifi.where())
        except Exception:
            pass
        # 显式绕过系统代理（urllib 在 macOS 会自动读取系统代理，
        # Clash 等代理的 CONNECT 隧道可能挂起导致云端调用无限等待）。
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
        choices = body.get("choices") or [{}]
        return str(((choices[0] or {}).get("message") or {}).get("content") or "")

    def _chat_dispatch(self, local_model: str, messages: list[dict[str, str]]) -> tuple[str, str]:
        """按主人选择分发；云端失败自动回退本机，绝不丢提炼。"""
        if self.provider == "zhipu" and self.api_key:
            try:
                return self._chat_cloud_with_deadline(messages), self._ZHIPU_MODEL
            except Exception as ssl_exc:
                # OpenSSL 证书链不完整时（bigmodel 缺中间证书），用系统 curl 重试。
                try:
                    return self._chat_zhipu_curl(self.api_key, messages), self._ZHIPU_MODEL
                except Exception as curl_exc:
                    self._last_cloud_error = (
                        f"ssl={type(ssl_exc).__name__}; curl={type(curl_exc).__name__}: {curl_exc}"[:200]
                    )
                    import logging

                    logging.getLogger("lingji.distillation").warning(
                        "cloud distillation failed, falling back to local: %s", self._last_cloud_error
                    )
        return self._chat(local_model, messages), local_model

    def _chat_zhipu_curl(self, api_key: str, messages: list[dict[str, str]]) -> str:
        """系统 curl 兜底：bigmodel 证书链缺中间证书时，macOS 的 curl
        （系统 TLS 栈，自动补中间证书）可以完成校验而 OpenSSL 不行。"""
        import subprocess

        payload = json.dumps(
            {"model": self._ZHIPU_MODEL, "messages": messages, "temperature": 0.2, "stream": False}
        ).encode("utf-8")
        completed = subprocess.run(
            [
                "/usr/bin/curl", "--noproxy", "*", "-sS", "-m", "115", "-X", "POST",
                self._ZHIPU_URL,
                "-H", "Content-Type: application/json",
                "-H", f"Authorization: Bearer {api_key}",
                "-d", "@-",
            ],
            input=payload,
            capture_output=True,
            timeout=115,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"curl exit {completed.returncode}: {completed.stderr[:120]!r}")
        body = json.loads(completed.stdout.decode("utf-8"))
        choices = body.get("choices") or [{}]
        return str(((choices[0] or {}).get("message") or {}).get("content") or "")

    def _chat_cloud_with_deadline(self, messages: list[dict[str, str]], deadline: float = 130.0) -> str:
        """带硬截止的云端调用：DNS/TLS 挂起无法靠 socket timeout 兜底，
        用独立线程 + join(deadline) 强制超时，避免 daemon 卡死在单段对话上。"""
        result: dict[str, str] = {}

        def _run() -> None:
            try:
                result["answer"] = self._chat_zhipu(self.api_key, messages)
            except Exception as exc:  # noqa: BLE001 - 回退路径需要知道原因
                result["error"] = f"{type(exc).__name__}: {exc}"[:200]

        worker = threading.Thread(target=_run, name="lingji-cloud-distill", daemon=True)
        worker.start()
        worker.join(deadline)
        if worker.is_alive():
            raise TimeoutError(f"cloud request exceeded {deadline:.0f}s deadline")
        if "error" in result:
            raise RuntimeError(result["error"])
        return result["answer"]

    def _chat(self, model: str, messages: list[dict[str, str]]) -> str:
        import urllib.request

        payload = json.dumps(
            {
                "model": model,
                "messages": messages,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.2, "num_ctx": 4096},
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
        # superseded 是被更新结论有意取代的终态：会话内容没变就不重提炼复活，
        # 否则它每轮满足 status != 'ready' 永久占住 started_at DESC 队列前排，
        # 饿死真正未提炼的会话（failed 行保留重试语义）。
        rows = conn.execute(
            """
            SELECT c.conversation_id, c.source_id, c.title, c.started_at, c.message_count
            FROM conversation_records c
            LEFT JOIN distilled_knowledge d ON d.conversation_id = c.conversation_id
            WHERE d.conversation_id IS NULL
               OR (d.status != 'ready' AND COALESCE(d.status, '') NOT IN ('superseded', 'empty', 'no_key_content'))
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
            # pending 口径 = 真正待提炼的数量：扣除已提炼与全部终态
            # （superseded/empty/no_key_content 都不是待办）。
            settled = int(conn.execute(
                "SELECT COUNT(*) FROM distilled_knowledge WHERE status != 'ready'"
            ).fetchone()[0])
            by_category: dict[str, int] = {}
            for row in conn.execute(
                "SELECT category, COUNT(*) AS n FROM distilled_knowledge WHERE status = 'ready' GROUP BY category"
            ):
                by_category[str(row["category"])] = int(row["n"])
        model = self._model or self._resolve_model()
        if self.provider == "zhipu" and self.api_key:
            model = self._ZHIPU_MODEL
        return {
            "total": total_convs,
            "ready": ready,
            "pending": max(0, total_convs - ready - settled),
            "by_category": by_category,
            "model": model,
            "available": model is not None,
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
                    "source_id": str(row["source_id"] or ""),
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

    def reset_distillations(self) -> int:
        """把存量要点归档（进 history），让 daemon 用新提示词全量重提炼。"""
        db = self._memory_db()
        if not self._db_available():
            return 0
        with self._connect() as conn:
            self._ensure_schema(conn)
            rows = conn.execute(
                "SELECT * FROM distilled_knowledge WHERE status = 'ready'"
            ).fetchall()
            now = _now()
            for row in rows:
                conn.execute(
                    """
                    INSERT INTO distilled_knowledge_history (
                        conversation_id, revision, title, summary, key_points_json,
                        category, model, superseded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(row["conversation_id"]), int(row["revision"]), str(row["title"]),
                        str(row["summary"]), str(row["key_points_json"]), str(row["category"]),
                        str(row["model"]), now,
                    ),
                )
            cursor = conn.execute("DELETE FROM distilled_knowledge WHERE status = 'ready'")
            conn.commit()
            return cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0

    def run_once(self, limit: int = 2) -> dict[str, Any]:
        """提炼至多 limit 段对话；返回进度统计。全自动、可重复调用。"""
        with self._lock:
            return self._run_once_locked(limit)

    def _run_once_locked(self, limit: int) -> dict[str, Any]:
        if not self._db_available():
            return {"status": "empty", "distilled": 0, "failed": 0, **self.stats()}
        model = self._resolve_model()
        # 进度面板展示"实际生效"的模型：云端启用时优先显示云端模型名。
        used_model_label = self._ZHIPU_MODEL if (self.provider == "zhipu" and self.api_key) else model
        if model is None and used_model_label is None:
            return {"status": "model_unavailable", "distilled": 0, "failed": 0, **self.stats()}
        if model is None:
            model = used_model_label
        distilled = 0
        failed = 0
        skipped = 0
        with self._connect() as conn:
            self._ensure_schema(conn)
            pending = self._pending_conversations(conn, max(1, int(limit)))
            for conversation in pending:
                conversation_id = str(conversation["conversation_id"])
                self._publish_current(conn, used_model_label, conversation)
                started = time.monotonic()
                try:
                    outcome = self._distill_one(conn, model, conversation)
                except Exception as exc:  # 单段失败不阻塞本轮其余对话
                    self._record_failure(conn, conversation_id, str(exc))
                    self._publish_finished(conn, used_model_label, str(conversation["title"] or "未命名对话"), time.monotonic() - started, False)
                    failed += 1
                    continue
                self._publish_finished(conn, used_model_label, str(conversation["title"] or "未命名对话"), time.monotonic() - started, bool(outcome))
                if outcome == "skipped":
                    skipped += 1
                elif outcome:
                    distilled += 1
                else:
                    failed += 1
        return {
            "status": "ok",
            "distilled": distilled,
            "failed": failed,
            "skipped_no_key_content": skipped,
            **self.stats(),
        }

    # ------------------------------------------------------------- progress
    def _publish_current(self, conn: sqlite3.Connection, model: str, conversation: dict[str, Any]) -> None:
        conn.execute(
            """
            INSERT INTO distill_progress (id, current_conversation_id, current_title, current_started_at, active_model, finished_json, cumulative_distilled, cumulative_failed, updated_at)
            VALUES (1, ?, ?, ?, ?, COALESCE((SELECT finished_json FROM distill_progress WHERE id = 1), '[]'),
                    COALESCE((SELECT cumulative_distilled FROM distill_progress WHERE id = 1), 0),
                    COALESCE((SELECT cumulative_failed FROM distill_progress WHERE id = 1), 0), ?)
            ON CONFLICT(id) DO UPDATE SET
                current_conversation_id = excluded.current_conversation_id,
                current_title = excluded.current_title,
                current_started_at = excluded.current_started_at,
                active_model = excluded.active_model,
                updated_at = excluded.updated_at
            """,
            (
                str(conversation["conversation_id"]),
                str(conversation["title"] or "未命名对话"),
                _now(),
                model,
                _now(),
            ),
        )
        conn.commit()

    def _publish_finished(self, conn: sqlite3.Connection, model: str, title: str, seconds: float, ok: bool) -> None:
        row = conn.execute("SELECT finished_json, cumulative_distilled, cumulative_failed FROM distill_progress WHERE id = 1").fetchone()
        try:
            finished = json.loads(str(row["finished_json"] or "[]")) if row is not None else []
        except json.JSONDecodeError:
            finished = []
        if not isinstance(finished, list):
            finished = []
        finished.append({"title": title[:60], "seconds": round(float(seconds), 1), "ok": bool(ok), "at": _now()})
        finished = finished[-6:]
        distilled = int(row["cumulative_distilled"] if row is not None else 0) + (1 if ok else 0)
        failed = int(row["cumulative_failed"] if row is not None else 0) + (0 if ok else 1)
        conn.execute(
            """
            INSERT INTO distill_progress (id, current_conversation_id, current_title, current_started_at, active_model, finished_json, cumulative_distilled, cumulative_failed, updated_at)
            VALUES (1, NULL, NULL, NULL, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                current_conversation_id = NULL,
                current_title = NULL,
                current_started_at = NULL,
                active_model = excluded.active_model,
                finished_json = excluded.finished_json,
                cumulative_distilled = excluded.cumulative_distilled,
                cumulative_failed = excluded.cumulative_failed,
                updated_at = excluded.updated_at
            """,
            (model, json.dumps(finished, ensure_ascii=False), distilled, failed, _now()),
        )
        conn.commit()

    def progress(self) -> dict[str, Any]:
        """主人面板用的实时进度：正在提炼哪段、最近几段耗时、累计成败。"""
        if not self._db_available():
            return {"active": False}
        with self._connect() as conn:
            self._ensure_schema(conn)
            row = conn.execute("SELECT * FROM distill_progress WHERE id = 1").fetchone()
        if row is None:
            return {"active": False}
        try:
            finished = json.loads(str(row["finished_json"] or "[]"))
        except json.JSONDecodeError:
            finished = []
        payload = {
            "active": bool(row["current_conversation_id"]),
            "current": {
                "conversation_id": row["current_conversation_id"],
                "title": row["current_title"],
                "started_at": row["current_started_at"],
            } if row["current_conversation_id"] else None,
            "model": row["active_model"],
            "finished": [item for item in finished if isinstance(item, dict)][-6:],
            "cumulative_distilled": int(row["cumulative_distilled"]),
            "cumulative_failed": int(row["cumulative_failed"]),
            "updated_at": row["updated_at"],
            "cloud_error": getattr(self, "_last_cloud_error", None),
        }
        return payload

    def _distill_one(self, conn: sqlite3.Connection, model: str, conversation: dict[str, Any]) -> bool:
        conversation_id = str(conversation["conversation_id"])
        title = str(conversation["title"] or "未命名对话")
        # status 必须真实读取：历史上这里漏取 status 列导致"取不到即按 ready"
        # 的错误默认，superseded 行被当成最新结论秒跳。
        existing = conn.execute(
            "SELECT messages_digest, revision, status, message_count FROM distilled_knowledge WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        digest = self._conversation_digest(conn, conversation_id)
        if digest is None:
            # 无消息的会话（坏导入/空壳行）永远提炼不出内容：必须落终态行出队，
            # 否则它以 0 秒失败永占 started_at DESC 队首，饿死全部真实候选
            # （f2a82fa0 superseded 饿死的同族新变种）。message_count=0 保留复活
            # 语义：消息将来被导入时 message_count 条件会自动让它重新入队。
            self._record_empty(conn, conversation_id)
            return False
        if (
            existing is not None
            and str(existing["messages_digest"]) == digest
            and str(existing["status"] or "ready") == "ready"
        ):
            # 已是最新，视为成功。历史行的 message_count 可能是旧口径；若不在此处
            # 修正，该会话会永远满足候选条件（message_count 不匹配）并每轮空转，
            # 把 ORDER BY started_at DESC 队列前排占满，饿死真正未提炼的会话。
            actual_count = int(
                conn.execute(
                    "SELECT COUNT(*) FROM message_records WHERE conversation_id = ?",
                    (conversation_id,),
                ).fetchone()[0]
            )
            if int(existing["message_count"] or 0) != actual_count:
                conn.execute(
                    "UPDATE distilled_knowledge SET message_count = ? WHERE conversation_id = ?",
                    (actual_count, conversation_id),
                )
                conn.commit()
            return True
        messages, _digest_used, message_count = self._transcript_payload(conn, conversation_id)
        recent = conn.execute(
            """
            SELECT title FROM distilled_knowledge
            WHERE status = 'ready' AND conversation_id != ?
            ORDER BY COALESCE(occurred_at, created_at) DESC LIMIT 10
            """,
            (conversation_id,),
        ).fetchall()
        prompt = self._build_prompt(title, self._render_transcript(messages))
        if recent:
            listing = "\n".join(f"- {r['title']}" for r in recent)
            prompt[-1]["content"] += f"\n\n近期已有结论的标题（若本次对话推翻其中某个，返回 supersedes 字段）：\n{listing}"
        answer, used_model = self._chat_dispatch(model, prompt)
        parsed = _parse_model_json(answer)
        if parsed is None:
            self._record_failure(conn, conversation_id, "模型输出无法解析为知识要点")
            return False
        summary = str(parsed.get("summary") or "").strip()
        raw_points = parsed.get("key_points")
        if isinstance(raw_points, str):
            key_points = [segment.strip() for segment in re.split(r"[;；\n]", raw_points) if segment.strip()]
        elif isinstance(raw_points, list):
            key_points = [str(point).strip() for point in raw_points if str(point).strip()]
        else:
            key_points = []
        key_points = [point for point in key_points if point]
        # 主人原则（2026-09-28）：不为记忆而记忆。模型按提示词契约明确返回空
        # 产出（summary/key_points 字段存在且为空）= 这段对话没有关键节点：
        # 落终态出队（绝不反复重试），内容将来变化时经 message_count 条件自动
        # 复活重新提炼。summary 空但要点非空仍入库；完全不符契约形状的输出
        # 仍是失败（保留重试），不冒充"没有值得记的"。
        if not summary and not key_points:
            if "summary" in parsed or "key_points" in parsed:
                self._record_no_key_content(conn, conversation_id, digest)
                return "skipped"
            self._record_failure(conn, conversation_id, "模型输出无法解析为知识要点")
            return False
        category = str(parsed.get("category") or "其他").strip() or "其他"
        confidence = _clamp_confidence(parsed.get("confidence"))
        short_title = str(parsed.get("short_title") or "").strip()
        if 2 <= len(short_title) <= 24 and "会话" not in short_title:
            title = short_title
        supersedes = str(parsed.get("supersedes") or "").strip()
        if supersedes:
            row = conn.execute(
                "SELECT conversation_id FROM distilled_knowledge WHERE title LIKE ? AND conversation_id != ? AND status = 'ready' LIMIT 1",
                (f"%{supersedes[:40]}%", conversation_id),
            ).fetchone()
            if row is not None:
                conn.execute(
                    "UPDATE distilled_knowledge SET status = 'superseded', superseded_by = ? WHERE conversation_id = ?",
                    (conversation_id, str(row["conversation_id"])),
                )
        now = _now()
        revision = 1 if existing is None else int(existing["revision"]) + 1
        if existing is not None:
            # 迭代可追溯（P3）：旧结论归档，新结论取代旧结论，时间线只记一条更新。
            old_row = conn.execute(
                "SELECT * FROM distilled_knowledge WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
            if old_row is not None:
                conn.execute(
                    """
                    INSERT INTO distilled_knowledge_history (
                        conversation_id, revision, title, summary, key_points_json,
                        category, model, superseded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        conversation_id, int(old_row["revision"]), old_row["title"],
                        old_row["summary"], old_row["key_points_json"], old_row["category"],
                        old_row["model"], now,
                    ),
                )
        conn.execute(
            """
            INSERT INTO distilled_knowledge (
                conversation_id, source_id, title, summary, key_points_json, category,
                model, messages_digest, message_count, revision, occurred_at,
                status, last_error, created_at, updated_at, confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ready', NULL, ?, ?, ?)
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
                updated_at = excluded.updated_at,
                confidence = excluded.confidence
            """,
            (
                conversation_id,
                str(conversation["source_id"] or ""),
                title,
                summary,
                json.dumps(key_points, ensure_ascii=False),
                category,
                used_model,
                digest,
                message_count,
                revision,
                str(conversation["started_at"] or now),
                now if existing is None else now,
                now,
                confidence,
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
        # 纵深防御：上云文本在记忆层脱敏之外再做一次敏感信息擦除。
        try:
            from src.extraction.privacy import PrivacyClassifier

            redactor = PrivacyClassifier()
        except Exception:
            redactor = None
        parts: list[str] = []
        budget = TRANSCRIPT_CHAR_BUDGET
        for message in messages:
            role = "用户" if message["role"] == "user" else "AI"
            content = redactor.redact(message["content"]) if redactor else message["content"]
            piece = f"{role}: {content.strip()}"
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

    def _record_no_key_content(
        self, conn: sqlite3.Connection, conversation_id: str, digest: str
    ) -> None:
        """无关键节点会话的终态标记：出队不重试；消息数变化时自动复活重新提炼。"""
        row = conn.execute(
            "SELECT source_id, title, started_at, message_count FROM conversation_records WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        if row is None:
            return
        now = _now()
        message_count = int(row["message_count"] or 0)
        conn.execute(
            """
            INSERT INTO distilled_knowledge (
                conversation_id, source_id, title, summary, key_points_json, category,
                model, messages_digest, message_count, revision, occurred_at,
                status, last_error, created_at, updated_at
            ) VALUES (?, ?, ?, '', '[]', '其他', '', ?, ?, 0, ?, 'no_key_content',
                      'no key content worth remembering', ?, ?)
            ON CONFLICT(conversation_id) DO UPDATE SET
                status = 'no_key_content',
                messages_digest = excluded.messages_digest,
                message_count = excluded.message_count,
                last_error = excluded.last_error,
                updated_at = excluded.updated_at
            """,
            (
                conversation_id,
                str(row["source_id"] or ""),
                str(row["title"] or "未命名对话")[:80],
                digest,
                message_count,
                str(row["started_at"] or now),
                now,
                now,
            ),
        )
        conn.commit()

    def _record_empty(self, conn: sqlite3.Connection, conversation_id: str) -> None:
        """无消息会话的终态标记：出队停止空转；消息导入后经 message_count 条件复活。"""
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
            ) VALUES (?, ?, ?, '', '[]', '其他', '', '', 0, 0, ?, 'empty', 'no messages to distill', ?, ?)
            ON CONFLICT(conversation_id) DO UPDATE SET
                status = 'empty',
                message_count = 0,
                last_error = 'no messages to distill',
                updated_at = excluded.updated_at
            """,
            (
                conversation_id,
                str(row["source_id"] or ""),
                str(row["title"] or "未命名对话"),
                str(row["started_at"] or now),
                now,
                now,
            ),
        )
        conn.commit()

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
