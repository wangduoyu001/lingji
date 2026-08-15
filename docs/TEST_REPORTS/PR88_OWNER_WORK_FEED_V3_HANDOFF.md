# PR #88 · Owner Work Feed v3 M5 交接报告

## 结论

```text
Product candidate: 1d99d10cdcb151c0a0257f7d0a93937cdb817b49
Cloud/release gates: PASS 6/6
Physical M5: PENDING
PR #88: Draft / DO NOT MERGE
```

本报告只证明第三版候选具备进入真实 M5 复验的条件，不代表主人体验已经 PASS。

## 1. 来源失败

上一轮：

```text
Product: f3cba4136bd169619277279a55007fcd4ef609f4
macOS Artifact: 9249367672
Verdict: FAIL / DO NOT MERGE
```

主人只能看懂“已收纳 2 份资料”，无法知道资料具体是什么、灵机做了什么、下一步是什么、是否需要自己行动。

## 2. 本轮产品变化

Owner Work Feed v3 将首页主单位从“数量 / 七阶段汇总卡”改为真实资料对象：

```text
你现在需要做什么
→ 灵机现在在做什么
→ 具体资料
→ 灵机已做
→ 下一步
→ 是否需要主人行动
```

数据仍来自现有 Memory Inspector、queue result、events、owner actions，不新增持久化事实源。

若统计有资料但明细不可读，首页必须显式降级，禁止只显示数量。资料需要审核时，资料行和首页顶部必须一致，并直接进入审核页面。

## 3. 精确自动门禁

```text
tests                            31897950526  PASS
P0 Windows Gate                  31897950577  PASS
macOS Desktop Gate               31897950589  PASS
Windows Desktop Release Baseline 31897950511  PASS
acceptance-doc-sync              31897950532  PASS
local-execution-handoff          31897950587  PASS
```

全部绑定产品 Commit `1d99d10cdcb151c0a0257f7d0a93937cdb817b49`。

## 4. Artifact 锁定

macOS：

```text
Run: 31897950589
Artifact: 9250384637 / lingji-macos-arm64
ZIP SHA256: 8be6bc89dcbc9869d310879e23168f3f9474233e41c23c39526afdc5c9d665c0
DMG: 灵机_0.1.0_aarch64.dmg
DMG bytes: 46344072
DMG SHA256: 2973311a02311e0fad1f6ccc666a90d966509e95f54a8e3895dbea283d6fdc49
```

Windows：

```text
Run: 31897950511
Artifact: 9250362769 / lingji-windows-0.1.0-1d99d10c
ZIP SHA256: a7612cd57036a8d46c5f93399d14f8509ab00dc801be5c04c7bff38a877ee9bb
NSIS SHA256: d263bb43ca4d86465a5eedd7637b9da5a625c72d28a0006909c1c943f81cf08e
Portable SHA256: bbb4c3d198d9c6e3ffa19773c1cac78788cb78750d75ca758383c37d96e8582f
```

两个 Artifact 均已独立下载复核；Windows `build-metadata.json.commit` 与产品 Commit 精确一致。

## 5. 新 M5 硬标准

至少 2 份真实或任务专用资料。主人不看开发文档必须直接回答：

```text
有哪些具体资料？
每份灵机已经做了什么？
每份下一步是什么？
我要做吗？
```

资料行和顶部主人动作必须一致；明细不可读时必须诚实降级；最近活动必须是真实事件；技术统计不能占据主结构。

Window Recovery 上一轮为 NOT_TESTED，本轮菜单、快捷键、Dock Reopen 必须全部进入真实主人验收。

## 6. 技术回归

仍必须复验：

- exact Artifact identity；
- arm64 / strict codesign；
- whole-bundle replace；
- Acceptance / Production 物理隔离；
- AuthStatus / `secret_export_count=0`；
- 两轮启动与停止前保存 PID；
- 每轮 stop 后 `state gone + PID gone + port free`；
- Production pollution count = 0；
- PASS 后清理 / FAIL 后恢复上一 App。

## 7. 当前任务

```text
Task ID: PR88-M5-OWNER-WORK-FEED-V3-1D99D10C
Report branch: acceptance/pr88-m5-owner-work-feed-v3-1d99d10c
Report: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_1d99d10c.md
```

历史失败 Artifact `9249367672`、`9224368022`、`9102748834` 均永久 DO NOT RETRY。
