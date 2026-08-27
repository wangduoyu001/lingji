from __future__ import annotations

import json
import math
import re
import threading
import time
from collections import OrderedDict
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Any, Protocol

from src.retrieval.memory_db import MemoryDatabase
from src.retrieval.source_authority import SourceAuthorityResolver
from src.retrieval.temporal import ALL_LIFECYCLE_STATUSES, TemporalQuery, temporal_fields


class SemanticProvider(Protocol):
    def search(
        self,
        query: str,
        limit: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]: ...


@dataclass(frozen=True)
class SearchFilters:
    project: str | None = None
    memory_types: tuple[str, ...] = ()
    statuses: tuple[str, ...] = ("active", "needs_review", "received")
    privacy: tuple[str, ...] = ("public", "private")
    agent_id: str | None = None
    tags: tuple[str, ...] = ()
    as_of: str | None = None
    include_archived: bool = False
    mode: str = "current"
    valid: bool = True

    def normalized(self) -> "SearchFilters":
        statuses = self.statuses
        if self.include_archived and "archived" not in statuses:
            statuses = (*statuses, "archived")
        temporal = TemporalQuery.from_values(self.mode, self.as_of)
        selected_mode = str(self.mode or "current").strip().lower()
        contract_valid = temporal.valid and selected_mode in {"current", "as_of", "history", "why"}
        # Keep implicit current time out of cache identity.  The caller adds a
        # per-search evaluation instant after cache lookup.
        as_of = temporal.as_of if self.as_of is not None else None
        if temporal.mode in {"as_of", "history"}:
            statuses = ALL_LIFECYCLE_STATUSES
        return SearchFilters(
            project=self.project,
            memory_types=tuple(sorted(set(self.memory_types))),
            statuses=tuple(sorted(set(statuses))),
            privacy=tuple(sorted(set(self.privacy))),
            agent_id=self.agent_id,
            tags=tuple(sorted(set(self.tags))),
            as_of=as_of,
            include_archived=self.include_archived,
            mode=selected_mode,
            valid=contract_valid,
        )


class HybridRetriever:
    """Fuse lexical, optional semantic and metadata signals using RRF."""

    def __init__(
        self,
        database: MemoryDatabase,
        semantic_provider: SemanticProvider | None = None,
        cache_size: int = 256,
        cache_ttl_seconds: float = 120.0,
        rrf_k: int = 60,
        source_authority: SourceAuthorityResolver | None = None,
    ):
        self.database = database
        self.semantic_provider = semantic_provider
        self.cache_size = max(int(cache_size), 0)
        self.cache_ttl_seconds = max(float(cache_ttl_seconds), 0.0)
        self.rrf_k = max(int(rrf_k), 1)
        # Direct retrievers have no authority context and therefore fail closed
        # for automatic structured evidence. Formal composition injects the
        # StateDB-backed resolver.
        self.source_authority = source_authority or SourceAuthorityResolver(None)
        self._cache: OrderedDict[str, tuple[float, list[dict[str, Any]]]] = OrderedDict()
        self._lock = threading.RLock()

    def search(
        self,
        query: str,
        limit: int = 10,
        filters: SearchFilters | None = None,
    ) -> list[dict[str, Any]]:
        return self._search_internal(query, limit, filters, diagnostics=False, attach_why=True)[0]

    def search_with_diagnostics(
        self,
        query: str,
        limit: int = 10,
        filters: SearchFilters | None = None,
    ) -> dict[str, Any]:
        """Run one retrieval and return results with call-local channel state.

        Diagnostics intentionally travel with this invocation instead of being
        stored on the retriever, so concurrent callers cannot observe another
        request's semantic failure.
        """
        results, diagnostics = self._search_internal(query, limit, filters, diagnostics=True, attach_why=True)
        return {"results": results, "diagnostics": diagnostics}

    def _search_internal(
        self,
        query: str,
        limit: int,
        filters: SearchFilters | None,
        *,
        diagnostics: bool,
        attach_why: bool = True,
        apply_source_authority: bool = True,
    ) -> tuple[list[dict[str, Any]], dict[str, str]]:
        clean_query = " ".join(str(query or "").split())
        channel_state = {
            "lexical": "available",
            "semantic": "available" if self.semantic_provider is not None else "unavailable",
            "reason_code": "none" if self.semantic_provider is not None else "semantic_provider_absent",
        }
        if not clean_query:
            return [], channel_state
        normalized = (filters or SearchFilters()).normalized()
        if not normalized.valid:
            return [], channel_state
        limit = max(int(limit), 1)
        revision = self.database.revision
        # An implicit current/why query is evaluated against the wall clock.
        # Caching it under a timeless key can replay a memory after its
        # valid_to boundary. Explicit as_of/history queries remain cacheable.
        cacheable = not (normalized.mode in {"current", "why"} and normalized.as_of is None)
        cache_key = self._cache_key(clean_query, limit, normalized, revision) if cacheable else ""
        if not diagnostics and cacheable:
            cached = self._cache_get(cache_key)
            if cached is not None:
                return cached, channel_state

        evaluation_filters = normalized
        if normalized.mode in {"current", "why"} and normalized.as_of is None:
            evaluation_filters = replace(
                normalized,
                as_of=datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"),
            )
        candidate_limit = max(limit * 6, 30)
        lexical = self.database.search_fts(
            clean_query,
            limit=candidate_limit,
            memory_types=normalized.memory_types,
            statuses=normalized.statuses,
            privacy=normalized.privacy,
            as_of=evaluation_filters.as_of,
            mode=evaluation_filters.mode,
        )
        semantic, semantic_state = self._semantic_search_with_status(
            clean_query, candidate_limit, evaluation_filters
        )
        channel_state.update(semantic_state)
        fused = self._fuse(clean_query, lexical, semantic, evaluation_filters)
        if apply_source_authority and normalized.mode in {"current", "why"}:
            fused, authority_state = self.source_authority.filter_current(fused)
            channel_state["source_authority"] = authority_state.get("source_authority", "available")
            if authority_state.get("reason_code") != "none" or channel_state.get("reason_code") == "none":
                channel_state["reason_code"] = authority_state.get("reason_code", "none")
        output = fused[:limit]
        if normalized.mode == "why" and attach_why:
            self._attach_why(clean_query, output, evaluation_filters)
        if not diagnostics and cacheable:
            self._cache_put(cache_key, output)
        return output, channel_state

    def _attach_why(self, query: str, output: list[dict[str, Any]], filters: SearchFilters) -> None:
        current_ids = {str(item.get("memory_id") or "") for item in output}
        historical: list[dict[str, Any]] = []
        seen_historical: set[str] = set()
        for historical_query in [query, *sorted(self._terms(query))]:
            for candidate in self.database.search_fts(
                historical_query,
                limit=max(len(output) * 12, 60),
                memory_types=filters.memory_types,
                statuses=ALL_LIFECYCLE_STATUSES,
                privacy=filters.privacy,
                mode="history",
            ):
                candidate_id = str(candidate.get("memory_id") or "")
                if candidate_id and candidate_id not in seen_historical:
                    seen_historical.add(candidate_id)
                    historical.append(candidate)
        if self.semantic_provider is not None:
            history_filters = replace(filters, mode="history", as_of=None, statuses=ALL_LIFECYCLE_STATUSES)
            for semantic in self._semantic_search(query, max(len(output) * 12, 60), history_filters):
                memory = self.database.fetch_memory(str(semantic.get("memory_id") or ""), include_chunks=True)
                resolved = self._resolve_semantic_result(semantic, memory)
                if resolved and self._passes_post_filters(resolved, history_filters) and not any(str(item.get("memory_id") or "") == str(resolved.get("memory_id") or "") for item in historical):
                    historical.append(resolved)
        excluded: list[dict[str, Any]] = []
        winners = {str(item.get("memory_id") or ""): item for item in output}
        conflict_ids = {
            str(value)
            for item in output
            for value in (item.get("authority_conflicts") or [])
        }
        temporal = TemporalQuery.from_values("current", filters.as_of)
        for candidate in historical:
            memory_id = str(candidate.get("memory_id") or "")
            if not memory_id or memory_id in current_ids:
                continue
            history_scope = replace(filters, mode="history", as_of=None)
            if not self._passes_post_filters(candidate, history_scope):
                continue
            allowed, reason = temporal.allows(candidate)
            if allowed and memory_id not in conflict_ids:
                continue
            if memory_id in conflict_ids:
                reason = "lower_authority_conflict"
            fields = temporal_fields(candidate)
            candidate_relationships = candidate.get("relationships") or {}
            if not isinstance(candidate_relationships, dict):
                candidate_relationships = {}
            candidate_conflict_key = str(
                candidate.get("conflict_key")
                or candidate.get("topic_key")
                or candidate.get("decision_key")
                or candidate_relationships.get("conflict_key")
                or candidate_relationships.get("topic_key")
                or candidate_relationships.get("decision_key")
                or ""
            )
            candidate_projects = candidate.get("project") or []
            if isinstance(candidate_projects, str):
                candidate_projects = [candidate_projects]
            candidate_project_scope = tuple(sorted(str(value) for value in candidate_projects))
            excluded.append({
                "memory_id": memory_id,
                "reason": reason,
                "conflict_key": candidate_conflict_key,
                "project_scope": candidate_project_scope,
                "memory_type": str(candidate.get("memory_type") or ""),
                "privacy": str(candidate.get("privacy") or ""),
                "authority": fields["authority"],
                "citation": {**self._citation(candidate), "source_refs": fields["source_refs"]},
                "valid_from": fields["valid_from"],
                "valid_to": fields["valid_to"],
                "superseded_by": fields["superseded_by"],
            })
            if len(excluded) >= 50:
                break
        for item in output:
            fields = temporal_fields(item)
            relationships = item.get("relationships") or {}
            if not isinstance(relationships, dict):
                relationships = {}
            item_conflict_key = str(
                item.get("conflict_key")
                or item.get("topic_key")
                or item.get("decision_key")
                or relationships.get("conflict_key")
                or relationships.get("topic_key")
                or relationships.get("decision_key")
                or ""
            )
            item_projects = item.get("project") or []
            if isinstance(item_projects, str):
                item_projects = [item_projects]
            item_project_scope = tuple(sorted(str(value) for value in item_projects))
            relevant_excluded = [
                candidate for candidate in excluded
                if (
                    candidate.get("conflict_key") == item_conflict_key
                    and candidate.get("project_scope") == item_project_scope
                    and candidate.get("memory_type") == str(item.get("memory_type") or "")
                    and candidate.get("privacy") == str(item.get("privacy") or "")
                )
            ] if item_conflict_key else [
                candidate for candidate in excluded
                if (
                    not candidate.get("conflict_key")
                    and candidate.get("project_scope") == item_project_scope
                    and candidate.get("memory_type") == str(item.get("memory_type") or "")
                    and candidate.get("privacy") == str(item.get("privacy") or "")
                )
            ]
            item["why"] = {
                **fields,
                "citation": {**self._citation(item), "source_refs": fields["source_refs"]},
                "selection_rule": "current_valid_and_authority_ordered",
                "exclusion_reason": item.get("temporal_reason") or "selected",
                "conflict": bool(item.get("authority_conflicts")),
                "excluded_candidates": relevant_excluded,
            }

    def _semantic_search(
        self,
        query: str,
        limit: int,
        filters: SearchFilters,
    ) -> list[dict[str, Any]]:
        return self._semantic_search_with_status(query, limit, filters)[0]

    def _semantic_search_with_status(
        self,
        query: str,
        limit: int,
        filters: SearchFilters,
    ) -> tuple[list[dict[str, Any]], dict[str, str]]:
        if not self.semantic_provider:
            return [], {"semantic": "unavailable", "reason_code": "semantic_provider_absent"}
        try:
            results = self.semantic_provider.search(query, limit, asdict(filters))
        except Exception:
            return [], {"semantic": "degraded", "reason_code": "semantic_query_failed"}
        normalized = []
        for item in results or []:
            if not isinstance(item, dict):
                continue
            chunk_id = str(item.get("chunk_id") or "")
            memory_id = str(item.get("memory_id") or "")
            if not chunk_id and not memory_id:
                continue
            normalized.append(
                {
                    **item,
                    "chunk_id": chunk_id,
                    "memory_id": memory_id,
                    "semantic_score": self._clamp_score(item.get("score", item.get("semantic_score", 0.0))),
                }
            )
        if not normalized and results:
            return [], {"semantic": "degraded", "reason_code": "semantic_results_invalid"}
        return normalized, {"semantic": "available", "reason_code": "none"}

    def _fuse(
        self,
        query: str,
        lexical: list[dict[str, Any]],
        semantic: list[dict[str, Any]],
        filters: SearchFilters,
    ) -> list[dict[str, Any]]:
        candidates: dict[str, dict[str, Any]] = {}
        scores: dict[str, float] = {}
        channels: dict[str, set[str]] = {}

        for rank, item in enumerate(lexical, 1):
            key = self._candidate_key(item)
            if not key or not self._passes_post_filters(item, filters):
                continue
            candidates[key] = dict(item)
            scores[key] = scores.get(key, 0.0) + 1.0 / (self.rrf_k + rank)
            channels.setdefault(key, set()).add("lexical")

        for rank, item in enumerate(semantic, 1):
            key = self._candidate_key(item)
            if not key:
                continue
            existing = candidates.get(key)
            if existing is None:
                memory = self.database.fetch_memory(str(item.get("memory_id") or ""), include_chunks=True)
                existing = self._resolve_semantic_result(item, memory)
                if not existing or not self._passes_post_filters(existing, filters):
                    continue
                candidates[key] = existing
            scores[key] = scores.get(key, 0.0) + 1.0 / (self.rrf_k + rank)
            channels.setdefault(key, set()).add("semantic")

        query_terms = self._terms(query)
        for key, item in candidates.items():
            scores[key] += self._metadata_boost(item, query_terms, filters)
            item["retrieval_channels"] = sorted(channels.get(key, set()))
            item["retrieval_score"] = round(scores[key], 8)
            item["citation"] = self._citation(item)

        ordered = sorted(
            candidates.values(),
            key=lambda item: (
                item.get("retrieval_score", 0.0),
                self._importance_value(item.get("importance")),
                str(item.get("updated_at") or item.get("updated") or ""),
            ),
            reverse=True,
        )
        deduped = self._dedupe(ordered)
        if filters.mode in {"current", "why"}:
            # A lower-authority active statement must not silently compete with
            # a higher-authority statement for the same project/type.  Keep the
            # conflict attached to the winner so why/history can explain it.
            groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
            for item in deduped:
                projects = item.get("project") or []
                if isinstance(projects, str):
                    projects = [projects]
                relationships = item.get("relationships") or {}
                if not isinstance(relationships, dict):
                    relationships = {}
                conflict_key = (
                    item.get("conflict_key")
                    or item.get("topic_key")
                    or item.get("decision_key")
                    or relationships.get("conflict_key")
                    or relationships.get("topic_key")
                    or relationships.get("decision_key")
                    or ""
                )
                if not str(conflict_key).strip():
                    continue
                key = ("|".join(sorted(str(value) for value in projects)), str(item.get("memory_type") or ""), str(conflict_key))
                groups.setdefault(key, []).append(item)
            hidden: set[str] = set()
            for items in groups.values():
                ranks = [temporal_fields(item)["authority_rank"] for item in items]
                if len(items) < 2 or len(set(ranks)) < 2:
                    continue
                winner = max(items, key=lambda item: temporal_fields(item)["authority_rank"])
                conflicts = []
                winner_id = str(winner.get("memory_id") or "")
                for item in items:
                    item_id = str(item.get("memory_id") or "")
                    if item is winner or temporal_fields(item)["authority_rank"] >= temporal_fields(winner)["authority_rank"]:
                        continue
                    hidden.add(item_id)
                    conflicts.append(item_id)
                if conflicts:
                    winner["authority_conflicts"] = conflicts
            deduped = [item for item in deduped if str(item.get("memory_id") or "") not in hidden]
        return deduped

    @staticmethod
    def _candidate_key(item: dict[str, Any]) -> str:
        return str(item.get("chunk_id") or item.get("memory_id") or "")

    def _resolve_semantic_result(
        self,
        item: dict[str, Any],
        memory: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not memory:
            return None
        chunk_id = str(item.get("chunk_id") or "")
        chunk = None
        for value in memory.get("chunks", []):
            if chunk_id and value.get("chunk_id") == chunk_id:
                chunk = value
                break
        if chunk is None and memory.get("chunks"):
            chunk = memory["chunks"][0]
        if not chunk:
            return None
        return {
            "chunk_id": chunk.get("chunk_id"),
            "memory_id": memory.get("memory_id"),
            "relative_path": memory.get("relative_path"),
            "title": memory.get("title"),
            "memory_type": memory.get("memory_type"),
            "memory_tier": memory.get("memory_tier"),
            "status": memory.get("status"),
            "review_status": memory.get("review_status"),
            "privacy": memory.get("privacy"),
            "importance": memory.get("importance"),
            "confidence": memory.get("confidence"),
            "project": memory.get("project", []),
            "tags": memory.get("tags", []),
            "relationships": memory.get("relationships", {}),
            "superseded_by": memory.get("superseded_by", ""),
            "valid_from": memory.get("valid_from"),
            "valid_to": memory.get("valid_to"),
            "pin_to_context": memory.get("pin_to_context", False),
            "agent_scope": memory.get("agent_scope", []),
            "recall_weight": memory.get("recall_weight", 1.0),
            "updated_at": memory.get("updated_at"),
            "heading": chunk.get("heading", ""),
            "text": chunk.get("text", ""),
            "start_line": chunk.get("start_line"),
            "end_line": chunk.get("end_line"),
            "snippet": chunk.get("text", "")[:240],
            "semantic_score": item.get("semantic_score", 0.0),
        }

    def _passes_post_filters(self, item: dict[str, Any], filters: SearchFilters) -> bool:
        memory_type = str(item.get("memory_type") or "").strip()
        if filters.memory_types and (not memory_type or memory_type not in filters.memory_types):
            return False
        privacy = str(item.get("privacy") or "").strip()
        if filters.privacy and (not privacy or privacy not in filters.privacy):
            return False
        scopes = item.get("agent_scope") or []
        if isinstance(scopes, str):
            scopes = [scopes]
        if scopes:
            if not filters.agent_id:
                if "all" not in scopes:
                    return False
            elif filters.agent_id not in scopes and "all" not in scopes:
                return False
        if filters.project:
            projects = item.get("project") or []
            if isinstance(projects, str):
                projects = [projects]
            project_text = " ".join(str(value) for value in projects).lower()
            if filters.project.lower() not in project_text:
                return False
        if filters.tags:
            item_tags = {str(value).lower() for value in (item.get("tags") or [])}
            if not set(tag.lower() for tag in filters.tags).issubset(item_tags):
                return False
        temporal = TemporalQuery.from_values(filters.mode, filters.as_of)
        allowed, reason = temporal.allows(item)
        item["temporal_reason"] = reason
        if not allowed:
            return False
        return True

    def _metadata_boost(
        self,
        item: dict[str, Any],
        query_terms: set[str],
        filters: SearchFilters,
    ) -> float:
        boost = 0.0
        title = str(item.get("title") or "").lower()
        heading = str(item.get("heading") or "").lower()
        tags = " ".join(str(tag) for tag in (item.get("tags") or [])).lower()
        if query_terms:
            title_matches = sum(1 for term in query_terms if term in title)
            heading_matches = sum(1 for term in query_terms if term in heading)
            tag_matches = sum(1 for term in query_terms if term in tags)
            boost += min(title_matches * 0.025, 0.10)
            boost += min(heading_matches * 0.012, 0.05)
            boost += min(tag_matches * 0.008, 0.03)
        if item.get("memory_tier") == "core":
            boost += 0.035
        if item.get("pin_to_context"):
            boost += 0.025
        boost += self._importance_value(item.get("importance")) * 0.004
        boost += min(max(float(item.get("recall_weight") or 1.0) - 1.0, -0.5), 2.0) * 0.01
        if filters.project:
            boost += 0.025
        if item.get("status") == "active":
            boost += 0.008
        if item.get("review_status") == "approved":
            boost += 0.008
        boost += temporal_fields(item)["authority_rank"] * 0.02
        if "semantic" in item.get("retrieval_channels", []):
            boost += self._clamp_score(item.get("semantic_score")) * 0.01
        return boost

    @staticmethod
    def _terms(query: str) -> set[str]:
        return {
            term.lower()
            for term in re.findall(r"[\w\u4e00-\u9fff]{2,}", query, flags=re.UNICODE)
            if term
        }

    @staticmethod
    def _importance_value(value: Any) -> int:
        mapping = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        return mapping.get(str(value or "").lower(), 0)

    @staticmethod
    def _clamp_score(value: Any) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        if math.isnan(number) or math.isinf(number):
            return 0.0
        return min(max(number, 0.0), 1.0)

    @staticmethod
    def _citation(item: dict[str, Any]) -> dict[str, Any]:
        citation = {
            "memory_id": item.get("memory_id"),
            "path": item.get("relative_path"),
            "heading": item.get("heading"),
            "start_line": item.get("start_line"),
            "end_line": item.get("end_line"),
        }
        relationships = item.get("relationships") or {}
        if isinstance(relationships, dict):
            for key in (
                "source_id", "conversation_id", "message_id",
                "source_external_id", "conversation_external_id",
                "message_external_id", "content_hash", "raw_reference",
                "role", "sequence",
            ):
                if relationships.get(key) not in (None, ""):
                    citation[key] = relationships[key]
        return citation

    @staticmethod
    def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        output = []
        seen_chunks = set()
        per_memory: dict[str, int] = {}
        for item in items:
            chunk_id = str(item.get("chunk_id") or "")
            memory_id = str(item.get("memory_id") or "")
            if chunk_id and chunk_id in seen_chunks:
                continue
            if per_memory.get(memory_id, 0) >= 3:
                continue
            seen_chunks.add(chunk_id)
            per_memory[memory_id] = per_memory.get(memory_id, 0) + 1
            output.append(item)
        return output

    def _cache_key(
        self,
        query: str,
        limit: int,
        filters: SearchFilters,
        revision: int,
    ) -> str:
        payload = {
            "query": query,
            "limit": limit,
            "filters": asdict(filters),
            "revision": revision,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def _cache_get(self, key: str) -> list[dict[str, Any]] | None:
        if not self.cache_size or not self.cache_ttl_seconds:
            return None
        now = time.monotonic()
        with self._lock:
            value = self._cache.get(key)
            if not value:
                return None
            created_at, result = value
            if now - created_at > self.cache_ttl_seconds:
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            return [dict(item) for item in result]

    def _cache_put(self, key: str, result: list[dict[str, Any]]) -> None:
        if not self.cache_size or not self.cache_ttl_seconds:
            return
        with self._lock:
            self._cache[key] = (time.monotonic(), [dict(item) for item in result])
            self._cache.move_to_end(key)
            while len(self._cache) > self.cache_size:
                self._cache.popitem(last=False)

    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()
