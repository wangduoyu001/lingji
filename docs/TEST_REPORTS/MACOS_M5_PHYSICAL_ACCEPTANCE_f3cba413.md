# PR #88 · Owner Home v2 macOS M5 验收报告

## 结论

```text
Verdict: FAIL
Merge recommendation: DO NOT MERGE
Product commit: f3cba4136bd169619277279a55007fcd4ef609f4
Artifact: lingji-macos-arm64 / 9249367672
```

安装包身份、签名、arm64、任务根隔离与两轮完整 Runtime 生命周期通过；主人体验仍未通过，不能合并。

## 已通过的技术验收

| 项目 | 结果 |
|---|---|
| 六道同 SHA CI 门禁 | PASS |
| ZIP / DMG 哈希及大小 | PASS |
| 内嵌 Commit | PASS：`f3cba4136bd169619277279a55007fcd4ef609f4` |
| 主程序、Sidecar、codesign | PASS：arm64 / strict codesign |
| whole-bundle replace | PASS |
| Acceptance 隔离 | PASS：Runtime 数据只在任务根；未创建 `~/Documents/acceptance`；正式 Production 目录无本轮新增写入 |
| 首次启动/停止 | PASS：已保存 PID，state 消失、PID 退出、8766 释放 |
| 第二次启动/停止 | PASS：已保存 PID，state 消失、PID 退出、8766 释放 |
| Secret 导出 | PASS：`secret_export_count=0`，公开报告不含 Token、Cookie、Authorization 或私人路径 |

## 主人体验阻塞缺陷

### M5-OWNER-HOME-001 · 收纳数量没有可理解的对象与结果

- 严重级别：P1
- 实际：首屏唯一可理解的信息是“已收纳 2 份资料”；主人不知道这两份资料是什么。
- 预期：每个数字应能展开到安全的来源/标题/时间/处理状态，并说明是否已解析、候选、确认、索引或可取回。

### M5-OWNER-HOME-002 · 自动工作与下一步仍不可见

- 严重级别：P1
- 实际：主人不知道系统做了什么、接下来做什么、是否需要主人行动。
- 预期：首页置顶显示主人待决事项、当前自动阶段、最近真实完成记录、失败/重试和下一步；无事件时必须如实说明空闲，不用统计数字替代过程。

### M5-OWNER-HOME-003 · Owner Home v2 没有形成可验收的工作流

- 严重级别：P1
- 实际：七阶段“发现来源 → 收纳 → 解析 → 候选 → 确认 → 索引 → 取回”未成为主人可理解、可追溯的主结构。
- 预期：每阶段关联真实 queue、memory、review、vector 与 events 数据，并支持向下查看具体项目。

## 未覆盖

主人体验已在首屏主结构失败，因此没有把“窗口找回”写成通过；该项为 `NOT_TESTED`，不得用技术代码存在替代主人确认。

## 下一步

1. 从“数量卡片”升级到可追溯的生命周期清单：资料名称/来源、时间、阶段、结果与下一步。
2. 首页先回答主人四个问题：是否需要我决定、正在做什么、刚完成什么、接下来做什么。
3. 七阶段必须显示真实事件和明确的空状态；技术统计继续下沉到高级诊断。
4. 完成新 Commit、同 SHA 新 Artifact 和全部自动门禁后，才可新建 ACTIVE M5 任务。
