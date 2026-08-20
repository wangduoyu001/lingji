# LingJi 功能可见性矩阵

> Updated: 2026-08-21  
> Scope: PR #105 Owner Fact Chain V5 / 当前正式 Tauri Desktop  
> Purpose: 回答“后端已经有的能力，主人在哪里看、能否理解、失败时去哪里”。

状态枚举：`DAILY_VISIBLE / ADVANCED_VISIBLE / AUTOMATIC_VISIBLE / DEFERRED / GAP`

| 能力 | 后端/正式入口 | 自动运行 | 当前 UI | 可见性 | 主人理解方式 | 异常/下一步 |
|---|---|---:|---|---|---|---|
| Capture 文本/网页/文件/媒体 | `src/control/capture.py`、`src/control/capture_api.py`、`src/extraction/` | 是 | 首页 Cmd+K、添加资料、工作 | `DAILY_VISIBLE` | 提交后显示真实 capture/job identity；处理进入 WorkItem | 失败进入工作/高级任务，可重试；不宣称已记住 |
| Extraction / Queue / Retry | `SQLiteExtractionQueue`、worker | 是 | 工作；高级→任务队列 | `AUTOMATIC_VISIBLE` | 首页看当前工作与下一 actor，工作页看完整结果 | 技术细节留高级，普通失败不制造主人待办 |
| Raw / 导入来源 | `storage/raw`、Extraction adapter | 是 | 添加资料；记忆来源检查 | `ADVANCED_VISIBLE` | 普通用户看来源名称/正式证据，不暴露私人绝对路径 | 需要正文读取授权时进入“需要我” |
| 永久记忆列表/正文 | `MemoryGateway`、Memory Inspector | 是 | 一级“记忆” | `DAILY_VISIBLE` | 显示正文片段、类型、状态、来源与可取回状态 | 无正文/证据时明确未知，不补写猜测 |
| Memory Candidate / Review | `MemoryReviewService` | 部分 | 首页“需要我”、永久记忆审核 | `DAILY_VISIBLE` | concrete `memory_id` 才产生主人动作 | 无候选对象时不使用 summary count 制造按钮 |
| Auto Review SHADOW | `src/auto_review/` | 是 | 高级→自动审查 SHADOW | `ADVANCED_VISIBLE` | 只解释建议和风险，不自动批准 | ACTIVE 在实现层拒绝 |
| Source / Conversation / Message | `src/sources/`、Structured Read Model | 是 | 高级→记忆来源检查 | `ADVANCED_VISIBLE` | 从永久记忆钻取来源/对话/消息证据 | 读取失败显示 degraded，不冒充空数据 |
| FTS / BM25 / 中文回退 | `src/retrieval/memory_db.py`、HybridRetriever | 是 | 记忆搜索；高级 Inspector | `DAILY_VISIBLE` | 用户只需要知道“全文取回可用/不可用” | Qdrant 失败仍保留 lexical 能力 |
| Qdrant / Semantic | `QdrantSemanticProvider` | 是 | 记忆详情；高级→向量中心 | `ADVANCED_VISIBLE` | 记忆页显示语义索引真实状态 | dimension mismatch 标记 rebuild_required，不自动破坏性重建 |
| Retrieval Trace / Quality | Memory Inspector / retrieval trace | 部分 | 高级→记忆来源检查/向量中心 | `GAP` | 当前能诊断命中，但普通用户质量解释仍偏技术 | 后续 P04/P05 做真实 Recall/Precision/Citation 评测，不把 coverage 当准确率 |
| Context Pack / MCP | `src/mcp_server.py`、MemoryGateway | 是 | 高级状态/设置/诊断 | `ADVANCED_VISIBLE` | Desktop 不做聊天框；AI 通过统一 MCP 读取记忆 | 真实多 AI 端到端证据仍属于后续 P06 |
| Obsidian / Vault / Git | `src/obsidian/` | 是 | 高级→Obsidian | `ADVANCED_VISIBLE` | 永久正文权威与索引状态分离展示 | 不自动改写正式知识；路径越界拒绝 |
| Scheduler / Watcher / 自动维护 | state DB / service runtime | 是 | 首页结果/工作；高级脑状态 | `AUTOMATIC_VISIBLE` | 正常维护不打扰主人，只把真实工作/异常结果投影出来 | 后续继续增强 retry/恢复的普通语言解释 |
| Models / Embedding | `src/model_center/` | 是 | 高级→AI 与模型、向量中心 | `ADVANCED_VISIBLE` | 显示实际激活/不可用，不按配置猜 | fallback/缺模型显示真实原因 |
| CPU/GPU/算力 | `src/hardware/` | 是 | 高级→系统与算力、脑状态 | `ADVANCED_VISIBLE` | 动态遥测和 capability 分开 | 没有遥测时 unknown/unavailable，不显示假 0 |
| Storage / Backup / Restore | `src/storage/` | 部分 | 高级→存储、备份 | `ADVANCED_VISIBLE` | 普通工作流不占首页，危险恢复要求确认 | 保持 Production/Acceptance 隔离 |
| 日志/诊断/环境验收 | Control API / acceptance | 否 | 高级→日志、环境验收 | `ADVANCED_VISIBLE` | 只用于故障排查 | 不向日常页面倾倒原始日志 |
| 机会系统 | `src` 既有机会能力 | 后续 | 当前不作为一级入口 | `DEFERRED` | 不抢占第二永久记忆大脑主线 | P11 等 P01-P10 稳定后恢复 |

## 一级 UI 当前职责

```text
首页   = 10 秒回答：需要我吗 / 刚做了什么 / 正在做什么 / 下一步谁做
记忆   = 真正记住了什么 + 为什么可信 + 来源证据
工作   = 所有真实 WorkItem 的当前状态、结果、下一 actor
需要我 = 只有 concrete PendingAction
高级   = 技术状态、模型、向量、来源、任务、存储、备份、设置、日志、验收
```

## PR #105 关闭的主要可见性缺口

- Home 不再从统计、generic event 或路径猜“灵机做了什么”。
- Work 与 Home 共享同一 owner-safe WorkItem projector。
- Home 与“需要我”共享同一 concrete PendingAction projector。
- Cmd+K 不再把“已入队”说成“已经记住”。
- Memory 一级页已经有可读正文片段与来源证据。
- 主动发现明确区分发现、授权、接管和执行。

## 仍保留的后续产品化缺口

以下不是 PR #105 的阻塞，不允许为了“看起来都做完”在本轮胡乱扩范围：

1. Retrieval Quality 的真实数据集和 Recall/Precision/MRR/Citation Accuracy；
2. Inspector / Vector 技术状态进一步翻译成普通用户语言；
3. Codex 之外更多 AI 的真实 MCP 端到端共享记忆证据；
4. 机会系统恢复开发。

这些继续按照 `docs/PROJECT_PROGRESS.md` 的 P04/P05/P06/P08/P09/P11 排队。
