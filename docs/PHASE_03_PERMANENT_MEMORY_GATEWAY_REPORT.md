# 灵机第三阶段：永久记忆、混合召回与多 AI 网关开发报告

## 状态

- 分支：`feature/single-vault-memory-foundation`
- PR：Draft PR #1
- 阶段版本：`LingJi Personal Memory OS v0.3-alpha`
- 自动测试：37/37 通过
- Python：3.11、3.12 均通过
- MCP smoke test：通过
- 合并状态：保持 Draft，等待本机未推送代码、真实 Vault 和 Windows 集成测试

## 本阶段目标

1. 把“长期知识库”升级为有审核、有失效时间、有 Agent 权限的永久记忆系统。
2. 建立不依赖向量服务也能稳定工作的高速全文召回。
3. 增加中文短查询、项目、标签、类型、隐私和时间过滤。
4. 为 ChatGPT、Codex、Claude、Gemini、Kimi、DeepSeek 和 Ollama 提供统一连接入口。
5. 保证所有索引可从 Obsidian 重建，避免数据库成为新的单点权威。

## 研究结论

### Letta

吸收 Core Memory 与 Archival Memory 分层：少量稳定记忆固定进入上下文，大量历史资料按需召回。

### Graphiti / Zep

吸收事件追加、事实有效时间、旧事实失效、增量更新和混合检索设计。

### LlamaIndex

吸收 BM25、向量、元数据过滤与 Reciprocal Rank Fusion 的组合方式。

### MCP

使用 Resources、Prompts 和 Tools 作为统一 AI 接口，并保留主人确认和权限边界。

## 新增核心模块

### `src/retrieval/chunker.py`

- 按 Markdown 标题层级分块
- 保留标题路径
- 保留开始行和结束行
- 使用稳定块 ID
- 支持最大长度和重叠窗口
- 长文本优先在句号或换行处分割

### `src/retrieval/memory_db.py`

新增 `storage/lingji_memory.db`：

- SQLite WAL
- busy timeout
- 外键
- FTS5
- trigram 优先，unicode61 回退
- BM25
- 事务式重建
- 单文档原子替换
- 文档、分块和 FTS 一致性检查
- revision 版本号

该数据库是可重建索引，不保存唯一正式正文。

### `src/retrieval/hybrid.py`

- 全文召回
- 可选语义召回接口
- RRF 排序融合
- 项目、标签、类型、状态、隐私和时间过滤
- Core Memory、重要性和 recall_weight 加权
- LRU + TTL 缓存
- revision 自动缓存失效

### `src/retrieval/enhanced.py`

中文短查询补偿：

- FTS5 主召回不足时才执行
- 将短中文组合拆为关键片段
- 使用受控 `LIKE` 补召回
- 保持项目、标签、隐私和时间过滤
- 不替代高速主召回

### `src/retrieval/context_pack.py`

Context Pack：

1. 先装入与 Agent 和项目匹配的 Core Memory
2. 再装入与任务相关的检索分块
3. 每项带来源路径、标题和行号
4. 严格限制字符预算
5. 保存 memory revision

### `src/memory/lifecycle.py`

永久记忆生命周期：

```text
candidate → owner approved → core/active
candidate → owner rejected → archive
core/active → superseded/valid_to
```

AI 只能提议，不能直接晋升。

### `src/memory/obsidian_ui.py`

生成：

- `00-System/Permanent-Memory.md`
- `00-System/Bases/Permanent Memory.base`
- `00-System/Templates/核心记忆模板.md`

Base 包含：

- 核心记忆
- AI 候选
- 手动草稿
- 已失效记忆

手动模板默认是草稿，不会因模板属性被误注入上下文。

### `src/gateway/profiles.py`

AI 权限配置：

- ChatGPT
- Codex
- Claude
- Gemini
- Kimi
- DeepSeek
- Ollama
- LingJi Local Agent

远程 AI 默认只允许 `public/private`；本地模型可按授权读取 `restricted`。

### `src/gateway/memory_gateway.py`

统一工具：

```text
search_memory
fetch_memory
get_core_memory
build_context_pack
propose_memory
recent_changes
memory_health
```

所有 AI 通过同一网关使用同一版记忆和权限。

### `src/gateway/adapters.py`

为不支持 MCP 或暂时使用直接 API 的模型生成统一 Context Envelope：

- OpenAI 格式
- Anthropic 格式
- Gemini 格式
- 通用 Prompt 格式

Envelope 带：

- agent ID
- memory revision
- project
- citations
- 检索内容不可信标记

### `src/mcp_server.py`

FastMCP Server：

- Tools
- Resources
- Prompt
- stdio
- Streamable HTTP

MCP SDK 单独锁定在：

```text
requirements-mcp.txt
mcp>=1.27,<2
```

避免基础服务被协议 SDK 的快速更新拖动。

## Obsidian 新目录

```text
00-System/Context-Packs
01-Inbox/AI-Memory
03-Knowledge/Core-Memory/Identity
03-Knowledge/Core-Memory/Preferences
03-Knowledge/Core-Memory/Goals
03-Knowledge/Core-Memory/Constraints
03-Knowledge/Core-Memory/Working-Rules
03-Knowledge/Core-Memory/General
09-Archive/Rejected-Memory-Candidates
```

## 永久记忆属性

```yaml
memory_tier: core
status: active
review_status: approved
pin_to_context: true
agent_scope:
  - all
recall_weight: 1.2
valid_from:
valid_to:
supersedes: []
superseded_by:
```

## 稳定性设计

1. Obsidian 正文与检索数据库分离。
2. 主服务启动时校验并建立召回库。
3. 文件变化只增量替换对应文档和分块。
4. 文件删除同时删除文档、分块和 FTS 行。
5. 每 6 小时检查 SQLite 和 FTS 一致性。
6. 检查失败自动从 Obsidian 重建。
7. 向量服务不可用时 FTS5 继续提供检索。
8. 召回库 revision 变化自动使旧缓存失效。
9. 远程模型不能读取 restricted 内容。
10. MCP Server 不启动主服务调度器和 Watchdog，避免多个客户端重复运行后台任务。

## 速度设计

- SQLite WAL 支持稳定并发读取
- FTS5/BM25 作为快速主召回
- 项目和隐私在数据库查询阶段过滤
- substring 只在主召回不足时运行
- 查询缓存默认 256 条、120 秒
- 每个记忆最多返回 3 个分块，降低上下文重复
- Context Pack 按字符预算截断

## 测试结果

共运行 37 项单元测试：

- 永久记忆候选、晋升、拒绝和权限
- Core Memory Agent Scope
- Context Pack 顺序与预算
- 中英文全文检索
- 中文短查询模糊补召回
- 项目、标签、隐私和时间过滤
- 行号引用
- 单文件增量更新和删除
- 数据库 revision 和完整性
- OpenAI、Anthropic、Gemini Context Adapter
- 提示词注入边界标记
- 原有 Obsidian、命令、调度、机会和索引功能

执行结果：

```text
Ran 37 tests
OK
```

GitHub Actions：

```text
unit-tests (3.11): success
unit-tests (3.12): success
mcp-smoke-test: success
```

## 当前限制

1. 语义向量接口已预留，但 Qdrant 仍未作为默认召回通道启用。
2. 关系图召回尚未实现，只保存类型化关系属性。
3. PDF、Word、Excel、PPT 尚未进入统一分块数据库。
4. Streamable HTTP 当前只适合本机，尚未实现公网认证、TLS、限流和 OAuth。
5. 尚未与主人电脑未推送的 `second_brain/lingji_tools.py` 合并。
6. 尚未在真实 Vault 上做性能基准、迁移预览和恢复演练。
7. 没有对各 AI 官方客户端逐个完成真实 MCP 连接测试。

## 下一阶段

优先级：

1. 与本机 `lingji_tools.py` 合并，统一旧工具和 Memory Gateway。
2. SQLite FTS5 性能基准与 1万、10万分块测试。
3. 接入 Qdrant/bge-m3，做真正 hybrid 检索与降级测试。
4. 加入关系图召回和时间事实冲突检测。
5. PDF、Word、Excel、PPT 解析和页码/单元格/幻灯片引用。
6. 为 Codex、ChatGPT、Claude、Gemini、Kimi、DeepSeek、Ollama 分别生成连接配置。
7. 对真实 Vault 创建快照后做迁移和回滚测试。

## 结论

本阶段已经把灵机从“可以搜索 Markdown”推进到：

```text
主人确认的核心记忆
+ 可重建全文召回库
+ 时间有效性
+ 多 AI 统一权限网关
+ MCP / 直接 API 双连接
```

当前适合标记为 `v0.3-alpha`，还不应合并成正式生产版。剩余工作主要是本机真实数据集成、语义向量、文档解析和各 AI 客户端的端到端连接验证，而不是继续给文件夹起更庄严的名字。
