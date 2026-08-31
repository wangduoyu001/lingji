# Owner Memory Detail Drilldown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变普通信息架构、永久记忆权威或现有主人操作的前提下，让主人点击任意当前记忆卡后进入真正可核对的记忆大详情，按需看到 canonical 正文、当前结论、时间线、来源原文、四层状态和需要主人处理的备用操作。

**Architecture:** 保留 `OwnerMemoryCardProjector` 的 current-only、有界摘要投影和四项普通导航。详情由已选中的单条 memory 组装现有 canonical/source/vector 路由与一个新增的认证、有界、分页 linked-evidence route；后端复用 `MemoryInspectorFacade`、`SourceReadModel`、`lingji_memory.db` 和现有 source/privacy authority，不增加数据库、projector、状态源、端口或 DELETE。Desktop 只在点击单卡后读取同一 `memory_id` 的资源，按页显示证据正文，所有历史/过时状态和技术字段都在详情语义中明确表达。

**Tech Stack:** Python/FastAPI-compatible Local Control API on authenticated `127.0.0.1:8766`; existing `MemoryInspectorFacade`, `SourceQueryService`, `SourceReadModel`, `lingji_memory.db`, semantic vector provider; React/TypeScript Desktop; Playwright rendered E2E; pytest focused contracts.

## Global Constraints

- 普通导航仍固定为 `首页 / 记忆内容 / 需要我 / 记忆来源`；普通列表请求仍为 `state=current`，历史、过时、替代版本、rejected 不得混入。
- 详情必须展示灵机实际记住的 canonical 正文、当前结论、按时间排序的发展过程、来源软件/会话/时间/角色与原文、raw/structured/vector/permanent 四层状态及是否需要主人处理。
- 修正、过时、移出、拒绝只位于最底部折叠的“备用操作”；不增加日常按钮，不增加物理删除。
- 唯一新增后端能力是认证、bounded、paginated linked-evidence route；默认 `limit=20`，硬上限 `50`，稳定排序，excerpt/body 有界；现有单条 message route 负责全文核对，不得直接暴露无界 `memory_evidence()`。
- canonical body 仅在选中单条 memory 后读取；超长正文明确 `truncated`/继续查看语义，不能把截断文本冒充完整。
- 没有 canonical 的 `conversation_evidence` 必须显示“这是原始会话，尚未形成长期记忆”，并复用现有 conversation messages 分页。
- raw absolute path、token、cookie、任意 JSON 不显示；technical IDs 默认折叠；safe `raw:`/`vault:` reference 只能在详情的来源核对区域出现。
- 所有 source/message/privacy/agent-scope/authority 检查复用现有 `SourceQueryService`；不可见、revoked、expired、hash mismatch、unknown 均 fail-closed，不伪造健康或完整。
- 不新建库、永久事实源、projector、队列、状态源、端口或删除路由；Desktop 不直连 SQLite/Qdrant。
- RED/GREEN 必须覆盖后端 auth/limit/pagination/stable order/privacy/source authority、前端真实请求/body/timeline/layers/fallback action/load more/no prefetch、rendered E2E 1024/1280、长文、unknown/error/409 和现有动作。
- 实现任务只运行 focused/product implementation；不得启动 live 8766/8767、安装候选、读取真实聊天/Vault/数据库或操作主人数据。
- 新 Mac acceptance 只能在实现产生新的产品 SHA、focused/full/release 门禁通过后另建；必须全包构建/安装并由 Computer Use 全页遍历，至少打开五种不同类型记忆并展开多个来源原文，主人确认前不能写完成。

---

### Task 1: Freeze the detail contract and RED coverage

**Files:**
- Modify: `tests/test_owner_memory_card_projector.py`
- Modify: `tests/test_memory_inspector_api.py`
- Create: `tests/test_owner_memory_detail_contract.py`
- Reference: `src/gateway/owner_memory_cards.py`, `src/gateway/memory_inspector.py`, `src/sources/service.py`

**Interfaces:**
- Produces the test contract for `MemoryInspectorFacade.list_memory_evidence(memory_id: str, *, limit: int = 20, offset: int = 0, include_content: bool = True) -> EvidencePage`.
- `EvidencePage` contains `as_of`, `memory_id`, `items`, and `pagination`; each item contains `source_id`, `conversation_id`, `message_id`, `role`, `sequence`, `occurred_at`, bounded `excerpt`, optional bounded `content`, `content_hash`, and safe `raw_reference`.
- Existing `OwnerMemoryCardProjector.list_cards()` remains summary-only; existing `get_card()` remains bounded and does not read all message bodies.

- [ ] **Step 1: Write the failing contract tests.** Add fixtures with 7 linked messages, 2 canonical chunks, a verified conclusion, one restricted source, one revoked source, one conversation-only evidence card, and one superseded card. Assert the following exact behavior:

```python
def test_detail_contract_keeps_current_list_summary_only(fixture_db, projector):
    cards = projector.list_cards(state="current", limit=20, offset=0)
    assert all("content" not in card for card in cards.items)
    assert all(len(card["evidence"]) <= 3 for card in cards.items if "evidence" in card)
    detail = projector.get_card(cards.items[0]["memory_id"], expand=True)
    assert detail["layers"]["raw"]["state"] in {"available", "unknown", "unavailable"}
    assert detail["layers"]["structured"]["state"] in {"available", "unknown", "unavailable"}
    assert detail["layers"]["vector"]["state"] in {"available", "partial", "unknown", "unavailable"}
    assert detail["layers"]["permanent"]["state"] in {"core", "derived", "pending", "not_permanent", "unknown"}

def test_evidence_page_contract_is_bounded_and_stably_ordered(facade, seeded_links):
    page = facade.list_memory_evidence(seeded_links.memory_id, limit=3, offset=0)
    assert [item.message_id for item in page.items] == ["m-01", "m-02", "m-03"]
    assert page.pagination == {"limit": 3, "offset": 0, "total": 7, "has_more": True}
    assert all(len(item.excerpt) <= 240 for item in page.items)
    assert all(item.content_hash for item in page.items)

def test_conversation_evidence_without_canonical_has_explicit_copy(projector, conversation_card):
    detail = projector.get_card(conversation_card.memory_id, expand=True)
    assert detail["projection"] == "conversation_evidence"
    assert detail["canonical"] is None
    assert detail["detail_message"] == "这是原始会话，尚未形成长期记忆"

def test_history_detail_is_explicitly_non_current(projector, superseded_id):
    detail = projector.get_card(superseded_id, expand=True)
    assert detail["freshness"]["state"] != "current"
    assert detail["freshness"]["replacement_id"]
    assert detail["action"]["delete"] is False
```

- [ ] **Step 2: Run RED tests against the 94461d56 baseline.**

Run: `python3 -m pytest -q tests/test_owner_memory_detail_contract.py tests/test_owner_memory_card_projector.py tests/test_memory_inspector_api.py --tb=short`

Expected: FAIL because no paginated evidence facade/route or detail canonical/layer contract is wired; preserve the failure output in the implementation report without weakening existing bounded-list assertions.

- [ ] **Step 3: Record the RED boundary.** Confirm the failing assertions identify missing detail behavior rather than fixture/setup errors, and record the exact baseline SHA `94461d56c64f31e1af6c7cdece51e959ddc0e8b1` in the task report.

---

### Task 2: Implement bounded linked-evidence authority in the existing facade

**Files:**
- Modify: `src/gateway/memory_inspector.py`
- Modify: `src/sources/service.py`
- Modify: `tests/test_owner_memory_detail_contract.py`
- Modify: `tests/test_source_service.py`

**Interfaces:**
- `MemoryInspectorFacade.list_memory_evidence(memory_id, *, limit=20, offset=0, include_content=True) -> EvidencePage` validates `1 <= limit <= 50`, rejects negative offsets, counts links before slicing, and never calls the existing unbounded `memory_evidence()` method.
- `SourceQueryService.list_memory_evidence_page(memory_id, *, limit, offset, include_content, viewer="owner") -> EvidencePage` applies the existing viewer privacy, agent scope, source authority, and safe-reference logic before returning items.
- Stable ordering is `(occurred_at_utc, sequence, source_id, conversation_id, message_id)` with missing/invalid times sorted after valid times; `total` and `has_more` are calculated from the visible set.

- [ ] **Step 1: Extend tests for authority and page boundaries.** Add cases for `limit=0`, `limit=51`, negative offset, equal timestamps, mixed timezone offsets, invalid timestamps, restricted source, revoked/expired source, agent-scope mismatch, and content-hash mismatch.

```python
def test_evidence_page_rechecks_visibility_and_source_authority(facade, fixture_db):
    page = facade.list_memory_evidence("memory-visible", limit=20, offset=0)
    assert [item.message_id for item in page.items] == ["visible-1"]
    assert "restricted-1" not in {item.message_id for item in page.items}
    assert "revoked-1" not in {item.message_id for item in page.items}
    assert "expired-1" not in {item.message_id for item in page.items}
    assert all("/Users/" not in item.raw_reference for item in page.items)
    assert all("token" not in item.excerpt.lower() for item in page.items)

def test_evidence_page_stable_tie_breakers(facade):
    page = facade.list_memory_evidence("memory-same-time", limit=50, offset=0)
    assert [item.message_id for item in page.items] == ["a", "b", "c", "d"]
```

- [ ] **Step 2: Run the new tests to verify RED.**

Run: `python3 -m pytest -q tests/test_owner_memory_detail_contract.py tests/test_source_service.py -k 'evidence_page or authority or tie_breaker' --tb=short`

Expected: FAIL at the missing page method or missing route-facing DTO, while existing single-message privacy tests remain green.

- [ ] **Step 3: Implement the minimal bounded read.** Query only visible link metadata for the requested page, sort with the exact stable key, then fetch at most that page's message bodies through the existing `get_message(..., include_content=True)` authority path. Apply an explicit per-item excerpt/body character bound and set a truncation flag when content is clipped. Return `total`, `offset`, `limit`, `has_more`, `as_of`, and the selected `memory_id`; keep technical identifiers in the DTO because the UI will fold them, but never include absolute paths, tokens, cookies, or raw JSON.

- [ ] **Step 4: Run GREEN focused tests.**

Run: `python3 -m pytest -q tests/test_owner_memory_detail_contract.py tests/test_source_service.py tests/test_memory_inspector_facade.py --tb=short`

Expected: PASS for page bounds, deterministic order, privacy/source authority, content hash pairing, and no use of unbounded `memory_evidence()`.

- [ ] **Step 5: Commit the bounded facade seam.**

```bash
git add src/gateway/memory_inspector.py src/sources/service.py tests/test_owner_memory_detail_contract.py tests/test_source_service.py
git commit -m "feat: add bounded owner memory evidence pages"
```

---

### Task 3: Expose the evidence page through authenticated 8766 API

**Files:**
- Modify: `src/control/api.py`
- Modify: `tests/test_owner_memory_card_api.py`
- Modify: `tests/test_memory_inspector_api.py`
- Reference: `src/control/memory_inspector.py`, existing authenticated memory routes

**Interfaces:**
- Register `GET /api/memory/inspector/memories/{memory_id}/evidence` in the existing control app.
- Query parameters are `limit: int = 20`, `offset: int = 0`, `include_content: bool = True`; invalid bounds return 422, missing/wrong token returns 401, and missing/unauthorized memory returns the existing safe 404/403 contract without body leakage.
- JSON response is `{ "as_of": str, "memory_id": str, "items": [...], "pagination": {"limit": int, "offset": int, "total": int, "has_more": bool} }`.

- [ ] **Step 1: Add API RED tests.** Extend the existing authenticated API fixture:

```python
def test_memory_evidence_route_is_authenticated_bounded_and_paginated(client, auth_token):
    assert client.get("/api/memory/inspector/memories/m-1/evidence").status_code == 401
    assert client.get(
        "/api/memory/inspector/memories/m-1/evidence",
        headers={"X-LingJi-Token": "wrong"},
    ).status_code == 401
    response = client.get(
        "/api/memory/inspector/memories/m-1/evidence?limit=2&offset=0",
        headers={"X-LingJi-Token": auth_token},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"] == {"limit": 2, "offset": 0, "total": 7, "has_more": True}
    assert all(len(item["excerpt"]) <= 240 for item in payload["items"])
    assert client.get(
        "/api/memory/inspector/memories/m-1/evidence?limit=51",
        headers={"X-LingJi-Token": auth_token},
    ).status_code == 422
```

- [ ] **Step 2: Run RED.**

Run: `python3 -m pytest -q tests/test_owner_memory_card_api.py tests/test_memory_inspector_api.py -k 'evidence' --tb=short`

Expected: FAIL because the route is not registered.

- [ ] **Step 3: Add the authenticated route.** Reuse the same token dependency and `MemoryInspectorFacade` composition as `/memories/{id}`, pass validated query values to `list_memory_evidence`, and map only known safe exceptions to existing HTTP responses. Do not add a route for the unbounded `memory_evidence()` method.

- [ ] **Step 4: Run GREEN API tests.**

Run: `python3 -m pytest -q tests/test_owner_memory_card_api.py tests/test_memory_inspector_api.py --tb=short`

Expected: PASS with 401/422 behavior, pagination metadata, bounded response bodies, and no raw secret/path leakage.

- [ ] **Step 5: Commit the API contract.**

```bash
git add src/control/api.py tests/test_owner_memory_card_api.py tests/test_memory_inspector_api.py
git commit -m "feat: expose authenticated paginated memory evidence"
```

---

### Task 4: Make the selected-memory snapshot complete and bounded

**Files:**
- Modify: `src/gateway/memory_inspector.py`
- Modify: `src/control/api.py`
- Modify: `tests/test_owner_memory_detail_contract.py`
- Modify: `tests/test_memory_inspector_api.py`

**Interfaces:**
- Extend the existing selected-memory route with bounded optional parameters `chunk_limit: int = 20`, `max_chars: int = 12000`, and `cursor: str | None = None`; do not create a second canonical store or route family.
- The selected-memory response contains `memory_id`, `as_of`, `content_hash`, `canonical` (or `None`), `canonical.truncated`, `canonical.next_cursor`, `conclusion`, `freshness`, `layers`, `source`, `action`, and `projection`.
- `projection == "conversation_evidence"` with no canonical returns the exact human-facing copy “这是原始会话，尚未形成长期记忆” and points the UI to existing conversation messages pagination.

- [ ] **Step 1: Add bounded canonical RED tests.**

```python
def test_selected_memory_returns_canonical_body_only_for_requested_memory(facade, fixture_db):
    detail = facade.get_memory_detail("memory-long", chunk_limit=1, max_chars=80)
    assert detail["memory_id"] == "memory-long"
    assert detail["canonical"]["truncated"] is True
    assert detail["canonical"]["next_cursor"]
    assert len(detail["canonical"]["text"]) <= 80

def test_selected_conversation_evidence_uses_existing_message_pagination(facade):
    detail = facade.get_memory_detail("conversation-only")
    assert detail["canonical"] is None
    assert detail["projection"] == "conversation_evidence"
    assert detail["conversation_messages_route"].endswith("/messages")
```

- [ ] **Step 2: Run RED.**

Run: `python3 -m pytest -q tests/test_owner_memory_detail_contract.py tests/test_memory_inspector_api.py -k 'canonical or conversation_only' --tb=short`

Expected: FAIL because the current memory inspector response is unbounded/all-chunk and does not carry truncation/cursor or the conversation-only copy.

- [ ] **Step 3: Implement bounded selected reads.** Read canonical chunks only after a memory ID is selected, cap each response, return continuation metadata, and preserve the selected memory's `content_hash`/`as_of` identity. Reuse existing vector/source routes and include their layer state in the composed detail contract; a vector check failure remains unknown/unavailable.

- [ ] **Step 4: Run GREEN.**

Run: `python3 -m pytest -q tests/test_owner_memory_detail_contract.py tests/test_memory_inspector_api.py tests/test_memory_inspector_facade.py --tb=short`

Expected: PASS for canonical body, truncation semantics, conversation-only fallback, vector/source layer states, and current/history identity.

- [ ] **Step 5: Commit the selected snapshot contract.**

```bash
git add src/gateway/memory_inspector.py src/control/api.py tests/test_owner_memory_detail_contract.py tests/test_memory_inspector_api.py
git commit -m "feat: bound selected owner memory snapshots"
```

---

### Task 5: Add explicit Desktop detail types and selected-only API calls

**Files:**
- Modify: `desktop/lingji-control/src/pages/ownerMemoryCardsTypes.ts`
- Modify: `desktop/lingji-control/src/pages/ownerMemoryCardsApi.ts`
- Modify: `desktop/lingji-control/src/pages/OwnerMemoryCardsPage.tsx`
- Modify: `desktop/lingji-control/scripts/owner-ui-menu-fast-track-smoke.mjs`

**Interfaces:**
- Add TypeScript types `OwnerMemoryDetail`, `CanonicalBody`, `EvidenceItem`, `EvidencePage`, `LayerState`, and `DetailLoadState` with explicit `truncated`, `nextCursor`, `hasMore`, `asOf`, and `contentHash` fields.
- Add API functions `getOwnerMemoryDetail(memoryId, options?)`, `getOwnerMemoryVector(memoryId)`, `getOwnerMemorySource(memoryId)`, and `getOwnerMemoryEvidence(memoryId, { limit = 20, offset = 0 })`, all using the existing `LingJiApi` token path and no direct database access.
- `open(memoryId)` first selects the card, then requests exactly the selected card's detail/canonical/vector/source/evidence page; list rendering must never call any body endpoint.

- [ ] **Step 1: Add frontend RED smoke assertions.** Instrument the existing fixture server and assert request order/targets and absence of prefetch:

```javascript
await page.getByRole('button', { name: '发布计划' }).click();
assert.deepEqual(requests.filter((url) => url.includes('/cards/')).length, 1);
assert(requests.some((url) => url.endsWith('/memories/memory-1')));
assert(requests.some((url) => url.includes('/memories/memory-1/evidence?limit=20&offset=0')));
assert(!requests.some((url) => url.includes('/messages/other-memory')));
await page.getByRole('button', { name: '加载更多来源' }).click();
assert(requests.some((url) => url.includes('/evidence?limit=20&offset=20')));
assert(!requests.some((url) => url.includes('/evidence?limit=20&offset=40')));
```

- [ ] **Step 2: Run RED.**

Run: `cd desktop/lingji-control && npm run test:owner-ui-menu-fast-track`

Expected: FAIL because opening a card currently requests only bounded card detail and one manually selected message, with no canonical/vector/source/evidence-page orchestration.

- [ ] **Step 3: Implement typed selected-only requests.** Use `Promise.all` only for the selected card's canonical/vector/source/first evidence page, retain independent load/error state for each section, and abort or ignore stale responses when the panel closes or a different card is selected. The list query remains `state=current`, `limit=20`, and has no body prefetch.

- [ ] **Step 4: Run GREEN static/contract checks.**

Run: `cd desktop/lingji-control && npm run test:owner-ui-menu-fast-track && npm run build`

Expected: PASS with request assertions, TypeScript build, existing four-menu/current-only behavior, and no additional list body requests.

- [ ] **Step 5: Commit the typed client seam.**

```bash
git add desktop/lingji-control/src/pages/ownerMemoryCardsTypes.ts desktop/lingji-control/src/pages/ownerMemoryCardsApi.ts desktop/lingji-control/src/pages/OwnerMemoryCardsPage.tsx desktop/lingji-control/scripts/owner-ui-menu-fast-track-smoke.mjs
git commit -m "feat: load owner memory details on selection"
```

---

### Task 6: Render the memory verification page and safe fallback actions

**Files:**
- Modify: `desktop/lingji-control/src/pages/OwnerMemoryCardsPage.tsx`
- Modify: `desktop/lingji-control/src/pages/LocalMemoryLoop.css`
- Modify: `desktop/lingji-control/src/pages/ownerMemoryCardsTypes.ts`
- Modify: `desktop/lingji-control/scripts/owner-ui-menu-fast-track-smoke.mjs`

**Interfaces:**
- Detail sections appear in this order: “灵机当前记住的内容”, “当前结论”, “事情怎么发展”, “来源与核对”, “四层状态”, “需要不需要主人处理”, then a collapsed bottom “备用操作”.
- Timeline rows display source software, conversation, occurred time, role, sequence, bounded excerpt/body, and a clear “继续查看全文” action using the existing single-message route.
- Layer labels are exactly “原始记录 / 结构记录 / 语义向量 / 长期记忆”; unknown/unavailable states use “尚未获得/不可用” rather than `0`, `healthy`, or `complete`.
- Historical detail shows freshness/replacement/reason in non-current language; normal list remains current-only. `action` drives the existing correction/invalidate/archive/reject calls only from the collapsed fallback.

- [ ] **Step 1: Add rendered RED assertions for visible semantics.** Extend the smoke fixture with current verified, no-vector, long canonical, conversation-only, superseded, restricted and action-required cards:

```javascript
assert(await page.getByText('灵机当前记住的内容').isVisible());
assert(await page.getByText('当前结论').isVisible());
assert(await page.getByText('事情怎么发展').isVisible());
assert(await page.getByText('原始记录').isVisible());
assert(await page.getByText('结构记录').isVisible());
assert(await page.getByText('语义向量').isVisible());
assert(await page.getByText('长期记忆').isVisible());
assert(await page.getByText('备用操作').isVisible());
assert(await page.getByText('这是原始会话，尚未形成长期记忆').isVisible());
assert((await page.locator('[data-testid="evidence-item"]').count()) <= 20);
```

- [ ] **Step 2: Run RED.**

Run: `cd desktop/lingji-control && npm run test:owner-ui-menu-fast-track`

Expected: FAIL because the current panel renders only topic, conclusion fallback, three previews, and existing action controls.

- [ ] **Step 3: Implement the detail sections.** Render canonical content with `truncated` badge and continuation affordance; render current conclusion/provenance without inferring a conclusion from message text; render evidence pages with role/time/sequence/source; render folded technical IDs and safe references; keep raw paths/tokens/cookies/JSON out of visible text and attributes. Use CSS max-width/overflow and a scrollable long-body region without horizontal overflow at 1024px.

- [ ] **Step 4: Move actions into the bottom disclosure.** Preserve existing correction/invalidate/archive/reject handlers, confirmation, fresh GET, and 409 protection. Label lifecycle actions as retaining history; provide no physical delete control. The detail panel close button and Escape behavior remain functional.

- [ ] **Step 5: Run GREEN UI smoke/build.**

Run: `cd desktop/lingji-control && npm run test:owner-ui-menu-fast-track && npm run build`

Expected: PASS for all visible sections, safe copy, fallback action placement, long-body truncation, and 1024/1280 layout.

- [ ] **Step 6: Commit the verification page.**

```bash
git add desktop/lingji-control/src/pages/OwnerMemoryCardsPage.tsx desktop/lingji-control/src/pages/LocalMemoryLoop.css desktop/lingji-control/src/pages/ownerMemoryCardsTypes.ts desktop/lingji-control/scripts/owner-ui-menu-fast-track-smoke.mjs
git commit -m "feat: render owner memory verification details"
```

---

### Task 7: Cover pagination, privacy failures, revisions, and existing actions

**Files:**
- Modify: `desktop/lingji-control/src/pages/OwnerMemoryCardsPage.tsx`
- Modify: `desktop/lingji-control/src/pages/ownerMemoryCardsApi.ts`
- Modify: `desktop/lingji-control/scripts/owner-ui-menu-fast-track-smoke.mjs`
- Modify: `desktop/lingji-control/tests/e2e_owner_memory_flow.mjs`
- Modify: `tests/test_owner_memory_card_projector.py`
- Modify: `tests/test_owner_memory_card_api.py`

**Interfaces:**
- “加载更多来源” advances by the current page size and appends only one bounded page; loading, retry, empty, 401/503, and 409 states are explicit and actionable.
- A changed `content_hash`/`as_of` returns a revision conflict that preserves unsaved owner edits and offers refresh; it must not silently replace the panel.
- Restricted evidence is collapsed and requires an explicit owner click; unavailable source/vector data remains unknown/unavailable.

- [ ] **Step 1: Add failure-mode RED tests.** Assert page 2 appends exactly 20-or-fewer items, page 3 is not fetched, 503 offers retry, 401 asks for reconnect/authentication, 409 preserves a draft correction, and source mismatch never displays the old conclusion.

```javascript
await page.getByRole('button', { name: '加载更多来源' }).click();
assert.equal(await page.locator('[data-testid="evidence-item"]').count(), 40);
assert.equal(requests.filter((url) => url.includes('/evidence?limit=20&offset=40')).length, 0);
assert(await page.getByText('详情版本已变化，请重新读取').isVisible());
assert(await page.getByText('请先重新连接灵机').isVisible());
```

- [ ] **Step 2: Run RED.**

Run: `cd desktop/lingji-control && npm run test:e2e:memory && npm run test:owner-ui-menu-fast-track`

Expected: FAIL on the newly asserted drilldown and failure semantics while existing action/current-only assertions remain diagnostic.

- [ ] **Step 3: Implement explicit state handling.** Use one request controller per selected detail, page evidence with `offset += items.length`, cap append count, and show retries inline. On 409, hold the draft and show both the current snapshot identity and refresh action. Keep existing owner correction/invalidation/archive/reject request paths and fresh GET behavior unchanged.

- [ ] **Step 4: Run GREEN failure/action tests.**

Run: `python3 -m pytest -q tests/test_owner_memory_card_projector.py tests/test_owner_memory_card_api.py tests/test_owner_memory_corrections.py tests/test_project_memory_api.py --tb=short`  
Run: `cd desktop/lingji-control && npm run test:owner-ui-menu-fast-track && npm run test:e2e:memory`

Expected: PASS for privacy/authority, current/history isolation, bounded loading, error/revision behavior, and all existing lifecycle actions.

- [ ] **Step 5: Commit edge-state behavior.**

```bash
git add desktop/lingji-control/src/pages/OwnerMemoryCardsPage.tsx desktop/lingji-control/src/pages/ownerMemoryCardsApi.ts desktop/lingji-control/scripts/owner-ui-menu-fast-track-smoke.mjs desktop/lingji-control/tests/e2e_owner_memory_flow.mjs tests/test_owner_memory_card_projector.py tests/test_owner_memory_card_api.py
git commit -m "test: cover owner memory detail edge states"
```

---

### Task 8: Add rendered 1024/1280 end-to-end proof and navigation regression

**Files:**
- Modify: `desktop/lingji-control/tests/e2e_owner_memory_flow.mjs`
- Modify: `desktop/lingji-control/scripts/owner-ui-menu-fast-track-smoke.mjs`
- Modify: `desktop/lingji-control/src/navigation.ts` only if a regression test proves the existing four-item order changed
- Modify: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`

**Interfaces:**
- Rendered fixture must include at least 37 current cards plus 3 history cards, 13 permanent memories, 3 conversations, 36 messages, one pending owner action, eight distinct readable conclusions, one vector-unavailable memory, one conflict, one long body, one conversation-only evidence card, and one superseded card.
- E2E must click at least five different memory types, expand multiple source originals through the existing single-message route, and verify current-only pages, exact pagination, body/timeline/layers/actions, 1024 and 1280 layouts, and no horizontal overflow.
- Ordinary nav remains exactly four destinations; advanced diagnostics stays collapsed/low emphasis and is not duplicated.

- [ ] **Step 1: Write the rendered RED scenarios.** Add real browser assertions for list leakage zero, selected-only request traces, canonical body/truncation, timeline ordering and load-more, source expansion, layer copy/state, conversation-only copy, historical replacement, action success/fresh GET, 401/503/409, Escape/close/focus, and 1024/1280 overflow.

- [ ] **Step 2: Run the rendered RED suite.**

Run: `cd desktop/lingji-control && npm run test:e2e:memory && npm run test:owner-ui-menu-fast-track`

Expected: FAIL only on the new detail expectations; the pre-existing four-menu/current-only/action assertions must remain passing or be diagnosed before implementation continues.

- [ ] **Step 3: Make the fixture and tests deterministic.** Record request URLs and response identities, assert UTC-stable timeline ordering, bound DOM evidence rows to one page, and use semantic selectors (`role`, labels, `data-testid`) rather than implementation-specific CSS text matching.

- [ ] **Step 4: Run the full rendered GREEN suite.**

Run: `cd desktop/lingji-control && npm run test:e2e:memory && npm run test:owner-ui-menu-fast-track && npm run test:smoke && npm run build`

Expected: PASS at both viewport sizes with all visible controls working and no prefetch/current-history/navigation regressions.

- [ ] **Step 5: Commit the rendered acceptance coverage.**

```bash
git add desktop/lingji-control/tests/e2e_owner_memory_flow.mjs desktop/lingji-control/scripts/owner-ui-menu-fast-track-smoke.mjs docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md
git commit -m "test: verify owner memory detail drilldown"
```

---

### Task 9: Run focused gates, synchronize acceptance docs, and hand off to a new Mac task

**Files:**
- Modify: `docs/PROJECT_STATUS.md`
- Modify: `docs/MODULES/CODE_MAP.md`
- Modify: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Modify: `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`
- Modify: `docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md`
- Create: `docs/TEST_REPORTS/OWNER_MEMORY_DETAIL_DRILLDOWN_IMPLEMENTATION.md`
- Create: `.superpowers/sdd/2026-08-31-owner-memory-detail-drilldown/task-implementation-report.md`

**Interfaces:**
- The implementation report records exact product SHA, RED/GREEN commands, focused results, changed files, privacy/current-history evidence, and explicit `NOT_TESTED` for live/installation/owner data.
- `LOCAL_EXECUTION_TASK.md` remains the only task entry and is `ACTIVE` only for `OWNER_MEMORY_DETAIL_DRILLDOWN_IMPLEMENTATION` with `FOCUSED_PRODUCT_IMPLEMENTATION_ONLY`; its product commit is the exact new implementation SHA and its report path is under `docs/TEST_REPORTS/`.
- The old `OWNER_UI_SOURCE_FILTER_REPAIR_4CE1E00A` is recorded as `COMPLETED / FAIL`, with `owner_observation: FAIL`, and is never active again.

- [ ] **Step 1: Update the acceptance log before final product verification.** Add the exact detail scope, RED/GREEN commands, no-live/no-owner-data boundary, later-Mac requirements (new SHA, full/release, fresh root, same-SHA Artifact, full Computer Use, five memory types and multiple originals), and rollback/cleanup rules to `CHANGE_ACCEPTANCE_LOG.md`.

- [ ] **Step 2: Run focused backend and Desktop gates.**

Run: `python3 -m pytest -q tests/test_owner_memory_detail_contract.py tests/test_owner_memory_card_projector.py tests/test_owner_memory_card_api.py tests/test_memory_inspector_api.py tests/test_memory_inspector_facade.py tests/test_source_service.py tests/test_owner_memory_corrections.py tests/test_project_memory_api.py --tb=short`  
Run: `cd desktop/lingji-control && npm run test:e2e:memory && npm run test:owner-ui-menu-fast-track && npm run test:smoke && npm run build`  
Run: `python3 -m compileall -q src tests`  
Run: `git diff --check`

Expected: PASS with no skipped detail assertions, while preserving any explicitly documented pre-existing unrelated baseline failures.

- [ ] **Step 3: Run governance gates.**

Run: `python3 scripts/check_acceptance_sync.py`  
Run: `python3 scripts/check_local_execution_handoff.py`

Expected: both commands report PASS; no product change is accepted without the synchronized acceptance log.

- [ ] **Step 4: Write the implementation report.** Include exact branch/commit, plan task count (9), RED/GREEN evidence, tests and results, changed files, known limitations, and the statement `live/安装/主人数据：NOT_TESTED`.

- [ ] **Step 5: Commit docs-only handoff after the implementation SHA is known.**

```bash
git add docs/PROJECT_STATUS.md docs/MODULES/CODE_MAP.md docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md docs/TEST_REPORTS/OWNER_MEMORY_DETAIL_DRILLDOWN_IMPLEMENTATION.md .superpowers/sdd/2026-08-31-owner-memory-detail-drilldown/task-implementation-report.md
git commit -m "docs: activate owner memory detail drilldown"
```

- [ ] **Step 6: Stop at the implementation boundary.** Do not build/install/start live services or create the Mac acceptance task in this implementation worktree. After a later product SHA passes the repository's full/release gates, the parent agent creates a fresh Mac acceptance task and preserves this implementation evidence.

## Self-review checklist

- Ordinary navigation/current-only list: Task 8 regression coverage.
- Canonical body/conclusion/timeline/source originals/layers/owner handling: Tasks 4–6.
- Bottom-only fallback actions and no physical delete: Task 6 and Task 7.
- Existing API/facade/read-model reuse and bounded paginated evidence: Tasks 2–4.
- Selected-only canonical read and explicit truncation: Tasks 4–5.
- Conversation-only copy and message pagination: Tasks 1, 4, and 8.
- Privacy/source authority/raw secret redaction/technical ID folding: Tasks 2, 3, 6, and 7.
- RED/GREEN focused and rendered 1024/1280 tests: Tasks 1, 3, 5, 6, 7, and 8.
- New SHA Mac acceptance, five memory types, multiple originals, owner confirmation gate: Global Constraints and Task 9.

Plan complete and saved to `docs/superpowers/plans/2026-08-31-owner-memory-detail-drilldown.md`. Execution must use the focused implementation task first; Mac acceptance is a separate later task after the new product SHA and release gates exist.
