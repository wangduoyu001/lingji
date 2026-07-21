# PROJECT_STATUS.md — LingJi 项目实时状态

> Updated（更新时间）: 2026-07-21  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> P0 Status（P0 状态）: `MERGED_AND_VALIDATED`  
> P2-03 Status（P2-03 状态）: `MERGED_AND_VALIDATED`  
> P2-03B Status（P2-03B 状态）: `MERGED_AND_VALIDATED`  
> P2-03C Status（P2-03C 状态）: `MERGED_AND_VALIDATED`  
> P2-04 Status（P2-04 状态）: `MERGED_AND_VALIDATED`  
> P2-05 Validated Integration Tree（P2-05 已验证集成树）: `1bf95b8d16a9daea52b60518f0e920a0c0bd50db`  
> P2-05 Formal Merge Commit（P2-05 正式合并提交）: `c77e78c0f71339264d54fc083dbc5cfabcfaa173`  
> P2-05 Status（P2-05 状态）: `MERGED_AND_VALIDATED`

## 1. 产品与代码主线

```text
src/
= 长期平台主线

desktop/lingji-control/
= 唯一正式 Desktop UI

second_brain/
= Compatibility/Migration Runtime
```

`second_brain/` 不再接收新的正式产品能力，只保留兼容、迁移和待退役实现。

## 2. 数据权威

```text
Obsidian Vault + Git
= 永久记忆和正式知识正文

storage/raw
= 原始导入材料

lingji_state.db
= 任务、队列、Runtime State 和 Audit Event

lingji_memory.db
= 可重建 Lexical/Metadata Index
  + Structured Read Model

Qdrant
= 可重建 Semantic Index
```

SQLite、Qdrant 和 Structured Read Model 都是可重建派生数据，不得取代 Obsidian Vault + Git 的永久知识权威。

## 3. 已完成并验证阶段

```text
P0 Workspace/Port Contract                         MERGED_AND_VALIDATED
P0 Engineering Hygiene                            MERGED_AND_VALIDATED
P1 Unified Semantic Memory                        MERGED_AND_VALIDATED
P2-01 Vector Center                               MERGED_AND_VALIDATED
P2-02 Collection Migration                        MERGED_AND_VALIDATED
P2-03 Structured Read Model                       MERGED_AND_VALIDATED
P2-03B Structured Ingestion Wiring                MERGED_AND_VALIDATED
P2-03C Capture Sources Foundation                 MERGED_AND_VALIDATED
P2-04 Memory Inspector UI                         MERGED_AND_VALIDATED
P2-05 Manual Capture Center                       MERGED_AND_VALIDATED
```

Production `bge-m3` Switch 和生产 Collection 重建仍未执行。

## 4. P2-03 Structured Read Model

- Source、Conversation、Message 派生表。
- Stable ID 和幂等 Upsert。
- Privacy、Project、Agent Scope 权限继承和显式覆盖。
- Message→Memory→Chunk→Vector 只读关系。
- Read Model Schema Version 验证。
- Inspector 稳定错误和路径脱敏。

正式入口：

```text
src/sources/read_model.py::SourceReadModel
src/sources/service.py::SourceQueryService
src/gateway/memory_inspector.py::MemoryInspectorFacade
src/control/api.py::create_control_app
```

## 5. P2-04 Memory Inspector Desktop UI

- Source、Conversation、Message、Memory、Chunk、Vector 关系查看。
- 分页、筛选、搜索防抖、请求取消和竞态保护。
- Message→Memory、Memory Source、Vector 状态展示。
- restricted 内容保护。
- 401、503、网络不可用、空数据和无筛选结果状态。

## 6. P2-05 Manual Capture Center

状态：`MERGED_AND_VALIDATED`

集成顺序：

```text
P2-05B -> f01e3b2cc49065cda69f1c8909933dd0c530e4ff
P2-05A -> 46a0c5276252734c121f0cad7a56cf3a4a7c4bdc
P2-05C -> fab0ba1b816c1228b8cfb3618aa04b5e2f2c4c3d
Validated tree -> 1bf95b8d16a9daea52b60518f0e920a0c0bd50db
Formal merge -> c77e78c0f71339264d54fc083dbc5cfabcfaa173
```

已实现：

- 文本、网页、支持文件、媒体、ChatGPT Export 和 Codex Report 手动提交。
- 正式 `manual_*` Capture Method 和现有 Adapter Registry 映射。
- 所有 Desktop 手动提交默认进入持久化 Extraction Queue。
- Capture Mode 持久化、暂停和恢复。
- Queue 分页、筛选、取消和重试。
- 脱敏 CaptureJob DTO、稳定错误码和 Audit Event。
- Tauri Capture Center、官方文件选择 Dialog 和最小权限。
- 完成任务可跳转 Memory Inspector。
- 临时 `_api_core.py` 和 `_queue_core.py` 已折回正式模块并删除。

最终门禁：

```text
Windows Python 3.12 full pytest: 398 passed / 11 skipped / 0 failed
npm ci: PASS
npm run test:capture: PASS
npm run test:smoke: PASS
npm run build: PASS
cargo check: PASS
formal PR tests: SUCCESS
formal PR P0 Windows Gate: SUCCESS
```

完整报告：

```text
docs/MODULES/P2_05_INTEGRATED_IMPLEMENTATION.md
docs/TEST_REPORTS/P2_05_INTEGRATED_VALIDATION_REPORT.md
```

## 7. 安全状态

```text
Production ChatGPT 正文读取: NO
Production Vault 修改: NO
Production SQLite 修改: NO
Production Qdrant 访问: NO
Qdrant Server 启动: NO
Ollama 启动: NO
生产模型切换: NO
数据库 Schema 修改: NO
新数据库: NO
第二套队列: NO
rebase: NO
force push: NO
```

## 8. 当前状态

```text
P0 Engineering Hygiene:
MERGED_AND_VALIDATED

P2-03 / P2-03B / P2-03C / P2-04:
MERGED_AND_VALIDATED

P2-05 Manual Capture Center:
MERGED_AND_VALIDATED
```

## 9. 下一步

```text
Obsidian CLI 正式迁入 src
-> 接入 8766 Local Control API
-> 接入 Runtime Settings
-> 接入 Tauri 状态与设置入口
-> 保持 second_brain 仅为兼容层
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
