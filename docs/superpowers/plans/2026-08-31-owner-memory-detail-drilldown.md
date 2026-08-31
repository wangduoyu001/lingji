# Owner Memory Detail Drilldown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让主人点击任意记忆卡后进入真正可核对的大详情，默认看见 canonical 正文、当前结论、发展过程、来源原文、四层状态和主人处理语义，同时保持四项普通导航与 current-only 列表不变。

**Architecture:** Owner UI 组合既有 `/api/memory/inspector/cards/{id}` bounded card、既有 `/memories/{id}` canonical、`/vector`、`/source` 和唯一新增的分页 evidence route；不把 card DTO 扩展成全文，也不让 canonical route 返回 card 状态。后端在现有 `SourceReadModel`/`SourceQueryService`/`MemoryInspectorFacade` 上增加 bounded linked-evidence page，Desktop 仅在选中单卡后并行读取该单条 memory 的资源。

**Tech Stack:** Python authenticated Local Control API on `127.0.0.1:8766`; existing `MemoryInspectorFacade`, `SourceQueryService`, `SourceReadModel`, `lingji_memory.db`, vector/source/message/conversation routes; React/TypeScript Desktop; pytest; Playwright rendered E2E.

## Global Constraints

- 普通导航严格为 `首页 / 记忆内容 / 需要我 / 记忆来源`；普通记忆列表继续请求 `state=current`，历史、过时、替代版本、rejected 不得混入。
- Owner 详情默认显示 canonical 正文、当前结论、按时间排序的过程、来源软件/会话/时间/角色/原文、`原始记录 / 结构记录 / 语义向量 / 长期记忆` 四层状态和是否需要主人处理。
- 修正、过时、移出、拒绝全部位于最底部折叠“备用操作”，不新增日常按钮，不新增物理删除。
- 唯一新 route 是 `GET /api/memory/inspector/memories/{memory_id}/evidence?limit=20&offset=0`；默认 `20`、最大 `50`，稳定排序；每 item `excerpt <= 240`、`content <= 4000`，单页 content 总量 `<= 24000`，返回 `truncated`。完整单条原文继续使用既有 `/messages/{id}`。
- Evidence 稳定排序键为 `(occurred_at_utc, sequence, source_id, conversation_id, message_id)`；`total`/`has_more` 对可见集合计算。
- canonical 只在选中单条 memory 后读取。`/memories/{id}` 只能增加向后兼容的 `chunk_limit`/`max_chars`/`cursor` 参数并保留原 response fields；`truncated` 必须明确为截断，不能暗示完整。
- `conversation_evidence` 没有 canonical 时由前端根据 card `kind`/`source.conversation_id` 显示“这是原始会话，尚未形成长期记忆”，并使用既有 conversation messages 分页；不得调用 canonical 读取来制造空白或错误。
- 后端复用既有 source privacy、agent scope、source authority、safe reference；未授权/撤销/过期/不可见来源正文不泄漏。raw absolute path、cookie、auth metadata、任意 JSON 不展示；technical IDs 默认折叠。
- 不新增数据库、projector、状态源、队列、端口或 DELETE；Desktop 不直连 SQLite/Qdrant。
- 本任务只允许 focused/product implementation，不启动 live 8766/8767、不安装候选、不读取真实聊天/Vault/数据库、不操作主人数据。
- 新 Mac acceptance 只能在新的产品 SHA 通过 focused/full/release 后另建；须全包构建/安装、Computer Use 全页遍历，至少点开五种不同记忆并展开多个来源全文，主人确认前不得完成。

---

### Task 1: Bounded evidence backend and selected-resource contracts

**Files:**
- Modify: `src/sources/service.py`
- Modify: `src/gateway/memory_inspector.py`
- Modify: `src/control/api.py`
- Modify: `tests/test_owner_memory_card_projector.py`
- Modify: `tests/test_owner_memory_card_api.py`
- Modify: `tests/test_memory_inspector_api.py`
- Modify: `tests/test_memory_inspector_facade.py`
- Modify: `tests/test_source_service.py`
- Create: `tests/test_owner_memory_detail_contract.py`

**Interfaces:**
- `SourceQueryService.list_memory_evidence_page(memory_id: str, *, limit: int = 20, offset: int = 0, include_content: bool = True, viewer: ViewerContext | None = None) -> EvidencePage`；未传入时继续使用既有 owner viewer。
- `MemoryInspectorFacade.list_memory_evidence(memory_id: str, *, limit: int = 20, offset: int = 0, include_content: bool = True) -> EvidencePage` delegates to the existing source authority path and never calls unbounded `memory_evidence()`.
- `EvidencePage` serializes `{as_of, memory_id, items, pagination}`. Each item serializes `source_id`, `conversation_id`, `message_id`, `role`, `sequence`, `occurred_at`, `excerpt`, optional bounded `content`, `content_hash`, safe `raw_reference`, and `truncated`.
- Register only `GET /api/memory/inspector/memories/{memory_id}/evidence`; validate `1 <= limit <= 50`, `offset >= 0`, require the existing auth dependency, and return the established 401/404/422 semantics.
- Existing `/api/memory/inspector/memories/{id}` may accept `chunk_limit`, `max_chars`, `cursor` while preserving its old document/chunk fields; it must not add card conclusion/freshness/layers/action fields.

- [ ] **Step 1: Write backend RED tests before implementation.** Use an isolated fixture with 7 linked messages, equal timestamps, mixed timezone offsets, 2 canonical chunks, one restricted source, one revoked source, one expired source, one conversation-only card, and one superseded card.

```python
def test_list_cards_stays_current_only_and_summary_bounded(projector):
    payload = projector.list_cards(state="current", limit=20, offset=0)
    assert all("content" not in card for card in payload["items"])
    assert all(len(card.get("evidence", [])) <= 3 for card in payload["items"])

def test_evidence_page_has_bounded_stable_order_and_pagination(facade):
    page = facade.list_memory_evidence("memory-1", limit=3, offset=0)
    assert [item["message_id"] for item in page["items"]] == ["m-01", "m-02", "m-03"]
    assert page["pagination"] == {"limit": 3, "offset": 0, "total": 7, "has_more": True}
    assert all(len(item["excerpt"]) <= 240 for item in page["items"])
    assert all(len(item["content"]) <= 4000 for item in page["items"])
    assert sum(len(item["content"]) for item in page["items"]) <= 24000

def test_evidence_page_rechecks_authority_and_safe_references(facade):
    page = facade.list_memory_evidence("memory-1", limit=50, offset=0)
    message_ids = {item["message_id"] for item in page["items"]}
    assert {"restricted", "revoked", "expired"}.isdisjoint(message_ids)
    assert all("/Users/" not in item["raw_reference"] for item in page["items"])
    assert all("cookie" not in item for item in page["items"])
    assert all("auth_metadata" not in item for item in page["items"])

def test_selected_memory_route_only_adds_bounded_canonical_options(client, auth_headers):
    response = client.get("/api/memory/inspector/memories/memory-1?chunk_limit=1&max_chars=80", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    item = payload["item"]
    assert {"memory_id", "chunks"}.issubset(item)
    assert "layers" not in item and "action" not in item
    assert item["chunks"][0]["truncated"] is True
```

- [ ] **Step 2: Run the backend RED suite.**

Run: `python3 -m pytest -q tests/test_owner_memory_detail_contract.py tests/test_owner_memory_card_projector.py tests/test_owner_memory_card_api.py tests/test_memory_inspector_api.py tests/test_memory_inspector_facade.py tests/test_source_service.py --tb=short`

Expected: the new page/route and bounded canonical assertions fail; existing card preview, auth, source privacy and single-message tests remain diagnosable and are not weakened.

- [ ] **Step 3: Implement the minimal backend.** Page visible link metadata first, sort by the exact UTC key, slice the requested page, then read only that page’s message bodies through `SourceQueryService`. Enforce item/page budgets, set `truncated`, return `total`/`has_more`, and use safe references. Wire the route to the existing auth and facade. Add canonical bounds only as optional parameters on the existing route.

- [ ] **Step 4: Run backend GREEN.**

Run: `python3 -m pytest -q tests/test_owner_memory_detail_contract.py tests/test_owner_memory_card_projector.py tests/test_owner_memory_card_api.py tests/test_memory_inspector_api.py tests/test_memory_inspector_facade.py tests/test_source_service.py --tb=short`

Expected: PASS for authentication, bounds, pagination, stable order, authority/privacy, response budgets, selected canonical bounds, and unchanged current-only summaries.

- [ ] **Step 5: Commit Task 1.**

```bash
git add src/sources/service.py src/gateway/memory_inspector.py src/control/api.py tests/test_owner_memory_detail_contract.py tests/test_owner_memory_card_projector.py tests/test_owner_memory_card_api.py tests/test_memory_inspector_api.py tests/test_memory_inspector_facade.py tests/test_source_service.py
git commit -m "feat: add bounded owner memory evidence route"
```

---

### Task 2: Selected-only Desktop detail composition and rendering

**Files:**
- Modify: `desktop/lingji-control/src/pages/ownerMemoryCardsTypes.ts`
- Modify: `desktop/lingji-control/src/pages/ownerMemoryCardsApi.ts`
- Modify: `desktop/lingji-control/src/pages/OwnerMemoryCardsPage.tsx`
- Modify: `desktop/lingji-control/src/pages/LocalMemoryLoop.css`
- Modify: `desktop/lingji-control/scripts/owner-ui-menu-fast-track-smoke.mjs`

**Interfaces:**
- Add `OwnerMemoryDetail`, `CanonicalBody`, `EvidenceItem`, `EvidencePage`, `LayerState`, and `DetailLoadState` with explicit `asOf`, `contentHash`, `truncated`, `nextCursor`, `hasMore`, `limit`, and `offset`.
- Add `getOwnerMemoryDetail(memoryId, options?)`, `getOwnerMemoryVector(memoryId)`, `getOwnerMemorySource(memoryId)`, and `getOwnerMemoryEvidence(memoryId, {limit = 20, offset = 0})` using `LingJiApi` and the existing auth path.
- `open(memoryId)` first selects one card, then concurrently loads only that ID’s `/cards/{id}`, bounded `/memories/{id}`, `/vector`, `/source`, and evidence page offset `0`; list rendering never loads canonical/message/evidence bodies.
- Conversation-only cards are handled from the selected card: display the exact copy “这是原始会话，尚未形成长期记忆” and use existing conversation messages pagination instead of calling `/memories/{id}`.

- [ ] **Step 1: Write Desktop RED request and DOM tests.** Extend the fixture server to record requests and provide current verified, no-vector, long-body, conversation-only, superseded, restricted and action-required cards.

```javascript
await page.getByRole('button', { name: '查看记忆详情' }).first().click();
assert(requests.some((url) => url.endsWith('/cards/memory-1')));
assert(requests.some((url) => url.endsWith('/memories/memory-1?chunk_limit=20&max_chars=12000')));
assert(requests.some((url) => url.includes('/memories/memory-1/evidence?limit=20&offset=0')));
assert(!requests.some((url) => url.includes('/messages/memory-2')));
assert(await page.getByText('灵机当前记住的内容').isVisible());
assert(await page.getByText('当前结论').isVisible());
assert(await page.getByText('事情怎么发展').isVisible());
assert(await page.getByText('原始记录').isVisible());
assert(await page.getByText('结构记录').isVisible());
assert(await page.getByText('语义向量').isVisible());
assert(await page.getByText('长期记忆').isVisible());
assert(await page.getByText('备用操作').isVisible());
```

- [ ] **Step 2: Run Desktop RED.**

Run: `cd desktop/lingji-control && npm run test:owner-ui-menu-fast-track`

Expected: FAIL because the current panel has only card previews and selected single-message behavior.

- [ ] **Step 3: Implement typed selected-only composition.** Keep ordinary list query `state=current&limit=20`, request detail resources only after selection, track each section’s loading/error/unknown state, and retain selected `asOf`/`contentHash`. Do not prefetch other cards or later evidence pages.

- [ ] **Step 4: Render the default-visible sections.** Show canonical text with explicit “内容已截断，可继续查看” when `truncated`; current conclusion and provenance; chronological evidence rows with source software/conversation/time/role/sequence and bounded body; four Chinese layer labels and truthful unknown/unavailable copy; owner-handling reason. Technical IDs and safe references stay in a collapsed disclosure. Put existing correction/invalidate/archive/reject controls only in bottom collapsed “备用操作”; do not add delete.

- [ ] **Step 5: Render conversation-only and long-body semantics.** For card `kind`/`source.conversation_id` with no canonical, show “这是原始会话，尚未形成长期记忆” and the existing paginated conversation messages. For long canonical/evidence content show bounded text plus continuation/single-message route, never claim the excerpt is complete.

- [ ] **Step 6: Run Desktop GREEN.**

Run: `cd desktop/lingji-control && npm run test:owner-ui-menu-fast-track && npm run build`

Expected: PASS for real selected-resource requests, no list prefetch, all default-visible sections, bottom fallback actions, conversation-only copy, truncation, safe disclosure, and 1024/1280 overflow.

- [ ] **Step 7: Commit Task 2.**

```bash
git add desktop/lingji-control/src/pages/ownerMemoryCardsTypes.ts desktop/lingji-control/src/pages/ownerMemoryCardsApi.ts desktop/lingji-control/src/pages/OwnerMemoryCardsPage.tsx desktop/lingji-control/src/pages/LocalMemoryLoop.css desktop/lingji-control/scripts/owner-ui-menu-fast-track-smoke.mjs
git commit -m "feat: render selected owner memory details"
```

---

### Task 3: Rendered E2E edge cases, pagination, and action regression

**Files:**
- Modify: `desktop/lingji-control/tests/e2e_owner_memory_flow.mjs`
- Modify: `desktop/lingji-control/scripts/owner-ui-menu-fast-track-smoke.mjs`
- Modify: `tests/test_owner_memory_card_api.py`
- Modify: `tests/test_owner_memory_corrections.py`

**Interfaces:**
- “加载更多来源” fetches exactly the next evidence page with `offset += currentItems.length`, appends at most 20/50 bounded items, and never fetches a later page before the owner clicks.
- 401/503 show understandable reconnect/retry copy; 409 keeps an unsaved correction draft and offers refresh; restricted evidence requires explicit expansion; vector unavailable remains unknown/unavailable.
- Existing correction/invalidate/archive/reject calls, confirmation and fresh GET continue to work from “备用操作”; history detail shows replacement/reason and never receives current label.

- [ ] **Step 1: Add rendered RED cases.** Use a deterministic fixture of 37 current + 3 history cards, 13 permanent memories, 3 conversations, 36 messages, 8 readable conclusions, one no-vector, one conflict, one long body, one conversation-only card, one superseded card and one owner pending action.

```javascript
await page.getByRole('button', { name: '加载更多来源' }).click();
assert.equal(await page.locator('[data-testid="evidence-item"]').count(), 40);
assert(requests.some((url) => url.includes('/evidence?limit=20&offset=20')));
assert(!requests.some((url) => url.includes('/evidence?limit=20&offset=40')));
assert(await page.getByText('详情版本已变化，请重新读取').isVisible());
assert(await page.getByText('请先重新连接灵机').isVisible());
assert(await page.getByText('这是原始会话，尚未形成长期记忆').isVisible());
assert((await page.getByRole('button', { name: '删除' }).count()) === 0);
```

- [ ] **Step 2: Run rendered RED.**

Run: `cd desktop/lingji-control && npm run test:e2e:memory && npm run test:owner-ui-menu-fast-track`

Expected: new drilldown, failure, and load-more assertions fail; pre-existing four-menu/current-only assertions must remain passing or be diagnosed before proceeding.

- [ ] **Step 3: Implement edge state and action regression.** Append only the clicked next page, provide retry/reconnect controls, preserve drafts across 409, and keep safe error text. Expand five different memory types and multiple source originals through existing `/messages/{id}` calls in the test; verify each lifecycle action changes state and fresh GET refreshes the detail.

- [ ] **Step 4: Run rendered GREEN.**

Run: `cd desktop/lingji-control && npm run test:e2e:memory && npm run test:owner-ui-menu-fast-track && npm run test:smoke && npm run build`

Expected: PASS for 1024/1280, long-body scrolling, bounded evidence pages, current/history isolation, conversation fallback, unknown/error/409, Escape/close/focus, source expansion, and existing actions.

- [ ] **Step 5: Commit Task 3.**

```bash
git add desktop/lingji-control/tests/e2e_owner_memory_flow.mjs desktop/lingji-control/scripts/owner-ui-menu-fast-track-smoke.mjs tests/test_owner_memory_card_api.py tests/test_owner_memory_corrections.py
git commit -m "test: verify owner memory detail edge cases"
```

---

### Task 4: Focused closeout, governance synchronization, and handoff

**Files:**
- Modify: `docs/PROJECT_STATUS.md`
- Modify: `docs/MODULES/CODE_MAP.md`
- Modify: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Modify: `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`
- Modify: `docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md`
- Create: `docs/TEST_REPORTS/OWNER_MEMORY_DETAIL_DRILLDOWN_IMPLEMENTATION.md`

**Interfaces:**
- The implementation report records the exact new product SHA, RED/GREEN results, changed files, security/current-history evidence, and explicit `NOT_TESTED` for live/installation/owner data.
- `LOCAL_EXECUTION_TASK.md` remains the only task entry with `task_id: OWNER_MEMORY_DETAIL_DRILLDOWN_IMPLEMENTATION`, `execution_mode: FOCUSED_PRODUCT_IMPLEMENTATION_ONLY`, and task count `4`.
- Old `OWNER_UI_SOURCE_FILTER_REPAIR_4CE1E00A` remains historical `COMPLETED / FAIL` and is never reactivated.

- [ ] **Step 1: Synchronize docs before closeout tests.** State the 4-task plan, exact route and budgets (`20/50`, `240/4000/24000`), selected-only canonical rule, conversation copy, bottom fallback actions, no-live boundary, and future Mac requirement (five memory types plus multiple expanded originals).

- [ ] **Step 2: Run final focused backend checks.**

Run: `python3 -m pytest -q tests/test_owner_memory_detail_contract.py tests/test_owner_memory_card_projector.py tests/test_owner_memory_card_api.py tests/test_memory_inspector_api.py tests/test_memory_inspector_facade.py tests/test_source_service.py tests/test_owner_memory_corrections.py tests/test_project_memory_api.py --tb=short`

Expected: PASS with no detail contract skipped.

- [ ] **Step 3: Run final Desktop and governance checks.**

Run: `cd desktop/lingji-control && npm run test:e2e:memory && npm run test:owner-ui-menu-fast-track && npm run test:smoke && npm run build`
Run: `python3 -m compileall -q src tests`
Run: `git diff --check`
Run: `python3 scripts/check_acceptance_sync.py`  
Run: `python3 scripts/check_local_execution_handoff.py`

Expected: all commands PASS; no live/installation/owner-data test is run in this task.

- [ ] **Step 4: Write the focused implementation report.** Record exact branch/commit, 4 task results, test outputs, no-live boundary, known limitations, and the next Mac acceptance gate without claiming owner PASS.

- [ ] **Step 5: Commit Task 4 docs/report.**

```bash
git add docs/PROJECT_STATUS.md docs/MODULES/CODE_MAP.md docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md docs/TEST_REPORTS/OWNER_MEMORY_DETAIL_DRILLDOWN_IMPLEMENTATION.md
git commit -m "docs: close owner memory detail implementation"
```

- [ ] **Step 6: Stop at the focused boundary.** Do not build/install/start live services or create a Mac acceptance task here. The parent agent creates a new Mac task only after a new product SHA passes full/release.

## Self-review

- Four ordinary destinations/current-only list: Tasks 2–3.
- Canonical body without card DTO mixing: Tasks 1–2.
- Unique bounded evidence route and authority/privacy: Task 1.
- Conversation-only fallback and existing messages pagination: Tasks 2–3.
- Default-visible detail sections, folded IDs, bottom fallback actions, no delete: Task 2.
- Pagination, truncation, unknown/error/409, 1024/1280 and five memory types: Task 3.
- Focused-only implementation and future Mac acceptance boundary: Task 4.
