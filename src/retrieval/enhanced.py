from __future__ import annotations

import json
import re
from typing import Any

from src.retrieval.hybrid import HybridRetriever as BaseHybridRetriever
from src.retrieval.hybrid import SearchFilters
from src.retrieval.temporal import temporal_fields


class HybridRetriever(BaseHybridRetriever):
    """Hybrid retrieval with a bounded substring fallback for short Chinese queries."""

    def search(
        self,
        query: str,
        limit: int = 10,
        filters: SearchFilters | None = None,
    ) -> list[dict[str, Any]]:
        limit = max(int(limit), 1)
        primary = super().search(query, limit=limit, filters=filters)
        if len(primary) >= limit:
            if (filters or SearchFilters()).mode == "why":
                for item in primary:
                    item["why"] = {**temporal_fields(item), "selection_rule": "current_valid_and_authority_ordered", "exclusion_reason": item.get("temporal_reason") or "selected"}
            return primary
        normalized = (filters or SearchFilters()).normalized()
        fallback = self._substring_search(query, max(limit * 3, 20), normalized)
        seen = {str(item.get("chunk_id") or item.get("memory_id") or "") for item in primary}
        combined = list(primary)
        for item in fallback:
            key = str(item.get("chunk_id") or item.get("memory_id") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            combined.append(item)
        combined.sort(
            key=lambda item: (
                float(item.get("retrieval_score") or 0.0),
                self._importance_value(item.get("importance")),
                str(item.get("updated_at") or ""),
            ),
            reverse=True,
        )
        output = self._dedupe(combined)[:limit]
        if normalized.mode == "why":
            conflict = len({temporal_fields(item)["authority_rank"] for item in output}) > 1
            for item in output:
                item["why"] = {**temporal_fields(item), "selection_rule": "current_valid_and_authority_ordered", "exclusion_reason": item.get("temporal_reason") or "selected", "conflict": conflict}
        return output

    def _substring_search(
        self,
        query: str,
        limit: int,
        filters: SearchFilters,
    ) -> list[dict[str, Any]]:
        terms = self._fallback_terms(query)
        if not terms:
            return []
        where = []
        params: list[Any] = []
        for term in terms:
            escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            where.append(
                "(d.title LIKE ? ESCAPE '\\' OR c.heading LIKE ? ESCAPE '\\' "
                "OR c.text LIKE ? ESCAPE '\\' OR d.tags_json LIKE ? ESCAPE '\\')"
            )
            params.extend([pattern, pattern, pattern, pattern])
        if filters.memory_types:
            where.append("d.memory_type IN (" + ",".join("?" for _ in filters.memory_types) + ")")
            params.extend(filters.memory_types)
        if filters.statuses and filters.mode in {"current", "why"}:
            where.append("d.status IN (" + ",".join("?" for _ in filters.statuses) + ")")
            params.extend(filters.statuses)
        if filters.privacy:
            where.append("d.privacy IN (" + ",".join("?" for _ in filters.privacy) + ")")
            params.extend(filters.privacy)
        # TemporalQuery post-filter performs timezone-normalized validation;
        # SQLite string comparisons would be wrong for offset timestamps.
        params.append(int(limit))
        sql = f"""
            SELECT
                c.chunk_id, c.memory_id, d.relative_path, d.title, d.memory_type,
                d.memory_tier, d.status, d.review_status, d.privacy, d.importance,
                d.confidence, d.project_json, d.tags_json, d.relationships_json,
                d.valid_from, d.valid_to, d.pin_to_context, d.agent_scope_json,
                d.recall_weight, d.updated_at, c.heading, c.text,
                c.start_line, c.end_line
            FROM memory_chunks c
            JOIN memory_documents d ON d.memory_id = c.memory_id
            WHERE {' AND '.join(where)}
            ORDER BY
                CASE WHEN d.title LIKE ? THEN 0 ELSE 1 END,
                d.recall_weight DESC,
                d.updated_at DESC
            LIMIT ?
        """
        title_pattern = f"%{terms[0]}%"
        params.insert(-1, title_pattern)
        with self.database._connection() as connection:
            rows = connection.execute(sql, params).fetchall()
        output = []
        query_terms = set(term.lower() for term in terms)
        for rank, row in enumerate(rows, 1):
            item = dict(row)
            item["project"] = self._loads(item.pop("project_json", "[]"), [])
            item["tags"] = self._loads(item.pop("tags_json", "[]"), [])
            item["relationships"] = self._loads(item.pop("relationships_json", "{}"), {})
            item["agent_scope"] = self._loads(item.pop("agent_scope_json", "[]"), [])
            item["pin_to_context"] = bool(item.get("pin_to_context"))
            if not self._passes_post_filters(item, filters):
                continue
            item["snippet"] = str(item.get("text") or "")[:240]
            item["retrieval_channels"] = ["substring"]
            score = 1.0 / (self.rrf_k + rank)
            score += self._metadata_boost(item, query_terms, filters)
            item["retrieval_score"] = round(score, 8)
            item["citation"] = self._citation(item)
            output.append(item)
        return output

    @staticmethod
    def _loads(value: Any, fallback: Any) -> Any:
        try:
            return json.loads(str(value))
        except (TypeError, ValueError, json.JSONDecodeError):
            return fallback

    @staticmethod
    def _fallback_terms(query: str) -> list[str]:
        clean = " ".join(str(query or "").strip().split())
        if not clean:
            return []
        terms: list[str] = []
        for token in re.findall(r"[A-Za-z0-9_.+-]+|[\u4e00-\u9fff]+", clean):
            if re.fullmatch(r"[\u4e00-\u9fff]+", token):
                if len(token) <= 2:
                    pieces = [token]
                elif len(token) <= 4:
                    pieces = [token[:2], token[-2:]]
                else:
                    pieces = [token[:2], token[-2:], token]
            else:
                pieces = [token]
            for piece in pieces:
                if piece and piece.lower() not in [value.lower() for value in terms]:
                    terms.append(piece)
        return terms[:4]
