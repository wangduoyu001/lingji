"""空快照跳过：空会话文件记为 skipped_empty 完成，不再伪装成适配器缺失。

背景（2026-09-24 主人指出）：生产队列 11 条失败里 10 条是空会话文件——
codex 适配器 schema 探测对空文件失败后被包装成 "No approved extraction
adapter"，与真失败混在一起无法排障。
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.automatic_memory import AuthorizationScope, SourceRegistry
from src.extraction.pipeline import ExtractionPipeline
from src.extraction.registry import AdapterRegistry
from src.storage import StateDatabase


def _authorized_codex_source(state_db: StateDatabase, root: Path, monkeypatch=None) -> str:
    if monkeypatch is not None:
        # 绕过"必须 ~/.codex/sessions"的真实家目录校验：单测用 tmp 根
        import src.automatic_memory.source_registry as registry_module

        monkeypatch.setattr(
            registry_module, "validate_codex_rollout_root",
            lambda r, eh=None: Path(r).resolve(),
        )
    registry = SourceRegistry(state_db)
    record = registry.register(
        AuthorizationScope(
            grant_id="grant-empty-skip",
            source_kinds=("codex_rollout",),
            roots=(str(root),),
            granted_at=datetime.now(timezone.utc),
            expires_at=None,
            owner_confirmed=True,
        ),
        "codex_rollout",
        str(root),
    )
    return record.source_id


def test_empty_snapshot_completes_as_skipped_empty(tmp_path: Path, monkeypatch):
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    empty = raw_root / ("0" * 63 + "0")
    empty.write_bytes(b"")  # 0 字节：空会话文件
    digest = hashlib.sha256(empty.read_bytes()).hexdigest()

    state_db = StateDatabase(tmp_path / "state" / "lingji_state.db")
    source_root = tmp_path / "source"
    source_root.mkdir()
    source_id = _authorized_codex_source(state_db, source_root, monkeypatch)

    pipeline = object.__new__(ExtractionPipeline)
    pipeline.queue = SimpleNamespace(path=tmp_path / "state" / "lingji_state.db")
    pipeline.sink = SimpleNamespace(raw_root=raw_root)
    pipeline.registry = AdapterRegistry()  # 无适配器：resolve 必然 LookupError
    pipeline.effective_home = None

    job = {
        "job_id": "LJ-JOB-EMPTY-TEST",
        "input_path": str(empty),
        "lease_token": "",
        "payload": {
            "source_id": source_id,
            "source_type": "codex_rollout",
            "raw_id": empty.name,
            "sha256": digest,
            "relative_path": "sessions/empty.jsonl",
        },
    }
    result = pipeline._execute_internal_snapshot(job)
    assert result["skipped_empty"] is True, "空快照必须记为 skipped_empty"
    assert result["adapter"] == "none"
    assert result["raw_snapshot"]["size"] == 0


def test_nonempty_unrecognized_snapshot_still_fails(tmp_path: Path, monkeypatch):
    """有内容但 schema 不认：保持 fail-closed，不吞成跳过。"""
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    junk = raw_root / ("1" * 63 + "1")
    junk.write_bytes(b"{ definitely not a known schema }\n")
    digest = hashlib.sha256(junk.read_bytes()).hexdigest()

    state_db = StateDatabase(tmp_path / "state2" / "lingji_state.db")
    source_root = tmp_path / "source2"
    source_root.mkdir()
    source_id = _authorized_codex_source(state_db, source_root, monkeypatch)

    pipeline = object.__new__(ExtractionPipeline)
    pipeline.queue = SimpleNamespace(path=tmp_path / "state2" / "lingji_state.db")
    pipeline.sink = SimpleNamespace(raw_root=raw_root)
    pipeline.registry = AdapterRegistry()
    pipeline.effective_home = None

    job = {
        "job_id": "LJ-JOB-JUNK-TEST",
        "input_path": str(junk),
        "lease_token": "",
        "payload": {
            "source_id": source_id,
            "source_type": "codex_rollout",
            "raw_id": junk.name,
            "sha256": digest,
            "relative_path": "sessions/junk.jsonl",
        },
    }
    try:
        pipeline._execute_internal_snapshot(job)
        raised = None
    except LookupError as exc:
        raised = exc
    assert raised is not None, "有内容的未知 schema 必须 fail-closed"
    assert "No approved extraction adapter" in str(raised)
