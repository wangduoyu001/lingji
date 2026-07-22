# PROJECT_STATUS.md — LingJi 项目实时状态

> Updated（更新时间）: 2026-07-22  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> Formal Head（正式提交）: `f955b7c8a9a28aa1351d02e5ef70be2551a565b2`  
> P2-08 Status: `MERGED_AND_VALIDATED`  
> P2-09 Status: `MERGED_AND_VALIDATED`

## 1. 当前结论

P2-08 Auto Review SHADOW Layer 与 P2-09 Runtime/Desktop Reliability 已完成实现、依赖合并、整仓 GitHub Actions 验证和本机现场验收。

```text
PR #24  P2-09A Runtime Truth                         MERGED
PR #25  P2-09B Canonical Idempotency + MCP Queue     MERGED
PR #26  P2-09C Desktop Polling Data Layer             MERGED
PR #27  P2-08A Deterministic Auto Review Core         MERGED
PR #28  P2-08B Local AI Reviewer + SHADOW API         MERGED
PR #29  P2-09D Desktop UX + SHADOW Dashboard          MERGED
PR #30  Combined Integration Verification             MERGED
PR #31  Project Status / Changelog / Code Map Sync    MERGED
```

最终集成门禁：

```text
tests workflow #696: SUCCESS
P0 Windows Gate #94: SUCCESS
Python 3.11: SUCCESS
Python 3.12: SUCCESS
Windows full tests: SUCCESS
Desktop smoke: SUCCESS
React/Vite build: SUCCESS
Tauri Rust check: SUCCESS
MCP smoke: SUCCESS
Browser capture smoke: SUCCESS
Obsidian plugin smoke: SUCCESS
```

2026-07-22，项目主人确认此前列出的真实 Windows、RTX 4060、Ollama、Qdrant、8766 与 Tauri 本机验收已经完成。该结论按主人现场确认记录；仓库未附加新的逐项命令、原始日志、耗时或硬件数值，因此文档不虚构这些细节。

## 2. 产品与代码主线

```text
src/
= 长期平台主线

desktop/lingji-control/
= 唯一正式 Desktop UI

second_brain/
= Compatibility / Migration Runtime
```

规则：

- 新正式能力进入 `src/`。
- Desktop 只通过认证的 8766 Local Control API 访问后端。
- `second_brain/` 不接收新的正式产品能力。
- Obsidian CLI 正式实现位于 `src/obsidian/`。
- MCP 默认使用 stdio；可选 HTTP 使用8767。

## 3. 数据权威

```text
Obsidian Vault + Git
= 永久记忆与正式知识正文

storage/raw
= 原始导入材料

lingji_state.db
= 任务、Extraction Queue、Runtime State、Audit Event

lingji_memory.db
= 可重建 Lexical/Metadata Index + Structured Read Model

Qdrant
= 可重建 Semantic Index
```

SQLite、Qdrant、向量和 Structured Read Model 均为派生数据，不得取代 Obsidian Vault + Git 的正式知识权威。

## 4. 已完成阶段

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
P2-06 Obsidian CLI Formal Migration               MERGED_AND_VALIDATED
P2-07 Codex-first Local Memory Loop                MERGED_AND_VALIDATED
P2-08 Auto Review SHADOW Layer                    MERGED_AND_VALIDATED
P2-09 Runtime/Desktop Reliability                 MERGED_AND_VALIDATED
```

## 5. P2-09 Runtime Truth

已实现：

- Brain Status 不再把未知 GPU 利用率伪装成0。
- 静态硬件信息与动态遥测分离。
- 动态遥测不可用时返回 `null`、`unavailable`、`stale` 与错误摘要。
- Embedding 默认主模型为 `bge-m3`，备用为 `nomic-embed-text`。
- Qdrant 维度不一致时阻止写入并标记 `rebuild_required`。
- `run_service.py` 明确记录 Core、Extraction Worker 与8766 Control API 的实际启动边界。

正式文件：

```text
src/config.py
src/control/service.py
src/hardware/
src/model_center/embedding.py
src/retrieval/qdrant_provider.py
run_service.py
```

## 6. P2-09 Canonical Idempotency 与 MCP Queue

已实现：

- `src/extraction/idempotency.py` 是唯一持久幂等算法来源。
- 文件使用内容哈希；目录使用稳定 Manifest；Payload 和 Options 使用 canonical JSON。
- Pipeline 与 Queue 共享同一算法。
- `submit_codex_work_report` 和 `capture_web_source` 默认先进入 SQLite Extraction Queue。
- `process_now=True` 仍先持久入队，再通过正常 Queue/Lease 路径处理。
- Work Report 必须包含任务、执行、仓库、分支、提交、文件和测试结构。
- CaptureDeduplicator 继续负责短窗口去重，不与持久幂等混为一套。

## 7. P2-09 Desktop Polling 与 UX

已实现：

- `usePollingResource<T>` 统一处理取消、无重叠、退避、隐藏暂停、过期、手动刷新与旧数据保留。
- Brain Status 保留“真实0”和“未知 null”的区别。
- Desktop 导航整理为五组：总览、记忆与项目、采集与处理、模型与运行、运维与设置。
- API 地址与控制令牌改为可折叠连接栏。
- Overview 展示真实 Memory、Vector、Embedding、Compute、Queue 和 Storage 状态。
- Auto Review SHADOW 看板展示建议、风险、规则、AI 摘要和主人反馈。

Desktop 不包含 Auto Review approve、reject、delete、execute 或 ACTIVE 控件。

## 8. P2-08 Auto Review SHADOW

模式合同：

```text
OFF
SHADOW
ACTIVE  # 仅枚举存在，当前实现拒绝
```

确定性硬规则要求主人审核：

- Core Memory。
- 删除、遗忘、归档、权限或隐私变更。
- restricted 内容。
- 跨项目合并。
- 知识冲突。
- 证据不足的耐久知识。
- 失败或未验证的开发报告。
- 主人亲自编辑的记忆。

本地 AI：

- 只接受本机 Ollama loopback 地址。
- 模型由 `auto_review_primary` / `auto_review_fallback` 角色解析。
- 只允许增加风险，不允许降低硬规则风险或改变确定性动作。
- 严格 JSON；失败时安全回退到确定性结果。
- 不请求或存储私有思维链。

8766 SHADOW API：

```text
GET  /api/auto-review/status
GET  /api/auto-review/decisions
GET  /api/auto-review/decisions/{decision_id}
GET  /api/auto-review/metrics
POST /api/auto-review/evaluate/{subject_id}
POST /api/auto-review/feedback
POST /api/auto-review/audit/verify
```

不存在自动批准、自动拒绝、删除、执行或启用 ACTIVE 的 API。

## 9. 审核与写入权威

```text
MemoryReviewService
= 主人审核入口

MemoryLifecycleService
= 唯一正式生命周期写入器

Auto Review
= 只生成 SHADOW 决策和 Audit Event
```

Auto Review 不得：

- 伪造 `owner_confirmed=True`。
- 修改候选状态。
- 写入 Core Memory。
- 写入 Obsidian。
- 写入 Qdrant。
- 执行批准、拒绝、删除或合并。

## 10. 安全状态

```text
自动 Qdrant Collection 删除/重建: NO
自动模型下载: NO
数据库 Schema 修改: NO
新数据库: NO
第二套队列: NO
第二套生命周期: NO
第二套审计数据库: NO
rebase: NO
force push: NO
master 修改: NO
```

本机验收允许在主人控制的现场环境中读取运行状态并验证既有生产依赖，但没有改变上述自动化和架构边界。

## 11. 本机验收结果

项目主人确认以下现场验收范围已完成：

```text
1. RTX 4060 真实遥测与失败路径。
2. nvidia-smi 不可用时的 unavailable/null 表达。
3. bge-m3 主模型调用。
4. nomic-embed-text 备用模型回退。
5. Qdrant 维度冲突保护与 lexical retrieval 保留。
6. Auto Review 本地模型主/备角色。
7. 8766 Token 鉴权与 Tauri 连接。
8. Desktop 隐藏窗口暂停、恢复、退避和布局。
9. SHADOW 评估后候选、Obsidian 和 Qdrant 不发生自动变更。
```

验收结论来源为项目主人现场确认。没有附加逐项原始日志时，不记录未提供的精确数值或命令输出。

Issue #23 已按 `completed` 关闭。

## 12. 关键文档

```text
docs/MODULES/P2_09A_RUNTIME_TRUTH.md
docs/MODULES/P2_09B_CANONICAL_IDEMPOTENCY.md
docs/MODULES/P2_09C_DESKTOP_DATA_LAYER.md
docs/MODULES/P2_09D_DESKTOP_UX_AUTO_REVIEW.md
docs/MODULES/P2_08A_AUTO_REVIEW_CORE.md
docs/MODULES/P2_08B_LOCAL_AI_REVIEWER.md
docs/MODULES/P2_08B_SHADOW_API.md
docs/TECH_RESEARCH/P2_08_STANDALONE_TO_LINGJI_MAPPING.md
docs/TEST_REPORTS/P2_08_P2_09_INTEGRATION_TEST_REPORT.md
```

## 13. 下一步

```text
保持 Auto Review 为 SHADOW
-> 积累主人反馈和审计样本
-> 评估误判率、风险分布与人工审核节省量
-> 在足够样本和独立设计评审前不开发 ACTIVE
```
