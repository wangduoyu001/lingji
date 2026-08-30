# Task 1 — Owner UI menu fast-track report

## Status

Implemented in original product/tests commit `e9a341d9314a23cac3a81b30de989447496a6f01`,
with Repair Round 1 in product/tests commit `2784dfa`. Docs/evidence is committed separately.

## RED evidence

Tests were extended before production changes.

```text
$ npm run test:e2e:memory
AssertionError [ERR_ASSERTION]: advanced diagnostics must have one collapsed disclosure
0 !== 1
```

Exact result: `1 failed` (the rendered fixture stopped at the missing collapsed disclosure).

```text
$ node scripts/owner-ui-menu-fast-track-smoke.mjs
AssertionError [ERR_ASSERTION]: advanced diagnostics must be a single disclosure
0 !== 1
```

Exact result: `1 failed` (the focused Playwright-rendered DOM stopped at the same missing disclosure).
The initial smoke launch also exposed an encoded-workspace `spawn npm ENOENT`; the smoke runner was
corrected to resolve its workspace with `fileURLToPath` before the product RED was recorded.

## GREEN and regression evidence

```text
$ npm run test:e2e:memory
e2e_owner_memory_flow: PASS
```

```text
$ npm run test:owner-ui-menu-fast-track
owner-ui-menu-fast-track-smoke: PASS
```

```text
$ npm run test:smoke
[smoke] PASS (23 scripts)
```

```text
$ npm run build
✓ 96 modules transformed.
✓ built in 395ms
```

```text
$ python3 -m pytest -q tests/test_owner_memory_corrections.py tests/test_owner_memory_card_projector.py tests/test_owner_memory_card_api.py tests/test_memory_review_service.py tests/test_memory_inspector_api.py tests/test_memory_inspector_facade.py tests/test_project_memory_api.py tests/test_task3_round2_direct.py tests/test_task3_round3_integration.py tests/test_source_read_model.py tests/test_source_service.py --tb=short
87 passed, 1 warning in 1.43s
```

Additional checks: `python3 -m compileall -q src tests` PASS; `git diff --check` PASS.

## Scope and implementation

- Added a native collapsed `高级诊断` disclosure in the Desktop shell. Its only advanced action is
  `打开高级诊断`; the ordinary sidebar remains exactly `首页 / 记忆内容 / 需要我 / 记忆来源`.
- Added an owner-facing `下一步` panel on Home. Pending actions route to `需要我`; zero pending
  actions say `灵机会继续自动检查，你现在不用做任何事。`; unavailable pending data remains an
  honest retry state.
- Removed duplicate advanced links from ordinary Home and memory-card footers, leaving one visual
  advanced entry in the shell.
- Kept existing card fields, source truth metadata, owner correction/invalidation/archive/confirm
  actions, source authorization/scan actions, attention resolve action, keyboard/focus handling,
  and technical details behind existing disclosures.
- Extended the rendered owner fixture with the collapsed-entry, Home next-step, and complete-card
  field assertions; added `scripts/owner-ui-menu-fast-track-smoke.mjs` and its package command.

## Self-review

- Ordinary menu has exactly four labels in the required order.
- Advanced diagnostics is closed by default, keyboard/mouse-toggleable, visually secondary, and
  reachable through one action without removing legacy direct PageIds.
- Home, cards, sources, and attention are checked through rendered DOM; IDs, paths, JSON and
  internal English labels are excluded from ordinary assertions.
- Existing owner state/action matrices remain covered by `e2e_owner_memory_flow.mjs` and the
  owner-card/source Python matrix. No backend/API/data model/retrieval/vector/quality-gate files
  changed.
- 1024px and 1280px rendered overflow checks pass; no live service, real data, Vault, installation,
  release, or Artifact was touched.

## Not run / concerns

- Not run: live 8766/8767, Sidecar/release/Artifact/installation, Production/Vault, real owner data,
  or owner visual acceptance. Those remain outside this Task 1 code/evidence scope.
- Existing build output retains the pre-existing Vite dynamic-import warnings.
- `LOCAL_EXECUTION_TASK.md` remains `IDLE` and was not changed.

## Repair Round 1 — review Important items

The review identified six Important findings. The repair stayed within Desktop UI copy/rendering,
existing action wiring, rendered tests, and acceptance evidence; no backend/API/data model,
retrieval, vector, quality-gate, live service, real data, Production/Vault, installation, or
`LOCAL_EXECUTION_TASK.md` changes were made.

### RED evidence (tests before repair implementation)

The focused Playwright smoke was extended first with real rendered assertions for all six review
behaviors. The baseline stopped at the first failing assertion:

```text
$ npm run test:owner-ui-menu-fast-track
AssertionError [ERR_ASSERTION]: ordinary runtime warning must not expose the control port
true !== false
```

Exact result: `1 failed` assertion (Node stops after the first assertion; the remaining new
assertions were present in the same run but were not reached). This is the expected RED for the
baseline ordinary sidebar text.

### GREEN and regression evidence

```text
$ npm run test:owner-ui-menu-fast-track
owner-ui-menu-fast-track-smoke: PASS
```

```text
$ npm run test:e2e:memory
e2e_owner_memory_flow: PASS
```

```text
$ npm run test:smoke
[smoke] PASS (23 scripts)
```

```text
$ npm run build
✓ 96 modules transformed.
✓ built in 499ms
```

```text
$ git diff --check
PASS (no output)
```

The rendered fixtures now prove source aggregate semantics from the existing snapshot facts:
`discovered.length`, `authorized.length`, current-state source facts for takeover, and scan-record
count; unknown aggregate inputs remain `尚未获得`, while a detected-only source cannot inflate the
takeover count. `last_error` is kept only in the existing collapsed `技术详情`; ordinary runtime
warnings no longer show port `8766`; source operation failures use safe actionable Chinese copy;
and Home's real pending action is rendered and clicked through to `需要我处理` in both focused and
full rendered coverage.

### Required acceptance gates

These commands were rerun after the docs/evidence update and passed:

```text
$ python3 scripts/check_acceptance_sync.py
[acceptance-sync] changed files: 2
[acceptance-sync] product-impacting files: 0
[acceptance-sync] PASS: no product-impacting changes detected.
```

```text
$ python3 scripts/check_local_execution_handoff.py
LOCAL_EXECUTION_HANDOFF: PASS
```

### Repair Round 1 commits

- Product/tests: `2784dfa` (`fix: clarify owner memory menus`).
- Docs/evidence: recorded separately after the product commit.

## Repair Round 2 — trusted completed-scan aggregate

The scoped re-review found one remaining Important issue: `snapshot.scans.length` was labeled as
completed checks even when the list mixed running/failed/paused records and was capped below the
summary total. The repair uses only the existing `snapshot.summary.counts.completed`; if that
status count is absent, the owner-facing value remains `尚未获得`. No endpoint, DTO, backend, or
data model was changed.

### RED evidence (test first)

The focused rendered fixture was changed first to return two mixed-status scan records while its
existing summary reports five total records and three completed records. The baseline stopped at
the aggregate assertion:

```text
$ npm run test:owner-ui-menu-fast-track
AssertionError [ERR_ASSERTION]: source aggregate must show 已完成检查 3 次
```

Exact result: `1 failed` assertion. The old implementation rendered the list length (`2`) instead
of the trusted completed count (`3`).

### GREEN and regression evidence

```text
$ npm run test:owner-ui-menu-fast-track
owner-ui-menu-fast-track-smoke: PASS
```

```text
$ npm run test:e2e:memory
e2e_owner_memory_flow: PASS
```

```text
$ npm run test:memory-sources && npm run test:memory-sources-repair
automatic-memory-sources-smoke: PASS
automatic-memory-sources-repair-smoke: PASS (Task8E behaviors included)
```

```text
$ npm run build
✓ 96 modules transformed.
✓ built in 407ms
```

```text
$ npm run test:smoke
[smoke] PASS (23 scripts)
```

```text
$ git diff --check
PASS (no output)
```

The focused and full rendered fixtures now assert that mixed running/failed/paused records are not
counted as completed and that a summary aggregate larger than the capped scan list is rendered
truthfully. Product/tests commit: `a8cfcae` (`fix: use trusted completed scan totals`).

### Required acceptance gates

These commands were rerun after the Round 2 docs/evidence update and passed:

```text
$ python3 scripts/check_acceptance_sync.py
[acceptance-sync] changed files: 2
[acceptance-sync] product-impacting files: 0
[acceptance-sync] PASS: no product-impacting changes detected.
```

```text
$ python3 scripts/check_local_execution_handoff.py
LOCAL_EXECUTION_HANDOFF: PASS
```

Docs/evidence is committed separately after the product/tests commit. Existing Vite dynamic-import
warnings remain; live/real-data/Production/Vault/installation/owner-observation checks remain
outside this scoped UI round.
