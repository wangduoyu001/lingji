# PROJECT_STATUS.md — LingJi 当前状态

> Updated: 2026-08-26
> Formal/default branch: `master`
> Product-code baseline before documentation cleanup: `3d7225f58fb5b5a9b035cfd72f92cb2267b48559`
> Current audited master Head: `ced1128e50d3b3758585573042ea6bcc6f315384`
> Last owner acceptance closeout: `e594e3f05e8726cbae7b0a590e6f515fb2cc67c5`
> Last rejected product candidate: `bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9`
> Current product phase: `PHASE 1 — SECOND BRAIN COMPLETION`
> Current engineering gate: `TASK 0 — AUTOMATIC MEMORY CONTRACT (DOCS-ONLY)`
> Opportunity Center: `FROZEN UNTIL PHASE 1 FINAL PASS`
> Architecture: `docs/ARCHITECTURE.md`
> Code entry points: `docs/MODULES/CODE_MAP.md`
> Future backlog: `docs/MODULES/FUTURE_DEVELOPMENT_TODO.md`
> Acceptance authority: `docs/ACCEPTANCE/README.md`

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

## 1A. Task 0 当前范围与真实进度

当前分支 `codex/phase1-automatic-memory` 只封板自动化第二大脑的研究结论、架构边界、开发计划和验收规则。Task 0 是 **docs-only**：不修改产品代码、测试代码或依赖文件，不创建真实验收 Artifact，不激活本机任务单，不读取 Production/Vault 正文，也不宣称任何新自动记忆能力已经实现。

已完成的 Task 0 证据是：隔离工作树从精确基准 `d12c1fb837257e83835a7cdb899bb29a9c675c3d` 创建；研究结论保存在 gitignored `.research/`；`.venv` focused 基线为 38 项收集、37 passed、1 skipped；当前 `LOCAL_EXECUTION_TASK.md` 仍为 `IDLE`。产品实现从 Task 1 开始，必须逐项通过 focused 测试和对应验收同步。

## 1B. 自动化第二大脑的锁定方向

Phase 1 的自动化第二大脑目标是：一次中文主人授权后，在明确 allowlist 内自动发现并持续接管官方支持或明确授权的 AI 记录，保存完整本地原始证据、来源链和可重建 RAG 投影，并在 Desktop 真实显示发现、处理、结果、失败、下一动作与执行者。

强制边界：ChatGPT 只接受官方导出；Codex transcript 必须 schema-detect 并对未知结构 fail-closed；Claude Desktop 不抓不透明内部存储，无官方导出时显示 `unsupported` 或 `consent_required`；禁止 Cookie、Token、凭证、浏览器资料、私有 DB、进程注入、应用目录写入、全盘扫描和网络上传。Obsidian 仅允许 `_LingJi/Memory Inbox`、`_LingJi/Memory Library` 或 `lingji_memory: true`，`lingji_memory: false` 最高优先级。

所有聊天先进入原始证据和可检索层。低风险、高置信、无冲突且置信度 `>= 0.90` 的 derived current memory 可以自动激活，但只是可重建投影；Core、身份、高风险和正式永久知识仍需主人明确确认。`superseded`、`invalidated`、`archived` 历史保留审计，但 current lexical/Qdrant/hybrid/Core/ContextPack/MCP 默认排除。Opportunity Center 在 Phase 1 PASS 前保持冻结。

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

### 4.1 已经存在的基础

当前 `master` 已有：

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

### 4.2 当前 P0 工程阻塞：Work Fact 已部分修复，但尚未成为正式产品链

截至 `ced1128e...`，SB-0 不能再描述为“完全未开始”，但也不能描述为“已经接通”。准确状态是：

| 子项 | 状态 | 当前事实 |
|---|---|---|
| Work persistence | `IMPLEMENTED_NOT_TESTED` | `WorkStore` 已能写入并读取 WorkItem、Event、PendingAction；Outcome 仅有写入 |
| Capture bridge contract | `IMPLEMENTED_NOT_TESTED` | `create_from_capture()` 已改用正式 `create_work()` |
| Projection reads | `IMPLEMENTED_NOT_TESTED` | `WorkProjector` 所需的 work/event/pending 读取方法已存在 |
| Control adapter | `IMPLEMENTED_NOT_TESTED` | `WorkControlService` 已按 Store → Projector 接线 |
| 合同测试文件 | `ADDED_NOT_RUN` | 已新增 store、capture bridge、control service、control contract 四个测试文件 |
| 正式 8766 路由 | `PENDING` | `create_control_app()` 尚未注册 `src/control/work_routes.py` |
| 正式 Service 共享接入 | `PENDING` | `LocalControlService` 尚未共享 `WorkControlService` / 同一 WorkStore |
| Python ↔ Desktop 合同 | `PENDING` | ID、状态、事件、PendingAction 与响应外壳不一致 |
| Outcome / NextAction / Memory 投影 | `PENDING` | 还没有完整读取、API 和跨页投影 |
| 自动与主人验收 | `NOT_RUN` | focused、full、release、发布版 UI 和主人确认均未完成 |

现有四个测试文件只证明合同测试代码已经加入仓库。其中 `tests/test_work_control_api.py` 当前验证的是 Control service 返回结构，不是正式 FastAPI 路由注册测试。

当前必须先完成：

1. 把 `/api/work/*` 注册到正式、认证的 `create_control_app()` 8766 路径；
2. 让 `LocalControlService`、Work service、projector 和 Capture 共享同一正式 Store；
3. 统一 Python DTO、API 响应与 TypeScript Work Fact 合同；
4. 补齐 Outcome、NextAction、PendingAction 与 Memory/Failure 的读取和投影；
5. 增加真正的 API、Projector、Desktop smoke 和端到端测试并实际执行；
6. 证明 Capture 成功后能以同一 `work_id` 查询事件、结果和下一 actor。

在以上门禁通过前，**禁止继续以视觉扩展为主的 UI 开发。**

## 5. Phase 1 重新规划后的开发顺序

### 5.0 Automatic Memory Tasks 1–11（Task 0 封板后按依赖顺序执行）

以下是自动化第二大脑的独立审查顺序；当前全部为 `PLANNED`，不代表代码已存在：

| Task | 交付边界 | 当前状态 |
|---|---|---|
| 1 | 来源注册、一次性中文授权、扫描状态与认证 8766 API | `PLANNED` |
| 2 | 一致快照、SHA-256 幂等、checkpoint/lease/retry/续扫 | `PLANNED` |
| 3 | macOS ChatGPT/Codex/Claude/generic JSON/JSONL/Markdown adapters | `PLANNED` |
| 4 | `watchfiles==1.2.0`、5 秒防抖、15 分钟 reconciliation、每日完整性、持久 scheduler | `PLANNED` |
| 5 | Obsidian 隔离、dry-run manifest、派生索引迁移与 rollback | `PLANNED` |
| 6 | derived current-memory promotion 与 Core/owner review 边界 | `PLANNED` |
| 7 | lexical/Qdrant/hybrid/Core/ContextPack/MemoryGateway/MCP 全链路 temporal filter | `PLANNED` |
| 8 | 中文 onboarding、authorize/revoke/scan/pause/retry、Work Fact、Python/TS DTO、Desktop | `PLANNED` |
| 9 | 现有 RAG/ContextPack/MCP 扩展与独立 100 问质量评测 | `PLANNED` |
| 10 | macOS M5 release、owner acceptance、UI 保持打开与报告 | `PLANNED` |
| 11 | macOS PASS 后的 Windows parity、PowerShell 5.1 与 release | `PLANNED` |

全局验收数值固定为：增量 30 秒内进入队列；自动记忆置信度 `>= 0.90`；`quality_score >= 90%`、`source_accuracy >= 95%`、`false_positive_rate <= 5%`、Codex MCP 真实成功率 `>= 95%`、重复正式内容 `0`、Production 污染 `0`、人工审核链 `100%`、重启恢复 `100%`。Task 4 才允许引入 watcher 依赖；Task 0 不引入依赖。

### SB-0 — Work Fact Contract Repair

目标：先让事实链真的能读写和通过 8766。

完成条件：

- Domain / SQLite / Service / API / TypeScript 合同一致；
- `/api/work/current`、timeline、pending 等正式接口可运行；
- 一条测试 WorkItem 可持久化、读取、投影；
- focused tests 覆盖正常、空状态、失败状态和重启后读取。

当前进度：**部分实现，未验证**。Store、Capture bridge、Projection read 与 Control adapter 已进入 `master`；正式 API 注册、Service 共享接入、Desktop 合同、Outcome/NextAction 和实际测试执行仍未完成。

### SB-1 — Capture → Work → Outcome 闭环

目标：所有主人输入都能追踪。

优先验证 `Cmd+K` 文本“记住”路径，再覆盖 web / file / supported media 等已有 Capture 类型。

完成条件：

```text
Capture accepted
-> WorkItem created
-> processing events
-> extraction result
-> Outcome success/failure
-> next actor
```

不得出现“提交成功但没有工作对象”。

### SB-2 — Work → Memory / Evidence 闭环

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
