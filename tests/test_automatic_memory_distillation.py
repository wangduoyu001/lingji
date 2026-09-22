"""Tests for the full-auto knowledge distillation layer."""

from __future__ import annotations

import json
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

from src.automatic_memory.distillation import KnowledgeDistiller


class _Settings:
    def __init__(self, memory_db_path: Path, base_url: str) -> None:
        self.memory_db_path = str(memory_db_path)
        self.ollama_base_url = base_url
        self.distill_model = ""


def _seed_memory_db(path: Path, *, conversations: int = 2) -> None:
    with sqlite3.connect(str(path)) as conn:
        conn.execute(
            """
            CREATE TABLE conversation_records (
                conversation_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                title TEXT NOT NULL,
                started_at TEXT,
                message_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE message_records (
                message_id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                occurred_at TEXT,
                sequence INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        for index in range(conversations):
            conversation_id = f"conv-{index}"
            conn.execute(
                "INSERT INTO conversation_records VALUES (?, 'src', ?, '2026-09-01T00:00:00+00:00', 2)",
                (conversation_id, f"对话 {index}"),
            )
            for seq in range(2):
                content = f"消息 {index}-{seq}：讨论了项目方案并确定使用本地模型。"
                conn.execute(
                    """
                    INSERT INTO message_records VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"msg-{index}-{seq}",
                        conversation_id,
                        "user" if seq == 0 else "assistant",
                        content,
                        f"hash-{index}-{seq}",
                        f"2026-09-01T00:0{seq}:00+00:00",
                        seq,
                    ),
                )
        conn.commit()


class _OllamaHandler(BaseHTTPRequestHandler):
    payload: dict[str, Any] = {
        "summary": "确定了使用本地模型的项目方案",
        "key_points": ["使用本地模型", "方案已确定"],
        "category": "决策",
    }
    fail_requests = False
    lock = threading.Lock()
    requests: list[dict[str, Any]] = []

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/tags":
            body = json.dumps(
                {
                    "models": [
                        {"name": "test-chat-huge:latest", "size": 16_000_000_000},
                        {"name": "test-chat:latest", "size": 4_700_000_000},
                        {"name": "nomic-embed-text:latest", "size": 274_000_000},
                    ]
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        with _OllamaHandler.lock:
            _OllamaHandler.requests.append(json.loads(raw.decode("utf-8")))
        if _OllamaHandler.fail_requests:
            self.send_response(500)
            self.end_headers()
            return
        body = json.dumps({"message": {"content": json.dumps(_OllamaHandler.payload, ensure_ascii=False)}}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: Any) -> None:
        return


@pytest.fixture()
def ollama_server():
    _OllamaHandler.requests = []
    _OllamaHandler.fail_requests = False
    server = HTTPServer(("127.0.0.1", 0), _OllamaHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def _distiller(tmp_path: Path, base_url: str) -> KnowledgeDistiller:
    memory_db = tmp_path / "lingji_memory.db"
    if not memory_db.exists():
        _seed_memory_db(memory_db)
    return KnowledgeDistiller(_Settings(memory_db, base_url))


def test_run_once_distills_all_conversations(tmp_path: Path, ollama_server: str) -> None:
    distiller = _distiller(tmp_path, ollama_server)
    result = distiller.run_once(limit=10)
    assert result["status"] == "ok"
    assert result["distilled"] == 2
    assert result["pending"] == 0
    stats = distiller.stats()
    assert stats["ready"] == 2
    assert stats["available"] is True
    listing = distiller.list_entries(limit=10)
    assert listing["pagination"]["total"] == 2
    entry = listing["items"][0]
    assert entry["summary"] == "确定了使用本地模型的项目方案"
    assert entry["category"] == "决策"
    assert "本地模型" in entry["key_points"][0]


def test_run_once_is_idempotent(tmp_path: Path, ollama_server: str) -> None:
    distiller = _distiller(tmp_path, ollama_server)
    distiller.run_once(limit=10)
    requests_after_first = len(_OllamaHandler.requests)
    result = distiller.run_once(limit=10)
    assert result["distilled"] == 0
    # 未变化的对话不再重复请求模型。
    assert len(_OllamaHandler.requests) == requests_after_first


def test_stale_message_count_candidate_is_repaired_without_model_call(tmp_path: Path, ollama_server: str) -> None:
    """历史行 message_count 旧口径不匹配时：修正口径、不重调模型、两轮内不再占候选。

    回归背景：生产库一批 ready 行的 message_count 是旧口径，每轮都满足候选条件
    （message_count != 实际消息数）却被 digest 秒跳，且永不修正——它们永久占满
    started_at DESC 队列前排，饿死真正未提炼的会话。
    """
    distiller = _distiller(tmp_path, ollama_server)
    distiller.run_once(limit=10)
    memory_db = tmp_path / "lingji_memory.db"
    with sqlite3.connect(str(memory_db)) as conn:
        conn.execute("UPDATE distilled_knowledge SET message_count = 0 WHERE conversation_id = 'conv-0'")
        conn.commit()
    requests_before = len(_OllamaHandler.requests)

    result = distiller.run_once(limit=10)
    # 口径修正不重调模型（秒跳成功计入 distilled，这里只认模型请求）。
    assert len(_OllamaHandler.requests) == requests_before
    with sqlite3.connect(str(memory_db)) as conn:
        fixed = int(conn.execute("SELECT message_count FROM distilled_knowledge WHERE conversation_id = 'conv-0'").fetchone()[0])
    assert fixed == 2

    # 第二轮：conv-0 退出候选，pending 归零（不再每轮空转占位）。
    result2 = distiller.run_once(limit=10)
    assert result2["pending"] == 0
    assert len(_OllamaHandler.requests) == requests_before


def test_stale_message_count_does_not_starve_undistilled_conversations(tmp_path: Path, ollama_server: str) -> None:
    """假候选不再永久占位：排队在后的未提炼会话在有限轮内被处理。"""
    distiller = _distiller(tmp_path, ollama_server)
    distiller.run_once(limit=10)
    memory_db = tmp_path / "lingji_memory.db"
    # 新增第三个会话（未提炼），同时把 conv-0 变成 message_count 旧口径的假候选。
    with sqlite3.connect(str(memory_db)) as conn:
        conn.execute(
            "INSERT INTO conversation_records VALUES (?, 'src', ?, '2026-09-03T00:00:00+00:00', 2)",
            ("conv-2", "对话 2"),
        )
        for seq in range(2):
            conn.execute(
                "INSERT INTO message_records VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    f"msg-2-{seq}",
                    "conv-2",
                    "user" if seq == 0 else "assistant",
                    f"消息 2-{seq}：确定了新的发布流程。",
                    f"hash-2-{seq}",
                    f"2026-09-03T00:0{seq}:00+00:00",
                    seq,
                ),
            )
        conn.execute("UPDATE distilled_knowledge SET message_count = 0 WHERE conversation_id = 'conv-0'")
        conn.commit()

    # 第一轮消化假候选（修正口径，不调模型），第二轮必须轮到真正未提炼的 conv-2。
    distiller.run_once(limit=1)
    distiller.run_once(limit=1)
    requests_now = len(_OllamaHandler.requests)
    assert requests_now > 0
    listing = distiller.list_entries(limit=10)
    distilled_ids = {item["conversation_id"] for item in listing["items"]}
    assert "conv-2" in distilled_ids


def test_superseded_rows_leave_candidate_queue_and_never_revive(tmp_path: Path, ollama_server: str) -> None:
    """superseded 是被更新结论取代的终态：不再进候选、不因 digest 相同被复活。

    回归背景：秒跳判断漏取 status 列（取不到即按 ready），superseded 行每轮满足
    status != 'ready' 进候选、每轮被秒跳成功，两个队列名额每轮空转，真正未提炼的
    会话被永久饿死（生产 549 个会话从未被提炼）。
    """
    distiller = _distiller(tmp_path, ollama_server)
    distiller.run_once(limit=10)
    memory_db = tmp_path / "lingji_memory.db"
    with sqlite3.connect(str(memory_db)) as conn:
        conn.execute("UPDATE distilled_knowledge SET status = 'superseded' WHERE conversation_id = 'conv-0'")
        conn.commit()
    requests_before = len(_OllamaHandler.requests)

    result = distiller.run_once(limit=10)
    # superseded 行既不重提炼复活，也不作为成功计数空转。
    assert len(_OllamaHandler.requests) == requests_before
    assert result["distilled"] == 0
    with sqlite3.connect(str(memory_db)) as conn:
        status = str(conn.execute("SELECT status FROM distilled_knowledge WHERE conversation_id = 'conv-0'").fetchone()[0])
        pending = conn.execute(
            """
            SELECT COUNT(*) FROM conversation_records c
            LEFT JOIN distilled_knowledge d ON d.conversation_id = c.conversation_id
            WHERE d.conversation_id IS NULL
               OR (d.status != 'ready' AND COALESCE(d.status, '') != 'superseded')
               OR d.message_count != (SELECT COUNT(*) FROM message_records m WHERE m.conversation_id = c.conversation_id)
            """
        ).fetchone()[0]
    assert status == "superseded"
    assert pending == 0


def test_changed_messages_bump_revision(tmp_path: Path, ollama_server: str) -> None:
    distiller = _distiller(tmp_path, ollama_server)
    distiller.run_once(limit=10)
    memory_db = tmp_path / "lingji_memory.db"
    with sqlite3.connect(str(memory_db)) as conn:
        conn.execute(
            "INSERT INTO message_records VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("msg-new", "conv-0", "user", "追加了一个新决定", "hash-new", "2026-09-02T00:00:00+00:00", 2),
        )
        conn.commit()
    result = distiller.run_once(limit=10)
    assert result["distilled"] >= 1
    listing = distiller.list_entries(limit=10)
    revisions = {item["conversation_id"]: item["revision"] for item in listing["items"]}
    assert revisions["conv-0"] == 2


def test_search_and_category_filter(tmp_path: Path, ollama_server: str) -> None:
    distiller = _distiller(tmp_path, ollama_server)
    distiller.run_once(limit=10)
    assert len(distiller.list_entries(query="本地模型")["items"]) == 2
    assert len(distiller.list_entries(query="不存在的关键词xyz")["items"]) == 0
    assert len(distiller.list_entries(category="决策")["items"]) == 2
    assert len(distiller.list_entries(category="项目")["items"]) == 0


def test_model_unavailable_reports_status(tmp_path: Path) -> None:
    memory_db = tmp_path / "lingji_memory.db"
    _seed_memory_db(memory_db)
    distiller = KnowledgeDistiller(_Settings(memory_db, "http://127.0.0.1:1"))
    result = distiller.run_once(limit=5)
    assert result["status"] == "model_unavailable"
    assert distiller.stats()["ready"] == 0


def test_model_failure_records_failed_status(tmp_path: Path, ollama_server: str) -> None:
    _OllamaHandler.fail_requests = True
    distiller = _distiller(tmp_path, ollama_server)
    result = distiller.run_once(limit=10)
    assert result["failed"] == 2
    stats = distiller.stats()
    assert stats["ready"] == 0
    # 失败的段落在服务恢复后会被重新拾起。
    _OllamaHandler.fail_requests = False
    recovered = distiller.run_once(limit=10)
    assert recovered["distilled"] == 2
    assert recovered["pending"] == 0


def test_configured_model_falls_back_to_available(tmp_path: Path, ollama_server: str) -> None:
    memory_db = tmp_path / "lingji_memory.db"
    _seed_memory_db(memory_db)
    settings = _Settings(memory_db, ollama_server)
    settings.distill_model = "qwen3:8b"  # 未安装：应回退到已安装的 chat 模型
    distiller = KnowledgeDistiller(settings)
    result = distiller.run_once(limit=10)
    assert result["status"] == "ok"
    assert distiller.list_entries(limit=1)["items"][0]["model"] == "test-chat:latest"


def test_prefers_smallest_installed_chat_model(tmp_path: Path, ollama_server: str) -> None:
    """提炼是摘要任务：无显式配置时应选最小的 chat 模型，而不是列表里第一个大模型。"""
    memory_db = tmp_path / "lingji_memory.db"
    _seed_memory_db(memory_db)
    distiller = KnowledgeDistiller(_Settings(memory_db, ollama_server))
    distiller.run_once(limit=10)
    assert distiller.list_entries(limit=1)["items"][0]["model"] == "test-chat:latest"


def test_designed_llm_default_beats_smaller_models(tmp_path: Path, ollama_server: str) -> None:
    """配置了设计默认 llm_model 且已安装时，优先于更小的模型。"""
    memory_db = tmp_path / "lingji_memory.db"
    _seed_memory_db(memory_db)
    settings = _Settings(memory_db, ollama_server)
    settings.distill_model = ""
    settings.llm_model = "test-chat-huge:latest"  # 已安装：作为设计默认应被采用
    distiller = KnowledgeDistiller(settings)
    distiller.run_once(limit=10)
    assert distiller.list_entries(limit=1)["items"][0]["model"] == "test-chat-huge:latest"


def test_unparsable_answer_is_recorded_and_retried(tmp_path: Path, ollama_server: str, monkeypatch: pytest.MonkeyPatch) -> None:
    distiller = _distiller(tmp_path, ollama_server)
    monkeypatch.setattr(distiller, "_chat", lambda model, messages: "这不是 JSON")
    result = distiller.run_once(limit=10)
    assert result["failed"] == 2
    monkeypatch.undo()
    recovered = distiller.run_once(limit=10)
    assert recovered["distilled"] == 2


def test_progress_reports_activity_and_results(tmp_path: Path, ollama_server: str) -> None:
    distiller = _distiller(tmp_path, ollama_server)
    before = distiller.progress()
    assert before["active"] is False
    distiller.run_once(limit=10)
    progress = distiller.progress()
    assert progress["active"] is False  # 本轮结束后不再有进行中的对话
    assert progress["cumulative_distilled"] == 2
    assert len(progress["finished"]) == 2
    assert all(item["ok"] for item in progress["finished"])
    assert progress["model"] == "test-chat:latest"


def test_model_override_switches_live(tmp_path: Path, ollama_server: str) -> None:
    memory_db = tmp_path / "lingji_memory.db"
    _seed_memory_db(memory_db)
    current = {"value": ""}
    distiller = KnowledgeDistiller(_Settings(memory_db, ollama_server), model_override=lambda: current["value"])
    current["value"] = "test-chat-huge:latest"
    distiller.run_once(limit=10)
    assert distiller.list_entries(limit=1)["items"][0]["model"] == "test-chat-huge:latest"
    # 覆盖清空后回到自动（最小 chat 模型）
    current["value"] = ""
    distiller._model = None
    assert distiller._resolve_model() == "test-chat:latest"


def test_installed_models_marks_active_and_sorts_by_size(tmp_path: Path, ollama_server: str) -> None:
    memory_db = tmp_path / "lingji_memory.db"
    _seed_memory_db(memory_db)
    distiller = KnowledgeDistiller(_Settings(memory_db, ollama_server))
    models = distiller.installed_models()
    names = [entry["name"] for entry in models]
    assert names == ["test-chat:latest", "test-chat-huge:latest"]  # embedding 模型被排除，小模型在前
    assert models[0]["active"] is True
    assert models[1]["active"] is False


class _ZhipuHandler(BaseHTTPRequestHandler):
    """假的智谱 chat/completions 服务。"""
    fail = False
    lock = threading.Lock()

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        if _ZhipuHandler.fail:
            self.send_response(502)
            self.end_headers()
            return
        body = json.dumps({
            "choices": [{"message": {"content": json.dumps({
                "short_title": "测试云端标题",
                "summary": "云端提炼的总结",
                "key_points": ["云端要点"],
                "category": "技术",
            }, ensure_ascii=False)}}]
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: Any) -> None:
        return


@pytest.fixture()
def zhipu_server():
    _ZhipuHandler.fail = False
    server = HTTPServer(("127.0.0.1", 0), _ZhipuHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_zhipu_provider_distills_via_cloud_and_falls_back(tmp_path: Path, ollama_server: str, zhipu_server: str) -> None:
    """云端服务可用时走 GLM-4-Flash；云端故障自动回退本机模型。"""
    import urllib.request

    class _Rewriter(_OllamaHandler):
        """把 distiller 的 zhipu URL 指向本地假服务的最小 monkeypatch 载体。"""

    memory_db = tmp_path / "lingji_memory.db"
    _seed_memory_db(memory_db)
    current = {"provider": "local", "key": ""}

    from src.automatic_memory import distillation as distillation_module

    distiller = KnowledgeDistiller(_Settings(memory_db, ollama_server),
                                   provider_override=lambda: current["provider"],
                                   api_key_override=lambda: current["key"])
    # 把云端 URL 重写到假服务
    original_url = distiller._ZHIPU_URL
    distiller._ZHIPU_URL = zhipu_server + "/chat/completions"

    current["provider"] = "zhipu"
    current["key"] = "test-key"
    result = distiller.run_once(limit=10)
    assert result["status"] == "ok"
    assert distiller.list_entries(limit=1)["items"][0]["model"] == "glm-4-flash"

    # 云端故障 → 自动回退本机
    _ZhipuHandler.fail = True
    memory_db2 = tmp_path / "lingji_memory2.db"
    _seed_memory_db(memory_db2)
    distiller2 = KnowledgeDistiller(_Settings(memory_db2, ollama_server),
                                    provider_override=lambda: "zhipu",
                                    api_key_override=lambda: "test-key")
    distiller2._ZHIPU_URL = zhipu_server + "/chat/completions"
    result2 = distiller2.run_once(limit=10)
    assert result2["status"] == "ok"
    assert result2["distilled"] == 2, "云端失败必须回退本机完成提炼"
    assert distiller2.list_entries(limit=1)["items"][0]["model"] == "test-chat:latest"
    _ = original_url, _Rewriter
