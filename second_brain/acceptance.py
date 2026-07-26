from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Callable

from second_brain.config import ROOT
from second_brain.models import ChatMessage, CodexTaskRequest, ConversationInput
from second_brain.runtime import Runtime
from second_brain.runtime_registry import RuntimeRegistry
from second_brain.utils import utc_now
from second_brain.watcher import BoundedWatcher


class AcceptanceService:
    def __init__(self, registry: RuntimeRegistry, api_url: str):
        self.registry = registry
        self.api_url = api_url

    def reset(self) -> dict:
        runtime = self.registry.reset_acceptance()
        return {"reset": True, "database": str(runtime.settings.database_path), "at": utc_now()}

    def run_all(self) -> dict:
        production_before = self._counts(self.registry.get("production"))
        runtime = self.registry.reset_acceptance()
        results: list[dict] = []
        evidence: dict[str, object] = {}

        def check(name: str, expected: str, operation: Callable[[], tuple[bool, object]]) -> None:
            started = time.perf_counter()
            try:
                passed, actual = operation()
                results.append(self._result(name, passed, expected, actual, started))
            except Exception as exc:
                results.append(self._result(name, False, expected, None, started, str(exc)))

        check(
            "system_health",
            "SQLite and embedded Qdrant ready; bge-m3 configured",
            lambda: (
                runtime.settings.database_path.exists()
                and runtime.vectors.status().get("ready") is True
                and runtime.embedder.status()["configured_model"] == "bge-m3",
                {"qdrant": runtime.vectors.status(), "embedding": runtime.embedder.status()},
            ),
        )

        conversation = ConversationInput(
            conversation_id="acceptance-chat-v1",
            source="acceptance",
            title="验收记忆提取",
            project="acceptance-project",
            messages=[
                ChatMessage(
                    role="user",
                    content=(
                        "以后必须先备份再升级。\n"
                        "最终决定采用独立第二大脑。\n"
                        "我喜欢直接看到测试结果。\n"
                        "下一步需要验证Codex回写。"
                    ),
                )
            ],
        )
        first = runtime.chats.import_conversation(conversation)
        evidence["conversation"] = first
        check("first_import", "first import succeeds", lambda: (first["imported"] is True, first))
        duplicate = runtime.chats.import_conversation(conversation)
        check("duplicate_import", "second import is deduplicated", lambda: (duplicate["duplicate"] is True, duplicate))

        candidates = runtime.distillation.distill(conversation_id=first["conversation_id"])
        evidence["candidates"] = [item["id"] for item in candidates]
        types = {item["memory_type"] for item in candidates}
        check(
            "distillation_types",
            "RULE, DECISION, PREFERENCE and TASK candidates",
            lambda: ({"RULE", "DECISION", "PREFERENCE", "TASK"}.issubset(types), sorted(types)),
        )

        plain = ConversationInput(
            conversation_id="acceptance-plain-v1",
            source="acceptance",
            title="普通解释",
            project="acceptance-project",
            messages=[ChatMessage(role="user", content="这是一段普通讨论，没有长期规则含义。")],
        )
        plain_result = runtime.chats.import_conversation(plain)
        plain_candidates = runtime.distillation.distill(conversation_id=plain_result["conversation_id"])
        check("plain_text_not_memory", "plain discussion creates zero candidates", lambda: (not plain_candidates, plain_candidates))

        rule = next(item for item in candidates if item["memory_type"] == "RULE")
        approved = runtime.memories.set_status(rule["id"], "active", "acceptance")
        check("approve_memory", "approved memory is active", lambda: (approved["status"] == "active", approved))
        task_candidate = next(item for item in candidates if item["memory_type"] == "TASK")
        rejected = runtime.memories.set_status(task_candidate["id"], "rejected", "acceptance")
        rejected_search = runtime.retrieval.search(task_candidate["content"], project="acceptance-project", active_only=True)
        check(
            "reject_excluded",
            "rejected memory is absent from active search",
            lambda: (all(item.get("id") != task_candidate["id"] for item in rejected_search), rejected),
        )

        conflict_old, _ = runtime.memories.create(
            "RULE", "冲突规则", "旧内容", "acceptance-project", "active", source_id=first["source_id"]
        )
        conflict_new, _ = runtime.memories.create(
            "RULE", "冲突规则", "新内容", "acceptance-project", "pending", source_id=first["source_id"]
        )
        runtime.memories.set_status(conflict_new["id"], "active", "acceptance")
        conflicts = runtime.conflicts.detect_for(conflict_new["id"])
        check("conflict_detection", "same-title differing rule creates conflict", lambda: (len(conflicts) > 0, conflicts))

        supersede_old, _ = runtime.memories.create("RULE", "覆盖规则", "旧规则", "acceptance-project", "active")
        superseded = runtime.memories.supersede(
            supersede_old["id"],
            None,
            {"memory_type": "RULE", "title": "覆盖规则", "content": "新规则", "project": "acceptance-project"},
            "acceptance",
        )
        check(
            "rule_supersede",
            "new active rule supersedes old rule",
            lambda: (
                superseded["old"]["status"] == "superseded" and superseded["new"]["status"] == "active",
                superseded,
            ),
        )
        check(
            "superseded_history",
            "old rule remains queryable as superseded",
            lambda: (runtime.memories.get(supersede_old["id"])["status"] == "superseded", supersede_old["id"]),
        )
        with runtime.database.connect() as connection:
            version_count = connection.execute(
                "SELECT COUNT(*) FROM memory_versions WHERE memory_id=?", (supersede_old["id"],)
            ).fetchone()[0]
            relation_count = connection.execute(
                "SELECT COUNT(*) FROM memory_relations WHERE to_memory_id=?", (supersede_old["id"],)
            ).fetchone()[0]
        check("version_relations", "version and relation history exist", lambda: (version_count >= 2 and relation_count >= 1, {"versions": version_count, "relations": relation_count}))

        search_results = runtime.retrieval.search("先备份再升级", project="acceptance-project", top_k=10)
        check("hybrid_search", "approved rule is retrievable", lambda: (any(item.get("id") == rule["id"] for item in search_results), search_results))
        context = runtime.retrieval.context("acceptance-project", "升级前应该做什么", 2000)
        check("codex_context", "context returns active rules", lambda: (len(context["active_rules"]) > 0, context))

        note = runtime.settings.obsidian_knowledge_dir / "acceptance-project" / "knowledge.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text("# 正式知识\n\n#验收\n\n" + "这是人工知识段落。" * 300, encoding="utf-8")
        memory_count_before = self._counts(runtime)["memories"]
        indexed = runtime.obsidian.index_file(note)
        memory_count_after = self._counts(runtime)["memories"]
        check("obsidian_chunking", "Obsidian document has multiple chunks and tags", lambda: (indexed.get("chunks", 0) > 1, indexed))
        check("obsidian_no_distill", "Obsidian indexing does not create memories", lambda: (memory_count_before == memory_count_after, {"before": memory_count_before, "after": memory_count_after}))

        codex = runtime.codex.record(
            CodexTaskRequest(
                project="acceptance-project",
                request="验证桌面UI",
                status="success",
                result="完成",
                files_changed=["second_brain/desktop/main.py"],
                tests=["desktop acceptance"],
            )
        )
        check("codex_writeback", "Codex task is stored", lambda: (codex["recorded"] is True, codex))

        with runtime.database.connect() as connection:
            source_messages = connection.execute(
                "SELECT COUNT(*) FROM messages msg JOIN conversations c ON c.id=msg.conversation_id WHERE c.source_id=?",
                (first["source_id"],),
            ).fetchone()[0]
            timeline_count = connection.execute(
                "SELECT (SELECT COUNT(*) FROM memories)+(SELECT COUNT(*) FROM tasks)"
            ).fetchone()[0]
            project_count = connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        check("source_trace", "source links to original messages", lambda: (source_messages > 0, source_messages))
        check("timeline_projects", "timeline and project data exist", lambda: (timeline_count > 0 and project_count > 0, {"timeline": timeline_count, "projects": project_count}))

        rebuilt = runtime.memories.rebuild_vectors()
        check("qdrant_rebuild", "Qdrant rebuild restores vectors", lambda: (rebuilt > 0 and runtime.vectors.status().get("vectors") == rebuilt, {"rebuilt": rebuilt, "status": runtime.vectors.status()}))

        watcher_payload = {
            "conversation_id": "acceptance-watcher-v1",
            "source": "acceptance_watcher",
            "title": "监听验收",
            "project": "acceptance-project",
            "messages": [{"role": "user", "content": "监听目录验收内容。"}],
        }
        watcher_file = runtime.settings.ai_inbox_dir / "watcher.json"
        watcher_file.parent.mkdir(parents=True, exist_ok=True)
        watcher_file.write_text(json.dumps(watcher_payload, ensure_ascii=False), encoding="utf-8")
        watcher = BoundedWatcher(self.api_url, runtime.settings, "acceptance")
        watcher_result = watcher.scan_once()
        check("watcher_scan", "bounded acceptance inbox scan imports one chat", lambda: (watcher_result["ai_chat"] == 1 and watcher_result["failed"] == 0, watcher_result))

        startup_files = ("start_lingji.bat", "start_lingji.py", "run_service.py")
        unchanged = subprocess.run(
            ["git", "diff", "--quiet", "master", "--", *startup_files],
            cwd=ROOT,
            check=False,
        ).returncode == 0
        check("original_isolation", "original startup chain is unchanged", lambda: (unchanged, startup_files))

        production_after = self._counts(self.registry.get("production"))
        check(
            "production_unchanged",
            "acceptance run does not alter production counts",
            lambda: (production_before == production_after, {"before": production_before, "after": production_after}),
        )

        report = {
            "workspace": "acceptance",
            "started_at": utc_now(),
            "passed": sum(1 for item in results if item["status"] == "passed"),
            "failed": sum(1 for item in results if item["status"] == "failed"),
            "results": results,
            "evidence": evidence,
        }
        self._save(report)
        return report

    def latest(self) -> dict:
        path = self._results_path()
        if not path.exists():
            return {"workspace": "acceptance", "passed": 0, "failed": 0, "results": []}
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def _save(self, report: dict) -> None:
        path = self._results_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    def _results_path(self) -> Path:
        return self.registry.acceptance_root / "results" / "latest.json"

    @staticmethod
    def _counts(runtime: Runtime) -> dict:
        with runtime.database.connect() as connection:
            return {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("sources", "conversations", "messages", "memories", "knowledge_documents", "tasks")
            }

    @staticmethod
    def _result(name: str, passed: bool, expected: str, actual: object, started: float, error: str | None = None) -> dict:
        return {
            "name": name,
            "status": "passed" if passed else "failed",
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "expected": expected,
            "actual": actual,
            "error": error,
        }

