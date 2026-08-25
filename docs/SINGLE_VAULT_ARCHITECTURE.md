# 灵机单一 Obsidian Vault 说明

> 文档角色：辅助说明，不是当前进度或实现清单。数据权威和长期边界以 `docs/ARCHITECTURE.md` 为准；实际入口、配置与测试以 `docs/MODULES/CODE_MAP.md` 和当前代码为准。

## 稳定原则

- 灵机只使用一个 Obsidian Vault 作为永久记忆与正式知识正文的权威。
- 文件夹、属性、标签和内部链接用于区分来源、生命周期、项目、隐私与关系；不得再建立第二个永久记忆事实源。
- `lingji_state.db` 保存任务、队列、运行状态与审计；`lingji_memory.db` 和 Qdrant 是可重建索引，不保存不可替代的正文真值。
- 原始导入材料保存在 `storage/raw`；正式知识和主人数据不得被静默移动、覆盖或删除。
- 私密内容默认不进入普通索引、命令队列或云模型；实际隐私规则以当前配置、代码和验收合同为准。

## 目录与交互

Vault 的目录、属性、标签、关系与人工管理规则见 `docs/OBSIDIAN_INTERACTION_AND_METADATA.md`。初始化、命令队列、兼容读取和迁移行为必须从 `docs/MODULES/CODE_MAP.md` 定位当前实现后执行。

本文不再列出历史环境变量、旧 `PEMISCore` 方法或“当前支持入口”清单，避免旧实现名称被误当成现行 API。
