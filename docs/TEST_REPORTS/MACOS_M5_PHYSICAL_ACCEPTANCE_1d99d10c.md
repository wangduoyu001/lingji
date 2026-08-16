# PR #88 · Owner Work Feed v3 macOS M5 验收报告

## 结论

```text
Verdict: FAIL
Merge recommendation: DO NOT MERGE
Product commit: 1d99d10cdcb151c0a0257f7d0a93937cdb817b49
Artifact: lingji-macos-arm64 / 9250384637
```

技术安装与隔离通过；主人体验未通过，Work Feed v3 未能让主人理解资料、系统动作、下一步或主人待办。

## 通过项

| 项目 | 结果 |
|---|---|
| 六道同 SHA CI 门禁 | PASS |
| ZIP / DMG 哈希、内嵌 Commit | PASS |
| Desktop / Sidecar arm64、strict codesign | PASS |
| whole-bundle replace | PASS |
| Acceptance 隔离与 Production 污染 | PASS / 0 |
| 第一次启动/停止 PID 三重证据 | PASS |
| 第二次启动/停止 PID 三重证据 | PASS |
| Secret 导出 | PASS / 0 |

## 主人体验阻塞缺陷

### M5-WORK-FEED-001 · “已做什么”和“下一步”不可理解

- 严重级别：P1
- 实际：主人看不懂灵机已做什么，也看不懂每份资料的下一步。
- 预期：每份资料都以自然语言明确展示真实已完成动作与下一步，而不是要求主人自行推断状态。

### M5-WORK-FEED-002 · “去处理”进入空页面

- 严重级别：P1
- 实际：点击“去处理”后看不到需要处理的内容；待确认点击进去为空。
- 预期：资料行、顶部待办与审核页面必须指向同一真实待决对象；无对象时不显示“去处理”。

### M5-WORK-FEED-003 · 无限“下一页”

- 严重级别：P1
- 实际：页面出现无限下一页行为。
- 预期：分页必须基于真实 total/cursor；无后续内容时禁用或隐藏下一页，不能循环空页。

### M5-WORK-FEED-004 · 记忆页为空且自动化不可见

- 严重级别：P1
- 实际：记忆页空白，首页也没有展示真正执行的智能化和自动化过程。
- 预期：Owner Work Feed、Memory 与待确认三者展示同一真实对象和事件链；空状态必须解释原因、影响、正在重试的动作及是否需要主人操作。

## 未覆盖

主人体验在核心 Work Feed 已失败，窗口找回未获单独肉眼确认，必须保持 `NOT_TESTED`，不能作为 PASS。

## 后续要求

需要进行全面的产品 UX 重构与学习审计：以真实资料对象、真实事件、真实待办为单一数据链，统一首页、审核、记忆和分页状态；完成新 Commit、新同 SHA Artifact 与门禁后，才可再次发起 M5 验收。
