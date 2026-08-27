# Phase 1 Product Landing — Task 3 Independent Review

Review target: `codex/phase1-automatic-memory` at `0d7bb84` (product/test commit `bc3636a`, evidence/docs commit `0d7bb84`). This is a read-only review; no live 8766 service, Artifact/release, Production Vault, or owner data was used.

## Verification performed

- Read the repository instructions, Task 3 brief/report, phase plan (including Global Rules, final Task 2 disposition, and Task 3), review diff `b36c597..0d7bb84`, authority documents, affected source/callers, and tests.
- `./.venv/bin/python -m pytest -q tests/test_automatic_memory_discovery.py tests/test_automatic_memory_runtime_flow.py tests/test_automatic_memory_work_fact.py tests/test_automatic_memory_obsidian.py tests/test_automatic_memory_control_api.py tests/test_extraction_worker.py --tb=short` — **24 passed, 1 warning**.
- Unfiltered direct matrix from the report (`tests/test_automatic_memory_runtime.py tests/test_packaged_control_api.py tests/test_automatic_memory_scheduler.py tests/test_automatic_memory_resume.py tests/test_automatic_memory_snapshot.py tests/test_extraction_worker.py tests/test_extraction_idempotency.py tests/test_automatic_memory_adapters.py` plus the Task 3 tests) — **195 passed, 1 failed, 7 warnings**. The failure is `test_automatic_memory_scheduler.py::test_daily_integrity_job_runs_without_event`; the reported `-k 'not daily_integrity_job_runs_without_event'` run has **1 deselected**. This is disclosed and matches the preserved Task 2 stale `integrity_seconds` timing edge, but the deselected run is not full proof.
- `./.venv/bin/python -m compileall -q src ...` — pass.
- `git diff --check` — **fails** on trailing whitespace in `task-3-report.md` lines 3–5.
- `./.venv/bin/python scripts/check_acceptance_sync.py` — pass (no product-impacting changes detected); `./.venv/bin/python scripts/check_local_execution_handoff.py` — pass (`IDLE`).
- Read-only probes in temporary directories reproduced the queue, Obsidian, sensitive-file, route, repeated-scan, and Work Fact findings below.

## Findings

### Important

#### I1 — Unauthorized internal snapshot jobs are re-leased indefinitely

Location: `src/extraction/pipeline.py:412-431` and `:498-519`; regression expectation `tests/test_extraction_worker.py:60-76`.

`_execute_internal_snapshot()` raises `PermissionError` when a source is missing/revoked, but both consumers call `release_claim()` and return the job to `queued`. Reproduction with one `automatic_memory_snapshot` payload containing `source_id='missing'`, followed by three `process_job()` calls, printed `queued queued awaiting authorization` on every iteration. `process_pending()` therefore repeatedly claims and releases the same unsupported job and can starve valid jobs. Task 3 requires malformed/unsupported internal jobs to fail closed and not remain queued. Minimal repair: terminal-fail or durable-quarantine invalid/deauthorized internal metadata and notify lifecycle; retain a bounded, explicitly distinguished retry only for genuinely transient authorization failures.

#### I2 — Ordinary Obsidian note bodies are read before exclusion

Location: `src/automatic_memory/path_policy.py:56-59`, `src/obsidian/discovery.py:158-160`, `src/obsidian/memory_scope.py:104-131`.

The Obsidian path policy invokes recursive `discover_memory_paths()`. `iter_markdown()` sends every markdown file through `decide()`, whose no-frontmatter path executes `candidate.read_text()` before it decides `excluded_ordinary`. A monkeypatched `Path.read_text` probe containing an ordinary `03-Knowledge/ordinary.md` and managed `_LingJi/Memory Inbox/managed.md` selected only the managed file but recorded reads of **both** files. This violates the explicit “ordinary Obsidian notes remain unread” boundary even though ordinary files are omitted from output. Minimal repair: enumerate managed directories without opening ordinary files; if `lingji_memory: true` support is retained outside them, use a bounded frontmatter-only read or an explicit precomputed allowlist, never a full body read.

#### I3 — Generic sensitive JSON files pass the path allowlist

Location: `src/automatic_memory/path_policy.py:14,33-37,63-73`.

`_sensitive()` only matches an exact filename in `_SENSITIVE_NAMES` or a database suffix. In an authorized `generic_ai_history` root, a probe with `credentials.json`, `auth-token.json`, `cookie.json`, `private.json`, and `safe.json` returned all five files. The policy and report claim credential/auth/token/cookie/private exclusion; these files can consequently reach an adapter and be read. Minimal repair: reject sensitive name components/prefixes/suffixes robustly (case-folded, separator-aware), and add generic-source tests for these forms rather than only exact names.

#### I4 — Repeated-scan idempotency evidence is vacuous, and the production count is false

Location: `tests/test_automatic_memory_runtime_flow.py:91-93`; `src/automatic_memory/checkpoint.py:318-350`; `src/extraction/queue.py:662-666`.

`test_repeated_snapshot_scan_reuses_idempotent_job()` only calls the single-scan test helper; it never starts a second scan or asserts duplicate counts. A real two-scan temporary-source probe produced two completed scans, **one** extraction row, and one structured source/conversation/message set, but both reports said `queued: 1`; the second Work Fact summary said `已处理 0 个来源文件` because its scan had no job row. The runner increments `processed` unconditionally even when queue admission returns an existing idempotent row. This fails truthful counts and leaves the claimed duplicate-zero proof absent. Minimal repair: distinguish inserted versus reused queue admission, report `queued` only for a new row (with a separate `reused` count if desired), and make the test execute both scans and assert durable queue/read-model counts and stable identities.

#### I5 — `/api/automatic-memory/scan` creates a running scan without a run-now scheduler action

Location: `src/control/automatic_memory_api.py:86-89`; comparison `src/automatic_memory/runtime.py:275-298`.

The existing packaged composition does correctly inject the service registry into `AutomaticMemoryRuntime`, and authorization lifecycle listeners are connected. However, the authenticated scan route calls `registry.start_scan()` directly rather than `runtime.scan_now()`/an equivalent scheduler-aware immediate action. After a source had already completed its startup scan, a route-equivalent call returned `status: running`; after 0.2 seconds the new scan was still `running` with no queue/work admission, relying on the regular scheduler interval. Thus the visible “scan” action can leave a durable unconsumed scan and does not provide the required real immediate action/Work Fact. Minimal repair: dispatch through the composed runtime’s scheduler `scan_now()` and return its report/work ID; when runtime is absent, reject the action rather than creating a durable unconsumed scan.

#### I6 — Work Fact source identity and terminal status are inconsistent

Location: `src/automatic_memory/runtime.py:311-329`; `src/work/store.py:106,328`.

The runtime correctly derives one `automatic-memory:{scan_id}` ID, but creates `WorkItem(... source_id=scan_id, status='accepted')` rather than the actual `source_id`, and no transition updates `work_items.status` when the outcome becomes completed/failed. A real two-scan probe returned Work Items with `source_id` equal to each scan ID and `status='accepted'`, while the projected outcome was `completed`. This makes source lookup and current-work status disagree with the terminal fact and weakens the required truthful Work Fact/API projection. Minimal repair: persist the actual source identity, update the existing Work Item status through the existing WorkStore transition path, and assert start/progress/terminal/API consistency.

#### I7 — Report/evidence commit metadata is stale and acceptance documentation is not truthful

Location: `.superpowers/sdd/2026-08-27-phase1-product-landing/task-3-report.md:5-6`; `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md:1704`.

The report says `Evidence/docs commit: pending` and the acceptance log says `报告/文档提交：待提交`, but the checked-out HEAD is already `0d7bb84` (`docs: record automatic memory ingestion evidence`), containing those docs. The review target must record this truthfulness defect. Minimal repair: update both authoritative entries to the exact docs commit (while not self-referencing this new review file).

#### I8 — Automatic internal extraction writes generated chat documents into the configured Obsidian Vault

Location: `src/extraction/bootstrap.py:29-51`, `src/extraction/pipeline.py:475-480`, `src/extraction/sink.py:387-402`, `src/extraction/adapters/generic_ai_history.py:138-155`.

The internal snapshot consumer invokes the existing `VaultExtractionSink`; bootstrap constructs it with `VaultLayout(settings.vault_path)`, and generic AI history emits `destination='source_archive'`, which resolves under that Vault. This is the real authorized Vault setting, not a separate LingJi internal vault. The current architecture documents a “Vault source documents” flow, but the phase boundary also says “No automatic publishing” and the Task 3/plan boundary says Obsidian is a manual memory interface and ordinary Vault content must remain untouched. This implementation therefore needs an explicit boundary decision before acceptance: if source archives are allowed as rebuildable source evidence, the brief/report must say so precisely; if “no automatic publishing” is binding, this is an Important owner-data/scope violation. Minimal repair under the latter interpretation: keep raw and structured read-model persistence through existing components but do not call the Vault document sink for automatic-memory chat snapshots (or route only to an explicitly managed non-formal source-evidence destination).

### Minor / observations

- Discovery uses `available` rather than the plan/UI vocabulary `detected`; tests only accept the implementation vocabulary. Confirm the DTO/state contract before Task 4.
- `git diff --check` reports trailing whitespace in the report metadata.
- Existing focused tests assert that structured rows exist, but do not independently verify exact roles, citation/provenance, ordering, or repeated-scan counts. The direct scheduler failure is disclosed and the Task 2 degraded/needs-restart disposition was not silently changed.
- No automatic promotion seam was found invoked by Task 3 runtime/scheduler/worker paths; the five sentinel tests remain unreachable. No second store, queue, parser, API, config center, UI/retrieval/vector/quality-runner implementation was added.

## Verdict

Spec Compliance: **FAIL** (I1–I8 are open Important findings; the required PASS threshold is zero Critical/Important findings).

Task Quality: **NEEDS_FIXES**. The focused tests pass, but the unfiltered direct matrix has one disclosed failure, the repeated-scan proof is vacuous, and the production boundary/count/terminal-state defects require repair and retest.
