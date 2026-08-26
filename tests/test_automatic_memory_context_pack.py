from __future__ import annotations

from pathlib import Path

from src.gateway.profiles import AIProfileRegistry
from src.gateway.memory_gateway import MemoryGateway
from src.obsidian.frontmatter import render_frontmatter
from src.retrieval import HybridRetriever, MarkdownChunker, MemoryDatabase
from src.retrieval.context_pack import ContextPackBuilder, ContextPackRequest
from src.retrieval.hybrid import SearchFilters
from src.sources import SourceQueryService, SourceReadModel


def _note(vault: Path, rel: str, memory_id: str, title: str, text: str, **extra: object) -> None:
    path = vault / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    values: dict[str, object] = {
        "id": memory_id,
        "title": title,
        "memory_type": "knowledge",
        "memory_tier": "archival",
        "status": "active",
        "review_status": "approved",
        "privacy": "private",
        "project": ["LingJi"],
        "tags": ["automatic-memory"],
        "valid_from": "2026-01-01T00:00:00Z",
    }
    values.update(extra)
    path.write_text(render_frontmatter(values, text), encoding="utf-8")


def _indexed(tmp_path: Path) -> tuple[MemoryDatabase, SourceReadModel, SourceQueryService]:
    vault = tmp_path / "vault"
    memory_db = MemoryDatabase(tmp_path / "lingji_memory.db")
    _note(
        vault,
        "03-Knowledge/core.md",
        "memory-core",
        "核心规则",
        "核心规则：统一记忆接口必须保留来源证据。",
        memory_tier="core",
        pin_to_context=True,
        agent_scope=["chatgpt"],
        authority="user_explicit",
    )
    _note(
        vault,
        "03-Knowledge/authority.md",
        "memory-authority",
        "项目权威决定",
        "项目权威决定：ContextPack 通过同一 MemoryGateway 输出。",
        authority="current_project_authority",
    )
    _note(
        vault,
        "03-Knowledge/old.md",
        "memory-old",
        "旧决定",
        "旧决定：ContextPack 不保留原始消息证据。",
        status="superseded",
        valid_to="2026-02-01T00:00:00Z",
        superseded_by="memory-authority",
        authority="old_chat_inference",
    )
    from src.indexer.index import PEMISIndex

    index = PEMISIndex(vault, tmp_path / "storage")
    index.build_index()
    memory_db.rebuild_from_index(index.get_all(), vault, MarkdownChunker())
    source_model = SourceReadModel(memory_db)
    source_model.upsert_bundle(
        {
            "source": {
                "source_id": "source-lingji",
                "source_type": "chatgpt",
                "external_id": "export-lingji",
                "display_name": "LingJi export",
                "privacy": "private",
                "projects": ["LingJi"],
                "agent_scope": ["chatgpt"],
            },
            "conversations": [
                {
                    "conversation_id": "conversation-a",
                    "external_id": "conversation-a",
                    "title": "ContextPack evidence",
                    "messages": [
                        {
                            "message_id": "message-a",
                            "external_id": "message-a",
                            "role": "user",
                            "sequence": 1,
                            "occurred_at": "2026-03-01T10:00:00Z",
                            "content": "ContextPack 通过同一 MemoryGateway 输出。",
                            "memory_links": [{"memory_id": "memory-authority"}],
                        },
                        {
                            "message_id": "message-duplicate",
                            "external_id": "message-duplicate",
                            "role": "assistant",
                            "sequence": 2,
                            "occurred_at": "2026-03-01T11:00:00Z",
                            "content": "ContextPack 通过同一 MemoryGateway 输出。",
                            "memory_links": [{"memory_id": "memory-authority"}],
                        },
                    ],
                }
            ],
        }
    )
    source_model.upsert_bundle(
        {
            "source": {
                "source_id": "source-wrong-project",
                "source_type": "chatgpt",
                "external_id": "export-other",
                "display_name": "Other project",
                "privacy": "private",
                "projects": ["Other"],
                "agent_scope": ["chatgpt"],
            },
            "conversations": [
                {
                    "conversation_id": "conversation-other",
                    "external_id": "conversation-other",
                    "title": "Other project evidence",
                    "messages": [
                        {
                            "message_id": "message-other",
                            "external_id": "message-other",
                            "role": "user",
                            "sequence": 1,
                            "content": "ContextPack 通过同一 MemoryGateway 输出。",
                            "memory_links": [{"memory_id": "memory-authority"}],
                        }
                    ],
                }
            ],
        }
    )
    service = SourceQueryService(
        source_model,
        workspace="acceptance",
        vault_path=tmp_path / "vault",
        raw_path=tmp_path / "raw",
        profiles=AIProfileRegistry(),
    )
    return memory_db, source_model, service


def test_context_pack_orders_memory_authority_and_linked_evidence_with_scope_ids(tmp_path: Path) -> None:
    database, source_model, service = _indexed(tmp_path)
    builder = ContextPackBuilder(
        database,
        HybridRetriever(database),
        source_read_model=source_model,
        source_query_service=service,
    )

    pack = builder.build(
        ContextPackRequest(
            agent_id="chatgpt",
            query="MemoryGateway 输出",
            project="LingJi",
            max_chars=12000,
        )
    )

    kinds = [section["kind"] for section in pack["sections"]]
    assert kinds[:2] == ["core_memory", "project_authority_memory"]
    evidence = [section for section in pack["sections"] if section["kind"] == "raw_message_evidence"]
    assert {item["message_id"] for item in evidence} == {"message-a", "message-duplicate"}
    assert all(item["source_id"] == "source-lingji" for item in evidence)
    assert all(item["conversation_id"] == "conversation-a" for item in evidence)
    assert all(item["memory_id"] == "memory-authority" for item in evidence)
    assert "message-other" not in pack["markdown"]
    assert "memory-authority" in pack["markdown"]


def test_context_pack_current_as_of_history_and_why_keep_temporal_reason(tmp_path: Path) -> None:
    database, source_model, service = _indexed(tmp_path)
    builder = ContextPackBuilder(
        database,
        HybridRetriever(database),
        source_read_model=source_model,
        source_query_service=service,
    )

    current = builder.build(ContextPackRequest(agent_id="chatgpt", query="决定", project="LingJi"))
    assert "memory-old" not in {item.get("memory_id") for item in current["sections"]}

    historical = builder.build(
        ContextPackRequest(
            agent_id="chatgpt",
            query="决定",
            project="LingJi",
            mode="history",
        )
    )
    assert "memory-old" in {item.get("memory_id") for item in historical["sections"]}
    assert all("lifecycle" in item and "observed_at" in item for item in historical["sections"])

    why = builder.build(
        ContextPackRequest(
            agent_id="chatgpt",
            query="决定",
            project="LingJi",
            mode="why",
        )
    )
    assert any(item.get("exclusion_reason") or item.get("why") for item in why["sections"])


def test_context_pack_reports_missing_provenance_when_memory_has_no_structured_link(tmp_path: Path) -> None:
    database, source_model, service = _indexed(tmp_path)
    builder = ContextPackBuilder(
        database,
        HybridRetriever(database),
        source_read_model=source_model,
        source_query_service=service,
    )

    pack = builder.build(
        ContextPackRequest(
            agent_id="chatgpt",
            query="核心规则",
            project="LingJi",
        )
    )

    core = next(item for item in pack["sections"] if item["memory_id"] == "memory-core")
    assert core["provenance_status"] == "missing"
    assert core["provenance_reason"] == "no_structured_message_link"


def test_context_pack_linked_evidence_enforces_agent_and_privacy_scope(tmp_path: Path) -> None:
    database, source_model, service = _indexed(tmp_path)
    source_model.upsert_bundle(
        {
            "source": {
                "source_id": "source-restricted",
                "source_type": "chatgpt",
                "external_id": "export-restricted",
                "display_name": "Restricted export",
                "privacy": "restricted",
                "projects": ["LingJi"],
                "agent_scope": ["claude"],
            },
            "conversations": [
                {
                    "conversation_id": "conversation-restricted",
                    "external_id": "conversation-restricted",
                    "title": "Restricted evidence",
                    "messages": [
                        {
                            "message_id": "message-restricted",
                            "external_id": "message-restricted",
                            "role": "user",
                            "sequence": 1,
                            "occurred_at": "2026-03-01T10:00:00Z",
                            "content": "不得越过 agent/privacy 边界的证据。",
                            "memory_links": [{"memory_id": "memory-authority"}],
                        }
                    ],
                }
            ],
        }
    )
    builder = ContextPackBuilder(
        database,
        HybridRetriever(database),
        source_read_model=source_model,
        source_query_service=service,
    )

    pack = builder.build(
        ContextPackRequest(
            agent_id="chatgpt",
            query="MemoryGateway 输出",
            project="LingJi",
        )
    )

    assert "message-restricted" not in pack["markdown"]
    assert all(item.get("message_id") != "message-restricted" for item in pack["sections"])


def test_gateway_and_direct_builder_have_identical_scoped_evidence_ids(tmp_path: Path) -> None:
    database, source_model, service = _indexed(tmp_path)
    retriever = HybridRetriever(database)
    builder = ContextPackBuilder(
        database,
        retriever,
        source_read_model=source_model,
        source_query_service=service,
    )
    direct = builder.build(
        ContextPackRequest(
            agent_id="chatgpt",
            query="MemoryGateway 输出",
            project="LingJi",
            mode="current",
        )
    )
    gateway = MemoryGateway(
        database,
        retriever,
        builder,
        object(),
        profiles=AIProfileRegistry(),
    )
    through_gateway = gateway.build_context_pack(
        "chatgpt",
        query="MemoryGateway 输出",
        project="LingJi",
        mode="current",
    )

    def identities(pack: dict[str, object]) -> list[tuple[str, str, str, str]]:
        return [
            (
                str(item.get("memory_id") or ""),
                str(item.get("source_id") or ""),
                str(item.get("conversation_id") or ""),
                str(item.get("message_id") or ""),
            )
            for item in pack["sections"]  # type: ignore[index]
        ]

    assert identities(direct) == identities(through_gateway)


def test_context_pack_rendering_never_slices_citation_and_is_bounded(tmp_path: Path) -> None:
    database = MemoryDatabase(tmp_path / "memory.db")
    vault = tmp_path / "vault"
    huge = "统一接口证据。" * 5000
    _note(vault, "03-Knowledge/huge.md", "memory-huge", "长证据", huge)
    from src.indexer.index import PEMISIndex

    index = PEMISIndex(vault, tmp_path / "storage")
    index.build_index()
    database.rebuild_from_index(index.get_all(), vault, MarkdownChunker())
    pack = ContextPackBuilder(database, HybridRetriever(database)).build(
        ContextPackRequest(agent_id="chatgpt", query="统一接口", max_chars=12000)
    )
    assert len(pack["markdown"]) <= 12000
    for section in pack["sections"]:
        citation = section["citation"]
        assert section["memory_id"] in pack["markdown"]
        assert str(citation.get("memory_id") or section["memory_id"]) in pack["markdown"]


def test_hybrid_diagnostics_are_per_call_and_semantic_failure_is_safe(tmp_path: Path) -> None:
    database = MemoryDatabase(tmp_path / "memory.db")

    class ThrowingProvider:
        def search(self, query: str, limit: int, filters: dict[str, object] | None = None):
            raise RuntimeError("token=/secret/path/qdrant")

    result = HybridRetriever(database, semantic_provider=ThrowingProvider()).search_with_diagnostics(
        "missing", filters=SearchFilters()
    )
    assert result["results"] == []
    assert result["diagnostics"]["lexical"] == "available"
    assert result["diagnostics"]["semantic"] == "degraded"
    assert result["diagnostics"]["reason_code"] == "semantic_query_failed"
    assert "/secret/path" not in str(result)

    absent = HybridRetriever(database).search_with_diagnostics("missing", filters=SearchFilters())
    assert absent["diagnostics"]["semantic"] == "unavailable"
    assert absent["diagnostics"]["reason_code"] == "semantic_provider_absent"
