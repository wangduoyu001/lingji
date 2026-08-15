# PROJECT_STATUS.md — LingJi 当前状态

> Updated: 2026-08-16
> Formal/default branch: `master`
> Current product PR: `#88`
> Current product candidate: `1d99d10cdcb151c0a0257f7d0a93937cdb817b49`
> Architecture: `docs/ARCHITECTURE.md`
> Code entry points: `docs/MODULES/CODE_MAP.md`
> Acceptance authority: `docs/ACCEPTANCE/README.md`

## 1. 当前结论

PR #88 已完成针对上一轮真实 M5 失败的第三版产品修复：**Owner Work Feed v3**。

当前状态：

```text
READY FOR M5 REACCEPTANCE
current local task: ACTIVE
product PR: Draft / DO NOT MERGE
```

这不是产品 PASS。六道同 SHA 自动门禁与新 macOS / Windows Artifact 已完成，只代表可以进入新的真实 M5 主人验收。

## 2. 上一轮失败与本轮修复

上一候选 `f3cba4136bd169619277279a55007fcd4ef609f4` / Artifact `9249367672` 的主人反馈：

- 只知道“已收纳 2 份资料”，不知道资料是什么；
- 不知道灵机做了什么；
- 不知道下一步；
- 不知道是否需要主人行动。

对应：`M5-OWNER-HOME-001 / 002 / 003`。

本轮根因确认：后端已经有真实 memory / queue result / events / owner actions，但旧首页把它们压缩成数量和阶段汇总。

Owner Work Feed v3 改为：

```text
你现在需要做什么
→ 灵机现在在做什么
→ 每一份真实资料
→ 灵机已做
→ 下一步
→ 是否需要主人行动
```

七阶段仍保留为每份资料的内部生命周期状态，但不再以 7 张汇总卡要求主人自己拼故事。

## 3. 当前产品身份与六道门禁

产品 Commit：

```text
1d99d10cdcb151c0a0257f7d0a93937cdb817b49
```

同 SHA PASS：

```text
tests                            31897950526
P0 Windows Gate                  31897950577
macOS Desktop Gate               31897950589
Windows Desktop Release Baseline 31897950511
acceptance-doc-sync              31897950532
local-execution-handoff          31897950587
```

## 4. 当前 Artifact

macOS：

```text
Artifact: 9250384637 / lingji-macos-arm64
ZIP SHA256: 8be6bc89dcbc9869d310879e23168f3f9474233e41c23c39526afdc5c9d665c0
DMG: 灵机_0.1.0_aarch64.dmg
DMG bytes: 46344072
DMG SHA256: 2973311a02311e0fad1f6ccc666a90d966509e95f54a8e3895dbea283d6fdc49
```

Windows：

```text
Artifact: 9250362769 / lingji-windows-0.1.0-1d99d10c
ZIP SHA256: a7612cd57036a8d46c5f93399d14f8509ab00dc801be5c04c7bff38a877ee9bb
NSIS SHA256: d263bb43ca4d86465a5eedd7637b9da5a625c72d28a0006909c1c943f81cf08e
Portable SHA256: bbb4c3d198d9c6e3ffa19773c1cac78788cb78750d75ca758383c37d96e8582f
```

两个 Artifact 已独立下载复核，Windows metadata 内嵌 Commit 与当前产品 Commit 完全一致。

## 5. 当前 M5 任务

```text
Task ID:
PR88-M5-OWNER-WORK-FEED-V3-1D99D10C

Task:
docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md

Result:
docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md

Report branch:
acceptance/pr88-m5-owner-work-feed-v3-1d99d10c
```

本轮核心不是看“页面有没有阶段”，而是至少使用 2 份资料后，主人不看开发文档即可回答：

```text
有哪些具体资料？
每份灵机做了什么？
每份下一步是什么？
我要做吗？
```

任一问题不能直接回答即 FAIL。

上一轮未完成主人确认的 Window Recovery 本轮必须实际验菜单、快捷键和 Dock Reopen，不能再保持 `NOT_TESTED`。

## 6. 已通过但必须继续回归的技术边界

- exact product Commit / Artifact identity；
- Apple Silicon arm64；
- strict codesign；
- whole-bundle 安装；
- Acceptance / Production 物理隔离；
- `secret_export_count=0`；
- AuthStatus 只含脱敏状态；
- 两轮启动与 exact-instance stop；
- stop 后 `state gone + PID gone + port free`；
- Production pollution count = 0；
- FAIL 后完整恢复上一 App 并清理本轮任务根。

## 7. 当前产品主线

```text
src/
= 长期平台主线

desktop/lingji-control/
= 唯一正式 Desktop UI

second_brain/
= Compatibility / Migration Runtime
```

规则不变：新正式能力进入 `src/` 或正式 Desktop；Desktop 只通过认证的 `127.0.0.1:8766` Local Control API 访问后端；MCP 默认 stdio，可选 HTTP 8767；8765 仅迁移兼容。

## 8. 数据与安全权威

```text
Obsidian Vault + Git = 永久记忆与正式知识正文
storage/raw = 原始导入材料
lingji_state.db = 任务、队列、运行状态与审计事件
lingji_memory.db = 可重建全文与元数据索引
Qdrant = 可重建语义索引
```

Owner Work Feed 不创建第二事实源，只读现有事实并做主人可理解的安全投影；不得暴露正文、绝对私人路径、raw snapshot 或 Secret。

## 9. 历史失败 Artifact

```text
9249367672 / f3cba413: DO NOT RETRY
9224368022 / 2c96b3ec: DO NOT RETRY
9102748834 / 171091fe: DO NOT RETRY
```

新 Artifact `9250384637` 只有本轮真实 M5 PASS 后才可继续；若本轮 FAIL，它也必须永久淘汰。
