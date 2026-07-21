# P2-07 Codex-First Local Memory Loop

> Status: `VALIDATED_READY_FOR_FORMAL_MERGE`  
> Integration Branch: `work/p2-07-integrated-validation`  
> Functional Integration Head: `2b4ce6680564b06d86000325f75cc6874a8ccd63`  
> Validation Contract Head: `56819e1dca5d14e9a3b55f506784312089a0a2db`  
> Formal PR: `#22`

## 1. 目标

P2-07 把 Codex 的项目、Session、检查点、长期记忆候选、主人审核、Context Pack、Obsidian 安全操作和 Desktop 可视化接成一条本地闭环。

```text
Codex Workspace
-> Project Resolver
-> Codex Session JSONL
-> Existing Extraction Pipeline
-> Structured Source / Conversation / Message
-> Project Context Pack
-> Candidate Review / Core Memory
-> Memory Inspector / Desktop UI
```

P2-07 不读取 Codex 私有数据库，不保存完整 Transcript 到 Obsidian，不创建 Project/Session 数据库表，不自动晋升 Core Memory。

## 2. 集成顺序

```text
P2-07A merge -> 38e5e0fe3b3168bb665252638499ab6fb98c82df
P2-07B merge -> af4fb529893a34f971f51d162956993280cf4ded
P2-07C merge -> 2b4ce6680564b06d86000325f75cc6874a8ccd63
```

顺序固定为 A -> B -> C：

1. A 提供 Project Resolver、Codex Session、Structured 映射和 Codex API/MCP。
2. B 提供项目 Context、候选审核、Core Integrity 和 Obsidian Notes API。
3. C 在冻结后的 A/B 合同上接 Desktop 页面和快捷导航。

## 3. 数据权威

```text
<storage_path>/project_registry.json
= 本机 Project 绑定与 Worktree 归一化

<storage_path>/raw/codex/sessions/<project-id>/<session-id>.jsonl
= Codex Session 唯一原始事件流

Obsidian Vault + Git
= 长期记忆和正式知识正文权威

lingji_state.db
= Queue、Runtime State 和 Audit Event

lingji_memory.db + Structured Read Model + Qdrant
= 可重建派生索引
```

Codex Session Adapter 的 `documents=()`，不会生成完整对话 Obsidian 文档。没有第二份 Session Raw Snapshot。

## 4. Project Resolver

识别优先级：

```text
.lingji/project.yaml
-> Project Registry
-> Git remote + Git common dir
-> UNASSIGNED
```

同一 Git Repository 的多个 Worktree 归一到同一 Project。不能确认时返回 `unassigned`，不会根据文件夹名或正文猜测永久 Project ID。

用户 DTO 只返回脱敏后的 `path_display`，不返回完整绝对路径。

## 5. Codex Session

正式服务：

```text
src/codex_sessions/archive.py::CodexSessionArchive
src/codex_sessions/service.py::CodexSessionService
src/extraction/adapters/codex_session.py::CodexSessionAdapter
```

能力：

- Session start / checkpoint / close。
- `external_session_id` 幂等恢复。
- JSONL 进程内锁、flush、fsync、稳定 sequence。
- 最后一行损坏 JSON 稳定忽略。
- Session 关闭后继续 checkpoint 返回 409。
- Secret、Token、Cookie、Authorization 和绝对文件路径递归脱敏。
- 关闭 Session 只保存最终状态、摘要、决策和剩余任务，不自动晋升 Core Memory。

## 6. Project Context Pack

正式服务：

```text
src/project_memory/context_service.py::ProjectContextService
src/project_memory/runtime.py::build_project_context_service
```

顺序：

```text
Core Memory
-> Decisions
-> Active Tasks / Blockers
-> Recent Codex Sessions
-> Related Messages / Memory
```

默认严格按 Project、Privacy、Agent Scope、Status 和 Review Status 过滤。Codex 不允许跨项目读取。

已完成的 Codex Session 可进入 Recent Sessions；每项必须存在稳定 Source、Conversation、Message、Memory 或相对路径引用。

## 7. Memory Review 与 Core Integrity

正式服务：

```text
src/project_memory/review_service.py::MemoryReviewService
src/project_memory/integrity.py::CoreMemoryIntegrityService
src/project_memory/body_hash.py
```

支持：

- Candidate 列表、详情和分页筛选。
- Approve、Edit Approve、Reject。
- 主人手动新增长期记忆。
- Core Memory 逻辑归档。
- `healthy / external_modified / missing` 检测。
- `expected_content_hash` 乐观锁和 409 冲突。

所有写入继续复用现有 `MemoryLifecycleService`。没有第二套 Lifecycle，没有永久删除。

Markdown 正文哈希使用统一 canonical body 规则，避免 Frontmatter 分隔空行造成新文件立即被误判为外部修改。

批准、编辑批准和归档后通过正式 `PEMISIndex` 条目重建 Memory Gateway，不把 `build_index()` 的统计结果误当索引条目。

## 8. Obsidian 安全读写

正式服务：

```text
src/control/obsidian_notes_api.py::SafeObsidianNotesService
```

允许读取：

```text
01-Inbox
02-Sources
03-Knowledge
04-Projects
05-Operations
```

允许主人新建：

```text
01-Inbox/Manual
03-Knowledge/Notes
05-Operations/Tasks
```

明确拒绝：

```text
08-Private
03-Knowledge/Core-Memory
00-System
绝对路径
Windows 盘符路径
..
NUL
Vault 外路径
```

API 只返回相对路径。扫描变化不会启动自动监听。

## 9. 8766 Local Control API

生产入口：

```text
run_control_api.py
src/control/p2_07_api.py::register_p2_07_routes
```

P2-07 Runtime 使用懒加载：Control API 启动不会强制构造 Qdrant、Indexer 或 Codex Session Runtime。第一个 P2-07 请求到达时才构造共享服务；未授权请求在初始化前返回 401。

主要路由：

```text
POST /api/codex/projects/resolve
GET  /api/codex/projects
GET  /api/codex/current
POST /api/codex/sessions/start
POST /api/codex/sessions/{session_id}/checkpoint
POST /api/codex/sessions/{session_id}/close
GET  /api/codex/sessions
GET  /api/codex/sessions/{session_id}
GET  /api/activity

POST /api/context/project
GET  /api/memory/review/candidates
GET  /api/memory/review/candidates/{memory_id}
POST /api/memory/review/candidates/{memory_id}/approve
POST /api/memory/review/candidates/{memory_id}/edit-approve
POST /api/memory/review/candidates/{memory_id}/reject
POST /api/memory/core
POST /api/memory/core/{memory_id}/archive
GET  /api/memory/core/{memory_id}/integrity

GET  /api/obsidian/notes
POST /api/obsidian/notes
POST /api/obsidian/scan
```

所有 Desktop 请求继续使用 `X-LingJi-Token`。

## 10. MCP

正式入口：

```text
src/mcp_server.py
src/mcp/project_context_tools.py
```

新增：

```text
lingji_resolve_project
lingji_start_session
lingji_checkpoint
lingji_close_session
lingji_build_context
```

MCP 使用同一个 Extraction Pipeline 处理既有采集工具和 Codex Session，不构造第二套 Pipeline。

`lingji_build_context` 强制：

```text
agent_id = codex
allow_cross_project = false
```

## 11. Desktop UI

新增正式页面：

```text
项目与对话
记忆审核
```

扩展：

```text
总览 Current Work
Memory Inspector 快捷目标
Obsidian 读取、手动新建和扫描变化
```

关键实现：

```text
desktop/lingji-control/src/pages/CodexWorkspacePage.tsx
desktop/lingji-control/src/pages/MemoryReviewPage.tsx
desktop/lingji-control/src/pages/MemoryInspectorLoopPage.tsx
desktop/lingji-control/src/pages/ObsidianLoopPage.tsx
desktop/lingji-control/src/components/ObsidianOperations.tsx
```

Activity 轮询：

```text
有活动 Session: 1 秒
无活动 Session: 5 秒
页面 inactive: 停止
窗口隐藏: 停止
```

使用 AbortController、独立 request ID 和 `visibilitychange` 防止旧请求覆盖新状态。

Inspector 快捷目标会真正消费：

```text
project_id
source_type
source_id
conversation_id
message_id
memory_id
```

不把正文写入 URL 或 localStorage。

## 12. 集成阶段修复

协调审查修复了独立分支测试无法发现的问题：

- A/B/C DTO 字段与请求体不一致。
- Context Pack 的 `task` / `query` 命名不一致。
- Reject、Archive、Owner Memory 缺少 `owner_confirmed` 或 Hash。
- Core Integrity `current_hash` 与 UI `content_hash` 不一致。
- Obsidian 正文 Hash 口径不一致。
- 已完成 Session 被 Active-only 过滤。
- Index rebuild 使用了错误的返回值。
- Inspector 快捷参数只传递但未消费。
- 旧 Smoke 不认识 Wrapper Page 和 API Client 分层。
- Desktop Smoke 失败日志无法定位具体脚本。
- CI 未真实执行 Tauri `cargo check`。

## 13. 明确未实现

```text
完整 Transcript UI
Codex 私有数据库读取
自动监听 Vault
WebSocket / SSE
永久删除
自动 Core Memory 晋升
跨项目 Context Pack
GraphRAG
HMAC / Tombstone / 复杂 Merge
手机端和浏览器专用客户端
自动审查执行器
```

自动审查已单独登记为 `P2-08 Auto Review Shadow Layer`（Issue #23），不得混入 P2-07。

## 14. 回滚

- 移除 `run_control_api.py` 中 `register_p2_07_routes(...)` 可停止 8766 P2-07 路由装配。
- 移除 MCP 的 Project Context Tool 注册不会影响既有 Memory Gateway 工具。
- Codex JSONL、Project Registry 和 Obsidian Core Memory 相互独立，可保留数据后回滚 UI/API。
- 不需要数据库 Schema 回滚。

## 15. 完成标准

P2-07 只有在以下全部通过后才允许正式合并：

```text
Linux full pytest
Windows full pytest
Clean-install validation
compileall
Desktop named smoke suite
TypeScript/Vite build
Tauri cargo check
MCP smoke
P0 Windows Gate
```

完整数字见：

```text
docs/TEST_REPORTS/P2_07_INTEGRATED_VALIDATION_REPORT.md
```
