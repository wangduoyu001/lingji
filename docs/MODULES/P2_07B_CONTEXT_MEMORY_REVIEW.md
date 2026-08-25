# P2-07B Project Context Pack + Long-Term Memory Review

> 文档角色：历史实施/验证快照，不是当前进度或当前架构权威。
> 当前状态看 `docs/PROJECT_STATUS.md`；当前代码入口看 `docs/MODULES/CODE_MAP.md`。

> Status: `IMPLEMENTED_NOT_TESTED`

## Scope

- Project-scoped Context Pack with fixed section budgets and stable citations.
- Backward-compatible AI profile permissions; Codex remains current-project only and cannot read restricted memory.
- Owner candidate review reusing `MemoryLifecycleService`.
- Owner manual memory follows candidate then promotion workflow.
- Core memory logical archive and read-only integrity detection.
- Safe Obsidian manual reads and managed-note creation.
- Standalone route and MCP registration functions; no formal assembly in this branch.

## Context Sources

Order: approved Core Memory, active Decisions, active Tasks/Blockers, recent sessions, query-related messages/memory. Default filters require exact project, allowed privacy, active status, approved review status, and matching agent scope. Section budgets are 35/25/20/20 percent.

## Review and Integrity

Approval requires owner confirmation plus expected hash, records `approved_hash`, `approved_at`, and `approved_by`, then calls the supplied existing index synchronization callback. Rejection records a reason through the existing lifecycle. Archive is logical only. Integrity states are `healthy`, `external_modified`, and `missing`; inspection never overwrites a file.

## Obsidian Safety

Readable roots: `01-Inbox`, `02-Sources`, `03-Knowledge`, `04-Projects`, `05-Operations`. Writable roots: `01-Inbox/Manual`, `03-Knowledge/Notes`, `05-Operations/Tasks`. Absolute paths, drive paths, traversal, `08-Private`, Core Memory, and system paths are rejected.

## Integration

Exports only `register_project_memory_routes(...)`, `register_obsidian_note_routes(...)`, and `register_project_context_tools(...)`. `src/control/api.py` and `src/mcp_server.py` remain untouched.

## Rollback

Revert the five P2-07B commits. No schema migration or physical deletion is involved.
