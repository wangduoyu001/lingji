from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from src.extraction.bootstrap import build_extraction_pipeline
from src.gateway.bootstrap import build_memory_gateway
from src.retrieval.hybrid import SearchFilters
from src.retrieval.memory_db import MemoryDatabase
from src.sources.read_model import SourceReadModel


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


def _history(path: Path, *, source_message: str) -> None:
    path.write_text(
        json.dumps(
            {
                "schema": "lingji.history.inbox",
                "schema_version": "1",
                "conversations": [
                    {
                        "conversation_id": "conversation-lexical-1",
                        "title": "Lexical evidence conversation",
                        "messages": [
                            {
                                "message_id": "message-lexical-1",
                                "role": "assistant",
                                "content": source_message,
                                "timestamp": "2026-08-27T00:00:00Z",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_generic_pipeline_wires_structured_message_into_formal_gateway_lexical_search(tmp_path: Path):
    settings = _settings(tmp_path)
    source = tmp_path / "history.json"
    message = "packaged structured lexical evidence 7f3e"
    _history(source, source_message=message)

    pipeline = build_extraction_pipeline(settings)
    extracted = pipeline.execute("generic_ai_history", input_path=source, execution_id="exec-lexical")
    assert extracted["structured_read_model"]["messages"] == 1

    gateway = build_memory_gateway(settings, rebuild_if_empty=False)
    try:
        result = gateway.retriever.search_with_diagnostics(message, filters=SearchFilters())
        assert result["results"], result
        hit = result["results"][0]
        assert hit["memory_type"] == "structured_evidence"
        relationships = hit["relationships"]
        assert relationships["source_id"]
        assert relationships["conversation_id"]
        assert relationships["message_id"]
        assert relationships["content_hash"]
        assert relationships["role"] == "assistant"
        assert relationships["sequence"] == 0
        assert hit["text"].endswith(message)
    finally:
        gateway.close()


def test_structured_projection_is_idempotent_and_rebuildable_without_vault_markdown(tmp_path: Path):
    settings = _settings(tmp_path)
    source = tmp_path / "history.json"
    _history(source, source_message="idempotent structured evidence 8a2b")
    pipeline = build_extraction_pipeline(settings)

    first = pipeline.execute("generic_ai_history", input_path=source, execution_id="exec-1")
    second = pipeline.execute("generic_ai_history", input_path=source, execution_id="exec-2")
    db = MemoryDatabase(settings.memory_db_path)
    docs = [item for item in db.list_documents() if item["memory_type"] == "structured_evidence"]
    assert first["structured_read_model"]["lexical_index"]["added"] == 1
    assert second["structured_read_model"]["lexical_index"]["added"] == 0
    assert second["structured_read_model"]["lexical_index"]["updated"] == 0
    assert len(docs) == 1
    assert not list((settings.vault_path / "__structured__").glob("**/*"))

    db.remove_memory(docs[0]["memory_id"])
    assert not db.search_fts("idempotent structured evidence")
    rebuilt = db.rebuild_structured_evidence()
    assert rebuilt["documents"] == 1
    assert db.search_fts("idempotent structured evidence")[0]["memory_id"] == docs[0]["memory_id"]

    gateway = build_memory_gateway(settings, rebuild_if_empty=False)
    try:
        gateway.rebuild([], settings.vault_path)
        assert gateway.retriever.search("idempotent structured evidence")
    finally:
        gateway.close()


def test_empty_structured_message_is_not_materialized_as_lexical_document(tmp_path: Path):
    db = MemoryDatabase(tmp_path / "lingji_memory.db")
    source_model = SourceReadModel(db)
    source_model.upsert_bundle(
        {
            "source": {"source_type": "generic_ai_history", "external_id": "empty-source", "display_name": "Generic"},
            "conversations": [
                {
                    "external_id": "empty-conversation",
                    "title": "Empty",
                    "messages": [{"external_id": "empty-message", "role": "assistant", "content": "", "sequence": 0}],
                }
            ],
        }
    )
    result = db.sync_structured_evidence()
    assert result["documents"] == 0
    assert not [item for item in db.list_documents() if item["memory_type"] == "structured_evidence"]


def test_non_active_source_evidence_is_archived_out_of_current_search(tmp_path: Path):
    db = MemoryDatabase(tmp_path / "lingji_memory.db")
    source_model = SourceReadModel(db)
    bundle = {
        "source": {"source_type": "generic_ai_history", "external_id": "revoked-source", "display_name": "Generic"},
        "conversations": [
            {
                "external_id": "revoked-conversation",
                "title": "Revoked",
                "messages": [{"external_id": "revoked-message", "role": "assistant", "content": "revoked source evidence", "sequence": 0, "occurred_at": "2026-08-27T00:00:00Z"}],
            }
        ],
    }
    source_model.upsert_bundle(bundle)
    db.sync_structured_evidence()
    assert db.search_fts("revoked source evidence")

    source_id = source_model.list_sources(limit=10)["items"][0]["source_id"]
    source_model.upsert_source({"source_id": source_id, "source_type": "generic_ai_history", "external_id": "revoked-source", "status": "revoked"})
    db.sync_structured_evidence()
    assert not db.search_fts("revoked source evidence")
    assert db.search_fts("revoked source evidence", mode="history")


def test_same_external_message_identity_from_two_sources_stays_separate(tmp_path: Path):
    db = MemoryDatabase(tmp_path / "lingji_memory.db")
    source_model = SourceReadModel(db)
    for source_type, content in (("chatgpt", "same external identity source one"), ("generic_ai_history", "same external identity source two")):
        source_model.upsert_bundle(
            {
                "source": {"source_type": source_type, "external_id": "account", "display_name": source_type},
                "conversations": [
                    {
                        "external_id": "conversation",
                        "title": source_type,
                        "messages": [{"external_id": "message", "role": "user", "content": content, "sequence": 0}],
                    }
                ],
            }
        )
    result = db.sync_structured_evidence()
    assert result["documents"] == 2
    docs = [item for item in db.list_documents() if item["memory_type"] == "structured_evidence"]
    assert len({item["relationships"]["source_id"] for item in docs}) == 2
    assert len({item["relationships"]["message_id"] for item in docs}) == 2


def test_gateway_context_pack_keeps_structured_citation_when_semantic_client_fails(tmp_path: Path):
    settings = _settings(tmp_path)
    source = tmp_path / "history.json"
    _history(source, source_message="qdrant outage lexical evidence 9c4d")
    pipeline = build_extraction_pipeline(settings)
    pipeline.execute("generic_ai_history", input_path=source, execution_id="exec-qdrant")
    gateway = build_memory_gateway(settings, rebuild_if_empty=False)

    class FailingSemantic:
        def search(self, query, limit, filters=None):
            raise RuntimeError("qdrant unavailable")

    try:
        gateway.retriever.semantic_provider = FailingSemantic()
        search = gateway.search_memory("chatgpt", "qdrant outage lexical evidence")
        assert search["results"]
        hit = search["results"][0]
        assert hit["memory_type"] == "structured_evidence"
        assert hit["citation"]["message_id"]
        assert hit["citation"]["conversation_id"]
        assert hit["citation"]["source_id"]
        pack = gateway.build_context_pack(
            "chatgpt", query="qdrant outage lexical evidence", include_core=False
        )
        section = next(item for item in pack["sections"] if item["memory_id"] == hit["memory_id"])
        assert section["provenance_status"] == "structured"
        assert section["citation"]["message_id"] == hit["citation"]["message_id"]
        assert pack["diagnostics"]["semantic"] == "degraded"
        assert pack["diagnostics"]["reason_code"] == "semantic_query_failed"
    finally:
        gateway.close()


def test_formal_mcp_search_entry_returns_structured_message_citation(monkeypatch, tmp_path: Path):
    import sys
    import types

    settings = _settings(tmp_path)
    source = tmp_path / "history.json"
    _history(source, source_message="mcp structured evidence 2e6f")
    pipeline = build_extraction_pipeline(settings)
    pipeline.execute("generic_ai_history", input_path=source, execution_id="exec-mcp")
    gateway = build_memory_gateway(settings, rebuild_if_empty=False)

    class FakeMCP:
        def __init__(self, *args, **kwargs):
            self.tools = {}

        def tool(self, *args, **kwargs):
            def register(function):
                self.tools[function.__name__] = function
                return function

            return register

        def resource(self, *args, **kwargs):
            return lambda function: function

        def prompt(self, *args, **kwargs):
            return lambda function: function

    mcp_package = types.ModuleType("mcp")
    mcp_server_package = types.ModuleType("mcp.server")
    fastmcp_package = types.ModuleType("mcp.server.fastmcp")
    fastmcp_package.FastMCP = FakeMCP
    monkeypatch.setitem(sys.modules, "mcp", mcp_package)
    monkeypatch.setitem(sys.modules, "mcp.server", mcp_server_package)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fastmcp_package)
    monkeypatch.setattr(
        "src.mcp_server.PEMISIndex",
        lambda *args, **kwargs: types.SimpleNamespace(
            build_index=lambda: None,
            get_all=lambda: [],
            layout=types.SimpleNamespace(should_index=lambda *args, **kwargs: False),
        ),
    )
    monkeypatch.setattr("src.mcp_server.SkillRegistry", lambda *args, **kwargs: types.SimpleNamespace(status=lambda: {}))
    monkeypatch.setattr("src.mcp_server.MarkdownChunker", lambda *args, **kwargs: object())
    monkeypatch.setattr("src.mcp_server.register_codex_mcp_tools", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.mcp_server.register_project_context_tools", lambda *args, **kwargs: None)
    try:
        from src import mcp_server

        server = mcp_server.create_mcp_server(
            gateway=gateway,
            codex_service=object(),
            project_context_service=object(),
            extraction_pipeline=object(),
            default_agent_id="chatgpt",
        )
        result = server.tools["search_memory"]("mcp structured evidence")
        assert result["results"]
        assert result["results"][0]["memory_type"] == "structured_evidence"
        assert result["results"][0]["citation"]["message_id"]
    finally:
        gateway.close()
