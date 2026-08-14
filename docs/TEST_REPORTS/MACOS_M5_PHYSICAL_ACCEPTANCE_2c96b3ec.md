# PR #88 · macOS M5 Reacceptance Report

## Executive Verdict

```text
Verdict: FAIL
Merge recommendation: DO NOT MERGE
Product commit: 2c96b3ec54b066204cad8db75455be24822852a9
Artifact: lingji-macos-arm64 / 9224368022
```

自动门禁、Artifact 身份、Apple Silicon 架构、签名、Acceptance 隔离和第二轮 Runtime 生命周期均得到验证；但主人对首屏体验给出“全部不合格”的明确结论。本轮不在验收分支修改产品。

## Identity and technical checks

| 项目 | 结果 |
|---|---|
| 六道同 SHA 远程门禁 | PASS |
| Artifact ZIP SHA256 | PASS: `6d7b4b8155d5f98abf3ec66fd2b793b51bac39833b08a92984781a7a07ac926e` |
| DMG SHA256 / bytes | PASS: `95b72565a30ca86c1eee1c2b0dd4c8239fcce774f32e66e7f24b33fe6b986372` / `46320432` |
| 内嵌 Commit | PASS: `2c96b3ec54b066204cad8db75455be24822852a9` |
| 主程序与 Sidecar | PASS: arm64 |
| whole-bundle replace / codesign | PASS |
| Acceptance 隔离 | PASS；Runtime 数据在任务根，未创建 `~/Documents/acceptance`，正式 Production 目录无本轮新增写入 |
| 第二次启动 / 精确停止 | PASS；state 消失、Sidecar PID 退出、8766 释放 |
| Secret 导出 | PASS；公开报告和证据未写入 Token、Cookie、Authorization 或私有路径 |

## Owner observation and blocking defects

### M5-UX-003 · 首页没有显现自动工作过程

- 严重级别：P1
- 主人结论：全部不合格。
- 实际：看不出系统自动执行了什么；首页没有把自动收纳、更新、取回、异常处理和待主人决策组织为可理解的连续过程。
- 预期：首页在不进入诊断页的情况下，让主人看见已完成、正在处理、失败/重试、下一步和真正需要自己决定的事项。

### M5-UX-004 · 新 UI 与旧版缺少可感知差异

- 严重级别：P1
- 实际：主人认为 UI 和之前没有区别；新增内容没有形成可感知的产品层级或价值。
- 预期：Memory Dashboard 必须成为日常首页主结构，不是原有页面上追加不显眼的数据块。

### M5-UX-005 · 信息层级不友好

- 严重级别：P1
- 实际：首页层级不利于理解重点、进度和下一步。
- 预期：先显示“是否需要我决定”与“系统当前工作”，再按记忆生命周期提供可展开细节；技术指标留在高级工具。

## Coverage limits

- “找回主窗口”被主人整体判为不合格，未获得单独的可通过肉眼确认。
- 首次停止未在停止前保存可复读 Sidecar PID，记为 `NOT_TESTED`，不冒充 PASS；第二次完整生命周期通过。

## Required next work

1. 把首页重构为真实的记忆生命周期进度看板，而非统计卡片。
2. 接入来源发现、收纳、解析、候选、确认、索引、取回、更新各阶段的真实事件、变化量、时间和失败/重试。
3. 把“需要主人决定”的项目独立置顶；无待决事项时明确安静地说明无需操作。
4. 完成新产品 Commit、同 SHA 双平台 Artifact 和全部门禁后，再更新任务单进行新的 M5 验收。
