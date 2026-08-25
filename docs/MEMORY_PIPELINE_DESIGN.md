# 灵机记忆管道说明

> 文档角色：辅助数据流说明，不是当前组件、默认值或定时任务清单。数据权威以 `docs/ARCHITECTURE.md` 为准，当前完成度以 `docs/PROJECT_STATUS.md` 为准，代码入口与测试以 `docs/MODULES/CODE_MAP.md` 为准。

## 稳定数据流

```text
原始输入
→ 采集与原始材料留存
→ 提取与结构化
→ 记忆候选与人工审核
→ Obsidian 正式正文
→ 可重建全文/元数据索引与可选语义索引
→ Memory Gateway / MCP / Desktop 召回
```

## 不变约束

- Obsidian Vault + Git 是永久记忆和正式知识正文的唯一权威。
- `storage/raw` 保留原始导入材料。
- `lingji_state.db` 只承担任务、队列、运行状态和审计。
- `lingji_memory.db` 与 Qdrant 必须可以从权威数据重建。
- AI 只能提出记忆候选，不能静默修改 Core Memory。
- 正式 Desktop 只通过认证的 Local Control API 访问后端。

历史版本中关于 `pemis_index.json`、固定嵌入模型/维度、默认定时任务和旧入口的描述已经移除；这些都必须以当前代码和配置为准。
