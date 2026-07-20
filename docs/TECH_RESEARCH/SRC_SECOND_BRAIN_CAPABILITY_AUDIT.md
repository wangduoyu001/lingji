# `src/` 与 `second_brain/` 能力对比审计

> 仓库：`wangduoyu001/lingji`
>
> 分支：`feature/second-brain-memory`
>
> 审计基线：远程 HEAD `284a77bb9e330609accd76a3d013c283f57be7f1`
>
> 审计方式：静态代码与文档审计。
>
> 本次没有修改功能代码、数据库、依赖、配置或运行数据，也没有执行本地测试。

## 1. 审计结论

`src/` 和 `second_brain/` 不是两个边界清晰的普通模块，而是两套逐渐重叠的记忆系统和运行时。

总体判断：

1. `src/` 已经成为更符合 LingJi 最新产品定位的长期主线。
2. `second_brain/` 是一套已经可运行的早期第二大脑实现，仍保存若干 `src/` 尚未完整接通的关键能力。
3. 两套系统当前存在数据库、API、端口、UI、采集、记忆生命周期、检索和配置的重复与冲突。
4. 不应继续在两边同时开发同类功能。
5. 不应立即删除 `second_brain/`，因为它目前仍实际承担：
   - Qdrant 向量搜索
   - Ollama 向量模型回退
   - 结构化会话和消息存储
   - 记忆版本、关系和冲突表
   - production / acceptance 双运行空间
   - Second Brain 验收 API 和 PySide6 验收界面
6. 推荐把 `src/` 定为最终统一架构，将 `second_brain/` 中仍有价值的能力逐项迁入或适配到 `src/`，完成能力对等验证后再退役旧运行时。

一句话定位：

```text
src/
= LingJi 的长期平台主线、统一记忆网关、采集系统、控制中心与运维系统

second_brain/
= 已可运行的早期结构化记忆与 Qdrant 原型，应进入冻结、迁移和兼容阶段
```

## 2. 两套架构的真实定位

### 2.1 `src/` 当前架构

```text
Obsidian 单一 Vault
  -> PEMISIndex
  -> lingji_memory.db
       -> Markdown 文档元数据
       -> 标题层级分块
       -> FTS5 / BM25
       -> 时间、隐私、项目、标签、Agent Scope
  -> HybridRetriever
       -> FTS5
       -> 中文子串回退
       -> 可选 SemanticProvider
       -> RRF 和元数据加权
  -> ContextPackBuilder
  -> MemoryGateway
       -> AIProfileRegistry
       -> MCP
       -> AI Context Adapter
  -> Local Control Service / API :8766
  -> Tauri / React 桌面控制中心
```

配套能力还包括：

- 统一 ExtractionAdapter
- SQLiteExtractionQueue
- 租约、心跳、重试和幂等
- ChatGPT、Codex、网页、社交平台和媒体采集
- 启动健康检查
- 硬件和 GPU 检测
- 本地模型清单
- ASR、OCR 和镜头检测
- 存储生命周期
- 校验备份和隔离恢复
- Skill Registry
- 调度、处理状态和审计事件
- 机会系统和 PEMIS 原有逻辑

### 2.2 `second_brain/` 当前架构

```text
AI Chat JSON / Codex JSON / Obsidian Markdown
  -> BoundedWatcher
  -> ChatConnector / CodexConnector / ObsidianConnector
  -> second_brain.sqlite3
       -> sources
       -> conversations
       -> messages
       -> memories
       -> memory_versions
       -> memory_relations
       -> conflicts
       -> retrieval_logs
       -> knowledge_documents
  -> MemoryService
  -> RetrievalService
       -> SQLite LIKE
       -> OllamaEmbedder
       -> Qdrant VectorStore
  -> FastAPI :8765
  -> PySide6 Desktop
```

它还提供：

- production / acceptance 物理隔离运行空间
- active memory 与 Qdrant point 的生命周期绑定
- Qdrant 重建
- pending / approve / reject / supersede
- 结构化 source / conversation / message 展开
- 冲突检测和冲突处理
- 验收场景和验收库重置

## 3. 最严重的架构矛盾

### 3.1 两个“事实来源”

`src/retrieval/memory_db.py` 明确规定：

```text
Obsidian 是权威记忆来源。
lingji_memory.db 是可删除并重建的派生索引。
```

`second_brain/` 的架构规则则规定：

```text
SQLite 是结构化事实来源。
Qdrant 是可重建缓存。
```

这两种设计不能长期同时成立。

当前可能出现：

1. Obsidian 中一条记忆已经被主人修改，但 `second_brain.sqlite3` 仍保存旧版本。
2. `second_brain.sqlite3` 中一条 active memory 已经批准，但 Obsidian Core Memory 中没有对应正式文件。
3. 两套系统分别认为自己保存的是当前事实。
4. AI 通过 MCP 读取 `src`，桌面 Inspector 又读取 `second_brain`，得到不同答案。

推荐唯一口径：

```text
正式知识和永久记忆正文：Obsidian / Git
运行事件和任务状态：lingji_state.db
可重建全文和语义索引：lingji_memory.db + Qdrant
原始输入：storage/raw
```

`second_brain.sqlite3` 不应继续作为第二套长期权威记忆库。

### 3.2 端口冲突

当前默认配置：

```text
second_brain FastAPI: 127.0.0.1:8765
src MCP Streamable HTTP: 127.0.0.1:8765
Local Control API: 127.0.0.1:8766
```

当 MCP 使用 Streamable HTTP 时，`src` MCP 与 `second_brain` API 无法同时绑定 `8765`。

这是确定的运行冲突，不是理论风险。

短期必须做到至少一项：

- 将 MCP HTTP 改为独立端口，例如 `8767`；或
- 将 Second Brain API 改为独立兼容端口；或
- 停止同时运行两套 HTTP 服务。

长期建议保留：

```text
8766 = 统一 Local Control API
8767 = 可选 MCP Streamable HTTP
stdio = Codex 等本地 MCP 默认模式
```

并逐步取消独立 `second_brain` API。

### 3.3 两套桌面 UI

当前同时存在：

```text
second_brain/desktop/
= PySide6 第二大脑桌面端

desktop/lingji-control/
= Tauri + React 灵机本地控制中心
```

仓库最新规则已经明确 Tauri 控制中心是长期主 UI。

因此：

- Tauri 应承接新的正式功能。
- PySide6 只保留验收和兼容作用。
- 不应继续让两个 UI 同时扩展记忆列表、检索、冲突和状态页面。
- Memory Inspector 应进入 Tauri，而不是再建立第三套桌面页面。

### 3.4 两套采集链路

`second_brain`：

```text
BoundedWatcher
  -> ChatConnector
  -> CodexConnector
  -> ObsidianConnector
```

`src`：

```text
ExtractionAdapter
  -> AdapterRegistry
  -> SQLiteExtractionQueue
  -> ExtractionPipeline
  -> VaultExtractionSink
  -> 增量索引回调
```

`src` 采集框架已经具备：

- 统一 Adapter 合同
- Adapter 版本
- 输入哈希
- 幂等键
- 文件和目录快照
- 任务优先级
- 有限重试
- worker 租约
- 心跳
- stale job 回收
- 运行时参数
- 隐私扫描
- 写入后增量索引

`second_brain` watcher 只使用修改时间 JSON 状态文件防重复，失败没有持久任务租约和完整重试语义。

新数据入口应只接入 `src/extraction/`。

## 4. 能力矩阵

| 能力 | `src/` | `second_brain/` | 当前领先方 | 审计结论 |
|---|---|---|---|---|
| 正式记忆正文 | Obsidian 单 Vault | SQLite memories | `src` | `src` 更符合最新产品规则 |
| 可重建记忆索引 | `lingji_memory.db` | Qdrant 可重建，SQLite 不可重建定位 | `src` | `src` 的事实层边界更清晰 |
| 结构化聊天存储 | Markdown 对话文档 | sources/conversations/messages 表 | `second_brain` | 应保留并迁移其审计价值 |
| 记忆候选 | AI-Memory Markdown | pending memories | `src` | `src` 有更明确主人审核边界 |
| Core Memory | 已实现分层和 pin | 无独立 Core 层 | `src` | `src` 明显更完整 |
| 主人确认 | promote/reject/supersede 强制确认 | API approve/reject 可执行 | `src` | `src` 权限边界更严格 |
| 版本历史 | Git/文件事件，未形成统一查询模型 | memory_versions 表 | `second_brain` | 可迁移查询能力，不应保留第二事实源 |
| 关系 | Frontmatter relationships | memory_relations 表 | 接近 | `src` 关系更贴近知识图谱，`second_brain` 查询更直接 |
| 冲突检测 | 尚无统一 ConflictService | 同项目、类型、标题差异检测 | `second_brain` | 逻辑简单但已可用，应迁移思想 |
| 中文全文检索 | FTS5 trigram + unicode61 回退 | LIKE | `src` | `src` 显著领先 |
| BM25 | 已实现 | 无 | `src` | 保留 |
| 中文短词回退 | 已实现 substring fallback | LIKE 本身可命中但无专门策略 | `src` | 保留 |
| 向量检索 | 有 SemanticProvider 接口，但未接线 | Qdrant 已真实接通 | `second_brain` | 这是迁移最高优先级 |
| 嵌入模型 | Embedder 存在，但未接入 MemoryGateway | OllamaEmbedder 已接入检索和重建 | `second_brain` | 适配到 `src` |
| 排序融合 | RRF + 多种元数据 boost | exact seed 与向量分数取 max | `src` | `src` 设计更成熟 |
| 项目过滤 | 已实现 | 已实现，并包含 global fallback | 接近 | 合并语义时保留 global fallback 解释 |
| 标签过滤 | 已实现 | 无 | `src` | 保留 |
| 隐私过滤 | public/private/restricted | 无 | `src` | 必须保留 |
| Agent Scope | 已实现 | 无 | `src` | 必须保留 |
| 时间有效性 | valid_from / valid_to 查询过滤 | 字段存在，检索未完整使用 | `src` | `src` 已形成闭环 |
| 核心记忆优先 | 已实现 | 无 | `src` | 保留 |
| 来源引用 | 文件、标题、行号、chunk | source_id/source_path，缺统一行号 | `src` | `src` 更适合可核查回答 |
| Context Pack | 核心优先、预算、revision、引用、注入警告 | 简单字符预算和类型分组 | `src` | `src` 明显领先 |
| 多 AI 权限 | AIProfileRegistry | 无 | `src` | 保留 |
| MCP | stdio + Streamable HTTP + tools/resources/prompts | 无独立 MCP | `src` | `src` 是正式出口 |
| ChatGPT 导入 | ZIP/JSON/目录、安全限制、隐私分类 | JSON/inline，结构化入库 | 各有优势 | 将结构化审计能力合入 `src` 导入结果 |
| Codex 导入 | 统一 Adapter 和报告候选 | CodexConnector | `src` | 新开发只用 `src` |
| 网页和社交采集 | 已实现统一 WebCaptureAdapter | 无 | `src` | 保留 |
| 媒体采集 | FFprobe/FFmpeg + ASR/OCR/镜头 | 无 | `src` | 保留 |
| 原始资料保存 | 统一 storage/raw 快照 | raw/ai_chat JSON | `src` | `src` 更通用 |
| 持久任务队列 | extraction_jobs + lease/retry | import_jobs，无 worker lease | `src` | `src` 明显领先 |
| API | 统一控制 API :8766 | Second Brain API :8765 | `src` 战略领先 | 逐步代理并退役旧 API |
| 桌面 UI | Tauri + React | PySide6 | `src` | Tauri 为长期主 UI |
| 验收空间 | 通用 acceptance checker | production/acceptance RuntimeRegistry | `second_brain` | 物理隔离概念值得迁移 |
| Qdrant collection 隔离 | 尚未接线 | production/acceptance collection | `second_brain` | 迁移时保留 |
| 系统状态 | Control API、health、events | memory/system status | `src` | 但当前脑状态尚未接真实记忆数据 |
| 硬件/GPU | 已实现 | 无 | `src` | 保留 |
| 模型中心 | 已实现 Ollama inventory 和 provider 状态 | 仅 embedding status | `src` | 保留 |
| 备份 | 校验 ZIP、SQLite snapshot、隔离恢复 | 无系统级备份 | `src` | 保留 |
| 存储生命周期 | 已实现 | 无 | `src` | 保留 |
| Skill Registry | 已实现 | 无 | `src` | 保留 |
| 调度和审计事件 | lingji_state.db | 部分 import/retrieval logs | `src` | `src` 更完整 |
| 机会系统 | 已实现 | 无 | `src` | `src` 独占业务能力 |

## 5. `src/` 领先能力详审

### 5.1 单一 Vault 与可重建索引

`src` 把正式记忆和知识保存在 Obsidian 中，`lingji_memory.db` 只保存：

- memory_documents
- memory_chunks
- FTS5 数据
- revision
- 索引统计

数据库损坏后可以由 Vault 重建。

这符合：

- 人工可编辑
- Git 可追踪
- AI 不能暗中改长期事实
- 索引可替换
- 不绑定某一个数据库实现

### 5.2 更成熟的全文检索

`src/retrieval/memory_db.py` 已实现：

- WAL
- busy_timeout
- FTS5
- trigram tokenizer
- unicode61 回退
- BM25 权重
- 标题、heading、正文和标签字段
- 时间有效性过滤
- 隐私过滤
- status 和 memory_type 过滤
- 行号和 chunk 引用
- revision
- integrity check

`src/retrieval/enhanced.py` 还为短中文查询提供了受控的 substring fallback。

这比 `second_brain` 当前使用：

```sql
WHERE title LIKE ? OR content LIKE ?
```

更适合长期大规模中文知识库。

### 5.3 更完善的排序逻辑

`src` 使用：

- lexical channel
- optional semantic channel
- RRF
- 标题命中加权
- heading 命中加权
- tag 命中加权
- core memory 加权
- pin_to_context 加权
- importance 加权
- recall_weight
- project 加权
- active / approved 加权
- 去重和单记忆 chunk 数量限制

`second_brain` 当前使用固定种子分数：

```text
memory exact = 0.55
knowledge exact = 0.65
vector = 0.7 * similarity
final = max(exact, vector)
```

`second_brain` 的方式简单、可解释，但不适合作为最终大规模混合排序。

### 5.4 Context Pack

`src` 已经具备真正面向多 AI 的 Context Pack：

- Core Memory 优先
- Agent Scope
- project
- privacy
- memory type
- tags
- 严格字符预算
- citation
- memory revision
- 生成时间
- 提示词注入边界

`second_brain.context()` 只对搜索结果做字符预算，并按 RULE、DECISION、LESSON、PREFERENCE 分类。

### 5.5 AI 权限模型

`AIProfileRegistry` 已定义：

- ChatGPT
- Codex
- Claude
- Gemini
- Kimi
- DeepSeek
- Ollama
- LingJi Local Agent

每个客户端具有：

- allowed_tools
- allowed_privacy
- max_context_chars
- can_propose_memory
- can_modify_core_memory
- local_only

`second_brain` 没有 Agent 级权限，只通过 workspace header 区分 production 和 acceptance。

### 5.6 统一 MCP

`src/mcp_server.py` 已公开：

- search_memory
- fetch_memory
- get_core_memory
- build_context_pack
- propose_memory
- recent_changes
- memory_health
- ChatGPT 导入
- Codex 报告
- 网页采集
- Skill 管理
- Extraction Queue 管理

同时提供 Resources 和 Prompt。

这是多个 AI 共享同一记忆的正式连接层。

### 5.7 统一采集与任务队列

`src/extraction` 已经解决扩展性和可靠性问题：

- AdapterRegistry
- 统一 request / batch / document 模型
- 幂等键包含来源、Adapter 名称、版本、文件哈希、payload 和 options
- 原始资料快照
- SQLite 持久队列
- worker lease token
- heartbeat
- stale lease 回收
- max attempts
- retry / failed
- 后处理索引回调

这套框架适合继续加入：

- 微信
- 浏览器
- 手机分享
- 本地文档
- 音频和视频
- 未来新平台

### 5.8 本地控制和运维

`src` 独占以下平台能力：

- Local Control API
- Tauri 控制中心
- Runtime Settings
- Hardware Capability
- GPU telemetry
- Model Inventory
- Media Semantic Service
- BackupManager
- StorageLifecycleManager
- StartupHealthChecker
- SkillRegistry
- Scheduler
- Processing State
- Audit Events
- Opportunity System

这些能力不应复制到 `second_brain/`。

## 6. `second_brain/` 必须保留并迁移的能力

### 6.1 已真实接通的 Qdrant

`second_brain/vector_store.py` 已支持：

- embedded Qdrant
- `:memory:` 测试模式
- 本地文件模式
- remote URL
- collection 自动创建
- dimension 检查
- cosine distance
- upsert
- delete
- document chunk delete
- query_points
- scroll
- status
- collection rebuild

`src` 虽然有 `SemanticProvider` 接口，但当前 `build_memory_gateway()` 明确使用：

```python
semantic_provider=None
```

因此现实状态是：

```text
src 检索 = FTS5 + substring + metadata
second_brain 检索 = LIKE + Qdrant
```

下一步最优做法不是重写向量库，而是把 `second_brain` 的 Qdrant 能力适配为 `src.retrieval.hybrid.SemanticProvider`。

建议目标入口：

```text
src/retrieval/semantic_qdrant.py
```

它应复用或迁移：

- VectorStore
- OllamaEmbedder
- collection status
- point upsert/delete
- rebuild

最终由 `build_memory_gateway()` 根据配置注入，而不是继续传 `None`。

### 6.2 结构化会话审计

`second_brain` 保存：

- source
- conversation
- message
- role
- ordinal
- external_id
- timestamp
- content_hash
- import job

`src` ChatGPT Adapter 会把完整对话保存为 Markdown，并保留节点、角色、模型和附件信息，但目前没有统一 SQL 会话查询模型。

需要区分：

```text
Markdown / raw export
= 权威来源

结构化 conversation/message 表
= 可重建查询索引
```

推荐将结构化会话查询能力迁入 `lingji_memory.db` 的派生索引层，或建立可由 Markdown/raw 重建的 Source Catalog。

禁止把迁移后的会话表重新定义为第二个正式事实来源。

### 6.3 版本、关系和冲突查询

`second_brain` 已有：

- memory_versions
- memory_relations
- conflicts

其中：

- version 表便于 Inspector 展示历史
- relation 表便于直接查询 supersedes
- conflict 表便于形成审核队列

`src` 当前依赖：

- Git 历史
- Markdown Frontmatter
- events

但缺少统一的 Inspector 查询模型。

推荐：

1. 正文版本继续由 Git / Markdown 负责。
2. `lingji_state.db.events` 记录 lifecycle 事件。
3. `lingji_memory.db` 可维护可重建的 relation / conflict read model。
4. 冲突结果只生成候选，不自动修改 Core Memory。

不建议直接复制 `second_brain.memories` 和 `memory_versions` 成为新的权威数据表。

### 6.4 production / acceptance 物理隔离

`RuntimeRegistry` 为 Second Brain 建立：

- production SQLite
- acceptance SQLite
- production Qdrant collection
- acceptance Qdrant collection
- acceptance raw/inbox/log/runtime 路径

这一思想值得保留。

迁移目标应是让 `src` 的统一服务支持：

```text
production workspace
acceptance workspace
```

并隔离：

- Vault fixture
- lingji_state.db
- lingji_memory.db
- Qdrant collection
- raw archive
- derived files
- logs

### 6.5 PySide6 验收经验

PySide6 本身不应继续作为正式主 UI，但其中的验收功能可以迁移：

- 重置验收库
- seed
- run all
- latest result
- production / acceptance 切换
- 记忆审核流程测试
- 冲突处理测试
- Qdrant rebuild 测试

迁移完成后，PySide6 可以进入冻结或退役状态。

## 7. 当前不应保留的重复实现

### 7.1 `second_brain` BoundedWatcher

新入口应全部进入 `src/extraction`。

保留 watcher 只会产生：

- 双重导入
- 不同幂等规则
- 不同原始归档目录
- 不同失败状态
- 不同重试方式
- 不同索引刷新时机

### 7.2 独立 Second Brain API

长期 Tauri 只应连接一个 authenticated base URL：

```text
http://127.0.0.1:8766
```

Second Brain 的只读能力应通过：

```text
LocalControlService
  -> MemoryGateway / Inspector Service
```

公开。

不应让 Tauri 同时连接 `8765` 和 `8766`。

### 7.3 PySide6 正式功能扩展

除兼容和迁移验证外，不再新增正式页面。

### 7.4 两套记忆批准流程

当前有：

```text
src:
AI candidate Markdown
  -> owner_confirmed
  -> Core Memory

second_brain:
pending SQLite memory
  -> approve API
  -> active SQLite memory
```

最终只保留第一套主人确认语义。

### 7.5 两套模型配置

当前默认值不同：

```text
src embed model: nomic-embed-text
second_brain primary: bge-m3
second_brain fallback: nomic-embed-text
```

最终模型选择应进入统一 Model Center / Runtime Settings。

Embedding Provider 不应各自读取不同环境变量并自行决定模型。

## 8. 文档与现实代码偏差

### 8.1 ARCHITECTURE.md 已落后

当前架构文档仍写：

- PySide6 是 Second Brain 桌面端
- No WebUI
- Second Brain 与 PEMIS 隔离并行

但最新仓库规则和代码已经形成：

- Tauri + React 主控制中心
- Local Control API
- MCP MemoryGateway
- 统一 Extraction Pipeline
- `src` 永久记忆与 Context Pack

因此 `docs/ARCHITECTURE.md` 已无法代表当前目标架构。

### 8.2 PROJECT_STATUS.md 的 MCP 描述已落后

状态文档仍提到 Second Brain MCP 未创建，但实际存在：

```text
src/mcp_server.py
run_mcp_server.py
```

它属于 `src` 主线，而不是 `second_brain/mcp_server.py`。

### 8.3 “Second Brain” 名称产生误导

从现实能力看：

```text
src/
已经包含长期记忆、召回、Context Pack、MCP、采集和控制中心。
```

因此 `second_brain/` 不再代表唯一第二大脑实现。

建议在文档中将它明确标记为：

```text
Legacy Second Brain Runtime
或
Second Brain Compatibility Runtime
```

直到迁移完成。

## 9. 推荐目标架构

```text
                           ┌──────────────────────────┐
                           │ Obsidian Single Vault    │
                           │ 正式知识与永久记忆正文   │
                           └────────────┬─────────────┘
                                        │
                 ┌──────────────────────┼──────────────────────┐
                 │                      │                      │
                 ▼                      ▼                      ▼
        lingji_state.db         lingji_memory.db            Qdrant
        运行/任务/事件          可重建全文与元数据索引      可重建语义索引
                 │                      │                      │
                 └──────────────────────┼──────────────────────┘
                                        ▼
                               Unified MemoryGateway
                               - FTS5 / substring
                               - semantic provider
                               - RRF
                               - privacy
                               - agent scope
                               - citations
                               - context pack
                               - conflict read model
                                        │
                   ┌────────────────────┼────────────────────┐
                   ▼                    ▼                    ▼
                 MCP             Local Control API       Internal Jobs
             stdio / HTTP             :8766
                                        │
                                        ▼
                                  Tauri Desktop
```

结构化原始来源：

```text
storage/raw
+ Vault Source Markdown
+ 可重建 conversation/message 查询索引
```

不再保留第二套权威 `memories` 数据库。

## 10. 分阶段收敛计划

### Phase 0：立即冻结重复扩展

目标：停止架构继续分叉。

1. 新记忆功能默认开发在 `src/`。
2. 新采集入口只进入 `src/extraction`。
3. 新桌面页面只进入 Tauri。
4. `second_brain/` 只允许：
   - 修复迁移阻塞问题
   - 增加兼容读取
   - 增加迁移测试
5. 解决 `8765` 端口冲突。
6. 文档标记 `second_brain` 为 compatibility runtime。

### Phase 1：把 Qdrant 接入 `src`

目标：先补上 `src` 最关键的现实缺口。

1. 将 Qdrant 封装成 `SemanticProvider`。
2. 接入统一 Runtime Settings 和 Model Center。
3. 索引 ID 使用稳定 memory_id + chunk_id。
4. 实现增量 upsert/delete。
5. 支持完整 rebuild。
6. 支持 collection status。
7. production / acceptance collection 隔离。
8. Qdrant 不可用时继续使用 FTS5。
9. 测试 RRF 排名在启用/禁用向量时均稳定。

### Phase 2：迁移结构化来源审计

目标：保留 `second_brain` 的 source/conversation/message 优势。

1. 从 ChatGPT Markdown/raw 重建 conversation/message 查询模型。
2. 保留 external_id、role、ordinal、timestamp、model、attachment reference。
3. 不把消息表定义为正式永久记忆。
4. Inspector 默认只展示元数据，正文按需展开。
5. 增加隐私过滤。

### Phase 3：迁移关系、冲突和 Inspector

目标：统一记忆可视化。

1. 基于 Vault metadata 和事件建立 relation read model。
2. 建立 read-only conflict candidate 检测。
3. 冲突不得自动修改 Core Memory。
4. Memory Inspector 只读取统一 MemoryGateway。
5. Brain Status 和 Inspector 使用同一统计来源。
6. Tauri 只连接 `8766`。

### Phase 4：双读对比验收

目标：证明可以安全退役旧运行时。

在同一测试资料上对比：

- 导入数量
- 来源数量
- 会话数量
- 记忆候选数量
- active/core 数量
- exact/FTS 召回结果
- semantic 召回结果
- project 范围
- privacy 范围
- conflict 数量
- citation
- Qdrant point 数量

所有差异必须有解释，禁止仅比较总数。

### Phase 5：退役 `second_brain` 运行时

满足以下条件后才允许：

1. `src` 已接通 Qdrant。
2. 结构化来源查询已迁移。
3. Inspector 已使用统一 MemoryGateway。
4. production / acceptance 已隔离。
5. 旧 SQLite 数据已导出和验证。
6. PySide6 验收能力已迁移。
7. 端到端和回归测试通过。
8. 本地真实数据完成只读对比。
9. 有可回滚备份。

退役方式：

- 先停止自启动
- 再停止写入
- 保留只读兼容期
- 最后移入 archive 或删除

禁止直接删除目录和数据库。

## 11. 文件级开发入口

### 11.1 `src/` 应继续扩展

| 目标 | 入口 |
|---|---|
| 统一记忆网关 | `src/gateway/memory_gateway.py` |
| Runtime 装配 | `src/gateway/bootstrap.py` |
| 全文和混合召回 | `src/retrieval/hybrid.py`、`src/retrieval/enhanced.py` |
| 索引数据库 | `src/retrieval/memory_db.py` |
| Context Pack | `src/retrieval/context_pack.py` |
| 增量同步 | `src/retrieval/incremental_sync.py` |
| 永久记忆生命周期 | `src/memory/lifecycle.py` |
| 统一采集 | `src/extraction/` |
| MCP | `src/mcp_server.py` |
| 控制服务 | `src/control/service.py` |
| 控制 API | `src/control/api.py` |
| Tauri UI | `desktop/lingji-control/src/` |
| 运行状态 | `src/storage/state_db.py` |
| 备份 | `src/storage/backup.py` |
| 模型中心 | `src/model_center/` |
| 媒体能力 | `src/media/` |
| Skill | `src/skills/` |

### 11.2 `second_brain/` 只作为迁移来源

| 可复用能力 | 当前入口 | 目标去向 |
|---|---|---|
| Qdrant | `second_brain/vector_store.py` | `src/retrieval` SemanticProvider |
| Ollama embedding | `second_brain/embedding.py` | 统一 Provider / Model Center |
| structured conversations | `second_brain/db.py`、`connectors/chat.py` | 可重建 Source/Conversation read model |
| memory versions | `second_brain/db.py` | Git + events + Inspector read model |
| relations/conflicts | `second_brain/conflict/`、DB tables | `src` conflict/read model |
| dual workspace | `second_brain/runtime_registry.py` | 统一 workspace runtime |
| acceptance scenarios | `second_brain/acceptance.py` | `src/acceptance` / Tauri 验收 |
| PySide flows | `second_brain/desktop/` | 迁移测试参考，不继续扩展 |

## 12. 测试审计

### 12.1 `src` 已有测试覆盖

相关测试包括：

- `tests/test_memory_retrieval.py`
- `tests/test_memory_lifecycle.py`
- `tests/test_permanent_memory_gateway.py`
- `tests/test_incremental_index_sync.py`
- `tests/test_chatgpt_importer.py`
- `tests/test_extraction_queue.py`
- `tests/test_extraction_worker.py`
- `tests/test_ai_context_adapters.py`
- `tests/test_control_api.py`
- `tests/test_control_api_extended.py`
- `tests/test_brain_status_e2e.py`
- `tests/test_backup_manager.py`
- `tests/test_model_inventory.py`
- `tests/test_media_extraction.py`
- `tests/test_media_semantic.py`

已验证的设计方向包括：

- 中英文全文检索
- line citation
- project/tag/privacy/time 过滤
- 增量更新和删除
- revision
- Core Memory 优先
- context budget
- remote AI 禁止 restricted
- AI 只能 propose，不能直接 promote

### 12.2 `second_brain` 已有测试覆盖

主要集中在：

- `tests/test_second_brain.py`
- `tests/test_desktop.py`

已覆盖：

- 对话导入幂等
- supersede
- SQLite 重建 Qdrant
- Obsidian 分块但不自动蒸馏
- API 路由存在
- 原启动链隔离
- PySide6 UI

### 12.3 迁移必须新增的契约测试

建议新增一套不依赖具体目录名称的 Memory Capability Contract：

1. 同一 Vault 输入产生稳定 memory_id。
2. FTS5 和 semantic channel 都返回 citation。
3. Qdrant 不可用时 FTS5 正常。
4. remote AI 不得读取 restricted。
5. active/core 与 semantic point 一致。
6. superseded 记忆不会进入当前上下文。
7. source/conversation/message 可由 raw 或 Markdown 重建。
8. production 和 acceptance 数据完全隔离。
9. Brain Status、Inspector、MCP 统计一致。
10. Tauri 只使用 Local Control API。
11. 同一输入不会被两条采集链重复写入。
12. 关闭 legacy runtime 后所有正式功能仍工作。

## 13. 风险排序

### P0：立即处理

1. `8765` 端口冲突。
2. 两个事实来源。
3. 两条采集链可能重复导入。
4. Tauri Brain Status 尚未读取真实统一记忆数据。
5. 新功能继续落到错误目录的风险。

### P1：近期处理

1. `src` Qdrant 尚未接线。
2. 结构化 conversation/message 尚未迁移。
3. relation/conflict 缺统一查询层。
4. production/acceptance 尚未统一到主运行时。
5. 文档架构与代码现实不一致。

### P2：完成收敛前处理

1. PySide6 退役。
2. Second Brain API 退役。
3. 旧数据库导出与只读兼容。
4. 合并模型配置。
5. 清理重复脚本、环境变量和运行目录。

## 14. 最终裁决

### 长期保留

```text
src/
desktop/lingji-control/
Obsidian Single Vault
lingji_state.db
lingji_memory.db
Qdrant as optional rebuildable semantic index
Local Control API
MCP
```

### 从 `second_brain/` 迁移后保留

```text
Qdrant VectorStore 思路和实现
Ollama embedding fallback
structured source/conversation/message read model
memory relation/conflict read model
production/acceptance physical isolation
acceptance scenarios
```

### 冻结并最终退役

```text
second_brain BoundedWatcher
独立 Second Brain 写 API
PySide6 正式功能开发
SQLite memories 作为第二事实来源
第二套 approve/reject/supersede 流程
重复模型配置
```

最终结论：

```text
src/ 应成为唯一长期主线。
second_brain/ 不应继续平行发展，但当前也不能直接删除。
正确做法是先迁移 Qdrant、结构化来源、冲突与验收能力，
完成双读验证后，再将 second_brain 退役为历史兼容层。
```
