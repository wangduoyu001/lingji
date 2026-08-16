# PROJECT_STATUS.md — LingJi 当前状态

> Updated: 2026-08-16
> Formal/default branch: `master`
> Current product PR: `#88`
> Last rejected product candidate: `1d99d10cdcb151c0a0257f7d0a93937cdb817b49`
> Architecture: `docs/ARCHITECTURE.md`
> Code entry points: `docs/MODULES/CODE_MAP.md`
> Acceptance authority: `docs/ACCEPTANCE/README.md`

## 1. 当前结论

PR #88 的 Owner Work Feed v3 已完成真实 macOS M5 复验：

```text
FAIL / DO NOT MERGE
current local task: IDLE
product PR: Draft
```

技术发布链不是本轮阻塞。产品身份、arm64、签名、隔离、Secret 边界、两轮 Runtime 生命周期和失败回滚均通过。

阻塞是**产品信息架构与真实数据链不成立**：界面仍然让主人解释状态，而不是让系统交代事实和动作。

## 2. 当前四个 P1 blocker

### M5-WORK-FEED-001 · 动作语义不可理解

“灵机已做”和“下一步”虽然有文字，但主人无法理解真实发生了什么。下一版不得继续用状态枚举拼句子，必须绑定真实事件/执行步骤/结果，并用自然语言说明结果、影响和下一动作。

### M5-WORK-FEED-002 · 假待办入口

“去处理”可进入一个没有待办对象的空页面。下一版只有存在**具体 pending action ID** 且目标页能加载同一对象时才允许显示处理按钮；否则必须显示“当前没有可处理事项”或一致性异常。

### M5-WORK-FEED-003 · 分页合同错误

Memory Inspector 存在无限“下一页”。前端必须使用后端 `has_more/cursor/total` 的真实分页合同，不能用未知 total 推断永远还有下一页，并要审计所有分页页面。

### M5-WORK-FEED-004 · 工作台、待确认、记忆和自动化割裂

待确认和记忆页为空，自动化过程不可见。下一版必须让 Workbench、Pending Action、Memory、Trace 指向同一真实对象链：

```text
资料/任务对象
→ 实际执行事件
→ 结果/记忆对象
→ 可执行待办（如有）
→ 下一系统动作
```

空状态也必须解释“为什么空、当前影响、系统是否会自动继续、主人是否需要操作”。

Window Recovery 上轮仍为 `NOT_TESTED`，下一次真实 M5 必须单独完成主人验证。

## 3. 权威失败证据

```text
Task: PR88-M5-OWNER-WORK-FEED-V3-1D99D10C
Product: 1d99d10cdcb151c0a0257f7d0a93937cdb817b49
macOS Artifact: 9250384637 / lingji-macos-arm64
Report branch: acceptance/pr88-m5-owner-work-feed-v3-1d99d10c
Report commit: 74ec2bf67795387ca1ae23377a3deda299cbcfd5
Cleanup receipt: d81713833d3d421554f35305f52459f4b4a3b236
PR #88 comment: 5305293579
```

`docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md` 保存最终回执。

## 4. 下一轮产品方向：Owner Workbench

不再做 Owner Home / Work Feed 的局部补丁。正式进入**工作台信息架构重构**：

```text
Sidebar
├─ 工作台：真实对象列表 + 选中对象详情
├─ 待办：只显示真实 pending action
├─ 记忆：真实已入库对象
├─ 自动化：真实 execution / trace
└─ 设置与诊断：技术状态
```

工作台采用稳定的 list/detail 结构；首页不再用大卡片解释系统。核心对象必须有结构化状态、真实最近动作、下一动作 actor、真实 pending action 和可展开 trace。

视觉目标：低噪声、桌面级、清晰层级、紧凑状态标签、单一上下文主操作；减少彩色大卡和重复统计。

## 5. 必须保持的技术边界

- `src/` 为长期平台主线；
- `desktop/lingji-control/` 为唯一正式 Desktop UI；
- `second_brain/` 只做兼容/迁移；
- Desktop 只通过认证的 `127.0.0.1:8766` Local Control API；
- Obsidian Vault + Git 为永久记忆正文；
- SQLite/Qdrant 是可重建索引与运行状态；
- Acceptance / Production 物理隔离；
- `secret_export_count=0`；
- Runtime stop 只处理精确实例；
- 不创建第二事实源来“美化状态”。

## 6. 下一轮发布条件

```text
搜索学习成熟 Agent / Task / Trace / Knowledge UI
→ 审计当前真实数据合同与分页
→ 建立统一 Owner Workbench 模型
→ 重构工作台 / 待办 / 记忆 / 自动化
→ 统一设计 tokens 与桌面布局
→ 真实场景 smoke + full tests
→ 更新 CHANGE_ACCEPTANCE_LOG + 实施报告
→ 新产品 Commit
→ 同 SHA macOS / Windows release gates
→ 新 Artifact + 哈希
→ 新 ACTIVE M5 task
```

## 7. 历史失败 Artifact

```text
9250384637 / 1d99d10c: DO NOT RETRY
9249367672 / f3cba413: DO NOT RETRY
9224368022 / 2c96b3ec: DO NOT RETRY
9102748834 / 171091fe: DO NOT RETRY
```
