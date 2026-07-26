# LingJi 统一第二大脑开发路线图

> 状态：开发执行规划，尚未开始功能实现  
> 更新：2026-07-20  
> 仓库：`wangduoyu001/lingji`  
> 分支：`feature/second-brain-memory`  
> 规划基线：`aacf82d5791dd2c2acdb35e63c0fee3c9862137c`  
> 架构权威：`docs/MODULES/UNIFIED_MEMORY_ARCHITECTURE_PLAN.md`  
> 能力审计：`docs/TECH_RESEARCH/SRC_SECOND_BRAIN_CAPABILITY_AUDIT.md`

## 0. 本文用途与边界

本文把已经确认的统一架构拆成可独立执行、可测试、可回滚、可交接的开发任务。

本次规划任务只允许修改 Markdown 文档。本文中的类、接口、API、表和页面均为后续开发目标，不代表已经实现。

本次没有：

- 修改功能代码
- 修改数据库或 schema
- 安装依赖
- 修改配置
- 启动 Qdrant 开发
- 执行数据迁移
- 删除 `src/` 或 `second_brain/`
- 运行本地功能测试

权威文档引用顺序：

1. `docs/MODULES/UNIFIED_MEMORY_ARCHITECTURE_PLAN.md`
2. 本路线图
3. `docs/MODULES/UNIFIED_DESKTOP_UI_PLAN.md`
4. `docs/MODULES/MEMORY_INSPECTOR_IMPLEMENTATION_PLAN.md`
5. `docs/VECTOR_DATABASE.md`
6. `docs/MEMORY_SYSTEM.md`
7. 代码与测试报告

发生冲突时，以真实代码、最新测试和 GitHub 远程分支为准。

---

# 1. 当前代码事实摘要

## 1.1 已完成并可直接复用的 `src/` 能力

| 能力 | 真实入口 | 当前状态 | 后续处理 |
|---|---|---|---|
| 单一 Vault 与永久记忆生命周期 | `src/memory/lifecycle.py` | 已实现候选、主人确认、Core、拒绝、supersede | 保留为唯一正式生命周期 |
| 可重建全文索引 | `src/retrieval/memory_db.py` | 已实现 SQLite、WAL、FTS5、BM25、trigram、unicode61 回退、revision、完整性检查 | 直接复用 |
| 中文短词召回 | `src/retrieval/enhanced.py` | 已实现受控 substring fallback | 直接复用，不另写中文检索 |
| 混合排序框架 | `src/retrieval/hybrid.py` | 已实现 lexical channel、可选 semantic channel、RRF、metadata boost、去重 | 保留为唯一排名流程 |
| 检索过滤 | `src/retrieval/hybrid.py`、`memory_db.py` | 已实现项目、类型、状态、隐私、时间、Agent Scope、标签过滤 | 保留，语义结果必须经过同一过滤 |
| Context Pack | `src/retrieval/context_pack.py` | 已实现 Core 优先、预算、citation、revision、注入边界 | 保留为所有 AI 统一上下文 |
| 统一 MemoryGateway | `src/gateway/memory_gateway.py` | 已实现搜索、读取、Core、Context Pack、候选、recent changes、health、rebuild | 扩展，不复制第二个网关 |
| 多 AI 权限 | `src/gateway/profiles.py` | 已实现工具权限、隐私范围、上下文上限、本地限制 | 保留为权限权威 |
| MCP | `src/mcp_server.py` | 已实现 stdio/HTTP、tools/resources/prompts | 继续作为 AI 正式出口 |
| 统一采集 | `src/extraction/` | 已实现 Adapter、持久队列、幂等、租约、心跳、重试、raw snapshot、增量索引回调 | 所有新采集只进入此处 |
| 运行状态与审计 | `src/storage/state_db.py` | 已实现 scheduler、processing state、events | 作为统一运行状态源 |
| Local Control | `src/control/service.py`、`src/control/api.py` | 已实现认证 API、设置、任务、硬件、模型、媒体、存储、备份、验收 | 扩展为桌面唯一网关 |
| Runtime Settings | `src/control/runtime_settings.py` | 已实现可校验、可覆盖、事件记录的设置框架 | 增加 memory/vector/workspace/MCP 分组 |
| 模型中心 | `src/model_center/` | 已实现 Ollama 清单、能力和运行状态读取 | 增加 Embedding Provider 状态与选择 |
| Tauri UI | `desktop/lingji-control/` | 已实现主壳、12 个页面、8766 API 客户端 | 作为唯一正式 UI 扩展 |
| 备份、存储、硬件、媒体、Skill、机会 | `src/storage/`、`src/hardware/`、`src/media/`、`src/skills/` 等 | 已有真实实现 | 不迁入 `second_brain`，只接统一状态和任务合同 |

## 1.2 `src/` 当前真实缺口

1. `src/gateway/bootstrap.py` 仍以 `semantic_provider=None` 构建 `HybridRetriever`。
2. 当前 `SemanticProvider` Protocol 只有 `search()`，缺少 upsert、delete、rebuild、health、coverage 和 point existence 合同。
3. `MemoryGateway.rebuild()` 和 `IncrementalMemorySynchronizer` 只同步 `lingji_memory.db`，没有同步 Qdrant。
4. `HybridRetriever._semantic_search()` 捕获全部异常后直接返回空列表，无法向 Brain Status、Inspector 或用户暴露降级原因。
5. `RuntimeSettingsStore` 当前没有 Qdrant、Embedding、Workspace 和 MCP 设置分组。
6. `src/config.py` 没有 Qdrant 配置，MCP HTTP 默认端口仍是 `8765`。
7. `src/config.py` 当前默认 `backup_dir="D:/codex/backups/pemis"`，属于开发者绝对路径，后续必须改成可配置的安全默认值。
8. `LocalControlService` 没有构建或注入统一 `MemoryGateway`。
9. `LocalControlService.brain_status()` 读取不存在的 `overview["memory_stats"]`，记忆与向量可能被错误显示为 0。
10. Brain Status 的 `recent_tasks=[]`、`processing_status="idle"` 目前是硬编码占位。
11. Tauri 缺少独立 Memory Inspector、Vector Center、知识中心、来源会话、AI 权限与 MCP、机会中心和全局服务状态栏。
12. 当前 UI smoke 主要检查文件和字符串存在，不是功能交互验收。

## 1.3 必须从 `second_brain/` 迁移的能力

| 能力 | 迁移来源 | 目标归属 | 迁移方式 |
|---|---|---|---|
| Qdrant embedded/remote/memory 模式 | `second_brain/vector_store.py` | `src/retrieval/` Provider | 适配和重构，不复制旧检索算法 |
| Ollama embedding 主备模型调用 | `second_brain/embedding.py` | `src/model_center/` | 统一 Provider、状态和 Runtime Settings |
| collection dimension 检查 | `second_brain/vector_store.py` | Qdrant Provider | 扩展为 degraded/rebuild_required 合同 |
| 增量 point upsert/delete 与 rebuild | `second_brain/memory/service.py`、`vector_store.py` | Memory Index Coordinator | 以稳定 chunk 为单位同步 |
| source/conversation/message 查询 | `second_brain/db.py`、`connectors/chat.py` | 可重建 Source Read Model | 只保留索引与审计价值 |
| 版本、关系、冲突查询模式 | `second_brain/db.py`、`conflict/` | 统一 Revision/Relation/Conflict Read Model | 基于 Vault、Git、events 派生 |
| production/acceptance 隔离思想 | `second_brain/runtime_registry.py` | `src` Workspace Runtime | 扩展为全资源物理隔离 |
| 验收场景 | `second_brain/acceptance.py` | 统一 capability contract | 重写为目录无关契约测试 |
| PySide6 有效流程 | `second_brain/desktop/` | Tauri 页面 | 能力迁移，不复制视觉代码 |

## 1.4 不应迁移、应逐步退役的能力

- `second_brain` 的 `LIKE + max(exact, vector)` 排名算法
- `second_brain.sqlite3.memories` 作为永久记忆正文事实源
- `BoundedWatcher` 作为正式采集链
- 独立 Second Brain FastAPI 作为正式桌面后端
- PySide6 作为正式产品 UI
- SQLite pending/approve 流程作为第二套记忆审核
- `vector-warning` 伪结果行
- Qdrant payload 中长期复制完整永久记忆正文
- 两套 embedding 默认值和环境变量
- 通过 HTTP header 但共享底层目录的“伪隔离”
- `second_brain` 自启动和持续写入，待退役门槛满足后关闭

---

# 2. 最终合并原则

1. `src/` 是唯一长期主线；`second_brain/` 是有退出条件的 compatibility runtime。
2. Obsidian Vault + Git 是永久记忆和正式知识正文的唯一权威。
3. `lingji_memory.db`、Qdrant、source/conversation/message 表均为可重建索引。
4. 所有 AI 只通过一个 `MemoryGateway` 读取记忆。
5. 所有检索只通过一个 `HybridRetriever` 排名流程。
6. Qdrant 只提供 semantic candidates 和诊断，不自行决定最终权限与排名。
7. 所有新采集只进入 `src/extraction/`。
8. 所有桌面功能只进入 Tauri，且只访问 `127.0.0.1:8766`。
9. Brain Status、Memory Inspector、Vector Center、MCP 必须读取同一个统计服务。
10. 兼容层必须有 feature flag、停止写入时间点、只读期和删除条件。
11. 不为“统一”进行无关目录搬迁或大规模重构。
12. 每个任务形成最小闭环：实现、测试、文档、回滚、提交。

---

# 3. 最终目标架构

```text
Input Sources
  -> src/extraction adapters
  -> SQLiteExtractionQueue / lease / retry / progress
  -> storage/raw immutable snapshot
  -> Vault source Markdown / derived assets / memory candidates
  -> owner review
  -> Obsidian Vault + Git canonical memory

Obsidian Vault + Git
  -> PEMISIndex
  -> MemoryIndexCoordinator
       -> lingji_memory.db
            FTS5 / BM25 / metadata / citations / revision
       -> QdrantSemanticProvider
            semantic chunks / coverage / health
  -> HybridRetriever
       one candidate pipeline
       FTS5 + substring + Qdrant + RRF + boosts
       privacy + Agent Scope + project + tag + time
  -> ContextPackBuilder
  -> MemoryGateway
       -> MCP stdio / optional HTTP :8767
       -> MemoryInspectorFacade
       -> MemoryStatisticsService
       -> internal jobs

LocalControlService
  -> authenticated Local Control API :8766
  -> Tauri / React primary desktop

Compatibility boundary
  second_brain API/DB/PySide6
  -> export + read-only parity adapters only
  -> no new primary feature
  -> retired after Phase 5 gate
```

## 3.1 唯一数据权威模型

```text
Obsidian Vault + Git
= permanent memory and formal knowledge body

storage/raw
= original imported material

lingji_state.db
= jobs, queue, scheduler, progress, processing state, audit events

lingji_memory.db
= rebuildable lexical, metadata, source, conversation, relation and diagnostic read models

Qdrant
= rebuildable semantic index
```

---

# 4. 跨阶段公共合同

## 4.1 WorkspaceContext

建议新增只读配置对象：

```text
WorkspaceContext
  name: production | acceptance
  vault_path
  raw_path
  storage_path
  state_db_path
  memory_db_path
  qdrant_mode
  qdrant_path_or_url
  qdrant_collection
  logs_path
  runtime_settings_path
  cache_path
  generated_assets_path
  backup_path
```

所有 Service、Provider 和 API 从同一个 WorkspaceContext 解析路径，不允许各模块自行拼接。

## 4.2 EmbeddingProvider

建议在 `src/model_center/embedding.py` 定义：

```python
class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]: ...
    def embed_many(self, texts: list[str]) -> list[list[float]]: ...
    def status(self) -> EmbeddingStatus: ...
    def reset_failures(self) -> None: ...
```

`EmbeddingStatus` 至少包含：configured primary、fallback、active model、dimension、endpoint、available、last_error、last_success_at、last_failure_at、fallback_active、confirmed compute device。

禁止沿用“某模型失败一次后进程生命周期永久不可用”的行为。应使用有限重试、冷却时间和显式刷新。

## 4.3 Semantic Provider 分层

保留 `HybridRetriever` 所需的最小搜索接口，同时增加独立索引和诊断接口：

```text
SemanticSearchProvider
  search(query, limit, filters) -> semantic candidates

SemanticIndexProvider
  upsert_chunks(chunks)
  delete_chunks(chunk_ids)
  rebuild(chunks, task_context)

SemanticDiagnosticsProvider
  status()
  counts_by_kind()
  point_exists(chunk_id)
  coverage(expected_chunk_ids)
```

`QdrantSemanticProvider` 实现以上接口。UI、API 和 MemoryGateway 不直接使用原始 QdrantClient。

## 4.4 稳定 point ID

当前 `chunk_id` 为稳定 `LJ-CHUNK-<hash>`，同一记忆、标题、顺序和正文不变时稳定；正文变化会生成新 chunk ID。

Qdrant point ID 建议使用：

```text
UUIDv5(namespace=LingJi, value=workspace + collection_schema + chunk_id)
```

payload 继续保存原始 `memory_id` 和 `chunk_id`。这样既满足 Qdrant ID 限制，又可重复重建。

## 4.5 Qdrant payload

最小 payload：

```text
schema_version
workspace
kind
memory_id
chunk_id
title
heading
relative_path
memory_type
memory_tier
status
review_status
privacy
project
tags
agent_scope
start_line
end_line
content_hash
memory_revision
embedding_provider
embedding_model
indexed_at
```

正常 UI 不展示 raw vector。大段正文不默认复制进 payload；返回结果根据 `memory_id/chunk_id` 回源 `MemoryDatabase`。

## 4.6 MemoryIndexCoordinator

建议新增 `src/retrieval/index_coordinator.py`，只负责协调：

```text
Vault/index entries
  -> lexical synchronizer
  -> changed/added/removed chunk delta
  -> semantic upsert/delete
  -> cache invalidation
  -> progress/events
```

`MemoryDatabase` 不直接依赖 Qdrant；`QdrantSemanticProvider` 不修改 Vault；`MemoryGateway` 不复制同步算法。

## 4.7 MemoryStatisticsService

建议新增 `src/gateway/memory_statistics.py`，统一提供：

- canonical memory counts
- lifecycle/tier/privacy distributions
- memory revision
- lexical documents/chunks/integrity
- Qdrant readiness/dimension/counts/coverage
- embedding state
- source/conversation/message counts
- queue/sync/rebuild/query timestamps
- workspace and degraded warnings

Brain Status、Inspector、Vector Center 和 MCP `memory_health` 均调用此服务。

## 4.8 Memory Capability Contract

建立目录无关测试合同，至少验证：

- stable memory_id
- stable chunk_id
- lexical 和 semantic 均返回 citation
- Qdrant 关闭后 lexical 正常
- restricted 不泄露
- active/core 与 point 一致
- superseded 不进入当前 Context Pack
- source/conversation/message 可重建
- production/acceptance 完全隔离
- Brain Status、Inspector、MCP 统计一致
- Tauri 只访问 8766
- 同一输入不重复导入
- 关闭 compatibility runtime 后正式功能仍工作

---

# 5. 阶段总览与依赖图

```text
P0-01 Freeze rules
   ├── P0-02 Port/process contract
   ├── P0-03 Workspace + capability contracts
   │
   └──────────────┬──────────────────────┐
                  ▼                      ▼
          P1 Semantic stack       contract fixtures
                  │
                  ▼
          P2 Source read model
                  │
                  ▼
      P3 Statistics + Trace + Inspector + Vector UI
                  │
                  ▼
      P4 Revision/Relation/Conflict + full workspace + UI parity
                  │
                  ▼
      P5 Dual read -> stop startup -> stop writes -> read-only -> retire
```

阶段退出原则：后一阶段不得通过直接读取 legacy DB 绕过前一阶段未完成的统一能力。

---

# 6. Phase 0：冻结重复开发与端口、工作空间合同

## Phase 0 目标

- 新记忆、新采集和新正式 UI 的归属形成可执行规则。
- `second_brain` 明确进入 compatibility 状态。
- 解决 8765 冲突的代码任务被独立拆分。
- 建立 WorkspaceContext 和 Memory Capability Contract 骨架。

## P0-01 冻结规则与兼容边界

1. **任务名称**：冻结重复记忆开发。  
2. **目标**：让仓库规则、状态和入口都明确 `src` 主线、Tauri 唯一 UI。  
3. **前置条件**：统一架构审计已完成。  
4. **明确范围**：文档、贡献规则、compatibility 标签和开发检查清单。  
5. **禁止范围**：不修改运行逻辑，不删除 legacy。  
6. **真实修改文件**：`AGENTS.md`、`docs/PROJECT_STATUS.md`、`docs/MODULES/CODE_MAP.md`，按需更新。  
7. **新增接口或方法**：无。  
8. **数据流**：无。  
9. **API 变化**：无。  
10. **UI 变化**：无。  
11. **配置变化**：无。  
12. **数据迁移**：无。  
13. **测试文件**：文档链接与路径检查脚本。  
14. **测试命令**：`git diff --check`；文档链接检查。  
15. **验收标准**：任何新任务都能唯一判断应修改 `src`、Tauri 或 compatibility 层。  
16. **回滚方法**：回退文档提交。  
17. **文档更新**：本路线图、Project Status、Code Map。  
18. **推荐提交信息**：`docs(memory): freeze duplicate memory development`。  
19. **独立子智能体**：适合文档子智能体。  
20. **新对话或 Worktree**：独立文档任务可新对话；不需要 Worktree。

## P0-02 端口与进程合同落地

1. **任务名称**：统一 8766/8767/stdio 端口与传输。  
2. **目标**：消除 MCP HTTP 与 compatibility API 的 8765 冲突。  
3. **前置条件**：P0-01。  
4. **明确范围**：`src` MCP 默认端口改为 8767；Tauri 固定经 8766；legacy 8765 明确只兼容。  
5. **禁止范围**：不重构 MCP 工具，不删除 legacy API。  
6. **真实修改文件**：`src/config.py`、`src/control/runtime_settings.py`、`src/mcp_server.py`、`run_mcp_server.py`、相关启动脚本和测试。  
7. **新增接口或方法**：`McpRuntimeConfig` 或等价只读配置解析。  
8. **数据流**：Runtime Settings -> MCP startup；Tauri -> Local Control 8766。  
9. **API 变化**：增加只读 MCP status；无桌面直连 8767。  
10. **UI 变化**：设置页显示 MCP transport/port/restart_required。  
11. **配置变化**：`mcp_port=8767`；保留环境变量覆盖。  
12. **数据迁移**：无。  
13. **测试文件**：`tests/test_mcp_server.py`、`tests/test_control_api.py`、Tauri API base 测试。  
14. **测试命令**：`python -m pytest tests/test_mcp_server.py tests/test_control_api.py -v`。  
15. **验收标准**：8765 legacy、8766 control、8767 MCP HTTP 可同时绑定；stdio 正常。  
16. **回滚方法**：恢复旧端口配置；不更改数据。  
17. **文档更新**：Architecture、Project Status、MCP 测试报告。  
18. **推荐提交信息**：`fix(runtime): separate mcp and compatibility ports`。  
19. **独立子智能体**：适合后端配置子智能体。  
20. **新对话或 Worktree**：建议独立 Worktree，避免与 Qdrant 任务冲突 `src/config.py`。

## P0-03 WorkspaceContext 与 Capability Contract 骨架

1. **任务名称**：定义统一工作空间和记忆能力合同。  
2. **目标**：后续 Provider、API、测试使用同一 workspace 解析。  
3. **前置条件**：P0-01。  
4. **明确范围**：只定义数据类、解析器和合同测试骨架。  
5. **禁止范围**：不迁移真实数据，不重写现有服务。  
6. **真实修改文件**：建议 `src/runtime/workspace.py`、`src/config.py`、`tests/test_workspace_contract.py`、`tests/test_memory_capability_contract.py`。  
7. **新增接口或方法**：`WorkspaceContext`、`WorkspaceResolver`、contract fixture factory。  
8. **数据流**：Settings + Runtime Settings -> WorkspaceContext -> Services。  
9. **API 变化**：规划 `GET /api/workspaces`，本任务可只做服务合同。  
10. **UI 变化**：无，后续全局 Workspace selector 使用。  
11. **配置变化**：定义 production/acceptance 路径字段，不立即迁移用户数据。  
12. **数据迁移**：无。  
13. **测试文件**：上述两个新测试文件。  
14. **测试命令**：`python -m pytest tests/test_workspace_contract.py tests/test_memory_capability_contract.py -v`。  
15. **验收标准**：临时目录中所有 mutable path 均隔离，合同用例先以 lexical-only 通过。  
16. **回滚方法**：移除未接线的合同层。  
17. **文档更新**：Code Map、workspace 设计报告。  
18. **推荐提交信息**：`feat(runtime): define workspace and memory capability contracts`。  
19. **独立子智能体**：适合独立后端子智能体。  
20. **新对话或 Worktree**：需要独立 Worktree；完成后再合并 Phase 1。

## Phase 0 退出条件

- 开发规则明确且不再新增 legacy 正式功能。
- 端口代码和测试完成，不再只是文档目标。
- WorkspaceContext 能物理解析全部资源。
- capability contract 在 lexical-only 模式有可执行骨架。

---

# 7. Phase 1：统一 Qdrant SemanticProvider 与 Embedding Provider

## Phase 1 设计决定

- 不搬运旧 RetrievalService。
- `HybridRetriever` 保持唯一排名入口。
- Qdrant Provider 只提供 semantic candidates、索引和诊断。
- 语义故障返回结构化 warning，不成为伪搜索结果。
- 切换 embedding 模型或维度时不静默清空当前 collection。
- 重建写入新 collection，验证后切换配置；旧 collection 保留到回滚窗口结束。

## P1-01 统一 EmbeddingProvider

1. **任务名称**：实现统一 Ollama Embedding Provider。  
2. **目标**：把主备模型、错误、维度和实际激活模型纳入 Model Center。  
3. **前置条件**：P0-03。  
4. **明确范围**：Provider 合同、Ollama adapter、状态和批量接口。  
5. **禁止范围**：不接 Qdrant，不改 RRF，不开发 UI 页面。  
6. **真实修改文件**：建议 `src/model_center/embedding.py`、`src/model_center/__init__.py`、`src/model_center/inventory.py`、`src/control/runtime_settings.py`、`tests/test_embedding_provider.py`。  
7. **新增接口或方法**：`EmbeddingProvider`、`OllamaEmbeddingProvider`、`EmbeddingStatus`、`embed_many()`、`reset_failures()`。  
8. **数据流**：Runtime Settings -> Model Center -> EmbeddingProvider -> vector list/status event。  
9. **API 变化**：后续由模型状态 API 返回 embedding state；本任务不扩路由也可验收。  
10. **UI 变化**：无正式页面；现有 Models 页后续读取状态。  
11. **配置变化**：provider、primary、fallback、endpoint、timeout、batch size、enabled。  
12. **数据迁移**：无。  
13. **测试文件**：`tests/test_embedding_provider.py`。  
14. **测试命令**：`python -m pytest tests/test_embedding_provider.py -v`；本地 Ollama integration profile。  
15. **验收标准**：主模型成功、主失败切备用、全部失败、刷新恢复、维度记录均可验证。  
16. **回滚方法**：保留原 `src` Embedder 配置，Provider 未接线前删除注入即可。  
17. **文档更新**：Embedding Provider 实施与测试报告。  
18. **推荐提交信息**：`feat(model-center): add unified embedding provider`。  
19. **独立子智能体**：适合模型 Provider 子智能体。  
20. **新对话或 Worktree**：需要独立 Worktree。

## P1-02 QdrantSemanticProvider 搜索与诊断

1. **任务名称**：适配 Qdrant 为 `src` SemanticProvider。  
2. **目标**：在不改变 RRF 的前提下提供 semantic candidates。  
3. **前置条件**：P1-01、P0-03。  
4. **明确范围**：embedded/remote/:memory:、collection、search、status、count、exists、coverage。  
5. **禁止范围**：不复制 legacy SQL/排名；不暴露 raw vector。  
6. **真实修改文件**：建议 `src/retrieval/semantic.py`、`src/retrieval/qdrant_provider.py`、`src/retrieval/__init__.py`、`tests/test_qdrant_semantic_provider.py`。  
7. **新增接口或方法**：`SemanticSearchProvider`、`SemanticIndexProvider`、`SemanticDiagnosticsProvider`、`QdrantSemanticProvider`。  
8. **数据流**：query -> EmbeddingProvider -> Qdrant -> semantic IDs/similarity -> HybridRetriever canonical resolve/filter。  
9. **API 变化**：无直接 Qdrant API；为后续 vector status 提供 service contract。  
10. **UI 变化**：无。  
11. **配置变化**：mode、path/url、collection prefix、enabled、timeout。  
12. **数据迁移**：无；测试使用 `:memory:`。  
13. **测试文件**：`tests/test_qdrant_semantic_provider.py`。  
14. **测试命令**：`python -m pytest tests/test_qdrant_semantic_provider.py -v`。  
15. **验收标准**：真实 in-memory Qdrant 完成 upsert/search/delete/count/exists；restricted payload 不越权。  
16. **回滚方法**：Provider feature flag 关闭后回到 lexical-only。  
17. **文档更新**：Vector Database、Provider 测试报告。  
18. **推荐提交信息**：`feat(retrieval): add qdrant semantic provider`。  
19. **独立子智能体**：适合检索 Provider 子智能体。  
20. **新对话或 Worktree**：需要独立 Worktree，避免与 UI 混合。

## P1-03 统一增量索引与重建协调器

1. **任务名称**：实现 MemoryIndexCoordinator。  
2. **目标**：同一次 Vault 同步产生 lexical 和 semantic 一致 delta。  
3. **前置条件**：P1-02。  
4. **明确范围**：added/updated/removed chunks、upsert/delete、rebuild、cache、events、progress。  
5. **禁止范围**：不让 MemoryDatabase 直接依赖 Qdrant；不自动删除旧 collection。  
6. **真实修改文件**：`src/retrieval/incremental_sync.py`、建议 `src/retrieval/index_coordinator.py`、`src/gateway/memory_gateway.py`、`src/gateway/bootstrap.py`、测试。  
7. **新增接口或方法**：`IndexDelta`、`MemoryIndexCoordinator.sync()`、`rebuild()`、`coverage()`。  
8. **数据流**：PEMISIndex -> chunk delta -> SQLite transaction -> Qdrant operations -> revision/cache/event。  
9. **API 变化**：后续任务 API 返回 task_id；本任务先服务层。  
10. **UI 变化**：无。  
11. **配置变化**：semantic enabled、batch size、rebuild target collection。  
12. **数据迁移**：首次显式 rebuild，不能启动时静默大规模运行。  
13. **测试文件**：`tests/test_incremental_index_sync.py`、`tests/test_memory_index_coordinator.py`。  
14. **测试命令**：`python -m pytest tests/test_incremental_index_sync.py tests/test_memory_index_coordinator.py -v`。  
15. **验收标准**：新增、修改、删除和无变化四种场景的 SQLite/Qdrant point 一致。  
16. **回滚方法**：关闭 semantic flag；保留 lexical DB 和旧 collection。  
17. **文档更新**：索引数据流与测试报告。  
18. **推荐提交信息**：`feat(retrieval): coordinate lexical and semantic indexing`。  
19. **独立子智能体**：适合，但需要与 P1-02 接口先冻结。  
20. **新对话或 Worktree**：需要新 Worktree。

## P1-04 Model Center、Runtime Settings 与 Workspace 接线

1. **任务名称**：把 Embedding/Qdrant 接入正式运行时。  
2. **目标**：`build_memory_gateway()` 不再固定 `semantic_provider=None`。  
3. **前置条件**：P1-01 至 P1-03。  
4. **明确范围**：配置解析、Provider 注入、production/acceptance collection、健康状态。  
5. **禁止范围**：不开发完整 Inspector，不改旧数据库。  
6. **真实修改文件**：`src/config.py`、`src/control/runtime_settings.py`、`src/model_center/inventory.py`、`src/gateway/bootstrap.py`、Workspace runtime、测试。  
7. **新增接口或方法**：`embedding_settings()`、`vector_settings()`、workspace-aware provider factory。  
8. **数据流**：Workspace + Runtime Settings -> provider factory -> MemoryGateway/IndexCoordinator。  
9. **API 变化**：设置定义可读取，状态服务可读取；无写向量 API。  
10. **UI 变化**：设置页自动显示新分组，保存时提示 restart/rebuild_required。  
11. **配置变化**：补齐所有 vector/embedding/workspace 字段；移除开发者绝对 backup 默认路径。  
12. **数据迁移**：旧环境变量映射到 compatibility fallback，设置文件不自动覆盖。  
13. **测试文件**：`tests/test_runtime_settings.py`、`tests/test_workspace_isolation.py`、gateway bootstrap 测试。  
14. **测试命令**：`python -m pytest tests/test_runtime_settings.py tests/test_workspace_isolation.py tests/test_permanent_memory_gateway.py -v`。  
15. **验收标准**：production/acceptance 使用不同路径和 collection；Provider 可启停；模型缺失时 lexical 可用。  
16. **回滚方法**：设置 `semantic_enabled=false`，恢复上一 collection 配置。  
17. **文档更新**：配置表、Code Map、迁移说明。  
18. **推荐提交信息**：`feat(runtime): wire semantic provider into memory gateway`。  
19. **独立子智能体**：不建议与 P1-03 并行修改 bootstrap。  
20. **新对话或 Worktree**：在 Phase 1 集成 Worktree 完成。

## P1-05 Vector 状态 API、契约测试与报告

1. **任务名称**：交付 Phase 1 可观察闭环。  
2. **目标**：后端真实报告向量、模型、降级和 coverage。  
3. **前置条件**：P1-04。  
4. **明确范围**：只读状态、测试、文档。  
5. **禁止范围**：不做完整 Vector Center UI，不提供无确认 rebuild 按钮。  
6. **真实修改文件**：`src/control/service.py`、`src/control/api.py`、`src/control/contracts.py`（建议）、相关测试。  
7. **新增接口或方法**：`vector_status()`、`vector_coverage()`、统一 warning/error code。  
8. **数据流**：Provider diagnostics -> shared status contract -> Local Control API。  
9. **API 变化**：建议 `GET /api/vector/status`、`GET /api/vector/coverage`。  
10. **UI 变化**：Brain Status 临时显示真实 semantic 状态，不伪造 0。  
11. **配置变化**：无新增。  
12. **数据迁移**：无。  
13. **测试文件**：`tests/test_memory_capability_contract.py`、`tests/test_control_api_extended.py`、`tests/test_brain_status_e2e.py`。  
14. **测试命令**：targeted tests；`python -m pytest tests/ -v`；UI smoke。  
15. **验收标准**：Qdrant unavailable、dimension mismatch、empty collection 和 healthy 均有不同真实状态。  
16. **回滚方法**：回退只读 API；Provider 数据不受影响。  
17. **文档更新**：`docs/TEST_REPORTS/UNIFIED_QDRANT_SEMANTIC_PROVIDER_REPORT.md`、Project Status、Changelog、Code Map。  
18. **推荐提交信息**：`test(retrieval): verify unified semantic capability contract`。  
19. **独立子智能体**：适合测试子智能体，须基于稳定接口。  
20. **新对话或 Worktree**：测试可独立 Worktree，最终由 Phase 1 集成者合并。

## Phase 1 退出条件

- `semantic_provider` 在启用配置下真实注入。
- lexical + semantic 进入同一 RRF。
- Qdrant 不可用时明确 degraded 且 lexical 正常。
- point ID、payload、dimension、coverage、collection 和 workspace 契约通过测试。
- production/acceptance 不共享可写资源。
- 有完整 Markdown 测试报告。

---

# 8. Phase 2：统一结构化来源查询模型

## Phase 2 schema 原则

建议在可重建 `lingji_memory.db` 中增加派生表，而不是新建权威数据库：

```text
source_records
conversation_records
message_records
attachment_records
source_index_meta
```

表中保存 metadata、稳定 ID、hash、privacy、路径、行号或 raw JSON pointer。完整正文默认从 Vault/raw 按需读取；如为检索性能保存 message text，也必须标记为 derived、可重建并受隐私过滤。

稳定 ID：

- source_id：source type + external source ID 或 raw content hash
- conversation_id：source_id + external conversation ID；缺失时使用规范化 conversation hash
- message_id：conversation_id + external message ID；缺失时使用 ordinal + role + content hash
- attachment_id：message_id + normalized attachment reference hash

## P2-01 Source Read Model schema 与重建器

1. **任务名称**：建立可重建 source/conversation/message 索引。  
2. **目标**：保留 legacy 结构化查询价值，不形成第二事实源。  
3. **前置条件**：P0-03；Phase 1 可并行结束后开始。  
4. **明确范围**：派生 schema、stable IDs、raw/Vault parser、全量 rebuild。  
5. **禁止范围**：不把消息自动晋升为记忆；不读取 legacy DB 作为长期源。  
6. **真实修改文件**：`src/retrieval/memory_db.py` 或独立 `src/sources/read_model.py`、ChatGPT Adapter 辅助解析、测试。  
7. **新增接口或方法**：`SourceReadModel`、`SourceReadModelRebuilder`、ID factory。  
8. **数据流**：storage/raw/Vault source docs -> normalized records -> rebuildable tables。  
9. **API 变化**：无，先服务层。  
10. **UI 变化**：无。  
11. **配置变化**：正文缓存开关、最大展开大小。  
12. **数据迁移**：首次从权威 raw/Vault rebuild；不直接复制 `second_brain.sqlite3`。  
13. **测试文件**：`tests/test_source_read_model.py`。  
14. **测试命令**：`python -m pytest tests/test_source_read_model.py -v`。  
15. **验收标准**：同一输入重建 ID 和数量稳定；删除来源后派生行删除；附件引用可追溯。  
16. **回滚方法**：删除派生表/独立索引并重建；raw/Vault 不变。  
17. **文档更新**：Source Read Model schema 与测试报告。  
18. **推荐提交信息**：`feat(sources): add rebuildable conversation read model`。  
19. **独立子智能体**：适合数据模型子智能体。  
20. **新对话或 Worktree**：需要独立 Worktree。

## P2-02 隐私查询服务与正文按需展开

1. **任务名称**：实现权限感知的来源查询服务。  
2. **目标**：默认返回 metadata，显式请求才展开私密正文。  
3. **前置条件**：P2-01。  
4. **明确范围**：list/detail/conversation/messages/attachments、pagination、privacy/Agent Scope。  
5. **禁止范围**：不绕过 AIProfileRegistry；不在日志输出全文。  
6. **真实修改文件**：建议 `src/sources/service.py`、`src/gateway/memory_gateway.py` 或专用 facade、测试。  
7. **新增接口或方法**：`SourceQueryService.list_sources()`、`get_conversation()`、`list_messages()`、`expand_message()`。  
8. **数据流**：Agent profile -> query filters -> derived records -> canonical body resolver。  
9. **API 变化**：后续 `/api/sources`、`/api/conversations/{id}`、`/api/messages/{id}`。  
10. **UI 变化**：无，下一任务接入。  
11. **配置变化**：展开上限、附件路径显示策略。  
12. **数据迁移**：无。  
13. **测试文件**：`tests/test_source_query_service.py`、隐私契约测试。  
14. **测试命令**：`python -m pytest tests/test_source_query_service.py tests/test_memory_capability_contract.py -v`。  
15. **验收标准**：restricted 对远程 profile 不可见；正文按需读取；分页稳定。  
16. **回滚方法**：停止暴露查询服务，派生索引可保留。  
17. **文档更新**：隐私和正文展开设计。  
18. **推荐提交信息**：`feat(sources): add permission-aware source queries`。  
19. **独立子智能体**：适合 API 前的数据服务子智能体。  
20. **新对话或 Worktree**：可在 P2 Worktree 继续。

## P2-03 Source API、Tauri 基础页与测试

1. **任务名称**：把来源审计接入 8766。  
2. **目标**：Tauri 能查看来源、会话、消息 metadata 和显式正文。  
3. **前置条件**：P2-02。  
4. **明确范围**：只读 API、Sources 页面、分页、错误与空状态。  
5. **禁止范围**：不接 legacy 8765；不做记忆批准。  
6. **真实修改文件**：`src/control/service.py`、`src/control/api.py`、`desktop/lingji-control/src/api.ts`、`types.ts`、`navigation.ts`、新页面和测试。  
7. **新增接口或方法**：API response contracts、Source page hooks。  
8. **数据流**：Tauri -> 8766 -> SourceQueryService -> derived index/canonical raw。  
9. **API 变化**：`GET /api/sources`、`GET /api/sources/{id}`、`GET /api/conversations/{id}`、`GET /api/messages/{id}`。  
10. **UI 变化**：新增“来源与主动投喂”，合并现有 Capture/Media 入口。  
11. **配置变化**：无。  
12. **数据迁移**：无。  
13. **测试文件**：`tests/test_source_control_api.py`、Tauri smoke/Playwright。  
14. **测试命令**：API tests；UI build；`node scripts/ui-modular-smoke.mjs`；Playwright。  
15. **验收标准**：真实权限、loading/error/empty/pagination/large conversation 均通过。  
16. **回滚方法**：隐藏新导航并回退 API，不影响 raw。  
17. **文档更新**：Phase 2 测试报告、UI plan、Code Map。  
18. **推荐提交信息**：`feat(ui): add unified source and conversation views`。  
19. **独立子智能体**：后端 API 与 Tauri 可分别子智能体。  
20. **新对话或 Worktree**：分 API/UI Worktree，合同先冻结。

## Phase 2 退出条件

- source/conversation/message 可从 raw 或 Vault 完整重建。
- 不依赖 legacy DB 才能查询。
- 权限、附件和正文展开有契约测试。
- 同一输入不会生成重复记录。

---

# 9. Phase 3：统一 Memory Inspector、Vector Center 与统计来源

## P3-01 MemoryStatisticsService 与真实 Brain Status

1. **任务名称**：统一记忆、向量、模型和任务统计。  
2. **目标**：消除 Brain Status 虚假 0、硬编码 idle 和空任务。  
3. **前置条件**：Phase 1，Source 统计可在 Phase 2 后补入。  
4. **明确范围**：shared statistics、health enums、timestamps、warnings。  
5. **禁止范围**：UI 不自行计算；不解析日志充当任务状态。  
6. **真实修改文件**：建议 `src/gateway/memory_statistics.py`、`src/control/service.py`、`src/gateway/memory_gateway.py`、`src/mcp_server.py`、测试。  
7. **新增接口或方法**：`MemoryStatisticsService.snapshot(workspace)`、`ServiceState`。  
8. **数据流**：Memory DB/Qdrant/Embedding/State DB -> statistics snapshot -> MCP/API/UI。  
9. **API 变化**：`GET /api/memory/status`；修正 `/api/brain/status`。  
10. **UI 变化**：Brain Status 先改为真实状态，最终并入 Overview。  
11. **配置变化**：健康检查超时和缓存时间。  
12. **数据迁移**：无。  
13. **测试文件**：`tests/test_memory_statistics.py`、`tests/test_brain_status_e2e.py`。  
14. **测试命令**：`python -m pytest tests/test_memory_statistics.py tests/test_brain_status_e2e.py -v`。  
15. **验收标准**：Brain Status、MCP health 和 Inspector fixture 的 counts/status 完全一致。  
16. **回滚方法**：恢复旧聚合，但保留新服务未接线；无数据变化。  
17. **文档更新**：状态合同和测试报告。  
18. **推荐提交信息**：`fix(status): use unified memory statistics`。  
19. **独立子智能体**：适合后端状态子智能体。  
20. **新对话或 Worktree**：独立 Worktree。

## P3-02 单一检索流程与 Trace

1. **任务名称**：为 HybridRetriever 增加共享 trace。  
2. **目标**：普通搜索和解释搜索使用同一候选、过滤、RRF 和排序。  
3. **前置条件**：Phase 1。  
4. **明确范围**：内部 retrieval execution、channel ranks、boosts、warnings、rejection reasons。  
5. **禁止范围**：不写第二套 scoring；不伪造历史 trace。  
6. **真实修改文件**：`src/retrieval/hybrid.py`、`src/retrieval/enhanced.py`、建议 `src/retrieval/trace.py`、测试。  
7. **新增接口或方法**：`RetrievalExecution`、`RetrievalTrace`、`search_with_trace()`。  
8. **数据流**：one execution -> results；optional trace serialization。  
9. **API 变化**：后续 Inspector search route 使用。  
10. **UI 变化**：无。  
11. **配置变化**：trace 默认关闭，避免普通 MCP 响应膨胀。  
12. **数据迁移**：无。  
13. **测试文件**：`tests/test_retrieval_trace.py`、`tests/test_memory_retrieval.py`。  
14. **测试命令**：`python -m pytest tests/test_retrieval_trace.py tests/test_memory_retrieval.py -v`。  
15. **验收标准**：普通/trace ordered IDs 完全相同；warnings 不混入 results。  
16. **回滚方法**：保留原 `search()`，撤销 trace facade。  
17. **文档更新**：Trace 合同与测试报告。  
18. **推荐提交信息**：`feat(retrieval): expose trace from shared ranking pipeline`。  
19. **独立子智能体**：适合检索专家子智能体。  
20. **新对话或 Worktree**：需要独立 Worktree，不与 UI 同时改。

## P3-03 MemoryInspectorFacade 与 Local Control API

1. **任务名称**：实现只读 Memory Inspector 后端。  
2. **目标**：统一 canonical memory、citation、vector、source、trace、relation placeholders。  
3. **前置条件**：P3-01、P3-02；Phase 2 可提供 source enrich。  
4. **明确范围**：list/detail/status/vector/source/search trace，全部只读。  
5. **禁止范围**：不批准、拒绝、编辑、删除、supersede、rebuild。  
6. **真实修改文件**：建议 `src/gateway/memory_inspector.py`、`src/control/service.py`、`src/control/api.py`、`src/control/contracts.py`、测试。  
7. **新增接口或方法**：`MemoryInspectorFacade`、paged read models、Inspector error codes。  
8. **数据流**：8766 -> facade -> MemoryGateway/MemoryDB/Statistics/Qdrant/SourceReadModel。  
9. **API 变化**：`/api/memory/inspector/status|list|{id}|{id}/source|{id}/vector|search`。  
10. **UI 变化**：无，本任务交付合同。  
11. **配置变化**：page size、trace limit。  
12. **数据迁移**：无。  
13. **测试文件**：`tests/test_memory_inspector.py`、`tests/test_memory_control_api.py`。  
14. **测试命令**：`python -m pytest tests/test_memory_inspector.py tests/test_memory_control_api.py -v`。  
15. **验收标准**：missing 404、权限 403、warnings 独立、workspace 明确、所有 route 只读。  
16. **回滚方法**：移除路由/facade，不修改数据。  
17. **文档更新**：Memory Inspector plan、API contract、测试报告。  
18. **推荐提交信息**：`feat(memory): add read-only inspector facade`。  
19. **独立子智能体**：适合 API 子智能体。  
20. **新对话或 Worktree**：独立 API Worktree。

## P3-04 Tauri Memory Inspector、Vector Center 与全局状态栏

1. **任务名称**：实现统一可视化页面。  
2. **目标**：用户能看到记忆为何命中、向量是否存在、模型和错误状态。  
3. **前置条件**：P3-03 和 Phase 1 vector APIs。  
4. **明确范围**：导航、类型、API client、Inspector、Vector Center、全局状态栏。  
5. **禁止范围**：不复制后端过滤/统计；不增加写按钮。  
6. **真实修改文件**：`navigation.ts`、`types.ts`、`api.ts`、`App.tsx`、新 pages/components/hooks、CSS、UI tests。  
7. **新增接口或方法**：typed DTOs、status badge、trace table、coverage views。  
8. **数据流**：Tauri -> 8766 typed read API -> render。  
9. **API 变化**：只消费已冻结合同。  
10. **UI 变化**：新增 Memory Inspector、Vector Center；Brain Status 内容拆分；全局状态栏。  
11. **配置变化**：无。  
12. **数据迁移**：无。  
13. **测试文件**：扩展 `ui-modular-smoke.mjs`；新增 Playwright tests。  
14. **测试命令**：npm build/typecheck；smoke；Playwright。  
15. **验收标准**：healthy/busy/degraded/unavailable/disabled/configuration_required 六态均可验证；无万能绿灯。  
16. **回滚方法**：撤销新导航和页面，后端保持可用。  
17. **文档更新**：UI plan、截图/交互验收报告。  
18. **推荐提交信息**：`feat(ui): add memory inspector and vector center`。  
19. **独立子智能体**：适合 Tauri UI 子智能体。  
20. **新对话或 Worktree**：需要独立 UI Worktree。

## P3-05 Phase 3 契约、API 与 UI 回归

1. **任务名称**：验证统一统计、Inspector 和 UI。  
2. **目标**：证明不是“页面存在”，而是数据和行为正确。  
3. **前置条件**：P3-04。  
4. **明确范围**：backend contracts、API、Playwright、large/empty/error/degraded。  
5. **禁止范围**：不以 skip 代替缺失前端构建；不全用 mock。  
6. **真实修改文件**：相关测试、fixtures、测试报告。  
7. **新增接口或方法**：fixture server、real in-memory Qdrant test harness。  
8. **数据流**：fixture Vault -> indexes -> API -> Tauri assertions。  
9. **API 变化**：无。  
10. **UI 变化**：仅修复测试发现问题。  
11. **配置变化**：测试环境配置。  
12. **数据迁移**：无。  
13. **测试文件**：capability contract、brain status、Inspector API、Playwright。  
14. **测试命令**：targeted；全量 pytest；UI build/smoke/Playwright。  
15. **验收标准**：Brain Status/Inspector/MCP stats 相等；Tauri 网络请求只指向 8766。  
16. **回滚方法**：回退 Phase 3 UI/API，保留 Phase 1/2 核心能力。  
17. **文档更新**：`docs/TEST_REPORTS/MEMORY_INSPECTOR_VECTOR_CENTER_REPORT.md`。  
18. **推荐提交信息**：`test(ui): verify inspector and vector center contracts`。  
19. **独立子智能体**：适合 QA 子智能体。  
20. **新对话或 Worktree**：独立测试 Worktree。

## Phase 3 退出条件

- 用户可在 Tauri 看见真实记忆、citation、trace、向量和降级状态。
- Brain Status、Inspector、MCP 使用同一统计源。
- Tauri 只访问 8766。
- 不存在虚假 0、虚假 GPU 或万能绿色状态。

---

# 10. Phase 4：版本、关系、冲突、完整隔离与旧 UI 能力迁移

## P4-01 Revision/Relation/Conflict Read Models

1. **任务名称**：迁移版本、关系和冲突查询思想。  
2. **目标**：Inspector 能查询历史与冲突，但正文仍由 Vault/Git 权威。  
3. **前置条件**：Phase 2、P3-03。  
4. **明确范围**：Git/file/events revision、Frontmatter/link relation、deterministic conflict candidates。  
5. **禁止范围**：不复制 legacy memory body；不自动改 Core。  
6. **真实修改文件**：建议 `src/memory/revisions.py`、`relations.py`、`conflicts.py`、派生 schema、Inspector enrich、测试。  
7. **新增接口或方法**：`RevisionReadModel`、`RelationReadModel`、`ConflictCandidateService`。  
8. **数据流**：Vault/Git/events -> derived read models -> Inspector；owner action 后续单独任务。  
9. **API 变化**：Inspector detail 增加 revisions/relations/conflict candidates。  
10. **UI 变化**：Inspector tabs。  
11. **配置变化**：conflict rules/version、Git history limit。  
12. **数据迁移**：从 canonical data rebuild；legacy 只用于 parity。  
13. **测试文件**：`tests/test_memory_revision_read_model.py`、`test_memory_relations.py`、`test_memory_conflicts.py`。  
14. **测试命令**：对应 targeted pytest。  
15. **验收标准**：superseded 历史可见但不进入 current context；冲突只生成候选。  
16. **回滚方法**：删除派生模型并重建，不影响 Vault/Git。  
17. **文档更新**：关系/冲突设计和测试报告。  
18. **推荐提交信息**：`feat(memory): add revision relation and conflict read models`。  
19. **独立子智能体**：可拆三个子智能体，但 schema/DTO 先冻结。  
20. **新对话或 Worktree**：建议三个小 Worktree，集成者统一合并。

## P4-02 Production/Acceptance 全资源隔离

1. **任务名称**：完成统一工作空间运行时。  
2. **目标**：不仅 collection，所有 mutable resources 都物理隔离。  
3. **前置条件**：P0-03、Phase 1、Phase 2。  
4. **明确范围**：Vault fixture、raw、state DB、memory DB、Qdrant、logs、cache、runtime settings、tasks、backup、assets。  
5. **禁止范围**：不通过 header 复用同一物理数据库。  
6. **真实修改文件**：Workspace runtime、config、control service/api、test fixtures、Tauri selector。  
7. **新增接口或方法**：`WorkspaceRuntimeRegistry`、safe acceptance reset。  
8. **数据流**：selected workspace -> isolated service graph -> response meta.workspace。  
9. **API 变化**：每个统一 API 返回 workspace；安全切换和列举。  
10. **UI 变化**：全局 Workspace selector 和明显 production warning。  
11. **配置变化**：每 workspace 全资源路径。  
12. **数据迁移**：先建立新 acceptance fixture；production 不自动移动。  
13. **测试文件**：`tests/test_workspace_isolation.py`、acceptance E2E。  
14. **测试命令**：workspace tests + full suite。  
15. **验收标准**：acceptance reset 后 production 文件、DB、collection、logs、settings hash 不变。  
16. **回滚方法**：保留旧 production config；新 workspace registry feature flag。  
17. **文档更新**：Workspace layout、恢复说明。  
18. **推荐提交信息**：`feat(runtime): isolate production and acceptance resources`。  
19. **独立子智能体**：不宜与其他配置任务并行。  
20. **新对话或 Worktree**：独立高风险 Worktree。

## P4-03 旧 UI 能力迁移与导航收敛

1. **任务名称**：完成 Tauri 功能对等和旧 UI 决策。  
2. **目标**：有价值能力在 Tauri 可发现，PySide6 不再承担正式功能。  
3. **前置条件**：Phase 2/3、P4-01/02。  
4. **明确范围**：按下方矩阵逐项 migrate/merge/redesign/retire。  
5. **禁止范围**：不复制 PySide6 视觉和 legacy API；不在 Inspector v1 加破坏性写操作。  
6. **真实修改文件**：Tauri navigation/pages/components、Local Control APIs、PySide 文档冻结标记、tests。  
7. **新增接口或方法**：统一 task/progress、diagnostics、knowledge、AI/MCP read contracts。  
8. **数据流**：Tauri -> 8766 -> src services。  
9. **API 变化**：Knowledge、AI/MCP、diagnostics、opportunity、acceptance contracts。  
10. **UI 变化**：最终 14 个导航区域。  
11. **配置变化**：设置页补齐所有可支持项。  
12. **数据迁移**：无。  
13. **测试文件**：Playwright page matrix、API contract tests。  
14. **测试命令**：backend full tests + UI build/smoke/Playwright。  
15. **验收标准**：矩阵每行有目标页面和验收；关闭 PySide6 不损失正式能力。  
16. **回滚方法**：页面级 feature flag；PySide6 仍只读保留。  
17. **文档更新**：Unified Desktop UI Plan、迁移报告。  
18. **推荐提交信息**：`feat(ui): complete unified desktop capability migration`。  
19. **独立子智能体**：页面可分子智能体，统一设计系统和 DTO 由主任务控制。  
20. **新对话或 Worktree**：每个页面可 Worktree；导航/App 集成最后串行。

## UI 迁移矩阵

| 原页面或组件 | 当前路径 | 实际功能 | 后端依赖 | Tauri 目标页 | 决策 | 验收测试 |
|---|---|---|---|---|---|---|
| DashboardPage | `second_brain/desktop/pages.py` | API/Ollama/Qdrant/watcher/counts | legacy `/system/status` | 总览 + 全局状态栏 | redesign | 统一统计合同与六态渲染 |
| AcceptancePage | 同上 | reset/run/latest/export | legacy acceptance | 环境验收 | migrate | isolated fixture、报告导出、production unchanged |
| ImportPage | 同上 | 表单/JSON/立即蒸馏 | legacy `/memory/import` | 来源与主动投喂 | redesign | 只走 `src/extraction`、幂等、任务进度 |
| MemoryPage | 同上 | 列表、详情、批准/拒绝/supersede | legacy memory DB | 记忆检查器 | redesign | v1 只读；后续 owner action 单独设计 |
| SearchPage | 同上 | 搜索和 Codex context | legacy retrieval | 记忆检查器 + AI 权限与 MCP | merge | shared trace 与 Context Pack 契约 |
| ConflictPage | 同上 | 冲突列表和解决 | legacy conflicts | 记忆检查器冲突页签 | redesign | 候选只读；不自动写 Core |
| KnowledgePage | 同上 | 文档、详情、索引、扫描 | legacy knowledge/watcher | 知识与 Obsidian | redesign | 使用统一 index task，不走 legacy watcher |
| ActivityPage | 同上 | tasks/projects/timeline | legacy DB | 任务与进度中心 + 机会中心 | merge | 结构化 progress、timeline events |
| SystemPage | 同上 | watcher、scan、rebuild、logs、目录 | legacy process/API | 日志与诊断 + 向量中心 + 设置 | merge | 危险操作单独确认和 task_id |
| Workspace selector | `second_brain/desktop/main_window.py` | production/acceptance 切换警告 | workspace header | 全局 Workspace selector | redesign | 全资源物理隔离测试 |
| BrainStatusPage | `desktop/lingji-control/src/pages/BrainStatusPage.tsx` | 记忆/向量/模型/GPU/任务摘要 | `/api/brain/status` | 总览、向量中心、模型与算力 | retire | 新页面统计一致后移除 |
| CapturePage | Tauri | 网页/文字/文件投喂 | `/api/share` | 来源与主动投喂 | merge | Adapter/queue/idempotency |
| MediaPage | Tauri | 媒体分析 | `/api/media/analyze` | 来源与主动投喂 + 模型与算力 | merge | task progress、provider state |
| SystemComputePage + ModelsPage | Tauri | 硬件、GPU、模型 | hardware/model APIs | 模型与算力 | merge | backend-confirmed GPU/model state |
| JobsPage | Tauri | 采集任务列表 | `/api/jobs` | 任务与进度中心 | migrate | progress contract、pause/resume/retry/cancel capability flags |
| LogsPage | Tauri | 日志 | `/api/logs` | 日志与诊断 | migrate | structured errors、redaction、export |

## 最终 Tauri 导航

1. 总览
2. 记忆检查器
3. 知识与 Obsidian
4. 来源与主动投喂
5. 任务与进度中心
6. 向量中心
7. 模型与算力
8. AI 权限与 MCP
9. 机会中心
10. 存储
11. 备份与恢复
12. 设置
13. 日志与诊断
14. 环境验收

## 全局状态栏

```text
Workspace | API | Memory Index | Qdrant | Embedding | Watcher | Scheduler | Tasks | GPU | Storage
```

只允许：

- `healthy`
- `busy`
- `degraded`
- `unavailable`
- `disabled`
- `configuration_required`

每项必须包含 `status`、`reason`、`checked_at`。禁止一个绿点代表所有服务。

## 长任务进度合同

```text
task_id
stage
processed
total
success_count
failure_count
current_item
elapsed
percentage
retry_count
latest_message
can_pause
can_resume
can_retry
can_cancel
```

`total` 不可知时 `percentage=null`，禁止伪造百分比。

## Phase 4 退出条件

- 版本、关系、冲突可从 canonical data 重建。
- production/acceptance 全资源隔离。
- UI 迁移矩阵全部完成或明确 retire。
- PySide6 关闭不影响正式产品。

---

# 11. Phase 5：双读验证与 `second_brain` 退役

## P5-01 导出与双读对比工具

1. **任务名称**：建立 legacy export 和双读 parity harness。  
2. **目标**：用同一 fixture 和只读真实样本比较两套结果。  
3. **前置条件**：Phase 1-4 退出。  
4. **明确范围**：只读 export、normalized compare、差异解释、报告。  
5. **禁止范围**：不从 legacy 覆盖 canonical data；不删除旧库。  
6. **真实修改文件**：建议 `src/migration/second_brain_export.py`、`dual_read.py`、tests、CLI/script。  
7. **新增接口或方法**：`LegacyExportReader`、`DualReadComparator`、`ParityReport`。  
8. **数据流**：legacy read-only + unified read-only -> normalized report。  
9. **API 变化**：默认不暴露公网；Tauri 环境验收可读取报告。  
10. **UI 变化**：环境验收显示差异和证据。  
11. **配置变化**：legacy DB 路径只读、报告目录。  
12. **数据迁移**：只导出，不导入。  
13. **测试文件**：`tests/test_memory_dual_read.py`、`tests/test_second_brain_export.py`。  
14. **测试命令**：targeted parity tests。  
15. **验收标准**：每个差异有类型、原因、严重度、证据；不能只比较总数。  
16. **回滚方法**：删除报告和工具，不影响任何数据。  
17. **文档更新**：双读规范和测试报告。  
18. **推荐提交信息**：`feat(migration): add second brain dual-read verification`。  
19. **独立子智能体**：适合迁移 QA 子智能体。  
20. **新对话或 Worktree**：独立只读 Worktree。

## P5-02 停止自启动、停止写入与只读兼容期

1. **任务名称**：分阶段关闭 compatibility runtime 写路径。  
2. **目标**：正式系统完全由 `src` 承担，legacy 只读。  
3. **前置条件**：P5-01 parity 达标、备份验证通过。  
4. **明确范围**：disable auto-start、write guards、read-only mode、用户提示。  
5. **禁止范围**：不删除目录/数据库；不强制迁移未验证数据。  
6. **真实修改文件**：legacy startup manager/scripts、compat API write guards、config/docs/tests。  
7. **新增接口或方法**：`compatibility_read_only` guard、retirement status。  
8. **数据流**：正式输入只走 src；legacy 仅查询/export。  
9. **API 变化**：legacy 写 API 返回 stable retired/read-only error。  
10. **UI 变化**：Tauri diagnostics 显示 compatibility 状态；PySide 写操作禁用。  
11. **配置变化**：`second_brain_autostart=false`、`second_brain_write_enabled=false`。  
12. **数据迁移**：无破坏迁移。  
13. **测试文件**：legacy write guard、src ingestion exclusive、startup tests。  
14. **测试命令**：full tests with compatibility runtime enabled read-only and disabled。  
15. **验收标准**：新输入只产生一份；legacy 写请求全部拒绝；正式能力不受影响。  
16. **回滚方法**：在回滚窗口内恢复写 flag，并恢复已验证备份。  
17. **文档更新**：操作手册、回滚手册、Project Status。  
18. **推荐提交信息**：`chore(compat): stop second brain writes and autostart`。  
19. **独立子智能体**：不建议完全自动；需要主开发者审核。  
20. **新对话或 Worktree**：高风险独立 Worktree。

## P5-03 关闭 legacy 回归与 archive 决策

1. **任务名称**：验证无 legacy 运行时并形成最终 archive 决策。  
2. **目标**：证明正式功能在 `second_brain` 不启动时完整工作。  
3. **前置条件**：只读兼容期完成、无未解释高风险差异。  
4. **明确范围**：no-legacy E2E、export checksum、rollback drill、archive plan。  
5. **禁止范围**：本任务默认仍不直接删除代码或数据库。  
6. **真实修改文件**：tests、CI profile、retirement report、archive manifest。  
7. **新增接口或方法**：compatibility-disabled test profile。  
8. **数据流**：only src runtime -> all formal capabilities。  
9. **API 变化**：无。  
10. **UI 变化**：无 legacy dependency indicator。  
11. **配置变化**：CI/local profile disables legacy。  
12. **数据迁移**：验证 export，不执行删除。  
13. **测试文件**：`tests/test_no_second_brain_runtime.py`、full UI E2E。  
14. **测试命令**：full pytest；Tauri full suite；manual rollback drill。  
15. **验收标准**：下方退役门槛全部满足并签署报告。  
16. **回滚方法**：恢复 compatibility read-only runtime 和备份。  
17. **文档更新**：`docs/TEST_REPORTS/SECOND_BRAIN_RETIREMENT_REPORT.md`。  
18. **推荐提交信息**：`test(compat): verify runtime without second brain`。  
19. **独立子智能体**：QA 可执行，最终决定必须人工审核。  
20. **新对话或 Worktree**：独立 release/retirement Worktree。

---

# 12. 双读对比清单

必须逐项比较并解释差异：

- 原始导入数量
- source 数量
- conversation 数量
- message 数量
- 记忆候选数量
- active/core 数量
- FTS 检索结果和排序
- semantic 检索结果和排序
- citation 路径与行号
- 隐私过滤
- Agent Scope
- Context Pack 内容和预算
- relation
- conflict
- Qdrant point 总量与 kind 分布
- expected/missing/orphan points
- production/acceptance workspace 隔离
- 同一输入的幂等结果
- compatibility runtime 关闭后的正式功能

---

# 13. 文件级修改规划

| 阶段 | 计划修改或新增 | 目的 |
|---|---|---|
| P0 | `src/config.py`、`src/control/runtime_settings.py`、`src/runtime/workspace.py` | 端口和 workspace 合同 |
| P1 | `src/model_center/embedding.py`、`src/retrieval/semantic.py`、`qdrant_provider.py`、`index_coordinator.py` | 统一 embedding/vector/index |
| P1 | `src/gateway/bootstrap.py`、`memory_gateway.py` | 正式接线，不再固定 semantic=None |
| P1/P3 | `src/gateway/memory_statistics.py`、`src/control/contracts.py` | 统一统计和 API DTO |
| P2 | `src/sources/read_model.py`、`service.py` 或 `memory_db.py` 派生 schema | 来源、会话、消息查询 |
| P3 | `src/retrieval/trace.py`、`src/gateway/memory_inspector.py` | 共享 trace 和 Inspector facade |
| P3/P4 | `src/control/service.py`、`src/control/api.py` | 8766 唯一桌面 API |
| P4 | `src/memory/revisions.py`、`relations.py`、`conflicts.py` | 派生 read models |
| P3/P4 | `desktop/lingji-control/src/navigation.ts`、`types.ts`、`api.ts`、`App.tsx`、pages/components | 唯一正式 UI |
| P5 | `src/migration/`、tests、reports | export、parity、retirement |
| Compatibility | `second_brain/` 仅 write guard、export、parity、diagnostic 修复 | 不新增正式能力 |

---

# 14. API 规划

## 14.1 兼容策略

当前 Local Control API 返回原始对象。不要在同一个任务中强行改完所有旧 endpoint。

建议：

- 新统一 endpoint 使用 typed response contract。
- 旧 endpoint 在 compatibility window 保持响应，逐页迁移。
- 统一 contract 可采用 `{ok,data,error,meta}`，其中 `meta` 必含 timestamp、request_id、workspace、revision；实施前先冻结 DTO 和前端 client。

## 14.2 计划 endpoint

```text
GET  /api/workspaces
GET  /api/memory/status
GET  /api/memory/inspector/status
GET  /api/memory/inspector/list
GET  /api/memory/inspector/{memory_id}
GET  /api/memory/inspector/{memory_id}/source
GET  /api/memory/inspector/{memory_id}/vector
POST /api/memory/inspector/search

GET  /api/vector/status
GET  /api/vector/coverage
GET  /api/vector/points/{chunk_id}

GET  /api/sources
GET  /api/sources/{source_id}
GET  /api/conversations/{conversation_id}
GET  /api/messages/{message_id}

GET  /api/ai/profiles
GET  /api/mcp/status
GET  /api/tasks/{task_id}/progress
```

所有 endpoint：

- 经过本地 token 认证
- 返回 workspace
- 使用 shared services
- 不直接执行独立 SQL/排名
- 不泄露秘密和未经请求的完整私密正文

---

# 15. 测试矩阵

| 层级 | 核心内容 | 真实依赖要求 | 退出标准 |
|---|---|---|---|
| 单元 | ID、payload、filters、RRF、dimension、status mapping | 可用 fake transport，但不替代集成 | 边界与错误全覆盖 |
| 集成 | Vault -> SQLite -> Qdrant；增量/rebuild；主备 embedding | `:memory:` Qdrant + fake deterministic embedder；另有 Ollama local profile | 真正完成 upsert/search/delete |
| 契约 | Memory Capability Contract | 目录无关 fixture | 13 项统一合同全部通过 |
| API | token、workspace、pagination、error、read-only | FastAPI TestClient + real temp DB/Qdrant | 状态和数据一致 |
| Tauri smoke | 文件、路由、类型、API base | build 后运行 | 不允许因 dist 缺失直接当通过 |
| Playwright | 导航、loading、empty、large、degraded、unavailable、settings validation | fixture control API | 14 页核心路径通过 |
| Workspace | production/acceptance 所有资源 | 两套 temp roots/collections | hash 和计数互不影响 |
| 降级 | Qdrant/Ollama/model/dimension failure | 显式故障注入 | lexical 正常，warning 真实 |
| 双读 | legacy/unified common fixtures | legacy read-only | 差异全部有解释 |
| No legacy | 不启动 `second_brain` | full src runtime | 所有正式能力通过 |

每个功能任务完成后运行相关 targeted tests；阶段结束运行：

```text
python -m pytest tests/ -v
```

并运行 Tauri build、smoke 和 Playwright。禁止删除测试、降低断言、改成 skip 或把“没有 CI”称为通过。

---

# 16. 风险与回滚方案

| 风险 | 防护 | 回滚 |
|---|---|---|
| embedding 维度变化 | 检测 dimension；标记 rebuild_required；新 collection 构建 | 切回旧模型和旧 collection |
| Qdrant 不可用 | lexical fallback；degraded warning | `semantic_enabled=false` |
| semantic 泄露 restricted | Qdrant pre-filter + canonical post-filter + contract tests | 禁用 semantic，保留 lexical |
| 两条采集重复写入 | 只允许 extraction；统一 idempotency key | 停止 legacy writes，清理派生重复而非原始资料 |
| workspace 串库 | WorkspaceContext、物理路径、hash tests | 切回旧 production config，保留 acceptance fixture |
| rebuild 中断 | task/lease/progress；新 collection；旧 collection 不删 | 回到旧 collection，重新执行 |
| Brain Status 造假 | shared statistics；禁止默认 0 | 显示 degraded/unavailable，不猜测 |
| Provider 失败永久黑名单 | cooldown、有限重试、显式 refresh | reset provider state |
| source read model 膨胀 | metadata + pointer；正文按需；可重建 | 删除派生索引并重建 |
| legacy 数据遗漏 | export checksum、dual read、read-only window | 恢复 compatibility read-only runtime |
| UI/后端合同漂移 | typed DTO、contract tests、Playwright | 页面 feature flag 回退 |
| 无关大重构 | 一任务一层或小闭环 | 回退单任务提交 |

---

# 17. `second_brain` 退役门槛

必须全部满足：

1. `src` 已真实接通 Qdrant SemanticProvider。
2. Embedding 主备模型、状态、维度和设置已统一。
3. FTS5、semantic、权限和 RRF 使用一个检索流程。
4. source/conversation/message 可从 raw/Vault 重建。
5. versions/relations/conflicts 查询能力已覆盖。
6. Inspector 和 Vector Center 只读取统一服务。
7. Brain Status、Inspector、MCP 统计一致。
8. Tauri 只访问 8766。
9. production/acceptance 全资源隔离。
10. legacy 数据完成导出、checksum 和只读双读。
11. 所有差异有解释，没有未处理高严重度差异。
12. compatibility runtime 停止自启动。
13. compatibility runtime 停止写入并完成只读观察期。
14. PySide6 关闭不损失正式功能。
15. `second_brain` 关闭后的 backend、MCP、Tauri、采集、备份、验收全部通过。
16. 有已验证备份和恢复演练。
17. 有最终 retirement report 和人工批准。

退役顺序固定：

```text
停止新增功能
-> 停止自启动
-> 停止写入
-> 保留只读兼容期
-> 导出与双读验证
-> 关闭旧运行时测试
-> archive 或删除
```

本路线图不授权删除任何目录或数据库。

---

# 18. 建议的第一项开发任务

第一项正式功能开发建议：

```text
Unified Qdrant SemanticProvider Integration
```

实际执行应先完成其最小前置任务 P0-02/P0-03，然后按：

```text
P1-01 EmbeddingProvider
-> P1-02 QdrantSemanticProvider
-> P1-03 MemoryIndexCoordinator
-> P1-04 Runtime wiring
-> P1-05 status/tests/report
```

不要把这五个任务压成一个同时修改检索、API、UI、迁移和 legacy 删除的巨大提交。那不是“一步到位”，那是把五种故障装进同一个纸箱。

---

# 19. 每阶段文档交付

每个阶段必须新增或更新 Markdown 报告，至少包括：

- 任务目标
- 代码入口
- 修改文件
- 架构决定
- 数据流
- 配置/API/UI 变化
- 测试命令和真实结果
- 已知限制
- 回滚方法
- 下一步
- 提交 SHA

建议报告：

- `docs/TEST_REPORTS/UNIFIED_QDRANT_SEMANTIC_PROVIDER_REPORT.md`
- `docs/TEST_REPORTS/SOURCE_READ_MODEL_REPORT.md`
- `docs/TEST_REPORTS/MEMORY_INSPECTOR_VECTOR_CENTER_REPORT.md`
- `docs/TEST_REPORTS/WORKSPACE_UI_PARITY_REPORT.md`
- `docs/TEST_REPORTS/SECOND_BRAIN_RETIREMENT_REPORT.md`

---

# 20. 本规划任务验收记录

本任务只交付规划文档。

- 功能代码：未修改
- 数据库/schema：未修改
- 依赖：未修改
- 配置：未修改
- 运行数据：未修改
- 功能测试：未运行
- CI：需在提交后查询，不能因没有状态而称为通过
- 下一步：等待明确开发指令后，从 P0-02/P0-03 和 Phase 1 任务链开始
