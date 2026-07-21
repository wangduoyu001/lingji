from src.project_memory.context_service import ProjectContextService


class Profiles:
    class P:
        agent_id = "codex"
        allowed_privacy = ("public", "private")
        max_context_chars = 18000
        can_read_other_projects = False
    def get(self, _): return self.P()


class DB:
    revision = 1
    def list_core_memories(self, **_):
        return [self.item("core", "core", "LJ-PROJ-LINGJI"), self.item("other", "core", "OTHER")]
    def list_recent(self, **_):
        return [self.item("decision", "decision", "LJ-PROJ-LINGJI"), self.item("task", "task", "LJ-PROJ-LINGJI")]
    def fetch_memory(self, memory_id, include_chunks=True):
        return {**self.item(memory_id, "core", "LJ-PROJ-LINGJI"), "chunks": [{"text": memory_id + "。" * 200}]}
    @staticmethod
    def item(mid, kind, project):
        return {"memory_id": mid, "title": mid, "memory_type": kind, "memory_tier": "core", "status": "active", "review_status": "approved", "privacy": "private", "project": [project], "agent_scope": ["codex"], "relative_path": f"03-Knowledge/{mid}.md"}


class Retriever:
    def search(self, *_, **__):
        return [{"memory_id": "message", "title": "message", "text": "related", "status": "active", "review_status": "approved", "privacy": "private", "project": ["LJ-PROJ-LINGJI"], "agent_scope": ["codex"], "citation": {"memory_id": "message", "path": "02-Sources/message.md"}}]


def test_project_pack_is_ordered_scoped_bounded_and_cited():
    pack = ProjectContextService(DB(), Retriever(), profiles=Profiles()).build("codex", "LJ-PROJ-LINGJI", "task", max_chars=1500)
    assert [item["memory_id"] for item in pack["core_memories"]] == ["core"]
    assert pack["decisions"] and pack["active_tasks"] and pack["related_messages"]
    assert len(pack["markdown"]) <= 1500
    assert pack["markdown"].index("Core Memory") < pack["markdown"].index("Decisions") < pack["markdown"].index("Active Tasks")
    assert all(any(c.values()) for c in pack["citations"])


def test_codex_cannot_enable_cross_project():
    import pytest
    with pytest.raises(PermissionError):
        ProjectContextService(DB(), Retriever(), profiles=Profiles()).build("codex", "LJ-PROJ-LINGJI", "", allow_cross_project=True)
