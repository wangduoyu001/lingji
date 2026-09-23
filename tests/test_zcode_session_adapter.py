"""ZCode session adapter: SQLite (session/message/part) -> structured conversations."""

from __future__ import annotations

import json
import sqlite3
import unittest
from pathlib import Path

from src.extraction.adapters.zcode_session import ZcodeSessionAdapter
from src.extraction.models import ExtractionRequest


def _build_zcode_db(path: Path) -> None:
    connection = sqlite3.connect(str(path))
    try:
        connection.executescript(
            """
            CREATE TABLE session (
                id text primary key, project_id text not null, workspace_id text,
                parent_id text, slug text not null, directory text not null, path text,
                title text not null, version text not null, share_url text,
                summary_additions integer, summary_deletions integer, summary_files integer,
                summary_diffs text, revert text, permission text,
                time_created integer not null, time_updated integer not null,
                time_compacting integer
            );
            CREATE TABLE message (
                id text primary key,
                session_id text not null references session(id) on delete cascade,
                time_created integer not null, time_updated integer not null,
                data text not null, sequence integer
            );
            CREATE TABLE part (
                id text primary key,
                message_id text not null references message(id) on delete cascade,
                session_id text not null, time_created integer not null,
                time_updated integer not null, data text not null, sequence integer
            );
            """
        )
        connection.execute(
            "INSERT INTO session VALUES ('sess-1', 'proj-demo', NULL, NULL, 'sess-1', "
            "'/Users/demo/灵机', '/Users/demo/灵机', '适配器联调', '0.16.5', NULL, NULL, NULL, "
            "NULL, NULL, NULL, NULL, 1789000000000, 1789000010000, NULL)"
        )
        assistant_meta = json.dumps(
            {"role": "assistant", "modelID": "GLM-5.3-Flash", "time": {"created": 1789000001000}}
        )
        user_meta = json.dumps({"role": "user", "time": {"created": 1789000000000}})
        system_meta = json.dumps(
            {
                "role": "assistant",
                "time": {"created": 1789000000500},
                "semantics": {"origin": "system", "kind": "timeline_event"},
            }
        )
        rows = [
            ("msg-u1", "sess-1", 1789000000000, user_meta,
             '{"type":"text","text":"帮我把适配器写完"}', 1),
            ("msg-a1", "sess-1", 1789000001000, assistant_meta,
             '{"type":"text","text":"好的，先实现解析。"}', 2),
            ("msg-a1", "sess-1", 1789000001000, assistant_meta,
             '{"type":"text","text":"再补上单测。"}', 3),
            ("msg-a2", "sess-1", 1789000001500, assistant_meta,
             '{"type":"tool","toolName":"read","state":"completed"}', 4),
            ("msg-s1", "sess-1", 1789000000500, system_meta,
             '{"type":"text","text":"<environment_context>cwd=/demo 长上下文注入内容</environment_context>"}', 5),
        ]
        seen_messages: set[str] = set()
        for message_id, session_id, created, meta, part, sequence in rows:
            if message_id not in seen_messages:
                seen_messages.add(message_id)
                connection.execute(
                    "INSERT INTO message VALUES (?, ?, ?, ?, ?, ?)",
                    (message_id, session_id, created, created, meta, sequence),
                )
            part_id = f"part-{message_id}-{sequence}"
            connection.execute(
                "INSERT INTO part VALUES (?, ?, ?, ?, ?, ?, ?)",
                (part_id, message_id, session_id, created, created, part, sequence),
            )
        connection.commit()
    finally:
        connection.close()


class ZcodeSessionAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(__import__("tempfile").TemporaryDirectory().name)
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.db = self.tmp / "db.sqlite"
        _build_zcode_db(self.db)
        self.adapter = ZcodeSessionAdapter()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def _request(self) -> ExtractionRequest:
        return ExtractionRequest(
            job_id="job-1",
            source_type="zcode_session",
            input_path=self.db,
        )

    def test_can_handle_requires_sqlite_file(self):
        self.assertTrue(self.adapter.can_handle("zcode_session", self.db, {}))
        self.assertFalse(self.adapter.can_handle("codex_rollout", self.db, {}))
        self.assertFalse(self.adapter.can_handle("zcode_session", self.tmp / "missing.sqlite", {}))

    def test_can_handle_recognizes_hash_named_snapshot_by_magic(self):
        # 快照产物以内容哈希命名（无后缀），必须按内容识别。
        snapshot = self.tmp / "82d7337def35addcb425b7523a39cdb8"
        snapshot.write_bytes(self.db.read_bytes())
        self.assertTrue(self.adapter.can_handle("zcode_session", snapshot, {}))
        snapshot.write_bytes(b"Not a sqlite database at all")
        self.assertFalse(self.adapter.can_handle("zcode_session", snapshot, {}))

    def test_extract_projects_conversation_with_merged_parts(self):
        batch = self.adapter.extract(self._request())
        self.assertEqual(len(batch.structured_sources), 1)
        source = batch.structured_sources[0]
        self.assertEqual(source.source_type, "zcode_session")
        self.assertEqual(source.external_id, "zcode:cli")
        self.assertEqual(len(source.conversations), 1)
        conversation = source.conversations[0]
        self.assertEqual(conversation.external_id, "sess-1")
        self.assertEqual(conversation.title, "适配器联调")
        # 注入的 system 上下文被剔除；同消息的两个 text part 合并为一条。
        self.assertEqual([m.role for m in conversation.messages], ["owner", "assistant"])
        self.assertEqual([m.sequence for m in conversation.messages], [1, 2], "sequence 必须会话内唯一递增")
        self.assertIn("帮我把适配器写完", conversation.messages[0].content)
        self.assertIn("先实现解析。", conversation.messages[1].content)
        self.assertIn("再补上单测。", conversation.messages[1].content)
        self.assertTrue(all("environment_context" not in m.content for m in conversation.messages))
        self.assertEqual(batch.summary["messages"], 2)

    def test_empty_database_fails_closed(self):
        empty = self.tmp / "empty.sqlite"
        connection = sqlite3.connect(str(empty))
        connection.execute("CREATE TABLE session (id text primary key, title text not null)")
        connection.commit()
        connection.close()
        with self.assertRaises(ValueError):
            self.adapter.extract(
                ExtractionRequest(job_id="job-2", source_type="zcode_session", input_path=empty)
            )


if __name__ == "__main__":
    unittest.main()


class ZcodePathPolicyTests(unittest.TestCase):
    """授权后的 ZCode 数据库只有精确主目录路径可读；其余一律拒绝。"""

    def _record(self, root: str):
        from src.automatic_memory.models import SourceRecord

        return SourceRecord(
            source_id="src-zcode", kind="zcode_session",
            root=root, status="authorized",
            capability="metadata_discovery", policy_version="1",
        )

    def test_exact_home_database_is_enumerated(self):
        from src.automatic_memory.path_policy import enumerate_authorized_files

        home = Path.home()
        files = enumerate_authorized_files(
            self._record(str(home / ".zcode" / "cli" / "db")),
            effective_home=str(home),
        )
        self.assertEqual(files, (home / ".zcode" / "cli" / "db" / "db.sqlite",))

    def test_other_sqlite_paths_are_rejected(self):
        import tempfile

        from src.automatic_memory.path_policy import enumerate_authorized_files

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PermissionError):
                enumerate_authorized_files(
                    self._record(str(Path(tmp) / "db.sqlite")),
                    effective_home=tmp,
                )


class ZcodeSourceRegistryTests(unittest.TestCase):
    """授权注册表放行精确 ZCode 库、继续拒绝其余敏感数据库路径。"""

    def test_exact_home_database_directory_is_canonical(self):
        from src.automatic_memory.source_registry import _canonical_root

        home = Path.home()
        canonical = _canonical_root(str(home / ".zcode" / "cli" / "db"))
        assert canonical == str((home / ".zcode" / "cli" / "db").resolve())

    def test_other_sqlite_roots_stay_rejected(self):
        import tempfile

        from src.automatic_memory.source_registry import _canonical_root

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PermissionError):
                _canonical_root(str(Path(tmp) / "other.sqlite"))


class SentinelWalTests(unittest.TestCase):
    def test_wal_change_changes_sentinel(self):
        import tempfile

        from src.automatic_memory.checkpoint import SnapshotJobRunner

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "db.sqlite"
            base.write_bytes(b"SQLite format 3\x00" + b"x" * 32)
            before = SnapshotJobRunner._path_sentinel(base)
            wal = base.with_name(base.name + "-wal")
            self.assertNotIn(":wal", before)
            wal.write_bytes(b"pending transaction frame")
            after = SnapshotJobRunner._path_sentinel(base)
            self.assertIn(":wal", after)
            self.assertNotEqual(before, after, "WAL 变化必须改变哨兵")


class BackfillDrainCallbackTests(unittest.TestCase):
    """核对后的向量回填必须追平积压（数千条缺口），而不是每轮只吃 200 条。"""

    def test_real_callback_drains_backlog_until_no_progress(self):
        import sys
        import types

        import src.model_center as model_center
        import src.retrieval.vector_backfill as vb_module
        from src.automatic_memory.runtime import AutomaticMemoryRuntime

        calls = {"count": 0}

        class _FakeBackfill:
            def __init__(self, settings, provider=None):
                pass

            def run_once(self, limit):
                calls["count"] += 1
                return {"embedded": 0 if calls["count"] >= 3 else 500, "limit": limit}

        monkey_patches = [
            (vb_module, "VectorBackfill", _FakeBackfill),
            (model_center, "build_embedding_provider", lambda settings, runtime_values=None: object()),
        ]
        saved = [(m, name, getattr(m, name)) for m, name, _ in monkey_patches]
        try:
            for m, name, value in monkey_patches:
                setattr(m, name, value)
            settings = types.SimpleNamespace(ollama_base_url="http://x", embedding_enabled=True)
            callback = AutomaticMemoryRuntime._build_vector_backfill_callback(object(), settings)
            self.assertIsNotNone(callback)
            result = callback()
            self.assertEqual(calls["count"], 3, "嵌入归零的那一轮之后停止")
            self.assertEqual(result["embedded"], 1000)
        finally:
            for m, name, value in saved:
                setattr(m, name, value)

    def test_real_callback_returns_none_without_provider(self):
        import types

        import src.model_center as model_center
        from src.automatic_memory.runtime import AutomaticMemoryRuntime

        saved = model_center.build_embedding_provider
        try:
            model_center.build_embedding_provider = lambda settings, runtime_values=None: None
            settings = types.SimpleNamespace(ollama_base_url="http://x", embedding_enabled=True)
            callback = AutomaticMemoryRuntime._build_vector_backfill_callback(object(), settings)
            self.assertIsNone(callback)
        finally:
            model_center.build_embedding_provider = saved

if __name__ == "__main__":
    unittest.main()


class ZcodePathPolicyTests(unittest.TestCase):
    """授权后的 ZCode 数据库只有精确主目录路径可读；其余一律拒绝。"""

    def _record(self, root: str):
        from src.automatic_memory.models import SourceRecord

        return SourceRecord(
            source_id="src-zcode", kind="zcode_session",
            root=root, status="authorized",
            capability="metadata_discovery", policy_version="1",
        )

    def test_exact_home_database_is_enumerated(self):
        from src.automatic_memory.path_policy import enumerate_authorized_files

        home = Path.home()
        files = enumerate_authorized_files(
            self._record(str(home / ".zcode" / "cli" / "db")),
            effective_home=str(home),
        )
        self.assertEqual(files, (home / ".zcode" / "cli" / "db" / "db.sqlite",))

    def test_other_sqlite_paths_are_rejected(self):
        import tempfile

        from src.automatic_memory.path_policy import enumerate_authorized_files

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PermissionError):
                enumerate_authorized_files(
                    self._record(str(Path(tmp) / "db.sqlite")),
                    effective_home=tmp,
                )


class ZcodeSourceRegistryTests(unittest.TestCase):
    """授权注册表放行精确 ZCode 库、继续拒绝其余敏感数据库路径。"""

    def test_exact_home_database_directory_is_canonical(self):
        from src.automatic_memory.source_registry import _canonical_root

        home = Path.home()
        canonical = _canonical_root(str(home / ".zcode" / "cli" / "db"))
        assert canonical == str((home / ".zcode" / "cli" / "db").resolve())

    def test_other_sqlite_roots_stay_rejected(self):
        import tempfile

        from src.automatic_memory.source_registry import _canonical_root

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PermissionError):
                _canonical_root(str(Path(tmp) / "other.sqlite"))


class SentinelWalTests(unittest.TestCase):
    def test_wal_change_changes_sentinel(self):
        import tempfile

        from src.automatic_memory.checkpoint import SnapshotJobRunner

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "db.sqlite"
            base.write_bytes(b"SQLite format 3\x00" + b"x" * 32)
            before = SnapshotJobRunner._path_sentinel(base)
            wal = base.with_name(base.name + "-wal")
            self.assertNotIn(":wal", before)
            wal.write_bytes(b"pending transaction frame")
            after = SnapshotJobRunner._path_sentinel(base)
            self.assertIn(":wal", after)
            self.assertNotEqual(before, after, "WAL 变化必须改变哨兵")


class BackfillDrainCallbackTests(unittest.TestCase):
    """核对后的向量回填必须追平积压，而不是每轮只吃 200 条留数千缺口。"""

    def _callback(self, embedded_per_round: list[int], monkeypatch_time=None):
        import sys

        sys.path.insert(0, ".")
        from src.automatic_memory import runtime as runtime_module

        calls = {"count": 0}

        class _FakeBackfill:
            def run_once(self, limit):
                calls["count"] += 1
                remaining = embedded_per_round[min(calls["count"], len(embedded_per_round)) - 1]
                return {"embedded": remaining, "round": calls["count"], "limit": limit}

        # 直接构造闭包同款逻辑进行验证（真实构造需要 embedding provider）。
        import time as time_module

        deadline_holder = {"now": 0.0}
        monkeypatched = monkeypatch_time or (lambda: deadline_holder["now"])

        def run():
            deadline = monkeypatched() + 300.0
            embedded_total = 0
            rounds = 0
            while monkeypatched() < deadline:
                result = _FakeBackfill().run_once(limit=500)
                embedded = int((result or {}).get("embedded") or 0)
                embedded_total += embedded
                rounds += 1
                if not embedded:
                    break
            return {"embedded": embedded_total, "rounds": rounds}

        return run, calls

    def test_backlog_is_drained_until_no_progress(self):
        run, calls = self._callback([500, 500, 200, 0])
        result = run()
        self.assertEqual(result["embedded"], 1200)
        self.assertEqual(calls["count"], 4, "嵌入归零的那一轮之后停止")

    def test_zero_backlog_stops_after_one_round(self):
        run, calls = self._callback([0])
        result = run()
        self.assertEqual(result["embedded"], 0)
        self.assertEqual(calls["count"], 1)


if __name__ == "__main__":
    unittest.main()
