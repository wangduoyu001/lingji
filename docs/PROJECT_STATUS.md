# PROJECT_STATUS.md — LingJi 当前状态与开发指挥

> Updated: 2026-08-22
> Formal/default branch: `master`
> Active development branch: `feat/sb0-work-fact-contract`
> Active PR: `#106` / Draft / DO NOT MERGE
> Current product code SHA: `1c1b6b9ceffa08f5d4638bdf001a4ca9702b2b2d`
> Latest coordination/docs head at this snapshot: `1a95b53db74f357d7f8af3e36357eb729c366903`
> Product phase: `PHASE 1 — SECOND BRAIN COMPLETION`
> Last completed node: `SB-0 — WORK FACT CONTRACT REPAIR / AUTOMATED_PASS`
> Active node: `SB-1 — CAPTURE → WORK → OUTCOME / ACTIVE`
> Next node: `SB-2 — WORK → MEMORY / EVIDENCE`
> Owner M5: `NOT ACTIVE`
> Opportunity Center: `FROZEN UNTIL PHASE 1 FINAL PASS`

Authority links:

- architecture: `docs/ARCHITECTURE.md`
- code entry points: `docs/MODULES/CODE_MAP.md`
- acceptance: `docs/ACCEPTANCE/README.md`
- node-specific acceptance: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- backlog: `docs/MODULES/FUTURE_DEVELOPMENT_TODO.md`

## 0. 跨对话开发接力协议

**本文件是唯一当前开发指挥文档。** 聊天上下文、PR 描述、历史 roadmap 和旧测试报告都不能替代本文件记录当前进度。

新对话继续开发时，按这个顺序读取：

```text
AGENTS.md
→ docs/PROJECT_STATUS.md
→ docs/MODULES/CODE_MAP.md 当前节点相关章节
→ docs/ACCEPTANCE/README.md
→ docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md 当前节点条目
→ 当前节点直接相关代码与测试
```

不需要重新全仓审计，除非当前远端代码与本文件明显冲突。

每个节点只能使用这些状态：

```text
NOT_STARTED
ACTIVE
BLOCKED
AUTOMATED_PASS
OWNER_PASS
CLOSED
```

每个节点必须持续记录：

```text
分支 / PR / 精确产品 SHA
已完成事实
尚未完成事实
自动验收结果
平台 Artifact（如有）
下一节点启动条件
下一步代码入口
```

更新规则：

1. 节点开始前先标 `ACTIVE`。
2. 每完成一个可验证子节点就更新，不等整轮结束后靠聊天回忆。
3. 产品代码变化后更新精确产品 SHA；docs/test-only commit 不冒充产品 SHA。
4. 自动门禁真实通过后才写 `AUTOMATED_PASS`。
5. 需要主人观察的内容未经主人确认不得写 `OWNER_PASS`。
6. 不创建 `CURRENT_PLAN`、`NEXT_PLAN`、`FINAL_PLAN`、handoff summary 等平行文档。
7. 当前计划进 `PROJECT_STATUS.md`；未来需求进 `FUTURE_DEVELOPMENT_TODO.md`；验收细节进 `docs/ACCEPTANCE/`。

## 1. 当前接力快照

```text
Phase:
  PHASE 1 — SECOND BRAIN COMPLETION

Branch:
  feat/sb0-work-fact-contract

PR:
  #106 Draft / DO NOT MERGE

Current product code:
  1c1b6b9ceffa08f5d4638bdf001a4ca9702b2b2d

Completed:
  SB-0 Work Fact Contract Repair = AUTOMATED_PASS

Active:
  SB-1 Capture → Work → Outcome

SB-1 current verification:
  backend real lifecycle tests passed on earlier SB-1 tree
  latest product tree includes retry-outcome fix + Desktop Cmd+K handoff
  latest full cross-platform gates are RUNNING / NOT YET FINAL

Next:
  finish SB-1 gates + report/status sync
  then activate SB-2 Work → Memory / Evidence

Owner M5:
  NOT ACTIVE

Opportunity Center:
  FROZEN
```

### 1.1 最近一次主人验收

最后一次真实 M5 仍然是：

```text
FAIL / DO NOT MERGE
```

上次核心失败：

- 看不清灵机到底接手了什么、执行了什么、结果是什么；
- Home / Work / Attention 没有同一真实事实链；
- Cmd+K “记住”没有形成可追踪 Capture → Work → Memory；
- Memory 正文/来源证据不足；
- 主动发现仍不像真实状态机；
- Window Recovery 仍需最终主人观察。

SB-0 和正在开发的 SB-1 正在逐层消除这些失败原因，但**没有新 M5 之前旧 FAIL 结论仍有效**。

## 2. SB-0 — Work Fact Contract Repair

状态：`AUTOMATED_PASS`

产品 SHA：

```text
c02f73fde7fb4492a665b4c1fd3f93c900499d52
```

已完成：

- WorkItem / ExecutionEvent / Outcome / NextAction / PendingAction DTO 统一；
- WorkStore 非破坏 schema migration；
- create/get/list/update/events/Outcome/NextAction/PendingAction/resolve 完整；
- WorkProjector / WorkControlService / LocalControlService 共享 canonical WorkStore；
- 正式认证 8766 注册 `/api/work/*`；
- Python ↔ TypeScript Work Fact contract 对齐；
- Home / Activity / Attention 不再把 API unavailable 冒充真实空状态；
- dedicated Work Fact tests + Desktop smoke；
- 同秒事件排序和旧 Outcome 状态兼容修复。

自动验收：

```text
Linux Python 3.11: 579 passed / 11 skipped / 0 failed
Linux Python 3.12: 579 passed / 11 skipped / 0 failed
Windows Python 3.12: 579 passed / 11 skipped / 0 failed
Desktop smoke/build: PASS
MCP smoke: PASS
Browser Capture smoke: PASS
Obsidian plugin smoke: PASS
acceptance-doc-sync: PASS
local-execution-handoff: PASS
P0 Windows Gate: PASS
macOS Desktop Gate: PASS
Windows Desktop Release Baseline: PASS
```

同 SHA Artifact：

```text
macOS arm64
artifact: lingji-macos-arm64
artifact_id: 9469111722
sha256: 7b1a4fe313da5ae4d709651fc9a18f43ee0281b57f15c7bddab9260fdeb559e8

Windows
artifact: lingji-windows-0.1.0-c02f73fd
artifact_id: 9469187504
sha256: e4fe344ad4b023da24e9a8ca125b9c6756da4057f01426b5c520d01fdd277eb6
```

SB-0 不单独宣称主人体验 PASS，最终随 Phase 1 M5 验收。

## 3. SB-1 — Capture → Work → Outcome

状态：`ACTIVE`

当前产品代码 SHA：

```text
1c1b6b9ceffa08f5d4638bdf001a4ca9702b2b2d
```

验收定义：`docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md` 顶部 SB-1 条目。

### 3.1 目标事实链

```text
Cmd+K / Capture Center / approved input
-> authenticated /api/capture/*
-> Capture validation
-> stable capture identity
-> stable WorkItem(work_id)
-> extraction job(job_id)
-> capture.accepted
-> extraction.queued
-> extraction.started
-> extraction.retrying? if needed
-> extraction.completed | extraction.failed | extraction.cancelled
-> Outcome success | failure | skipped
-> NextAction actor
-> Desktop uses same work_id
```

### 3.2 已完成子节点

#### A. Stable Capture → Work identity

已完成：

- `work_id` 由 Capture idempotency identity 确定，不依赖随机 UI 状态；
- Capture 接受响应增加 `capture_id + work_id + job_id`；
- extraction job options 持久保存 `_lingji_work_id / _lingji_capture_id / _lingji_capture_identity`；
- 同一内容跨 CaptureControlService / Runtime 重建仍复用同一 WorkItem；
- duplicate 会记录真实 `capture.duplicate`，不生成第二份主人工作事实。

主要代码：

```text
src/control/capture.py
src/control/capture_api.py
src/work/capture_bridge.py
```

#### B. Extraction worker → Work lifecycle

已完成：

- queue claim → `extraction.started`；
- transient retry → `extraction.retrying` + system NextAction；
- completed → success Outcome；
- final failed → failure Outcome；
- cancelled → skipped Outcome；
- lifecycle callback 自身失败只记录日志，不篡改 extraction queue 结果；
- 没有 `_lingji_work_id` 的通用 extraction job 不被伪装成 Capture Work。

主要代码：

```text
src/extraction/pipeline.py
src/extraction/bootstrap.py
src/work/capture_bridge.py
```

#### C. Retry truth fix

已完成：

- `WorkStore.clear_outcome(work_id)`；
- failed/cancelled Work 重试前删除旧 terminal Outcome；
- 同一 WorkItem 重新进入 accepted/running 时不会同时保留“上次失败仍是当前结果”的矛盾状态。

主要代码：

```text
src/work/store.py
src/work/capture_bridge.py
```

#### D. Real integration tests

已完成并在较早 SB-1 tree 的真实 GitHub Actions 中通过：

```text
tests/test_capture_work_lifecycle.py
```

覆盖：

- real CaptureControl → real ExtractionPipeline → same SQLite → completed Outcome；
- Runtime/Service 重建后 duplicate 仍是 same job_id + same work_id；
- real Worker failure → failed Work + safe failure Outcome；
- rejected input 不创建主人 WorkItem。

该批进入整库测试后：

```text
Linux Python 3.11: 583 passed / 11 skipped / 0 failed
Linux Python 3.12: PASS
Windows Python: PASS on subsequent SB-1 tree before latest retry/Desktop fixes
```

这只是中间证据，**不能替代当前产品 SHA 的最终门禁**。

#### E. Desktop Capture work handoff

已实现：

- `CaptureSubmissionResponse.work_id`；
- Capture job DTO 展示 `work_id`；
- Capture Center 成功后只有拿到真实 work_id 才宣称“灵机已接手”；
- job/detail 提供“查看工作”；
- API 没返回 work_id 时明确显示不能宣称已接手。

主要代码：

```text
desktop/lingji-control/src/pages/captureCenterTypes.ts
desktop/lingji-control/src/pages/CaptureCenterPage.tsx
desktop/lingji-control/src/AppPages.tsx
```

#### F. Cmd/Ctrl+K 快速“记住”

已实现：

- Cmd+K / Ctrl+K 打开快速“记住”；
- Cmd/Ctrl+Enter 提交；Esc 关闭；
- 与 Capture Center 共用 `CaptureCenterApi.submitText()`；
- 唯一后端入口仍是 `/api/capture/text`；
- 不直写 `/api/memory`，不使用 localStorage 作为事实源；
- 提交失败保留输入并显示真实 API 错误；
- 成功后显示 capture/work/job ID；有 work_id 才允许“查看工作”。

主要代码：

```text
desktop/lingji-control/src/components/QuickCapture.tsx
desktop/lingji-control/src/components/QuickCapture.css
desktop/lingji-control/src/App.tsx
```

门禁：

```text
desktop/lingji-control/scripts/quick-capture-smoke.mjs
desktop/lingji-control/scripts/capture-center-smoke.mjs
```

### 3.3 已发现并修复的 SB-1 回归

一次 QuickCapture 接入误把 `App.tsx` 覆盖成过时简版，导致旧正式壳中的：

```text
NAVIGATION
RuntimeBoundary
release metadata
runtime lifecycle controls
```

被删除。

GitHub Desktop smoke 在 `b2f8d217...` 及时失败并定位该问题。当前产品代码已恢复正式 App shell，仅在 RuntimeBoundary 内嵌入 QuickCapture。

**该失败不能被忽略，也不能把旧 b2f8d217 tree 标成通过。**

### 3.4 当前未完成 / 正在验证

当前最新产品代码需要完成以下真实门禁：

```text
1. Linux Python 3.11 full tests
2. Linux Python 3.12 full tests
3. Windows Python full tests
4. Desktop smoke 21 scripts
5. React production build
6. Tauri configuration / Rust gate
7. acceptance-doc-sync
8. local-execution-handoff
9. P0 Windows Gate
10. macOS Desktop Gate
11. Windows Desktop Release Baseline
```

当前状态：`RUNNING / NOT YET FINAL`。

不得在上述当前树门禁完成前把 SB-1 标成 `AUTOMATED_PASS`。

### 3.5 SB-1 剩余代码/文档收口

自动门禁若发现红灯：

```text
先按真实日志修复
→ 补回归断言
→ 更新本节点产品 SHA
→ 重跑门禁
```

自动门禁全绿后：

```text
更新 docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md
  product Commit: exact SB-1 SHA
  自动验收 checkbox -> real result

生成/更新
  docs/TEST_REPORTS/SB1_CAPTURE_WORK_OUTCOME.md

更新本文件
  SB-1 -> AUTOMATED_PASS
  SB-2 -> ACTIVE
```

### 3.6 下一步代码入口

若当前门禁红：

```text
直接读取失败 job log，然后只修对应模块。
```

若门禁绿：

```text
SB-2 first audit:
src/extraction/structured_sink.py
src/project_memory/
src/gateway/memory.py
src/gateway/memory_inspector.py
src/sources/read_model.py
Desktop Memory Inspector / Memory pages
相关 tests
```

SB-1 结束前不得进入 SB-2 功能实现，也不得开发 Opportunity Center。

## 4. Phase 1 节点总表

| Node | Scope | Status | Exit gate |
|---|---|---|---|
| SB-0 | Work Fact Contract Repair | `AUTOMATED_PASS` | unified DTO/store/8766/Desktop + cross-platform gates |
| SB-1 | Capture → Work → Outcome | `ACTIVE` | real capture produces traceable work/events/outcome + current-tree gates |
| SB-2 | Work → Memory / Evidence | `NOT_STARTED` | readable memory + provenance + bidirectional trace |
| SB-3 | Retrieval / Vector / Inspector verification | `NOT_STARTED` | lexical/semantic/Qdrant/embedding truth consistent |
| SB-4 | AI Memory Access / Context Pack / MCP | `NOT_STARTED` | one governed memory access path |
| SB-5 | Owner UI continuity | `NOT_STARTED` | Home/Work/Attention/Capture/Memory same facts |
| SB-6 | Compatibility / Migration completion | `NOT_STARTED` | formal flow independent of compatibility runtime |
| SB-7 | Automatic E2E Acceptance Gate | `NOT_STARTED` | real end-to-end fixture + full validation |
| SB-8 | Release + Owner Final Acceptance | `NOT_STARTED` | same-SHA artifacts + real-machine + owner PASS |

## 5. Phase 1 最终 PASS 合同

Phase 1 只有以下全部成立才能进入机会面板：

- Work Fact 合同端到端通过；
- Capture → Work → Memory / Failure 可追踪；
- Memory 内容和来源可读、可验证；
- owner review / Core / supersede 等生命周期无越权；
- lexical / semantic / Qdrant / embedding 真值一致；
- Source / Conversation / Message provenance 成立；
- MemoryGateway / Context Pack / MCP 共享同一记忆与权限；
- Home / Work / Attention / Capture / Memory 不互相矛盾；
- compatibility runtime disabled 后正式能力仍可用；
- Production / Acceptance 无污染；
- focused / full / required release gates 通过；
- 最终候选 Artifact 身份锁定；
- 当前验收任务执行完成；
- 主人无法自动证明的体验项由主人实际确认；
- 最终 M5 = `PASS`。

任何一项为 `FAIL / BLOCKED / NOT_TESTED`，Phase 1 都不能写成完成。

## 6. Phase 2 启动门禁

只有 Phase 1 最终 PASS 后，本文件才允许切换为：

```text
PHASE 2 — OPPORTUNITY CENTER
```

届时先审计现有：

```text
src/opp_generator.py
src/opportunities/
旧 PEMIS Opportunity 数据与评分
现有 Vault / scheduler / feedback 路径
```

机会对象必须复用已经验收通过的 Source + Work Fact + Evidence 基础设施，然后才开发 Opportunity Center。

## 7. 技术边界与冻结项

保持不变：

- `src/` = 长期平台主线；
- `desktop/lingji-control/` = 唯一正式 Desktop UI；
- `second_brain/` = 兼容、迁移和验收来源，不新增主产品能力；
- Desktop 只通过认证 `127.0.0.1:8766`；
- Obsidian Vault + Git = 永久记忆正文权威；
- SQLite / Qdrant = 运行状态或可重建派生层；
- Acceptance / Production 必须物理隔离；
- AI 不自动批准永久记忆；
- 不自动破坏性 rebuild Qdrant；
- 不为美化 UI 建第二事实源。

Phase 1 最终 PASS 前冻结：

```text
Opportunity Center 新功能
Opportunity Score 重做
机会数据模型扩展
机会自动验证产品流程
每日简报新阶段
LLM Router 新阶段
AnySearch 新阶段
```

## 8. 不要重复返工的稳定基础

除非新回归证据明确失败，不要把主要时间重新消耗在：

- 产品 / Artifact 精确身份机制；
- Apple Silicon arm64 基础构建；
- strict codesign；
- whole-bundle replace；
- Acceptance / Production 隔离原则；
- Secret export 边界；
- exact-instance Runtime stop 原则；
- 记忆分页终点规则；
- 高级技术信息下沉原则。

相关模块变化时仍需回归，但它们不是当前主矛盾。

## 9. 历史失败 Artifact

永久 `DO NOT RETRY`：

```text
9258682849 / bd1e7a17
9250384637 / 1d99d10c
9249367672 / f3cba413
9224368022 / 2c96b3ec
9102748834 / 171091fe
```

当前没有 ACTIVE 主人本机验收任务。旧 Artifact 不得因为仍可下载而重跑。
