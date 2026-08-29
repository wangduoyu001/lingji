# Task 1 — Safe Mac Codex Discovery and Rollout Import

## Result

`DONE_WITH_CONCERNS`

Implemented bounded Darwin Codex rollout discovery, streaming/fail-closed
rollout extraction, existing registry/bootstrap/API wiring, authorization path
policy, and owner-facing source actions. No live application, Acceptance root,
Production/Vault, or owner data was accessed.

## TDD evidence

- RED discovery command: `./.venv/bin/pytest -q tests/test_owner_real_history_discovery.py --tb=short`
  could not execute because this worktree has no `.venv`; equivalent
  `python3 -m pytest -q ...` produced `2 failed` for the missing Darwin
  candidates and unsupported `codex_rollout` enumeration.
- RED rollout command: `python3 -m pytest -q tests/test_owner_codex_rollout_adapter.py --tb=short`
  produced collection failure because `CodexRolloutAdapter` did not exist.
- GREEN focused command:
  `python3 -m pytest -q tests/test_owner_real_history_discovery.py tests/test_owner_codex_rollout_adapter.py tests/test_owner_real_history_import_flow.py tests/test_automatic_memory_discovery.py tests/test_automatic_memory_runtime_flow.py tests/test_automatic_memory_control_api.py tests/test_automatic_memory_adapters.py --tb=short`
  → `70 passed, 3 warnings`.
- Static checks: `python3 -m compileall -q src/automatic_memory src/extraction src/control`
  and `git diff --check` → pass.

## Implemented behavior

- Darwin-only discovery emits the exact `~/.codex/sessions` and
  `~/.codex/archived_sessions` candidates with nullable file/byte/mtime
  inventory, using metadata-only `stat` and bounded traversal.
- Symlink roots/files, sensitive names, arbitrary roots, and non-rollout files
  are rejected; non-Darwin configured-path behavior remains compatible.
- `codex_rollout` streams JSONL records, recognizes session identity from
  `session_meta.payload.id/session_id`, accepts only explicit user/assistant
  messages, deduplicates stable/event copies, preserves content/provenance
  hashes and external identities, and ignores tools, reasoning, world state,
  configuration and malformed/truncated records.
- Adapter is registered in the existing extraction registry and packaged
  bootstrap; automatic snapshots reuse the existing snapshot/queue/structured
  sink and source lifecycle authority.
- Source API exposes structured owner actions; Desktop shows Codex file count
  and `允许接管 Codex`, always exposes ChatGPT `选择官方导出目录`, and keeps
  unsupported Claude without a next-step heading or fake action.

## Concerns / limits

- Desktop rendered E2E/build and the requested 23-script smoke suite were not
  run because `desktop/lingji-control/node_modules` is absent in this worktree;
  no dependency installation was performed.
- Full/release validation and physical owner acceptance are intentionally out
  of scope while `LOCAL_EXECUTION_TASK.md` is IDLE.
