# AI_MODEL_STRATEGY.md — 模型策略边界

> Updated: 2026-08-25
> Status: SUPPORTING STRATEGY
> 当前配置权威：`src/config.py::Settings`、Runtime Settings、Model Center
> 未来 Model Router：`docs/MODULES/FUTURE_DEVELOPMENT_TODO.md`

本文件不再固定 DeepSeek、Qwen、Ollama 或特定 Embedding 模型为长期“当前默认值”。模型可用性、成本、能力和安装状态会变化，必须由运行时探测、主人配置和可更新证据决定。

稳定原则：

- 不把模型名称、端点或回退链复制到多份文档。
- 云端模型和本地模型都通过明确 Provider/Settings 边界接入。
- Secret 只存在本机凭据边界，仓库和状态同步只保存非敏感状态。
- Embedding 变化必须验证维度与 Qdrant collection；不自动破坏生产索引。
- 模型不可用时显示真实降级和原因，不伪造 healthy、0 或 completed。
- 自动模型路由属于未来阶段；在 `PROJECT_STATUS.md` 提升前不得插队开发。

PEMIS 历史快照中的模型名称只描述当时生成数据，不代表当前产品策略。
