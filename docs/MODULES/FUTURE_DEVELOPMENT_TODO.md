# LingJi 未来开发待办事项

> 状态：规划待办，不代表已经实现  
> 仓库：`wangduoyu001/lingji`  
> 分支：`feature/second-brain-memory`  
> 边界：本文只记录 LingJi / 灵机相关任务，不记录 AI 短剧导演系统内部实现。

## 0. 本文用途

本文用于沉淀 LingJi 后续开发任务，重点覆盖：

- 统一第二大脑
- 统一记忆系统
- Obsidian 知识入口
- AI 聊天记录归档与检索
- 赚钱机会雷达
- 每日简报沉淀
- MCP / AnySearch / 本地向量库
- AI 工具与模型能力管理
- 与外部项目的接口边界

本文不写入 AI 短剧导演系统的内部逻辑，例如 Story Beat、Shot Schema、镜头库、导演分镜、资产锁定、视频生成、QC 返修等。这些内容必须放到 `wangduoyu001/ai-short-drama-production-controller`。

---

# 1. P0：统一记忆系统主线

## 1.1 明确唯一事实源

- [ ] 保持 Obsidian Vault + Git 作为永久记忆和正式知识正文的唯一权威源。
- [ ] 保持 `src/` 作为长期主线，不再发展第二套正式记忆核心。
- [ ] 明确 `second_brain/` 只作为兼容、迁移、验收参考，不作为最终正式运行链路。
- [ ] 禁止形成两套记忆核心、两条采集链、两套正式 UI、两个事实来源。

## 1.2 MemoryGateway 统一出口

- [ ] 所有 AI 读取记忆必须通过一个 `MemoryGateway`。
- [ ] 扩展 `MemoryGateway`，支持搜索、读取、Core、Context Pack、候选记忆、recent changes、health、rebuild。
- [ ] 不新增第二个 Gateway。
- [ ] 所有外部 AI / Codex / MCP / 桌面 UI 通过同一网关读取上下文。

## 1.3 HybridRetriever 检索统一

- [ ] 保持一个 `HybridRetriever` 排名流程。
- [ ] 语义检索结果必须经过同一权限过滤、隐私过滤、项目过滤、状态过滤。
- [ ] Qdrant 只提供 semantic candidates 和诊断，不自行决定最终排名与权限。
- [ ] 增加语义检索失败的 degraded 状态，不允许静默返回空结果。

---

# 2. P0：向量库与 RAG 能力

## 2.1 Qdrant Provider 合同

- [ ] 扩展 `SemanticProvider` Protocol，增加 `upsert`、`delete`、`rebuild`、`health`、`coverage`、`point_exists`。
- [ ] 从 `second_brain/vector_store.py` 迁移 Qdrant embedded / remote / memory 模式思想。
- [ ] 增加 collection dimension 检查。
- [ ] 增加 rebuild_required / degraded / healthy 状态。
- [ ] Qdrant payload 不长期复制完整永久记忆正文，只保存必要索引、引用和诊断字段。

## 2.2 Embedding Provider

- [ ] 统一 Ollama embedding 主备模型调用。
- [ ] 支持 bge-m3 等本地 embedding 模型状态读取。
- [ ] 在 Runtime Settings 中增加 embedding 配置分组。
- [ ] 在模型中心展示 embedding provider 可用性、维度、速度和错误状态。

## 2.3 增量同步

- [ ] `MemoryGateway.rebuild()` 必须同步 SQLite FTS 与 Qdrant。
- [ ] `IncrementalMemorySynchronizer` 必须同步 Qdrant upsert / delete。
- [ ] 以稳定 chunk 为单位同步。
- [ ] 增加 index coverage 报告，展示哪些来源已进入全文索引、哪些已进入向量索引。

---

# 3. P0：AI 聊天记录作为自动记忆入口

## 3.1 聊天记录采集

- [ ] 将 AI 聊天记录作为 LingJi 记忆的唯一自动入口。
- [ ] Obsidian 继续作为手动知识入口，不让聊天记录直接污染正式知识正文。
- [ ] 设计 Chat Import Adapter，支持从导出文本、Markdown、JSON、API 或本地归档导入。
- [ ] 每条聊天记录保留 source、conversation_id、message_id、role、时间、主题、项目归属。

## 3.2 候选记忆生成

- [ ] 聊天记录默认进入候选记忆，不直接写入 Core。
- [ ] 增加自动摘要、事实抽取、偏好抽取、项目约束抽取。
- [ ] 提供主人确认 / 拒绝 / supersede 流程。
- [ ] 支持把长期有效内容晋级为 Core Memory。

## 3.3 来源可追溯

- [ ] 每条候选记忆必须能追溯到原始聊天来源。
- [ ] Memory Inspector 中展示原文片段、抽取原因、置信度、是否已确认。
- [ ] 禁止无来源的“AI 自己觉得你说过”。这种东西像赛博谣言，应该直接拦住。

---

# 4. P1：赚钱机会雷达

## 4.1 Opportunity Score 机会评分

- [ ] 新增 `Opportunity Score`，按商业价值筛选 AI 新闻、项目、工具和市场信号。
- [ ] 评分维度包括：市场需求、购买意图、痛点强度、竞品收入模式、获客渠道、验证成本、自动化程度、是否能收费、是否可复制、风险等级。
- [ ] 普通 AI 新闻默认不进入机会池。
- [ ] 只有出现付费信号、真实需求、开源热度、融资、价格变化、平台规则变化、API 变化时才进入候选机会。

## 4.2 机会字段扩展

- [ ] 增加需求强度字段。
- [ ] 增加购买意图字段。
- [ ] 增加竞品收入模式字段。
- [ ] 增加获客渠道字段。
- [ ] 增加验证动作字段。
- [ ] 增加验证成本字段。
- [ ] 增加实际转化字段。
- [ ] 增加是否成交字段。
- [ ] 增加实际收入字段。
- [ ] 增加联系人 / 社区来源 / 跟进状态字段。

## 4.3 验证闭环

- [ ] 每个机会必须能生成一个最小验证动作。
- [ ] 每个验证动作必须记录成本、耗时、结果和下一步。
- [ ] 机会不再只记录“看起来能赚钱”，必须记录“有没有人愿意付钱”。

---

# 5. P1：每日简报沉淀机制

## 5.1 简报归档

- [ ] 每日 AI 简报保存到 `docs/DAILY_BRIEF/YYYY-MM-DD.md`。
- [ ] 每份简报包含 AI 赚钱、AI 工具、模型、本地硬件、自媒体、跨境/TikTok、风险和可执行动作。
- [ ] 简报不直接改核心架构文档。

## 5.2 文档更新队列

- [ ] 新增或维护 `docs/DOC_UPDATE_QUEUE.md`。
- [ ] 每日简报提取“值得沉淀”的文档更新建议。
- [ ] 每条建议记录来源日期、影响模块、目标文档、建议内容、证据强度、是否立即执行。
- [ ] 每周统一筛选高优先级建议后再合并核心文档。

## 5.3 决策日志

- [ ] 新增或维护 `docs/DECISION_LOG.md`。
- [ ] 记录为什么选择某个模型、工作流、架构、数据源或工具。
- [ ] 防止重复推翻已经确认的方向。人类项目最擅长把同一个决定反复开会，别学。

---

# 6. P1：MCP / AnySearch / 外部工具入口

## 6.1 MCP 统一工具接口

- [ ] 保持 MCP 作为 AI 工具调用的正式出口。
- [ ] 增加 MCP 设置、状态、权限、错误诊断页面。
- [ ] 让 Obsidian、GitHub、本地文件、浏览器、搜索工具通过统一工具层接入。
- [ ] 每个 MCP 工具必须有权限范围、上下文上限、日志与失败降级。

## 6.2 AnySearch 默认搜索层

- [ ] 将 AnySearch 作为 LingJi 的默认外部搜索层候选。
- [ ] 架构路径：`Obsidian -> LingJi -> Planner Agent -> AnySearch MCP / 本地向量库(RAG)`。
- [ ] AnySearch 结果必须经过 LingJi 的来源记录、去重、可信度和机会评分。
- [ ] 禁止直接把搜索结果当结论写入 Core Memory。

---

# 7. P1：模型能力矩阵与 LLM Router

## 7.1 Model Capability Matrix

- [ ] 建立 `model_capability_matrix.json` 或等价配置。
- [ ] 记录 GPT、Claude、Kimi、Qwen、Gemini、本地模型的能力表现。
- [ ] 字段包括 coding、writing、story、reasoning、context、speed、api_cost、local_support、preferred_tasks、last_verified。
- [ ] 模型能力必须定期复核，不要凭印象长期使用。模型圈每天变脸，比短视频标题还勤快。

## 7.2 LLM Router

- [ ] 建立 LLM Router，按任务自动选择模型。
- [ ] 任务类型包括：写代码、总结、检索增强、文档整理、机会评分、自动化规划。
- [ ] 支持云端模型与本地模型混合。
- [ ] 支持成本上限、失败降级、备用模型。

---

# 8. P2：桌面控制台与可视化

## 8.1 Brain Status

- [ ] Brain Status 必须读取同一个统计服务。
- [ ] 修复 memory_stats 显示错误或硬编码占位。
- [ ] 展示记忆数量、候选数量、Core 数量、向量覆盖率、最近任务、错误状态。

## 8.2 Memory Inspector

- [ ] 独立 Memory Inspector 页面。
- [ ] 支持查看候选记忆、Core、拒绝、supersede、来源原文。
- [ ] 支持一键确认、拒绝、编辑、合并。

## 8.3 Vector Center

- [ ] 独立 Vector Center 页面。
- [ ] 展示 Qdrant 状态、collection、dimension、coverage、rebuild_required、degraded 原因。
- [ ] 支持手动 rebuild、增量重建、错误诊断。

## 8.4 知识中心与机会中心

- [ ] 新增知识中心，展示 Obsidian 正式知识、来源、标签、引用关系。
- [ ] 新增机会中心，展示机会评分、验证状态、付费信号、下一步动作。

---

# 9. P2：与 AI 导演系统的边界接口

## 9.1 LingJi 只提供情报、记忆和调度入口

- [ ] LingJi 可以记录 AI 短剧方向的商业机会、工具更新、模型变化和项目上下文。
- [ ] LingJi 可以向导演系统提供检索、上下文包、工具情报和机会建议。
- [ ] LingJi 不实现导演系统内部模块。
- [ ] LingJi 不维护 Story Beat、Shot Schema、Shot Library、Workflow Library、视频 Provider、镜头 QC、自动返修等导演系统内部数据结构。

## 9.2 对外接口

- [ ] 为导演系统提供 Context Pack API。
- [ ] 为导演系统提供 AI 工具/模型情报查询。
- [ ] 为导演系统提供项目记忆检索。
- [ ] 为导演系统提供商业机会和平台规则风险提示。

---

# 10. 不允许混入 LingJi 的内容

以下内容不要写进 LingJi 开发待办，必须放入 AI 短剧导演系统仓库：

- Story Beat 剧情节拍库
- Shot Schema 镜头结构
- Shot Library 镜头库
- Workflow Library 视频工作流库
- 角色 / 场景 / 道具资产锁定
- 人物站位、运镜、焦段、景别
- 视频生成 Provider Router
- QC Agent 镜头质检
- Auto Repair 自动返修
- ComfyUI 视频执行层
- 打斗动作线、攻击线、防守线、受力方向
- 分镜卡、首帧、尾帧、生成提示词

这些都属于导演系统，不属于 LingJi 主仓库。

---

# 11. 下一步执行顺序

## 第一批执行

- [ ] 完成 Qdrant Provider 合同设计。
- [ ] 完成 Embedding Provider 设计。
- [ ] 完成 Chat Import Adapter 规划。
- [ ] 完成 Opportunity Score 字段设计。
- [ ] 新增 `docs/DAILY_BRIEF/` 和 `docs/DOC_UPDATE_QUEUE.md`。

## 第二批执行

- [ ] 接入 AnySearch MCP。
- [ ] 建立 Model Capability Matrix。
- [ ] 建立 LLM Router。
- [ ] 完成 Memory Inspector 文档与接口规划。
- [ ] 完成 Vector Center 文档与接口规划。

## 第三批执行

- [ ] 实现机会验证闭环。
- [ ] 实现简报自动归档。
- [ ] 实现文档更新队列半自动生成。
- [ ] 与 AI 导演系统建立只读上下文接口。

---

# 12. 当前结论

LingJi 的长期定位是：

```text
个人赚钱机会操作系统
+ 第二大脑
+ AI 工具记忆总线
+ 项目执行控制台
```

它负责记忆、检索、机会判断、工具情报、上下文调度。

它不负责导演分镜、视频生成、资产锁定和镜头返修。

项目边界必须保持清楚，否则两个仓库都会变成“万能 AI 大杂烩”，最后万能到没人敢维护。
