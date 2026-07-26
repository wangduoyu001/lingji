# P2-10C Memory Workspace UI Test Report

## Branch

```text
work/p2-10c-memory-workspace-ui
```

## Scope

This report covers the Desktop UI refinement for:

```text
Memory Review
Auto Review SHADOW
Memory Inspector
Codex Project and Session Workspace
```

## New smoke test

```text
desktop/lingji-control/scripts/memory-workspace-ui-smoke.mjs
```

The smoke verifies:

- Memory Review has an owner-authority hero, review workbench, candidate cards, detail panel and action dock;
- Codex Workspace has a project rail, Session browser, Session detail, activity timeline and Context Pack builder;
- Auto Review has a SHADOW hero, decision inbox, decision explanation and read-only evaluator;
- Memory Inspector keeps evidence-browser columns, restricted-content handling and detail drawer;
- shared workspace styles exist;
- forbidden automatic memory mutation endpoints remain absent;
- permanent deletion language remains absent.

The new test is registered in the complete Desktop smoke suite, increasing the suite from 15 to 16 scripts.

## Existing contract tests preserved

The implementation continues to pass:

```text
memory-review-smoke.mjs
codex-workspace-smoke.mjs
auto-review-shadow-smoke.mjs
memory-inspector-smoke.mjs
native-desktop-ui-smoke.mjs
ui-modular-smoke.mjs
```

These tests preserve:

- content-hash conflict protection;
- owner confirmation;
- required rejection reason;
- archive rather than permanent delete;
- hidden-window polling pause;
- bounded Context Pack generation;
- Auto Review mutation count and SHADOW-only endpoints;
- inspector query and mapping contracts;
- Tauri-only credential behavior.

## GitHub Actions results

Validated implementation head before this documentation-only update:

```text
be1ac496d6f931fdafd5504b4d2a513dee6f12d6
```

Workflow results:

```text
tests #719: SUCCESS
P0 Windows Gate #108: SUCCESS
```

Passed gates:

```text
16-script Desktop smoke suite: SUCCESS
React / TypeScript / Vite production build: SUCCESS
Tauri configuration validation: SUCCESS
Tauri Rust cargo check: SUCCESS
Python 3.11 unit tests: SUCCESS
Python 3.12 unit tests: SUCCESS
Python 3.12 full repository gate: SUCCESS
Windows compile and full tests: SUCCESS
clean-install contract validation: SUCCESS
full Python entry-point compile: SUCCESS
MCP smoke: SUCCESS
Browser capture smoke: SUCCESS
Obsidian plugin smoke: SUCCESS
```

## Manual owner checks still required

CI validates contracts, source compilation, Windows tests, frontend production build and Rust compilation. It does not prove interaction with the packaged application on the owner's real Windows machine.

Remaining checks:

1. Open Artificial Memory Review and verify candidate selection is visually obvious.
2. Verify no approve or reject action is shown before selecting a candidate.
3. Verify approve, edit-approve and reject controls remain disabled during requests.
4. Verify reject requires a reason.
5. Verify the review queue and detail panel remain usable at the minimum Desktop width.
6. Open Auto Review and verify it is visually distinct from the real mutation page.
7. Verify ACTIVE mode displays a blocking warning.
8. Verify a selected SHADOW decision shows rules, evidence and AI summary.
9. Open Project and Conversation Workspace and verify project, Session and detail selection states.
10. Verify Context Pack generation and clipboard copy.
11. Verify activity shortcuts open Memory Inspector.
12. Verify restricted messages remain collapsed until actively expanded.
13. Verify the Inspector detail drawer fits inside the Tauri window and can be closed.
14. Verify source, conversation and message columns preserve their selection chain.

## Data and authority impact

```text
Database schema changed: no
Memory API semantics changed: no
New automatic mutation: no
Auto Review ACTIVE enabled: no
Permanent delete added: no
New credentials store: no
Production memory mutation during CI: no
second_brain changes: no
```

## Status

```text
CI_VALIDATED_AWAITING_OWNER_PACKAGED_APP_CHECK
```
