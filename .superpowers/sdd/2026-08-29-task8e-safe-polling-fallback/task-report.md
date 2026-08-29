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

- `Settings.automatic_memory_event_watcher_enabled` is tri-state: unset resolves to periodic mode
  on Darwin and preserves event-watcher mode elsewhere; explicit true/false always wins.
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

## Repair Round 1 disposition

The independent review identified two Important findings and three evidence gaps. This round
keeps the existing scheduler and source lifecycle boundaries and adds no new data authority.

- Platform policy is centralized in `src/automatic_memory/policy.py`. With no explicit setting,
  Darwin resolves to periodic reconciliation and Windows/non-Darwin resolves to the historical
  event watcher. `AutomaticMemoryRuntime` accepts an injectable `platform_provider`; an explicit
  `automatic_memory_event_watcher_enabled` setting always wins.
- Runtime and summary API responses now carry the configured reconciliation interval and maximum
  change-detection delay. The source UI uses an executable pure helper: 60/900/1800 seconds render
  as 1/15/30 minutes, while missing/invalid intervals render “尚未获得”; event mode renders no
  periodic notice.
- Tests now cover two quiet reconciliation periods with zero event scans, scheduled discovery,
  pause/resume/restart, revoke, runtime/API parity, platform defaults and overrides. The Desktop
  smoke executes the interval/copy helper for each mode instead of relying only on copy regexes.
- `docs/PROJECT_STATUS.md` now records the platform split, truthful 15-minute default, 30-second
  SLA limitation, and continuing Phase 1 `BLOCKED` disposition.

Repair Round 1 product/test commit is `cf09946102d89ddf67f3f69bae79f7bd45180dfe`; the docs
commit follows after final verification. No live app, package, install, Artifact, Production/Vault,
or owner data was used.
