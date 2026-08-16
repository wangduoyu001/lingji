# PROJECT_STATUS.md — LingJi 当前状态

> Updated: 2026-08-16
> Formal/default branch: `master`
> Current product PR: `#88`
> Current product candidate: `bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9`
> Current local task: `PR88-M5-OWNER-WORKBENCH-V4-BD1E7A17 / ACTIVE`
> Architecture: `docs/ARCHITECTURE.md`
> Code entry points: `docs/MODULES/CODE_MAP.md`
> Acceptance authority: `docs/ACCEPTANCE/README.md`

## 1. 当前结论

Owner Workbench V4 已完成全面 UI / 信息架构重构并 squash 进入 PR #88 产品分支。

当前状态：

```text
product commit: bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9
automatic product gates: 6/6 PASS
same-SHA macOS artifact: READY
same-SHA Windows artifact: READY
current local task: ACTIVE / M5 REACCEPTANCE
product PR: Draft / DO NOT MERGE
```

自动技术门禁已完成，但最终产品结论仍取决于真实 M5 主人体验、Window Recovery、生命周期、安全边界、远程报告与清理闭环。

## 2. V4 解决的上轮四个 P1

上一候选 `1d99d10c...` 的真实 M5 失败点是：动作语义不可理解、空待办、无限下一页、记忆/自动化割裂。

V4 对应改造：

### 2.1 主人简报替代技术仪表盘

首页固定回答：

```text
现在需要主人吗
刚刚真正做了什么
现在正在做什么
接下来做什么
记忆发生了什么变化
主动发现了什么
```

Runtime/PID/端口/模型/向量/日志等下沉到高级区。

### 2.2 真实对象级“需要我”

主人待办必须来自真实对象：候选永久记忆使用 `memory_id`，正文读取授权使用 `candidate_id`，不可逆维护有明确动作边界。没有对象就没有动作按钮。

首页与“需要我”共享 `ownerWorkbenchModel.ts` 的统一主人判断，不再各自拼状态。

### 2.3 候选记忆精确直达

候选记忆动作按同一个 `memory_id` 进入人工审核详情，不再只跳到空列表或要求主人再次寻找。

### 2.4 一级永久记忆工作区

“记忆”成为一级日常页面，支持真实对象列表、搜索/筛选、详情、来源证据和可解释空状态；永久正文权威仍是 Obsidian Vault + Git。

### 2.5 分页边界修复

受影响页面统一要求真实 `has_more` 或可证明的 `total`。两者未知时保守停止，不再用“本页刚好满了”推断永远还有下一页。

### 2.6 工作履历与全局入口

“工作”用主人语言展示发生了什么、结果、下一步和下一执行者。`Cmd/Ctrl + K` 提供真实快速记录和导航；未实现的开放式 Agent 动作明确不执行，不制造假成功。

## 3. 同 SHA 自动产品门禁

精确产品 SHA：

```text
bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9
```

六道门全部 PASS：

```text
tests: 31928631115
P0 Windows Gate: 31928631099
macOS Desktop Gate: 31928631105
Windows Desktop Release Baseline: 31928631101
acceptance-doc-sync: 31928631103
local-execution-handoff: 31928631118
```

## 4. 当前正式 Artifact

### macOS Apple Silicon

```text
Artifact: 9258682849
Name: lingji-macos-arm64
Workflow: 31928631105
ZIP SHA256: c26408c350bf35701bdf6aa97e75f65e7bead42fb6ed92d11838334274e1a888
DMG: 灵机_0.1.0_aarch64.dmg
DMG SHA256: a5d54cba4f99411541527be7230d568f32a8fba90efed14ff9756df6b393bb46
```

### Windows x64

```text
Artifact: 9258675881
Name: lingji-windows-0.1.0-bd1e7a17
Workflow: 31928631101
ZIP SHA256: 0696ae6615d8afc44f46efc264fd7852e7d971866efc1285f2397d87a36ce4b1
NSIS SHA256: b9341ae7982375cac1a771ad7082b8ba76014b60c4a1c300de5791ce77a84339
Portable SHA256: 2435fcbfbc0e211c76c64ec5556c9f36fef84c12cd603c421ef0607c8da5f3b3
Manifest SHA256: 4815fcb4403cfd29dc08a1d4fa099fc1d1ab0700b6aa0dbf2e3c347a6b508cdd
```

独立下载复核确认 ZIP digest 与 GitHub 一致，Windows `build-metadata.json` 的产品 Commit 也是精确 `bd1e7a17...`。

## 5. 当前 M5 任务

```text
Task: PR88-M5-OWNER-WORKBENCH-V4-BD1E7A17
Mode: MACOS_M5_PHYSICAL_REACCEPTANCE
Artifact: 9258682849 only
Report branch: acceptance/pr88-m5-owner-workbench-v4-bd1e7a17
Report: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_bd1e7a17.md
```

本轮必须重点验证：

- 主人第一眼是否知道要不要做事、发生了什么、下一步是什么；
- 一级导航 `首页 / 记忆 / 工作 / 需要我 / 高级` 是否清晰；
- 永久记忆是否可浏览、可查证来源；
- “需要我”是否只出现真实对象；
- 候选 `memory_id` 是否精确直达同一详情；
- `Cmd/Ctrl + K` 是否真实记录/导航且不假执行；
- 所有受影响分页是否有真实终点；
- Window Recovery 菜单、快捷键、Dock Reopen 三条路径；
- 两轮 Runtime exact-instance lifecycle，尤其第一轮保存 PID 后再 stop；
- `secret_export_count=0`；
- `production_pollution_count=0`。

任何 P0/P1 主人体验失败都必须 `FAIL / DO NOT MERGE`。

## 6. 技术边界保持不变

- `src/` 为长期平台主线；
- `desktop/lingji-control/` 为唯一正式 Desktop UI；
- `second_brain/` 只做兼容/迁移；
- Desktop 只通过认证的 `127.0.0.1:8766` Local Control API；
- Obsidian Vault + Git 为永久记忆正文权威；
- SQLite/Qdrant 为可重建索引与运行状态；
- Acceptance / Production 物理隔离；
- Secret 只留在系统安全凭据边界；
- Runtime stop 只处理精确实例；
- 不创建第二事实源来美化状态；
- AI 不能自动批准永久记忆；
- 不自动执行破坏性 Qdrant rebuild。

## 7. 历史失败 Artifact

以下均永久 `DO NOT RETRY`：

```text
9250384637 / 1d99d10c
9249367672 / f3cba413
9224368022 / 2c96b3ec
9102748834 / 171091fe
```

当前 V4 Artifact `9258682849` 只有在本轮最终得到 FAIL 后才转为 `DO NOT RETRY`。

## 8. 合并边界

PR #88 当前仍然：

```text
DRAFT / DO NOT MERGE
```

只有新 M5 的主人体验、技术安全、Window Recovery、两轮生命周期、报告、远程回执和安全清理全部 PASS 后，才允许进入最终合并判断。
