# PROJECT_STATUS.md — LingJi 项目实时状态

> Updated（更新时间）: 2026-07-20  
> Branch（分支）: `work/p2-03-structured-read-model`  
> Verified Commit（已验证提交）: `b9950b4066fbb0b602c2ffba5109da2fa8371cf3`  
> Status（状态）: P2-03 `IMPLEMENTED_NOT_TESTED`  
> Documentation Contract（文档维护合同）: `docs/DOCUMENTATION_MAINTENANCE.md`

## 1. 产品方向

```text
src/
= 长期平台主线

desktop/lingji-control/
= 唯一正式 Desktop UI（桌面用户界面）

second_brain/
= Compatibility Runtime（兼容运行层）、迁移工具和验收来源
```

LingJi 的目标是一个私有 Second Brain（第二大脑）和一套可供授权 AI Client（AI 客户端）共享的记忆系统。

## 2. 数据权威

```text
Obsidian Vault + Git
= 永久记忆和正式知识文本

storage/raw
= 原始导入材料

lingji_state.db
= 任务、队列和 Audit Event（审计事件）

lingji_memory.db
= 可重建 Lexical/Metadata Index（词法与元数据索引）
  + Structured Read Model（结构化读取模型）

Qdrant
= 可重建 Semantic Index（语义向量索引）
```

`second_brain.sqlite3` 仍是迁移期 Compatibility Data（兼容数据），不是长期数据权威。P2-03 不会自动读取或迁移生产兼容数据库。

## 3. 端口与运行合同

```text
8765 = second_brain Compatibility API（兼容接口）
8766 = authenticated Local Control API（带认证的本地控制接口）
8767 = optional MCP Streamable HTTP（可选 MCP 流式 HTTP）
stdio = default local MCP transport（默认本地 MCP 传输方式）
```

Tauri（跨平台桌面应用框架）只能通过 8766 访问正式控制接口，不得直接连接 8765、8767、Qdrant、Ollama 或 SQLite。

## 4. 已完成并合并阶段

### P0 Workspace 与端口合同

已完成：

- `WorkspaceContext` 与 `WorkspaceResolver`
- Production/Acceptance Workspace（生产与验收工作区）物理隔离
- 独立 Qdrant Collection（向量集合）
- 8765、8766、8767 和 stdio 端口合同

### P1 Unified Semantic Memory（统一语义记忆）

已完成并通过真实本机验收：

- `EmbeddingProvider`
- `QdrantSemanticProvider`
- `MemoryIndexCoordinator`
- `HybridRetriever`
- `MemoryGateway` Runtime Wiring（运行时接线）
- `MemoryStatisticsService`
- `/api/memory/status`
- `/api/vector/status`
- `/api/vector/coverage`
- `/api/brain/status`

真实本机验收：

```text
Ollama 0.32.0                    可用
bge-m3                           已安装并验证
bge-m3 actual dimension          1024
Qdrant in-memory                 PASS
Qdrant temporary embedded disk   PASS
vector coverage                  2/2 = 1.0
multilingual retrieval           PASS
acceptance isolation             PASS
```

P1 报告：

- `docs/TEST_REPORTS/P1_05_MEMORY_VECTOR_STATUS_TEST_REPORT.md`
- `docs/TEST_REPORTS/P1_05_LOCAL_ACCEPTANCE_SUMMARY.md`

### P2-01 Vector Center（向量中心）

状态：

```text
MERGED_AND_VALIDATED
```

已进入正式 Tauri UI：

- Memory Index（记忆索引）状态
- Embedding Provider（向量嵌入提供器）状态
- Qdrant 状态
- Vector Coverage（向量覆盖率）
- live/snapshot/unavailable/stale 状态
- 15 秒自动刷新
- 页面不可见时停止请求
- `Promise.allSettled()` 部分失败降级
- 未知值显示 `-`，真实零显示 `0`
- Brain Status 假零修复

本机汇总：

```text
5 项 Smoke Test（冒烟测试）通过
npm run build 通过
```

报告：`docs/TEST_REPORTS/P2_01_VECTOR_CENTER_UI_TEST_REPORT.md`

### P2-02 Collection Migration（向量集合迁移工具）

状态：

```text
MERGED_AND_VALIDATED
```

已实现：

- 独立候选 Collection 构建
- 目标模型和向量维度验证
- 精确向量数量验证
- 100% 覆盖率验证
- Activation Settings（激活设置）
- Rollback Settings（回滚设置）
- Atomic Manifest（原子迁移清单）

本机汇总：

```text
8/8 重点单元测试通过
真实 bge-m3 隔离验收通过
candidate coverage = 100%
```

报告：`docs/TEST_REPORTS/P2_02_VECTOR_COLLECTION_MIGRATION_TEST_REPORT.md`

## 5. P2-03 Structured Read Model

当前开发分支已实现：

```text
src/sources/read_model.py
src/sources/service.py
src/gateway/memory_inspector.py
src/control/memory_inspector.py
```

新增可重建派生表：

```text
source_read_model_meta
source_records
conversation_records
message_records
message_memory_links
```

已实现合同：

- Stable ID（稳定 ID）
- Idempotent Upsert（幂等更新或插入）
- Source/Conversation/Message 列表与详情
- Message 列表只返回 preview，不返回完整正文
- `limit/offset` 分页，范围 1..200
- 稳定时间排序和 ID tie-breaker（并列排序补充键）
- source/project/privacy/status/role/time/q 筛选
- Privacy Filter（隐私过滤）
- Agent Scope（智能体读取范围）
- Workspace 响应与数据库隔离合同
- Message→Memory、Memory→Chunk、Chunk→Vector 诊断
- 只读 `/api/memory/inspector/*` 8766 GET 路由
- 401/404/422/503 错误合同
- 绝对路径和敏感 metadata 清理
- Qdrant 无法安全确认时 `exists=null`

当前没有执行：

- 生产聊天历史导入
- `second_brain.sqlite3` 自动迁移
- Production Vault/SQLite/Qdrant 访问
- Production bge-m3 Collection 构建
- Tauri Memory Inspector 页面

计划：`docs/MODULES/P2_03_STRUCTURED_READ_MODEL_PLAN.md`  
报告：`docs/TEST_REPORTS/P2_03_STRUCTURED_READ_MODEL_TEST_REPORT.md`

## 6. 当前测试状态

最近一次已记录全量本机汇总仍为：

```text
223 passed
0 failed
8 skipped
```

该结果不是 P2-03 测试结果。测试数量相对 P1-05 仍存在：

```text
UNRECONCILED_TEST_COUNT_DELTA
```

P2-03 当前已执行辅助检查：

```text
Python py_compile                    PASS
临时 SQLite 隔离冒烟                 PASS
禁止端口/Qdrant/raw vector 静态扫描 PASS
```

P2-03 重点 pytest 和直接相关回归尚未执行，因此准确状态是：

```text
IMPLEMENTED_NOT_TESTED
```

不得把代码提交、静态编译或无 CI 红灯解释为功能测试通过。

## 7. 当前准确状态

```text
Embedding migration                  已实现并本机验证
Qdrant provider                      已实现并本机验证
Workspace isolation                  已实现并本机验证
Lexical/vector coordination          已实现并本机验证
MemoryGateway runtime wiring         已实现并本机验证
8766 status API                      已实现并本机验证
Tauri Vector Center                  已合并并验证
Collection Migration Tool            已合并并验证
Structured Read Model                已实现，重点测试待执行
Memory Inspector Facade/API          已实现，重点测试待执行
Production bge-m3 switch             未执行
Production vector rebuild            未执行
Tauri Memory Inspector               未实现
```

## 8. bge-m3 当前定位

`bge-m3` 是已经通过 Acceptance Validation（验收验证）的中英混合文本向量模型，实际向量维度为 1024。

它尚未成为正式生产默认模型。生产切换仍必须遵循：

```text
创建新生产候选 Collection
-> 全量重建
-> 覆盖率验证
-> Retrieval Quality A/B Test（检索质量对比测试）
-> 受控配置切换
-> 保留旧 Collection 回滚
```

禁止把不同维度模型的向量写进同一 Collection。

## 9. 当前最高优先级

### P2-03 审查与重点验证

需要在完整本机仓库执行：

```powershell
python -m pytest `
  tests/test_source_read_model.py `
  tests/test_source_service.py `
  tests/test_memory_inspector_facade.py `
  tests/test_memory_inspector_api.py `
  -v --tb=short
```

然后执行直接相关回归：

```powershell
python -m pytest `
  tests/test_memory_retrieval.py `
  tests/test_permanent_memory_gateway.py `
  tests/test_workspace_contract.py `
  tests/test_control_api.py `
  -v --tb=short
```

审查和测试通过后才能合并正式分支。

### P2-04 Memory Inspector（记忆检查器）

P2-03 合同稳定后开发 Tauri 页面，包括：

- 来源列表
- 对话时间线
- 消息上下文
- 记忆关联
- Chunk 展开
- Vector 状态
- 搜索和筛选
- 来源追踪

## 10. 暂缓任务

以下任务不阻塞 P2-03 审查：

- 历史远程分支删除
- 依赖统一重构
- 正式 `bge-m3` 生产切换
- 失败候选 Collection 自动清理
- Collection 历史管理 UI
- 旧 PySide6 桌面完全退役

## 11. 开发冻结规则

- 新记忆功能只进入 `src/`
- 新数据导入只进入 `src/extraction/`
- 新正式桌面功能只进入 `desktop/lingji-control/`
- `second_brain/` 仅用于兼容、导出、迁移和验收阻塞修复
- Tauri 不得直接访问 8765、8767、Qdrant、Ollama 或 SQLite
- Control Process 不得为了诊断重新打开 Embedded Qdrant
- 不得删除兼容数据，直到导出、等价验证和回滚要求通过
- 不得为了文档修改重复运行本机完整验证

## 12. 下一开发顺序

```text
P2-03 重点测试与代码审查
-> 合并 feature/second-brain-memory
-> P2-04 Memory Inspector
-> 集中 Regression Test 与 Startup Contract 修复
-> 正式 bge-m3 候选 Collection 与受控切换
```

当前合并状态：

```text
NOT_MERGED_AWAITING_REVIEW
```

里程碑报告：`docs/FINAL_P2_MERGE_REPORT.md`
