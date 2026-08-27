# Task 5B 独立终审：Desktop Owner Workflow UI

日期：2026-08-28
审查基线：`0bdcc93`
被审产品 HEAD：`674766a3eb4f69cfdca12c072db6a3400f852530`
范围：`0bdcc93..HEAD` 的 Task 5B Desktop/DTO、Task 5A 接线、相关验收与回归证据。
审查方式：只读；未修改产品代码、测试或既有报告，未启动 live 8766、Sidecar、Artifact、Production/Vault 或主人数据。

## 结论

- Spec Compliance：**FAIL**
- Task Quality：**NEEDS_FIXES**
- 处置：**REPAIR_ROUND_1**
- Critical：0
- Important：2
- Minor：3

当前不能给出 `ACCEPT_FOR_TASK6`。最小修复仅限 Task 5B Desktop loading/错误反馈与证据契约校正；不得扩展后端/API、增加状态源、修改记忆/RAG/向量、启动真实 8766 或制作 Artifact。

## Findings

### I1 — Memory Review 初次读取和候选详情没有诚实 loading 反馈

严重级别：Important
位置：`desktop/lingji-control/src/pages/MemoryReviewPage.tsx:18-48,50-63`

`load()` 发起候选请求时没有设置或渲染 loading 状态。首次请求期间 `items` 仍为空，页面直接显示“没有待审核记忆”，把尚未完成的读取误报为空；点击候选后虽然设置了 `busy`，列表按钮没有“读取中…”或 disabled/详情占位反馈。刷新候选也只在已有 `busy` 时禁用，不能让主人确认请求仍在进行。

这违反 Task 5B 的“所有异步操作反馈”以及 loading/empty 必须诚实的要求。修复边界：仅在现有 `MemoryReviewPage` 增加候选列表与候选详情的 loading/refreshing 反馈；错误时保留已有数据并明确错误，不改变后端契约。

### I2 — provenance rendered 证据使用了实际后端不会返回的 mock-only 字段

严重级别：Important
位置：`desktop/lingji-control/tests/e2e_owner_memory_flow.mjs:66-67`；对照 `src/project_memory/review_service.py:136-150`

实际 `MemoryReviewService._read_candidate()` 的候选 payload 仅提供 `memory_id/title/content_preview/project_ids/proposed_by/memory_type/importance/confidence/created_at/source_refs/current_hash/relative_path/similar_core`（详情再加 `content`）。它不提供 `source_name`、`source_session_id`、`source_message_id`、`conversation_title`、`message_excerpt`、`provenance_at`、`current_state`、`history_state`、`proposal_reason` 或 `affected_agents`。

但 rendered E2E 的假服务在候选列表和详情中注入了上述全部字段，并据此断言来源名、会话、片段、状态和 why 均可读。故该测试只能证明 UI 能显示一份非正式契约的假 payload，不能证明现有真实 API 接线；在真实服务下这些字段会全部落到“尚未获得”（时间仅回退到真实的 `created_at`），且现有 `source_refs` 没有被展示。该问题直接触及“DTO 与 backend payload 对齐”“不允许 mock-only 自证”和 provenance 关键行为证据。

修复边界：让 rendered fixture 严格复用现有候选 API payload，并分别断言真实可用字段与缺失字段的“尚未获得”；如要展示来源引用，只能复用现有 `source_refs`，不得顺手新增后端字段或 API。修复后须重新提供 provenance 的独立 rendered 证据。

## Minor findings

### M1 — 失败/处理中 Attention 分支只有源码覆盖，没有 rendered 证据

`AttentionPage` 有 `处理中…` 与失败 Notice，且成功后会刷新 pending projection；但 E2E 只返回立即成功的 resolve，没有延迟或失败响应，未独立证明失败时待办仍可见、错误不会伪装成功。

### M2 — 复制失败分支未被 rendered 验证

`CodexWorkspacePage` 已捕获 `navigator.clipboard.writeText` 失败并显示“复制失败”，但本轮 rendered E2E 没有注入失败 clipboard 或断言该文案。代码接线存在，证据覆盖不足。

### M3 — 900px rendered 检查未覆盖本轮受影响页面

E2E 最后在“高级诊断”页设置 900px 并检查 `scrollWidth`；没有在 Activity、Attention、Memory Review 或 Memory Inspector 页面检查。全局 CSS 的 `body min-width: 0` 与相应 media query 静态接线合理，但本轮关键页面没有完整 rendered 证据。

## 已独立验证通过

### 1. Activity / Work Fact

- `ActivityPage` 真实请求 `/api/work/history?limit=20&offset=${offset}`，使用后端 `items/limit/offset/total/has_more` 分页；上一页/下一页边界接线正确，5 秒轮询和手动刷新均存在。
- 主要卡片展示中文 phase/result/time/source/next actor，事件 JSON 仅在“查看技术详情（执行事件）”折叠区；未知字段使用“尚未获得”，连接中/首次加载/错误/过期/空列表均有相应显示。
- Task 5A `WorkProjector.history()` 返回的 `summary.phase/result/time/source/source_id/next_actor` 与前端 DTO 对齐；resolve 响应为 `action_id/work_id/resolved`，前端不虚构额外字段。

### 2. Attention / pending action

- `AttentionPage` 真实读取 `/api/work/pending-actions`，按钮调用编码后的 `/api/work/pending-actions/{action_id}/resolve`，成功后强制刷新同一 pending 投影；按钮有 `处理中…`、失败 Notice 和过期/刷新错误提示。
- Task 5A 独立终审确认 resolve 在同一 WorkStore 事实链内幂等、重启后收敛，且清除旧 owner next action 时保留更新的 system next action。

### 3. Memory Review / Inspector 接线

- Review/Inspector 的来源名、会话/片段、时间、当前/历史状态、why 在字段缺失时使用“尚未获得”；Inspector 的 source/message/memory links 通过现有 API 请求，点击会真实打开详情而非改本地假状态。
- Inspector 来源消息链接改为真实 `openMessage()` 请求，失败显示“详情读取失败，已保留当前可用数据”。
- Memory Review approve/edit/reject/create/archive 仍使用现有认证 API 与 owner confirmation/hash 保护；本轮没有发现静态死按钮。

### 4. 导航、Home 与隔离边界

- `NAVIGATION` 隐藏重复的 legacy `capture` 项，`PageId` 与 `AppPages` 仍保留 `capture` 兼容分支；Capture Center 是唯一可见手动投喂入口。仓库现有 SPA 没有独立 pathname router，本轮未改变既有内部 page-id 兼容行为。
- Task 4 Home 的五问、`本次更新`/`本次跳过`、缺失值“尚未获得”、来源与扫描动作保持；Task 4 source/runtime/inspector/observation smokes 均通过。
- 未见 Production/Vault、live runtime、Artifact 或主人数据访问。

## 自动化验证

以下命令均在产品 HEAD `674766a` 上独立执行：

```text
Task 5A focused:
40 passed, 2 warnings

Work/Task8/Capture/automatic-memory Work Fact regression:
102 passed, 2 warnings

Desktop:
npm ci --ignore-scripts       PASS（依赖安装；npm audit 报既有 1 moderate/1 high）
npm run build                 PASS
npm run test:work-fact        PASS
npm run test:memory-review    PASS
npm run test:e2e:memory       PASS（rendered fake-server flow）
npm run test:memory-sources   PASS
npm run test:memory-sources-repair PASS
npm run test:runtime          PASS
npm run test:inspector        PASS
npm exec -- tsx scripts/observation-first-ui-smoke.mjs PASS

Known existing baseline:
npm run test:codex-loop       FAIL: codex-workspace-smoke expects “当前项目” in CurrentWorkPanel
```

`test:codex-loop` 失败不是本轮回归：`desktop/lingji-control/src/components/CurrentWorkPanel.tsx` 与 `scripts/codex-workspace-smoke.mjs` 均未出现在 `0bdcc93..HEAD` diff，且同一未改动断言在基线代码中已存在。该失败按既有报告声明保留，未被掩盖、删除或改成 skip。

```text
./.venv/bin/python -m compileall -q src tests                 PASS
./.venv/bin/python scripts/check_acceptance_sync.py            PASS（product-impacting files 0）
./.venv/bin/python scripts/check_local_execution_handoff.py    PASS
git diff --check 0bdcc93..HEAD                                PASS
final product worktree before report                          CLEAN
```

## 缺失的真实验收（不作为本轮 PASS）

未启动 live 8766，未构建或安装 Sidecar/Artifact，未访问 Production/Vault/主人数据，未进行主人观察。 `LOCAL_EXECUTION_TASK.md` 为 `IDLE`，符合本轮禁止事项；这些项目不能被本报告推断为通过。

## 最小修复边界与复测

1. 仅为 Memory Review 增加真实列表/详情 loading 与刷新反馈，并补充加载期间不显示空态的 rendered 断言。
2. 将 E2E provenance fixture 收紧为 `MemoryReviewService` 现有 payload；补齐真实字段与缺失“尚未获得”的断言，不新增后端字段/API。
3. 复测 Task 5B build、work-fact/memory-review smokes、rendered E2E、40 个 Task 5A 测试、102 个 Work/Task8/Capture 回归，以及 acceptance sync/handoff/compileall/diff-check。

## 最终判定

```text
Product commit: 674766a3eb4f69cfdca12c072db6a3400f852530
Spec Compliance: FAIL
Task Quality: NEEDS_FIXES
Verdict: REPAIR_ROUND_1
Owner observation complete: NO
Live 8766 / Artifact: NOT_RUN
Critical findings: 0
Important findings: I1, I2
Minor findings: M1, M2, M3
Acceptance docs synchronized: YES（pre-existing Task 5B entry）
Temporary evidence cleaned: NOT_APPLICABLE（no live acceptance evidence created）
```
