"""Owner-facing memory cards built from the existing read models.

This module is deliberately a projection.  It does not create a table, write
state, or make an AI inference.  In particular, a card for an imported
conversation that has not been promoted is still useful evidence, but is
clearly marked as not being permanent memory.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from src.retrieval.temporal import parse_instant
from src.sources import SourceQueryService, ViewerContext

MAX_PREVIEW = 240
MAX_EVIDENCE = 3
MAX_SOURCE_PAGE = 200


@dataclass(frozen=True)
class OwnerMemoryCard:
    """Serializable, read-only owner memory card DTO."""

    memory_id: str
    kind: str
    state: str
    topic: str
    developments: tuple[str, ...]
    conclusion: str | None
    freshness: dict[str, Any]
    source: dict[str, Any]
    layers: dict[str, Any]
    trust: dict[str, Any]
    action: dict[str, Any]
    projection: dict[str, Any]
    evidence_count: int
    permanent_memory: str
    current_hash: str | None = None
    evidence: tuple[dict[str, Any], ...] = ()

    def to_dict(self, *, include_evidence: bool = False) -> dict[str, Any]:
        item = {
            "memory_id": self.memory_id,
            "kind": self.kind,
            "state": self.state,
            "topic": self.topic,
            "developments": list(self.developments[:MAX_EVIDENCE]),
            # ``evidence_lines`` is an owner-friendly alias retained for the
            # API contract while ``developments`` keeps the DTO compact.
            "evidence_lines": list(self.developments[:MAX_EVIDENCE]),
            "conclusion": self.conclusion,
            "freshness": dict(self.freshness),
            "source": dict(self.source),
            "layers": {key: dict(value) for key, value in self.layers.items()},
            "trust": dict(self.trust),
            "action": dict(self.action),
            "projection": dict(self.projection),
            "evidence_count": self.evidence_count,
            "permanent_memory": self.permanent_memory,
        }
        if include_evidence:
            item["evidence"] = [dict(value) for value in self.evidence[:MAX_EVIDENCE]]
            if self.current_hash:
                item["current_hash"] = self.current_hash
        return item


class OwnerMemoryCardProjector:
    """Project canonical memories and raw conversations into owner cards."""

    def __init__(
        self,
        database: Any,
        source_service: SourceQueryService,
        statistics: Any | None = None,
        *,
        gateway: Any | None = None,
        state_db: Any | None = None,
        workspace: str = "production",
    ):
        self.database = database
        self.source_service = source_service
        self.statistics = statistics
        self.gateway = gateway
        self.state_db = state_db
        self.workspace = str(workspace or "production")

    def list_cards(
        self,
        *,
        viewer: ViewerContext | None = None,
        state: str | None = None,
        action: str | None = None,
        source: str | None = None,
        source_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
        include_evidence: bool = False,
    ) -> dict[str, Any]:
        selected_limit, selected_offset = self._page_values(limit, offset)
        selected_viewer = viewer or self.source_service.owner_viewer()
        cards = self._all_cards(selected_viewer)
        cards = [card for card in cards if self._matches(card, state, action, source or source_id)]
        cards.sort(key=self._sort_key, reverse=True)
        total = len(cards)
        page = cards[selected_offset : selected_offset + selected_limit]
        return {
            "workspace": self.workspace,
            "viewer_scope": getattr(selected_viewer, "viewer_scope", "owner"),
            "viewer_agent_id": getattr(selected_viewer, "agent_id", None),
            "items": [card.to_dict(include_evidence=include_evidence) for card in page],
            "pagination": {
                "limit": selected_limit,
                "offset": selected_offset,
                "total": total,
                "has_more": selected_offset + len(page) < total,
            },
        }

    def get_card(
        self,
        memory_id: str,
        *,
        viewer: ViewerContext | None = None,
        include_evidence: bool = True,
    ) -> dict[str, Any]:
        selected_viewer = viewer or self.source_service.owner_viewer()
        wanted = str(memory_id or "").strip()
        # First locate the selected projection without reading any message
        # bodies.  Re-project only that one memory with detail enabled; doing
        # ``allow_message_detail`` across the full list would defeat the
        # selected-message boundary for cards appearing earlier in the page.
        for card in self._all_cards(selected_viewer):
            if card.memory_id == wanted:
                if card.kind == "memory":
                    for document in self._list_documents():
                        document_id = str(document.get("memory_id") or document.get("id") or "").strip()
                        if document_id == wanted:
                            card = self._memory_card(document, selected_viewer, allow_message_detail=True)
                            break
                return {
                    "workspace": self.workspace,
                    "viewer_scope": getattr(selected_viewer, "viewer_scope", "owner"),
                    "viewer_agent_id": getattr(selected_viewer, "agent_id", None),
                    "item": card.to_dict(include_evidence=include_evidence),
                }
        raise LookupError("memory card not found")

    def summary(self, *, viewer: ViewerContext | None = None) -> dict[str, Any]:
        """Return full-card counts for Home without deriving from one page."""
        selected_viewer = viewer or self.source_service.owner_viewer()
        cards = self._all_cards(selected_viewer)
        conversations = self._paged_conversations(selected_viewer)
        measured_messages = [item.get("message_count") for item in conversations]
        message_count = (
            sum(measured_messages)
            if all(type(value) is int and value >= 0 for value in measured_messages)
            else None
        )
        return {
            "workspace": self.workspace,
            "cards": len(cards),
            "conversations": len(conversations),
            "messages": message_count if conversations else 0,
            "permanent": sum(1 for card in cards if str(card.layers.get("permanent", {}).get("state")) in {"available", "complete"}),
            "vectorized": sum(1 for card in cards if str(card.layers.get("vector", {}).get("state")) in {"available", "complete"}),
            "owner_review": sum(1 for card in cards if str(card.action.get("type")) in {"confirm", "review"}),
        }

    # Public alias used by callers that prefer the term ``project``.
    project = get_card

    def _all_cards(self, viewer: ViewerContext, *, allow_message_detail: bool = False) -> list[OwnerMemoryCard]:
        documents = self._list_documents()
        documents.extend(self._candidate_documents())
        promoted_conversations: set[str] = set()
        cards: list[OwnerMemoryCard] = []
        for document in documents:
            if not self._visible_memory(document, viewer):
                continue
            if str(document.get("memory_type") or "") == "structured_evidence":
                # Structured evidence is the index projection of a message,
                # not an additional owner memory card.
                continue
            card = self._memory_card(document, viewer, allow_message_detail=allow_message_detail)
            cards.append(card)
            conversation_id = self._relationship(document, "conversation_id")
            if conversation_id:
                promoted_conversations.add(conversation_id)
            promoted_conversations.update(
                str(item.get("conversation_id") or "")
                for item in card.evidence
                if str(item.get("conversation_id") or "")
            )
        cards.extend(self._conversation_cards(viewer, promoted_conversations))
        return cards

    def _candidate_documents(self) -> list[dict[str, Any]]:
        """Read promotion decisions as optional evidence, never as new state."""
        if self.state_db is None or not hasattr(self.state_db, "recent_events"):
            return []
        try:
            events = self.state_db.recent_events(limit=100000)
        except Exception:
            return []
        known = {str(item.get("memory_id") or item.get("id") or "") for item in self._list_documents()}
        output: list[dict[str, Any]] = []
        # ``recent_events`` is newest-first; retain the latest terminal state
        # for each candidate and never let an older pending event win.
        for event in events:
            if str(event.get("event_type") or "") not in {"memory_promotion_decision", "memory_promotion_owner_approved", "memory_promotion_owner_rejected"}:
                continue
            payload = event.get("payload")
            if not isinstance(payload, Mapping):
                try:
                    payload = json.loads(str(event.get("payload_json") or "{}"))
                except (TypeError, ValueError, json.JSONDecodeError):
                    payload = {}
            payload = dict(payload or {})
            memory_id = str(payload.get("memory_id") or payload.get("candidate_id") or event.get("entity_id") or "").strip()
            if not memory_id or memory_id in known:
                continue
            state = str(payload.get("status") or payload.get("state") or "pending_owner_review").strip().lower()
            if state in {"active", "visible_active"}:
                # Keep the latest terminal meaning when the canonical
                # projection is temporarily absent; never fall back to an
                # older pending event and ask the owner to confirm it.
                output.append({
                    "memory_id": memory_id,
                    "title": str(payload.get("title") or payload.get("topic") or memory_id),
                    "memory_type": str(payload.get("memory_type") or "knowledge"),
                    "memory_tier": "derived",
                    "status": "active",
                    "review_status": "projection_unavailable",
                    "privacy": str(payload.get("privacy") or "private"),
                    "confidence": payload.get("confidence"),
                    "valid_from": None,
                    "valid_to": None,
                    "relationships": {"canonical_projection": "unavailable", "terminal_state": state},
                })
                known.add(memory_id)
                continue
            pending = state in {"pending_owner_review", "requires_owner_review", "needs_review", "candidate", "received", "preparing"}
            lifecycle = "needs_review" if pending else state
            review_status = "pending_owner_review" if pending else lifecycle
            relationships = {
                "evidence_refs": payload.get("evidence_refs") or payload.get("source_refs") or [],
                "authority": payload.get("authority") or payload.get("source_authority") or "",
                "development_lines": payload.get("development_lines") or payload.get("evidence_lines") or [],
                "invalidating_reason": payload.get("reason") or payload.get("rejection_reason") or payload.get("error") or "",
            }
            if not pending:
                relationships["canonical_projection"] = "unavailable"
            output.append({
                "memory_id": memory_id,
                "title": str(payload.get("title") or payload.get("topic") or memory_id),
                "memory_type": str(payload.get("memory_type") or "knowledge"),
                "memory_tier": "derived",
                "status": lifecycle,
                "review_status": review_status,
                "privacy": str(payload.get("privacy") or "private"),
                "confidence": payload.get("confidence"),
                "valid_from": None,
                "valid_to": None,
                "relationships": relationships,
            })
            known.add(memory_id)
        return output

    def _memory_card(self, document: Mapping[str, Any], viewer: ViewerContext, *, allow_message_detail: bool = False) -> OwnerMemoryCard:
        memory_id = str(document.get("memory_id") or document.get("id") or "").strip()
        relationships = self._relationships(document)
        refs = self._evidence_refs(relationships)
        refs = self._bounded_memory_refs(memory_id, refs, viewer)
        all_evidence = self._evidence_for_refs(refs, viewer, allow_message_detail=allow_message_detail)
        evidence = all_evidence[:MAX_EVIDENCE]
        evidence_by_id = {str(item.get("message_id") or ""): item for item in all_evidence}
        expected_refs = {self._ref_value(item): item for item in refs if self._ref_value(item)}
        provenance = "unknown"
        if expected_refs:
            provenance = "verified"
            for ref_id, ref in expected_refs.items():
                actual = evidence_by_id.get(ref_id)
                expected_hash = ref.get("content_hash") if isinstance(ref, Mapping) else None
                if actual is None or (expected_hash and str(actual.get("content_hash") or "") != str(expected_hash)):
                    provenance = "mismatch"
                    break
        source = self._source_for(document, evidence, viewer)
        status = str(document.get("status") or "unknown").strip().lower()
        freshness = self._freshness(document, status, source)
        conflict = self._conflict(relationships)
        confidence = self._confidence(document.get("confidence"))
        trust_state = "conflict" if conflict == "conflict" else "provenance_mismatch" if provenance == "mismatch" else "low_confidence" if confidence is not None and confidence < 0.8 else "trusted" if confidence is not None and provenance == "verified" else "unknown"
        trust = {
            "state": trust_state,
            "confidence": confidence,
            "conflict": conflict,
            "provenance": provenance,
        }
        permanent = self._permanent_layer(document, status)
        projection = {"state": "unavailable" if relationships.get("canonical_projection") in {"unavailable", "unknown"} else "available", "reason": "canonical memory projection is unavailable" if relationships.get("canonical_projection") in {"unavailable", "unknown"} else None}
        structured = self._layer("unavailable", projection["reason"]) if projection["state"] != "available" else self._layer("available", "已有结构化记录")
        layers = {
            "raw": self._layer("available" if evidence or source.get("message_count", 0) else "unknown", "原始证据可查看" if evidence else "原始证据尚未获得"),
            "structured": structured,
            "vector": self._vector_layer(memory_id),
            "permanent": permanent,
        }
        conclusion = self._conclusion(document, evidence) if evidence and provenance == "verified" and conflict != "conflict" else None
        action = self._recommend_action(
            status,
            freshness,
            trust,
            source,
            permanent,
            is_core=str(document.get("memory_tier") or "").lower() == "core",
        )
        topic = self._topic(document.get("title"), memory_id)
        developments = tuple(self._development_lines(document, evidence if provenance == "verified" else ()))[:MAX_EVIDENCE]
        return OwnerMemoryCard(
            memory_id=memory_id,
            kind="memory",
            state=status,
            topic=topic,
            developments=developments,
            conclusion=conclusion,
            freshness=freshness,
            source=source,
            layers=layers,
            trust=trust,
            action=action,
            projection=projection,
            evidence_count=len(refs),
            permanent_memory=permanent["label"],
            current_hash=str(document.get("content_hash") or relationships.get("content_hash") or "") or None,
            evidence=tuple(evidence),
        )

    def _bounded_memory_refs(
        self,
        memory_id: str,
        refs: list[Any],
        viewer: ViewerContext,
    ) -> list[Any]:
        """Enrich evidence identities with read-model previews only.

        ``memory_sources`` deliberately excludes message bodies.  Using it
        here keeps card-list projection useful while reserving ``get_message``
        for the selected-card detail action.
        """
        if not memory_id or not hasattr(self.source_service, "memory_sources"):
            return refs
        try:
            response = self.source_service.memory_sources(memory_id, viewer=viewer)
        except TypeError:
            try:
                response = self.source_service.memory_sources(memory_id)
            except Exception:
                return refs
        except Exception:
            return refs
        links = response.get("links") if isinstance(response, Mapping) else None
        if not isinstance(links, list):
            return refs
        by_id = {
            self._ref_value(link): link
            for link in links
            if isinstance(link, Mapping) and self._ref_value(link)
        }
        # An empty canonical reference set means provenance is genuinely
        # unknown; do not manufacture evidence from an unrelated link list.
        if not refs:
            return refs
        enriched: list[Any] = []
        for ref in refs:
            ref_id = self._ref_value(ref)
            link = by_id.get(ref_id)
            if isinstance(link, Mapping) and isinstance(ref, Mapping):
                enriched.append({**dict(link), **dict(ref)})
            else:
                enriched.append(ref)
        return enriched

    def _conversation_cards(self, viewer: ViewerContext, promoted: set[str]) -> list[OwnerMemoryCard]:
        conversations = self._paged_conversations(viewer)
        cards: list[OwnerMemoryCard] = []
        for conversation in conversations:
            conversation_id = str(conversation.get("conversation_id") or "").strip()
            if not conversation_id or conversation_id in promoted:
                continue
            messages = self._conversation_messages(conversation_id, viewer)
            source = self._source_for_conversation(conversation, messages, viewer)
            evidence = tuple(self._message_evidence(messages))[:MAX_EVIDENCE]
            developments = tuple(item["preview"] for item in evidence)
            freshness = self._conversation_freshness(conversation, source)
            trust = {"state": "unknown", "confidence": None, "conflict": "unknown", "provenance": "verified" if evidence else "unknown"}
            layers = {
                "raw": self._layer("available" if evidence else "unknown", "原始会话证据可查看" if evidence else "原始证据尚未获得"),
                "structured": self._layer("available", "已有结构化会话记录"),
                "vector": self._layer("not_applicable", "尚未形成永久记忆索引"),
                "permanent": self._layer("not_permanent", "尚未加入永久记忆"),
            }
            action = {"type": "review", "label": "查看并决定是否加入永久记忆", "reason": "本会话尚未晋级为永久记忆"}
            cards.append(
                OwnerMemoryCard(
                    memory_id=f"conversation:{conversation_id}",
                    kind="conversation_evidence",
                    state=str(freshness.get("state") or "unknown"),
                    topic=self._topic(conversation.get("title"), conversation_id),
                    developments=developments,
                    conclusion=None,
                    freshness=freshness,
                    source=source,
                    layers=layers,
                    trust=trust,
                    action=action,
                    projection={"state": "available", "reason": None},
                    evidence_count=len(evidence),
                    permanent_memory="尚未加入永久记忆",
                    evidence=evidence,
                )
            )
        return cards

    def _list_documents(self) -> list[dict[str, Any]]:
        try:
            return [dict(item) for item in self.database.list_documents(include_chunks=False)]
        except TypeError:
            return [dict(item) for item in self.database.list_documents()]

    def _paged_conversations(self, viewer: ViewerContext) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        offset = 0
        while True:
            response = self.source_service.list_conversations(viewer=viewer, limit=MAX_SOURCE_PAGE, offset=offset)
            page = self._items(response)
            output.extend(page)
            pagination = self._pagination(response)
            if not page or offset + len(page) >= int(pagination.get("total") or len(output)):
                break
            offset += len(page)
        return output

    def _conversation_messages(self, conversation_id: str, viewer: ViewerContext) -> list[dict[str, Any]]:
        response = self.source_service.list_messages(viewer=viewer, conversation_id=conversation_id, limit=MAX_SOURCE_PAGE, offset=0)
        messages = self._items(response)
        # Source list endpoints intentionally omit bodies.  Detail reads are
        # still bounded to the first page and are only used to produce the
        # short evidence preview on a card.
        enriched: list[dict[str, Any]] = []
        # List endpoints are deliberately metadata/preview-only.  Full message
        # bodies are fetched exclusively by the explicit message-detail route.
        enriched.extend(messages[:MAX_SOURCE_PAGE])
        return enriched

    def _evidence_for_refs(self, refs: list[Any], viewer: ViewerContext, *, allow_message_detail: bool = False) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for ref in refs:
            message_id = self._ref_value(ref)
            if not message_id:
                continue
            # References may carry a bounded preview.  Never turn card-list
            # projection into a full message read; detail projection may use
            # the existing service only after the owner selected a card.
            message = dict(ref) if isinstance(ref, Mapping) else {"message_id": message_id}
            if allow_message_detail:
                try:
                    response = self.source_service.get_message(message_id, viewer=viewer)
                except TypeError:
                    response = self.source_service.get_message(message_id)
                except Exception:
                    response = {}
                detail = dict(response.get("item") or response) if isinstance(response, Mapping) else {}
                if detail:
                    message = detail
            message.setdefault("message_id", message_id)
            if not message:
                continue
            output.append(self._message_evidence_item(message))
        return output

    def _message_evidence(self, messages: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
        return [self._message_evidence_item(item) for item in list(messages)[:MAX_EVIDENCE]]

    @staticmethod
    def _message_evidence_item(message: Mapping[str, Any]) -> dict[str, Any]:
        content = " ".join(str(message.get("preview") or message.get("content_preview") or message.get("excerpt") or "").split())
        return {
            "message_id": str(message.get("message_id") or ""),
            "conversation_id": str(message.get("conversation_id") or "") or None,
            "source_id": str(message.get("source_id") or "") or None,
            "role": str(message.get("role") or "unknown"),
            "occurred_at": message.get("occurred_at"),
            "preview": content[:MAX_PREVIEW],
            "content_hash": str(message.get("content_hash") or "") or None,
        }

    def _source_for(self, document: Mapping[str, Any], evidence: list[dict[str, Any]], viewer: ViewerContext) -> dict[str, Any]:
        relationships = self._relationships(document)
        source_id = self._relationship(document, "source_id") or str(next((item.get("source_id") for item in evidence if item.get("source_id")), ""))
        source_item: dict[str, Any] = {}
        if source_id:
            try:
                try:
                    response = self.source_service.get_source(source_id, viewer=viewer)
                except TypeError:
                    response = self.source_service.get_source(source_id)
                source_item = self._item(response)
            except Exception:
                source_item = {}
        latest = self._latest_time(evidence)
        conversation_id = self._relationship(document, "conversation_id") or str(next((item.get("conversation_id") for item in evidence if item.get("conversation_id")), ""))
        count = len(evidence)
        if conversation_id:
            messages = self._conversation_messages(conversation_id, viewer)
            count = int(self._pagination(self.source_service.list_messages(viewer=viewer, conversation_id=conversation_id, limit=1, offset=0)).get("total") or len(messages))
            latest = self._latest_time(self._message_evidence(messages)) or latest
        return {
            "source_id": source_id or None,
            "label": str(source_item.get("display_name") or source_item.get("source_type") or "来源未知"),
            "type": source_item.get("source_type") or relationships.get("structured_source_type") or None,
            "status": source_item.get("status") or relationships.get("source_status") or "unknown",
            "conversation_id": conversation_id or None,
            "message_count": count,
            "latest_evidence_at": latest,
        }

    def _source_for_conversation(self, conversation: Mapping[str, Any], messages: list[dict[str, Any]], viewer: ViewerContext) -> dict[str, Any]:
        source_id = str(conversation.get("source_id") or "").strip()
        source_item: dict[str, Any] = {}
        if source_id:
            try:
                try:
                    response = self.source_service.get_source(source_id, viewer=viewer)
                except TypeError:
                    response = self.source_service.get_source(source_id)
                source_item = self._item(response)
            except Exception:
                source_item = {}
        latest = self._latest_time(self._message_evidence(messages)) or self._latest_time([
            {"occurred_at": conversation.get("ended_at")},
            {"occurred_at": conversation.get("started_at")},
        ])
        return {
            "source_id": source_id or None,
            "label": str(source_item.get("display_name") or source_item.get("source_type") or "来源未知"),
            "type": source_item.get("source_type"),
            "status": source_item.get("status") or "unknown",
            "conversation_id": str(conversation.get("conversation_id") or "") or None,
            "message_count": int(conversation.get("message_count") or len(messages)),
            "latest_evidence_at": latest,
        }

    def _vector_layer(self, memory_id: str) -> dict[str, Any]:
        if self.statistics is None:
            return self._layer("unknown", "向量状态尚未获得")
        try:
            snapshot = dict(self.statistics.vector_status() or {})
        except Exception:
            snapshot = {}
        semantic = getattr(getattr(self.gateway, "retriever", None), "semantic_provider", None)
        if semantic is None:
            return self._layer("unavailable", "没有可用的逐条向量检查服务")
        try:
            coverage = dict(self.statistics.vector_coverage() or {})
        except Exception:
            coverage = {}
        coverage_state = str(coverage.get("state") or "").lower()
        try:
            memory = self.database.fetch_memory(memory_id, include_chunks=True)
            chunks = list((memory or {}).get("chunks") or [])
        except Exception:
            return self._layer("unavailable", "向量片段无法核对")
        if not chunks:
            return self._layer("unknown", "没有可核对的向量片段")
        results: list[bool | None] = []
        for chunk in chunks:
            try:
                value = semantic.exists(str(chunk.get("chunk_id") or ""))
                results.append(value if type(value) is bool else None)
            except Exception:
                results.append(None)
        if all(value is True for value in results):
            return self._layer("complete", "该记忆的向量索引完整")
        if any(value is True for value in results):
            return self._layer("partial", "该记忆只有部分向量索引")
        if any(value is None for value in results):
            return self._layer("unavailable", "向量覆盖状态尚未获得" if coverage_state in {"", "unknown", "unavailable", "degraded"} else "该记忆的向量状态无法核对")
        return self._layer("unavailable", "该记忆尚未建立向量索引")

    @staticmethod
    def _layer(state: str, reason: str | None = None) -> dict[str, Any]:
        return {"state": state or "unknown", "label": reason or "状态尚未获得", "reason": reason}

    @staticmethod
    def _permanent_layer(document: Mapping[str, Any], status: str) -> dict[str, Any]:
        if OwnerMemoryCardProjector._relationships(document).get("canonical_projection") in {"unavailable", "unknown"}:
            return {"state": "unknown", "label": "永久状态尚未获得", "reason": "canonical memory projection is unavailable"}
        tier = str(document.get("memory_tier") or "").lower()
        if tier == "core" and status == "active":
            return {"state": "available", "label": "永久记忆", "reason": None}
        if status in {"needs_review", "received", "preparing"} or str(document.get("review_status") or "").lower() in {"pending_owner_review", "needs_review"}:
            return {"state": "pending_owner_review", "label": "等待主人确认", "reason": None}
        return {"state": "not_permanent", "label": "不是永久记忆", "reason": None}

    @staticmethod
    def _recommend_action(
        status: str,
        freshness: Mapping[str, Any],
        trust: Mapping[str, Any],
        source: Mapping[str, Any],
        permanent: Mapping[str, Any],
        *,
        is_core: bool = False,
    ) -> dict[str, Any]:
        source_status = str(source.get("status") or "").lower()
        if source_status in {"revoked", "expired", "disabled", "archived"}:
            return {"type": "reauthorize_source", "label": "重新授权来源", "reason": "来源当前不可用"}
        if status in {"needs_review", "received", "preparing"} or permanent.get("state") == "pending_owner_review":
            return {"type": "confirm", "label": "确认是否加入永久记忆", "reason": "这条内容仍在等待主人确认"}
        # Core memories use lifecycle-safe owner actions. They must never be
        # routed through candidate approval endpoints. Lifecycle status is
        # checked independently of the permanent layer because invalidated and
        # archived core files are intentionally no longer ``available``.
        if is_core:
            if status == "archived" or freshness.get("state") == "archived":
                return {"type": "archive", "label": "移出当前记忆", "reason": str(freshness.get("reason") or "内容已移出当前记忆")}
            if status == "invalidated" or freshness.get("state") in {"overdue", "invalidated"}:
                return {"type": "invalidate", "label": "标记已经过时", "reason": str(freshness.get("reason") or "内容可能已过时")}
            if status in {"active", "superseded"} or permanent.get("state") == "available":
                return {"type": "correct", "label": "修正内容", "reason": "如有变化，可生成新的当前版本"}
        if freshness.get("state") in {"superseded", "invalidated", "archived", "rejected", "rolled_back", "repair_required", "overdue", "source_revoked"}:
            return {"type": "review", "label": "检查并决定是否移出当前记忆", "reason": str(freshness.get("reason") or "内容可能已过时")}
        if trust.get("conflict") == "conflict" or trust.get("provenance") in {"mismatch", "unknown"} or trust.get("state") in {"low_confidence", "unknown"}:
            return {"type": "review", "label": "检查来源并修正", "reason": "可信或来源证据需要主人复核"}
        return {"type": "none", "label": "目前无需处理", "reason": None}

    @staticmethod
    def _freshness(document: Mapping[str, Any], status: str, source: Mapping[str, Any]) -> dict[str, Any]:
        if str(source.get("status") or "").lower() in {"revoked", "expired", "disabled", "archived"}:
            return {"state": "source_revoked", "reason": "来源已撤销或过期", "replacement_id": None}
        replacement = document.get("superseded_by") or OwnerMemoryCardProjector._relationships(document).get("superseded_by")
        relationships = OwnerMemoryCardProjector._relationships(document)
        reason = relationships.get("supersession_reason") or relationships.get("supersede_reason") or relationships.get("invalidating_reason") or relationships.get("archive_reason") or document.get("archive_reason")
        if status in {"superseded", "invalidated", "archived", "rejected", "rolled_back", "repair_required"}:
            return {"state": status, "reason": reason or "生命周期状态已变化", "replacement_id": replacement or None}
        start = parse_instant(document.get("valid_from"))
        end = parse_instant(document.get("valid_to"))
        if document.get("valid_from") not in (None, "") and start is None or document.get("valid_to") not in (None, "") and end is None:
            return {"state": "unknown", "reason": "有效时间格式无法确认", "replacement_id": replacement or None}
        if start is None and end is None:
            return {"state": "unknown", "reason": "缺少证据时间", "replacement_id": replacement or None}
        now = datetime.now(timezone.utc)
        if end is not None and now >= end:
            return {"state": "overdue", "reason": "有效期已结束", "replacement_id": replacement or None}
        if start is not None and now < start:
            return {"state": "not_yet_current", "reason": "尚未到生效时间", "replacement_id": replacement or None}
        return {"state": "current", "reason": None, "replacement_id": replacement or None}

    @staticmethod
    def _conversation_freshness(conversation: Mapping[str, Any], source: Mapping[str, Any]) -> dict[str, Any]:
        if str(source.get("status") or "").lower() in {"revoked", "expired", "disabled", "archived"}:
            return {"state": "source_revoked", "reason": "来源已撤销或过期", "replacement_id": None}
        started = conversation.get("started_at")
        ended = conversation.get("ended_at")
        if not started and not ended:
            return {"state": "unknown", "reason": "缺少证据时间", "replacement_id": None}
        parsed = [parse_instant(value) for value in (started, ended) if value not in (None, "")]
        if not parsed or any(value is None for value in parsed):
            return {"state": "unknown", "reason": "证据时间格式无法确认", "replacement_id": None}
        return {"state": "current", "reason": None, "replacement_id": None}

    @staticmethod
    def _development_lines(document: Mapping[str, Any], evidence: list[dict[str, Any]]) -> list[str]:
        lines = [str(item.get("preview") or "").strip() for item in evidence if str(item.get("preview") or "").strip()]
        return lines[:MAX_EVIDENCE]

    @staticmethod
    def _conclusion(document: Mapping[str, Any], evidence: list[dict[str, Any]]) -> str | None:
        relationships = OwnerMemoryCardProjector._relationships(document)
        for key in ("conclusion", "current_conclusion", "summary"):
            value = relationships.get(key)
            if value and evidence:
                return " ".join(str(value).split())[:MAX_PREVIEW]
        return None

    @staticmethod
    def _topic(value: Any, fallback: str) -> str:
        topic = " ".join(str(value or "").split()).strip()
        # IDs are for technical details only; ordinary cards always have a
        # deterministic human-readable fallback.
        return topic[:160] if topic else "一条待核对的记忆"

    @staticmethod
    def _confidence(value: Any) -> float | None:
        try:
            result = float(value)
            return result if math.isfinite(result) and 0 <= result <= 1 else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _conflict(relationships: Mapping[str, Any]) -> str:
        for key in ("authority_conflict", "has_conflict", "conflict", "conflict_state"):
            value = relationships.get(key)
            if value is True or str(value).lower() in {"true", "1", "conflict", "unresolved"}:
                return "conflict"
        return "none"

    @staticmethod
    def _relationships(document: Mapping[str, Any]) -> dict[str, Any]:
        value = document.get("relationships") or document.get("relationships_json") or {}
        if isinstance(value, Mapping):
            return dict(value)
        return {}

    @classmethod
    def _relationship(cls, document: Mapping[str, Any], key: str) -> str:
        value = document.get(key) or cls._relationships(document).get(key)
        return str(value or "").strip()

    @staticmethod
    def _evidence_refs(relationships: Mapping[str, Any]) -> list[Any]:
        refs = relationships.get("evidence_refs") or relationships.get("source_refs") or []
        if isinstance(refs, (str, Mapping)):
            return [refs]
        return list(refs)

    @staticmethod
    def _ref_value(ref: Any) -> str:
        if isinstance(ref, Mapping):
            return str(ref.get("value") or ref.get("message_id") or "").strip()
        return str(ref or "").strip()

    @staticmethod
    def _latest_time(items: Iterable[Mapping[str, Any]]) -> str | None:
        values = [str(item.get("occurred_at") or "").strip() for item in items if str(item.get("occurred_at") or "").strip()]
        if not values:
            return None
        parsed = [(parse_instant(value), value) for value in values]
        if any(instant is None for instant, _value in parsed):
            return None
        return max(parsed, key=lambda pair: pair[0])[1]

    @staticmethod
    def _items(response: Any) -> list[dict[str, Any]]:
        if isinstance(response, Mapping):
            items = response.get("items")
            if isinstance(items, list):
                return [dict(item) for item in items]
            item = response.get("item")
            return [dict(item)] if isinstance(item, Mapping) else []
        return []

    @staticmethod
    def _pagination(response: Any) -> dict[str, Any]:
        if isinstance(response, Mapping) and isinstance(response.get("pagination"), Mapping):
            return dict(response["pagination"])
        return {}

    @staticmethod
    def _item(response: Any) -> dict[str, Any]:
        if not isinstance(response, Mapping):
            return {}
        value = response.get("item")
        return dict(value) if isinstance(value, Mapping) else dict(response)

    @staticmethod
    def _visible_memory(document: Mapping[str, Any], viewer: ViewerContext) -> bool:
        privacy = str(document.get("privacy") or "private")
        if privacy not in getattr(viewer, "allowed_privacy", ("public", "private", "restricted")):
            return False
        if viewer.owner:
            return True
        scopes = document.get("agent_scope") or OwnerMemoryCardProjector._relationships(document).get("agent_scope") or []
        if isinstance(scopes, str):
            scopes = [scopes]
        return not scopes or "all" in scopes or getattr(viewer, "agent_id", None) in scopes

    @staticmethod
    def _sort_key(card: OwnerMemoryCard) -> tuple[str, str]:
        return (str(card.source.get("latest_evidence_at") or ""), card.memory_id)

    @staticmethod
    def _matches(card: OwnerMemoryCard, state: str | None, action: str | None, source: str | None) -> bool:
        if state:
            wanted = str(state).strip().lower()
            values = {card.state.lower(), str(card.freshness.get("state") or "").lower(), str(card.layers.get("permanent", {}).get("state") or "").lower(), card.kind.lower()}
            if wanted not in values:
                return False
        if action and str(action).strip().lower() != str(card.action.get("type") or "").lower():
            return False
        if source:
            wanted = str(source).strip().casefold()
            values = {str(card.source.get(key) or "").casefold() for key in ("source_id", "type", "label")}
            if wanted not in values:
                return False
        return True

    @staticmethod
    def _page_values(limit: int, offset: int) -> tuple[int, int]:
        selected_limit, selected_offset = int(limit), int(offset)
        if not 1 <= selected_limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        if selected_offset < 0:
            raise ValueError("offset must be greater than or equal to zero")
        return selected_limit, selected_offset


# Compatibility names make the projection easy to discover for callers and
# keep the public contract explicit.
OwnerMemoryCardProjection = OwnerMemoryCardProjector
project_owner_memory_cards = OwnerMemoryCardProjector
