from __future__ import annotations

from pathlib import Path

from src.gateway.profiles import AIProfileRegistry
from src.retrieval.context_pack import ContextPackRequest


class _FakeMCP:
    def __init__(self, *args, **kwargs) -> None:
        self.tools: dict[str, object] = {}

    def tool(self, *args, **kwargs):
        def register(function):
            self.tools[function.__name__] = function
            return function

        return register

    def resource(self, *args, **kwargs):
        return lambda function: function

    def prompt(self, *args, **kwargs):
        return lambda function: function


class _Gateway:
    def __init__(self):
        self.profiles = AIProfileRegistry()
        self.state_db = None

    def build_context_pack(self, agent_id, **kwargs):
        return {
            "agent_id": agent_id,
            "request": {"agent_id": agent_id, **kwargs},
            "sections": [{"kind": "raw_message_evidence", "memory_id": "m1", "source_id": "s1", "conversation_id": "c1", "message_id": "msg1"}],
            "markdown": "# Context Pack\n\n> 来源：s1/c1/msg1/m1\n",
        }


def test_mcp_registered_build_context_pack_preserves_scope_contract(monkeypatch):
    import sys
    import types

    config = types.ModuleType("src.config")
    config.settings = types.SimpleNamespace(
        storage_path=Path("/tmp"),
        vault_path=Path("/tmp/vault"),
        index_private=False,
        memory_chunk_max_chars=500,
        memory_chunk_overlap_chars=60,
        mcp_default_agent_id="chatgpt",
        mcp_server_name="test",
    )
    monkeypatch.setitem(sys.modules, "src.config", config)
    from src import mcp_server

    mcp_package = types.ModuleType("mcp")
    mcp_server_package = types.ModuleType("mcp.server")
    fastmcp_package = types.ModuleType("mcp.server.fastmcp")
    fastmcp_package.FastMCP = _FakeMCP
    monkeypatch.setitem(sys.modules, "mcp", mcp_package)
    monkeypatch.setitem(sys.modules, "mcp.server", mcp_server_package)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fastmcp_package)
    monkeypatch.setattr(mcp_server, "PEMISIndex", lambda *args, **kwargs: types.SimpleNamespace(build_index=lambda: None, get_all=lambda: [], layout=types.SimpleNamespace(should_index=lambda *args, **kwargs: False)))
    monkeypatch.setattr(mcp_server, "SkillRegistry", lambda *args, **kwargs: types.SimpleNamespace(status=lambda: {}))
    monkeypatch.setattr(mcp_server, "MarkdownChunker", lambda *args, **kwargs: object())
    monkeypatch.setattr(mcp_server, "build_extraction_pipeline", lambda *args, **kwargs: object())
    monkeypatch.setattr(mcp_server, "register_codex_mcp_tools", lambda *args, **kwargs: None)
    monkeypatch.setattr(mcp_server, "register_project_context_tools", lambda *args, **kwargs: None)
    gateway = _Gateway()

    server = mcp_server.create_mcp_server(
        gateway=gateway,
        codex_service=object(),
        project_context_service=object(),
        extraction_pipeline=object(),
        default_agent_id="chatgpt",
    )
    result = server.tools["build_context_pack"](
        query="统一上下文",
        agent_id="chatgpt",
        project="LingJi",
        max_chars=12000,
        mode="why",
        as_of="2026-03-01T00:00:00Z",
    )
    assert result["request"]["agent_id"] == "chatgpt"
    assert result["request"]["project"] == "LingJi"
    assert result["request"]["mode"] == "why"
    assert result["request"]["as_of"] == "2026-03-01T00:00:00Z"
    assert result["sections"][0]["message_id"] == "msg1"


def test_mcp_registered_real_gateway_excludes_current_stale_and_renders_why(monkeypatch, tmp_path):
    import sys
    import types

    from src.gateway.memory_gateway import MemoryGateway
    from src.retrieval import HybridRetriever
    from src.retrieval.context_pack import ContextPackBuilder
    from tests.test_automatic_memory_context_pack import _indexed

    database, source_model, source_query_service = _indexed(tmp_path)
    retriever = HybridRetriever(database)
    builder = ContextPackBuilder(
        database,
        retriever,
        source_read_model=source_model,
        source_query_service=source_query_service,
    )
    gateway = MemoryGateway(
        database,
        retriever,
        builder,
        object(),
        profiles=AIProfileRegistry(),
    )

    config = types.ModuleType("src.config")
    config.settings = types.SimpleNamespace(
        storage_path=Path("/tmp"),
        vault_path=Path("/tmp/vault"),
        index_private=False,
        memory_chunk_max_chars=500,
        memory_chunk_overlap_chars=60,
        mcp_default_agent_id="chatgpt",
        mcp_server_name="test",
    )
    monkeypatch.setitem(sys.modules, "src.config", config)
    mcp_package = types.ModuleType("mcp")
    mcp_server_package = types.ModuleType("mcp.server")
    fastmcp_package = types.ModuleType("mcp.server.fastmcp")
    fastmcp_package.FastMCP = _FakeMCP
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
    monkeypatch.setattr("src.mcp_server.build_extraction_pipeline", lambda *args, **kwargs: object())
    monkeypatch.setattr("src.mcp_server.register_codex_mcp_tools", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.mcp_server.register_project_context_tools", lambda *args, **kwargs: None)

    from src import mcp_server

    server = mcp_server.create_mcp_server(
        gateway=gateway,
        codex_service=object(),
        project_context_service=object(),
        extraction_pipeline=object(),
        default_agent_id="chatgpt",
    )
    current = server.tools["build_context_pack"](
        query="ContextPack",
        agent_id="chatgpt",
        project="LingJi",
        mode="current",
    )
    why = server.tools["build_context_pack"](
        query="ContextPack",
        agent_id="chatgpt",
        project="LingJi",
        mode="why",
    )
    assert "memory-old" not in current["markdown"]
    assert "memory-old" in why["markdown"]
    assert "status_superseded" in why["markdown"]


def test_mcp_registered_real_gateway_retrieves_short_chinese_with_diagnostics(monkeypatch, tmp_path):
    import sys
    import types

    from src.gateway.memory_gateway import MemoryGateway
    from src.retrieval import HybridRetriever
    from src.retrieval.context_pack import ContextPackBuilder
    from tests.test_automatic_memory_context_pack import _short_chinese_indexed

    database, source_model, source_query_service = _short_chinese_indexed(tmp_path)
    retriever = HybridRetriever(database)
    builder = ContextPackBuilder(
        database,
        retriever,
        source_read_model=source_model,
        source_query_service=source_query_service,
    )
    gateway = MemoryGateway(database, retriever, builder, object(), profiles=AIProfileRegistry())

    config = types.ModuleType("src.config")
    config.settings = types.SimpleNamespace(
        storage_path=Path("/tmp"),
        vault_path=Path("/tmp/vault"),
        index_private=False,
        memory_chunk_max_chars=500,
        memory_chunk_overlap_chars=60,
        mcp_default_agent_id="chatgpt",
        mcp_server_name="test",
    )
    monkeypatch.setitem(sys.modules, "src.config", config)
    mcp_package = types.ModuleType("mcp")
    mcp_server_package = types.ModuleType("mcp.server")
    fastmcp_package = types.ModuleType("mcp.server.fastmcp")
    fastmcp_package.FastMCP = _FakeMCP
    monkeypatch.setitem(sys.modules, "mcp", mcp_package)
    monkeypatch.setitem(sys.modules, "mcp.server", mcp_server_package)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fastmcp_package)
    monkeypatch.setattr("src.mcp_server.PEMISIndex", lambda *args, **kwargs: types.SimpleNamespace(build_index=lambda: None, get_all=lambda: [], layout=types.SimpleNamespace(should_index=lambda *args, **kwargs: False)))
    monkeypatch.setattr("src.mcp_server.SkillRegistry", lambda *args, **kwargs: types.SimpleNamespace(status=lambda: {}))
    monkeypatch.setattr("src.mcp_server.MarkdownChunker", lambda *args, **kwargs: object())
    monkeypatch.setattr("src.mcp_server.build_extraction_pipeline", lambda *args, **kwargs: object())
    monkeypatch.setattr("src.mcp_server.register_codex_mcp_tools", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.mcp_server.register_project_context_tools", lambda *args, **kwargs: None)

    from src import mcp_server

    server = mcp_server.create_mcp_server(
        gateway=gateway,
        codex_service=object(),
        project_context_service=object(),
        extraction_pipeline=object(),
        default_agent_id="chatgpt",
    )
    result = server.tools["build_context_pack"](
        query="灵机",
        agent_id="chatgpt",
        project="LingJi",
        mode="current",
    )
    assert "memory-lingji" in {item["memory_id"] for item in result["sections"]}
    assert "message-lingji" in result["markdown"]
    assert result["diagnostics"]["semantic"] == "unavailable"
