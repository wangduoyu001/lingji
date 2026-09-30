"""Knowledge 层来源授权过滤扩展（2026-09-30 P1 修复）的单元契约。

`SourceAuthorityResolver` 此前只拦 `structured_evidence`；修复后凡携带
`automatic_memory_source_id` 的派生条目一律受来源授权管辖，唯一豁免是
主人门槛批准的 Core（memory_tier=core 且 review_status=approved）。
"""

from __future__ import annotations

from src.retrieval.source_authority import SourceAuthorityResolver


class _FakeState:
    def __init__(self, authorized: set[str] | None = None):
        self.authorized = authorized or set()

    def list_automatic_memory_sources(self, *, now: str) -> list[dict[str, str]]:
        return [
            {"source_id": source_id, "status": "authorized"}
            for source_id in sorted(self.authorized)
        ]


def _knowledge_item(source_id: str, *, tier: str = "candidate", review: str = "") -> dict:
    return {
        "memory_id": f"LJ-KNOW-{source_id}",
        "memory_type": "knowledge",
        "memory_tier": tier,
        "review_status": review,
        "relationships": {"automatic_memory_source_id": source_id},
    }


def test_non_core_knowledge_from_revoked_source_is_filtered() -> None:
    resolver = SourceAuthorityResolver(_FakeState(authorized={"src-alive"}))
    items = [
        _knowledge_item("src-alive"),
        _knowledge_item("src-revoked"),
    ]
    filtered, state = resolver.filter_current(items)
    assert [item["memory_id"] for item in filtered] == ["LJ-KNOW-src-alive"]
    assert state["source_authority"] == "denied"
    allowed, diagnostic = resolver.allows_current(_knowledge_item("src-revoked"))
    assert allowed is False
    assert diagnostic["reason_code"] == "source_authority_denied"


def test_owner_approved_core_is_exempt_from_revocation() -> None:
    resolver = SourceAuthorityResolver(_FakeState(authorized=set()))
    core_item = _knowledge_item("src-revoked", tier="core", review="approved")
    filtered, _ = resolver.filter_current([core_item])
    assert filtered == [core_item]
    allowed, diagnostic = resolver.allows_current(core_item)
    assert allowed is True
    assert diagnostic["reason_code"] == "none"


def test_core_without_owner_approval_stays_governed() -> None:
    resolver = SourceAuthorityResolver(_FakeState(authorized=set()))
    item = _knowledge_item("src-revoked", tier="core", review="needs_review")
    filtered, _ = resolver.filter_current([item])
    assert filtered == []


def test_item_without_source_link_is_untouched() -> None:
    resolver = SourceAuthorityResolver(_FakeState(authorized=set()))
    item = {"memory_id": "LJ-MEM-manual", "memory_type": "knowledge", "relationships": {}}
    filtered, state = resolver.filter_current([item])
    assert filtered == [item]
    assert state["reason_code"] == "none"
    allowed, _ = resolver.allows_current(item)
    assert allowed is True


def test_structured_evidence_semantics_unchanged() -> None:
    resolver = SourceAuthorityResolver(_FakeState(authorized=set()))
    item = {
        "memory_id": "LJ-EVIDENCE-x",
        "memory_type": "structured_evidence",
        "memory_tier": "evidence",
        "relationships": {"automatic_memory_source_id": "src-revoked"},
    }
    filtered, _ = resolver.filter_current([item])
    assert filtered == []


def test_state_db_unavailable_fails_closed_but_core_exempt() -> None:
    resolver = SourceAuthorityResolver(None)
    linked = _knowledge_item("src-any")
    filtered, state = resolver.filter_current([linked])
    assert filtered == []
    assert state["source_authority"] == "unavailable"
    core_item = _knowledge_item("src-any", tier="core", review="approved")
    assert resolver.filter_current([core_item])[0] == [core_item]
    allowed, _ = resolver.allows_current(core_item)
    assert allowed is True
