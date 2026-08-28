from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from src.automatic_memory import AuthorizationScope, SourceRegistry
from src.extraction.bootstrap import build_extraction_pipeline
from src.gateway.bootstrap import build_memory_gateway
from src.retrieval.memory_db import MemoryDatabase
from src.retrieval.hybrid import HybridRetriever, SearchFilters
from src.retrieval.source_authority import SourceAuthorityResolver
from src.sources.read_model import SourceReadModel
from src.storage import StateDatabase


def _settings(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        storage_path=root / "storage",
        state_db_path=root / "storage" / "lingji_state.db",
        memory_db_path=root / "storage" / "lingji_memory.db",
        vault_path=root / "vault",
        runtime_settings_file="runtime_settings.json",
        scheduler_poll_seconds=0.05,
        extraction_poll_seconds=0.05,
        extraction_batch_size=1,
        extraction_max_attempts=1,
        extraction_lease_heartbeat_seconds=2,
        extraction_stale_after_seconds=30,
        embedding_enabled=False,
        semantic_enabled=False,
        semantic_batch_size=16,
        memory_chunk_max_chars=1400,
        memory_chunk_overlap_chars=180,
        memory_search_cache_size=0,
        memory_search_cache_ttl_seconds=0,
        qdrant_distance="cosine",
        qdrant_timeout_seconds=1,
        qdrant_collection_schema="v1",
        vault_auto_init=True,
        index_private=False,
        workspace_name="acceptance",
        production_qdrant_collection="",
        vault_dir=str(root / "vault"),
        vault_layout_version="1",
        log_path=root / "logs",
        runtime_settings_path=root / "storage" / "runtime_settings.json",
    )


def _history(path: Path, message: str, *, timestamp: str = "2026-08-27T00:00:00Z") -> None:
    path.write_text(json.dumps({
        "schema": "lingji.history.inbox",
        "schema_version": "1",
        "conversations": [{
            "conversation_id": "conversation-task6s",
            "title": "Task6S conversation",
            "messages": [{"message_id": "message-task6s", "role": "assistant", "content": message, "timestamp": timestamp}],
        }],
    }), encoding="utf-8")


def _automatic(root: Path, message: str):
    settings = _settings(root)
    source_path = root / "history.json"
    _history(source_path, message)
    state = StateDatabase(settings.state_db_path)
    registry = SourceRegistry(state)
    authorized = registry.register(
        AuthorizationScope(
            grant_id="grant-task6s",
            source_kinds=("generic_ai_history",),
            roots=(str(root),),
            granted_at=datetime.now(timezone.utc),
            expires_at=None,
            owner_confirmed=True,
        ),
        "generic_ai_history",
        str(root),
    )
    pipeline = build_extraction_pipeline(settings)
    pipeline.execute(
        "generic_ai_history",
        input_path=source_path,
        payload={"source_id": authorized.source_id},
        options={"automatic_memory": True},
        execution_id="task6s-v1",
    )
    gateway = build_memory_gateway(settings, rebuild_if_empty=False)
    return settings, source_path, state, registry, authorized, pipeline, gateway


def test_natural_grant_expiry_is_fail_closed_without_lifecycle_callback(tmp_path: Path):
    settings, source, state, registry, authorized, pipeline, gateway = _automatic(tmp_path, "natural expiry evidence")
    del source, pipeline, registry
    try:
        assert gateway.search_memory("chatgpt", "natural expiry evidence")["results"]
        with state._connection() as connection:
            connection.execute(
                "UPDATE automatic_memory_grants SET expires_at = ? WHERE grant_id = ?",
                ((datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(), "grant-task6s"),
            )
        assert state.list_automatic_memory_sources(now=datetime.now(timezone.utc).isoformat())[0]["status"] == "expired"
        assert gateway.search_memory("chatgpt", "natural expiry evidence")["results"] == []
    finally:
        gateway.close()


def test_projection_observer_failure_does_not_reopen_revoked_current_evidence(tmp_path: Path):
    settings, source, state, registry, authorized, pipeline, gateway = _automatic(tmp_path, "observer failure evidence")
    del settings, source, state, pipeline
    registry.add_lifecycle_listener(lambda _source: (_ for _ in ()).throw(RuntimeError("projection unavailable")))
    try:
        registry.revoke(authorized.source_id)
        assert gateway.search_memory("chatgpt", "observer failure evidence")["results"] == []
    finally:
        gateway.close()


def test_revoke_linearization_blocks_inflight_upsert_from_returning_current(tmp_path: Path, monkeypatch):
    settings, source, state, registry, authorized, pipeline, gateway = _automatic(tmp_path, "revoke race evidence")
    entered = threading.Event()
    release = threading.Event()
    original = pipeline.structured_sink.read_model._upsert_source

    def blocked(connection, record):
        entered.set()
        assert release.wait(5)
        return original(connection, record)

    monkeypatch.setattr(pipeline.structured_sink.read_model, "_upsert_source", blocked)
    errors: list[BaseException] = []

    def run():
        try:
            pipeline.execute(
                "generic_ai_history", input_path=source,
                payload={"source_id": authorized.source_id},
                options={"automatic_memory": True}, execution_id="task6s-race",
            )
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=run)
    thread.start()
    assert entered.wait(5)
    registry.revoke(authorized.source_id)
    release.set()
    thread.join(10)
    try:
        assert not errors
        assert gateway.search_memory("chatgpt", "revoke race evidence")["results"] == []
    finally:
        gateway.close()


def test_state_authority_unavailable_fails_closed_with_truthful_diagnostic(tmp_path: Path):
    settings, source, state, registry, authorized, pipeline, gateway = _automatic(tmp_path, "authority outage evidence")
    del source, state, registry, authorized, pipeline
    class BrokenState:
        def list_automatic_memory_sources(self, **_kwargs):
            raise OSError("state database locked")
    try:
        gateway.retriever.source_authority.state_db = BrokenState()
        outcome = gateway.retriever.search_with_diagnostics("authority outage evidence")
        assert outcome["results"] == []
        assert outcome["diagnostics"]["source_authority"] == "unavailable"
        assert outcome["diagnostics"]["reason_code"] == "source_authority_unavailable"
    finally:
        gateway.close()


def test_explicit_current_cache_hit_rechecks_source_authority(tmp_path: Path):
    settings, source, state, registry, authorized, pipeline, gateway = _automatic(tmp_path, "cached authority evidence")
    del source, pipeline, registry
    try:
        retriever = HybridRetriever(
            gateway.database,
            source_authority=SourceAuthorityResolver(state),
            cache_size=8,
            cache_ttl_seconds=120,
        )
        # Evaluate after the fixture ingestion; a midnight timestamp can be
        # earlier than the projection's valid_from on hosts whose clock is
        # already later on the same day.
        filters = SearchFilters(
            mode="current",
            as_of=datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        )
        assert retriever.search("cached authority evidence", filters=filters)
        state.revoke_automatic_memory_source_atomic(
            authorized.source_id,
            revoked_at=datetime.now(timezone.utc).isoformat(),
            reason="cache authority test",
        )
        assert retriever.search("cached authority evidence", filters=filters) == []
    finally:
        gateway.close()


def test_structured_rebuild_archives_active_orphan_projection(tmp_path: Path):
    settings, source, state, registry, authorized, pipeline, gateway = _automatic(tmp_path, "orphan projection evidence")
    del source, state, registry, authorized, pipeline
    try:
        model = SourceReadModel(MemoryDatabase(settings.memory_db_path))
        model.rebuild([])
        rebuilt = gateway.database.sync_structured_evidence()
        assert rebuilt["documents"] == 0
        assert gateway.search_memory("chatgpt", "orphan projection evidence")["results"] == []
        history = gateway.search_memory("chatgpt", "orphan projection evidence", mode="history")
        assert history["results"]
        assert history["results"][0]["status"] == "archived"
    finally:
        gateway.close()


def test_context_pack_linked_automatic_evidence_uses_same_authority_guard(tmp_path: Path):
    settings, source, state, registry, authorized, pipeline, gateway = _automatic(tmp_path, "linked revoked evidence")
    try:
        ordinary_path = tmp_path / "ordinary.md"
        ordinary_path.write_text("ordinary anchor", encoding="utf-8")
        gateway.database.upsert_from_entry(
            {"id": "ordinary-anchor", "title": "Ordinary anchor", "memory_type": "note", "memory_tier": "archival"},
            ordinary_path,
        )
        doc = next(d for d in gateway.database.list_documents() if d["memory_type"] == "structured_evidence")
        message_id = doc["relationships"]["message_id"]
        SourceReadModel(gateway.database).link_message_memory(message_id, "ordinary-anchor")
        registry.revoke(authorized.source_id)
        pack = gateway.build_context_pack("chatgpt", query="ordinary anchor", include_core=False)
        assert not [section for section in pack["sections"] if section["kind"] == "raw_message_evidence"]
    finally:
        gateway.close()


def test_content_update_keeps_current_new_and_history_old_with_as_of(tmp_path: Path):
    settings, source, state, registry, authorized, pipeline, gateway = _automatic(tmp_path, "VERSION ONE evidence")
    del state, registry
    try:
        before = [d for d in gateway.database.list_documents() if d["memory_type"] == "structured_evidence"]
        assert len(before) == 1
        old_valid_from = before[0]["valid_from"]
        _history(source, "VERSION TWO evidence", timestamp="2026-08-28T00:00:00Z")
        pipeline.execute(
            "generic_ai_history", input_path=source,
            payload={"source_id": authorized.source_id},
            options={"automatic_memory": True}, execution_id="task6s-v2",
        )
        current = gateway.search_memory("chatgpt", "VERSION TWO evidence")["results"]
        history_old = gateway.search_memory("chatgpt", "VERSION ONE evidence", mode="history")["results"]
        assert current and not gateway.search_memory("chatgpt", "VERSION ONE evidence")["results"]
        assert history_old
        docs = [d for d in gateway.database.list_documents() if d["memory_type"] == "structured_evidence"]
        assert len(docs) == 2
        current_hash = current[0]["relationships"]["content_hash"]
        old = next(d for d in docs if d["relationships"]["content_hash"] != current_hash)
        new = next(d for d in docs if d["relationships"]["content_hash"] == current_hash)
        assert old["status"] == "superseded"
        assert old["superseded_by"] == new["memory_id"]
        assert old["memory_id"] in new["relationships"]["supersedes"]
        assert old["relationships"]["supersession_reason"]
        assert gateway.search_memory("chatgpt", "VERSION ONE evidence", mode="as_of", as_of=old_valid_from)["results"]
    finally:
        gateway.close()


def test_same_bytes_and_cross_source_versions_are_independent(tmp_path: Path):
    settings, source, state, registry, authorized, pipeline, gateway = _automatic(tmp_path, "same bytes evidence")
    del state, registry
    try:
        first = [d for d in gateway.database.list_documents() if d["memory_type"] == "structured_evidence"]
        pipeline.execute(
            "generic_ai_history", input_path=source,
            payload={"source_id": authorized.source_id}, options={"automatic_memory": True}, execution_id="task6s-replay",
        )
        second = [d for d in gateway.database.list_documents() if d["memory_type"] == "structured_evidence"]
        assert len(first) == len(second) == 1
        assert first[0]["memory_id"] == second[0]["memory_id"]
    finally:
        gateway.close()


def test_ordered_raw_snapshot_replay_rebuilds_versions(tmp_path: Path):
    settings = _settings(tmp_path)
    v1 = tmp_path / "v1.json"
    v2 = tmp_path / "v2.json"
    _history(v1, "replay VERSION ONE")
    _history(v2, "replay VERSION TWO", timestamp="2026-08-28T00:00:00Z")
    state = StateDatabase(settings.state_db_path)
    registry = SourceRegistry(state)
    authorized = registry.register(
        AuthorizationScope(
            grant_id="grant-replay",
            source_kinds=("generic_ai_history",), roots=(str(tmp_path),),
            granted_at=datetime.now(timezone.utc), expires_at=None, owner_confirmed=True,
        ), "generic_ai_history", str(tmp_path),
    )
    pipeline = build_extraction_pipeline(settings)
    replayed = pipeline.replay_automatic_snapshots(
        "generic_ai_history", [v1, v2], source_id=authorized.source_id,
        execution_id_prefix="task6s-replay",
    )
    assert len(replayed) == 2
    gateway = build_memory_gateway(settings, rebuild_if_empty=False)
    try:
        db = gateway.database
        docs = [d for d in db.list_documents() if d["memory_type"] == "structured_evidence"]
        assert len(docs) == 2
        assert gateway.search_memory("chatgpt", "replay VERSION ONE", mode="history")["results"]
        assert gateway.search_memory("chatgpt", "replay VERSION TWO")["results"]
    finally:
        gateway.close()


def test_ordinary_memory_is_not_rejected_by_automatic_source_guard(tmp_path: Path):
    db = MemoryDatabase(tmp_path / "memory.db")
    (tmp_path / "ordinary.md").write_text("ordinary Obsidian memory", encoding="utf-8")
    db.upsert_from_entry({"id": "ordinary", "title": "Obsidian", "memory_type": "note", "memory_tier": "archival"}, tmp_path / "ordinary.md")
    from src.retrieval.hybrid import HybridRetriever
    assert HybridRetriever(db).search("ordinary Obsidian memory")
