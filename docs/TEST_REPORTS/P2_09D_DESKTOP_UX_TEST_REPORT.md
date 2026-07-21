# P2-09D Desktop UX Test Report

## Environment

Development was performed through the writable GitHub connector on stacked branch `work/p2-09d-desktop-ux-auto-review`, based on `work/p2-09c-desktop-data`.

No local Node, npm, browser, Tauri or 8766 runtime was attached to this conversation.

## Smoke coverage

`desktop/lingji-control/scripts/auto-review-shadow-smoke.mjs` verifies:

- grouped navigation is wired through five groups;
- the Auto Review page is registered;
- the connection panel is collapsible;
- the UI uses only status, metrics, decisions, evaluation and feedback routes;
- no approve/reject/delete/execute/ACTIVE route appears in the dashboard;
- the page visibly states that SHADOW does not change memory;
- manual Memory Review identifies itself as the unique memory-change authority.

The smoke is registered in the existing desktop smoke suite, which runs before TypeScript and Vite builds.

## Expected build validation

GitHub Actions should execute:

- existing desktop smoke suite;
- TypeScript compile;
- Vite production build;
- repository-required Tauri/Rust checks where configured.

## Manual validation still required

1. Five navigation groups scroll correctly at desktop window sizes.
2. Connection URL/token inputs remain hidden until expanded.
3. Browser mode can connect with a valid token and rejects an invalid token.
4. SHADOW status/metrics/decisions recover after a temporary 8766 outage.
5. Stale data remains visible with a warning after refresh failure.
6. Candidate evaluation creates an audit decision but does not change candidate state.
7. Feedback creates an audit event only.
8. Manual approve/reject flows remain unchanged.
9. ACTIVE or mutation-enabled status renders as an error.
10. Decision details remain readable with long reason text.

## Execution status

Status at document creation: `TESTS_ADDED_NOT_EXECUTED`.

## Backend/data impact

- Python backend changed: no.
- Database schema changed: no.
- Memory lifecycle changed: no.
- Obsidian/Qdrant changed: no.
- Automatic execution control added: no.

## Dependency

This branch depends on P2-09C polling contracts. Full runtime behavior also depends on P2-08A/P2-08B Auto Review backend integration.

## Final commit

Record the final PR head after CI-driven fixes.
