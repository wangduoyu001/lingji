# DEVELOPMENT_RULES.md — LingJi Development Rules

> Generated: 2026-07-20

## Branch Isolation

1. This worktree is on `feature/second-brain-memory`. Never modify or write runtime data into `C:\Users\Administrator\Documents\New project-ai`.
2. Before each Codex task, read `.codex/context/PROJECT_SUMMARY.md`, `ACTIVE_RULES.md`, `ARCHITECTURE.md`, `RECENT_DECISIONS.md`, and `KNOWN_ISSUES.md`.
3. If the API is available, call `POST http://127.0.0.1:8765/memory/context` before planning.
4. Do not add the second-brain service to `start_lingji.bat`, `start_lingji.py`, or `run_service.py`.

## Development Understanding Requirement

1. Before developing any new feature, first understand the existing project structure and related modules.
2. Do not create new files based only on feature names or assumptions.
3. Before code changes, record or confirm:
   - target module path
   - existing service/class/function entry points
   - data flow
   - API registration location
   - test location
4. Prefer existing project documentation and code maps over repeated repository scanning.
5. If the required code path is already documented, do not require Codex or local tools unless execution/testing is needed.

## Task Routing Requirement

1. Use the simplest capable method for every task.
2. Tasks that can be completed directly through repository documents, Markdown, planning, review, or small non-runtime changes should be completed directly without using Codex.
3. Do not use Codex for simple documentation edits, architecture notes, requirement整理, or other tasks that do not require a local environment.
4. If multiple simple tasks are known, complete them together instead of repeatedly creating separate execution tasks.
5. Use Codex only when local environment access is required, including:
   - running tests
   - checking real hardware
   - building applications
   - debugging runtime issues
   - validating local services
6. Use independent development agents for isolated coding tasks when they can modify code without blocking the main workflow.

## Data Boundaries

1. AI chat records are the **only** automatic memory source.
2. Obsidian content is manual formal knowledge — index it, but never auto-distill into memories.
3. The watcher may only scan the three configured roots: AI-chat inbox, Codex-task inbox, and Obsidian knowledge directory.
4. No drive-wide scanning.
5. All new runtime data stays on D: drive.

## Obsidian CLI Safety Rules

1. No deleting, overwriting, or batch-moving vault files without explicit approval.
2. Read existing notes before modifying them.
3. Batch operations must support dry-run.
4. Stop and output preview only if affecting >20 notes.
5. Create a Git checkpoint before modifying formal notes.
6. Use official Obsidian CLI (`Obsidian.com`) for daily single-note operations.
7. Allow direct Markdown read in vectorization, backup, Git, and offline scans.
8. Do not commit `.obsidian` cache, secrets, tokens, database files, or personal paths.
9. Do not auto-publish any content.
10. Re-read and verify after writing.
11. All auto-generated content must record source, generation time, and task ID.

## File Conventions

1. All Python files must use `encoding="utf-8"` (no BOM).
2. Read files with `encoding="utf-8-sig"` to handle legacy BOM.
3. Write files via `scripts/_exec.py` or Node.js MCP `fs.writeFileSync`.
4. PowerShell does not support `&&` piping or `<< heredoc`.

## Memory Management

1. Important memories remain `pending` until explicit approval.
2. Active memories are embedded in Qdrant for semantic search.
3. SQLite and raw archives are the sources of truth; Qdrant is rebuildable.
4. Superseded memories retain version history.

## Testing

1. After code changes, run existing tests: `python -m pytest tests/ -v`
2. Web UI projects must use Playwright for end-to-end verification.
3. Do not delete tests, skip tests, lower assertions, or fake results to pass.

## Knowledge Management

1. Capture First: new files get classified/tagged/summarized before opportunity analysis.
2. Only **knowledge_entry / ai_news / opportunity_entry** types get Frontmatter tags.
3. All generated content records source, generation time, and task_id.

## Python Conventions

1. Use type hints (`from __future__ import annotations`).
2. All public-facing tools must wrap results in `tool_result()` format.
3. Return `{ok, data, error, meta}` from all tool calls.
4. Keep logic layers light: Data → Index → Logic → Ops
