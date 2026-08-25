# MEMORY_SYSTEM.md — 记忆系统稳定边界

> Updated: 2026-08-25
> Status: SUPPORTING GUIDE
> 架构权威：`docs/ARCHITECTURE.md`
> 当前完成度：`docs/PROJECT_STATUS.md`

本文件不再维护分支、阶段顺序、完成清单或迁移状态。

稳定边界只有：

```text
正式知识与永久记忆正文 = Obsidian Vault + Git
原始输入 = storage/raw
任务、队列、运行状态与审计 = lingji_state.db
词法/元数据索引 = lingji_memory.db（可重建）
语义索引 = Qdrant（可重建）
```

- AI 只能提出记忆候选，不能静默批准或覆盖 Core Memory。
- Source、Conversation、Message、索引和向量是可追溯或可重建层，不是第二个永久正文权威。
- 正式读取统一经过 MemoryGateway、Context Pack 和 MCP 权限边界。
- Production 与 Acceptance 必须隔离 Vault、raw、数据库、Qdrant、日志、设置和备份。
- `second_brain/` 只保留兼容、迁移和验收来源，不新增正式能力。

当前 Capture、Work Fact、Memory lifecycle、检索、Desktop 与 AI 接入是否已经闭环，只能由 `PROJECT_STATUS.md` 和对应测试证据判断，不能从本文件推断。
