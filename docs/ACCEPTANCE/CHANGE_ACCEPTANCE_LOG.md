# 验收要求变更记录

> 每个包含产品代码、运行时、UI、连接器、数据链路、脚本、依赖或发布流程变化的 PR，都必须在本文件顶部追加一条记录。
>
> 记录描述“本次代码变化后，验收必须新增、修改或回归什么”。历史记录不得删除，只能更正明显错误并说明原因。

## 2026-08-20 · PR #105 / PR #88 · Owner Fact Chain V5 + 验收前独立自审

- 产品分支：`fix/pr88-owner-fact-chain-v5` → `feature/owner-autopilot-ui-codexpp`
- 产品基线：`bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9`（M5 已拒绝，Artifact `9258682849` 永久 `DO NOT RETRY`）
- 来源失败：`PR88-M5-OWNER-WORKBENCH-V4-BD1E7A17 / FAIL / DO NOT MERGE`
- 影响模块：Capture 身份、extraction queue 工作对象、Capture Control 安全投影、首页、工作履历、主人待办一致性、Desktop smoke、macOS release smoke、验收治理。
- 风险等级：P1。
- 用户可感知变化：`Cmd/Ctrl+K` 或 Capture 提交后，必须得到真实 `capture_id + job_id`；同一 `job_id` 作为唯一 WorkItem 贯穿工作状态和结果。首页与“工作”读取同一个 `/api/capture/jobs` 投影，不再通过记忆数量、`relative_path`、通用 event 或 Codex 当前状态推测“灵机做了什么”。主动发现只表示“发现”，不得提前宣称“已接管/已执行”。
- 数据或安全边界变化：不新增 WorkItem 数据库，不新增第二事实源。现有 `extraction_jobs` 继续承担持久 WorkItem；`capture_id` 持久写入该 job payload。Owner DTO 只暴露白名单字段、稳定 ID、结果引用和可读 outcome，不暴露 captured body、raw payload、绝对路径、raw snapshot、Token/Cookie/Authorization/Credential/Secret。

### 新增或修改的自动验收

- [ ] `tests/test_capture_control.py`：证明 `capture_id` 持久进入 queue job，`job_id == work_item_id`，重启 `CaptureControlService` 后同一内容仍复用同一 WorkItem 与 canonical `capture_id`，不得依赖内存 `_job_by_key` 才成立。
- [ ] 同一测试必须覆盖 queued/running/completed/failed/cancelled 的 `outcome_state + next_actor + next_action`；未知状态不得推测下一动作，普通失败不得自动创建主人待办。
- [ ] 同一测试必须证明 completed 结果只暴露稳定 `result_object_ids/result_refs`，伪造的私人绝对路径、正文、原始 error、Token 等不得进入 owner DTO。
- [ ] `owner-work-feed-smoke.mjs`：Owner Work Feed 只消费 `CaptureJobsResponse`；禁止 `relative_path` 猜关联、禁止 generic event 冒充 WorkItem、禁止记忆数量制造工作履历。
- [ ] `observation-first-ui-smoke.mjs`：首页和“工作”必须共享 WorkItem projector；首页读取 `/api/capture/jobs`，工作页不得重新读取/解释原始 `/api/jobs` 或把 `/api/codex/current` 冒充 LingJi WorkItem。
- [ ] `assistant-autopilot-smoke.mjs`：发现来源必须明确“发现不等于已授权、已接管或已执行”；Owner PendingAction 继续只来自真实 Memory Review candidate、Assistant import candidate、不可逆 vector rebuild 对象。
- [ ] `macos-release-smoke.mjs`：Mac Release 静态门禁同步 V5 WorkItem 合同，同时继续验证 exact-head、arm64、Sidecar、Acceptance isolation、窗口找回和 Secret 边界。
- [ ] `GlobalOwnerCommand`：文本必须使用 `source_type=text`；成功反馈显示真实 `capture_id/job_id/status`；没有 `capture_id` 或请求失败时不得说“已经记住”。
- [ ] `npm run test:smoke`、`npm run build`、Python 3.11/3.12/Windows、MCP、Obsidian、browser、Rust/Tauri 全部回归；不得删除、skip 或弱化旧断言换取绿灯。
- [ ] PR #105 精确 Head 的 `tests`、`macOS Desktop Gate`、`acceptance-doc-sync`、`local-execution-handoff` 必须全部 PASS。开发分支通过仍不等于可以 M5。
- [ ] PR #105 合入产品分支后，新的精确产品 SHA 必须重新通过 `tests`、`P0 Windows Gate`、`macOS Desktop Gate`、`Windows Desktop Release Baseline`、`acceptance-doc-sync`、`local-execution-handoff` 六道同 SHA 门禁，并生成新的同 SHA Mac/Windows Artifact。

### 验收前强制独立自审

- [ ] **新增硬门禁：任何新的 M5 任务创建前，实施代理必须先完成独立代码审计与端到端事实链复核，不允许把“CI 全绿”直接当验收前置 PASS。**
- [ ] 自审必须检查：无第二事实源/重复队列；Capture → WorkItem → Outcome → Memory/PendingAction 可追踪；关系重启后仍成立；Owner UI 不会无对象宣称“已做/已记住/需要你”；失败与未知状态不被美化；Owner DTO 不泄露正文、私人绝对路径或 Secret；Mac/Windows 使用同一业务实现；测试未被弱化。
- [ ] 自审报告必须写入 `docs/TEST_REPORTS/PR88_OWNER_FACT_CHAIN_V5_IMPLEMENTATION.md`，并明确列出“发现的问题 → 修复 → 剩余限制 → verdict”。
- [ ] 自审 verdict 只允许：`PASS_FOR_M5_PREPARATION / FAIL_FIX_REQUIRED / BLOCKED`。
- [ ] 只有 `PASS_FOR_M5_PREPARATION`，且随后 focused/full/release、同 SHA 双平台 Artifact 与哈希锁定全部完成，才允许把 `LOCAL_EXECUTION_TASK.md` 从 `IDLE` 改成新的 `ACTIVE` M5 task。

### 新增或修改的真机验收

- [ ] **当前仍禁止激活 M5。** PR #105 未完成自审、六道产品级门禁和同 SHA 双平台 Artifact 前，`LOCAL_EXECUTION_TASK.md` 必须保持 `IDLE`。
- [ ] `Cmd+K → 记住：<task fixture>`：界面必须显示真实 `capture_id/job_id`；进入“工作”后能找到同一 WorkItem；刷新/重启后身份不变。
- [ ] WorkItem 从 queued/running 到 completed/failed 后，首页与“工作”的状态、结果、下一动作和下一执行者必须一致。
- [ ] completed 只有在真实 result refs/object IDs 存在时才允许跳转/声称产生结果；不能因为 job completed 就宣称“形成永久记忆”。
- [ ] “需要我”每个动作必须有真实对象；首页不得从 pending count、WorkItem failure 或静态发现说明制造主人待办。
- [ ] 主动发现必须能区分 `发现 → 等授权 → 已创建 WorkItem → 执行 → 结果`；本轮如果只完成“发现”，必须明确停在发现而不是写“接管完成”。
- [ ] 继续回归 Window Recovery 菜单、快捷键、Dock Reopen 三路径主人肉眼确认，以及 exact Artifact identity、arm64、strict codesign、whole-bundle replace、Acceptance/Production 物理隔离、`secret_export_count=0`、两轮 exact-instance Runtime stop、Production pollution=0。

### 主人肉眼确认

- [ ] 不看技术文档，主人 10 秒内能回答：`这是什么对象`、`灵机具体做了什么`、`结果是什么`、`下一步谁做`、`我是否需要操作`。
- [ ] 首页与“工作”描述同一 WorkItem 时不存在相互矛盾；没有 WorkItem 时首页明确没有已执行工作。
- [ ] “发现工具/来源”不会被误解为“灵机已经接管”。
- [ ] “记忆”只有真实可读内容/摘要和来源证据时才被视为第二永久记忆大脑能力成立。

### 回归项

- [ ] 不新增第二个永久记忆事实源，不新增第二个 WorkItem 数据库或编排器；`extraction_jobs` 是当前 Capture 工作的唯一持久 WorkItem。
- [ ] Obsidian Vault + Git 仍是永久记忆正文权威；SQLite/Qdrant 仍为可重建派生状态/索引。
- [ ] 未经主人授权不得读取真实 AI 对话正文，不自动批准 Permanent/Core Memory，不自动执行破坏性 Production Qdrant rebuild。
- [ ] Production/Acceptance 物理隔离、CredentialStore/AuthStatus、release exact-head、Sidecar exact-instance lifecycle 与跨平台同代码主线不得回退。
- [ ] 历史失败 Artifact `9258682849 / 9250384637 / 9249367672 / 9224368022 / 9102748834` 均不得作为新 M5 输入。

### 清理与回滚

- PR #105 开发只修改代码、测试和文档，不触碰主人 Production 数据。
- 若 V5 回归 Capture/Extraction，可回退 PR #105 的 V5 commits；不得通过恢复 V4 的路径猜测、generic event 工作履历或降低 Secret/隔离门禁来“修复”。
- 真机阶段仍使用全新 task-scoped Acceptance root、whole-bundle replace 与失败恢复旧 App 的既有协议。

### 不在范围

- 不在 V5 事实链修复中新增第二套 Agent 编排框架。
- 不实现自动 Permanent/Core Memory 批准。
- 不把通用健康检查事件包装为业务 WorkItem。
- 不因当前 PR 修复 UI 投影就宣称“所有自动发现来源已经实现完整接管”。

### 最终报告

- 计划与自审门禁：`docs/TEST_REPORTS/PR88_OWNER_FACT_CHAIN_V5_PLAN.md`
- 实施、自测与独立自审：`docs/TEST_REPORTS/PR88_OWNER_FACT_CHAIN_V5_IMPLEMENTATION.md`
- 新 M5 报告：仅在上述前置全部满足后创建 `docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_<new-short-sha>.md`。

---

## 2026-08-16 · PR #102 / PR #88 · Active Permanent-Memory Workbench v4

- 产品分支：`fix/pr88-owner-workbench-v4` → `feature/owner-autopilot-ui-codexpp`
- 产品基线：`1d99d10cdcb151c0a0257f7d0a93937cdb817b49`
- 来源失败：`PR88-M5-OWNER-WORK-FEED-V3-1D99D10C / FAIL / DO NOT MERGE`
- 影响模块：Desktop 主导航、Owner Briefing 首页、一级永久记忆、工作履历、主人待办、全局输入、分页、统一视觉系统、Desktop smoke、macOS release smoke、跨平台集成测试。
- 风险等级：P1。
- 用户可感知变化：从“监控仪表盘/工具仓库”重构为“第二永久记忆大脑 + 主动型本地智能助手”的主人工作台。日常主导航收敛为 `首页 / 记忆 / 工作 / 需要我 / 高级`；首页回答系统做了什么、正在做什么、接下来做什么和主人是否需要行动；记忆成为一级可浏览、可搜索、可验证来源的产品表面。
- 数据或安全边界变化：不新增永久记忆事实源；Obsidian Vault + Git 继续作为永久记忆与正式知识权威。V4 只组合现有 authenticated Control API、Memory Inspector、Review、Assistant Hub、Jobs、Codex Current 与 Capture；不扩大正文读取权限、不自动批准永久记忆、不自动执行破坏性 Qdrant 重建、不导出 Credential/Secret。

### 新增或修改的自动验收

- [ ] `desktop/lingji-control/scripts/observation-first-ui-smoke.mjs`：锁定 5 个一级主人入口、Owner Briefing 六问、一级记忆来源证据、真实工作履历、对象级待办、全局输入和统一 V4 视觉系统。
- [ ] `owner-home-action-consistency-smoke.mjs`：主人行动必须来自真实 `memory_id` / `candidate_id`；汇总计数与对象明细不一致时必须显示 degraded/consistency 状态，禁止生成会打开空页面的按钮。
- [ ] `memory-progress-smoke.mjs`：永久记忆成为一级表面；没有验证样本不得宣称准确率；语义检索不可用时必须明确保留全文检索能力。
- [ ] `assistant-autopilot-smoke.mjs`：主动发现继续只读安全元数据；正文授权必须绑定精确 candidate；后台技术问题不得冒充主人待办；Autopilot 不得自动批准永久记忆、无限重试或破坏性重建 Qdrant。
- [ ] `MemoryHomePage`：必须使用真实 `/api/memory/inspector/memories`、`/status`、`/{id}/source`、`/{id}/vector`，展示“记住了什么 / 为什么能相信它 / 来源证据”；没有主人专属证据时不得用通用模板捏造“记忆缺口”。
- [ ] `GlobalOwnerCommand`：`Cmd/Ctrl+K` 可聚焦；`记住：...` 必须真实调用 `/api/capture/text`，失败时不得宣称已记录，重复内容不得重复创建；其他尚未支持的自然语言命令必须明确能力边界。
- [ ] `ActivityPage`：工作履历必须来自真实 `/api/jobs` 和 `/api/codex/current`，说明“发生了什么 / 灵机做了什么 / 结果 / 下一步”；普通失败不得自动升级为主人待办。
- [ ] `AttentionPage`：只能展示真实 Review candidate、Assistant import candidate 或真实不可逆维护边界；无真实对象时页面必须为空态或未知态，不得依赖 `pending_review_count` 生成按钮。
- [ ] `MemoryReviewPage`、`MemoryInspectorPage`、`CaptureCenterPage`、一级 `MemoryHomePage`：所有“下一页”必须服从后端 `has_more` 或可验证 `total` 边界，`has_more=false` 时禁止继续翻页。
- [ ] Owner UI 投影继续禁止泄漏 captured body、Authorization/Cookie/Token、Credential/Secret、raw snapshot 和私人绝对路径。
- [ ] `npm run test:smoke`、`npm run build`、Python 3.11/3.12/Windows、MCP、Obsidian plugin、browser capture、Rust/Tauri 回归全部 PASS。
- [ ] PR #102 精确 Head 的 `tests`、`macOS Desktop Gate`、`acceptance-doc-sync`、`local-execution-handoff` 必须全部 PASS；这里只是开发分支自动门禁，不得直接作为 M5 产品 Artifact。
- [ ] PR #102 合入产品分支后，新的**精确产品 Commit**必须重新通过 `tests`、`P0 Windows Gate`、`macOS Desktop Gate`、`Windows Desktop Release Baseline`、`acceptance-doc-sync`、`local-execution-handoff` 六道同 SHA 门禁，才允许选择双平台 Artifact。

### 新增或修改的真机验收

- [ ] **当前禁止激活真机验收。** PR #102 自动验收或合并后六道产品门禁任何一项未通过时，`docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md` 必须保持 `IDLE`。
- [ ] 只有新的精确产品 Commit 六道门 6/6 PASS、Mac/Windows 新 Artifact 身份与哈希独立复核完成后，才允许在 `master` 创建新的 ACTIVE M5 任务。
- [ ] 后续 M5 首屏 5 秒内必须能回答：`灵机刚刚做了什么`、`现在在做什么`、`接下来会做什么`、`我现在需要做什么`。
- [ ] 一级“记忆”必须能够查看真实记忆对象、内容/安全预览、来源证据和取回状态；不能再只看到“2 份资料 / 11 个片段”等统计数字。
- [ ] “需要我”中每个可点击动作必须有真实对象；点击后目标页面必须存在同一对象或直接执行该对象的明确授权动作，不允许空待办。
- [ ] 全局输入必须可真实提交一条任务专用记录并在失败/重复情况下给出真实反馈。
- [ ] 视觉与结构必须与 V3 明显不同：稳定侧栏、紧凑列表/详情、时间线、少量状态标签；技术 PID/端口/路径/Commit 默认隐藏在高级详情。
- [ ] Window Recovery 仍为强制主人验证：菜单 `窗口 → 将灵机带到当前屏幕`、快捷键和 macOS Dock Reopen 至少按任务协议完成真实找回。
- [ ] 继续回归 exact Artifact identity、arm64、strict codesign、whole-bundle replace、Acceptance/Production 物理隔离、AuthStatus、`secret_export_count=0`、两轮 exact-instance Sidecar stop、`state gone + PID gone + port free`、Production pollution=0。

### 主人肉眼确认

- [ ] 不看技术文档，主人能够明确理解：系统刚刚替我做了什么、现在做什么、下一步谁做、我是否需要行动。
- [ ] “记忆”看起来是第二永久记忆大脑，而不是数据库检查器：能看到具体记忆及其来源，空状态也能说明系统会继续自动处理还是确实没有内容。
- [ ] “工作”看起来是灵机的工作履历，而不是原始队列/日志。
- [ ] “需要我”只在真的需要授权、永久记忆判断、冲突或不可逆操作时打扰主人。
- [ ] 全局 `⌘K` 入口容易发现，不要求主人先理解内部模块名称。
- [ ] 端口、Qdrant、Embedding、SQLite、PID、Commit、DataRoot 等技术信息不占日常首屏。

### 回归项

- [ ] 不新增第二个永久记忆事实源；`lingji_memory.db` 与 Qdrant 仍为可重建索引。
- [ ] 未经主人授权不得读取真实 AI 对话/导出正文；主动扫描不得全盘递归或跟随符号链接。
- [ ] 不允许自动批准永久记忆、自动删除/重建 Production Qdrant、自动修改第三方 AI 客户端配置或自动发布内容。
- [ ] Production/Acceptance 物理隔离、CredentialStore/AuthStatus、Sidecar exact-instance stop、release exact-head 和 Windows/macOS 同代码主线不得回退。
- [ ] 旧失败 Artifact `9250384637`、`9249367672`、`9224368022`、`9102748834` 不得作为新 M5 输入。
- [ ] PR #88 在新精确 Artifact 的真实 M5 与主人体验 PASS 前继续保持 Draft / DO NOT MERGE。

### 清理与回滚

- 本轮开发与 CI 不触碰主人 Production 数据；临时产物由 workflow 清理。
- PR #102 阶段不创建 M5 task-scoped Runtime，也不选择正式 Artifact。
- 后续真机任务必须使用新的 task-scoped Acceptance root 和 whole-bundle replace；FAIL 时恢复原 App并只保留最小必要失败证据。
- 回滚允许撤销 V4 主人投影、导航和样式，但不得回退已经通过的认证、隔离、Sidecar 生命周期、窗口找回与 release identity 修复。

### 不在范围

- 不在 V4 UI 重构中自动批准 Permanent/Core Memory。
- 不新增全盘文件扫描。
- 不宣称已实现开放式 Agent 命令执行；当前全局入口只执行可验证的记录与导航能力。
- 不在 PR #102 开发分支激活 `LOCAL_EXECUTION_TASK.md`。

### 最终报告

- 实施与自动验收报告：`docs/TEST_REPORTS/PR88_OWNER_WORKBENCH_V4_IMPLEMENTATION.md`
- 新 M5 报告：仅在合并后产品同 SHA 六道门和新 Artifact 锁定后创建 `docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_<new-short-sha>.md`。

---

## 2026-08-16 · PR #99 / PR #88 修复 · Owner Work Feed v3

- 产品分支：`fix/pr88-owner-work-feed-v3` → `feature/owner-autopilot-ui-codexpp`
- 产品 Commit：`pending exact PR head`
- 来源失败：`PR88-M5-OWNER-HOME-V2-F3CBA413 / f3cba4136bd169619277279a55007fcd4ef609f4 / Artifact 9249367672 / FAIL / DO NOT MERGE`
- 影响模块：Desktop 首页、Memory Inspector 明细投影、extraction queue 结果关联、Owner actions、Desktop smoke、macOS release smoke。
- 风险等级：P1。
- 用户可感知变化：首页从“汇总阶段卡”改为“你现在要不要做事 → 具体资料 → 灵机已做 → 下一步 → 是否需要主人行动”；每份资料成为首页主单位，统计与 recent activity 下沉为折叠次级信息。
- 数据或安全边界变化：不新增持久化事实源；只读现有 authenticated Memory Inspector、overview queue/events、Autopilot status；Owner Work Feed 投影禁止输出正文、绝对私人路径、raw snapshot 或 Credential/Secret。

### 新增或修改的自动验收

- [ ] `tsx desktop/lingji-control/scripts/owner-work-feed-smoke.mjs`：真实数据语义验证。已完成并索引的资料必须显示具体标题/来源/已做/下一步；处理中但尚未产生 memory row 的 queue job 仍必须显示；pending review 必须变成主人动作；未知 source 必须显示“知识库资料”而不是空白。
- [ ] 同一 smoke 必须验证 `expectedDocuments > 0` 但明细为空时进入 `detailsState=unavailable`，明确提示“不会用一个数字代替资料列表”，禁止再次退化成只显示“已收纳 N 份”。
- [ ] 同一 smoke 必须验证前端投影不包含 captured body、Authorization/Cookie/Token、绝对私人路径、raw snapshot 路径；未知内部 event 不得冒充主人活动。
- [ ] `observation-first-ui-smoke.mjs`：首页必须存在“你现在需要做什么 / 灵机现在在做什么 / 资料工作清单 / 灵机已做 / 下一步”，并禁止 `buildWorkflow`、七阶段汇总卡和技术 Metric 网格回归为首页主结构。
- [ ] `memory-progress-smoke.mjs`：资料数量、片段、覆盖率只能留在折叠高级状态；没有验证样本继续明确 `not_measured`，禁止把覆盖率或片段数包装成准确率。
- [ ] `assistant-autopilot-smoke.mjs`：AI 历史读取授权、候选记忆确认、向量重建等真正需要主人决定的事项必须直接进入首页行动区；普通后台故障不得伪装成主人待办。
- [ ] `macos-release-smoke.mjs`：Owner Work Feed 不得暴露 Credential/Secret，且继续回归 macOS exact-head、arm64、Sidecar、窗口找回和 Acceptance isolation 合同。
- [ ] `npm run test:smoke` 与 `npm run build`：Owner Work Feed 数据语义、Desktop smoke、TypeScript 与生产构建全部 PASS。
- [ ] 新精确 Head 的 `tests`、`acceptance-doc-sync`、`local-execution-handoff`、`macOS Desktop Gate` 全部 PASS；合入产品分支后再要求 `P0 Windows Gate` 与 `Windows Desktop Release Baseline` 对同一新产品 Commit PASS。

### 新增或修改的真机验收

- [ ] 只允许使用本轮修复合并后**新产品 Commit**生成的全新 macOS/Windows Artifact；失败 Artifact `9249367672`、`9224368022`、`9102748834` 永久禁止重跑。
- [ ] 使用至少 2 份真实或任务专用资料复验：首页必须直接显示它们各自的具体标题/安全来源，不能只显示“已收纳 2 份”。
- [ ] 对每一份可见资料，主人必须能在不打开技术文档的情况下回答：`灵机已经做了什么`、`下一步是什么`、`这一步由灵机自动做还是需要我做`。
- [ ] 若系统统计有资料但 Memory Inspector 明细不可读，首页必须显式显示“明细暂不可用/正在重试”，该状态不得被视为 Owner Home PASS。
- [ ] 首页顶部必须明确二选一：`现在不用你做任何事`，或列出具体主人动作及“去处理”入口；不得要求主人根据阶段卡自行推断。
- [ ] 最近活动只能来自真实 allowlisted events；没有真实活动时明确空闲，不制造虚假“系统很忙”的动画或文案。
- [ ] Window Recovery 仍为最终 PASS 必测项：菜单、快捷键、Dock Reopen 至少按任务协议完成真实找回；不能因首页先通过就跳过。
- [ ] 继续回归 exact Artifact identity、arm64、strict codesign、whole-bundle replace、Acceptance/Production 隔离、AuthStatus、`secret_export_count=0`、first/second exact-instance stop、`state gone + PID gone + port free` 和 Production pollution=0。

### 主人肉眼确认

- [ ] 不看任何开发/验收文档，主人能直接回答四个问题：`目前有哪些具体资料？`、`每份灵机做了什么？`、`下一步是什么？`、`我要做吗？`。
- [ ] “已收纳 N 份”“7 个阶段”“覆盖率”等汇总信息单独存在不能算通过；具体对象与下一步必须先于统计。
- [ ] 首页与失败的 Owner Home v2 有明显结构差异，不是在原七阶段页面上追加一张明细卡。
- [ ] 技术统计、Qdrant、Embedding、端口、SQLite 等不占日常首屏。
- [ ] 真正需要授权/确认时入口唯一、文案明确；没有主人事项时界面明确说明无需操作。

### 回归项

- [ ] Owner Work Feed 不得输出 `payload.text`、transcript/html/selected_text、raw snapshot、绝对私人路径或 Credential/Secret。
- [ ] 未经主人授权不得读取真实 AI 对话正文；不得自动批准永久记忆、自动删除/重建 Production Qdrant 或自动修改第三方 AI 客户端配置。
- [ ] Production/Acceptance 物理隔离、CredentialStore/AuthStatus、`secret_export_count=0`、Sidecar exact-instance stop 与 release exact-head 身份合同不得回退。
- [ ] Windows 与 macOS 继续使用同一业务 UI/Runtime 代码；本轮不能演变成 Mac 特供逻辑。
- [ ] PR #88 在新精确 Artifact 的真实 M5 主人体验 PASS 之前保持 Draft / DO NOT MERGE。

### 清理与回滚

- 本轮开发分支不触碰主人 Production 数据；CI 临时产物按 workflow 清理。
- 新真机任务必须使用新的 task-scoped Acceptance root 和 whole-bundle replace；FAIL 时恢复原 App，并仅保留最小必要失败证据。
- 回滚仅允许移除 Owner Work Feed v3 的纯派生投影、首页结构和样式；不得回退已经通过的认证、隔离、Sidecar 生命周期、窗口找回或 release identity 修复。

### 不在范围

- 不新增新的自动导入正文权限。
- 不新增第二个持久化数据库或 Owner Feed 事实源。
- 不实现自动永久记忆批准。
- 不在本轮开发分支激活 `LOCAL_EXECUTION_TASK.md`；只有新产品 Commit、六道同 SHA 门禁、新双平台 Artifact 与哈希全部锁定后，才允许在 `master` 创建新的 ACTIVE M5 任务。

### 最终报告

- 实施报告：`docs/TEST_REPORTS/PR88_OWNER_WORK_FEED_V3_IMPLEMENTATION.md`
- 新 M5 报告：`docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_<new-short-sha>.md`

---

## 2026-08-15 · PR #88 M5 UX 修复 · Owner Home v2

- 产品分支：`fix/pr88-owner-home-v2` → `feature/owner-autopilot-ui-codexpp`
- 产品 Commit：`pending exact PR head`
- 来源失败：`PR88-M5-REACCEPTANCE-2C96B3EC / FAIL / DO NOT MERGE`
- 影响模块：Desktop 首页信息架构、真实事件流投影、Memory Progress、空闲 CurrentWork 降噪、macOS 主窗口找回入口、Desktop smoke。
- 风险等级：P1。
- 用户可感知变化：首页改成“现在发生什么 → 自动工作流走到哪一步 → 最近真正自动做过什么”；七阶段流程直接展示 `发现来源 → 收纳 → 解析 → 候选 → 确认 → 索引 → 取回`；空闲 Codex 工作块不再占首页；主窗口入口改为 `窗口 → 将灵机带到当前屏幕` 并增加快捷键与 Dock Reopen。
- 数据或安全边界变化：不新增事实源；首页只读现有 `overview.events`、queue、memory progress、vector 和 Autopilot 状态；不扩大正文读取、永久记忆批准、Qdrant 重建、Secret、Production/Acceptance 或外部客户端权限。

### 新增或修改的自动验收

- [ ] `node desktop/lingji-control/scripts/observation-first-ui-smoke.mjs`：锁定自动驾驶首屏、七阶段真实流程、`overview.events` 事件流、空闲 CurrentWork 隐藏与技术指标下沉。
- [ ] `node desktop/lingji-control/scripts/memory-progress-smoke.mjs`：锁定 Memory Progress v2 的真实 coverage / queue 状态和 `not_measured` 质量边界，禁止伪造准确率。
- [ ] `node desktop/lingji-control/scripts/window-recovery-smoke.mjs`：锁定 `窗口` 子菜单、`将灵机带到当前屏幕`、`CmdOrCtrl+Shift+L`、unminimize/show/center/focus 与 macOS `RunEvent::Reopen`。
- [ ] `node desktop/lingji-control/scripts/run-smoke-suite.mjs` 与 `npm run build`：Desktop 回归与生产构建 PASS。
- [ ] Rust/Tauri `cargo test` / `cargo check`：macOS 条件事件和跨平台主线不能破坏编译。
- [ ] GitHub `tests`、`P0 Windows Gate`、`macOS Desktop Gate`、`Windows Desktop Release Baseline`、`acceptance-doc-sync`、`local-execution-handoff`：新精确 Head 全部 PASS 后才允许进入新 Artifact 阶段。

### 新增或修改的真机验收

- [ ] 只使用本轮修复合并后的**新产品 Commit**生成的新 macOS/Windows Artifact；失败 Artifact `9224368022` 与历史 `9102748834` 永久禁止重跑。
- [ ] M5 首屏在不打开高级工具的情况下，能直接回答：是否需要主人决定、此刻系统正在做什么、自动流程走到哪、最近真实做过什么、下一步是什么。
- [ ] 七阶段流程的状态必须能与真实 queue / memory / review / vector 数据对应；空闲时不得用假的“正在工作”动画或默认绿色掩盖未知状态。
- [ ] “最近自动完成”必须来自已有 StateDatabase events；没有事件时明确没有新记录，不伪造活动。
- [ ] Memory Progress 必须能看懂收纳、更新和索引覆盖；无验证样本继续明确“不宣称准确率”。
- [ ] 将主窗口最小化、隐藏或移动离屏后，菜单 `窗口 → 将灵机带到当前屏幕`、快捷键和 macOS Dock Reopen 至少各验证一条真实找回路径；恢复后窗口可见、居中并获得焦点。

### 主人肉眼确认

- [ ] 首页与上一失败版有明显、可感知的首屏结构差异，而不是在旧页面上增加几个卡片。
- [ ] 不看技术文档即可理解灵机已经自动做了什么、正在做什么、是否真的需要操作。
- [ ] 信息层级先给行动与流程，端口、数据库、Qdrant、Embedding 等技术信息不占日常首屏。
- [ ] Memory Progress 看起来是工作进度，不是统计数字堆积。
- [ ] 主窗口找回入口容易发现，且实际有效。

### 回归项

- [ ] 未经主人授权不得读取真实 ChatGPT/Codex 正文；自动发现继续只读元数据。
- [ ] 不允许自动批准永久记忆，不允许自动删除/重建 Production Qdrant，不允许自动修改第三方 AI 客户端配置。
- [ ] Production/Acceptance 物理隔离、CredentialStore/AuthStatus、`secret_export_count=0`、Sidecar exact-instance stop 和 release exact-head 身份合同不得回退。
- [ ] Windows 与 macOS 继续使用同一业务 UI/Runtime 代码；macOS 仅允许平台窗口事件条件分支。
- [ ] PR #88 在新精确 Artifact 的 M5 主人体验 PASS 之前保持 Draft / DO NOT MERGE。

### 清理与回滚

- 本轮开发分支不触碰主人 Production 数据；CI 临时产物按 workflow 清理。
- 新真机任务必须重新创建 task-scoped Acceptance root，whole-bundle 替换安装；FAIL 时恢复原 App，PASS 后按任务协议删除临时备份与任务根。
- 回滚只允许回退 Owner Home v2 UI 投影与窗口入口，不得回退已经通过的认证、隔离、Sidecar 生命周期和 release identity 修复。

### 不在范围

- 不新增新的自动导入正文权限。
- 不实现自动永久记忆批准。
- 不把 Activity/Diagnostics 全部重做一遍。
- 不在本轮开发分支直接激活 `LOCAL_EXECUTION_TASK.md`；只有新产品 Commit、新双平台 Artifact 和哈希全部锁定后，才允许在 `master` 创建新的 ACTIVE M5 任务。

### 最终报告

- 实施报告：`docs/TEST_REPORTS/PR88_OWNER_HOME_V2_IMPLEMENTATION.md`
- 新 M5 报告：`docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_<new-short-sha>.md`

---

## 填写模板

```markdown
## YYYY-MM-DD · <PR/任务> · <短标题>

- 产品分支：`<branch>`
- 产品 Commit：`<sha 或 pending>`
- 影响模块：
- 风险等级：P0 / P1 / P2 / P3
- 用户可感知变化：
- 数据或安全边界变化：

### 新增或修改的自动验收

- [ ] `<测试命令或测试文件>`：验证什么

### 新增或修改的真机验收

- [ ] `<步骤>`：预期结果

### 主人肉眼确认

- [ ] `<必须人工观察的行为>`

### 回归项

- [ ] `<历史 Bug 或兼容承诺>`

### 清理与回滚

- 临时数据前缀：
- 覆盖安装或迁移方式：
- 临时备份删除条件：
- 测试数据清理方式：

### 不在范围

- `<本次没有实现且不得宣称已完成的能力>`

### 最终报告

- 报告路径：`docs/TEST_REPORTS/<REPORT>.md`
- 报告分支：`acceptance/<task>-<short-sha>`
```

---

## 2026-08-14 · PR #88 · Phase 4/5 后最终 Head Artifact 重新锁定

- 产品分支：`feature/owner-autopilot-ui-codexpp`
- 产品 Commit：`pending final relock head`
- 影响模块：双平台 Release 身份、最终 Artifact 收口、M5 任务交接；本记录与 `src/README.md` 触发重新验证，不改变 Runtime 行为。
- 风险等级：P0（最终真机输入必须与当前 PR #88 产品 Head 完全一致）。
- 用户可感知变化：无新增产品交互；只重新锁定包含“找回主窗口”和“记忆进度看板”后的最终双平台包。
- 数据或安全边界变化：无；不得放宽 Production/Acceptance 隔离、CredentialStore、AuthStatus、Secret 导出或主人授权边界。

### 新增或修改的自动验收

- [ ] `tests`、`P0 Windows Gate`、`Windows Desktop Release Baseline`、`macOS Desktop Gate`、`acceptance-doc-sync`、`local-execution-handoff` 必须全部绑定同一最终 Head 并 PASS。
- [ ] macOS 与 Windows Artifact 必须由该同一精确 Head 生成；下载后独立复核 ZIP/DMG/NSIS 哈希与内嵌 Commit metadata。
- [ ] `90398fd87f3419c598632479d2a00626b4554122` 的已通过 Artifact 只作为 Phase 5 自动验证历史证据；若最终 Head 不同，不得作为最终 M5 输入。

### 新增或修改的真机验收

- [ ] 仅在六道门全部对最终同一 Head 通过、双平台 Artifact 身份与哈希锁定、PR #88 任务单更新后，才允许启动新的 M5 真机复验。
- [ ] M5 必须包含 Phase 4“找回主窗口”与 Phase 5“记忆进度看板”主人肉眼检查，同时继续回归首次启动、身份、隔离、Sidecar 真实退出与授权边界。

### 主人肉眼确认

- [ ] 首页应能直接看懂系统正在收纳/更新/取回什么；没有验证样本时不得把覆盖率包装成“准确率”。
- [ ] 主窗口被最小化或移出可见区域后，“找回主窗口”必须可发现且能恢复到当前屏幕并获得焦点。

### 回归项

- [ ] 不允许复用任何 SHA 早于最终 Head 的 macOS / Windows Artifact 作为最终 M5 输入。
- [ ] 不允许 Mac/Windows Artifact、任务单、结果回执和最终报告引用不同产品 SHA。
- [ ] 不允许恢复已拒绝 Artifact `9102748834`，也不允许回退 Sidecar graceful shutdown、Acceptance 任务根隔离或认证 Secret 边界。

### 清理与回滚

- 本次仅产生 CI Artifact、临时验证数据和任务级报告；按既有任务协议清理，不删除主人数据。
- 回滚仅允许回退本次 release-trigger 文档，不得回退 Phase 4/5 已验证产品能力或治理门禁。

### 不在范围

- 不新增 Runtime 功能，不继续扩展 PR #88 产品范围；本轮只完成最终同 SHA 收口并准备 M5 复验。

### 最终报告

- 报告路径：`docs/TEST_REPORTS/PR88_FINAL_ARTIFACT_CLOSEOUT.md`
- M5 报告：`docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_<final-short-sha>.md`

---

## 2026-08-14 · PR #88 Phase 5 · 记忆进度看板

- 产品分支：`feature/owner-autopilot-ui-codexpp`
- 产品 Commit：`pending memory progress commit`
- 影响模块：Local Control API、首页进度看板、自动收纳/更新/取回状态。
- 风险等级：P1（首页不应把未知质量伪装成精准取回）。
- 用户可感知变化：首页显示收纳资料/片段、自动更新队列和检索覆盖；高级工具仍承担检修。
- 数据或安全边界变化：无新增事实源；只读聚合现有队列和记忆状态，永久记忆仍需主人确认。

### 新增或修改的自动验收

- [ ] `memory-progress-smoke.mjs`：API、首页三段进度和“不测量不宣称准确率”合同必须同时存在。
- [ ] `tests/test_control_api.py`：`/api/memory/progress` 必须认证，且返回真实收纳/队列/覆盖率数据。

### 新增或修改的真机验收

- [ ] 首页能直接看见收纳、更新和取回进度；没有验证样本时必须写明尚未建立验证样本。

### 主人肉眼确认

- [ ] 首页是否像持续工作的进度看板，而不是后期检修入口。

### 回归项

- [ ] 不得把向量数量或覆盖率称为“准确率”。

### 清理与回滚

- 不产生额外 Runtime 数据；回滚只移除只读聚合和首页展示。

### 最终报告

- 新 Artifact 的 M5 报告必须记录首页进度看板、自动收纳、自动更新与检索质量状态。

---

## 2026-08-14 · PR #88 Phase 4 · 主窗口找回

- 产品分支：`feature/owner-autopilot-ui-codexpp`
- 产品 Commit：`pending window recovery commit`
- 影响模块：Tauri 主窗口、macOS 菜单栏、Desktop smoke。
- 风险等级：P1（窗口被拖离可见屏幕后，主人无法回到灵机）。
- 用户可感知变化：菜单栏新增“找回主窗口”；它会取消最小化、显示、居中并置前主窗口。
- 数据或安全边界变化：无；不访问 Runtime、DataRoot、Vault、凭据或网络。

### 新增或修改的自动验收

- [ ] `node desktop/lingji-control/scripts/window-recovery-smoke.mjs`：必须同时存在主窗口查找、取消最小化、显示、居中、置前和菜单入口。
- [ ] `node desktop/lingji-control/scripts/run-smoke-suite.mjs`：统一桌面 smoke 必须包含窗口找回回归项。
- [ ] macOS Desktop Gate：构建后的 App 必须能从菜单栏触发找回窗口，不得只依赖首次启动的居中配置。

### 新增或修改的真机验收

- [ ] 在 M5 上将主窗口移出可见区域或最小化后，从菜单栏点击“找回主窗口”；窗口必须回到当前屏幕中央并获得焦点。

### 主人肉眼确认

- [ ] “找回主窗口”是否容易发现，且是否能真正找回误放的窗口。

### 回归项

- [ ] 不得因自定义菜单移除现有 macOS 菜单栏能力。
- [ ] 不得重置窗口以外的用户设置或影响 Runtime 生命周期。

### 清理与回滚

- 不产生临时数据；回滚仅移除菜单项和找回调用，不删除或改写用户数据。

### 最终报告

- 报告路径：`docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_<new-short-sha>.md`
- M5 任务单必须在新 macOS Artifact 生成后更新；失败的 `65de7292` Artifact 不得复用。

---

## 2026-08-14 · PR #88 · 最终同 SHA Artifact 收口文档

- 产品分支：`feature/owner-autopilot-ui-codexpp`
- 产品 Commit：`041c5fc805d2280c4d84d78bca45799f131ad61b`
- 影响模块：`src/` 主线职责说明、PR #88 最终 Artifact 收口报告。
- 风险等级：P1（发布身份和验收结论一致性）。
- 用户可感知变化：无产品交互变化；明确 macOS 与 Windows 最终包必须来自同一精确产品 Commit。
- 数据或安全边界变化：无；不改变 Runtime、数据根、凭据或授权边界。

### 新增或修改的自动验收

- [ ] `acceptance-doc-sync`：`src/README.md` 与 `PR88_FINAL_ARTIFACT_CLOSEOUT.md` 必须在同一变更中有本条验收记录。
- [ ] macOS Desktop Gate、P0 Windows Gate、Windows Desktop Release Baseline：均绑定同一产品 Commit；Artifact 下载后复核哈希与内嵌 metadata。

### 新增或修改的真机验收

- [ ] 仅使用同 SHA 的新 macOS DMG 和 Windows Artifact 进入 M5 / Windows 真机验收；旧 Artifact 不得复用。

### 主人肉眼确认

- [ ] M5 真机验收仍仅确认首次体验、首页信息层级与必要授权边界；PR #88 保持 Draft。

### 回归项

- [ ] 不允许 Mac/Windows Artifact、报告或任务单引用不同产品 SHA。

### 清理与回滚

- 临时 Artifact、解压目录、日志和测试 Runtime 在远程核验后按任务协议清理；不删除主人数据。
- 回滚仅回退发布收口文档，不回退已验证的 Runtime / Sidecar 修复。

### 最终报告

- 报告路径：`docs/TEST_REPORTS/PR88_FINAL_ARTIFACT_CLOSEOUT.md`
- M5 报告：`docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_<short-sha>.md`

---

## 2026-08-13 · PR #88 Phase 4 · macOS 最终 DMG 真实退出三重门禁

- 产品分支：`feature/owner-autopilot-ui-codexpp`
- 产品 Commit：`pending final closeout head`
- 影响模块：macOS 最终 DMG 首启/二启隔离 Gate、Sidecar 退出验证、DMG 清理。
- 风险等级：P0（最终 DMG 可卸载性、二启可靠性与验收真实性）。
- 用户可感知变化：无新增交互；仅收紧最终安装包验收，避免把 state 文件消失误判为 Sidecar 已真实退出。
- 数据或安全边界变化：仍只发送当前 task-scoped runtime 的精确 `instance_id` stop request；禁止 `killall`，禁止把主动 kill Sidecar PID 当正常成功路径。

### 新增或修改的自动验收

- [ ] `macOS Desktop Gate`：每次停止必须同时确认 `sidecar-state.json` 消失、启动时记录的 Sidecar PID 已退出、8766 已无 LISTEN，三项同时满足后才允许二启或卸载 DMG。
- [ ] 真实退出等待最长 30 秒；超时必须打印 state、Sidecar PID 的 `ps`、`lsof -nP -iTCP:8766 -sTCP:LISTEN` 与 Desktop launch log，然后 FAIL。
- [ ] 最终 DMG App 首启/二启继续要求 authenticated 8766 ping、task-scoped DataRoot、`~/Documents/acceptance` 不存在、metadata exact-head、主程序/Sidecar arm64、codesign 与 DMG detach 全部 PASS。
- [ ] Windows 已通过的 Uvicorn graceful managed-stop 不得因本次 macOS Gate 修改回退。

### 新增或修改的真机验收

- [ ] 新精确 Artifact 在 M5 上完整替换安装后，退出和再次启动均不得留下上一实例 Sidecar 或 8766 listener；最终退出后可正常清理任务临时根。

### 主人肉眼确认

- [ ] 本轮不新增主人操作；真机仍只需要确认首次体验、首页智能化与必要授权边界。

### 回归项

- [ ] 不允许只凭 state 消失判定 Runtime 已退出。
- [ ] 不允许全局清理 LingJi/Codex/其他 AI 进程。
- [ ] 不放宽 `LINGJI_ACCEPTANCE_DATA_ROOT`、认证 Secret、Release exact-head 或 Windows 共用主线。

### 清理与回滚

- 临时数据仅在 task root；成功后清理普通日志、挂载点、重复 Artifact 与临时 Runtime。
- 回滚只允许恢复 Gate 等待逻辑，不得回退 Sidecar 的 Uvicorn graceful shutdown bridge。

### 最终报告

- 报告路径：`docs/TEST_REPORTS/PR88_M5_MACOS_GATE_EXIT_VERIFICATION.md`
- PR #88 保持 Draft，直到新精确 Artifact 的真实 M5 复验 PASS。

---

## 2026-08-12 · PR #88 Phase 4 · Sidecar 真实退出生命周期与最终 DMG 收口

- 产品分支：`feature/owner-autopilot-ui-codexpp`
- 产品 Commit：`pending final closeout head`
- 影响模块：packaged Sidecar 生命周期、macOS 最终 DMG 首启/二启隔离 Gate、验收清理。
- 风险等级：P0（最终 DMG 可卸载性与 Runtime 生命周期真实性）。
- 用户可感知变化：无新增交互；修复仅保证后台 Sidecar 真正退出后才宣告停止，避免验收或退出阶段残留进程占用安装介质。
- 数据或安全边界变化：停止仍使用精确 `instance_id` 的 task-scoped request，不扩大进程清理范围，不使用全局 kill/killall。

### 新增或修改的自动验收

- [ ] `tests/test_packaged_control_api.py`：匹配 stop request 被消费且 SIGTERM 已发送后，只要进程尚未真实退出，`sidecar-state.json` 必须继续存在；不再保护“收到停止请求即删除 state”的旧错误行为。
- [ ] `macOS Desktop Gate`：最终 DMG App 首启/二启必须 authenticated 8766 ping；每次退出后等待真实 Sidecar state 消失，再执行 DMG detach，`Resource busy` 不得出现。
- [ ] 最终 DMG 内 App metadata、主程序 arm64、Sidecar arm64、task-scoped DataRoot 与 `Documents/acceptance` 隔离合同继续全部 PASS。

### 新增或修改的真机验收

- [ ] 新精确 Artifact 在 M5 上覆盖安装后，退出/再次启动不得留下上一实例 Sidecar；8766 生命周期与任务根隔离保持正确。

### 回归项

- [ ] 不允许以 state 提前删除伪装进程已经退出。
- [ ] 不允许为了卸载 DMG 使用全局进程清理。
- [ ] 不放宽 `LINGJI_ACCEPTANCE_DATA_ROOT`、身份、认证状态或 Secret 边界。

### 清理与回滚

- 临时数据仅使用任务根；失败时保留最小日志后删除本轮临时 Runtime。
- 回滚仅恢复生命周期实现，不得回退到 state 提前消失的语义。

### 最终报告

- 报告路径：`docs/TEST_REPORTS/PR88_M5_SIDECAR_LIFECYCLE_FIX.md`
- PR #88 保持 Draft，直到新精确 Artifact 的真实 M5 复验 PASS。

---

## 2026-08-12 · PR #88 Phase 4 · 安全认证状态同步

- 产品分支：`feature/owner-autopilot-ui-codexpp`
- 产品 Commit：`pending unified closeout head`
- 影响模块：macOS Keychain、Windows Credential Manager、`lingji_state.db`、8766 Local Control API、Desktop Overview、Autopilot、验收证据导出。
- 风险等级：P0（认证秘密与状态边界）。
- 用户可感知变化：首页只显示连接结论；凭据内容、长度、路径和请求头不会显示或同步。

### 新增或修改的自动验收

- [ ] fake CredentialStore 的 get/set/delete/exists 与错误映射；CI 不触碰真实系统凭据。
- [ ] AuthStatus 的 verifying、verified、expired、invalid、permission_insufficient 状态及重启恢复。
- [ ] 8766 `/api/auth/status`、Overview 和 Autopilot 只消费非敏感结论。
- [ ] `LOCAL_AUTH_STATUS_PR88.json` 仅由 allowlist 导出，伪造 Token/Cookie/Authorization Header 必须无法进入；仓库 secret scan PASS，`secret_export_count=0`。
- [ ] macOS / Windows 使用相同状态模型；真实 Keychain / Credential Manager 只在对应真机验收验证。

### 清理与回滚

- 不创建凭据文件、SQLite Secret 或 Git Secret。回滚仅移除状态层代码；不得删除主人已有系统凭据。
- 最终报告：`docs/TEST_REPORTS/PR88_M5_PHASE4_FAILURE_REPAIR.md`；状态快照：`docs/TEST_REPORTS/evidence/LOCAL_AUTH_STATUS_PR88.json`。

### Isolation guard follow-up

- [ ] 当 acceptance task root 与传入 root 不一致时，必须在校验 task root 自身的 Windows C: 盘策略前报告 `LINGJI_ACCEPTANCE_DATA_ROOT` 合同错误；Windows 回归与最终 DMG 首启/二启 Gate 必须 PASS。
- 回滚：仅恢复既有 validation order；不得放宽 task-scoped acceptance root 的精确匹配。
- [ ] DMG isolation Gate 每次启动后必须向该 runtime 的 `sidecar-stop-request.json` 发送 instance-scoped stop，再卸载 DMG；不得以全局杀进程方式清理。

---

## 2026-08-11 · PR #88 Phase 3 · Autopilot 启动架构与真机阻断修复

- 产品分支：`feature/owner-autopilot-ui-codexpp`
- 产品 Commit：`pending`
- 来源真机报告：`acceptance/macos-m5-ux-reacceptance-bf9da9ff` / `26946c58cd96158c6318d5f9b5b8f83a91c62aa9`
- 来源结论：`FAIL / DO NOT MERGE`
- 影响模块：macOS/Windows Desktop bootstrap、首次启动、Runtime 数据隔离、首页 Owner Autopilot、AI 来源接管、macOS/Windows Release identity、M5 安装替换协议、Desktop smoke
- 风险等级：P0
- 用户可感知变化：Mac 正常首次启动不再要求主人选择资料目录；灵机自动选择平台安全默认目录、自动启动与恢复。首页不再展示技术 Metric 大面板，AI 来源无授权事项时降为安静的后台接管状态。只有读取真实正文、永久记忆和不可逆操作进入主人决策。
- 数据或安全边界变化：新增 `LINGJI_ACCEPTANCE_DATA_ROOT` 作为仅验收进程使用的 task-scoped 临时根；普通启动不得复用历史 Acceptance workspace；自动化不扩大真实正文读取、永久记忆批准或不可逆重建权限。

### 本轮必须关闭的真机缺陷

- [ ] `M5-IDENTITY-001`：PR Artifact 内嵌 Commit 必须精确等于产品 Head，不得使用 PR merge commit。
- [ ] `M5-UX-002`：Mac 首次启动必须自动确定安全资料目录并继续，手动路径只能作为自动准备失败后的兜底。
- [ ] `M5-ISOLATION-001`：验收 Runtime 所有写入必须在任务单指定 `LINGJI_ACCEPTANCE_DATA_ROOT` 下，`~/Documents/acceptance` 等任务根外新增目录数量必须为 0。
- [ ] `M5-INSTALL-001`：禁止 overlay 写入旧 `.app`；必须整体备份旧 App、完整替换新 App、签名复验失败时整体回滚。

### 新增或修改的自动验收

- [ ] `desktop/lingji-control/scripts/assistant-autopilot-smoke.mjs`：验证自动 bootstrap、AI 元数据被动接管、正文授权边界、永久记忆边界和 acceptance override。
- [ ] `desktop/lingji-control/scripts/observation-first-ui-smoke.mjs`：禁止手选目录重新成为正常首次启动主流程；禁止首页恢复技术 Metric 大面板。
- [ ] `desktop/lingji-control/scripts/macos-release-smoke.mjs`：验证 macOS 自动默认目录、task-scoped acceptance override 与 Release exact-head identity 配置。
- [ ] Rust unit tests：验证 `auto_selected` bootstrap 合同、workspace/path 合同与 acceptance 隔离规则。
- [ ] GitHub `tests`：Python 3.11/3.12、Windows Python、MCP、Desktop smoke、React build、Tauri 配置全部 PASS。
- [ ] GitHub `P0 Windows Gate`：同一产品代码不得破坏 Windows Runtime、首次配置和 Rust/Tauri 基线。
- [ ] GitHub `Windows Desktop Release Baseline`：checkout 与 release metadata 必须使用同一精确 PR Head。
- [ ] GitHub `macOS Desktop Gate`：显式 checkout PR Head；`.app` 与最终 DMG 主二进制必须嵌入该精确 SHA；Sidecar、API boot、DMG mount 全部 PASS。
- [ ] `acceptance-doc-sync` / `local-execution-handoff`：治理门禁必须 PASS。

### 新增或修改的真机验收

- [ ] 使用新精确 Artifact，验收前通过任务单设置 `LINGJI_ACCEPTANCE_DATA_ROOT="$ACCEPTANCE_ROOT/runtime-data"`，并在 Runtime 启动前注入。
- [ ] 旧 `/Applications/灵机.app` 必须整体移入任务临时备份；完整复制新 App；`codesign --verify --deep --strict` PASS 后才启动，禁止 overlay copy。
- [ ] Release Metadata / App 内嵌 commit 与任务单产品 Head 完全一致。
- [ ] 首次打开不手动选择 DataRoot 即可自动准备并进入首页；若自动准备失败，才允许出现手动路径兜底。
- [ ] 所有 SQLite、Qdrant、token、logs、raw、vault、backup 写入只出现在 task-scoped runtime-data；`~/Documents/acceptance` 不得因本轮创建。
- [ ] 首页无主人事项时明确“无需操作”；技术异常显示为后台自动处理中，不进入主人决策数。
- [ ] AI 来源识别不把“2 个工具 / 4400 条工作记录元数据”作为主要任务卡；无授权事项时只以被动状态显示。
- [ ] 合成导出候选只展示一次清晰授权；未授权真实正文读取次数为 0，永久记忆自动批准为 0。
- [ ] 生命周期完成启动 → healthy → 退出 → Core/8766 释放 → 同任务根再次启动 → healthy。

### 主人肉眼确认

- [ ] 第一次打开无需理解 DataRoot、Workspace、Qdrant、Embedding、端口即可进入可用状态。
- [ ] 首页首先告诉主人“有没有必须由我决定的事”，而不是展示后台技术指标或大量扫描计数。
- [ ] 没有主人事项时界面足够安静，不需要为了确认系统正常而点按钮。
- [ ] 真正权限边界出现时，动作清晰且只有一个主要选择。
- [ ] 主人明确确认相比 bf9da9ff 已达到可接受的智能化/自动化主流程；未确认前 PR #88 保持 Draft。

### 回归项

- [ ] 未经主人授权不得读取真实 AI 对话/导出正文。
- [ ] 不允许自动批准永久记忆。
- [ ] 不允许自动删除或重建 Production Qdrant。
- [ ] 不允许自动修改外部 AI 客户端配置。
- [ ] Windows 与 macOS 必须保持同一核心代码，不创建 Mac 特供业务实现。
- [ ] 自动准备失败必须真实降级到手动兜底，不能伪造成功。
- [ ] Production DataRoot / Vault 污染为 0。

### 清理与回滚

- 临时数据前缀：`MACOS-M5-AUTOPILOT-PHASE3-<short-sha>`。
- 安装方式：`whole_bundle_replace`，禁止 overlay。
- 临时 App 备份：仅存于 `$ACCEPTANCE_ROOT/app-backup`；新版本 PASS 后随任务根删除；新版本 FAIL 时先恢复旧 App并验证签名。
- Runtime 测试根：`$ACCEPTANCE_ROOT/runtime-data`，结束后整体删除。
- 失败证据仅保留最小必要内容；成功日志、截图、DMG、重复 ZIP、临时 Qdrant/SQLite 全部按 M5 协议清理。

### 不在范围

- 未授权静默导入 AI 正文。
- 自动批准永久记忆。
- 无备份执行破坏性 Repair。
- 自动修改第三方 AI 客户端配置。
- 本轮不把所有高级工具页面重做一遍；目标是启动主链和日常首页智能化。

### 最终报告

- 实施报告：`docs/TEST_REPORTS/OWNER_AUTOPILOT_PHASE3_IMPLEMENTATION.md`
- M5 报告：`docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_<short-sha>.md`
- M5 报告分支：`acceptance/macos-m5-autopilot-phase3-<short-sha>`
- PR #88：保持 Draft，直到精确 Artifact、M5 真机和主人体验全部 PASS。

---

## 2026-08-11 · PR #88 · Owner Autopilot UI 与本机 AI 自动发现

- 产品分支：`feature/owner-autopilot-ui-codexpp`
- 产品 Commit：`b34a8752507c99ef929e98769fe37276166aa98d`
- 影响模块：桌面首页、首次启动引导、Codex 工作记录、AI 工具元数据发现、ChatGPT/Codex 导出候选规划与授权导入、Desktop smoke
- 风险等级：P1
- 用户可感知变化：首页优先解释“发现了什么、正在做什么、需要主人决定什么”；Codex 的 Session 计数改为“工作记录”并解释来源；首次启动不再要求主人先理解 DataRoot、Qdrant 或 Windows 专属非 C 盘术语。
- 数据或安全边界变化：自动发现只读取已知位置和文件元数据；不读取真实对话正文、不跟随符号链接、不修改外部 AI 客户端、不自动批准永久记忆；读取发现的导出包前仍需要主人一次明确授权。

### 新增或修改的自动验收

- [x] `python -m pytest -q tests/test_assistant_hub_discovery.py tests/test_assistant_hub_imports.py`：本地 `9 passed`，验证只读发现、路径脱敏、候选白名单、候选失效重验与非相关文件排除。
- [x] `node desktop/lingji-control/scripts/assistant-autopilot-smoke.mjs`：验证首页自动发现、15 秒轮询、授权边界、Codex 工作记录解释与高级技术信息折叠合同。
- [x] Python `py_compile` 与 TypeScript `transpileModule`：验证新增 Python 与 TS/TSX 可解析。
- [ ] GitHub `tests`：Python 3.11/3.12、Windows Python、Desktop UI smoke/build、MCP 与其他仓库回归必须 PASS。
- [ ] GitHub `P0 Windows Gate`：不得破坏已验收的 Windows Runtime、路径、安装和 UI 基线。
- [ ] GitHub `macOS Desktop Gate`：Apple Silicon 构建、Tauri、Sidecar 与 DMG 门禁必须 PASS。
- [ ] `acceptance-doc-sync` 与 `local-execution-handoff`：本条记录与后续真机任务必须通过治理门禁。

### 新增或修改的真机验收

- [ ] 使用 PR #88 精确 Head 生成的新 macOS arm64 Artifact 覆盖安装；首次打开必须只给出一个可理解的主要动作“选择存放位置 / 开始使用灵机”，DataRoot、acceptance 等技术细节默认折叠。
- [ ] Mac 首次使用页面不得出现要求主人理解“非 C 盘”的 Windows 专属主文案；目录选择、保存配置、启动 Core 和重新打开必须可完成。
- [ ] 首页启动后无需点击“扫描”即可自动识别本机 Codex；若存在 Claude Code / WorkBuddy，也应只读显示其真实识别状态。
- [ ] 自动发现阶段检查日志/API/测试资料，确认真实对话正文读取次数为 0，Core Memory 自动新增为 0。
- [ ] 准备一个任务专用的合成 ChatGPT/Codex 导出候选：UI 应先显示文件名/大小等元数据，主人一次授权后立即进入正式处理队列，不再要求输入路径或二次提交。
- [ ] 打开 Codex 工作记录页：若显示 `2`，页面必须明确说明这是 2 条本机识别到的 Codex Session 工作记录，不是灵机新建的 2 个聊天窗口；列表应自动刷新。
- [ ] Windows 使用同一代码基线复验首次配置、自动发现、首页、Codex 工作记录和授权导入，不得因 Mac 文案优化破坏 Windows 路径选择或 Runtime 启动。

### 主人肉眼确认

- [ ] 主人首次打开后不看技术文档，能够直接理解灵机下一步会自己做什么以及自己只需要决定什么。
- [ ] 主人在首页能快速回答四个问题：`发现了什么`、`正在做什么`、`已经自动处理了什么`、`现在有什么必须由我决定`。
- [ ] 主人看到 Codex 工作记录数量时不再把它理解为灵机莫名创建的聊天窗口。
- [ ] Qdrant、Embedding、DataRoot、端口、MCP 等技术信息不会占据日常主流程，需要时仍能从“系统健康细节 / 高级工具”查看。

### 回归项

- [ ] 未经主人授权不得读取任何真实 ChatGPT/Codex 导出正文。
- [ ] 自动扫描不得递归全盘、不得跟随符号链接、不得向前端暴露本机绝对路径。
- [ ] 不允许自动批准永久记忆；现有人工记忆审核链保持有效。
- [ ] Runtime、Qdrant、SQLite、MCP、Sidecar 所有权与生命周期合同不得因本轮 UI/发现优化改变。
- [ ] Windows 与 macOS 使用同一产品代码；不得为 Mac 创建独立业务分支或复制核心逻辑。
- [ ] 自动发现失败时 UI 必须说明会继续重试，不得把未知/失败显示为“全部正常”。

### 清理与回滚

- 临时数据前缀：后续 M5 / Windows 真机任务使用任务 ID 独立前缀，不使用主人 Production 根目录。
- 覆盖安装或迁移方式：使用精确 PR #88 Artifact 覆盖当前验收版本；不卸载主人正式数据。
- 临时备份删除条件：真机报告和远程回执确认后按现有任务清理合同删除。
- 测试数据清理方式：只删除本轮任务创建的合成导出包、临时 DataRoot、日志和安装验证残留；不得删除主人真实 Vault、Production 数据或 AI 客户端配置。
- 回滚：回退 PR #88 的 Owner Autopilot UI / assistant_hub 变更；不得通过关闭 acceptance 门禁或放宽内容授权边界回滚。

### 不在范围

- Codex 原始 Session / JSONL 的静默正文自动导入。
- Claude Code / WorkBuddy 对话正文导入。
- 自动下载或安装 Ollama / Embedding 模型。
- 自动重建 Production Qdrant。
- 自动批准永久记忆。
- 修改外部 AI 客户端配置而不经主人授权。

### 最终报告

- 实施与自动测试报告：`docs/TEST_REPORTS/OWNER_AUTOPILOT_UI_CODEXPP_IMPLEMENTATION.md`
- 真机报告：在精确 CI / Artifact 通过后创建 `docs/TEST_REPORTS/MACOS_M5_OWNER_AUTOPILOT_ACCEPTANCE_<short-sha>.md`
- 真机报告分支：`acceptance/macos-m5-owner-autopilot-<short-sha>`
- PR #88 保持 Draft，直到 CI、Mac/Windows 回归与主人可理解性检查完成。

---

## 2026-08-01 · PR #60 后续 · 代码发布验证临时目录安全清理修复

- 产品分支：`fix/cleanup-code-validation-workspace`
- 产品 Commit：`pending`
- 来源阻塞：`PR60-CODE-RELEASE-VALIDATION-A90A18A6 / BLOCKED_POST_CLEANUP`
- 影响模块：本机任务治理、安全清理工具、代码发布链结果回执
- 风险等级：P1
- 用户可感知变化：不需要重跑已通过的 15 套 release 验证；修复后只补做安全清理、最终回执和远程复读。
- 数据或安全边界变化：不触碰产品 Runtime、UI、Vault、数据库、Qdrant、真实资料或用户 AI 配置；仍只允许删除任务 ID 推导出的精确临时目录。

### 新增或修改的自动验收

- [x] `python -m pytest -q tests/test_cleanup_acceptance_workspace.py`：本地隔离验证 `10 passed`。
- [ ] GitHub `tests`：验证 Python 3.11、3.12、Windows 和完整仓库回归。
- [ ] `acceptance-doc-sync`：验证脚本变化已同步本记录。

### 新增或修改的真机验收

- [ ] 使用 `PR60-CODE-RELEASE-VALIDATION-A90A18A6` 对 `D:\codex\LingJiValidation\PR60-CODE-a90a18a6` 先 dry-run。
- [ ] dry-run 清单必须只包含该任务创建的 product、report、release、日志、缓存和证据目录。
- [ ] 显式 `--execute` 后目标目录必须不存在，相邻目录和主人数据保持不变。
- [ ] 更新原报告与结果回执为最终 `PASS`，再次 push 并远程复读。

### 主人肉眼确认

- [x] 不需要主人参与；本任务不安装、不启动 UI、不读取真实数据。

### 回归项

- [ ] 不允许通配符删除。
- [ ] 不允许删除清理根目录本身。
- [ ] 不允许删除根目录外或非直接子目录。
- [ ] 任务类型、PR号和 8 位 Commit 身份必须与目录名精确匹配。
- [ ] 旧 `D69874AF` 记忆质量任务仍能清理两个明确登记的 `1c514877` 历史目录。
- [ ] 不跟随符号链接或 Windows reparse point。

### 清理与回滚

- 当前清理根：`D:\codex\LingJiValidation`
- 当前目标：`PR60-CODE-a90a18a6`
- 安全入口：`scripts/cleanup_acceptance_workspace.py`
- 回滚：回退本次策略和测试；不得恢复宽泛白名单或手工强删。

### 不在范围

- 不重跑产品代码、Desktop、Rust/Tauri 或 Windows release 验证。
- 不生成或安装正式 GitHub Artifact。
- 不解决 PR #60 与 master 的后续合并冲突。
- 不进入 Day 0、UI 或真实数据验收。

### 最终报告

- 修复报告：`docs/TEST_REPORTS/PR60_CODE_VALIDATION_CLEANUP_POLICY_FIX.md`
- 原验证报告：`docs/TEST_REPORTS/PR60_CODE_RELEASE_VALIDATION_a90a18a6.md`
- 原报告分支：`acceptance/pr60-code-release-validation-a90a18a6`

---

## 2026-07-31 · PR #60 · d69874af 引导修复复验与真实数据记忆质量试运行

- 产品分支：`feature/unified-ai-memory-connectors`
- 产品 Commit：`d69874afd8def42a40c4a5cc5e678a71921d44b5`
- 固定 Artifact：`lingji-windows-0.1.0-d69874af`
- Artifact ID：`8762312712`
- Artifact ZIP SHA256：`6bf1f591502617c400ce482f6beb0d5e430a172cd036137bb4a39cae2cbf4cb4`
- 安装器 SHA256：`d62867b7b7c90bee8273b3cf5720f53099c266897ce95d0e42224deae31bf262`
- 影响模块：首次使用引导、AI 软件与历史目录发现、Codex 连接状态机、Embedding/Qdrant 诊断、Day 0、真实数据试运行、报告提交和本地清理
- 风险等级：P0
- 用户可感知变化：页面必须给出唯一当前动作，主动解释扫描结果和可导入范围，不再同时显示“配置正常”和“命令不存在”，向量问题必须展示具体原因与处理入口。
- 数据或安全边界变化：Day 0 未 PASS 禁止读取真实资料；历史目录只读取元数据，读取内容前必须获得主人授权；Production 保持只读和物理隔离。

### 已通过的自动验收

- [x] `acceptance-doc-sync #43`
- [x] `local-execution-handoff #35`
- [x] `tests #1138`
- [x] `P0 Windows Gate #258`
- [x] `Windows Desktop Release Baseline #142`
- [x] 旧模糊文案“已设置，等待测试”回归断言。
- [x] 配置文件、客户端命令和真实连接三个状态分离。

### 新增或修改的真机验收

- [ ] 开始前使用 `scripts/cleanup_acceptance_workspace.py` 清理旧任务专用临时目录；脚本必须先 dry-run，再显式 `--execute`，且只能操作任务单允许的精确目录。
- [ ] Day 0 在任何真实数据导入前完成：固定 Artifact、覆盖安装、Runtime、8766/8767、MCP 鉴权、真实 Codex 调用、候选边界、A-01、三轮 Core 重启和 Windows 重启。
- [ ] 页面始终只有一个明确主要动作；扫描完成后主动说明发现的软件和历史目录元数据。
- [ ] 发现历史目录后主动询问是否查看或导入，明确说明当前支持与不支持的格式。
- [ ] 配置文件存在、`codex` 命令可用和真实 MCP 连接必须分别显示；缺少命令时不得显示 ready。
- [ ] Embedding/Qdrant 必须显示配置模型、激活模型、缺失模型、最近错误、Qdrant 状态、是否需要重建和当前可执行入口。
- [ ] 主人明确授权后，Stage 1 只导入 1 部剧本、1 份 Codex 报告、少量 ChatGPT 历史和 1 个明确 Obsidian 目录。
- [ ] Stage 1 无 P0/P1 后才逐步扩展到最多 10 部授权剧本和其他授权资料。
- [ ] 至少执行 20 道质量题：精确事实不少于 8、跨文档比较不少于 4、来源核验不少于 4、负面边界不少于 4。

### 主人肉眼确认

- [ ] Checkpoint A：安装和首次打开，无黑窗，首页正常，唯一下一步清楚，状态文案能区分。
- [ ] Checkpoint B：Codex 能看到 LingJi 工具、真实调用成功、返回内容正确。
- [ ] Checkpoint C：主人亲自批准一个测试候选、拒绝一个测试候选，页面可理解。
- [ ] Checkpoint D：Windows 重启后无黑窗，灵机恢复且页面可操作。
- [ ] Checkpoint E：主人至少抽查 10 道质量题，确认答案与来源评分。

### 强制回归项

- [ ] Day 0 未 PASS 时禁止导入真实资料。
- [ ] 未经主人授权不得读取或导入任何真实目录内容。
- [ ] 剧本人物、剧情和台词不得进入主人个人事实。
- [ ] 不存在的问题必须承认未知，不得拿相似资料冒充。
- [ ] 候选未批准前 Core Memory 不增加，拒绝候选不进入永久记忆。
- [ ] A-01 隔离不得读取或修改主人真实 `CODEX_HOME`。
- [ ] 覆盖安装和连接器回滚不得破坏主人数据或配置。
- [ ] Windows 重启后 Runtime、MCP、Workspace、DataRoot 和 Vault 恢复。
- [ ] 开始前和结束后临时目录必须清理；清理失败时只能 BLOCKED，不得绕过安全策略。

### 质量阈值

```text
quality_score >= 90%
source_accuracy >= 95%
false_positive_rate <= 5%
Codex MCP 真实调用成功率 >= 95%
重复正式内容 = 0
Production 污染 = 0
人工审核链成功率 = 100%
Windows 重启后恢复 = 100%
```

### 清理与回滚

- 当前临时数据前缀：`PR60_MEMORY_TRIAL_D69874AF_`
- 当前临时根目录：`D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-d69874af`
- 必须清理的历史临时目录：`D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-1c514877`、`D:\codex\LingJiAcceptance\PR60-1c514877`
- 安全清理入口：`python scripts/cleanup_acceptance_workspace.py --task-id PR60-MEMORY-QUALITY-TRIAL-D69874AF --target <精确目录>`；确认 dry-run 后追加 `--execute`。
- 清理工具拒绝验收根目录本身、根目录外路径、非白名单目录和不匹配任务身份；不跟随符号链接或 Windows reparse point。
- 覆盖安装方式：固定安装器直接覆盖，不卸载。
- 临时配置副本：每个客户端最多一个，哈希验证后删除。
- 主人授权的真实资料是否保留由主人选择，Codex不得擅自删除。
- 报告第一次远程确认后清理，更新结果回执，再次 push 和远程复读。

### 不在范围

- Codex 原始 Session / JSONL 自动导入。
- Claude Code 和 WorkBuddy 历史导入。
- 自动下载 Embedding 模型。
- 自动重建 Production Qdrant。
- 自动批准永久记忆。
- 远程或公网 MCP。

### 最终报告

- 专项协议：`docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md`
- 任务单：`docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`
- 报告路径：`docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_d69874af.md`
- 报告分支：`acceptance/pr60-memory-quality-trial-d69874af`
- 产品 PR 必须保持 Draft 且不得合并，直到 Day 0、Stage 1、质量指标、主人检查点、远程提交和清理全部满足 PASS。

---

## 2026-07-30 · PR #60 · 1c514877 首轮试运行（历史失败，禁止重跑）

- 产品分支：`feature/unified-ai-memory-connectors`
- 产品 Commit：`1c5148779624910f1c6072d95d6c6f6822f631e6`
- 固定 Artifact：`lingji-windows-0.1.0-1c514877`
- Artifact ID：`8723868744`
- 状态：历史 `FAIL / BLOCKED_SUBMISSION`，已被 2026-07-31 的 d69874af 条目取代。
- 已知缺陷：`D0-UX-001` 页面缺少统一引导；`D0-CODEX-002` 配置状态和命令状态矛盾；`BLOCKED_POST_CLEANUP` 旧临时目录未清理。
- 历史报告：`docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_1c514877.md`
- 历史报告分支：`acceptance/pr60-memory-quality-trial-1c514877`
- 当前不得再按该产品 Commit、Artifact 或报告路径执行。

---

## 2026-07-30 · 本机任务信箱与结果回执硬门禁

- 产品分支：`master`
- 产品 Commit：`governance-only`
- 影响模块：仓库治理、Codex 本机执行交接、报告提交、远程复读、本地垃圾清理、GitHub Actions
- 风险等级：P1
- 用户可感知变化：用户只需告诉 Codex 去看任务单，或告诉 ChatGPT Codex 已完成；不再复制长指令、解释 Git、上传报告或排查分支。
- 数据或安全边界变化：不改变产品数据；明确禁止清理主人 DataRoot、Vault、正式记忆和用户 AI 配置，只清理本轮临时验收垃圾。

### 新增或修改的自动验收

- [x] `python scripts/check_local_execution_handoff.py`：校验任务单、结果回执、身份一致性、开始/结束清理、远程确认和报告 Commit 字段。
- [x] `python -m pytest -q tests/test_local_execution_handoff.py`：覆盖 PENDING、COMPLETED、远程确认缺失、清理失败、身份不一致和阻塞提交。
- [x] `local-execution-handoff` Workflow：在 `master`、开发分支和 `acceptance/**` 报告分支执行；报告分支结果不是 `COMPLETED` 时失败。

### 新增或修改的真机验收

- [x] Codex 只读取 `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md` 中 `status: ACTIVE` 的任务，不从聊天或本机残留推断。
- [x] 每次开始前整体清理上一轮临时验收目录、Artifact、日志、截图、fixture、checkpoint、临时配置副本和 worktree，再释放 8766/8767。
- [x] 报告 push 后使用 `git ls-remote` 和 GitHub API 重新读取远程分支、Commit、报告、结果回执和 PR 评论。
- [x] 第一次远程确认后清理本轮本地垃圾，更新结果回执，再次 push 和远程复读。

### 主人肉眼确认

- [x] 用户只负责下达“去看任务单干活”或“Codex 已完成”，不负责 Git、上传、报告路径和清理操作。

### 回归项

- [x] 禁止把本机生成报告误写成已经上传。
- [x] 禁止 `git push` 命令执行后未复读远程就宣布完成。
- [x] 禁止长期堆积旧验收目录、重复安装包、日志、截图、fixture、checkpoint、配置副本和 worktree。
- [x] 禁止清理主人正式数据或其他任务数据。

### 清理与回滚

- 临时数据前缀：由 `LOCAL_EXECUTION_TASK.md` 每个任务单独声明。
- 覆盖安装或迁移方式：本次为治理变更，不涉及产品安装。
- 临时备份删除条件：远程报告第一次确认后删除；只保留哈希。
- 测试数据清理方式：本机任务结束时删除任务单指定临时根目录和带任务前缀的数据。

### 不在范围

- 不改变 LingJi 产品 Runtime、UI、数据库、记忆或连接器功能。
- 不代替具体任务的真机验收标准。
- 不要求用户学习 Git 或参与报告提交。

### 最终报告

- 规则权威：`docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md` 与 `docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md`
- 自动门禁：`.github/workflows/local-execution-handoff.yml`

---

## 2026-07-29 · PR #60 · P0-A 与统一 AI 记忆连接器重新真机验收（历史方案）

- 产品分支：`feature/unified-ai-memory-connectors`
- 产品 Commit：`1c5148779624910f1c6072d95d6c6f6822f631e6`
- 固定 Artifact：`lingji-windows-0.1.0-1c514877`
- Artifact ID：`8723868744`
- 状态：被后续真实数据试运行方案取代，保留为历史记录。
- 已通过自动验收：`tests #1081`、`P0 Windows Gate #240`、`Windows Desktop Release Baseline #129`、A-01 回归。
- 原计划报告：`docs/TEST_REPORTS/PR60_OWNER_CODEX_FULL_REACCEPTANCE_1c514877.md`
- 原计划分支：`acceptance/pr60-owner-1c514877`
- 当前不得再按该旧路径执行。

---

## 2026-07-29 · PR #62 · 建立统一 Codex 验收权威

- 产品分支：`docs/acceptance-governance`
- 治理实现与门禁验证基线：`e43da870bc755321f5bd0db4a40aca31df91124d`
- 影响模块：仓库治理、Codex 执行入口、CI 文档同步门禁
- 风险等级：P1
- 用户可感知变化：Codex 拉取代码后可直接从仓库读取当前验收指令，不再依赖聊天中复制的旧指令。
- 数据或安全边界变化：没有产品数据变更；新增规则要求临时证据和配置副本在报告提交后清理。

### 新增或修改的自动验收

- [x] `python scripts/check_acceptance_sync.py`
- [x] `python -m pytest -q tests/test_acceptance_sync.py`
- [x] GitHub Workflow `acceptance-doc-sync #1`
- [x] GitHub Workflow `tests #1082`
- [x] GitHub Workflow `P0 Windows Gate #241`

### 新增或修改的真机验收

- [x] Codex 从仓库读取验收权威，不依赖聊天历史。
- [x] 代码变化后必须同步验收标准。
- [x] 报告提交后清理临时 Artifact、日志、截图、fixture 和配置副本。

### 主人肉眼确认

- [x] 主人明确要求仓库成为验收指令权威。

### 回归项

- [x] 不允许代码变更后遗漏验收标准更新。
- [x] 不允许为了补报告移动已打包产品 Head。
- [x] 不允许长期堆积重复验收垃圾。

### 清理与回滚

- 临时数据前缀：`ACCEPTANCE_GOVERNANCE_`
- 不涉及产品安装或正式数据。

### 不在范围

- 不改变 LingJi 产品功能。
- 不替代模块测试报告。
- 不自动合并产品 PR。

### 最终报告

- 报告路径：`docs/TEST_REPORTS/ACCEPTANCE_GOVERNANCE_IMPLEMENTATION.md`
- 治理 PR：`#62`