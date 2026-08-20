# PR88 Owner Fact Chain V5 Implementation Report

## Status

`PASS_FOR_M5_PREPARATION`

> 该结论只表示 PR #105 的代码、自审和自动前置门禁已经达到“可进入产品分支发包准备”的标准；不等于 M5 真机已经 PASS。

## Code candidate

- PR: `#105`
- branch: `fix/pr88-owner-fact-chain-v5`
- implementation SHA: `79955a09f42b7eb525fff1f11c454c373df8aa6c`
- rejected V4 product baseline: `bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9`

## 已完成

### 1. Capture → WorkItem 身份链

- `CaptureEnvelope.capture_id` 持久进入现有 `extraction_jobs` payload。
- `job_id` 直接作为 Capture/Extraction WorkItem identity；没有新增第二套 Work 数据库或编排器。
- 重启后可通过持久 queue 恢复 `capture_id ↔ job_id`，重复提交复用 canonical identity。

### 2. Owner-safe WorkItem 投影

`src/control/capture.py::CaptureControlService.job_dto()` 只向 Desktop 返回主人可读白名单：

- `work_item_id`
- `capture_id`
- title/source/status
- `outcome_state/outcome_summary`
- `next_actor/next_action`
- 稳定 `result_refs/result_object_ids`

明确不返回 captured body、raw payload、绝对输入路径、worker 原始错误、Token/Cookie/Credential/Secret。

### 3. Home / Work 共享同一事实投影

- 首页和“工作”统一消费 `/api/capture/jobs`。
- 两者统一经过 `desktop/lingji-control/src/ownerWorkFeed.ts`。
- 记忆数量、`relative_path`、generic event、Codex current 不再被用来制造“灵机做了什么”。
- queued/running/retrying/completed/failed/cancelled 都显示真实结果、下一步和下一 actor；未知状态不猜。

### 4. Home / 需要我 共享 PendingAction 投影

- `desktop/lingji-control/src/ownerWorkbenchModel.ts` 是唯一主人动作 projector。
- Memory Review candidate、Assistant import candidate、不可逆 vector rebuild 对象才允许形成主人动作。
- summary count、普通 WorkItem failure、静态发现说明不得制造待办。

### 5. Capture / Cmd+K 不再提前宣称“已经记住”

- 文本是一等 `source_type=text`。
- 成功反馈显示真实 `capture_id/job_id/status`。
- 没有 `capture_id` 或请求失败时明确不宣称已经记住。
- 永久记忆是否形成只以真实 MemoryRecord/result ref 为准。

### 6. Memory 是可检查的第二大脑表面

一级“记忆”页面已经显示：

- 可读正文片段；
- 正式来源；
- 行级引用（存在时）；
- 关联证据；
- 向量/取回状态。

没有证据时明确显示未知/缺失，不补写猜测。

### 7. 主动发现不再冒充接管

来源检测只表示“发现”。只有主人授权并生成真实 WorkItem 后，才允许进入接管/执行语义。

## 独立自审

### 发现的问题

自审发现 `desktop/lingji-control/src/ownerWorkbenchSummary.ts` 是后续临时增加但未成为任何主人页面权威的第二层 presentation model。继续把它硬接进 Home 会在 `ownerWorkFeed` 与 `ownerWorkbenchModel` 之外再产生一层状态翻译，增加事实漂移风险。

### 修复

在 `79955a09...` 删除该死层，保持：

- WorkItem：`/api/capture/jobs → ownerWorkFeed → Home + Work`
- PendingAction：真实候选对象 → `ownerWorkbenchModel → Home + 需要我`

同时新增 `owner-10-second-smoke.mjs` 并纳入全量 Desktop smoke suite。

### 自审结论

- 第二 WorkItem 数据库：`无`
- 第二主人工作 projector：`无`
- 第二 PendingAction projector：`无`
- 无对象宣称“已做/已记住/需要你”：`已加自动门禁`
- Owner DTO 私密正文/绝对路径/Secret 泄漏：`已加回归门禁`
- Mac/Windows 业务实现分叉：`未发现`
- 测试删除/skip/弱化换绿灯：`未发现`

## 精确 SHA 自动证据

Implementation SHA `79955a09f42b7eb525fff1f11c454c373df8aa6c`：

- `tests` run `32391549495`: **PASS**
  - Python 3.11: PASS
  - Python 3.12: PASS
  - Windows tests: PASS
  - Desktop full smoke + React build: PASS
  - MCP smoke: PASS
  - browser capture smoke: PASS
  - Obsidian plugin smoke: PASS
- `macOS Desktop Gate` run `32391549584`: **PASS**
  - Apple Silicon identity: PASS
  - frontend/sidecar/Rust/app bundle: PASS
  - embedded product identity: PASS
  - packaged sidecar contract + 8766 boot: PASS
  - DMG create/mount/verify: PASS
  - installed App Acceptance isolation + two-cycle runtime lifecycle: PASS
- `acceptance-doc-sync` run `32391549523`: **PASS**
- `local-execution-handoff` run `32391549512`: **PASS**

## 10 秒体验自动前置门禁

新增 `desktop/lingji-control/scripts/owner-10-second-smoke.mjs`，自动证明页面合同具备以下前置条件：

1. 首页能展示真实进行中 WorkItem；
2. 首页能展示真实 terminal outcome；
3. 首页展示下一执行者；
4. “需要我”数量来自 concrete object；
5. “工作”与首页读取同一 owner-safe WorkItem endpoint/projector；
6. “记忆”展示正文/来源/证据入口；
7. Cmd+K 不提前宣称永久记忆成立。

该 smoke 已由上述 `desktop-ui-smoke` 精确 SHA 门禁执行并 PASS。

## 剩余限制

以下仍必须在新的产品 SHA / Artifact 上完成，不能被本报告冒充：

- PR #105 squash merge 到 `feature/owner-autopilot-ui-codexpp`；
- merge 后产品 exact SHA 六道门；
- 同 SHA Windows + macOS 新 Artifact 与哈希锁定；
- M5 主人 10 秒肉眼理解；
- Window Recovery 菜单 / 快捷键 / Dock Reopen 三路径肉眼确认；
- 最终 Production pollution=0 与清理回执。

## Verdict

`PASS_FOR_M5_PREPARATION`

代码和自动前置门禁可以进入产品分支发包阶段。不得复用任何历史失败 Artifact，也不得在新的同 SHA 双平台 Artifact 锁定前把 M5 任务标为 ACTIVE。
