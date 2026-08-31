# OWNER_UI_SOURCE_FILTER_REPAIR_4CE1E00A — Mac Acceptance Handoff

## 1. Status

```text
Status: PENDING
Verdict: PENDING
Product commit: 4ce1e00acb17bc5e4e4c183f58d30551ef76b101
Review: PASS / APPROVED (Critical 0, Important 0, Minor 0)
Acceptance mode: MACOS_OWNER_UI_EXPERIENCE_ONLY
Release gate: NOT_A_RELEASE_GATE
Acceptance root: /tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a
```

This handoff does not claim a Mac build, installation, live 8766 run, Computer Use
observation, owner confirmation, release, Phase 1 PASS, or merge.

## 2. Reviewed scope

The independent review is recorded in
`.superpowers/sdd/2026-08-30-owner-ui-menu-fast-track/owner-ui-source-conclusion-final-review.md`.
It covers the source filter in `8ec447e0` and conclusion persistence in `4ce1e00a`.

`not_found` records remain in raw discovery diagnostics but are not ordinary cards unless
an authorized lifecycle matches. Available, consent-required and unsupported records remain
visible; authorized/revoked lifecycle remains visible; visible source count is the owner
found-count source of truth. `/tmp` and `/private/tmp` alias handling remains macOS-only.

Existing `conclusion`, `current_conclusion`, and `summary` values use entry-over-properties
precedence in the existing relationship projection. List/detail share one projector result,
and verified-evidence gating remains fail-closed for missing, mismatched, or unavailable evidence.
No new table or permanent fact source was added.

## 3. Automated evidence

| Check | Result |
|---|---|
| Owner card API/projector focused tests | 36 passed, 1 warning |
| `npm run test:memory-sources` | PASS |
| `npm run test:owner-ui-menu-fast-track` | PASS |
| `npm run test:e2e:memory` | PASS |
| `npm run test:smoke` | PASS (23 scripts) |
| `npm run build` | PASS (97 modules; existing Vite warnings) |
| Affected Python compileall | PASS |
| `git diff --check` | PASS |

## 4. Required Mac execution

Before installation, clean only task-owned state and release ports 8766/8767. Build the
arm64 candidate from the exact product commit, verify strict codesign, preserve the existing
whole-app backup, and use only the new root. Keep all prior roots read-only:

- `/tmp/LingJiAcceptance/owner-ui-live-repair-6ea11e4`
- `/tmp/LingJiAcceptance/owner-ui-redesign-43009a0`
- `/tmp/LingJiAcceptance/owner-ui-menu-fast-track-task-2-6baf4ee6`
- `/tmp/LingJiAcceptance/owner-ui-menu-fast-track-task-2-b299e5b`

The new synthetic seed must contain 37 cards (3 history), 13 permanent, 3 conversations,
36 messages, and exactly 1 owner high-risk pending action. It must contain at least 8 varied
owner-readable conclusions and explicitly mark the data synthetic; do not manufacture an
automatic-scan failure pending. Discovery must include available sessions and a not-found
archive, while ordinary source UI must show exactly 1 Codex card and a found count equal to
visible cards. Full-root Computer Use and owner confirmation are pending. After self-check,
leave the app and sidecar open for the owner.

## 5. Historical failure boundary

The previous `6ea11e4` owner observation failed on source presentation: available Codex
sessions and not-found archived sessions produced two same-named Codex cards, and a missing
directory was described as discovered. This evidence remains preserved and is not a result of
the new candidate.
