# 灵机本地控制中心说明

> 文档角色：辅助说明，不是当前架构、进度或开发顺序权威。稳定边界以 `docs/ARCHITECTURE.md` 为准，当前能力与缺口以 `docs/PROJECT_STATUS.md` 为准，代码入口与验收命令以 `docs/MODULES/CODE_MAP.md` 为准。

## 稳定结论

- 正式桌面端位于 `desktop/lingji-control/`，不是 Obsidian 插件。
- Desktop 只通过带认证的 `127.0.0.1:8766` Local Control API 访问后端，不直接操作 SQLite 或任意覆盖 Vault。
- Python 主线位于 `src/`；MCP 默认使用 stdio，可选 HTTP 使用 8767。
- Obsidian Vault 保存永久记忆和正式知识正文；状态库、记忆索引和 Qdrant 均不得成为第二个正文真值源。
- 对正式知识、主人数据、凭据和高风险操作的保护规则，以 `AGENTS.md`、`docs/ARCHITECTURE.md` 和 `docs/DEVELOPMENT_RULES.md` 为准。

## 当前实现导航

- Desktop：`desktop/lingji-control/`
- Local Control API：`src/control/api.py`
- Service 层：`src/control/service.py`
- 设置、认证、任务、记忆和采集入口：见 `docs/MODULES/CODE_MAP.md`

旧版页面清单、推荐技术选型、随机端口方案和开发顺序已从本文移除，避免把早期设计设想误读为当前产品能力。任何新增页面或协议必须先更新当前状态、代码导航和增量验收要求。
