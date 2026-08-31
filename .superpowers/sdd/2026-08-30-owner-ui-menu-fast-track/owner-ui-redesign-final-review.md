# Owner UI Redesign Final Review

Date: 2026-08-31
Scope: Repair Round 1 independent read-only re-review for `/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards`

Spec Compliance: PASS
Quality: APPROVED
Critical/Important/Minor: 0 / 0 / 0
Mac candidate: 可以放行

## Findings Disposition

- 之前的分页 Critical 已关闭。`OwnerMemoryCardsPage` 现在把“初始加载”和“20 秒自动刷新”拆开，并用 `offsetRef` 保持当前页，避免翻页后被 `load(0)` 拉回首页。[OwnerMemoryCardsPage.tsx](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/desktop/lingji-control/src/pages/OwnerMemoryCardsPage.tsx:42) [OwnerMemoryCardsPage.tsx](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/desktop/lingji-control/src/pages/OwnerMemoryCardsPage.tsx:47) [OwnerMemoryCardsPage.tsx](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/desktop/lingji-control/src/pages/OwnerMemoryCardsPage.tsx:67) E2E 现在也真实覆盖了“>20 current + 翻到第二页 + 20.5 秒 refresh 后仍留在第二页”。[e2e_owner_memory_flow.mjs](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/desktop/lingji-control/tests/e2e_owner_memory_flow.mjs:770) [e2e_owner_memory_flow.mjs](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/desktop/lingji-control/tests/e2e_owner_memory_flow.mjs:777)

- 之前“测试绕开分页”的 Critical 也关闭了。fixture 现在生成 45 条混合数据，其中 36 条是 `current`，并明确断言普通流第一页 20 条、第二页 16 条、非 current 条目不出现。[e2e_owner_memory_flow.mjs](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/desktop/lingji-control/tests/e2e_owner_memory_flow.mjs:197) [e2e_owner_memory_flow.mjs](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/desktop/lingji-control/tests/e2e_owner_memory_flow.mjs:201) [e2e_owner_memory_flow.mjs](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/desktop/lingji-control/tests/e2e_owner_memory_flow.mjs:755) [e2e_owner_memory_flow.mjs](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/desktop/lingji-control/tests/e2e_owner_memory_flow.mjs:773)

- 首页汇总口径问题已关闭到可接受状态。后端 `summary()` 的 `cards` 已改为 current-only；首页文案也明确区分“当前记忆/长期记忆只统计 current”和“对话/消息显示已导入总规模”。[owner_memory_cards.py](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/src/gateway/owner_memory_cards.py:149) [OverviewPage.tsx](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/desktop/lingji-control/src/pages/OverviewPage.tsx:42) E2E 对 `36` 的 current total 和解释文案都做了断言。[e2e_owner_memory_flow.mjs](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/desktop/lingji-control/tests/e2e_owner_memory_flow.mjs:414) [e2e_owner_memory_flow.mjs](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/desktop/lingji-control/tests/e2e_owner_memory_flow.mjs:421)

- `<=760px` 导航可访问性问题已关闭。按钮新增 `aria-label`，即使 `.desktop-nav-copy` 在窄屏隐藏，主导航仍保留可访问名称。[DesktopShell.tsx](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/desktop/lingji-control/src/components/DesktopShell.tsx:84) [styles.css](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/desktop/lingji-control/src/styles.css:478) smoke 和 e2e 都检查了四个精确标签。[owner-ui-menu-fast-track-smoke.mjs](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/desktop/lingji-control/scripts/owner-ui-menu-fast-track-smoke.mjs:142) [e2e_owner_memory_flow.mjs](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/desktop/lingji-control/tests/e2e_owner_memory_flow.mjs:731)

- Attention 的文案也达到本轮可接受标准。说明文案已经明确“灵机暂时不会替你做这个决定；处理后会继续自动整理”，按钮从泛化的“完成处理”改成了“我已确认，继续处理”。[AttentionPage.tsx](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/desktop/lingji-control/src/pages/AttentionPage.tsx:22) [AttentionPage.tsx](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/desktop/lingji-control/src/pages/AttentionPage.tsx:29)

- 没有发现新的 Critical/Important。并发和错误态方面，`requestId` 仍防止旧请求覆盖新页，待办/来源读取失败时也继续保留“正在确认/自动重试”的显式状态，不会伪装成空结果。[OwnerMemoryCardsPage.tsx](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/desktop/lingji-control/src/pages/OwnerMemoryCardsPage.tsx:50) [OwnerMemoryCardsPage.tsx](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/desktop/lingji-control/src/pages/OwnerMemoryCardsPage.tsx:54) [OverviewPage.tsx](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/desktop/lingji-control/src/pages/OverviewPage.tsx:39) [AttentionPage.tsx](/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-real-history-memory-cards/desktop/lingji-control/src/pages/AttentionPage.tsx:24)

## Verification

- `npm run test:owner-ui-menu-fast-track` PASS
- `npm run test:e2e:memory` PASS

## Release Decision

Mac candidate: 可以放行
