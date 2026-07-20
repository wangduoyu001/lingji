# LingJi（灵机）项目上下文

> 更新日期：2026-07-20
> 当前开发分支：`feature/second-brain-memory`
> 统一方案：`docs/MODULES/UNIFIED_MEMORY_ARCHITECTURE_PLAN.md`

## 项目定位

LingJi 是一个本地优先的私人第二大脑、所有授权 AI 的统一记忆系统，以及机会发现与决策平台。

最终产品只有一个，不再把 `src/` 与 `second_brain/` 描述为两套长期并行产品。

## 当前代码定位

```text
src/
= 长期平台主线
= 统一采集、永久记忆、检索、Context Pack、AI 权限、MCP、控制 API、任务与运维

second_brain/
= 兼容与迁移运行时
= 当前仍保存已接通的 Qdrant、Ollama embedding、结构化会话、版本关系、冲突和验收能力

desktop/lingji-control/
= 唯一正式桌面 UI

second_brain/desktop/
= 验收、兼容和诊断 UI
```

新功能不得继续在两套记忆运行时或两套正式 UI 中重复开发。

## 唯一事实源规则

```text
永久记忆正文与正式知识：Obsidian Vault + Git
原始导入资料：可配置 storage/raw
任务、处理状态与审计事件：lingji_state.db
全文与元数据索引：lingji_memory.db，可重建
语义向量索引：Qdrant，可重建
会话与消息查询：可由 raw 或 Vault 重建的派生 read model
```

`second_brain.sqlite3` 在迁移期间保留，但不再作为最终长期记忆事实源。

## 当前已验证能力

`src/` 已具备：

- FTS5、BM25、trigram 与中文短词回退
- 项目、标签、隐私、时间与 Agent Scope 过滤
- Core Memory、候选审核与主人确认边界
- Context Pack、引用行号与 memory revision
- 多 AI 权限与统一 MemoryGateway
- MCP、统一 Extraction Pipeline、持久队列、幂等、重试与租约
- Tauri 控制中心、模型与 GPU、媒体、备份、Skill、调度与机会系统

`second_brain/` 当前仍具备：

- 实际可运行的 Qdrant 向量搜索
- Ollama embedding 主备模型
- sources / conversations / messages
- memory_versions / memory_relations / conflicts
- production / acceptance 隔离样板
- Second Brain 验收 API 与 PySide6 流程

## 当前关键缺口

`src/gateway/bootstrap.py` 仍以 `semantic_provider=None` 构建检索器，因此 `src` 的语义检索接口已存在但尚未接通真实 Qdrant。

下一阶段优先把 `second_brain` 的 Qdrant 与 embedding 能力适配进 `src.retrieval.hybrid.SemanticProvider`，而不是继续扩展第二套检索系统。

## 目标运行链路

```text
所有输入
  -> src/extraction
  -> raw 快照、隐私扫描、幂等任务
  -> Vault 来源文档与记忆候选
  -> 主人审核
  -> Obsidian/Git 永久记忆
  -> lingji_memory.db + Qdrant
  -> HybridRetriever + ContextPackBuilder
  -> Unified MemoryGateway
  -> MCP / Local Control API / 所有授权 AI

Tauri
  -> Local Control API :8766
```

## 端口口径

目标：

```text
8766 = Local Control API
8767 = 可选 MCP Streamable HTTP
stdio = Codex 等本地 MCP 默认模式
```

当前代码仍存在 `second_brain` API 与 `src` MCP HTTP 同用 `8765` 的冲突。未修改和测试代码前，不得宣称该冲突已解决。

## 开发前必读顺序

1. `AGENTS.md`
2. `docs/AI_CONTEXT.md`
3. `docs/PROJECT_STATUS.md`
4. `docs/ARCHITECTURE.md`
5. `docs/DEVELOPMENT_RULES.md`
6. `docs/MODULES/UNIFIED_MEMORY_ARCHITECTURE_PLAN.md`
7. 与任务相关的模块、审计和测试文档

## 主要目录

| 路径 | 作用 |
|---|---|
| `src/` | 长期统一主线 |
| `second_brain/` | 兼容、迁移与验收来源 |
| `desktop/lingji-control/` | 唯一正式 Tauri UI |
| `second_brain/desktop/` | PySide6 验收与诊断 |
| `tests/` | 单元、集成、UI 与迁移契约测试 |
| `scripts/` | 启动、停止、环境与验收脚本 |
| `docs/` | 架构、状态、规则、审计与报告 |

## 开发原则

- 先理解真实代码，再设计，再开发。
- 新记忆功能只进入 `src/`。
- 新采集只进入 `src/extraction/`。
- 新正式 UI 只进入 Tauri。
- 优先适配已有能力，不复制数据库、检索器或接口。
- 不得把索引数据库升级成第二个永久事实源。
- 所有状态、进度、GPU 与向量数据必须由后端确认。
- 功能开发与大段代码完成后必须更新对应 Markdown 报告。
- 未执行真实测试时，不得宣称验收通过。
