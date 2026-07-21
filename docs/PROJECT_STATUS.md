# PROJECT_STATUS.md — LingJi 项目实时状态

> Updated（更新时间）: 2026-07-21  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> Formal Integration Commit（正式集成提交）: `41a5264b344d24300ab731dffc19985402f5b24e`  
> Integrated Development Branch（集成开发分支）: `work/p2-04-integrated-validation`  
> Integrated Base Commit（集成基础提交）: `432ae059454cc7db8ab0ba4aaa63d24f5c9173e9`  
> Verified Code Commit（已验证代码提交）: `2688b8b2521890af852b049e78795cffade43584`  
> P2-03 Status（P2-03 状态）: `MERGED_AND_VALIDATED`  
> P2-03B Status（P2-03B 状态）: `MERGED_AND_VALIDATED`  
> P2-03C Status（P2-03C 状态）: `MERGED_AND_VALIDATED`  
> P2-04 Status（P2-04 状态）: `MERGED_AND_VALIDATED`  
> Integrated Merge State（集成合并状态）: `MERGED_AND_VALIDATED`

## 1. 产品与代码主线

```text
src/
= 长期平台主线

desktop/lingji-control/
= 唯一正式 Desktop UI（桌面用户界面）

second_brain/
= Compatibility/Migration Runtime（兼容与迁移运行层）
```

P2-03 至 P2-04 已完成联合开发、返工、集成、本机集中验证，并以安全 fast-forward 方式进入正式分支。未执行 rebase 或 force push。

## 2. 数据权威

```text
Obsidian Vault + Git
= 永久记忆和正式知识正文

storage/raw
= 原始导入材料

lingji_state.db
= 任务、队列、Runtime State（运行状态）和 Audit Event（审计事件）

lingji_memory.db
= 可重建 Lexical/Metadata Index（词法与元数据索引）
  + Structured Read Model（结构化读取模型）

Qdrant
= 可重建 Semantic Index（语义索引）
```

`second_brain.sqlite3` 仍是 Compatibility Data（兼容数据）和迁移证据，不是长期事实源。

## 3. 已完成并验证阶段

```text
P0 Workspace/Port Contract（工作区与端口合同）  MERGED_AND_VALIDATED
P1 Unified Semantic Memory（统一语义记忆）      MERGED_AND_VALIDATED
P2-01 Vector Center（向量中心）                 MERGED_AND_VALIDATED
P2-02 Collection Migration（向量集合迁移）      MERGED_AND_VALIDATED
P2-03 Structured Read Model（结构化读取模型）    MERGED_AND_VALIDATED
P2-03B Structured Ingestion Wiring（结构化采集接线） MERGED_AND_VALIDATED
P2-03C Capture Sources Foundation（信息入口基础） MERGED_AND_VALIDATED
P2-04 Memory Inspector UI（记忆检查器）          MERGED_AND_VALIDATED
```

Production bge-m3 Switch（生产模型切换）和生产 Collection（向量集合）重建仍未执行。

## 4. P2-03 Structured Read Model

状态：

```text
MERGED_AND_VALIDATED
```

已实现并验证：

- Source/Conversation/Message（来源、对话、消息）派生表。
- Stable ID（稳定标识符）和 Idempotent Upsert（幂等更新或插入）。
- Privacy Filter（隐私过滤）和 Agent Scope（智能体范围）。
- `privacy_inherited`、`projects_inherited`、`agent_scope_inherited`。
- Source→Conversation 与 Conversation→Message 权限同步。
- 显式子级权限保护。
- Schema Version（数据库结构版本）验证。
- Message→Memory→Chunk→Vector 只读关联。
- `rebuild_required` true/false/null 三态。
- Inspector 503 稳定错误和路径脱敏。
- HTTP/HTTPS URL 认证信息和敏感查询参数脱敏。
- 只读 `/api/memory/inspector/*` GET API。

正式单一实现：

```text
src/sources/read_model.py::SourceReadModel
src/gateway/memory_inspector.py::MemoryInspectorFacade
src/control/api.py::create_control_app
```

## 5. P2-03B Structured Ingestion Wiring

状态：

```text
MERGED_AND_VALIDATED
```

当前正式数据流：

```text
Raw Snapshot（原始快照）
-> Adapter（适配器）
-> Vault write（知识库写入）
-> on_documents_written
-> StructuredReadModelSink
-> SourceReadModel.upsert_bundle()
-> Audit Event（审计事件）
```

已实现并验证：

- `StructuredMessage`、`StructuredConversation`、`StructuredSource`。
- ChatGPT Adapter 同时生成 Markdown 和结构化消息。
- Raw/Vault 安全相对引用。
- Structured Sink 幂等写入 Read Model。
- 每条 Message 优先使用自身 `document_stable_id` 建立 Memory Link。
- Memory Link 缺失时只跳过对应 Message，不影响其他 Message。
- Structured Sink 失败不回滚 Raw/Vault。
- `StateDatabase.append_event()` 正式审计事件接线。
- Audit Event 写入失败不影响采集主流程。
- Vector Provider 和 Snapshot 错误只返回稳定摘要，不泄漏本机路径。

## 6. P2-03C Capture Sources Foundation

状态：

```text
MERGED_AND_VALIDATED
```

已实现并验证：

- `src/capture/` 统一入口模型、策略、去重、服务和监听器合同。
- Capture 只负责入口合同和调度，Extraction 负责解析和写入。
- LOW_POWER、NORMAL、DEEP_CAPTURE、PAUSED 四种模式。
- 全局键盘监听、全屏截图监听默认关闭。
- 文件、网页、文本稳定去重。
- 去重采用 `probe -> Pipeline success -> commit`，失败后允许重试。
- 手机分享和浏览器扩展仅保留后端合同，客户端暂不开发。
- Codex、Web、Media 显式启用结构化回退。
- 未知 Adapter 默认不自动包装。
- Metadata 递归敏感字段检查，不能覆盖保留字段。
- `process_later=True` 强制进入队列。

## 7. P2-04 Memory Inspector Desktop UI

状态：

```text
MERGED_AND_VALIDATED
```

已实现并验证：

- Desktop 侧边栏新增“记忆检查器”。
- Source、Conversation、Message、Memory、Chunk、Vector 关系查看。
- 后端分页、筛选、搜索防抖、请求取消和竞态保护。
- Message→Memory 关系、Memory Source、Vector 状态展示。
- `rebuild_required` true/false/null 三态显示。
- restricted 内容列表隐藏摘要，详情默认折叠。
- 401、503、网络不可用、空数据和筛选无结果状态区分。
- Memory Source 使用 `canonical.citations` 数组。
- Chunk 数量使用 `chunk_count -> chunks.length -> 未知` 回退。
- `memoryInspectorContract.ts` 已移除 `ts-nocheck`。
- TypeScript Build、Smoke Tests 和 Vite Build 均通过。

## 8. 统一异常脱敏

唯一正式工具：

```text
src/extraction/errors.py::safe_extraction_error
```

使用位置：

```text
src/extraction/pipeline.py
src/extraction/adapters/chatgpt.py
src/extraction/structured_sink.py
```

对外稳定摘要：

```text
Post-extraction index synchronization failed; see local logs
<conversation_id>: conversation extraction failed; see local logs
structured read model write failed; see local logs
Vector status unavailable; see local logs
```

完整异常只进入本地 logger，不得进入 API response、`batch.warnings`、`index_error` 或 Vector HTTP 200 响应。

## 9. 集成测试结果

### 9.1 Python 语法检查

```text
python -m compileall
PASS
exit code: 0
```

### 9.2 遗漏历史回归组

```text
collected: 20
passed: 20
failed: 0
skipped: 0
duration: 8.05s
exit code: 0
```

### 9.3 最终里程碑门禁集合

```text
collected: 91
passed: 91
failed: 0
skipped: 0
duration: 11.30s
exit code: 0
```

### 9.4 Frontend 门禁

```text
test:inspector: PASS
test:smoke: PASS（6/6）
tsc -b: PASS（0 errors）
npm run build: PASS
```

### 9.5 Full Repository Pytest

```text
collected: 338
passed: 306
failed: 19
skipped: 13
duration: 45.99s
```

19 个失败属于里程碑门禁外的环境相关测试：

- `test_qdrant_semantic_provider.py`: 7，测试环境未启动 Qdrant。
- `test_memory_capability_contract.py`: 6，Windows `C:\Temp` 系统盘限制。
- `test_semantic_runtime_wiring.py`: 5，Windows `C:\Temp` 系统盘限制。
- `test_status_snapshot_wiring.py`: 1，Windows `C:\Temp` 系统盘限制。

这些失败不属于 P2-03 → P2-04 目标门禁；目标门禁 91/91 全部通过。

## 10. 数据安全

```text
读取 Production ChatGPT 正文: NO
修改 Production Vault: NO
修改 Production SQLite: NO
访问 Production Qdrant: NO
启动 Production Qdrant: NO
启动 Ollama: NO
启动 Tauri: NO
切换生产模型: NO
创建或删除生产 Collection: NO
修改数据库 Schema: NO
```

## 11. 当前状态

```text
P2-03:  MERGED_AND_VALIDATED
P2-03B: MERGED_AND_VALIDATED
P2-03C: MERGED_AND_VALIDATED
P2-04:  MERGED_AND_VALIDATED

Integrated Merge State:
MERGED_AND_VALIDATED
```

## 12. 下一阶段边界

用户已明确暂不开发：

```text
系统监听
剪贴板监听
文件夹监听
手机分享客户端
浏览器插件
```

下一阶段聚焦：

```text
P2-05 Manual Capture Center（手动信息入口中心）
-> Capture Control API
-> 任务状态持久化
-> 手动文本、网页、文件、媒体导入
-> Desktop 任务进度与结果跳转
```

正式分支后续开发必须从当前 `feature/second-brain-memory` 最新提交创建新分支。