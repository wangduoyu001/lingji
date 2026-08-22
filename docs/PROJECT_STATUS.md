# PROJECT_STATUS.md — LingJi 当前状态与开发指挥

> Updated: 2026-08-22
> Formal/default branch: `master`
> Active development branch: `feat/sb0-work-fact-contract`
> Active development PR: `#106` / Draft / DO NOT MERGE
> Current product commit: `c02f73fde7fb4492a665b4c1fd3f93c900499d52`
> Last owner acceptance closeout: `e594e3f05e8726cbae7b0a590e6f515fb2cc67c5`
> Last rejected product candidate: `bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9`
> Current product phase: `PHASE 1 — SECOND BRAIN COMPLETION`
> Last completed engineering node: `SB-0 — WORK FACT CONTRACT REPAIR / AUTOMATED GATES PASS`
> Current engineering node: `SB-1 — CAPTURE → WORK → OUTCOME`
> Opportunity Center: `FROZEN UNTIL PHASE 1 FINAL PASS`
> Architecture: `docs/ARCHITECTURE.md`
> Code entry points: `docs/MODULES/CODE_MAP.md`
> Future backlog: `docs/MODULES/FUTURE_DEVELOPMENT_TODO.md`
> Acceptance authority: `docs/ACCEPTANCE/README.md`

## 0. 跨对话开发接力协议

本文件是**唯一当前开发指挥文档**。聊天上下文、PR 评论、历史计划、旧测试报告都不能代替本文件记录“当前做到哪里、下一步做什么”。

由于开发会频繁跨对话窗口，任何继续开发的会话必须先执行以下最小读取顺序：

```text
AGENTS.md
→ docs/PROJECT_STATUS.md
→ docs/MODULES/CODE_MAP.md 当前节点相关章节
→ docs/ACCEPTANCE/README.md
→ docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md 当前节点条目
→ 当前节点直接相关代码与测试
```

每个工程节点必须在本文件维护以下状态：

```text
节点编号 / 名称
状态: NOT_STARTED | ACTIVE | BLOCKED | AUTOMATED_PASS | OWNER_PASS | CLOSED
开发分支 / PR / 精确产品 SHA
已完成事实
尚未完成事实
自动验收结果
平台 Artifact（如有）
下一节点启动条件
下一步代码入口
```

硬规则：

1. 一个节点开始前，先把它写成 `ACTIVE`，并把前一节点的真实结果写清楚。
2. 每完成一个可验证子节点，立即更新本文件，不等整轮开发结束后靠聊天回忆补写。
3. 节点自动门禁完成后写 `AUTOMATED_PASS`；需要主人真机/肉眼确认的，不得提前写 `OWNER_PASS` 或 `CLOSED`。
4. 新窗口不得从聊天历史猜测进度。仓库文档与当前远端代码冲突时，以当前远端代码和 CI 事实纠正文档。
5. `PROJECT_STATUS.md` 只记录当前阶段、节点和下一步；未来需求继续进入 `FUTURE_DEVELOPMENT_TODO.md`，验收细节继续进入 Acceptance 文档，避免再次堆出多份“最终计划”。
6. 产品影响代码提交后，必须在同一开发节点更新本文件中的精确 SHA 与验收状态。

### 0.1 当前接力快照

```text
Phase: PHASE 1 — SECOND BRAIN COMPLETION
Branch: feat/sb0-work-fact-contract
PR: #106 Draft / DO NOT MERGE
Product SHA: c02f73fde7fb4492a665b4c1fd3f93c900499d52
Completed: SB-0 automated implementation + cross-platform CI/release gates
Active: SB-1 Capture → Work → Outcome
Next after SB-1: SB-2 Work → Memory / Evidence
Owner M5: NOT ACTIVE
Opportunity Center: FROZEN
```

新对话读取到这里后，不需要重新审计整个仓库。先继续 SB-1 当前未完成项。

## 1. 当前唯一产品目标

当前只做一件事：**把灵机的第二大脑做成完整、可理解、可追踪、可验证的正式产品，并完成全部规定验收。**

在 Phase 1 最终 PASS 之前：

- 不开发新的机会面板；
- 不重做 Opportunity Score；
- 不扩展机会数据模型；
- 不增加机会自动验证产品流程；
- 不让每日简报、LLM Router、AnySearch 或其他新产品阶段插队；
- 现有 `src/opp_generator.py`、`src/opportunities/` 只允许必要的兼容和回归修复。

Phase 1 PASS 后，Phase 2 第一优先级固定为 **Opportunity Center / 机会面板**。

## 2. 最近一次主人验收结论

最后一次真实 M5 验收仍然是：

```text
FAIL / DO NOT MERGE
```

失败不是安装、签名、Sidecar、隔离或发布链问题。技术发布链的大部分基础已经证明可用。

真正阻塞是：**主人无法从产品中清楚看见灵机接管了什么、执行了什么、结果是什么、下一步由谁执行，也无法稳定验证一条输入如何变成可追溯记忆。**

关键失败观察：

- 首页暗示存在待确认事项，但“需要我”没有同一个真实 `PendingAction`；
- 首页暗示系统完成了工作，但“工作”没有真实履历；
- `Cmd+K` 的“记住”真实提交失败，没有形成 Capture → Work → Memory 闭环；
- 记忆缺少主人可读正文/摘要和清楚来源证据；
- 主动发现更像静态说明，不是“发现 → 授权 → 接管 → 执行 → 结果”的真实状态；
- Window Recovery 的菜单 / 快捷键 / Dock Reopen 三路径仍缺最终主人肉眼验收。

SB-0 已修复“没有可信统一 Work Fact contract”的底层阻塞，但还没有完成真实主人输入到 Outcome/Memory 的全链，所以旧 M5 结论仍然有效，当前不激活新的主人验收。

## 3. Phase 1 的“第二大脑完成”定义

第二大脑不是某一个 Memory 页面。Phase 1 必须同时成立以下九个能力面。

### 3.1 单一事实与记忆权威

```text
Permanent memory / formal knowledge
= Obsidian Vault + Git

Runtime work / task / audit facts
= lingji_state.db / formal Work Fact persistence

Lexical / metadata index
= lingji_memory.db

Semantic index
= Qdrant
```

不得引入第二套永久记忆正文、第二套任务事实源或第二套正式 UI。

### 3.2 Capture 与来源链

真实输入必须形成可追踪链：

```text
Input
-> Capture
-> Extraction
-> Raw snapshot / provenance
-> Source / Conversation / Message
-> WorkItem
-> Memory candidate / formal knowledge outcome / explicit failure
```

主人必须能知道：输入是什么、来自哪里、系统做到了哪一步、失败在哪里。

### 3.3 Work Fact 工作事实链

唯一工作语义：

```text
SourceObject
-> Discovery / Intent
-> WorkItem
-> ExecutionEvent
-> Outcome
-> NextAction + actor
-> PendingAction? only when owner is required
-> MemoryRecord? when memory is produced
```

Home / Work / Attention / Capture / Memory 只能投影同一条事实链。

### 3.4 Memory lifecycle

必须能稳定证明：

- 记忆正文可读；
- 来源和 citation 可验证；
- candidate / owner review / accepted / rejected / core / superseded 等状态真实；
- AI 不静默批准永久记忆；
- Core Memory 不被自动覆盖；
- 记忆、索引和来源 ID 可关联。

### 3.5 Retrieval / Vector / Embedding

必须证明：

- lexical 与 semantic 使用同一正式检索流程；
- Qdrant 状态、collection、dimension、coverage 和错误真实；
- Embedding 模型和状态真实；
- semantic 不可用时 lexical 正常降级；
- 维度不匹配只进入 `rebuild_required`，不自动破坏生产 collection；
- Memory Inspector / Brain Status / MCP 的统计不能互相矛盾。

### 3.6 AI 统一记忆访问

正式 AI 客户必须通过统一 MemoryGateway / Context Pack / MCP 权限边界读取记忆。

必须证明：

- privacy / project / Agent Scope 生效；
- restricted memory 不越权；
- Context Pack 有 citation；
- 不存在每个 AI 各存一份正式记忆的行为。

### 3.7 Obsidian 正式集成

Obsidian 已迁入 `src/obsidian/` 正式主线。Phase 1 需要做的是最终产品闭环验证，而不是重新迁移。

必须证明：

- Workspace Vault 路径正确；
- Production / Acceptance 隔离；
- 安全读写、Dry Run、错误和路径边界；
- Desktop 状态和设置真实；
- 不写入旧机器专属目录。

### 3.8 唯一 Desktop 体验

正式 UI 只有：

```text
desktop/lingji-control/
```

正常主人体验首先回答：

1. 灵机现在在做什么？
2. 最近完成或失败了什么？
3. 是否有事情真的需要主人？
4. 灵机记住了什么，证据在哪里？

高级技术页继续保留，但不能用大量状态卡替代工作事实。

### 3.9 Runtime / Packaging / Recovery

必须保持：

- authenticated `127.0.0.1:8766`；
- Tauri → Rust RuntimeManager → packaged Sidecar；
- exact-instance start / stop；
- Production / Acceptance 物理隔离；
- Secret 不出安全凭据边界；
- macOS / Windows 构建与发布门禁；
- Window Recovery 规定路径完成真实验证。

## 4. 当前代码真实进度

### 4.1 已经存在的正式基础

当前开发树已有：

```text
src/work/models.py
src/work/store.py
src/work/capture_bridge.py
src/work/projector.py
src/control/work_routes.py
src/control/work_service.py

desktop/lingji-control/src/contracts/workFact.ts
desktop/lingji-control/src/components/CurrentWorkPanel.tsx
desktop/lingji-control/src/pages/ActivityPage.tsx
desktop/lingji-control/src/pages/AttentionPage.tsx
```

并已有 Capture、Extraction、MemoryGateway、Qdrant provider、Memory Inspector、Source read model、Memory lifecycle、MCP、Obsidian、Sidecar 等基础模块。

方向已经从“UI 根据聚合状态猜系统在干什么”转为“UI 投影真实工作事实”。

### 4.2 SB-0 — AUTOMATED_PASS

开发分支：`feat/sb0-work-fact-contract`  
PR：`#106` Draft / DO NOT MERGE  
产品代码 SHA：`c02f73fde7fb4492a665b4c1fd3f93c900499d52`

已完成：

- WorkItem / ExecutionEvent / Outcome / NextAction / PendingAction DTO 统一；
- WorkStore 补齐安全 schema migration、create/get/list/update、events、Outcome、NextAction、PendingAction 与 resolve；
- CaptureWorkBridge 改为使用正式 WorkStore；
- WorkProjector / WorkControlService / LocalControlService 共用正式 Store；
- `/api/work/current`、`/api/work/recent`、`/api/work/{work_id}`、`/api/work/timeline/{work_id}`、`/api/work/pending-actions` 注册到认证 8766；
- Python 与 Desktop TypeScript Work Fact contract 对齐；
- Home / Activity / Attention 不再把 API 失败伪装成真实空状态；
- 新增 `test_work_store.py`、`test_work_projector.py`、`test_work_control_api.py`、`test_capture_work_bridge.py` 和 `work-fact-smoke.mjs`；
- 修复同秒事件顺序与旧 schema Outcome 状态兼容；
- 清理与新事实合同冲突的旧 Desktop smoke 断言。

自动验收事实：

```text
Linux Python 3.11: 579 passed / 11 skipped / 0 failed
Linux Python 3.12: 579 passed / 11 skipped / 0 failed
Windows Python 3.12: 579 passed / 11 skipped / 0 failed
Desktop smoke/build: PASS
MCP smoke: PASS
Browser capture smoke: PASS
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
product_sha: c02f73fde7fb4492a665b4c1fd3f93c900499d52

Windows
artifact: lingji-windows-0.1.0-c02f73fd
artifact_id: 9469187504
sha256: e4fe344ad4b023da24e9a8ca125b9c6756da4057f01426b5c520d01fdd277eb6
product_sha: c02f73fde7fb4492a665b4c1fd3f93c900499d52
```

SB-0 当前状态：`AUTOMATED_PASS`。它尚未单独激活主人验收，因为 Phase 1 的主人产品价值仍取决于 SB-1/SB-2 等后续闭环。

### 4.3 SB-1 — ACTIVE

目标：把真实主人输入与已经验收通过的 Work Fact 基础连接起来。

当前优先路径：

```text
Cmd+K 文本“记住”
-> formal Capture endpoint
-> capture_id
-> WorkItem(work_id)
-> capture.accepted
-> extraction queued/running
-> extraction completed/failed
-> Outcome success/failure/skipped
-> NextAction actor
-> Desktop 可按同一 work_id 查询
```

本节点必须检查并修复：

1. Cmd+K 当前实际调用的 Capture API 与响应 contract；
2. CaptureService / control capture route 是否在真实接受时调用 CaptureWorkBridge；
3. Extraction enqueue / worker 生命周期如何把 job 状态映射成同一 WorkItem 的 ExecutionEvent；
4. success/failure 是否都会落 Outcome，而不是只 toast；
5. capture_id / source_id / import_id / job_id / work_id 的稳定关联位置；
6. 幂等重复提交不得制造多个互相矛盾的 WorkItem；
7. Desktop Capture 成功响应必须携带 `work_id`，并能跳到同一工作事实；
8. 真实失败必须保留可查询 WorkItem 与失败事件。

SB-1 自动验收最低要求：

```text
one text capture
-> response contains stable capture_id + work_id
-> same work_id visible through /api/work/{work_id}
-> timeline contains accepted + processing + completed/failed
-> Outcome persisted after process restart
-> failure path remains visible
-> duplicate/idempotent path is deterministic
-> Desktop smoke verifies work_id handoff
```

SB-1 下一步代码入口：

```text
src/control/capture_api.py
src/capture/service.py
src/work/capture_bridge.py
src/extraction/pipeline.py
src/extraction/queue.py
src/extraction/worker.py
src/extraction/structured_sink.py
desktop/lingji-control/src/* Cmd+K / Capture call sites
tests/test_capture_api.py
tests/test_capture_control.py
tests/test_capture_service.py
tests/test_capture_work_bridge.py
```

SB-1 结束前不得进入 SB-2 的 Memory UI 扩展，也不得开发 Opportunity Center。

## 5. Phase 1 开发节点总表

| Node | Scope | Status | Exit gate |
|---|---|---|---|
| SB-0 | Work Fact Contract Repair | `AUTOMATED_PASS` | unified DTO/store/8766/Desktop + cross-platform gates |
| SB-1 | Capture → Work → Outcome | `ACTIVE` | real capture produces traceable work/events/outcome |
| SB-2 | Work → Memory / Evidence | `NOT_STARTED` | readable memory + provenance + bidirectional trace |
| SB-3 | Retrieval / Vector / Inspector verification | `NOT_STARTED` | lexical/semantic/Qdrant/embedding truth consistent |
| SB-4 | AI Memory Access / Context Pack / MCP | `NOT_STARTED` | one governed memory access path |
| SB-5 | Owner UI continuity | `NOT_STARTED` | Home/Work/Attention/Capture/Memory same facts |
| SB-6 | Compatibility / Migration completion | `NOT_STARTED` | formal flow independent of compatibility runtime |
| SB-7 | Automatic E2E Acceptance Gate | `NOT_STARTED` | end-to-end fixture + full validation |
| SB-8 | Release + Owner Final Acceptance | `NOT_STARTED` | same-SHA artifacts + real-machine + owner PASS |

### SB-2 — Work → Memory / Evidence

目标：系统说“记住了”时，主人能够证明它真的记住了什么。

完成条件：

- Memory 有可读正文或摘要；
- Source / citation / provenance 可打开；
- WorkItem 与 Memory ID 互相可追踪；
- Failure 明确显示而不是降级成空结果；
- candidate / owner review 行为不被绕过。

### SB-3 — Retrieval / Vector / Memory Inspector 总核验

目标：不重新开发已经存在的 Qdrant / Inspector，而是补齐产品真实性与一致性。

完成条件：

- lexical + semantic 正式查询链通过；
- Qdrant available / unavailable 两种模式；
- embedding / dimension / coverage / rebuild_required 真值；
- per-memory / per-chunk vector existence；
- Inspector / Brain Status / MCP counts 一致；
- source、conversation、message、memory、chunk、vector 可连续追踪。

### SB-4 — AI Memory Access / Context Pack / MCP 核验

目标：证明第二大脑不仅 Desktop 能看，批准的 AI 也真正共享同一记忆。

完成条件：

- MemoryGateway 是统一出口；
- Context Pack citation 完整；
- project / privacy / Agent Scope 合同测试；
- MCP 正常与降级路径；
- compatibility runtime disabled 时正式 AI memory flow 仍成立。

### SB-5 — Owner UI 连续性

目标：基于已经通过的事实合同完成 UI，而不是反过来。

顺序：

```text
Home
-> Work
-> Attention
-> Capture
-> Memory
-> Discovery status
-> Advanced diagnostics continuity
```

硬规则：

- Home 没有 WorkItem 不得宣称“灵机做了”；
- 没有 PendingAction 不得宣称“需要你”；
- Activity / Work 必须显示真实事件和 Outcome；
- 空状态解释为什么空、系统是否会继续自动工作；
- 同一对象跨页面保持同一 ID 和状态。

### SB-6 — Compatibility / Migration Completion Check

目标：确认 `second_brain/` 不再承载任何正式必需能力。

完成条件：

- 正式流程在 compatibility runtime disabled 状态下通过；
- 旧数据有可验证 export / rollback 路径；
- 不急于物理删除兼容目录；
- 不允许新正式能力回流 `second_brain/`。

### SB-7 — Automatic End-to-End Acceptance Gate

必须至少覆盖真实 fixture：

```text
输入
-> Capture
-> Work
-> Events
-> Outcome
-> Memory / PendingAction / Failure
-> Retrieval
-> Desktop projection
-> MCP / Context Pack where applicable
```

运行：

```powershell
.\scripts\validate.ps1 -Mode focused -Area <affected-area>
.\scripts\validate.ps1 -Mode full
python scripts/check_acceptance_sync.py
```

产品影响变化同步更新 `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`。

### SB-8 — Release + Owner Final Acceptance

自动门禁通过后才允许生成新产品候选。

顺序：

```text
final product commit
-> full gate
-> release gate
-> same-SHA platform artifacts
-> hash lock
-> new ACTIVE acceptance task
-> packaged Desktop real-machine acceptance
-> owner observations
-> result / cleanup / remote reread
```

只有最终结论为 PASS，Phase 1 才算完成。

## 6. Phase 1 最终 PASS 条件

以下全部满足，才允许进入机会面板：

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
- 新候选 Artifact 身份锁定；
- 当前验收任务执行完成；
- 主人无法自动证明的体验项由主人实际确认；
- 最终结果为 `PASS`。

任何一项 FAIL / BLOCKED / NOT_TESTED，都不能把 Phase 1 写成完成。

## 7. Phase 2：机会面板启动门禁

Phase 1 PASS 后，才更新本文进入：

```text
PHASE 2 — OPPORTUNITY CENTER
```

届时第一步不是画页面，而是审计现有：

```text
src/opp_generator.py
src/opportunities/
旧 PEMIS Opportunity 数据与评分
现有 Vault / scheduler / feedback 路径
```

然后让机会对象进入已经验收通过的 Source + Work Fact + Evidence 基础设施，再开发 Opportunity Center。

详细未来需求只记录在 `docs/MODULES/FUTURE_DEVELOPMENT_TODO.md`。

## 8. 已确认稳定项，不要重复返工

除非新的回归证据表明失败，否则不要把主要时间重新消耗在：

- 产品 / Artifact 精确身份机制；
- Apple Silicon arm64；
- strict codesign；
- whole-bundle replace；
- Acceptance / Production 物理隔离原则；
- Secret export 边界；
- exact-instance Runtime stop 原则；
- 记忆分页终点规则；
- 高级技术信息下沉原则。

这些仍需随相关变化回归，但不是当前产品主矛盾。

## 9. 技术边界保持不变

- `src/` 为长期平台主线；
- `desktop/lingji-control/` 为唯一正式 Desktop UI；
- `second_brain/` 只做兼容、迁移和验收来源；
- Desktop 只通过认证的 `127.0.0.1:8766`；
- Obsidian Vault + Git 为永久记忆正文权威；
- SQLite / Qdrant 为运行状态或可重建派生层；
- Acceptance / Production 必须物理隔离；
- AI 不自动批准永久记忆；
- 不自动破坏性 rebuild Qdrant；
- 不建立第二事实源来美化 UI。

## 10. 历史失败 Artifact

以下均永久 `DO NOT RETRY`：

```text
9258682849 / bd1e7a17
9250384637 / 1d99d10c
9249367672 / f3cba413
9224368022 / 2c96b3ec
9102748834 / 171091fe
```

当前没有 ACTIVE 本机验收任务。旧 Artifact 不得因为仍可下载而重跑。
