"""Regressions for the real startup/recall/Core paths, using isolated stores."""
import sqlite3
import subprocess
import sys
from pathlib import Path

from src.config import Settings
from src.gateway.bootstrap import build_memory_gateway
from src.indexer.index import PEMISIndex
from src.retrieval import MemoryDatabase, HybridRetriever
from src.runtime import WorkspaceResolver
from tests.fixtures.workspace_paths import allow_test_workspace_root


def note(vault, relative, ident, text, *, core=False):
    path = vault / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nid: {ident}\ntitle: {text}\nmemory_type: knowledge\n"
        f"memory_tier: {'core' if core else 'archival'}\nstatus: active\n"
        "review_status: approved\nprivacy: private\nagent_scope: [all]\n"
        f"pin_to_context: {'true' if core else 'false'}\n---\n# {text}\n\n{text}\n",
        encoding="utf-8",
    )
    return path


def test_existing_index_opens_during_another_process_write(tmp_path):
    path = tmp_path / "index.db"
    MemoryDatabase(path)
    writer = sqlite3.connect(path)
    writer.execute("BEGIN IMMEDIATE")
    writer.execute("UPDATE memory_meta SET value=value WHERE key='revision'")
    try:
        try:
            result = subprocess.run(
                [sys.executable, "-c", "from src.retrieval import MemoryDatabase; import sys; print(MemoryDatabase(sys.argv[1]).fts_tokenizer)", str(path)],
                capture_output=True, text=True, timeout=3,
                cwd=Path(__file__).resolve().parents[1],
            )
        except subprocess.TimeoutExpired:
            result = None
        assert result is not None, "opening an existing index waited for a writer"
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() in {"trigram", "unicode61"}
    finally:
        writer.rollback()
        writer.close()


def test_semantic_gate_preserves_low_score_exact_match(tmp_path):
    vault = tmp_path / "vault"
    note(vault, "notes/exact.md", "EXACT", "薏仁")
    note(vault, "notes/noise.md", "NOISE", "太空航行记录")
    index = PEMISIndex(vault, tmp_path / "storage")
    index.build_index()
    db = MemoryDatabase(tmp_path / "index.db")
    db.rebuild_from_index(index.get_all(), vault)

    class Semantic:
        def search(self, query, limit, filters=None):
            return [{"memory_id": ident, "score": 0.2} for ident in ("EXACT", "NOISE")]

    retriever = HybridRetriever(db, Semantic(), semantic_min_score=0.55)
    results = retriever.search("薏仁")
    assert [r["memory_id"] for r in results] == ["EXACT"]
    assert "semantic" not in results[0]["retrieval_channels"]
    assert retriever.search("不存在的测试问题") == []


def test_nonempty_index_recovers_approved_core_without_erasing_existing_rows(tmp_path):
    with allow_test_workspace_root(tmp_path):
        settings = Settings(_env_file=None, workspace_root=str(tmp_path / "workspaces"),
                            semantic_enabled=False, vault_auto_init=False)
        workspace = WorkspaceResolver.resolve(settings, "acceptance", environ={}, project_root=tmp_path)
        vault = workspace.vault_path
        note(vault, "notes/retained.md", "RETAIN", "已有知识不能丢失")
        index = PEMISIndex(vault, workspace.storage_path)
        index.build_index()
        db = MemoryDatabase(workspace.memory_db_path)
        db.rebuild_from_index(index.get_all(), vault)
        core = note(vault, "03-Knowledge/Core-Memory/Preferences/core.md", "CORE", "回答保持简洁", core=True)
        original = core.read_bytes()
        gateway = build_memory_gateway(settings, workspace=workspace)
        assert [m["memory_id"] for m in gateway.get_core_memory("codex")["memories"]] == ["CORE"]
        assert gateway.database.fetch_memory("RETAIN") is not None
        assert core.read_bytes() == original
        revision = gateway.database.revision
        gateway.close()
        second = build_memory_gateway(settings, workspace=workspace)
        assert second.database.revision == revision
        second.close()


def test_core_identity_change_and_revocation_are_reconciled(tmp_path):
    from src.retrieval.incremental_sync import IncrementalMemorySynchronizer
    vault = tmp_path / 'vault'
    relative = '03-Knowledge/Core-Memory/preference.md'
    note(vault, relative, 'OLD', '旧偏好', core=True)
    db = MemoryDatabase(tmp_path / 'memory.db')
    sync = IncrementalMemorySynchronizer(db)
    sync.sync_core(vault, tmp_path / 'storage')
    path = note(vault, relative, 'NEW', '新偏好', core=True)
    sync.sync_core(vault, tmp_path / 'storage')
    assert db.fetch_memory('OLD') is None
    assert db.fetch_memory('NEW') is not None
    path.write_text(path.read_text().replace('review_status: approved', 'review_status: pending'))
    sync.sync_core(vault, tmp_path / 'storage')
    assert db.fetch_memory('NEW') is None


def test_invalid_semantic_output_still_reports_degradation(tmp_path):
    from src.retrieval.hybrid import SearchFilters
    class Semantic:
        def search(self, *args):
            return [{'memory_id': 'broken', 'score': float('nan')}]
    retriever = HybridRetriever(MemoryDatabase(tmp_path / 'db'), Semantic(), semantic_min_score=.55)
    results, status = retriever._semantic_search_with_status('query', 10, SearchFilters())
    assert results == []
    assert status['reason_code'] == 'semantic_results_invalid'


def test_owner_confirmed_timeless_core_matches_retrieval_current_state():
    from src.gateway.owner_memory_cards import OwnerMemoryCardProjector
    core = {'memory_tier': 'core', 'review_status': 'approved'}
    assert OwnerMemoryCardProjector._freshness(core, 'active', {})['state'] == 'current'
    assert OwnerMemoryCardProjector._freshness(core, 'archived', {})['state'] == 'archived'
    assert OwnerMemoryCardProjector._freshness(core, 'active', {'status':'revoked'})['state'] == 'source_revoked'
    assert OwnerMemoryCardProjector._freshness({'memory_tier':'derived'}, 'active', {})['state'] == 'unknown'
