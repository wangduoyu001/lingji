# Owner Real History and Memory Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让灵机在 Mac 上先安全发现并接管主人已有的 Codex 会话，再把已导入证据投影为简洁、可追溯、可判断时效与处理动作的中文记忆卡片。

**Architecture:** 继续使用现有 `SourceRegistry → snapshot/checkpoint → extraction queue → SourceReadModel/MemoryDatabase → Qdrant → authenticated 8766 → Desktop` 主线。新增内容只包括一个受限的 macOS Codex rollout 候选发现/适配器，以及现有 Memory Inspector 上方的 owner-facing card projector；不新增数据库、索引器、队列、端口、永久事实源或第二套 UI。原始会话始终是证据，Core/永久记忆仍只由 Obsidian Vault + Git 承担。

**Tech Stack:** Python 3.11、FastAPI、SQLite/FTS、现有 Qdrant seam、React/TypeScript/Tauri、pytest、Playwright。

## Global Constraints

- 根代理只负责规划、调度和独立验收；功能代码、测试和修复全部由 `gpt-5.6-luna` 子代理完成。
- 所有产品行为必须先有真实 RED，再写最小 GREEN；不得删除测试、改成 skip、降低断言或把未执行写成通过。
- 不读取、复制或索引 `auth.json`、Token、Cookie、浏览器存储、客户端 SQLite/LevelDB、Claude 内部数据库、Codex 配置或任何未授权路径。
- 未授权前只允许读取候选目录和文件的名称、扩展名、大小、mtime、文件标识；不得读取聊天正文。
- Codex 只读取 `~/.codex/sessions/**/*.jsonl` 和 `~/.codex/archived_sessions/*.jsonl` 中经格式探测支持的 rollout；禁止读取整个 `~/.codex`。
- Codex rollout 解析只接收 `session_meta`、明确的 user/assistant message 记录和必要时间/身份字段；忽略 reasoning、tool call/output、world state、base instructions、权限、配置、模型密文与其他内部事件。
- ChatGPT 继续只接收官方导出 ZIP/JSON；官方流程仍需要主人操作一次。官方依据：[OpenAI 数据导出说明](https://help.openai.com/en/articles/7260999-how-do-i-export-my-chatgpthistory-and-data)。
- Claude 无受支持官方导出时保持 `暂不支持`，不得读取其内部存储；没有真实动作时不得渲染“下一步”或假按钮。
- 候选发现不等于授权，授权不等于导入，导入不等于向量化，向量化不等于永久记忆；API 和 UI 必须分别显示真实状态，未知为 `null/unknown/尚未获得`。
- 普通 UI 不展示聊天流水账、内部 ID、JSON、hash、路径或 chunk；记忆卡只展示主题、2–3 条过程/结论、时效、来源、四层状态和主人动作，原始正文按需展开。
- “删除”在普通 UI 中实现为 `标记失效` 或 `归档/移出当前记忆`；不得物理删除原始聊天、source/conversation/message、审计事件或历史版本。
- Core、身份、高风险、冲突和低置信内容必须主人确认；自动提取不能静默改写 Core Memory。
- Mac 首先完成；Windows 只保持现有语义不回退，本计划不实现 Windows 默认路径。
- 所有开发与自动测试使用合成 fixture/临时目录；真实主人会话只在新的 ACTIVE 本机任务和主人已授权范围内读取。

---

### Task 1: Safe Mac Codex Discovery and Rollout Import

**Files:**
- Modify: `src/automatic_memory/discovery.py`
- Modify: `src/automatic_memory/path_policy.py`
- Modify: `src/automatic_memory/models.py`
- Modify: `src/extraction/adapters/codex.py`
- Modify: `src/extraction/adapters/__init__.py`
- Modify: `src/extraction/registry.py`
- Modify: `src/control/automatic_memory_api.py`
- Modify: `desktop/lingji-control/src/pages/memorySourcesTypes.ts`
- Modify: `desktop/lingji-control/src/pages/memorySourcesApi.ts`
- Modify: `desktop/lingji-control/src/pages/MemorySourcesPage.tsx`
- Test: `tests/test_owner_real_history_discovery.py`
- Test: `tests/test_owner_codex_rollout_adapter.py`
- Test: `tests/test_owner_real_history_import_flow.py`
- Test: `desktop/lingji-control/tests/e2e_owner_memory_flow.mjs`

**Interfaces:**
- Produces: `DiscoveredSource` metadata evidence with nullable `file_count`, `byte_count`, `earliest_mtime`, `latest_mtime`, `format`, and structured owner action.
- Produces: an adapter name `codex_rollout` for source kind `codex_rollout`, emitting the existing `NormalizedSource`, `NormalizedConversation`, and `NormalizedMessage` contracts.
- Consumes: existing authorization, snapshot, checkpoint, queue, structured sink, Work Fact and scan APIs; no second task system.

- [ ] **Step 1: Add RED metadata-discovery tests**

  Use synthetic macOS homes containing `sessions/YYYY/MM/DD/rollout-*.jsonl`, `archived_sessions/rollout-*.jsonl`, auth/config/SQLite decoys and symlink escapes. Assert that discovery returns two Codex candidates with exact file/byte/time evidence, reads no file bodies before authorization, never traverses outside the two roots, and does not return private client stores.

- [ ] **Step 2: Run the discovery tests and record the expected failure**

  Run: `./.venv/bin/pytest -q tests/test_owner_real_history_discovery.py --tb=short`

  Expected RED: current discovery returns no default Codex candidates and has no inventory fields.

- [ ] **Step 3: Implement bounded metadata-only candidates**

  Extend the existing discovery model without changing authorization. On Darwin only, resolve the two exact roots under the supplied/effective home, enumerate `.jsonl` metadata with bounded count/depth, reject symlinks and sensitive names, and return nullable measured fields. On other platforms keep the current configured-path behavior.

- [ ] **Step 4: Add RED rollout parser tests**

  Fixtures must contain `session_meta`, `turn_context`, `event_msg`, `response_item`, tool calls/outputs, reasoning, world state, duplicate user/assistant representations, malformed lines, an oversized line and mid-write truncation. Hand-derived expectations must prove stable session identity, correct role/order/time, no tool/reasoning ingestion, idempotent replay and fail-closed unknown format.

- [ ] **Step 5: Run the parser tests and record the expected failure**

  Run: `./.venv/bin/pytest -q tests/test_owner_codex_rollout_adapter.py --tb=short`

  Expected RED: current `codex_transcript` adapter rejects the rollout shape.

- [ ] **Step 6: Implement a streaming, fail-closed rollout adapter**

  Parse line-by-line with a bounded record size. Use `session_meta.payload.id/session_id` as conversation identity; accept only explicit user/assistant message variants; normalize duplicate event/response copies by stable item ID or content/time/role identity; preserve content hash and source/conversation/message external identities. Do not emit tool, reasoning, encrypted or configuration records.

- [ ] **Step 7: Add RED end-to-end import tests**

  Authorize a synthetic candidate through the authenticated automatic-memory flow, scan twice, crash/restart once, and assert exact source/conversation/message counts, zero duplicates, stable Work Fact, content-addressed raw snapshot, third-party sentinel unchanged and revoked source excluded from current retrieval.

- [ ] **Step 8: Run the flow tests and implement the minimal registry/API wiring**

  Run: `./.venv/bin/pytest -q tests/test_owner_real_history_import_flow.py --tb=short`

  Then register the adapter and reuse the existing snapshot/queue/structured sink. No direct adapter call from the API or Desktop is allowed.

- [ ] **Step 9: Fix owner actions and visible evidence**

  The Codex card must show `发现 N 个本机对话文件` before authorization, then a real `允许接管 Codex` action. ChatGPT must always expose a `选择官方导出目录` action. Claude without a safe export must show `暂不支持 · 目前没有可执行操作`, without a `下一步` heading or disabled/fake button.

- [ ] **Step 10: Verify Task 1 and commit**

  Run the three focused pytest files, automatic-memory discovery/flow regressions, rendered owner E2E, 23 Desktop smoke scripts, build, compileall, diff-check, acceptance-sync and local-handoff checks. Commit product/tests separately from docs/evidence.

---

### Task 2: Owner Memory Card Projection

**Files:**
- Create: `src/gateway/owner_memory_cards.py`
- Modify: `src/gateway/memory_inspector.py`
- Modify: `src/control/memory_inspector.py`
- Modify: `src/control/api.py`
- Test: `tests/test_owner_memory_card_projector.py`
- Test: `tests/test_owner_memory_card_api.py`

**Interfaces:**
- Consumes: existing `MemoryDatabase`, `SourceReadModel/SourceQueryService`, optional read-only StateDB promotion events, per-memory vector inspection and shared temporal predicates.
- Produces: `GET /api/memory/inspector/cards` and `GET /api/memory/inspector/cards/{memory_id}` on authenticated 8766.
- Produces: `OwnerMemoryCard` as a projection only; it owns no table and persists no new truth.

- [ ] **Step 1: Add RED card projector tests**

  Build literal fixtures for active, candidate, core, derived evidence, superseded, invalidated, archived, source revoked, missing timestamps, low confidence, provenance mismatch, authority conflict, vector complete/partial/unavailable and no-vector-provider. Assert each field is derived from the existing authorities and unknown values remain unknown.

- [ ] **Step 2: Run projector RED**

  Run: `./.venv/bin/pytest -q tests/test_owner_memory_card_projector.py --tb=short`

  Expected RED: no unified card projection exists.

- [ ] **Step 3: Implement the owner card DTO/projector**

  Each card must include stable IDs; `topic`; at most three evidence-backed development/result lines; latest conclusion only when evidence exists; freshness state/reason/replacement; source label, counts and latest evidence time; `raw/structured/vector/permanent` states; confidence/conflict/provenance; and one owner action recommendation. Do not synthesize unsupported conclusions in the UI. For raw conversations without a promoted memory, create a read-only conversation evidence card marked `尚未加入永久记忆`, using a deterministic topic and bounded message previews.

- [ ] **Step 4: Add RED API/permission/pagination tests**

  Assert authenticated owner scope, `limit 1..50`, stable offset pagination, exact total/has_more, filters for state/action/source, default collapsed evidence, bounded expanded previews, restricted visibility, safe references and no raw full text in list responses.

- [ ] **Step 5: Run API RED and register the minimal routes**

  Run: `./.venv/bin/pytest -q tests/test_owner_memory_card_api.py --tb=short`

  Add only the two routes to the existing Memory Inspector API. Reuse the existing message detail route for full original text.

- [ ] **Step 6: Verify Task 2 and commit**

  Run both focused files plus existing Inspector, temporal current/as_of/history/why, promotion provenance, vector-unavailable and permissions regressions; then compileall, diff-check, acceptance-sync and local-handoff. Commit product/tests separately from docs/evidence.

---

### Task 3: Concise Memory Cards and Safe Owner Corrections

**Files:**
- Create: `desktop/lingji-control/src/pages/OwnerMemoryCardsPage.tsx`
- Create: `desktop/lingji-control/src/pages/ownerMemoryCardsApi.ts`
- Create: `desktop/lingji-control/src/pages/ownerMemoryCardsTypes.ts`
- Modify: `desktop/lingji-control/src/AppPages.tsx`
- Modify: `desktop/lingji-control/src/DesktopShell.tsx`
- Modify: `desktop/lingji-control/src/types.ts`
- Modify: `desktop/lingji-control/src/navigation.ts`
- Modify: `desktop/lingji-control/src/pages/OverviewPage.tsx`
- Modify: `desktop/lingji-control/src/pages/MemoryReviewPage.tsx`
- Modify: `src/control/project_memory_api.py`
- Modify: `src/project_memory/review_service.py`
- Modify: `src/memory/lifecycle.py`
- Test: `tests/test_owner_memory_corrections.py`
- Test: `desktop/lingji-control/tests/e2e_owner_memory_flow.mjs`
- Test: relevant Desktop smoke scripts

**Interfaces:**
- Consumes: Task 2 cards API and existing message-detail/approve/edit-approve/reject/archive APIs.
- Produces: owner navigation with exactly four ordinary entries in this order: `首页 / 记忆内容 / 需要我 / 记忆来源`; Activity becomes a Home summary and existing Inspector/Review/Vector/Workspace pages remain reachable only from one low-emphasis `高级诊断` entry.
- Produces: one normal page `记忆内容`, not a new backend, fact source, design system or second diagnostics UI.
- Produces: owner-confirmed `correct`, `invalidate`, and `archive` transitions using existing version/lifecycle semantics; never physical deletion.

- [ ] **Step 1: Add rendered RED for the owner memory page**

  Use at least 12 cards across two pages. Assert the first screen shows exact total, displayed count, source distribution and multiple concise cards; each card contains topic, no more than three process/result lines, current/overdue label, source, four layer chips, trust state and a plain action recommendation. Assert raw IDs/JSON/path/chunks are absent until technical details.

- [ ] **Step 2: Run rendered RED**

  Run: `cd desktop/lingji-control && npm run test:e2e:memory`

  Expected RED: no ordinary memory-card page exists.

- [ ] **Step 3: Implement the concise page and navigation**

  Add `记忆内容` to ordinary navigation and reduce the ordinary menu to the four entries above; do not delete old `PageId` routes. Default list limit is 20; show `已显示 X / 共 Y 条` and working next/previous controls. At 1280px use a calm two-column card grid and at 1024px collapse to one column without horizontal overflow. Reuse existing `DesktopUX.css`, `LocalMemoryLoop.css`, panels, pills, focus rings and detail drawer; do not introduce a new visual system. Card detail shows evidence-backed summary and source links; `查看来源` fetches only the selected message detail. Technical fields remain folded. Every state and action must remain understandable without color alone, keyboard reachable, and at least 40px clickable.

- [ ] **Step 4: Add RED lifecycle action tests**

  Assert candidate confirm/edit/reject, Core correction creating a new active version and superseding the old, invalidation with reason/valid_to, archive semantics, stale expected hash returning 409, and all raw/source/message/audit evidence remaining readable.

- [ ] **Step 5: Run lifecycle RED and implement safe transitions**

  Run: `./.venv/bin/pytest -q tests/test_owner_memory_corrections.py --tb=short`

  Add no `DELETE` route. UI labels must be `修正内容`, `标记已经过时`, and `移出当前记忆`; each requires confirmation and shows the resulting current/history state after a fresh API read.

- [ ] **Step 6: Connect Home proof without duplication**

  Home shows only: discovered candidate count, imported conversation/message count, memory card total, permanent count, vectorized count and owner-review count, each from the same card/source APIs. Missing counts render `尚未获得`, never fake zero. Show at most three recent real Work Facts as `最近工作` and label them as work records, not memories. A single primary button opens `记忆内容`; Home never copies full card bodies, raw paths, IDs, JSON, chunks, vector collection or model details.

- [ ] **Step 7: Verify Task 3 and commit**

  Run lifecycle tests, rendered E2E, all 23 Desktop smoke scripts, build, Inspector/Review/API regressions, compileall, diff-check, acceptance-sync and local-handoff. Rendered E2E must use at least 12 distinct cards and also prove two-page navigation, exact totals, the four ordinary menu entries, one advanced entry, current/pending/superseded/stale/revoked/conflict/no-vector/not-permanent states, no default raw ID/path/hash/JSON/chunk leakage, working source drill-down, owner actions with fresh re-read, 409 preservation, keyboard/focus behavior and 1024/1280 no-overflow layouts. Every visible button must perform a real navigation or API action. Commit product/tests separately from docs/evidence.

---

### Task 4: Mac Owner Data Proof and Experience Acceptance

**Files:**
- Modify before execution: `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`
- Modify after execution: `docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md`
- Modify: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Modify: `docs/PROJECT_STATUS.md`
- Modify: `docs/MODULES/CODE_MAP.md`
- Create: one report under `docs/TEST_REPORTS/` using `REPORT_TEMPLATE.md`

**Interfaces:**
- Consumes: exact reviewed Task 1–3 product HEAD and its same-SHA Mac arm64 Artifact.
- Produces: a real owner-observable result; it does not declare Phase 1 complete unless every gate below passes.

- [ ] **Step 1: Complete broad review and release gates**

  Generate a whole-plan review package and obtain an independent review with zero Critical/Important findings. Run `release` once on the final tree, not `full` followed by release; re-read the compact validation summary.

- [ ] **Step 2: Activate a new bounded Mac task**

  The task must name the exact product commit/artifact/hash, owner data root, rollback, Production/Vault exclusions and authorized sources. Stop and replace the currently running Acceptance candidate by exact PID only; preserve its backup until the new owner run is accepted or rolled back.

- [ ] **Step 3: Verify metadata discovery before reading content**

  On the real machine, the UI must show the exact measured Codex candidate count and time range before authorization, while sentinels prove zero reads/writes outside the two rollout roots and zero third-party mutation.

- [ ] **Step 4: Perform the one-time owner authorization and import**

  Use the visible `允许接管 Codex` action. Verify background progress, restart at measured 30% and 70%, exact final source/conversation/message counts, zero duplicate identities, no Codex/Claude/ChatGPT process or file mutation, and responsive Desktop.

- [ ] **Step 5: Traverse every visible page and action**

  The root agent uses the real installed UI. Verify source evidence, memory-card totals/pagination, multiple old topics, freshness, source drill-down, vector/permanent truth, confirm/correct/invalidate/archive in an isolated owner fixture, and no fake `下一步`. Keep the UI open.

- [ ] **Step 6: Ask only for owner content/experience confirmation**

  The owner must be able to answer from the UI: how many records were found/imported, which sources, what several remembered matters say, whether each is current, where it came from, whether it is vectorized/permanent and whether action is required. Root must not claim owner PASS on the owner's behalf.

- [ ] **Step 7: Close report, remote receipts and cleanup**

  Follow the current acceptance authority: commit the report on an acceptance branch, push, re-read remote branch/commit/report/result, clean only task-owned temporary data after remote confirmation, push the cleanup receipt and re-read again. Leave accepted app open until the owner confirms.

## Final Product Acceptance

- Before authorization, the real Mac shows exactly `340` current+archived Codex rollout candidates on the 2026-08-29 host baseline, with measured bytes/time range; if the filesystem changes, the displayed total must equal a fresh metadata sentinel rather than the frozen number.
- After authorization/import, imported conversation and message totals exactly match SourceReadModel pagination totals; duplicate source/conversation/message identities are all zero after a repeated scan and restart.
- The normal page shows at least 10 distinct, content-bearing memory cards when the imported corpus contains at least 10 eligible conversations, with exact total and pagination. It does not present scan Work Facts as memories.
- Every card truthfully distinguishes raw evidence, structured record, vector status and permanent memory. `unknown/degraded/missing` is never shown as success.
- Superseded/invalidated/archived content never appears as current; source, replacement and reason remain available in history/why.
- Original evidence remains unchanged and available after correction/invalidation/archive. No owner-facing physical delete exists for raw AI history.
- Claude shows no fake next step; ChatGPT shows a real official-export selection path and the official export remains the only old-history route.
- Third-party source content, mtime, permissions and configuration differences are zero apart from natural app writes; auth/token/cookie/private DB reads are zero.
- The final owner report remains `FAIL/BLOCKED` until the owner explicitly confirms the installed UI demonstrates real memory work.
