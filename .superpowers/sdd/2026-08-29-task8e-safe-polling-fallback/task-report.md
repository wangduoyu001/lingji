# Task8E Safe Polling Fallback

## Verdict

`IMPLEMENTED_FOCUSED_PASS / READY_FOR_ROOT_ACCEPTANCE`

This worktree implements the conservative macOS automatic-memory fallback. The formal runtime
defaults to periodic reconciliation and does not start `watchfiles` event admission. Startup
incremental reconciliation, the persisted 15-minute reconciliation job, daily integrity job,
manual immediate scan, authorization, and revoke remain on the existing scheduler/registry path.

The fallback explicitly does **not** satisfy the 30-second event SLA. It provides automatic
change discovery at the next scheduled reconciliation, at most 15 minutes in the production
configuration. Phase 1 automatic takeover remains `BLOCKED` pending the root agent's separately
authorized real macOS observation.

## Scope and safety boundary

- Base: `c70ce6b165213151ca02baf34ff11e2217a21c82`.
- Product/test commits: `6862c46bd9718998235d42cf7a29a7e02ea7ea95` and
  `eff22b4ea3476088f32a87f7b90b4fcf330b75d2`.
- Branch: `codex/task8e-safe-polling-fallback`.
- Worktree: `/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/task8e-safe-polling-fallback`.
- No watcher algorithm repair, deletion invalidation, read-model seam, new queue/database,
  retrieval change, memory architecture change, or ordinary Obsidian reads were introduced.
- No package/install/live app/Acceptance root/Production/Vault/owner data was used.

## TDD evidence

### RED

`tests/test_task8e_safe_polling_fallback.py` was run against the clean base before the fallback
implementation:

```text
3 failed
TypeError: AutomaticMemoryScheduler.__init__() got an unexpected keyword argument 'event_watcher_enabled'
```

This proves the new contract was absent at the baseline rather than passing accidentally.
The UI contract smoke was also run before wiring and failed on the missing periodic copy.

### GREEN

After the minimal implementation:

```text
tests/test_task8e_safe_polling_fallback.py                 3 passed
affected automatic-memory backend matrix                    72 passed, 1 warning
desktop automatic-memory sources repair smoke              PASS
desktop 23-script smoke                                    PASS (23 scripts)
desktop TypeScript/Vite build                              PASS
compileall and git diff --check                            PASS
check_acceptance_sync.py                                   PASS
check_local_execution_handoff.py                           PASS
```

The fallback tests verify that event watcher start is not called, startup reconciliation and
daily integrity jobs remain registered, manual scan still runs, scheduled jobs remain executable,
revoke prevents subsequent scan admission, and the runtime mode is `periodic_reconciliation`.

## Implementation summary

- `Settings.automatic_memory_event_watcher_enabled` defaults to `False`.
- `AutomaticMemoryRuntime` passes that setting into the existing scheduler and exposes
  `automation_mode`, `event_watcher_enabled`, and `next_reconciliation_seconds` in the existing
  runtime status DTO.
- `AutomaticMemoryScheduler` skips watcher start/pause/resume/stop lifecycle calls when fallback
  is disabled, while retaining the existing watcher for explicit compatibility/test injection.
- Existing reconciliation and integrity Cron jobs are unchanged; reconciliation remains the
  correctness mechanism and manual `scan_now` remains unchanged.
- Existing Memory Sources UI renders a truthful periodic-mode notice: startup incremental scan,
  automatic checking, and latest discovery within 15 minutes. It contains no 30-second realtime
  takeover claim.
- The summary API uses scheduled-reconciliation wording in periodic mode.

## Not executed

Packaging, installation, release, live 8766/8767, real macOS Desktop observation, Production or
Vault access, and owner confirmation were intentionally not executed. Those remain root-agent
scope and are not implied by this focused pass.

## Changed files

Product/test commits `6862c46bd9718998235d42cf7a29a7e02ea7ea95` and
`eff22b4ea3476088f32a87f7b90b4fcf330b75d2` contain:

- `src/automatic_memory/scheduler.py`
- `src/automatic_memory/runtime.py`
- `src/config.py`
- `src/control/automatic_memory_api.py`
- `desktop/lingji-control/src/pages/MemorySourcesPage.tsx`
- `desktop/lingji-control/src/pages/memorySourcesTypes.ts`
- `desktop/lingji-control/scripts/automatic-memory-sources-repair-smoke.mjs`
- `tests/test_task8e_safe_polling_fallback.py`
- `tests/test_automatic_memory_scheduler.py`

The acceptance log, implementation plan, and this report are committed separately as the docs
commit after the product/test commit.
