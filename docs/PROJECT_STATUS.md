# PROJECT_STATUS.md — LingJi 项目实时状态

> Updated（更新时间）: 2026-07-21  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> Current Formal HEAD（当前正式提交）: `43dfbd2fdfc2f81545e825fa21328e72153eeddb`  
> P0 Validation Branch（P0 验证分支）: `work/p0-engineering-hygiene`  
> P0 Verified Code Commit（P0 已验证代码提交）: `08b507c2855e05a1d971cb2bcae5c8d2fea578eb`  
> P0 Status（P0 状态）: `FOCUSED_TESTED_AWAITING_FORMAL_MERGE`  
> P2-03 Status（P2-03 状态）: `MERGED_AND_VALIDATED`  
> P2-03B Status（P2-03B 状态）: `MERGED_AND_VALIDATED`  
> P2-03C Status（P2-03C 状态）: `MERGED_AND_VALIDATED`  
> P2-04 Status（P2-04 状态）: `MERGED_AND_VALIDATED`  
> P2-05 Status（P2-05 状态）: `PLANNED_BLOCKED_UNTIL_P0_MERGE`

## 1. 产品与代码主线

```text
src/
= 长期平台主线

desktop/lingji-control/
= 唯一正式 Desktop UI（桌面用户界面）

second_brain/
= Compatibility/Migration Runtime（兼容与迁移运行层）
```

`second_brain/` 不再接收新的正式产品能力，只保留兼容、迁移和待退役实现。

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

SQLite、Qdrant、Read Model 都是可重建派生数据，不得取代 Obsidian Vault + Git 的永久知识权威。

## 3. 已完成并验证阶段

```text
P0 Workspace/Port Contract（工作区与端口合同）       MERGED_AND_VALIDATED
P1 Unified Semantic Memory（统一语义记忆）           MERGED_AND_VALIDATED
P2-01 Vector Center（向量中心）                      MERGED_AND_VALIDATED
P2-02 Collection Migration（向量集合迁移）           MERGED_AND_VALIDATED
P2-03 Structured Read Model（结构化读取模型）         MERGED_AND_VALIDATED
P2-03B Structured Ingestion Wiring（结构化采集接线）  MERGED_AND_VALIDATED
P2-03C Capture Sources Foundation（信息入口基础）      MERGED_AND_VALIDATED
P2-04 Memory Inspector UI（记忆检查器）               MERGED_AND_VALIDATED
```

Production bge-m3 Switch（生产模型切换）和生产 Collection（向量集合）重建仍未执行。

## 4. P0 Engineering Hygiene

状态：

```text
FOCUSED_TESTED_AWAITING_FORMAL_MERGE
```

已完成：

- 删除 `src/config.py` 中机器专属 D 盘备份默认值。
- 未配置备份目录时统一使用 `<storage_path>/backups`。
- 保留 Workspace、环境变量和用户显式配置优先级。
- Obsidian CLI 改为环境、PATH 和平台标准目录探测。
- Windows 支持 `%LOCALAPPDATA%\Programs\Obsidian` 等标准路径。
- Vault 名称由显式环境变量或 Vault 目录名推导。
- 增加 Windows Python 3.12 和 Linux Python 3.13 依赖约束。
- 建立核心、UI、媒体、MCP 和测试依赖所有权。
- 删除启动文件逐字比较测试，改为行为和 AST 合同测试。
- 建立 Windows 测试专用 Workspace 临时根放行机制。
- 保留生产 `C:\` 系统盘拒绝保护和专用验证测试。
- Qdrant 单元测试使用确定性的 in-memory 合同。
- Brain Status API 测试不再启动真实端口或真实硬件探测。
- 新增 Windows GitHub Actions 自动门禁。

## 5. P2-03 Structured Read Model

状态：`MERGED_AND_VALIDATED`

已实现：

- Source、Conversation、Message 派生表。
- Stable ID 和幂等 Upsert。
- Privacy、Project、Agent Scope 权限继承和显式覆盖。
- Message→Memory→Chunk→Vector 只读关系。
- Read Model Schema Version 验证。
- Inspector 503 稳定错误与路径脱敏。
- 只读 `/api/memory/inspector/*` API。

正式入口：

```text
src/sources/read_model.py::SourceReadModel
src/sources/service.py::SourceQueryService
src/gateway/memory_inspector.py::MemoryInspectorFacade
src/control/api.py::create_control_app
```

## 6. P2-03B Structured Ingestion Wiring

状态：`MERGED_AND_VALIDATED`

正式数据流：

```text
Raw Snapshot
-> Adapter
-> Vault write
-> StructuredReadModelSink
-> SourceReadModel.upsert_bundle()
-> Memory Index
-> Audit Event
```

已验证：

- ChatGPT Markdown 与结构化 Source/Conversation/Message 同步生成。
- Raw/Vault 使用安全相对引用。
- Sink 幂等写入。
- Message 级 Memory Link。
- Sink 或 Audit 失败不回滚 Raw/Vault。
- 外部错误摘要不泄露绝对路径和异常原文。

## 7. P2-03C Capture Sources Foundation

状态：`MERGED_AND_VALIDATED`

已实现：

- `src/capture/` 统一入口模型、Policy、去重和服务合同。
- Capture 负责入口和调度，Extraction 负责解析和写入。
- LOW_POWER、NORMAL、DEEP_CAPTURE、PAUSED 模式。
- 文件、网页和文本稳定去重。
- `probe -> success -> commit` 两阶段去重。
- `process_later=True` 强制排队。
- Metadata 递归敏感字段检查。
- 手机分享和浏览器扩展只保留后端合同，客户端暂缓。

## 8. P2-04 Memory Inspector Desktop UI

状态：`MERGED_AND_VALIDATED`

已实现：

- Source、Conversation、Message、Memory、Chunk、Vector 关系查看。
- 分页、筛选、搜索防抖、请求取消和竞态保护。
- Message→Memory、Memory Source、Vector 状态展示。
- `rebuild_required` true/false/null 三态。
- restricted 内容保护。
- 401、503、网络不可用、空数据和无筛选结果状态。
- TypeScript、Smoke Test 和 Vite Build 全部通过。

## 9. P0 最终门禁结果

### Windows Python 3.12

```text
Dependency install: PASS
pip check: PASS
validate_clean_install: PASS
compileall: PASS
```

### Full Repository Pytest

```text
collected: 370
passed: 359
failed: 0
skipped: 11
warnings: 2
duration: 63.24s
exit code: 0
```

### Desktop

```text
npm ci: PASS
npm run test:smoke: PASS
npm run build: PASS
exit code: 0
```

完整报告：

```text
docs/TEST_REPORTS/P0_ENGINEERING_HYGIENE_TEST_REPORT.md
```

## 10. 安全状态

```text
Production ChatGPT 正文读取: NO
Production Vault 修改: NO
Production SQLite 修改: NO
Production Qdrant 访问: NO
Qdrant Server 启动: NO
Ollama 启动: NO
生产模型切换: NO
数据库 Schema 修改: NO
rebase: NO
force push: NO
```

## 11. 当前合并状态

```text
P0 Engineering Hygiene:
READY_FOR_FORMAL_MERGE

P2-05:
BLOCKED_UNTIL_P0_FORMAL_MERGE
```

## 12. 下一步

```text
合并 P0 到 feature/second-brain-memory
-> 更新 CHANGELOG
-> 关闭 Issue #9
-> 将三个 P2-05 分支移动到统一正式基线
-> 启动 P2-05A / P2-05B / P2-05C 并行开发
```

当前明确不开发：

```text
系统监听
剪贴板监听
文件夹监听
手机分享客户端
浏览器插件
平台专用自动采集客户端
```