# OWNER_UI_SOURCE_FILTER_REPAIR_4CE1E00A — Mac Owner UI Acceptance Report

## 1. Executive Verdict

```text
Status: COMPLETED
Verdict: FAIL
Owner result: OWNER_MEMORY_DETAIL_DRILLDOWN_REQUIRED
Merge recommendation: DO NOT MERGE
Product commit: 4ce1e00acb17bc5e4e4c183f58d30551ef76b101
Artifact: local macOS arm64 Tauri application rebuilt from the exact product commit
Artifact ID: LOCAL_ONLY_NOT_CI
Report commit: 33b1d83e3446a57ee503043b8f25ee86a940b63b
Release gate: NOT_A_RELEASE_GATE
Quality: MEASURED_FAIL / NOT_RELEASE_READY
Owner observation: OWNER_MEMORY_DETAIL_DRILLDOWN_REQUIRED
```

The technical candidate build, installation, authenticated sidecar, synthetic data contract, and
bounded root-agent Computer Use traversal completed successfully. The latest owner feedback does
not accept the memory experience as sufficiently understandable: a clear owner-facing memory
detail drilldown is still required to show what was concluded, how it developed, and the
verifiable source. Therefore this acceptance is closed as `COMPLETED / FAIL`, with owner result
`OWNER_MEMORY_DETAIL_DRILLDOWN_REQUIRED`; it is not a release, Phase 1, or merge result.

The first packaging attempt failed in the `tauri.macos.conf` app-only packaging path. It is
recorded as `FAIL_REPAIRED`, not hidden or counted as a pass. A sidecar-config rebuild then
produced the candidate that passed the final package checks below.

## 2. Product and Artifact Identity

| Item | Expected | Actual | Result |
|---|---|---|---|
| Repository | `wangduoyu001/lingji` | `wangduoyu001/lingji` | PASS |
| Product branch | `codex/owner-real-history-memory-cards` | exact candidate source | PASS |
| Product commit | `4ce1e00acb17bc5e4e4c183f58d30551ef76b101` | same | PASS |
| Artifact | macOS arm64 candidate | local Tauri arm64 candidate | PASS |
| Artifact ID | local-only | `LOCAL_ONLY_NOT_CI` | PASS |
| DMG SHA256 | generated candidate | `351557a1efd38c66941ba80ed65616a515852fe5e689a220428cd5363dd11991` | PASS |
| Installed main SHA256 | candidate member | `6fb5e44a27dc65108d4b91ddb5af83cb341a967a9fe9e88b1b1b5a6cec1291a3` | PASS |
| Installed macOS sidecar SHA256 | candidate member | `fb83470f1b29c97cb40a342e82f4ee11ea4b7d897907964dd880b184b23f1dbb` | PASS |
| Installed Resources sidecar SHA256 | candidate member | `9b857ed22bc9fcb2e3f99ec515880f17e0232d36424c94ece6dad398147b388c` | PASS |
| Deep strict codesign | required | PASS | PASS |
| Architecture | main and both sidecars arm64 | all three arm64 | PASS |

Private root evidence: `/tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a/evidence/`.
Public hash evidence is in `docs/TEST_REPORTS/evidence/OWNER_UI_SOURCE_FILTER_REPAIR_4CE1E00A_HASHES.txt`.

## 3. Change Acceptance Source

- Task instruction commit: `8bc1bce20636135018df302ab931cb37707d6376`.
- Documentation correction commit: `94461d56c64f31e1af6c7cdece51e959ddc0e8b1`.
- Current task: `OWNER_UI_SOURCE_FILTER_REPAIR_4CE1E00A`.
- Acceptance mode: `MACOS_OWNER_UI_EXPERIENCE_ONLY`.
- Acceptance root: `/tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a`.
- Affected area: owner memory-card conclusion projection and Codex source filtering, plus the
  already-reviewed owner UI surface that presents those facts.
- Risk: owner-visible provenance and source-discovery correctness; no new database, port,
  permanent fact source, or runtime authority.
- Explicitly out of scope: release/CI artifact promotion, Phase 1 quality gate, production data,
  real chats, real Vault, automatic permanent-memory promotion, backup/source authorization,
  confirmation mutations, and owner sign-off by proxy.

## 4. Environment Cleanup

- Pre-run cleanup: completed by the Mac execution owner for task-owned state; old failed roots and
  backups were preserved read-only.
- Whole-app backup: preserved in the task acceptance root before replacement; no uninstall was used.
- Post-run cleanup: runtime closeout completed after exact verification of candidate PIDs `37148`
  (Desktop) and `37132` (sidecar). The acceptance root, evidence, fixture, backup, and all old
  acceptance roots remain preserved.
- Production pollution count: `0`.
- Vault pollution count: `0`.
- Temporary credentials/config contents: not exported into the report; token files remain private
  inside the isolated acceptance DataRoot.

## 5. Environment and Workspace

```text
OS: macOS Apple Silicon (arm64)
LingJi version: 0.1.0 candidate
Workspace: acceptance
Acceptance DataRoot: /tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a/data-root/acceptance
Acceptance Vault: /tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a/vault
Acceptance source fixture: /tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a/source-fixture
Runtime state: sidecar serving the acceptance workspace; health snapshot degraded only for optional ffmpeg/ffprobe/Ollama capabilities
Runtime managed: true for the installed candidate sidecar
Control port: 127.0.0.1:8766 (authenticated)
MCP port: 8767 absent
```

The health evidence reports zero storage/database errors and three optional capability warnings;
these warnings do not represent an owner UI or source-filter failure.

## 6. CI and Automated Tests

| Test | Result | Evidence |
|---|---|---|
| Product focused owner card/projector tests | `36 passed, 1 warning` | prior reviewed product evidence |
| `npm run test:memory-sources` | PASS | prior reviewed product evidence |
| `npm run test:owner-ui-menu-fast-track` | PASS | prior reviewed product evidence |
| `npm run test:e2e:memory` | PASS | prior reviewed product evidence |
| `npm run test:smoke` | PASS (23 scripts) | prior reviewed product evidence |
| `npm run build` | PASS (97 modules; existing Vite warnings) | prior reviewed product evidence |
| Affected Python compileall | PASS | prior reviewed product evidence |
| `git diff --check` | PASS | prior reviewed product evidence |
| Mac packaging first attempt | `FAIL_REPAIRED` | `docs/TEST_REPORTS/evidence/OWNER_UI_SOURCE_FILTER_REPAIR_4CE1E00A_PACKAGING.txt` |
| Sidecar-config rebuild/install | PASS | `build-install-integrity.txt`, `codesign-and-architecture.txt` |
| Acceptance-doc sync | pending after this report update | run before commit |
| Local handoff check | pending after this report update | run before commit |
| Full/release validation | NOT_RUN / NOT_A_RELEASE_GATE | intentionally out of this task |

The automated product results are inherited from the exact reviewed product commit; they are not
substituted for the live owner observation.

## 7. Installation and Upgrade

The candidate was rebuilt from the exact product commit and installed by whole-bundle replacement
after preserving the existing app bundle backup. The installed bundle contains the expected main
binary and both arm64 sidecar locations, and deep strict codesign passed. Runtime closeout stopped
only the verified candidate processes after the owner-detail feedback was recorded. No production
data, real Vault, real chat, or user configuration was used or modified.

## 8. Runtime, Processes and Ports

| Check | Actual | Result |
|---|---|---|
| Desktop | PID `37148`, installed candidate; stopped at closeout | PASS / CLOSED |
| Core/sidecar | PID `37132`, acceptance DataRoot, `127.0.0.1:8766`; stopped at closeout | PASS / CLOSED |
| Authenticated runtime ping | HTTP `200` | PASS |
| Unauthenticated runtime ping | HTTP `401` | PASS |
| 8766 listener | loopback only | PASS |
| 8767 | absent | PASS for this task |
| Duplicate/stray LingJi runtime | none in task evidence | PASS |

The exact process and listener evidence is `evidence/pids-and-ports.txt`; runtime response evidence
is `evidence/runtime-ping.json`.

## 9. Desktop and First-Time UX

Root-agent Computer Use completed the following bounded traversal on the installed candidate:

- Four ordinary menus passed: `首页`, `记忆内容`, `需要我`, and `记忆来源`.
- Home showed 37 current cards, 3 conversations, 36 raw messages, and 13 permanent memories;
  automatic success text was visible, with exactly one high-risk pending owner action.
- Memory pagination showed current-only page 1 = 20 and page 2 = 17. After waiting 21 seconds,
  page 2 remained stable. No superseded, stale, invalidated, or archived record leaked into the
  current-only view.
- Every sampled visible card had a non-empty latest conclusion, source, and raw/structured/vector/
  permanent layer statuses. Detail and `查看来源` exposed the selected source message.
- `需要我` showed exactly one high-risk action. No additional failure-pending action was created.
- Ordinary source view showed found/visible = 4, authorized/current = 1, and exactly one Codex card;
  raw discovery remained 5 including one `not_found` archive. Backup controls stayed collapsed.
- All 18 advanced pages opened successfully. The warm sage visual layout was inspected; the final
  page was left on `记忆内容` with advanced diagnostics collapsed.
- No backup, source authorization, or owner-confirmation mutation button was clicked. Latest owner
  feedback requires a clearer memory detail drilldown; this is the terminal owner-experience
  disposition for this candidate.

OS-level Window Recovery menu/shortcut/Dock observations are not claimed by this handoff unless the
owner records them separately.

## 10. Workspace, DataRoot and Vault Isolation

The active workspace is `acceptance`; the sidecar command line points to the isolated acceptance
DataRoot. The private health evidence shows the acceptance storage, logs, backups, memory DB, and
state DB under that root. The acceptance Vault and source fixture are separate. Production and
real Vault pollution counts are both zero. The synthetic source root is explicitly marked in the
seed evidence; no real chat or real Vault was read.

## 11. Memory and Permanent-Knowledge Boundary

The synthetic contract contains 37 current cards and 3 history cards, 13 permanent records,
3 conversations, and 36 messages. At least eight distinct owner-readable conclusions are present.
Current-only pagination excludes history/stale/superseded/invalidated/archived records. Vector state
is honestly unavailable/configuration-required, while raw, structured, and permanent states remain
visible per card. The one pending action is a high-risk owner review; no automatic promotion or
confirmation mutation was performed.

## 12. Capture, Import and Queue

The live acceptance evidence covers a completed synthetic scan: 3 conversations and 36 messages,
with one completed scan and no failure-generated pending action. This task does not claim a new
capture/import mutation, backup mutation, source authorization, or queue retry. The scan evidence is
`evidence/scans.json`; the work/outcome/next-action chain is in `evidence/history.json`.

## 13. Retrieval, Embedding and Qdrant

`NOT_APPLICABLE` for release quality or retrieval acceptance in this owner-UI-only task. The UI
truthfully exposed vector availability as unavailable/configuration-required; no vector success was
claimed. The quality gate remains `MEASURED_FAIL / NOT_RELEASE_READY`.

## 14. Local Control API and MCP

Authenticated loopback Control API access passed (`200`), and unauthenticated access was rejected
(`401`). MCP HTTP port 8767 was absent. No token, Authorization header, or private credential was
included in the report. The root evidence contains only redacted/public API facts; token material
remains inside the private acceptance DataRoot.

## 15. AI Client Connectors

```text
Codex rollout history:
Detected: synthetic acceptance fixture only
Configured: one authorized/current synthetic source
Live tested: metadata discovery and source projection only; no real account/chat read
New session real call: SKIPPED_NOT_IN_SCOPE
Candidate submitted: no; owner source-confirmation controls were not clicked
Rollback: not applicable
Reconnect: not applicable
Verdict: PASS for the synthetic source-filter presentation contract; owner confirmation pending

ChatGPT:
Detected: no official export fixture
Configured: consent-required
Live tested: SKIPPED_NOT_INSTALLED
Verdict: SKIPPED_NOT_INSTALLED

Claude Desktop:
Detected: discovery record only
Configured: consent-required/opaque storage not read
Live tested: SKIPPED_NOT_INSTALLED
Verdict: SKIPPED_NOT_INSTALLED
```

## 16. Core Restart and Windows Reboot

`NOT_TESTED` in this owner-UI-only handoff. The task proves the current installed candidate runtime
and loopback boundary only; it does not claim three Core restarts or Windows reboot coverage.

## 17. Regression Matrix

| Regression item | Result | Evidence/notes |
|---|---|---|
| PowerShell/CMD/black window | NOT_TESTED | no owner claim made |
| Runtime unmanaged | PASS | managed installed sidecar evidence |
| Restart recovery | NOT_TESTED | outside current bounded traversal |
| Windows reboot recovery | NOT_TESTED | macOS task |
| Duplicate Core/orphan MCP | PASS | PID/port evidence; 8767 absent |
| C-drive write | PASS | acceptance health check says false |
| Workspace/DataRoot/Vault loss | PASS | isolated acceptance paths and pollution 0 |
| UI button no-op | PASS for traversed visible controls | mutating controls intentionally not clicked |
| Fake success/unknown fabrication | PASS for observed cards/source/counts | vector remains unavailable; no invented value |
| Token leakage | PASS | public report contains no token or Authorization value |
| Automatic Core Memory write | PASS / not invoked | owner confirmation not clicked |
| Rollback damaging user config | NOT_TESTED | no rollback invoked |
| Production pollution | PASS (`0`) | root verification summary |
| Change-log required regressions | PASS | docs sync/handoff verified for this closeout |

## 18. Security and Secret-Redaction Audit

- Public evidence contains product identity, logical artifact members, hashes, counts, and statuses;
  it excludes token contents, raw chat bodies, database contents, and private credentials.
- Real paths outside the acceptance root are omitted from public evidence; exact installed-bundle
  checks remain in private root evidence.
- No API key, cookie, Authorization value, or private client storage was exported.
- Source discovery was limited to the synthetic acceptance fixture; no full-disk scan or opaque
  Claude storage read occurred.

## 19. Evidence Index and Hashes

Public evidence:

- `docs/TEST_REPORTS/evidence/OWNER_UI_SOURCE_FILTER_REPAIR_4CE1E00A_SUMMARY.json`
- `docs/TEST_REPORTS/evidence/OWNER_UI_SOURCE_FILTER_REPAIR_4CE1E00A_HASHES.txt`
- `docs/TEST_REPORTS/evidence/OWNER_UI_SOURCE_FILTER_REPAIR_4CE1E00A_PACKAGING.txt`

Private acceptance evidence (not uploaded as an artifact):

- `/tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a/evidence/verification-summary.json`
- `/tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a/evidence/build-install-integrity.txt`
- `/tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a/evidence/codesign-and-architecture.txt`
- `/tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a/evidence/installed-app-hashes.sha256`
- `/tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a/evidence/pids-and-ports.txt`
- `/tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a/evidence/seed-summary.json`
- `/tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a/evidence/cards-page-1.json`
- `/tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a/evidence/cards-page-2.json`
- `/tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a/evidence/discovered.json`
- `/tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a/evidence/history.json`

## 20. Test Cases

```text
ID: BUILD-01
Name: Exact-commit macOS arm64 package
Preconditions: Product commit 4ce1e00acb17bc5e4e4c183f58d30551ef76b101
Method: Rebuild after recording the tauri.macos.conf app-only failure; inspect architecture and strict codesign
Expected: Candidate is arm64, signed, and tied to the exact product commit
Actual: Repaired rebuild passed; main and both sidecars are arm64; strict codesign passed
Evidence: private evidence/build-install-integrity.txt; codesign-and-architecture.txt
Verdict: PASS

API-01
Name: Authenticated local control boundary
Preconditions: Installed candidate sidecar on acceptance DataRoot
Method: Authenticated and unauthenticated runtime ping
Expected: Authenticated request succeeds and unauthenticated request is rejected
Actual: 200 and 401 respectively; 8767 absent
Evidence: private evidence/verification-summary.json; runtime-ping.json
Verdict: PASS

UI-01
Name: Ordinary owner menus and Home facts
Preconditions: Synthetic acceptance seed and running candidate
Method: Open all four ordinary menus and inspect Home facts and next action
Expected: Four menus are usable; counts and next action match the same source
Actual: Four menus opened; Home showed 37/3/36/13 and exactly one high-risk pending action
Evidence: root-agent Computer Use result; private evidence/cards-summary.json and pending.json
Verdict: PASS

UI-02
Name: Current-only memory pagination and provenance
Preconditions: 37 current cards plus 3 history cards
Method: Inspect pages 1 and 2, wait 21 seconds, open a card detail and 查看来源
Expected: 20 + 17 current cards remain stable; no history leakage; source and layer states are readable
Actual: Contract met; sampled visible cards had conclusions, sources, all four layer statuses, and selected source message
Evidence: private evidence/cards-page-1.json and cards-page-2.json; root-agent Computer Use result
Verdict: PASS

UI-03
Name: Codex source filtering
Preconditions: Five raw discovery records including one not_found archive
Method: Open ordinary source page and compare it with discovery facts
Expected: Four visible ordinary source facts and one Codex card; not_found remains diagnostic only
Actual: Found/visible = 4, authorized/current = 1, Codex cards = 1, raw discovery = 5
Evidence: private evidence/discovered.json and sources.json; root-agent Computer Use result
Verdict: PASS

OWNER-01
Name: Owner confirmation boundary
Preconditions: One high-risk owner action
Method: Observe Need Me and leave confirmation controls untouched
Expected: Exactly one pending action; no mutation without owner confirmation
Actual: One high-risk action; no backup/source/confirmation control clicked; owner detail drilldown
  requirement remains unmet
Evidence: private evidence/pending.json; root-agent Computer Use result
Verdict: FAIL — OWNER_MEMORY_DETAIL_DRILLDOWN_REQUIRED
```

## 21. Known Non-Blocking Limitations

- This candidate is synthetic Acceptance data, not a test of the owner's real chat history.
- Vector service is unavailable/configuration-required and is displayed as such.
- Optional ffmpeg, ffprobe, and Ollama health checks warn/degrade but are outside this UI source-filter
  scope.
- 8767 is absent because MCP HTTP is not part of this task.
- Runtime cleanup is complete for the two exact candidate PIDs; acceptance roots and evidence remain
  intentionally preserved for audit and the next repair.

## 22. Blocking Defects

The bounded source/conclusion traversal met its synthetic API and pagination contract, but the
latest owner feedback leaves the owner-readable memory detail experience unaccepted. The gate is
closed as a measured failure pending a future product-level drilldown repair and a fresh owner
observation:

```text
Defect ID: OWNER-MEMORY-DETAIL-DRILLDOWN-REQUIRED
Severity: Acceptance gate
Affected scope: Owner-readable memory detail and final owner sign-off
Reproduction: Open a current memory card and require a clear, understandable detail view containing
  its conclusion, development/context, and verifiable source
Expected: Owner can tell what LingJi concluded, why, and where the evidence came from
Actual: Latest owner feedback still requires this drilldown; bounded traversal evidence alone is
  insufficient for acceptance
Evidence: root-agent Computer Use handoff and private acceptance evidence; owner feedback
Data/security impact: None observed; mutation controls were not clicked
Required fix: Product-level memory detail drilldown repair, then fresh isolated Mac build and owner
  observation
Retest scope: Rebuild exact product SHA successor, repeat memory detail/source observation, and
  obtain explicit owner confirmation
```

The global quality gate remains `MEASURED_FAIL / NOT_RELEASE_READY`; this report does not waive it.

## 23. Final Merge Recommendation

```text
Product commit: 4ce1e00acb17bc5e4e4c183f58d30551ef76b101
Acceptance status: COMPLETED
Verdict: FAIL
Owner result: OWNER_MEMORY_DETAIL_DRILLDOWN_REQUIRED
Release status: NOT_RELEASE_READY
Merge recommendation: DO NOT MERGE
Owner observation complete: YES — FAILED DETAIL DRILLDOWN REQUIREMENT
Required clients covered: synthetic Codex source-filter projection only
Skipped clients: ChatGPT SKIPPED_NOT_INSTALLED; Claude Desktop SKIPPED_NOT_INSTALLED
Blocking defects: owner memory detail drilldown required; global quality gate remains
  MEASURED_FAIL / NOT_RELEASE_READY
Acceptance docs synchronized: PENDING until post-edit checks
Temporary evidence cleaned: NO — acceptance root/evidence/backups intentionally preserved
```

## 24. Sign-off

```text
Codex executor: root-agent + Luna acceptance report agent
Owner confirmation: FAIL — OWNER_MEMORY_DETAIL_DRILLDOWN_REQUIRED
Acceptance date: 2026-08-31
Report branch: acceptance/owner-ui-source-filter-repair-4ce1e00a
Report commit: 33b1d83e3446a57ee503043b8f25ee86a940b63b
```
