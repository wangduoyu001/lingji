# PROJECT_STATUS.md — LingJi 当前状态

> Updated: 2026-08-16
> Formal/default branch: `master`
> Current product PR: `#88`
> Last rejected product candidate: `f3cba4136bd169619277279a55007fcd4ef609f4`
> Architecture: `docs/ARCHITECTURE.md`
> Code entry points: `docs/MODULES/CODE_MAP.md`
> Acceptance authority: `docs/ACCEPTANCE/README.md`

## 1. 当前结论

PR #88 的 Owner Home v2 已完成真实 macOS M5 复验，最终结论：

```text
FAIL / DO NOT MERGE
current local task: IDLE
product PR: Draft
```

技术侧不是当前阻塞。包身份、arm64、签名、Acceptance 隔离、两轮 Runtime 生命周期、Secret 边界和失败清理均通过。

真正阻塞仍是主人无法从首页理解系统正在发生什么。

## 2. 当前三个 P1 blocker

### M5-OWNER-HOME-001

首页只让主人看懂“已收纳 2 份资料”，但看不到这两份资料具体是什么。

下一版必须让每个统计数字能下钻到真实对象，并至少展示：

```text
资料标题 / 安全来源
收纳时间
当前阶段
最近完成动作
下一步
是否需要主人行动
```

### M5-OWNER-HOME-002

主人不知道灵机已经做了什么、接下来要做什么，也不知道自己是否需要行动。

首页第一屏必须先回答：

```text
我现在需要做什么？
灵机现在正在做什么？
刚刚完成了什么？
下一步是谁做？
```

### M5-OWNER-HOME-003

“发现来源 → 收纳 → 解析 → 候选 → 确认 → 索引 → 取回”虽然存在于 UI 概念中，但没有形成可追溯的真实工作流。

下一版必须把阶段绑定到真实资料对象、queue / review / memory / vector / events 数据，并允许向下看具体项目，而不是只展示阶段名或数量。

## 3. 最近一次 M5 权威证据

```text
Task:
PR88-M5-OWNER-HOME-V2-F3CBA413

Product Commit:
f3cba4136bd169619277279a55007fcd4ef609f4

macOS Artifact:
9249367672 / lingji-macos-arm64

Report branch:
acceptance/pr88-m5-owner-home-v2-f3cba413

Report commit:
d9a32e28ceb5505546e3bb45d16bb459b6d5a051

Cleanup receipt commit:
2a515a04540274809557d7f12ccdee1308a355e3

PR #88 result comment:
5303141355
```

`docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md` 保存最近一次最终回执。

## 4. 已通过并必须保持的技术边界

后续产品修复不得破坏：

- 精确产品 Commit / Artifact 身份；
- Apple Silicon arm64；
- strict codesign；
- whole-bundle 安装；
- Acceptance / Production 物理隔离；
- `secret_export_count=0`；
- AuthStatus 仅暴露脱敏状态；
- 两轮启动与 exact-instance stop；
- stop 后 `state gone + PID gone + port free`；
- Production pollution count = 0；
- FAIL 后恢复上一版本与安全清理。

这些项已经通过，但每个新候选仍需同 SHA 自动和真机回归。

## 5. 当前产品修复方向

下一轮不再做“Owner Home v2.1”式微调，而是把首页的数据模型改成 **Owner Work Feed / 可追溯工作清单**。

首页核心单位从：

```text
数量 / 状态卡 / 阶段卡
```

改为：

```text
真实资料对象
→ 系统动作历史
→ 当前阶段
→ 下一步
→ Owner Action
```

目标是让主人不理解 Qdrant、Embedding、SQLite、queue 或端口，也能直接知道：

- 灵机发现/收纳了什么；
- 对每份资料做到了哪一步；
- 最近发生了什么；
- 为什么停在这里；
- 是灵机继续自动处理，还是需要主人确认。

技术统计继续下沉到高级诊断。

## 6. 当前产品主线

```text
src/
= 长期平台主线

desktop/lingji-control/
= 唯一正式 Desktop UI

second_brain/
= Compatibility / Migration Runtime
```

规则不变：

- 新正式能力进入 `src/`；
- 新正式 Desktop 能力进入 `desktop/lingji-control/`；
- Desktop 只通过认证的 `127.0.0.1:8766` Local Control API 访问后端；
- MCP 默认 stdio，可选 HTTP 使用 8767；
- 8765 仅为迁移期兼容 API；
- `second_brain/` 不接收新的正式产品能力。

## 7. 数据与安全权威

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
- 默认只绑定 `127.0.0.1`；
- Production / Acceptance 物理隔离；
- Secret 只进入系统安全凭据存储；
- Runtime stop 只处理精确实例。

## 8. 下一轮发布条件

```text
理解三个 Owner Home blocker
→ 核对现有后端是否已有对象/事件数据
→ 定义新的 Owner Work Feed 数据合同
→ 修改产品代码和测试
→ 更新 CHANGE_ACCEPTANCE_LOG.md
→ focused + full + release CI
→ 锁定新的单一产品 Commit
→ 同 SHA macOS / Windows Artifact
→ Artifact 哈希锁定
→ 新 LOCAL_EXECUTION_TASK: ACTIVE
→ M5 真机复验
```

在新任务生成前，`LOCAL_EXECUTION_TASK.md` 保持 `IDLE`。

## 9. 历史失败 Artifact

```text
9249367672 / f3cba413: DO NOT RETRY
9224368022 / 2c96b3ec: DO NOT RETRY
9102748834 / 171091fe: DO NOT RETRY
```

历史失败报告保留为证据，不承担当前任务职责。
