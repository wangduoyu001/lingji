# PR #88 Owner Home v2 实施与验证报告

日期：2026-08-15

## 1. 背景与目标

上一轮 M5 真机复验对产品 Commit `2c96b3ec54b066204cad8db75455be24822852a9` 的最终结论为 `FAIL / DO NOT MERGE`。技术身份、签名、Apple Silicon、Acceptance 数据隔离、认证 Secret 边界和第二次启动/停止通过，但以下主人体验项失败：

- `M5-UX-003`：首页看不出系统自动执行了什么；
- `M5-UX-004`：新 UI 与旧版没有明显、可感知差异；
- `M5-UX-005`：信息层级不友好，重点、进度、下一步不清楚；
- “找回主窗口”未获主人通过；
- Memory Progress Dashboard 未获主人通过。

本轮不增加新的事实源，也不通过增加更多统计卡解决问题。目标是把已有真实运行状态重新组织成主人可理解的自动化产品结构。

## 2. 根因

`LocalControlService.overview()` 已经返回现有真实数据：

- `events`：`StateDatabase.events` 最近真实事件；
- `queue`：处理队列与最近任务；
- `memory_progress`：收纳、更新、索引覆盖；
- `memory_runtime`：记忆/向量状态；
- `AutopilotEngine`：当前巡检、后台问题、主人事项与已执行安全修复。

旧首页虽然有这些数据，但视觉上仍主要是并列状态块。用户需要自己把“发现、收纳、解析、审核、索引、取回”拼成一条流程，所以系统看起来仍像监控面板，而不是自动驾驶系统。

## 3. 本轮设计

首页固定三层：

```text
现在发生什么
→ 自动工作流走到哪一步
→ 最近真正自动做过什么
```

### 3.1 自动驾驶主状态

首屏只优先回答：

1. 有没有必须由主人决定的事；
2. 灵机此刻正在处理什么；
3. 如果有异常，是系统正在自行处理还是必须由主人介入。

排序规则：

```text
主人决策 > 正在处理/排队 > 自动恢复异常 > 正常持续运行
```

### 3.2 七阶段真实工作流

首页直接展示：

```text
发现来源 → 收纳 → 解析 → 候选 → 确认 → 索引 → 取回
```

每一阶段只读取现有真实状态：

- 来源发现：现有 assistant_hub 元数据扫描；
- 收纳：memory documents/chunks；
- 解析：queue running/retrying/completed/failed；
- 候选：真实 pending review；
- 确认：真实 owner decision；
- 索引：vector state + coverage；
- 取回：coverage + precision_message。

没有验证样本时继续明确 `not_measured`，不得宣称准确率。

### 3.3 最近自动完成

首页开始直接消费 `overview.events`，把已有 audit event 翻译为用户可读事件，例如：

- 资料已收下并进入后台队列；
- 重复资料已自动跳过；
- 失败任务已重新排队；
- 自动巡检修复并复验；
- 资料收纳暂停/恢复。

这部分是已有 StateDatabase 事件的只读投影，不增加第二个运行状态库。

### 3.4 CurrentWork 降噪

Codex/当前工作面板只有在以下任一条件成立时显示：

- 有真实 activity；
- 有 pending review；
- 当前状态读取真实失败。

空闲时不再常驻一个“系统当前空闲”的 Codex 卡片。

### 3.5 Memory Progress v2

旧版统计块改成：

- 主标题：已收纳多少资料；
- 次级说明：片段数量和真实索引覆盖；
- 进度条：coverage；
- 仅保留更新中 / 等待 / 已完成；
- 底部继续显示 `precision_message`，未验证就明确不宣称准确率。

## 4. macOS 找回主窗口

旧版只有单个全局菜单文本，真机发现性不足。本轮改为：

```text
窗口
└─ 将灵机带到当前屏幕    Cmd/Ctrl + Shift + L
```

动作仍为精确主窗口：

```text
unminimize → show → center → focus
```

macOS 额外处理 `RunEvent::Reopen`，点击 Dock 图标时也会找回主窗口。

不触碰 Runtime、DataRoot、Vault、Secret 或其他用户设置。

## 5. 修改文件

```text
desktop/lingji-control/src/pages/OverviewPage.tsx
desktop/lingji-control/src/OwnerHomeV2.css
desktop/lingji-control/src/App.tsx
desktop/lingji-control/src/components/CurrentWorkPanel.tsx
desktop/lingji-control/src-tauri/src/main.rs
desktop/lingji-control/scripts/observation-first-ui-smoke.mjs
desktop/lingji-control/scripts/memory-progress-smoke.mjs
desktop/lingji-control/scripts/window-recovery-smoke.mjs
docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md
docs/TEST_REPORTS/PR88_OWNER_HOME_V2_IMPLEMENTATION.md
```

## 6. 自动验证合同

必须通过：

```text
node desktop/lingji-control/scripts/observation-first-ui-smoke.mjs
node desktop/lingji-control/scripts/memory-progress-smoke.mjs
node desktop/lingji-control/scripts/window-recovery-smoke.mjs
node desktop/lingji-control/scripts/run-smoke-suite.mjs
npm run build
cargo test / cargo check
python tests
acceptance-doc-sync
local-execution-handoff
P0 Windows Gate
macOS Desktop Gate
Windows Desktop Release Baseline
```

本报告提交时远程 CI 尚未执行完成，因此不能把这些项目提前写成 PASS。

## 7. 下一轮真机验收

代码侧通过后仍不能关闭 M5 UX blocker。必须使用**新产品 Commit + 同 SHA 新 macOS/Windows Artifact**重新真机验证：

1. 首屏是否能在几秒内看懂“是否需要我决定”；
2. 是否能直接看懂“此刻正在做什么”；
3. 七阶段流程是否让自动化过程明显可见；
4. “最近自动完成”是否来自真实事件且容易理解；
5. 技术指标是否已经退出日常首屏；
6. Memory Progress 是否能看懂而不是统计数字堆积；
7. macOS `窗口 → 将灵机带到当前屏幕`、快捷键和 Dock Reopen 是否都能有效找回窗口。

主人未通过前，PR #88 继续 Draft / DO NOT MERGE。

## 8. 安全与回滚

- 不新增永久事实源；
- 不改变 AI 正文读取授权；
- 不改变永久记忆人工确认边界；
- 不自动重建 Production Qdrant；
- 不改变 Acceptance/Production 隔离；
- 不导出 Secret；
- Windows 与 macOS 共用同一 UI/Runtime 代码，只在 Tauri 平台事件上使用 macOS 条件分支。

回滚仅回退本轮首页视觉/投影和窗口入口，不回退已经通过的 Sidecar、认证、隔离和 release identity 修复。

旧 Artifact `9224368022` 与 `9102748834` 均保持 `DO NOT RETRY`。
