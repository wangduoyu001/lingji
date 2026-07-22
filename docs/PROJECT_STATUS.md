# PROJECT_STATUS.md — LingJi 项目实时状态

> Updated（更新时间）: 2026-07-22  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> Formal Head（正式提交）: `325ad6e4a5f9d2c21bc4441039f32a28292b0f1d`  
> P2-08 Status: `MERGED_AND_VALIDATED`  
> P2-09 Status: `MERGED_AND_VALIDATED`  
> P2-10A Status: `MERGED_AND_CI_VALIDATED`

## 1. 当前结论

P2-08 Auto Review SHADOW、P2-09 Runtime/Desktop Reliability 与 P2-10A Owner-visible Settings Governance Core 已进入正式功能分支。

```text
PR #24  P2-09A Runtime Truth                         MERGED
PR #25  P2-09B Canonical Idempotency + MCP Queue     MERGED
PR #26  P2-09C Desktop Polling Data Layer             MERGED
PR #27  P2-08A Deterministic Auto Review Core         MERGED
PR #28  P2-08B Local AI Reviewer + SHADOW API         MERGED
PR #29  P2-09D Desktop UX + SHADOW Dashboard          MERGED
PR #30  Combined Integration Verification             MERGED
PR #31  P2-08/P2-09 Documentation Sync                MERGED
PR #32  P2-08/P2-09 Local Acceptance Closeout         MERGED
PR #33  P2-10A Settings Governance Core               MERGED
```

P2-10A 最终门禁：

```text
tests workflow #709: SUCCESS
P0 Windows Gate #102: SUCCESS
Python 3.11: SUCCESS
Python 3.12: SUCCESS
Windows full tests: SUCCESS
14-script Desktop smoke: SUCCESS
React/Vite build: SUCCESS
Tauri Rust check: SUCCESS
MCP smoke: SUCCESS
Browser capture smoke: SUCCESS
Obsidian plugin smoke: SUCCESS
```

P2-10A 完成的是设置治理代码底座。完整 Desktop 视觉重设计与信息层级优化尚未开始，不得把“代码合同稳定”写成“UI 已完成”。

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
- Desktop 只通过认证的8766 Local Control API访问后端。
- `second_brain/` 不接收新的正式产品能力。
- Obsidian CLI正式实现位于 `src/obsidian/`。
- MCP默认使用stdio；可选HTTP使用8767。

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
P2-10A Owner-visible Settings Governance Core     MERGED_AND_CI_VALIDATED
```

## 5. P2-10A 设置治理结论

后端正式权威：

```text
src/control/runtime_settings.py
= 兼容持久化与基础类型校验

src/control/settings_governance.py::OwnerSettingsRegistry
= 推荐值、影响、风险、能力状态、预览与确认合同

src/control/settings_catalog.py::CompleteOwnerSettingsRegistry
= 当前完整主人可见设置目录

src/control/governed_service.py::GovernedLocalControlService
= 正式8766运行服务
```

Desktop 不再复制：

- 设置默认值。
- 分组标签。
- 推荐值。
- 风险等级。
- 性能、存储、费用和隐私影响。
- Provider可用性原因。

这些内容全部由认证的 `/api/settings` 返回。

## 6. 设置变更流程

正式流程：

```text
Desktop Draft
-> 只收集 dirty values
-> POST /api/settings/preview
-> 后端类型与跨字段校验
-> 返回当前值/目标值/默认值/推荐值/影响/风险
-> 高风险变更要求主人确认
-> POST /api/settings/commit
-> 写入既有 runtime_settings.json
-> 写入既有 Audit Event
```

新增认证接口：

```text
POST /api/settings/preview
POST /api/settings/commit
```

既有接口继续保留：

```text
GET  /api/settings
PATCH /api/settings
POST /api/settings/reset
```

正式 Desktop 高风险流程不能绕过 Preview 与 Confirmation。

## 7. 高风险设置合同

当前高风险示例：

- 开启自动清理。
- 修改冷存储路径。
- 修改明确的 Obsidian Vault 路径。

高风险提交要求后端确认短语：

```text
CONFIRM_HIGH_RISK_SETTINGS
```

该短语只是交互确认合同，不是密钥，也不能替代8766 Token。

## 8. 跨字段与能力校验

当前阻止：

- 自动转写开启但 ASR Provider 为 `off`。
- 自动 OCR 开启但 OCR Provider 为 `off`。
- 镜头检测开启但 Scene Provider 为 `off`。
- 冷存储开启但未选择目录。

能力不可用时设置仍可见，并返回：

```text
availability_state
disabled_reason
optional_requirements
```

加载设置页不会为了显示状态而执行耗时的外部 Obsidian CLI 命令。

## 9. Auto Review 设置治理

P2-08新增设置已进入主人可见 Registry：

```text
auto_review_mode
auto_review_ai_enabled
auto_review_timeout_seconds
```

`auto_review_mode` 只允许：

```text
OFF
SHADOW
```

ACTIVE不进入选项。若环境配置错误写成ACTIVE，设置目录回落OFF；执行层仍继续拒绝ACTIVE。

## 10. Desktop 设置代码结构

```text
desktop/lingji-control/src/pages/settingsTypes.ts
= 后端合同类型

desktop/lingji-control/src/pages/settingsApi.ts
= API客户端

desktop/lingji-control/src/pages/useSettingsController.ts
= 草稿、预览、确认、提交、重置和离开保护

desktop/lingji-control/src/pages/SettingsPage.tsx
= 搜索、筛选和页面编排

desktop/lingji-control/src/components/settings/SettingField.tsx
= 单个设置项渲染
```

已实现：

- 全局搜索。
- 只显示已修改。
- 只看高风险。
- 只看不可用。
- 单项恢复默认。
- 分组恢复默认。
- 未保存草稿离开提示。
- 手动重新加载确认。
- 重置单项时保留其他未保存草稿。
- 只提交真实变化项。

## 11. P2-09 Runtime Truth

- Brain Status 不再把未知GPU利用率伪装成0。
- 静态硬件信息与动态遥测分离。
- 动态遥测不可用时返回 `null`、`unavailable`、`stale` 与错误摘要。
- Embedding默认主模型为 `bge-m3`，备用为 `nomic-embed-text`。
- Qdrant维度不一致时阻止写入并标记 `rebuild_required`。

## 12. P2-08 Auto Review SHADOW

模式合同：

```text
OFF
SHADOW
ACTIVE  # 仅枚举存在，当前实现拒绝
```

Auto Review不得：

- 伪造 `owner_confirmed=True`。
- 修改候选状态。
- 写入Core Memory。
- 写入Obsidian。
- 写入Qdrant。
- 执行批准、拒绝、删除或合并。

## 13. 审核与写入权威

```text
MemoryReviewService
= 主人审核入口

MemoryLifecycleService
= 唯一正式生命周期写入器

Auto Review
= 只生成SHADOW决策和Audit Event
```

## 14. 安全状态

```text
自动 Qdrant Collection 删除/重建: NO
自动模型下载: NO
数据库 Schema 修改: NO
新数据库: NO
第二套配置文件: NO
第二套队列: NO
第二套生命周期: NO
第二套审计数据库: NO
rebase: NO
force push: NO
master 修改: NO
```

## 15. 关键文档

```text
docs/MODULES/P2_10A_SETTINGS_GOVERNANCE_CORE.md
docs/TEST_REPORTS/P2_10A_SETTINGS_GOVERNANCE_TEST_REPORT.md
docs/MODULES/P2_09A_RUNTIME_TRUTH.md
docs/MODULES/P2_09B_CANONICAL_IDEMPOTENCY.md
docs/MODULES/P2_09C_DESKTOP_DATA_LAYER.md
docs/MODULES/P2_09D_DESKTOP_UX_AUTO_REVIEW.md
docs/MODULES/P2_08A_AUTO_REVIEW_CORE.md
docs/MODULES/P2_08B_LOCAL_AI_REVIEWER.md
docs/MODULES/P2_08B_SHADOW_API.md
```

## 16. 下一步

```text
P2-10B Desktop UI / Information Architecture Refinement
-> 基于稳定设置合同设计页面层级
-> 重做总览、设置中心和全局状态语义
-> 不复制后端默认值或风险规则
-> 不开发ACTIVE
```
