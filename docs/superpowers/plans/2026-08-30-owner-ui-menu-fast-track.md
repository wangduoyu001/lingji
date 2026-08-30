# Owner UI / Menu Fast-Track Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 先把灵机的普通界面和菜单做成主人一眼能懂、可以实际操作的 Mac 体验版，并完成真实应用逐页验收；质量/向量深层门禁延期，不再阻塞本轮 UI 体验。

**Architecture:** 复用现有认证 8766 API、Owner Memory Cards、来源和 Work Fact 事实链，不新增后端或数据模型。Desktop 只做信息架构、中文文案、可读层级和已有动作接线；技术诊断留在折叠高级入口。完成自动化 UI 证据后，从同一产品 SHA 构建本地 arm64 应用，在隔离 Acceptance 数据上由根代理实际点击并留给主人确认。

**Tech Stack:** React/TypeScript、现有 Tauri Desktop、现有 Playwright rendered fixture、现有 Python Local Control API、macOS arm64。

## Global Constraints

- 只做 UI、菜单、既有事实展示和已有动作接线；不开发新的记忆能力、来源、数据库、队列、检索、模型或云服务。
- 普通菜单固定为：首页、记忆内容、需要我、记忆来源；高级诊断不得与普通菜单并列抢占注意力。
- 普通页面不得显示 JSON、内部 ID、commit、端口、provider、collection、token、原始异常或技术状态码；这些只能在折叠高级详情。
- 首页只回答：灵机是否正常、记住了多少/来自哪里、最近做了什么、现在是否需要主人处理、下一步是什么。
- 记忆内容每张卡只回答：这件事是什么、发展/讨论结果、当前结论、是否过时、来源、原始/结构化/向量/永久状态、是否需要主人修正或删除。
- “来源”必须显示发现/授权/接管/扫描数量的真实口径，不得把检测到软件冒充已经接管；没有可执行下一步时不得显示假按钮。
- “需要我”只显示真实待办；没有待办时明确表示灵机继续自动工作，不制造焦虑。
- 所有数字、状态和动作继续来自同一认证 API；缺失显示“尚未获得”，不得补 0 或假成功。
- Luna 负责全部代码与修复；根代理只维护计划、调度、独立验收和主人交接。
- 100 问/4R2、100k、Windows、正式 release merge gate 均延期并如实标记，不得伪装通过。
- 本轮 Mac 应用只可称为 `OWNER_UI_EXPERIENCE_CANDIDATE`，不得称 Phase 1 正式发布完成。

---

### Task 1: Four-menu owner UI closure

**Files:**
- Modify: `desktop/lingji-control/src/navigation.ts`
- Modify: `desktop/lingji-control/src/components/DesktopShell.tsx` only if required for a collapsed advanced entry
- Modify: `desktop/lingji-control/src/pages/OverviewPage.tsx`
- Modify: `desktop/lingji-control/src/pages/OwnerMemoryCardsPage.tsx`
- Modify: `desktop/lingji-control/src/pages/AttentionPage.tsx`
- Modify: `desktop/lingji-control/src/pages/MemorySourcesPage.tsx`
- Modify: existing page CSS in `desktop/lingji-control/src/styles.css` or the current page style owner only
- Modify: `desktop/lingji-control/tests/e2e_owner_memory_flow.mjs`
- Create: `desktop/lingji-control/scripts/owner-ui-menu-fast-track-smoke.mjs`
- Modify: `desktop/lingji-control/package.json`
- Modify: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Modify: `docs/MODULES/CODE_MAP.md`
- Report: `.superpowers/sdd/2026-08-30-owner-ui-menu-fast-track/task-1-report.md`

**Interfaces:**
- Consumes: existing owner-card, source snapshot, pending action and Work Fact APIs/DTOs.
- Produces: exactly four ordinary navigation destinations plus one visually secondary advanced disclosure; no new API.

- [ ] **Step 1: Capture RED for the owner's wording and menu contract**
  Extend the rendered fixture and a focused DOM smoke so the old UI fails unless all four ordinary menu labels, the collapsed advanced entry, clear Home next step, complete memory-card fields, source truth counts and zero-attention copy are present. Assert technical strings/JSON/internal IDs are absent from ordinary views.

- [ ] **Step 2: Run RED**
  Run `npm run test:e2e:memory` and the new focused smoke; record exact missing/misleading assertions before production changes.

- [ ] **Step 3: Implement the minimum UI closure**
  Reorder and relabel existing routes without creating pages. Use a compact visual hierarchy: one clear status sentence, small factual counts, one next-step panel, and readable memory cards. Keep technical details inside existing or new `<details>` disclosure. Preserve keyboard/focus/aria and existing correct/invalidate/archive/authorize/scan actions.

- [ ] **Step 4: Verify all owner states**
  Cover zero data, imported memories, current/superseded/stale/conflict, raw-only, vector unavailable, permanent/pending, revoked/unsupported source, scan running/completed/failed, real pending action and zero pending action. At 1024 and 1280 widths there must be no horizontal overflow or clipped actions.

- [ ] **Step 5: Run GREEN and regression**
  Run `npm run test:e2e:memory`, the new focused smoke, `npm run test:smoke`, `npm run build`, the existing owner-card/source Python focused matrix, compileall, diff-check, acceptance sync and local handoff.

- [ ] **Step 6: Commit and review**
  Commit product/tests as `fix: clarify owner memory menus` and docs/evidence separately. A fresh Luna must return Spec Compliance PASS and Task Quality APPROVED before Task 2.

### Task 2: Mac owner UI experience candidate

**Files:**
- Modify: `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`
- Modify: `docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md`
- Modify: `docs/PROJECT_STATUS.md`
- Modify: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Report: `.superpowers/sdd/2026-08-30-owner-ui-menu-fast-track/task-2-report.md`

**Interfaces:**
- Consumes: Task 1 reviewed exact product SHA and existing macOS Tauri build/sidecar process.
- Produces: one local arm64 signed application installed with backup, isolated Acceptance DataRoot, authenticated sidecar, full visible-control traversal, screenshots/observations and an app left open for owner confirmation.

- [ ] **Step 1: Activate one bounded local task**
  Set a new unique task ID with mode `MACOS_OWNER_UI_EXPERIENCE_ONLY`, exact product SHA, physical isolation roots, backup/rollback and explicit `NOT_A_RELEASE_GATE` wording. Do not reuse a rejected Artifact.

- [ ] **Step 2: Build and inspect exact-SHA application**
  Run Desktop build/tests already accepted in Task 1, build the Tauri arm64 bundle from the exact SHA, verify architecture and strict codesign, back up the installed app and replace the whole bundle. Do not delete owner data or old backup.

- [ ] **Step 3: Launch isolated candidate**
  Configure a temporary Acceptance DataRoot/Vault/source fixture that contains multiple readable memories covering current, superseded, stale, conflict, raw/vector/permanent states and at least one real pending action. Start the app and authenticated 8766 sidecar; prove Production/Vault pollution 0.

- [ ] **Step 4: Root-agent full UI traversal**
  The root agent, using Computer Use, must visit every ordinary menu and the advanced disclosure, click every visible enabled control, verify resulting API/data/process state, check 1024-equivalent and normal window sizes, reopen via menu/shortcut/Dock where available, and record only owner-facing results.

- [ ] **Step 5: Leave app open for owner**
  Do not close the UI or clean the Acceptance fixture. Report what the owner should look at in plain Chinese and wait for explicit owner PASS/FAIL. No Phase 1/release/merge claim is allowed before that confirmation and the deferred quality gate.

## Acceptance decision

- UI candidate passes only if the owner can explain, without technical help: what LingJi remembered, how it developed, the current conclusion, whether it is outdated, where it came from, whether it is raw/vector/permanent, and whether to correct/delete it.
- If the owner finds a UI or menu problem, create one bounded UI repair from the observed screen; do not reopen 4R2/100-question work in that repair.
- Deferred technical quality remains explicitly `MEASURED_FAIL / NOT_RELEASE_READY` until separately resumed.
