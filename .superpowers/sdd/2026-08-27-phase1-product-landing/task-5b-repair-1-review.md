# Task 5B Repair Round 1 — Final Independent Review

日期：2026-08-28
审查代理：Luna（独立只读终审）
分支：`codex/phase1-automatic-memory`
产品当前 HEAD：`8136374`
Repair Round 1 产品提交：`98c0212`、`8e3b263`
证据/验收提交：`995aa0c`、`8136374`
初审报告提交：`9272e60`

## 范围与边界

本轮只复核初审 `9272e60` 的 Task 5B I1/I2、Task 4/5A 回归和初审 M1/M2/M3 的披露。已读取 `AGENTS.md`、`docs/PROJECT_STATUS.md`、`docs/MODULES/CODE_MAP.md`、`docs/ACCEPTANCE/README.md`、`LOCAL_EXECUTION_TASK.md`、`LOCAL_EXECUTION_RESULT.md`、`CODEX_ACCEPTANCE_INSTRUCTIONS.md`、`CHANGE_ACCEPTANCE_LOG.md`、初审报告、最新 Task 5B 报告及直接受影响源代码/测试。

只允许写入本报告；未修改产品代码、测试、任务单或既有报告，未启动 live `8766/8767`、Sidecar、Artifact，未访问 Production/Vault、真实主人数据或外部云服务。`LOCAL_EXECUTION_TASK.md` 保持 `IDLE`。测试产生的精确 E2E/Vite 进程已按 PID 清理，8766/8767/4178 无残留监听。

## 结论

- Spec Compliance：**PASS**
- Task Quality：**PASS**
- 处置：**ACCEPT_FOR_TASK6**
- Critical：0
- Important：0
- Minor：3（沿用初审 M1/M2/M3，均为非阻塞证据覆盖不足）

初审两个 Important 均关闭；没有把 Important 降级为 Minor，也没有新增 Critical/Important。Task 5B 可进入 Task 6 组合审查，但本报告不代表真实 8766、发布版、Artifact、Production/Vault 或主人验收通过。

## 初审 Important 复核

### I1 — Memory Review 的 loading、错误/空态和选择竞态：PASS

直接复核 `desktop/lingji-control/src/pages/MemoryReviewPage.tsx`：

- 初次候选列表和刷新均设置 `listLoading`；在无旧数据且请求未完成时只显示“正在读取候选记忆…”，不会显示“没有待审核记忆”或“尚未获得”。有旧列表时保留旧数据，并将刷新按钮显示为“刷新中…”。
- 列表失败设置独立的 `listError`；无旧数据时显示“候选记忆读取失败，请重试。”，成功空列表才进入 `Empty`。有旧数据的刷新失败保留旧列表并显示错误 Notice，不伪装为空。
- 候选详情在请求开始时设置 `detailLoading`，右侧显示“正在读取候选详情…”，不会在详情 pending 时展示旧详情或空态。
- 列表使用 `AbortController` 加 `requestId`，详情使用独立的 `detailAbortRef` 加 `detailRequestId`。新选择会取消旧详情请求；即使迟到响应返回，也只有当前 request id 能写入 `selected`、编辑内容和完整性状态。组件卸载会取消详情请求。
- 取消错误不会污染错误提示；真实 `ApiError` 仍分别进入列表/详情错误路径。

`npm run test:memory-review` 的 smoke 重新检查了 loading 文案、独立 `listError`、AbortController 和 request-id 保护。rendered flow 实际走过候选列表延迟 loading、详情延迟 loading、`mem-1`/`mem-2` 连续选择以及旧详情迟到响应保护，并断言最终选择仍为较新的候选。

### I2 — provenance fixture/DTO 与真实 backend payload：PASS

直接对照 `src/project_memory/review_service.py::_read_candidate()`（行 136–150）与 `desktop/lingji-control/src/pages/memoryReviewTypes.ts`、`tests/e2e_owner_memory_flow.mjs`：

- fixture 只使用现有候选接口真实字段：`memory_id`、`title`、`content_preview`（列表）、`content`（详情）、`project_ids`、`proposed_by`、`importance`、`confidence`、`created_at`、`source_refs`、`current_hash`、`relative_path`；没有新增 API 或 mock-only provenance 字段。
- 初审指出的 `source_name`、`source_session_id`、`source_message_id`、`conversation_title`、`message_excerpt`、`provenance_at`、`current_state`、`history_state`、`proposal_reason`、`affected_agents` 已从 fixture/前端候选类型移除。测试不再凭这些非正式字段断言来源链。
- UI 将真实 `relative_path` 显示为来源，将真实 `source_refs` 显示为来源引用，将真实 `created_at` 显示为时间；会话、原文片段、当前/历史状态、影响 Agent、why 在当前 backend 未提供时明确显示“尚未获得”。不存在从 ID 推断人类来源名、会话、片段、状态或理由的逻辑。
- rendered 断言覆盖 `来源：01-Inbox/AI-Memory/release.md`、`来源引用：message-1`、真实时间路径以及所有缺失 provenance 字段的“尚未获得”；同时断言 `source_session_id` 等 mock-only 文案不出现。

因此当前证据证明的是现有 `_read_candidate()` 契约，而不是凭 mock 扩展出的来源语义；未来 backend 若提供更多字段，需另行扩大契约和测试，不能把本报告解释为已具备会话/原文/why 数据。

## 回归复核

以下命令均在当前 HEAD 新鲜执行：

```text
npm run build
→ PASS（tsc + Vite build；仅既有 dynamic-import warnings）

npm run test:work-fact
→ work-fact-smoke: PASS

npm run test:memory-review
→ memory-review-smoke: PASS

npm run test:memory-sources
→ automatic-memory-sources-smoke: PASS

npm run test:memory-sources-repair
→ automatic-memory-sources-repair-smoke: PASS

npm run test:runtime
→ runtime-sidecar-smoke: PASS

npm run test:inspector
→ memory-inspector-smoke: PASS

npm run test:capture
→ capture-center-smoke: PASS

npm exec -- tsx scripts/observation-first-ui-smoke.mjs
→ observation-first-ui-smoke: PASS

./.venv/bin/python -m pytest -q tests/test_work_control_api.py tests/test_task8_work_fact.py tests/test_work_store.py tests/test_work_control_service.py tests/test_task8_extraction_work_lifecycle.py tests/test_task8_work_transition_matrix.py
→ 40 passed, 2 warnings

./.venv/bin/python -m pytest -q tests/test_work*.py tests/test_task8*.py tests/test_capture*.py tests/test_automatic_memory_work_fact.py
→ 102 passed, 2 warnings

./.venv/bin/python -m compileall -q src tests
→ PASS

git diff --check 9272e60fc5fa4b485831e101f5f1a66573f1498d..HEAD
→ PASS

./.venv/bin/python scripts/check_acceptance_sync.py
→ PASS（当前工作树 changed files 1，product-impacting files 0）

./.venv/bin/python scripts/check_local_execution_handoff.py
→ PASS（LOCAL_EXECUTION_TASK.md 为 IDLE）
```

### rendered E2E 运行说明

`npm run test:e2e:memory` 在本机实际完成了 fake-8766 rendered flow 的所有断言：Activity 中文 Work History 与结果、Attention resolve 后退出列表、来源状态/失败恢复、Memory Review 列表和详情 loading、`mem-1`/`mem-2` 迟到选择保护、真实 provenance 字段/缺失字段、Capture Center 去重、900px 无横向裁切均已到达；调试日志最后到达 `browser.close()`。

但本机 Playwright 选用的系统 Chrome 在 `browser.close()` 阶段没有返回，导致命令在工具 30 秒窗口内未产生正常退出码；这是 runner/browser 生命周期限制，不是断言失败，且按 PID 已清理测试 Node/Vite 进程。为保持证据诚实，本报告不把这次命令写成带正常退出码的 `PASS`，而将已完成的断言与关闭阶段限制分开披露。此前同一 rendered flow 在证据提交中记录为 PASS；本次独立审查没有修改其测试代码来规避该限制。

### codex-loop 基线边界

`npm run test:codex-loop` 仍失败于未改动的既有断言：`codex-workspace-smoke.mjs` 要求 `CurrentWorkPanel.tsx` 包含“当前项目”，而当前组件只有“当前工作”等文案。`CurrentWorkPanel.tsx` 与该 smoke 不在 `9272e60..HEAD` 的修复范围，失败不是 Task 5B Repair Round 1 引入；未删除、减弱或 skip 该基线测试。

## 初审 Minor 复核

以下三项按初审定义仍是非阻塞证据覆盖不足，报告没有把它们降级为 Important，也没有声称已经补齐：

- M1：Attention 失败/处理中分支存在源码和 smoke 接线，但 rendered flow 只覆盖成功 resolve；未独立渲染注入失败 resolve。
- M2：Context Pack 复制失败分支存在真实异常处理和反馈文案，但 rendered flow 未注入 clipboard 失败。
- M3：900px rendered 检查在当前 E2E 只落在高级诊断页；Activity、Attention、Memory Review、Memory Inspector 未逐页 rendered 检查。

三项不影响 I1/I2 的行为契约，也不构成 Critical/Important；后续若要求提高证据完整性，可在新的测试证据工作中补充，不得据此声称本轮已完成主人验收。

## 组合与安全边界

- Activity 继续请求认证 `/api/work/history` 分页，并显示中文 phase/result/time/source/next actor；事件 JSON 仅在技术详情 disclosure 中展示。
- Attention 继续请求认证 `/api/work/pending-actions`，resolve 后强制刷新同一 pending 投影；成功后待办真实退出，失败路径保留错误反馈。
- Capture Center 是唯一可见手动投喂入口；`capture` 兼容 PageId/路由仍保留，重复 legacy 导航隐藏；Inspector 的内部 deep-link target 仍由现有 `onOpenInspector`/target 机制传递。
- Task 4 Home/source/runtime/inspector/observation smokes 与 Task 5A 40 项 focused、102 项广义回归均通过；未修改其后端/API、WorkStore、Task 4 Home 或记忆算法。
- 本轮产品差异仅限 Memory Review loading/error/concurrency、真实候选字段收口及对应 deterministic evidence；未新增 store、queue、API、状态源、RAG、向量或持久化事实源。

## 最终判定

```text
Spec Compliance: PASS
Task Quality: PASS
Critical: 0
Important: 0
Minor: M1, M2, M3
Verdict: ACCEPT_FOR_TASK6
Product HEAD: 8136374
Repair commits: 98c0212, 8e3b263
Evidence commits: 995aa0c, 8136374
LOCAL_EXECUTION_TASK: IDLE
Live 8766/8767, Sidecar, Artifact, Production/Vault, owner data: NOT_RUN
```
