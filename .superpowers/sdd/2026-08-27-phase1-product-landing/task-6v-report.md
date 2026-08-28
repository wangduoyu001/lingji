# Task 6V — Packaged Automatic-Memory Gate Closeout

日期：2026-08-28（Asia/Shanghai）  
工作树：`/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`  
产品 HEAD：`684398e2b56447203ff6b77b4e93cae2c07b38f2`

## Disposition

```text
Task6R focused: PASS (6 passed)
Task6V packaged: PASS (2 passed, 1 warning) x 2 independent invocations
Focused regression: PASS (376 passed, 3 warnings)
Desktop build/smokes: PASS
Desktop rendered E2E: PASS
Critical: 0
Important: 0
Automated disposition: AUTOMATED_ACCEPTED / READY_FOR_TASK7
Live/Artifact/release/Production/Vault/owner acceptance: NOT_RUN
```

## Packaged evidence

Command (run twice from fresh pytest temporary roots):

```text
./.venv/bin/pytest -q tests/integration/test_automatic_memory_packaged_flow.py --tb=short -x
run 1: 2 passed, 1 warning, 294.47s
run 2: 2 passed, 1 warning, 295.59s
```

Each invocation executes the ten packaged scenarios and separate 30%/70%
crash roots. The harness records verified 64-hex raw hashes, transient marker
inventory, logical source/scan/job/Work Fact identity and status sets,
structured message/version metadata, queue/duplicate counts, real killed and
recovery PIDs, child inventory, port rebind, preserved logs, and terminal
cleanup. Crash recovery waits for the measured crashed scan leases, then uses
production startup reconciliation with no manual scan fallback. Both roots
completed the original durable scan at `20/20` with 20 jobs and zero duplicates.

The packaged composition exercises Gateway/Hybrid, registered production MCP
search/context-pack, lexical fallback under injected semantic-client failure,
current/why fail-closed authority after revoke/expiry, history/as-of retention,
v1/v2 evidence version status and supersession, and heartbeat
instance/generation isolation after restart. Focused Task6H coverage supplies
the active Work Fact failure/degraded/recovery contract.

## Regression and Desktop evidence

The focused command covered Task6Q/H/S/A, Task6L/M/P/R, automatic-memory
runtime/scheduler/snapshot/resume/source/watcher/adapters/Control/MCP/context/
Work Fact, and Task4 reset regressions: `376 passed, 3 warnings`.

Desktop build, runtime, memory-source repair/source, Work Fact, memory-review
smokes, and rendered `e2e_owner_memory_flow` all passed. The rendered wait was
changed only in test code from `networkidle` to `domcontentloaded` plus the
existing landing-heading readiness assertion; authenticated polling makes
network-idle nondeterministic. No Desktop product code changed.

Additional checks passed:

```text
./.venv/bin/python -m compileall -q src tests
git diff --check
python scripts/check_acceptance_sync.py
python scripts/check_local_execution_handoff.py
```

Initial post-Task6R failures exposed only harness evidence defects:
authorization/pause ordering, root-derived identity normalization, and startup
recovery attempted before measured lease expiry. These were corrected in the
existing integration harness without modifying `src/` or weakening assertions.

This report is automated Acceptance evidence only. It does not approve release,
Artifact, live 8766/8767, Production/Vault, or owner acceptance.
`LOCAL_EXECUTION_TASK.md` remains `IDLE`.
