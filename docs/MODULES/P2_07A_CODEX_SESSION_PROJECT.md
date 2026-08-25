# P2-07A Project Resolver + Codex Session Bridge

> 文档角色：历史实施/验证快照，不是当前进度或当前架构权威。
> 当前状态看 `docs/PROJECT_STATUS.md`；当前代码入口看 `docs/MODULES/CODE_MAP.md`。

> Updated: 2026-07-21
> Branch: `work/p2-07a-codex-session-project`
> Base Commit: `8b033eba1be6d4e7509a763b8333299672d2161b`
> Status: `IMPLEMENTED_NOT_TESTED`
> Merge State: `NOT_MERGED_AWAITING_COORDINATED_REVIEW`

## 1. 目标

P2-07A 建立 Codex 主动、显式、可控的项目与会话入口，不读取 Codex 未公开数据库或私有缓存：

```text
Codex
-> LingJi MCP
-> ProjectResolver
-> CodexSessionService
-> Existing ExtractionPipeline
-> Raw JSONL Session Archive
-> StructuredSource / Conversation / Message
-> SourceReadModel
```

完整会话事件流只保存一份 Raw JSONL，不复制为 Obsidian Transcript，不自动创建 Core Memory。

## 2. 项目识别优先级

```text
1. 最近父目录的 .lingji/project.yaml
2. project_registry.json 中的本机绑定
3. Git remote + git common dir
4. UNASSIGNED
```

Manifest 合同：

```text
schema_version = 1
project_id 以 LJ-PROJ- 开头
privacy = public | private | restricted
```

无法确认 Git 身份且没有 Manifest/Registry 绑定时：

```text
state = unassigned
project_id = ""
```

不会根据文件夹名或聊天内容猜项目，也不会直接用绝对路径生成永久 ID。

## 3. Worktree 归一化

`ProjectResolver` 执行：

```text
git rev-parse --show-toplevel
git rev-parse --git-common-dir
git remote get-url origin
git branch --show-current
```

同一 Git Common Dir 或同一已确认 Repository 的不同 Worktree 会归到同一个 `project_id`。本机可重建 Registry 位于：

```text
<storage_path>/project_registry.json
```

Registry 原子写入、稳定排序、Root 去重；损坏时记录日志并稳定降级为空 Registry。用户 DTO 只返回掩码后的 `path_display`。

## 4. Session 数据流

`CodexSessionService` 提供：

```text
resolve_project
start_session
checkpoint
close_session
get_session
list_sessions
activity
```

调用方提供 `external_session_id` 时，稳定 `session_id` 基于：

```text
project_id + external_session_id
```

否则使用随机种子生成 `LJ-CODEX-SESSION-<hash>`。

事件先写 Raw Archive，写入成功后才进入 Structured Ingestion。相同 `event_id` 不重复追加；相同 `content_hash` 会返回重复内容引用。关闭后的 Session 拒绝新 Checkpoint。

## 5. Raw 存储

唯一原始事件流：

```text
<storage_path>/raw/codex/sessions/<project-id>/<session-id>.jsonl
```

合同：

- UTF-8，一行一个规范化事件。
- 进程内文件锁。
- 追加后 flush + fsync。
- 追加前检查 event_id。
- 读取时忽略最后一行不完整 JSON。
- Raw Reference 只使用 `raw:codex/sessions/...jsonl`，不返回绝对路径。

没有新增 Session SQLite 表、Project SQLite 表、第二套 JSON 原始文件或第二套 Pipeline。

## 6. Structured Source 映射

Adapter：

```text
src/extraction/adapters/codex_session.py::CodexSessionAdapter
name = codex_session
source_types = codex_session
```

输出：

```text
ExtractionBatch(documents=(), structured_sources=(...))
```

因此不会生成 Obsidian Transcript。

映射：

```text
StructuredSource.external_id = codex:<project_id>
StructuredConversation.external_id = session_id
StructuredMessage.external_id = event_id
```

Source / Conversation / Message 继承同一 `project_id`，Agent Scope 为 `codex` 与 `lingji-local`。Message 保存脱敏后的阶段摘要与 Raw Reference。Metadata 只保留 branch、worktree_name、checkpoint_kind、basename changed_files、commits、test_status 和 blockers 等安全字段。

## 7. MCP 工具

新增：

```text
lingji_resolve_project
lingji_start_session
lingji_checkpoint
lingji_close_session
```

四个工具共用 `create_mcp_server()` 已创建的 Extraction Pipeline。工具签名不接受任意 Vault 路径，不提供 Core Memory 写入能力。

## 8. Local Control API

独立注册函数：

```text
src/control/codex_api.py::register_codex_routes(app, codex_service, token_validator)
```

计划路由已实现，但本阶段没有修改 `src/control/api.py` 或 `src/control/service.py`，正式装配留给集成阶段。

路由：

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
```

所有路由依赖调用方提供的 `token_validator`。稳定业务错误保留错误码；未知异常仅写 logger，对外返回固定摘要。

## 9. Activity Event

事件类型：

```text
PROJECT_RESOLVED
SESSION_STARTED
CHECKPOINT_RECEIVED
SOURCE_ARCHIVED
CONVERSATION_INDEXED
SESSION_CLOSED
FAILED
```

Audit/Activity 写入失败只记录 `logger.exception`，不回滚已经成功的 Raw 或 Structured 操作。用户事件 DTO 不包含绝对路径和敏感正文。

## 10. 脱敏

递归处理敏感键和值：

```text
api_key / token / password / secret
authorization / cookie / private_key
sk-*
Bearer *
```

完整环境变量、完整命令输出和本机绝对路径不会写入 Session Event 或 Structured Metadata。

## 11. 修改文件

```text
src/project_context/
src/codex_sessions/
src/extraction/adapters/codex_session.py
src/extraction/adapters/__init__.py
src/extraction/bootstrap.py
src/control/codex_api.py
src/mcp_server.py
tests/test_project_context.py
tests/test_codex_session_service.py
tests/test_codex_session_adapter.py
tests/test_codex_session_api.py
tests/test_codex_mcp_tools.py
```

未修改数据库 Schema、SourceReadModel、Memory Gateway、Obsidian、Desktop、`src/control/api.py` 或 `src/control/service.py`。

## 12. 已知限制

1. `register_codex_routes(...)` 尚未装配进正式 Local Control API，这是任务明确的集成阶段边界。
2. 当前只提供主动 MCP/API Checkpoint，不监听键盘、剪贴板、文件夹或 Codex 私有缓存。
3. Session 列表从 JSONL 重建，数量很大时后续可增加可重建索引，但本阶段不新增表。
4. 完整指定测试套件尚未在权威完整工作树执行。

## 13. 回滚

协调合并前可直接放弃分支。需要逐提交回滚时，按相反顺序 revert 文档、测试、MCP/API、Session/Adapter、ProjectResolver 提交。没有数据库迁移或 Obsidian Transcript 需要清理。

## 14. 提交

```text
9edfe02025b3c762698cba8b1e3ad3b705b33a8d
feat(project): add project manifest and worktree resolver

91b4d99e75ce630490d094e8c07da1ac7e65bb73
feat(codex): add durable session archive and structured mapping

16301267c7473c74a2529ef418c5d575a4b1e0ea
feat(mcp): expose codex session bridge

f53dfc3fcce16e235f22d66c3c008444c61a4bf7
test(codex): cover project and session contracts
```

最终文档提交 SHA 以分支最终 HEAD 为准。
