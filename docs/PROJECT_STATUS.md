# PROJECT_STATUS.md — LingJi 当前状态

> Updated: 2026-08-21  
> Formal/default branch: `master`  
> Current product PR: `#88`  
> Current development PR: `#105 / fix/pr88-owner-fact-chain-v5`  
> V5 implementation SHA: `79955a09f42b7eb525fff1f11c454c373df8aa6c`  
> V5 self-review verdict: `PASS_FOR_M5_PREPARATION`  
> Current local task: `IDLE / NO ACTIVE M5 TASK`  
> Architecture: `docs/ARCHITECTURE.md`  
> Product ledger: `docs/PROJECT_PROGRESS.md`  
> Acceptance authority: `docs/ACCEPTANCE/README.md`

## 1. 当前结论

上一轮 PR #88 Owner Workbench V4 在真实 macOS M5 上结论仍是：

```text
FAIL / DO NOT MERGE
Artifact 9258682849 / bd1e7a17 = DO NOT RETRY
```

失败核心不是打包，而是主人看不出灵机真实接管、执行和完成了什么。

PR #105 已完成 V5 事实链修复与独立自审，当前代码候选达到：

```text
PASS_FOR_M5_PREPARATION
```

这不等于 M5 PASS。下一步必须先把 #105 squash merge 到产品分支，再对新的产品 exact SHA 重跑六道门并锁定同 SHA Mac/Windows Artifact，之后才允许激活新的 M5 本机任务。

## 2. V5 已完成的产品修复

### 2.1 Capture → WorkItem 可追踪

```text
CaptureEnvelope.capture_id
        ↓ durable payload
extraction_jobs.job_id = WorkItem identity
        ↓
CaptureControlService owner-safe DTO
        ↓
/api/capture/jobs
```

- 不新增第二 WorkItem 数据库；
- `capture_id` 持久化，重启后可恢复；
- duplicate 复用 canonical WorkItem identity；
- queued/running/retrying/completed/failed/cancelled 都有真实 outcome、next_actor、next_action。

### 2.2 首页 / 工作统一事实源

```text
/api/capture/jobs
→ ownerWorkFeed
→ Home + Work
```

禁止继续使用：

- 记忆数量制造工作履历；
- `relative_path` 猜关联；
- generic event 冒充 WorkItem；
- Codex current 冒充 LingJi 工作事实。

### 2.3 首页 / 需要我统一 PendingAction

```text
Memory Review candidate
Assistant import candidate
Irreversible vector rebuild object
        ↓
ownerWorkbenchModel
        ↓
Home + 需要我
```

没有 concrete object 就没有主人动作。普通失败、汇总计数、静态发现说明不得制造待办。

### 2.4 Cmd+K / Capture 真实反馈

- 文本为一等 `source_type=text`；
- 返回真实 `capture_id/job_id/status`；
- 已入队不再写“已经记住”；
- 是否形成永久记忆以真实 MemoryRecord/result ref 为准。

### 2.5 记忆一级页可验证

“记忆”已经展示：

- 可读正文片段；
- 正式来源；
- 行级引用（存在时）；
- 关联证据；
- 向量/取回状态。

没有证据时显示未知/缺失，不补写猜测。

### 2.6 主动发现语义修正

“发现”只表示检测到支持来源。只有授权并创建真实 WorkItem 后，才允许显示“接管/执行”。

## 3. 独立自审结论

自审发现未接线的 `ownerWorkbenchSummary.ts` 会成为第三层 presentation model，增加事实漂移风险。已在 `79955a09...` 删除，不再强行套一层状态翻译。

当前单一投影规则：

```text
WorkItem      → ownerWorkFeed       → Home + Work
PendingAction → ownerWorkbenchModel → Home + 需要我
MemoryRecord  → Memory Inspector    → 记忆
```

完整自审：`docs/TEST_REPORTS/PR88_OWNER_FACT_CHAIN_V5_IMPLEMENTATION.md`。

## 4. 精确代码候选自动门禁

Implementation SHA `79955a09f42b7eb525fff1f11c454c373df8aa6c`：

```text
tests                     PASS  run 32391549495
macOS Desktop Gate        PASS  run 32391549584
acceptance-doc-sync       PASS  run 32391549523
local-execution-handoff   PASS  run 32391549512
```

`tests` 内 Python 3.11、Python 3.12、Windows、Desktop full smoke/build、MCP、browser capture、Obsidian plugin 均 PASS。

新增 `owner-10-second-smoke.mjs` 已纳入全量 Desktop smoke 并通过。

## 5. 功能可见性

当前正式 UI 仍只有：

```text
desktop/lingji-control/
```

一级入口：

```text
首页 / 记忆 / 工作 / 需要我 / 高级
```

功能可见性审计已写入：

```text
docs/MODULES/FUNCTION_VISIBILITY_MATRIX.md
```

当前仍属于后续阶段、不能冒充本轮已完成的项目：

- Retrieval Quality 真实样本评测；
- Inspector / Vector 普通用户语言进一步产品化；
- Codex 之外其他 AI 共享记忆的真实端到端验证；
- 机会系统恢复开发。

## 6. 当前唯一剩余门禁

PR #105 代码阶段已达到产品分支准备标准。接下来只允许：

```text
1. squash merge #105 → feature/owner-autopilot-ui-codexpp
2. 获取新的 product exact SHA
3. 同 SHA：tests
4. 同 SHA：P0 Windows Gate
5. 同 SHA：Windows Desktop Release Baseline
6. 同 SHA：macOS Desktop Gate
7. 同 SHA：acceptance-doc-sync
8. 同 SHA：local-execution-handoff
9. 锁定 Mac/Windows Artifact 与哈希
10. 更新 LOCAL_EXECUTION_TASK 为新的 ACTIVE M5
11. 主人真机：10 秒理解 + Window Recovery 三路径 + Production pollution=0 + 清理
```

在第 9 步以前：

```text
LOCAL_EXECUTION_TASK = IDLE
```

## 7. 已稳定，不重复返工

以下只做必要回归：

- Apple Silicon arm64；
- strict codesign；
- whole-bundle replace 合同；
- Acceptance / Production 物理隔离；
- Credential/Secret 边界；
- `secret_export_count=0`；
- exact-instance Runtime start/stop；
- 记忆分页终点；
- Production pollution 保护；
- Qdrant destructive rebuild 禁止自动执行。

## 8. 历史失败 Artifact

以下永久 `DO NOT RETRY`：

```text
9258682849 / bd1e7a17
9250384637 / 1d99d10c
9249367672 / f3cba413
9224368022 / 2c96b3ec
9102748834 / 171091fe
```

## 9. 合并边界

PR #88 继续保持：

```text
DRAFT / DO NOT MERGE
```

直到新的产品 exact SHA 完成同 SHA 双平台门禁、Artifact 锁定和主人 M5 真机验收。
