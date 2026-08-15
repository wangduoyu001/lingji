# PR #88 · Owner Work Feed v3 实施与验证报告

## 1. 来源失败

上一候选：

```text
Product commit: f3cba4136bd169619277279a55007fcd4ef609f4
macOS Artifact: 9249367672
M5 task: PR88-M5-OWNER-HOME-V2-F3CBA413
Verdict: FAIL / DO NOT MERGE
```

真实主人反馈：

- 只看得到“已收纳 2 份资料”；
- 不知道具体是哪两份资料；
- 不知道灵机已经做了什么；
- 不知道下一步是什么；
- 不知道是否需要主人行动。

对应 `M5-OWNER-HOME-001 / 002 / 003`。

## 2. 根因

不是缺数据，而是首页错误地把真实对象压缩成汇总。

现有后端已经提供：

- `/api/memory/inspector/memories`：真实记忆对象的 `title / relative_path / memory_type / review_status / updated_at`；
- `/api/overview.queue.recent`：任务的 `source_type / payload / status / result / created_at / completed_at`；
- queue `result`：`created / updated / skipped / indexed / relative_path`；
- `/api/overview.events`：真实系统事件；
- `/api/autopilot/status`：真实 owner actions / background issues。

Owner Home v2 前端只保留了极少 queue 字段，再把数据做成数量、阶段卡和统计卡，导致真实对象身份、系统动作和下一步丢失。

## 3. v3 设计

首页主结构改为：

```text
你现在需要做什么
→ 灵机现在在做什么
→ 资料工作清单（每一份真实资料）
   → 资料标题 / 来源 / 当前状态
   → 灵机已做
   → 下一步
   → 是否需要主人行动
→ 最近真实活动（折叠）
→ 系统统计与高级状态（折叠）
```

七阶段流程仍作为内部生命周期语义存在，但不再以 7 张汇总卡作为首页主结构。阶段只附着在真实资料对象上。

## 4. 数据投影

新增 `desktop/lingji-control/src/ownerWorkFeed.ts`，它是**纯派生选择器**，不持久化任何新事实：

- memory row 与 queue result 通过安全 `relative_path` 关联；
- queue 的绝对 `input_path` 只允许提取文件名作为最后兜底，不输出绝对路径；
- 不投影 `payload.text / transcript / html / selected_text`；
- 不投影 raw snapshot 路径；
- 未知内部 event 不进入主人活动流；
- 缺少 source type 时明确显示“知识库资料”，禁止出现空白来源；
- 没有验证样本时继续不宣称准确率。

如果统计层显示 `expectedDocuments > 0` 但 Memory Inspector 返回 0 个具体对象，投影必须进入：

```text
detailsState: unavailable
```

并明确显示：

```text
系统统计到 N 份资料，但当前无法读取具体明细。
灵机不会用一个数字代替资料列表。
```

禁止再次退化为“只显示 N 份”。

## 5. Owner Action 一致性

首页顶部待办不得和资料行互相打架。

规则：

```text
reviewDecisionCount = max(CurrentWork pending review count, Owner Work Feed concrete owner-required rows)
```

因此：

- 只要任一具体资料已经是 `pending_review`，顶部不能显示“现在不用你做任何事”；
- 顶部必须出现候选记忆待确认；
- 资料行“去确认”必须直达 `memory_review`，不经过模糊的通用状态页；
- 即使另一个异步计数接口还没返回，具体对象本身仍能驱动顶部主人动作。

## 6. 已修改文件

```text
desktop/lingji-control/src/pages/OverviewPage.tsx
desktop/lingji-control/src/ownerWorkFeed.ts
desktop/lingji-control/src/OwnerWorkFeed.css
desktop/lingji-control/src/App.tsx
desktop/lingji-control/scripts/owner-work-feed-smoke.mjs
desktop/lingji-control/scripts/owner-home-action-consistency-smoke.mjs
desktop/lingji-control/scripts/observation-first-ui-smoke.mjs
desktop/lingji-control/scripts/memory-progress-smoke.mjs
desktop/lingji-control/scripts/macos-release-smoke.mjs
desktop/lingji-control/scripts/assistant-autopilot-smoke.mjs
desktop/lingji-control/scripts/run-smoke-suite.mjs
docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md
```

旧 `OwnerHomeV2.css` 已移除，避免失败的信息架构继续作为活跃样式合同存在。

## 7. 自动测试合同

`owner-work-feed-smoke.mjs` 覆盖：

1. 已完成并索引的真实资料必须显示具体标题、来源、“灵机已做”和“下一步”；
2. 处理中、尚未生成 memory row 的 queue job 仍必须显示具体资料；
3. `pending_review` 必须明确 `ownerActionRequired=true`；
4. 统计有 2 份但明细为空必须 `detailsState=unavailable`；
5. 投影 JSON 不得出现绝对私人路径、正文或 raw snapshot 路径；
6. 未知内部事件不得冒充主人可见活动；
7. source type 缺失时必须显示“知识库资料”，不得输出空标签。

`owner-home-action-consistency-smoke.mjs` 覆盖：

1. 顶部 review count 必须合并 `feed.summary.needsOwner`；
2. owner-required 资料行必须直接进入 `memory_review`；
3. “现在不用你做任何事”和“需要你处理”两个状态的选择逻辑必须有明确代码合同。

同时更新：

- `observation-first-ui-smoke.mjs`：禁止 `buildWorkflow` / 七阶段汇总卡回归为首页主结构；
- `memory-progress-smoke.mjs`：统计与质量边界下沉到折叠高级状态；
- `macos-release-smoke.mjs`：继续锁定 credential 不上首页、M5 release identity 与窗口恢复合同；
- `assistant-autopilot-smoke.mjs`：首页必须明确显示 AI 历史授权、候选记忆确认和向量重建等具体主人动作；
- `run-smoke-suite.mjs`：统一执行真实 Owner Work Feed 数据语义和 Owner Action 一致性测试。

## 8. 新 M5 验收标准

新 M5 不再问“七阶段是不是显示了”，而是给真实数据后要求主人能在首页直接回答：

```text
1. 目前有哪些具体资料？
2. 每份资料灵机已经做了什么？
3. 每份资料下一步是什么？
4. 哪些需要我行动，哪些不用？
```

任一问题无法直接回答即 `FAIL / DO NOT MERGE`。

额外硬门：

- 统计显示有资料但明细拿不到时，必须明确报“明细不可用”，不能只显示数量；
- 资料行若标记“需要你处理”，首页顶部必须同步为主人待办；
- 真实 pending review 的“去确认”必须直达审核页面；
- Activity 不允许用未知内部事件制造“系统很忙”的假象。

## 9. 技术回归边界

本轮不得破坏：

- Apple Silicon arm64 / strict codesign；
- exact product commit / Artifact identity；
- Acceptance / Production 物理隔离；
- `secret_export_count=0`；
- CredentialStore / AuthStatus 边界；
- first/second exact-instance stop；
- `state gone + PID gone + port free`；
- Window Recovery 菜单、快捷键、Dock Reopen；
- Windows 与 macOS 同一业务 UI/Runtime 主线。

## 10. 验证状态

开发分支：`fix/pr88-owner-work-feed-v3`，产品修复 PR：`#99`。

已确认在此前 PR Head 上通过：

- Owner Work Feed 真实数据 smoke；
- Desktop smoke；
- React/TypeScript production build；
- Tauri configuration validation；
- `local-execution-handoff`。

首轮 `acceptance-doc-sync` 因缺少 change-specific `CHANGE_ACCEPTANCE_LOG.md` 记录而失败，未降低门禁；现已在本分支顶部补充 Owner Work Feed v3 验收条目，历史记录完整保留。

本报告自身、Owner Action 一致性 smoke 与来源空标签修复完成后，必须以**最新精确 Head**重新跑全部 PR 门禁。旧 Head 的绿灯不继承。

只有该最新 Head 的 Desktop smoke、TypeScript build、仓库 tests、`acceptance-doc-sync`、`local-execution-handoff`、macOS Gate 全部 PASS 后，才允许 squash 合入产品分支。合入后必须再由新的产品 Commit 重新跑双平台 release gates 并生成全新 Artifact；任何旧 Artifact 不得复用。
