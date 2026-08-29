# PROJECT_STATUS.md — LingJi 当前状态

> Updated: 2026-08-28
> Formal/default branch: `master`
> Phase 1 implementation base: `d12c1fb837257e83835a7cdb899bb29a9c675c3d`
> Current Phase 1 product head: `b43401c2f241820e6ebf5d89b31dad8638224751` (Task 7M-Reset product/tests)
> Current implementation branch: `codex/phase1-automatic-memory`
> Last owner acceptance closeout: `e594e3f05e8726cbae7b0a590e6f515fb2cc67c5`
> Last rejected product candidate: `bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9`
> Current product phase: `PHASE 1 — SECOND BRAIN COMPLETION`
> Current engineering gate: `TASK 7 — MEASUREMENT CONTRACT CAP / BLOCKED`
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

## 1A. 当前实现范围与真实进度

当前分支 `codex/phase1-automatic-memory` 已完成并冻结 Tasks 0–6 的自动化/UI 交付边界；Task 7 的质量测量组合仍被证据契约门禁阻塞。已有来源授权与扫描状态、一致快照/续扫、受支持来源适配、监听与调度、Obsidian 隔离、派生记忆晋级，以及全检索路径的 current/as_of/history/why 时态隔离。Task 8 的 Work Fact、8766 读取接口和 Desktop 真实投影已进入分支，但发布版与主人验收仍未进行。

此前唯一已复现的 P0 缺口是：一次终态失败已经产生主人待办后，实时生命周期 callback 随即成功时，成功 Outcome 会立即写入，但旧 PendingAction 要等后续 `WorkStore` 重放/读取才被解决。Task 1 已通过单一事务转换和 callback/replay/restart/乱序矩阵修复并回归验证；剩余执行权威为 `docs/superpowers/plans/2026-08-26-phase1-automatic-memory-followup.md`。

当前 `LOCAL_EXECUTION_TASK.md` 仍为 `IDLE`。在 Work Fact 收口、固定 100 问评测、统一 RAG、质量/规模门禁和同 SHA Artifact 锁定之前，不执行新的真实安装或 M5 主人验收。

Task 3 Repair Round 1 已在本分支产品提交 `f2f7312` 完成八项重要缺口修复；最终 Repair Round 2 产品提交 `7058da0` 补齐 BOM/CRLF frontmatter、自动 Generic AI 跨来源身份命名空间和暂停恢复 Work Fact 计数。该状态仅表示代码与合成 fixture 验证通过；不表示 Artifact、真实 UI、主人观察或 Production/Vault 验收完成。Task 2 的 stale scheduler cleanup-state 边界已由 Task 6A 产品/测试提交 `15eb4433c9d6c3ba218e89d50bec84987ad35915` 收口；自动晋级 seam 仍禁止调用。

Task 4C 已完成一个有界的 Home 事实显示收口：在不改后端的前提下，首页现在明确显示本次更新、本次跳过；后端缺失时保持“尚未获得”，未知队列活动不再伪装为“后台自动运行”。产品/测试提交为 `4aa0b7841dab76fed5c784008c2449808e3648f2`，它只表示确定性 UI/build/E2E 证据通过，不表示真实 8766、Artifact、主人观察或发布验收通过。该收口依据 Task 4 最终审查 `f3d70084e8dfb8a07e2fe46f7e1008e11cdf7c2d`，不扩大到后端、CurrentWorkPanel 或新功能。

Task 5A 已完成 Owner Work API 基础收口（代码/测试已通过 focused 验证，等待独立审查）：复用现有 `WorkStore` 与认证 8766，提供有界工作历史分页、重启可恢复的按时间线读取，以及按稳定 `action_id` 幂等解决主人待办。当前不代表 UI、真实 8766、Artifact、Production/Vault 或主人验收完成。

Task 5A Repair Round 1 已完成最后授权修复，等待独立终审：解决主人待办后不再残留旧的主人下一步，且不会删除更新的系统下一步；来源摘要来自现有工作标题并保留精确来源 ID 作为次要诊断。产品/测试提交为 `5e71cda68edfb86eac99804bc66fbfb6540bcb9c`，自动验证聚焦 40 passed、广义 Work/Task8/Capture/自动记忆回归 102 passed；不代表真实服务、UI、Artifact 或主人验收完成。

Task 5B UI 已完成本地 focused 实现：Activity 读取认证 `/api/work/history` 分页并以中文摘要为主，Attention 通过既有 resolve 路由完成真实待办，Memory Review/Inspector 显示现有字段可提供的可读 provenance 并保留真实检查入口，导航隐藏重复 legacy Capture，900px 与复制反馈有确定性覆盖。产品/测试与验收报告待独立审查；未启动 live 8766、Sidecar、Artifact，未访问 Production/Vault 或主人数据，`LOCAL_EXECUTION_TASK.md` 仍为 `IDLE`。

Task 5B final review disposition: ACCEPTED_FOR_TASK6 / ACCEPT_FOR_TASK6; final review commit `bd2ff43`, reviewed product head `8136374`, Critical=0, Important=0, Minor=3 non-blocking evidence gaps. No live 8766, Sidecar, Artifact, Production/Vault or owner data was run.

Task8E Safe Polling Fallback Repair Round 1 已完成代码与合成 fixture 验证：Darwin/macOS 在未显式配置时使用 `periodic_reconciliation`，不启动不可靠的 `watchfiles` event watcher；Windows 与其他平台默认保持 event watcher，显式配置仍可覆盖。现有启动增量扫描、15 分钟默认 reconciliation、每日 integrity、手动扫描、授权/revoke 和 pause/resume/restart 生命周期保持在同一 scheduler/registry。Runtime/API 暴露真实 reconciliation interval 与最大变化发现延迟，Desktop 根据字段显示定期核对文案；字段缺失时显示“尚未获得”。产品/测试提交为 `6862c46`、`eff22b4`、`cf09946102d89ddf67f3f69bae79f7bd45180dfe`，报告位于 `.superpowers/sdd/2026-08-29-task8e-safe-polling-fallback/task-report.md`。本 fallback 不满足 30 秒事件 SLA，只保证按配置周期自动核对（默认最迟 15 分钟）；Phase 1 自动接管门禁仍为 `BLOCKED`。未执行 live 8766/8767、打包、安装、Artifact、Production/Vault 或主人验收。

Task 6A Lifecycle Closeout: implementation/focused evidence `IMPLEMENTED_FOCUSED_PASS`; product/tests `15eb4433c9d6c3ba218e89d50bec84987ad35915`. A real watcher thread can remain `degraded/cleanup_pending` while alive, then a later retry after natural exit clears stale scheduler cleanup state and reaches `stopped`. Final review commit `22aae07be9accf7d56a4273e8d45a521b2323dab` accepted Task6A for Task6 composition. Task 6 packaged E2E is now the active code/evidence gate; release/Artifact/owner acceptance remain unclaimed.

Task 6A Repair Round 1（独立审查 `9ed229461165b748066b9cba3d2ed169af43db56`）已完成：产品/测试提交 `efde650e77a4ecda7f7266aefe48b29b9e8712de` 为唯一授权修复，按 watcher/Cron/source ownership 精确重试和清除 cleanup，且 start/stop 共用 lifecycle serialization。最终 review `22aae07be9accf7d56a4273e8d45a521b2323dab` accepted for Task6。Task 6 packaged E2E、release、Artifact 与主人验收仍未完成或授权。

Task 6 Repair Round 1（diagnostic review `361733b3c660e1b5dc36e5500e1f2436da41572e`）：产品/测试提交 `04eb1d3`、`b6e8c77`、`31f40a3` 已完成有界 durable scan/work identity 和 packaged evidence harness 修复。定向 regression 52 passed；单 root clean Acceptance raw evidence 已记录在唯一权威报告 `docs/TEST_REPORTS/PHASE1_AUTOMATION_UI_GATE.md`。Task6H 已在现有 StateDB/AutomaticMemoryScheduler/Cron loop 内加入 instance/generation 绑定的持久 heartbeat 与 active Work Fact 无事件刷新；Repair Round 1（审查 `8daf700f4dd5dbea90e32305a67c764420b147d7`）进一步保证 touch/write 失败按 source 隔离、持久 degraded/reason/error 与下一次成功自动恢复，focused `8 passed`。Task6 仍 `IN_PROGRESS / NOT_ACCEPTED`：packaged ingestion 不产生正式 lexical memory document（scenario 8 BLOCKED），crash 30/70 终态 identity matrix 仍待 Task6 外部 gate 收口。不得宣称 release、Artifact、主人或 Production/Vault 验收。

Task 6L Structured Evidence Lexical Wiring（Repair Round 1 已实现，待独立终审）：`StructuredReadModelSink` 现在在既有 `lingji_memory.db` 内，把非空 structured message rows 物化为可重建 `memory_type=structured_evidence` / `memory_tier=evidence` FTS 文档；文档保留 source/conversation/message 复合身份、role/order/content hash/raw/time provenance，不写 Obsidian、不创建 candidate/active memory、不调用 promotion seam。正式 Gateway/Hybrid/MCP/ContextPack 复用该 lexical projection，Qdrant/semantic 查询失败时保留 lexical hit 与 degraded diagnostics；普通 Obsidian rebuild 不会删除该投影，且可从 structured rows 单独 rebuild。Repair Round 1 的产品/测试提交为 `5258ecef98e2b58dfb9c12af585a4fbd44c260dd`：现有 SourceRegistry lifecycle listener 将 StateDB 的 revoke/expired/unsupported/degraded 状态 fail-closed 投影为 structured source/evidence archived，启动重启时重新投影；自动 Generic source identity 不再随 raw bytes 改变，内容更新幂等 upsert 同一 message evidence，raw citation、role、sequence 继续出现在正式 citation/ContextPack。Task6 主报告仍 `IN_PROGRESS / NOT_ACCEPTED`，等待 Task6H heartbeat、crash 最终门禁与独立终审。

Task 6S Query-Time Source Authority + Evidence Versions（Repair Round 1 已实现，待全新独立终审）：正式 Gateway composition 注入 `SourceAuthorityResolver`，current/why structured automatic evidence 每次查询批量读取现有 StateDB SourceRegistry authority；unknown、expired/revoked、StateDB unavailable/locked 一律 fail closed，普通非自动记忆不受影响。structured evidence 使用 `(source_id, conversation_id, message_id, content_hash)` 版本身份，旧 active 原子 supersede 并保留 history/as_of；same-byte replay 不改写，`ExtractionPipeline.replay_automatic_snapshots()` 按序重放正式 pipeline。Repair Round 1 product/tests 为 `9692cf7`，补齐 current/why cache re-check、read-model orphan archive、ContextPack linked-evidence authority guard。Task6 权威报告仍 `IN_PROGRESS / NOT_ACCEPTED`，不改变 Task6H/crash/live/Artifact/主人验收状态。

Task 6C Deterministic Crash-Recovery Receipt 已完成自动化收口：测试提交
`6eb469fefafe0a33e6ac65f765c7663741883811`，唯一权威报告已更新为
`PASS_AUTOMATED / READY_FOR_TASK7`。两次 fresh packaged gate 均为 `2 passed,
1 warning`（每次包含 30%/70% 两个 clean roots 与十场景）；四个真实 sidecar
PID crash receipts 均在 6/20 或 14/20 barrier 后由 startup reconciliation
恢复原 scan，终态 20/20 completed、jobs 20、duplicates 0、fallback false。
Task6S lexical/Qdrant 与 Task6H heartbeat age `<=10s` 纳入并通过 packaged
flow；focused scheduler/checkpoint/lease/cron/startup 回归 `155 passed, 2
warnings`，Desktop/build/rendered E2E、compile/diff/sync/handoff 通过。该结论
仅是临时 Acceptance 自动证据，不是 release、Artifact、live 8766/8767、
Production/Vault 或 owner PASS；fresh security review 仍待执行。

Task 6C Repair Round 1 fresh review 已将上述历史 PASS 置为 superseded：真实
crash/recovery/stop 后仍残留 `.automatic-memory-*.json` transient marker，违反
I1 terminal/stop cleanup receipt。现有 harness 修补未提交并已恢复至
`6eb469f`；该项需要最小产品 cleanup 授权，当前 Task6 保持
`IN_PROGRESS / NOT_ACCEPTED`，不得宣称 READY_FOR_TASK7。

Task 6M 已在产品/测试提交 `1901628eee197e3d71d7e070c41c9e586d5468de` 完成有界
transient lifecycle 修复：adapter dispatch 硬链接现在携带受限的现有 queue
`job_id + lease_token`，启动、worker process/stop reconciliation 只处理 raw root
直接子 regular file，并将 terminal、释放、过期或可证明死亡的本机 worker marker
清理；活跃 lease、未知/畸形/foreign、symlink、目录保留。清理 inventory 复用现有
pipeline/worker/runtime status 暴露，unlink 失败可重试且不伪报成功。Task6M focused
用例 `8 passed`，runtime receipt 断言纳入回归后受影响回归 `150 passed, 3 warnings`；Task 6 总状态仍
`IN_PROGRESS / NOT_ACCEPTED`，未执行 live/Artifact/release/主人验收。

## 1B. 自动化第二大脑的锁定方向

Phase 1 的自动化第二大脑目标是：一次中文主人授权后，在明确 allowlist 内自动发现并持续接管官方支持或明确授权的 AI 记录，保存完整本地原始证据、来源链和可重建 RAG 投影，并在 Desktop 真实显示发现、处理、结果、失败、下一动作与执行者。

强制边界：ChatGPT 只接受官方导出；Codex transcript 必须 schema-detect 并对未知结构 fail-closed；Claude Desktop 不抓不透明内部存储，无官方导出时显示 `unsupported` 或 `consent_required`；禁止 Cookie、Token、凭证、浏览器资料、私有 DB、进程注入、应用目录写入、全盘扫描和网络上传。Obsidian 仅允许 `_LingJi/Memory Inbox`、`_LingJi/Memory Library` 或 `lingji_memory: true`，`lingji_memory: false` 最高优先级。

所有聊天先进入原始证据和可检索层。Automatic archival and candidate generation continue; automatic activation is quarantined; owner approval is required until a future independently approved recovery gate exists. Derived current memory 仍只是可重建投影；Core、身份、高风险和正式永久知识仍需主人明确确认。`superseded`、`invalidated`、`archived` 历史保留审计，但 current lexical/Qdrant/hybrid/Core/ContextPack/MCP 默认排除。Opportunity Center 在 Phase 1 PASS 前保持冻结。

此前 Task7 测量 runner 的原始 100 问结果仅作历史基线保留；Task7M-Reset 已重置其证据组合。当前质量 runner 只在带精确 lease token/owner 校验的临时 Acceptance roots 编排现有导入、Work/Memory/Gateway contracts；不可用证据保持 nullable/`NOT_MEASURED`，不进入 `EvaluationReport`，实测失败保持 `FAIL`，清理失败覆盖预清理结论并由 CLI 复核完整清理库存。release、100k、Artifact、Production/Vault 和主人验收保持未执行，Task8 不得开始。

Task7 Measurement Repair 已完成有界测量架构修复但未通过质量门禁：生产污染保持
`null/NOT_MEASURED`，Acceptance protected boundary 单独记录；两个真实授权临时来源
执行损坏隔离并得到 `attempted=2/completed=1/failed=1/continued=1/retrievable=1`；
MCP strict parity、选择前 baseline、清理前后机器库存与持久 4R2 readiness 均已接入。
修复后原始质量仍为 `FAIL`（事实召回 0/106、引用 0/106、strict MCP 0/100，baseline
因无完整选择前会话而 NOT_MEASURED），因此 100k/release/Artifact/Production/Vault/
主人验收仍未执行。当前状态是 `MEASUREMENT_NOT_ACCEPTED`，等待独立审查；不得把修复
误报为质量通过或进入 Task8。

Task7M-Reset 已完成新的运行证据组合（代码/测试待独立审查）：corruption 使用两个真实
授权来源的正式 scan→queue→worker→Work Fact→read-model 路径；ContextPack 提供与正式
构建共用的选择前只读观测；MCP 空包、身份/边界错配和严格 100/100 准入均 fail-closed；
scale envelope 校验 run identity、fixture、verdict、测量字段和 readiness 一致性，并允许
Production nullable 时仅以功能质量准入 scale。当前 CLI 实测仍为 `FAIL`，MCP `0/100`、
baseline `NOT_MEASURED`，未运行 100k/release/Artifact/主人验收；需要独立审查为零
Critical/Important 后才可进入一次有界 retrieval 诊断。

Task7O 最终独立审查（报告提交 `ce9807adb8aa9f4997819105ff3f1a949d93105b`）结论为
`BLOCKED_AT_MEASUREMENT_CAP / NO_DIAGNOSTIC`，发现 1 个 Critical、3 个 Important：
canonical loader 可接受未知顶层字段并忽略 duplicate evidence detail 冲突，promotion
测量过滤非候选 orphan link，缺失 memory identity 可被判为 ready，activation quarantine
未验证 actual/reason/category。故当前 Task7 measurement 仍未接受；raw facts/citations/
MCP 均为 0，但不能把这些数字当作最终产品 retrieval 诊断。Tasks 2–6 的自动化/UI
接受状态不回退；未运行 100k、release、Mac、owner 或真实数据验收，Task8 不得开始。

Task7E 的 PowerShell executable-entry 证据已通过真实 Windows runner 取得：现有
`p0-windows-gate.yml` 的 full pytest artifact 在 `33153622216` 明确记录真实
`scripts/validate.ps1` 调用成功进入、非零阻断和 `preflight` 唯一 hook；因此
`scale-env=0`、`scale-command=0`。P0 总体仍因既有 Windows full 测试和 Desktop
smoke 失败，不能视为 release、4R2、100k 或 Phase 1 通过；Task7 的正式质量评测
已记录为 `FAIL_MEASURED_QUALITY`，首个既有边界为 retrieval/structured-evidence 事实绑定不足。

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

### 4.2 当前 P0 工程阻塞：Work Fact 收口已实现，等待独立审查与后续门禁

截至 `8f2267d...`，准确状态是：

| 子项 | 状态 | 当前事实 |
|---|---|---|
| Work persistence / projector | `IMPLEMENTED_FOCUSED_PASS` | WorkItem、Event、Outcome、Failure、NextAction、PendingAction 可重启读取；稳定 ID 重放幂等；事件候选按 UTC instant/phase rank/stable ID 选择 |
| Capture / extraction bridge | `IMPLEMENTED_FOCUSED_PASS` | 单一 `apply_extraction_transition` 事务统一成功、失败、重试、direct execute、callback/replay/restart；即时失败→成功在任何 projector/replay 前解决旧待办 |
| 正式 8766 路由 | `IMPLEMENTED_FOCUSED_PASS` | `/api/work/current`、pending-actions、timeline 已注册在既有认证 8766 服务 |
| Python ↔ Desktop 合同 | `IMPLEMENTED_FOCUSED_PASS` | Overview、Activity、Attention 使用同一 Work Fact DTO/API；静态假数据已移除 |
| Task 8 独立审查 | `PENDING_INDEPENDENT_REVIEW` | follow-up Task 1 产品 Commit `31a14a4` 完成 review round 1 修复；需独立 Luna 复审确认无 Critical/Important 问题 |
| 发布版与主人验收 | `NOT_RUN` | 当前任务单 IDLE；未创建或重跑任何 Artifact |

当前必须先完成一个明确门禁：独立审查确认 `2f833aa` 的 callback/replay/restart/重复/乱序矩阵及指定回归，再调度固定 100 问评测；在此之前不调度 RAG，也不继续视觉扩展。

Task 4 Product Landing UI 已接入 Desktop：新增“记忆来源”观察页与一次性后端事实 onboarding，使用既有认证 8766 discovered/sources/scans/summary/runtime 读写接口；Home 现在投影来源、活动、本次扫描计数与记忆状态。原产品 `2dc03e6` 经独立审查 `44b00d3` 与 Round 2 审查 `d5f902a` 后，最终修复产品 `b45b1dd7bf860510473f49388b8424d62de9f787` 已补齐长时 capped-backoff 重试/断连重置、真实 outage/recovery 与 delayed-navigation race、精确授权证据、撤销重授权、九态渲染覆盖、暂停文案、post-action snapshot、polling late-error 与 token 回归。契约 smoke、Playwright/系统 Chrome 渲染 harness、TypeScript build 已通过；真实打包版与主人验收仍未执行。

## 5. Phase 1 重新规划后的开发顺序

### 5.0 Automatic Memory Tasks 1–11（Task 0 封板后按依赖顺序执行）

以下是自动化第二大脑的独立审查顺序；详细剩余执行拆分见 follow-up 计划：

| Task | 交付边界 | 当前状态 |
|---|---|---|
| 1 | 来源注册、一次性中文授权、扫描状态与认证 8766 API | `FROZEN / REVIEW PASS` |
| 2 | 一致快照、SHA-256 幂等、checkpoint/lease/retry/续扫 | `FROZEN / FINAL REVIEW PASS` |
| 3 | macOS ChatGPT/Codex/Claude/generic JSON/JSONL/Markdown adapters | `FROZEN / REVIEW PASS` |
| 4 | `watchfiles==1.2.0`、5 秒防抖、15 分钟 reconciliation、每日完整性、持久 scheduler | `FROZEN / REVIEW PASS` |
| 5 | Obsidian 隔离、dry-run manifest、派生索引迁移与 rollback | `FROZEN / REVIEW PASS` |
| 6 | derived current-memory promotion 与 Core/owner review 边界 | `FROZEN / OWNER-REVIEW QUARANTINED` |
| 7 | lexical/Qdrant/hybrid/Core/ContextPack/MemoryGateway/MCP 全链路 temporal filter | `FROZEN / REVIEW PASS` |
| 8 | Work Fact、Python/TS DTO、8766、Desktop 与提取生命周期 | `IMPLEMENTED / TASK 1 REVIEW ROUND 1 PENDING` |
| 9 | 固定 100 问评测、统一 RAG/ContextPack/MCP、质量与规模门禁 | `PLANNED AFTER TASK 8` |
| 10 | macOS M5 release、owner acceptance、UI 保持打开与报告 | `PLANNED AFTER QUALITY PASS` |
| 11 | macOS PASS 后的 Windows parity、PowerShell 5.1 与 release | `BLOCKED BY MAC PASS` |

全局验收数值固定为：增量 30 秒内进入队列；自动记忆置信度 `>= 0.90`；`quality_score >= 90%`、`source_accuracy >= 95%`、`false_positive_rate <= 5%`、Codex MCP 真实成功率 `>= 95%`、重复正式内容 `0`、Production 污染 `0`、人工审核链 `100%`、重启恢复 `100%`。Task 4 才允许引入 watcher 依赖；Task 0 不引入依赖。

### SB-0 — Work Fact Contract Repair

目标：先让事实链真的能读写和通过 8766。

完成条件：

- Domain / SQLite / Service / API / TypeScript 合同一致；
- `/api/work/current`、timeline、pending 等正式接口可运行；
- 一条测试 WorkItem 可持久化、读取、投影；
- focused tests 覆盖正常、空状态、失败状态和重启后读取。

当前进度：**产品链已实现并通过 focused/独立审查的大部分门禁，剩余一个 load-bearing 一致性问题**。callback 与 replay 的终态写入仍是两套代码；失败后立即成功时旧主人待办不能在同一调用内清除。follow-up Task 1 必须先统一状态转换并通过完整矩阵，才能把 SB-0 标为完成。

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
Task 6M 独立审查（当前 disposition）：报告
`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6m-review.md` 在审查
HEAD `b65f81d659f787e349d545f51c4ddb94af770d4b` 给出 `Spec Compliance FAIL /
Task Quality NEEDS_FIXES`，Critical=0、Important=5、Minor=2。旧版
`.automatic-memory-{uuid}.json` 残留没有兼容回收；lease mismatch 与 queue/DB
error 未完全 fail-closed/可观察，且 cleanup inventory 尚未由 Desktop 消费；修复后 packaged 30/70 crash/restart/stop 尚未
fresh 复验。已授权且最多一轮 `REPAIR_ROUND_1`；Task6 继续
`IN_PROGRESS / NOT_ACCEPTED`，不得标记 `Task6M ACCEPTED_FOR_FINAL_VALIDATION`。

Task 6M Repair Round 1 已在独立审查 `b65f81d659f787e349d545f51c4ddb94af770d4b`
后完成，产品/测试提交 `4b51392fe448472e9099978ff2528f742dff887b`。仅关闭
I1/I2/I3/I5 与 M1/M2：legacy marker 需 exact grammar + 同目录 content-addressed
raw 的 dev/ino/size hard-link 证明；v1 terminal/released/expired/dead cleanup
需 queue input_path/raw/job identity 证明；queue/SQLite/stat/unlink 异常 fail-closed
并进入既有 runtime cleanup receipt；unlink 前 lstat 变化保留；Desktop 现消费
`cleanup_pending/cleanup_error` 并显示不含路径、job、lease 的中文可重试提示。
focused lifecycle/runtime `31 passed, 1 warning`，受影响回归 `250 passed,
3 warnings`，Desktop source smoke/build PASS。I4 fresh packaged 30/70 明确延期至
全新 Task6V；Task6 仍 `IN_PROGRESS / NOT_ACCEPTED`，不得宣称最终验收、live、
Artifact、Production/Vault 或主人 PASS。
Task 6M Repair Round 1 final independent review (2026-08-28)：报告
`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6m-final-review.md` 针对 docs HEAD
`28f798557459b7cd7a1187d462969e43c871450a` 与产品/测试 `4b51392fe448472e9099978ff2528f742dff887b`
给出 `FAIL / BLOCKED_AT_REPAIR_CAP`，Critical=0、Important=2、Minor=2。terminal/queued/retrying
的 WRONG lease marker 仍可被删除，raw-root scan error 仍有未捕获异常与未脱敏 receipt；其余
legacy proof、正常 finally、inline SIGKILL/restart、lstat guard 与有界 UI 实现已复核。I4
packaged 30/70 延期至 Task6V，不计为本轮产品失败；Task 6M 保持 `NOT_ACCEPTED`，Task6 保持
`IN_PROGRESS / NOT_ACCEPTED`，不再授权本轮修复。

Task 6L Durable Lease Ownership Receipt 已完成有界架构补齐（产品/测试
`4fd2386`, `382091b`）：在现有 `extraction_jobs` 增加 nullable
`last_claim_lease_fingerprint`，claim 同事务写入 SHA-256 lease receipt，终态与
release 清当前 lease 但保留最近 claim 指纹，retry/force generation reset 清除旧指纹。
v1 transient marker 现在必须同时满足 marker lease hash、durable ownership、raw
hard-link identity；running 还须 current lease 匹配，NULL/wrong-generation/foreign
marker fail closed。reconcile 的 root/iterdir/lstat/raw-hash/queue/unlink 异常只输出
allowlist code，不带 path/job/lease/token；现有 pipeline/worker/runtime cleanup
pending retry 与 public queue/service/MCP DTO 脱敏保持。Task6L focused `11 passed`，
相关 backend regression `218 passed, 2 warnings`，Desktop static/build/rendered cleanup
notice recovery 通过。Task6M 历史 `FAIL / BLOCKED_AT_REPAIR_CAP` 不改写；Task6 仍
`IN_PROGRESS / NOT_ACCEPTED`，Task6V fresh packaged 30/70、live/Artifact/Production/
Vault/owner acceptance 均未执行。

Task 6L independent review (2026-08-28)：报告
`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6l-review.md` 审查
`880bd8c1beeddfda0b0c76752038ca7da521adfe`（产品/测试 `4fd2386`、`382091b`）结论为
`FAIL / NEEDS_FIXES`，Critical=0、Important=1、Minor=0。现有 focused/regression
`218 passed, 2 warnings`，Desktop static/build/rendered、compile、diff、sync、handoff
均通过；但普通低层 queue `get/list` 及等价 raw read 仍返回 plaintext
`lease_token` 与 `last_claim_lease_fingerprint`，不满足 Task6L 明确的普通 queue read
脱敏边界。Task6L 保持 `NOT_ACCEPTED`，仅授权一轮有界 Repair Round 1；Task6M 历史
`FAIL / BLOCKED_AT_REPAIR_CAP` 不变，Task6 仍 `IN_PROGRESS / NOT_ACCEPTED`。

Task 6L Repair Round 1 已按 review record `9edb9eab98b5abf58999b0e16d09ece729c2e45e`
（reviewed product baseline `880bd8c1beeddfda0b0c76752038ca7da521adfe`）只修复 I1：
产品/测试 commit `2daac07` 将普通 queue `get/list/list_page/get_by_idempotency_key`
及 Control/MCP projection 递归脱敏 lease token/fingerprint，并提供仅内部使用的
`_get_claimed_job_internal()` 当前 lease seam；durable fingerprint 继续只经
`ownership_receipt()` 布尔谓词参与 ownership。新增 RED 后 repair focused `34 passed`，
required backend matrix `219 passed, 2 warnings`；Desktop static/build/rendered、
compile、diff 均通过。Task6L 等待新鲜独立复审，仍 `NOT_ACCEPTED`；Task6M 历史
`FAIL / BLOCKED_AT_REPAIR_CAP` 不改写，Task6 仍 `IN_PROGRESS / NOT_ACCEPTED`，Task6V
packaged 30/70、live/Artifact/Production/Vault/owner acceptance 均未执行。

Task 6L Repair Round 1 final independent review (2026-08-28)：报告
`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6l-final-review.md`
审查 HEAD `d328e58926e0466a912bde8c73fbaa5f64633cf5`、repair 产品/测试
`2daac0733495798f3e576363a885c28e8c4ce392`，结论为 `FAIL /
BLOCKED_AT_REPAIR_CAP`，Critical=0、Important=1、Minor=0。Fresh required
backend matrix `219 passed, 2 warnings`，Task6L focused `12 passed`；Desktop
static/build/rendered、compile、diff、acceptance sync、local handoff 均通过。
修复后普通 queue projection 的 lease 字段名已递归移除，claim 仅由
pipeline 内部调用且没有 Control/MCP 直出；但 complete/fail 清除当前 token
后，任意嵌套 result 字符串及 `last_error` 仍可能原样保留旧 plaintext
lease token，故 I1 仍阻塞 Task6L。Task6L 保持 `NOT_ACCEPTED`，Task6 保持
`IN_PROGRESS / NOT_ACCEPTED`；Task6M 历史 `FAIL / BLOCKED_AT_REPAIR_CAP`
不改写，Task6V packaged 30/70、live/Artifact/Production/Vault/owner
acceptance 均未执行。

Task 6P Queue Persistence Lease Redaction（新有界任务）：针对 Task6L final review
I1 的 terminal `result`/`last_error` 旧 lease plaintext，现有 queue 持久化边界新增
递归、循环/深度/节点/字符串有界 scrubber。complete/fail/cancel-running 在清 current
lease 的同一事务先 scrub，enqueue/force payload/options 复用；ordinary queue reads、
Control/MCP/process summary、lifecycle callback 和 extraction 错误日志均不重新暴露
lease material。private worker seam、`ownership_receipt()` durable fingerprint、
Task6L/Task6M 历史保持不变。RED `3 failed`、Task6P focused `5 passed`，受影响
queue/worker/pipeline 回归 `77 passed, 2 warnings`；扩大 Task6L/M/P、runtime、Control/MCP、
structured、Work 矩阵为 `241 passed, 2 warnings`。Desktop memory source static/build/
rendered checks pass；compile、diff-check、acceptance sync、local handoff pass。Task6 仍
`IN_PROGRESS / NOT_ACCEPTED`，Task6V packaged 30/70、live/Artifact/Production/Vault/
owner acceptance 未执行。

Task 6P Repair Round 1（review `d61acdf39eefca8870b46b7a3172fe8ce20d5d6f`）仅修复
lifecycle callback I1：现有 `_notify_lifecycle` 对 callback job/result/error 统一使用
bounded scrubber，callback 接收安全 projection；claimed private job 仍只供 worker
complete/fail/heartbeat 使用。普通、automatic、direct execute success/failure 及
custom-object fail-closed 均有回归，业务 terminal commit 不因观察回调失败回滚。
Task6 仍 `IN_PROGRESS / NOT_ACCEPTED`；Task6L/M 历史 `FAIL / BLOCKED_AT_REPAIR_CAP`
与 Task6V/live/Artifact/Production/Vault/owner 边界保持不变。

Task 6P Repair Round 1 产品/tests commit `924ac0c433a5d1029cce456cec1e6f24ef7dc7ba`
已完成：Task6P focused `10 passed`；expanded fresh matrix 原始结果为 `354 passed,
2 failed`，两项均为既有 structured-evidence fixture 缺少 `vault_path`，排除后为
`354 passed, 2 deselected, 6 warnings`。Desktop source/repair/build/rendered、
compileall、diff-check、acceptance sync、local handoff 均通过。Task6P 等待新鲜独立
复审，Task6 仍 `IN_PROGRESS / NOT_ACCEPTED`，不改变 Task6L/M blocked 历史或 Task6V
外部验收边界。

Task 6P Repair Round 1 final independent review (2026-08-28)：报告
`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6p-final-review.md` 审查
tree `33f6ffa407badda2531228a651aea6762dd4cfac` 与 repair product/tests
`924ac0c433a5d1029cce456cec1e6f24ef7dc7ba`，结论为 `FAIL /
BLOCKED_AT_REPAIR_CAP`，Critical=0、Important=1、Minor=0。Fresh focused
`10 passed`，affected backend `266 passed, 7 warnings`；完整无筛选 pytest 为
`1359 passed, 11 skipped, 7 failed`。两项既有 `structured_evidence_lexical`
`vault_path` failures 在 repair tree 与 base `d61acdf` 均独立复现，未被
deselect。Desktop source/repair/build/rendered、compile、diff、acceptance sync、
local handoff 均通过。I1：scrubber 收集任意显式 lease-key 字符串且不限制值大小/数量，
随后全局替换 callback 正文；`lease_token: "a"` 会破坏普通正文，违反 ordinary
text 与合理边界要求。Task6P 与 Task6 继续 `NOT_ACCEPTED` / `IN_PROGRESS`；Task6L/M
历史 blocked 结论及 Task6V/live/Artifact/Production/Vault/owner 边界不改写。

Task 6Q Trusted Lifecycle Projection Correctness 已在产品/测试 commit
`de412d52df3478c9cfa09b11572cb3841095d897` 收口该 I1：callback projection 的
`_notify_lifecycle()` 只接受内部 claim 调用链显式提供、严格验证的 32hex lease token
及对应 64hex fingerprint（最多两项），不再从 payload/result/error 显式敏感键值派生
replacement。direct execute 的 trusted list 为空，仅递归移除 allowlist 敏感键；普通
正文、短值和任意 `a` 保持。Task6P 历史 `FAIL / BLOCKED_AT_REPAIR_CAP` 保留，Task6
仍 `IN_PROGRESS / NOT_ACCEPTED`，Task6V packaged 30/70、live/Artifact/Production/
Vault/owner acceptance 仍未执行。

Task 6P independent review (2026-08-28)：报告
`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6p-review.md` 审查
HEAD `815a3bb5c0d245f6f33a984e7349e927b0090418` 与产品/测试
`19525638ba3f33223fac005aa258f33dd2eb6091`，结论为 `FAIL /
REPAIR_ROUND_1_AUTHORIZED`，Critical=0、Important=1、Minor=0。Fresh
Task6P focused `5 passed`，expanded backend `279 passed, 3 warnings`，Desktop
source/rendered/build、compile、acceptance sync、local handoff 通过；但
pipeline `process_next/process_internal_next/process_job` 的 lifecycle callback
仍收到带明文 `lease_token` 的 claimed job，direct `execute` callback 仍透传
显式嵌套 lease key。仅授权一轮有界 lifecycle projection repair；Task6P 保持
`NOT_ACCEPTED`，Task6 保持 `IN_PROGRESS / NOT_ACCEPTED`。Task6L/M 历史结论、
Task6V packaged 30/70、live/Artifact/Production/Vault/owner acceptance 均不改写。

### Task 6V packaged closeout（2026-08-28，当前自动化状态）

Task6R 产品 HEAD `684398e2b56447203ff6b77b4e93cae2c07b38f2` 已修复
`snapshot-owned` terminal cleanup。Task6V 仅在现有 integration harness 内补齐
transient/raw 分类、跨 root 自然身份与状态 parity、实测 PID/child/port cleanup
receipt、lease barrier 后 startup recovery，以及 Desktop rendered 的确定性就绪等待；
没有修改 `src/` 或 Desktop 产品代码。

完整 packaged gate 从独立临时 roots 连续两次 GREEN：
`2 passed, 1 warning, 294.47s` 与 `2 passed, 1 warning, 295.59s`。每次覆盖十个
场景、30%/70% 真实 sidecar crash/restart、原 scan `20/20`、transient=0、raw 64hex
hash、自然身份/状态 parity、fallback=false、queued/duplicates=0、PID/child/port/log
清理、Gateway/Hybrid/MCP/ContextPack lexical fallback、revoke/expiry current/history/
as_of/version、heartbeat instance/generation。Task6H active Work Fact degraded/recovery
由 focused 套件覆盖。

Task6V focused matrix `376 passed, 3 warnings`；Desktop build、runtime、source/repair、
Work Fact、memory-review smokes 与 rendered E2E 均通过；compileall、diff-check、
acceptance-sync、local-handoff 通过。当前自动化 disposition 为
`AUTOMATED_ACCEPTED / READY_FOR_TASK7`，不代表 release、Artifact、live 8766/8767、
Production/Vault 或 owner acceptance；`LOCAL_EXECUTION_TASK.md` 仍为 `IDLE`。

### Task 7N2 corruption retrieval evidence（2026-08-28）

Task7N2 已将 corruption isolation 测量收口为真实的授权 source → scan → durable
queue → worker → Work Fact → structured read-model → lexical/Hybrid/Gateway 检索链。
测量现在发布精确 source/scan/job 身份、队列和 Work Fact 终态计数、适配器期望复合
身份与 content hash、有效检索身份及坏源泄漏数；任何目标集合、终态、Work Fact、
read-model 或 Gateway 身份异常均 fail closed。聚焦及 Task7M/N1 直接回归 `125 passed`，
但 Task7 总质量结果仍须以真实固定题集评测为准，尚未进入 100k、release、Artifact、
Production/Vault 或主人验收。

### Task 7N3 promotion evidence and thin quality orchestration（2026-08-28）

Task7N3 已完成有界 measurement 收口：产品/测试提交
`21e4db93a1cf63a709c831fdab7720f6e7845a47` 新增 `quality_promotion.py`，逐条调用正式
`AutoMemoryPromotionService`，并从持久 read model 复算 promotion projection、message
link、audit 与 missing/extra/duplicate；protected、assistant-only、authority-conflict
的错误 active、非 active projection/link 和重复/孤儿 evidence 均 fail closed。两个历史
直接调用方已迁移到 nullable `evaluation_report`/Production 与 raw measured counters，
保留 opaque ID、SQLite 全值扫描、敏感信息和拒绝语义。semantic degradation、100k fixture/run
分别归入 `quality_degradation.py`、`scale_benchmark.py`，quality_gate 仅保留正式评测编排
和兼容导出，约从 1409 行降至 1129 行。

Task7N3 focused matrix 为 `156 passed, 1 skipped, 1 warning`；质量 CLI 仍诚实测得
`FAIL`（事实 `0/106`、引用 `0/106`、MCP `0/100`、Context baseline `NOT_MEASURED`、
自动晋级 `0/93`），不代表 Task7、100k、release、Artifact、真实服务或主人验收通过。
报告：`.superpowers/sdd/2026-08-27-phase1-product-landing/task-7n3-report.md`；等待独立
审查后才能决定 retrieval 诊断，Task8 不得开始。

### Task 7O measurement contract closure（2026-08-28）

Task7O 仅收口 Task7N 的证据契约，不改变检索、排序、向量、模型或自动晋级策略。最终
独立审查报告 `ce9807adb8aa9f4997819105ff3f1a949d93105b` 判定
`BLOCKED_AT_MEASUREMENT_CAP / NO_DIAGNOSTIC`（Critical=1、Important=3）；C1/I1/I2/I3
尚未关闭。质量 CLI 仍返回 raw facts/citations/MCP `0` 与 baseline 未测量，但 measurement
未接受，不能将这些数字当作最终产品 retrieval 诊断。Tasks 2–6 自动化/UI 状态不回退；
未运行 100k、release、Artifact、Mac、owner 或真实数据验收，Task8 不得开始。
