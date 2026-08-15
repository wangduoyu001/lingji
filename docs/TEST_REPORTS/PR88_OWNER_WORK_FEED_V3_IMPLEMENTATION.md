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

七阶段流程仍然作为内部生命周期语义存在，但不再以 7 张汇总卡作为首页主结构。阶段只附着在真实资料对象上。

## 4. 数据投影

新增 `desktop/lingji-control/src/ownerWorkFeed.ts`，它是**纯派生选择器**，不持久化任何新事实：

- memory row 与 queue result 通过安全 `relative_path` 关联；
- queue 的绝对 `input_path` 只允许提取文件名作为最后兜底，不输出绝对路径；
- 不投影 `payload.text / transcript / html / selected_text`；
- 不投影 raw snapshot 路径；
- 未知内部 event 不进入主人活动流；
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

## 5. 已修改文件

```text
desktop/lingji-control/src/pages/OverviewPage.tsx
desktop/lingji-control/src/ownerWorkFeed.ts
desktop/lingji-control/src/OwnerWorkFeed.css
desktop/lingji-control/src/App.tsx
desktop/lingji-control/scripts/owner-work-feed-smoke.mjs
desktop/lingji-control/scripts/observation-first-ui-smoke.mjs
desktop/lingji-control/scripts/memory-progress-smoke.mjs
desktop/lingji-control/scripts/macos-release-smoke.mjs
desktop/lingji-control/scripts/assistant-autopilot-smoke.mjs
desktop/lingji-control/scripts/run-smoke-suite.mjs
```

旧 `OwnerHomeV2.css` 已移除，避免失败的信息架构继续作为活跃样式合同存在。

## 6. 自动测试合同

`owner-work-feed-smoke.mjs` 覆盖：

1. 已完成并索引的真实资料必须显示具体标题、来源、“灵机已做”和“下一步”；
2. 处理中、尚未生成 memory row 的 queue job 仍必须显示具体资料；
3. `pending_review` 必须明确 `ownerActionRequired=true`；
4. 统计有 2 份但明细为空必须 `detailsState=unavailable`；
5. 投影 JSON 不得出现绝对私人路径、正文或 raw snapshot 路径；
6. 未知内部事件不得冒充主人可见活动。

同时更新：

- `observation-first-ui-smoke.mjs`：禁止 `buildWorkflow` / 七阶段汇总卡回归为首页主结构；
- `memory-progress-smoke.mjs`：统计与质量边界下沉到折叠高级状态；
- `macos-release-smoke.mjs`：继续锁定 credential 不上首页、M5 release identity 与窗口恢复合同；
- `assistant-autopilot-smoke.mjs`：首页必须明确显示 AI 历史授权、候选记忆确认和向量重建等具体主人动作；
- `run-smoke-suite.mjs`：加入真实 Owner Work Feed 数据语义测试。

## 7. 验收标准

新 M5 不再问“七阶段是不是显示了”，而是给真实数据后要求主人能在首页直接回答：

```text
1. 目前有哪些具体资料？
2. 每份资料灵机已经做了什么？
3. 每份资料下一步是什么？
4. 哪些需要我行动，哪些不用？
```

任一问题无法直接回答即 `FAIL / DO NOT MERGE`。

## 8. 技术回归边界

本轮不得破坏：

- Apple Silicon arm64 / strict codesign；
- exact product commit / Artifact identity；
- Acceptance / Production 物理隔离；
- `secret_export_count=0`；
- CredentialStore / AuthStatus 边界；
- first/second exact-instance stop；
- `state gone + PID gone + port free`；
- Windows 与 macOS 同一业务 UI/Runtime 主线。

## 9. 验证状态

当前代码已进入开发分支 `fix/pr88-owner-work-feed-v3`。

最终结果只有在该分支精确 Head 的 Desktop smoke、TypeScript build、仓库 tests、Windows/macOS release gates 全部通过后才能回填为 PASS。任何 CI 失败必须修复并从新 Head 重跑，不继承旧绿灯。
