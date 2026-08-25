# VECTOR_DATABASE.md — 向量检索稳定边界

> Updated: 2026-08-25
> Status: SUPPORTING GUIDE
> 架构权威：`docs/ARCHITECTURE.md`
> 代码与测试入口：`docs/MODULES/CODE_MAP.md`

旧版迁移计划、旧默认模型和“只有 `second_brain/` 接通 Qdrant”的描述已经过时，不再作为当前实现说明。

长期合同：

- Qdrant 是可重建语义索引，不是永久记忆正文权威。
- 正式检索为 lexical + semantic + metadata/privacy/project/time/Agent Scope 的统一流程。
- Qdrant 不可用时 lexical 必须继续，并真实显示 degraded 状态。
- 模型或维度不匹配只标记 `rebuild_required`；不得自动删除或重建 Production collection。
- collection、dimension、coverage、per-memory/per-chunk existence 与错误必须来自后端事实。
- Production 与 Acceptance 使用隔离 collection 或隔离路径。
- 模型名称和运行默认值从 `src/config.py::Settings`、Runtime Settings 和 Model Center 读取，不在本文复制。

当前 provider 接线、覆盖率、真实本机模型和验收状态以 `PROJECT_STATUS.md` 与对应 `TEST_REPORTS` 为准。
