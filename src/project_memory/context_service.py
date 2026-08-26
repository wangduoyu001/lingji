from __future__ import annotations

from typing import Any, Callable, Iterable

from src.gateway.profiles import AIProfileRegistry
from src.retrieval.hybrid import SearchFilters
from src.retrieval.temporal import TemporalQuery

from .models import ProjectContextPack, stable_citation


class ProjectContextService:
    """Build a bounded, project-scoped and citation-only context pack."""

    ALLOCATIONS = {
        "core_memories": 0.35,
        "decisions_tasks": 0.25,
        "recent_sessions": 0.20,
        "related_messages": 0.20,
    }

    def __init__(self, database, retriever, *, profiles=None, session_provider: Callable[..., Iterable[dict[str, Any]]] | None = None):
        self.database = database
        self.retriever = retriever
        self.profiles = profiles or AIProfileRegistry()
        self.session_provider = session_provider

    def build(self, agent_id: str, project_id: str, query: str, session_id: str | None = None, max_chars: int | None = None, allow_cross_project: bool = False, mode: str = "current", as_of: str | None = None) -> dict[str, Any]:
        profile = self.profiles.get(agent_id)
        if not project_id:
            raise ValueError("project_id is required")
        if allow_cross_project and (agent_id != "lingji-local" or not profile.can_read_other_projects):
            raise PermissionError("PROJECT_ACCESS_DENIED")
        limit = min(max(int(max_chars or profile.max_context_chars), 1000), profile.max_context_chars)
        pack = ProjectContextPack(agent_id=profile.agent_id, project_id=project_id, session_id=session_id or "", max_chars=limit)

        core_budget = int(limit * self.ALLOCATIONS["core_memories"])
        dt_budget = int(limit * self.ALLOCATIONS["decisions_tasks"])
        sessions_budget = int(limit * self.ALLOCATIONS["recent_sessions"])
        related_budget = max(limit - core_budget - dt_budget - sessions_budget, 0)

        core = self.database.list_core_memories(agent_id=profile.agent_id, project=None if allow_cross_project else project_id, privacy=profile.allowed_privacy, limit=100, mode=mode, as_of=as_of)
        pack.core_memories = self._bounded(self._eligible_full(core, profile, project_id, allow_cross_project, mode, as_of), core_budget)

        recent = self.database.list_recent(limit=200, privacy=profile.allowed_privacy)
        decisions = [item for item in recent if str(item.get("memory_type")) == "decision"]
        tasks = [item for item in recent if str(item.get("memory_type")) in {"task", "blocker"}]
        half = dt_budget // 2
        pack.decisions = self._bounded(self._eligible_full(decisions, profile, project_id, allow_cross_project, mode, as_of), half)
        pack.active_tasks = self._bounded(self._eligible_full(tasks, profile, project_id, allow_cross_project, mode, as_of), dt_budget - half)

        sessions = list(self.session_provider(project_id=project_id, session_id=session_id or "", limit=30) if self.session_provider else [])
        pack.recent_sessions = self._bounded(
            self._eligible(
                sessions,
                profile,
                project_id,
                allow_cross_project,
                allowed_statuses={"active", "completed", "failed", "abandoned"},
                mode=mode,
                as_of=as_of,
            ),
            sessions_budget,
        )

        if query:
            results = self.retriever.search(query, limit=40, filters=SearchFilters(project=None if allow_cross_project else project_id, privacy=profile.allowed_privacy, agent_id=profile.agent_id, include_archived=False, mode=mode, as_of=as_of))
            pack.related_messages = self._bounded(self._eligible(results, profile, project_id, allow_cross_project, mode=mode, as_of=as_of), related_budget)

        sections = [
            ("Core Memory", pack.core_memories),
            ("Decisions", pack.decisions),
            ("Active Tasks / Blockers", pack.active_tasks),
            ("Recent Codex Sessions", pack.recent_sessions),
            ("Related Messages / Memory", pack.related_messages),
        ]
        pack.citations = []
        for _, items in sections:
            for item in items:
                citation = stable_citation(item)
                if citation and citation not in pack.citations:
                    pack.citations.append(citation)
        pack.markdown = self._render(pack, sections)
        if len(pack.markdown) > limit:
            pack.markdown = self._natural_take(pack.markdown, limit)
        return pack.to_dict()

    def _eligible_full(self, items, profile, project_id, allow_cross_project, mode="current", as_of=None):
        for item in self._eligible(items, profile, project_id, allow_cross_project, mode=mode, as_of=as_of):
            memory_id = str(item.get("memory_id") or "")
            full = self.database.fetch_memory(memory_id, include_chunks=True) if memory_id else item
            if full:
                merged = dict(item)
                merged.update(full)
                yield merged

    def _eligible(self, items, profile, project_id, allow_cross_project, allowed_statuses=None, mode="current", as_of=None):
        statuses = set(allowed_statuses or {"active"})
        temporal = TemporalQuery.from_values(mode, as_of)
        for raw in items:
            item = dict(raw)
            allowed, _ = temporal.allows(item)
            if not allowed:
                continue
            path = str(item.get("relative_path") or (item.get("citation") or {}).get("path") or "")
            if path.startswith("08-Private/"):
                continue
            if str(item.get("privacy") or "private") not in profile.allowed_privacy:
                continue
            if mode in {"current", "why"} and str(item.get("status") or "active") not in statuses:
                continue
            review = str(item.get("review_status") or "approved")
            if review not in {"", "approved"}:
                continue
            scopes = item.get("agent_scope") or []
            if scopes and profile.agent_id not in scopes and "all" not in scopes:
                continue
            projects = item.get("project") or item.get("project_ids") or []
            if isinstance(projects, str):
                projects = [projects]
            if not allow_cross_project and project_id not in projects:
                continue
            if not stable_citation(item) and not (item.get("citation") and any((item.get("citation") or {}).values())):
                continue
            citation = item.get("citation") or {}
            item.setdefault("memory_id", citation.get("memory_id"))
            item.setdefault("relative_path", citation.get("path"))
            yield item

    def _bounded(self, items, budget):
        output, used = [], 0
        for item in items:
            text = self._text(item)
            remaining = budget - used
            if remaining < 80:
                break
            clipped = self._natural_take(text, remaining)
            if not clipped:
                continue
            result = dict(item)
            result["text"] = clipped
            result.pop("chunks", None)
            output.append(result)
            used += len(clipped)
        return output

    @staticmethod
    def _text(item):
        chunks = item.get("chunks") or []
        if chunks:
            return "\n\n".join(str(chunk.get("text") or "").strip() for chunk in chunks if chunk.get("text")).strip()
        return str(item.get("text") or item.get("snippet") or item.get("content") or item.get("summary") or "").strip()

    @staticmethod
    def _natural_take(text, budget):
        clean = str(text or "").strip()
        if not clean or budget < 20:
            return ""
        if len(clean) <= budget:
            return clean
        stop = max(budget - 1, 0)
        boundary = max(clean.rfind("。", 0, stop), clean.rfind("\n", 0, stop), clean.rfind(". ", 0, stop))
        if boundary < budget // 2:
            boundary = stop
        return clean[: boundary + 1].rstrip() + "…"

    @staticmethod
    def _render(pack, sections):
        lines = ["# LingJi Project Context Pack", "", f"- Agent: `{pack.agent_id}`", f"- Project: `{pack.project_id}`", f"- Session: `{pack.session_id}`", ""]
        for title, items in sections:
            lines.extend([f"## {title}", ""])
            for item in items:
                label = item.get("title") or item.get("memory_id") or item.get("message_id") or "Context"
                lines.extend([f"### {label}", "", str(item.get("text") or ""), ""])
                citation = stable_citation(item)
                if citation:
                    refs = [f"{k}={v}" for k, v in citation.items() if v]
                    lines.extend(["> Citation: " + " · ".join(refs), ""])
        return "\n".join(lines).rstrip() + "\n"
