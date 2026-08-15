# PROJECT_STATUS.md — LingJi 当前状态

> Updated: 2026-08-15
> Formal/default branch: `master`
> Current product PR: `#88`
> Current product candidate: `f3cba4136bd169619277279a55007fcd4ef609f4`
> Architecture: `docs/ARCHITECTURE.md`
> Code entry points: `docs/MODULES/CODE_MAP.md`
> Acceptance authority: `docs/ACCEPTANCE/README.md`

## 1. 当前结论

PR #88 已完成上一轮 M5 失败后的 Owner Home v2 产品修复。当前新候选：

```text
f3cba4136bd169619277279a55007fcd4ef609f4
READY FOR M5 REACCEPTANCE
DRAFT / DO NOT MERGE
```

当前状态**不是 PASS**。它只表示：新的产品代码、同 SHA 自动门禁、macOS Artifact 与 Windows Artifact 已经锁定，可以进入新的真实 M5 主人体验复验。

上一候选 `2c96b3ec...` 的真实 M5 结论保持 `FAIL / DO NOT MERGE`，其 Artifact `9224368022` 永久禁止重跑。

## 2. Owner Home v2 已完成的修复

上一轮阻塞：

- `M5-UX-003`：首页看不出系统自动执行了什么；
- `M5-UX-004`：新 UI 与旧版没有明显、可感知差异；
- `M5-UX-005`：信息层级不友好；
- 主窗口找回未通过主人观察；
- Memory Progress 未通过主人观察。

当前候选已实现：

```text
现在发生什么
→ 自动工作流走到哪一步
→ 最近真正自动做过什么
```

具体包括：

- 首屏“灵机自动驾驶”，主人事项优先；
- “此刻正在做”读取真实 queue / recent action；
- 七阶段流程：`发现来源 → 收纳 → 解析 → 候选 → 确认 → 索引 → 取回`；
- “最近自动完成”直接读取已有 `overview.events`；
- 空闲 Codex / CurrentWork 不再常驻首页；
- Memory Progress v2 展示真实收纳、更新、coverage 与未测量质量状态；
- macOS `窗口 → 将灵机带到当前屏幕`；
- `Cmd/Ctrl + Shift + L` 快捷键；
- macOS Dock Reopen 找回窗口。

不新增第二事实源，不扩大正文读取、永久记忆批准或破坏性 Qdrant 权限。

## 3. 当前精确产品门禁

Commit `f3cba4136bd169619277279a55007fcd4ef609f4`：

```text
tests                            run 31894132471  PASS
P0 Windows Gate                  run 31894132505  PASS
macOS Desktop Gate               run 31894132498  PASS
Windows Desktop Release Baseline run 31894132475  PASS
acceptance-doc-sync              run 31894132538  PASS
local-execution-handoff          run 31894132477  PASS
```

## 4. 当前 Artifact

### macOS

```text
Run: 31894132498
Artifact: 9249367672
Name: lingji-macos-arm64
Artifact ZIP SHA256:
3e0c2cee26f485ac339cb1db544799f8e40c61b01a9f28d23300aa9f4ff2cc36

DMG: 灵机_0.1.0_aarch64.dmg
DMG bytes: 46339959
DMG SHA256:
a2dfaad32a77b8853bac6fe720667618fe65e6ffbfb1b3342d0f64fc0ecbe6cd
```

### Windows

```text
Run: 31894132475
Artifact: 9249378683
Name: lingji-windows-0.1.0-f3cba413
Artifact ZIP SHA256:
3415fb914d2ec50620634cc03ed5b5961424e314a0b2cdacdedebf5c72e7a049

NSIS SHA256:
e8261683f6e4a1afc4bd50094a80115684641095121050b152d122b25a83a13b

Portable SHA256:
6346a503bcad1fd1def02f4eca126ffb1298df1b5b7815a7cedacdd5c87b4cf2
```

Windows `build-metadata.json.commit` 已独立复核为精确产品 Commit `f3cba4136bd169619277279a55007fcd4ef609f4`。

## 5. 当前 M5 任务

唯一权威入口：

```text
docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md
```

当前任务：

```text
PR88-M5-OWNER-HOME-V2-F3CBA413
status: ACTIVE
execution_mode: MACOS_M5_PHYSICAL_REACCEPTANCE
```

结果回执：

```text
docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
status: PENDING
verdict: PENDING
```

本轮重点不是再证明 CI，而是证明主人真实看到的新产品体验确实解决上一轮失败。

## 6. 真机必须关闭的体验项

主人必须实际确认：

1. 首屏几秒内能判断是否需要自己决定；
2. 能看懂“此刻正在做什么”；
3. 七阶段自动流程可见且有真实状态；
4. “最近自动完成”是真事件，不是假忙碌；
5. 信息层级明显区别于上一失败版；
6. Memory Progress 像工作进度而不是数字墙；
7. `窗口 → 将灵机带到当前屏幕` 容易发现且实际有效；
8. 快捷键与 Dock Reopen 至少完成真实路径回归。

主人未明确 PASS 前不得合并 PR #88。

## 7. 技术回归仍然强制

即使本轮重点是 UX，以下历史通过项仍需真机回归：

- macOS Artifact / DMG / embedded Commit 精确身份；
- Apple Silicon arm64；
- whole-bundle 安装与 codesign；
- Acceptance Runtime 物理隔离；
- AuthStatus / Secret 边界，`secret_export_count=0`；
- 两轮启动与 exact-instance stop；
- 每次停止前保存 Sidecar PID，随后 `state gone + PID gone + port free`；
- Production pollution count = 0；
- FAIL 时恢复原 App；
- 最终远程报告与本机垃圾清理。

上一轮第一次停止没有保存可复读 PID，因此是 `NOT_TESTED`；本轮必须补齐，不能用推断冒充 PASS。

## 8. 当前产品主线

```text
src/
= 长期平台主线

desktop/lingji-control/
= 唯一正式 Desktop UI

second_brain/
= Compatibility / Migration Runtime
```

规则：

- 新正式能力进入 `src/`；
- 新正式 Desktop 能力进入 `desktop/lingji-control/`；
- Desktop 只通过认证的 `127.0.0.1:8766` Local Control API；
- MCP 默认 stdio，可选 HTTP 8767；
- 8765 仅为迁移期兼容 API；
- `second_brain/` 不接收新的正式产品能力。

## 9. 数据与安全权威

```text
Obsidian Vault + Git = 永久记忆与正式知识正文
storage/raw = 原始导入材料
lingji_state.db = 任务、队列、运行状态与审计事件
lingji_memory.db = 可重建全文与元数据索引
Qdrant = 可重建语义索引
```

长期边界：

- AI 不静默修改 Core Memory；
- 不自动删除/重建 Production Qdrant；
- 不自动下载大型模型；
- 默认仅绑定 `127.0.0.1`；
- Production / Acceptance 物理隔离；
- Secret 只进入系统安全凭据存储；
- Runtime stop 只处理精确实例。

## 10. 历史失败 Artifact

```text
9224368022 / 2c96b3ec: DO NOT RETRY
9102748834 / 171091fe: DO NOT RETRY
```

历史失败报告保留为证据，不覆盖当前 ACTIVE 任务。
