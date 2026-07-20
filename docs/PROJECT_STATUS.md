# PROJECT_STATUS.md — LingJi 项目实时状态

> Updated（更新时间）: 2026-07-20  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> Validated Code Commit（已验证代码提交）: `8a4860553edfbb698665c7dcb1f8bfaf3f556eba`  
> Status（状态）: P2 MERGED（P2 已合并）  
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

Qdrant
= 可重建 Semantic Index（语义向量索引）

Structured Read Model
= 面向 Memory Inspector 的可重建结构化读取模型
```

`second_brain.sqlite3` 仍是迁移期 Compatibility Data（兼容数据），不是长期数据权威。

## 3. 端口与运行合同

```text
8765 = second_brain Compatibility API（兼容接口）
8766 = authenticated Local Control API（带认证的本地控制接口）
8767 = optional MCP Streamable HTTP（可选 MCP 流式 HTTP）
stdio = default local MCP transport（默认本地 MCP 传输方式）
```

Tauri（跨平台桌面应用框架）只能通过 8766 访问正式控制接口，不得直接连接 8765、8767、Qdrant、Ollama 或 SQLite。

## 4. 已完成阶段

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

## 5. 当前测试状态

最新本机 Codex 汇总：

```text
223 passed
0 failed
8 skipped
```

该结果证明本次执行范围没有失败，但存在 Test Quality Debt（测试质量债务）：

1. `tests/test_desktop.py`
   - 未安装 PySide6 时跳过旧桌面测试。
   - 正式桌面主线已经转向 Tauri。

2. `test_original_startup_files_are_unchanged`
   - 当前只比较工作区文件与 `HEAD`。
   - 只能发现未提交修改，不能保护端口、入口和 Workspace 合同。
   - 后续必须改为 Semantic Startup Contract Test（语义启动合同测试）。

3. Test Count Delta（测试数量差异）
   - P1-05：244 passed、2 failed、9 skipped。
   - P2 汇总：223 passed、0 failed、8 skipped。
   - 当前缺少完整日志解释总数下降。
   - 状态：`UNRECONCILED_TEST_COUNT_DELTA`。

上述问题不阻塞 P2-03，但下一次全量 Regression Test（回归测试）必须解释测试收集数量变化。

## 6. 当前准确状态

```text
Embedding migration                  已实现并本机验证
Qdrant provider                      已实现并本机验证
Workspace isolation                  已实现并本机验证
Lexical/vector coordination          已实现并本机验证
MemoryGateway runtime wiring         已实现并本机验证
8766 status API                      已实现并本机验证
Tauri Vector Center                  已合并并验证
Collection Migration Tool            已合并并验证
Production bge-m3 switch             未执行
Production vector rebuild            未执行
Structured Read Model                未实现
Memory Inspector                     未实现
```

## 7. bge-m3 当前定位

`bge-m3` 是已经通过 Acceptance Validation（验收验证）的中英混合文本向量模型，实际向量维度为 1024。

它尚未成为正式生产默认模型。

生产切换仍必须遵循：

```text
创建新生产候选 Collection
-> 全量重建
-> 覆盖率验证
-> Retrieval Quality A/B Test（检索质量对比测试）
-> 受控配置切换
-> 保留旧 Collection 回滚
```

禁止把不同维度模型的向量写进同一 Collection。

## 8. 当前最高优先级

### P2-03 Structured Read Model（结构化读取模型）

目标是为 Memory Inspector 提供稳定的只读数据合同：

- Source（来源）
- Conversation（对话）
- Message（消息）
- Memory（记忆）
- Chunk（文本分块）
- Vector Linkage（向量关联）

必须支持：

- 分页
- 时间排序
- 来源筛选
- 项目筛选
- 关键词搜索
- Conversation/Message 关联
- Message/Memory 关联
- Memory/Chunk 关联
- Chunk/Vector 状态关联
- Privacy Filter（隐私过滤）
- Workspace 隔离
- 8766 Token Authentication（令牌认证）

P2-03 只开发后端读取合同，不开发 Memory Inspector 页面。

### P2-04 Memory Inspector（记忆检查器）

P2-03 稳定后开发 Tauri 页面，包括：

- 来源列表
- 对话时间线
- 消息上下文
- 记忆关联
- Chunk 展开
- Vector 状态
- 搜索和筛选
- 来源追踪

## 9. 暂缓任务

以下任务不阻塞 P2-03：

- 历史远程分支删除
- 依赖统一重构
- 正式 `bge-m3` 生产切换
- 失败候选 Collection 自动清理
- Collection 历史管理 UI
- 旧 PySide6 桌面完全退役

## 10. 开发冻结规则

- 新记忆功能只进入 `src/`
- 新数据导入只进入 `src/extraction/`
- 新正式桌面功能只进入 `desktop/lingji-control/`
- `second_brain/` 仅用于兼容、导出、迁移和验收阻塞修复
- Tauri 不得直接访问 8765、8767、Qdrant、Ollama 或 SQLite
- 不得删除兼容数据，直到导出、等价验证和回滚要求通过
- 不得为了文档修改重复运行本机完整验证

## 11. 下一开发顺序

```text
P2-03 Structured Read Model
-> P2-04 Memory Inspector
-> 集中 Regression Test 与 Startup Contract 修复
-> 正式 bge-m3 候选 Collection 与受控切换
```

里程碑报告：`docs/FINAL_P2_MERGE_REPORT.md`
