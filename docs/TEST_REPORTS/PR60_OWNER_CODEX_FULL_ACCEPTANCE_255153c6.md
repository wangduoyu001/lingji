# PR #60 Owner + Codex Full Acceptance Report

## 1. Executive Verdict

**FAIL — PR #60 owner-machine acceptance did not pass; do not merge.**

The fixed artifact and installed Runtime were verified, but the required local
Python full suite failed. Several mandatory UI, Codex-client, import, review and
lifecycle observations were also not completed because the Windows UI automation
interface could not operate the installer or Desktop window, and no owner visual
observation was provided.

## 2. Product and Artifact Identity

| ID | Name | Prerequisite | Method | Expected | Actual | Evidence | Conclusion |
|---|---|---|---|---|---|---|---|
| A1 | Source identity | Fixed repository clone | Detached checkout and `rev-parse` | `255153c6…` | Matched | Local Git state | PASS |
| A2 | CI identity | GitHub authenticated API | Match successful Windows Release run by Head SHA | Fixed commit only | Run `30443031644` matched and succeeded | Public GitHub metadata | PASS |
| A3 | ZIP integrity | Artifact ID 8720375948 | Download exact ZIP and SHA256 | Fixed ZIP hash | `24c92e…cf82d4` matched | Private hash record | PASS |
| A4 | Release contents | Extracted ZIP | Hash installer, portable EXE, manifest and SHA256SUMS rows | All fixed hashes match | All matched; manifest declared the fixed Sidecar SHA256 | Private hash record | PASS |

## 3. Environment Cleanup

| ID | Name | Prerequisite | Method | Expected | Actual | Evidence | Conclusion |
|---|---|---|---|---|---|---|---|
| C1 | Old LingJi processes and ports | Existing installation | Stop only `lingji-control-center` and `lingji-core`; inspect 8766/8767 | No residual process/listener | No residual process or listener before install | Private process/port snapshot | PASS |
| C2 | Old temporary acceptance directory | User-approved directory deletion | Shell and File Explorer control attempt | Old directory removed | Shell deletion was denied by host policy; Explorer automation returned a Windows interface error | Current directory inspection | NOT_TESTED |

No Production DataRoot, Vault, formal memory, database or user configuration was
deleted.

## 4. Environment and Workspace

The installed Control process used a non-system-drive Acceptance DataRoot. The
authenticated runtime ping returned `ok`; `/api/health` returned `degraded`,
which is consistent with the documented non-fatal Embedding limitation.

## 5. Source Documents Read

Read from fixed commit `255153c6…`: `AGENTS.md`, Desktop Quickstart, both
implementation reports, Assistant Hub and connector module documents, CODE_MAP,
PROJECT_STATUS, CHANGELOG, and the tests, P0 Windows Gate and Windows Release
workflows.

## 6. CI and Local Automated Tests

| ID | Name | Prerequisite | Method | Expected | Actual | Evidence | Conclusion |
|---|---|---|---|---|---|---|---|
| T1 | Required connector and MCP modules | Isolated Python 3.12 | Four mandated test files | Pass | 20 passed | Private log | PASS |
| T2 | Full Python suite | Isolated Python 3.12 | `pytest -q --tb=short` | Pass | 541 passed, 1 failed, 11 skipped | Private log | FAIL |
| T3 | Desktop Smoke | npm dependencies | `npm run test:smoke` | Pass | 22 scripts passed | Private log | PASS |
| T4 | React/TypeScript/Vite build | npm dependencies | `npm run build` | Pass | Pass | Private log | PASS |
| T5 | Tauri Rust | Rust toolchain | `cargo check`; `cargo test` | Pass | Check passed; 9 tests passed | Private log | PASS |

The full-suite failure was
`SecondBrainTests.test_second_brain_is_not_in_original_start_chain`, whose child
`python` process exited non-zero. No source code or test was changed.

## 7. Installation

| ID | Name | Prerequisite | Method | Expected | Actual | Evidence | Conclusion |
|---|---|---|---|---|---|---|---|
| I1 | Exact NSIS cover install | Verified installer | Silent NSIS cover installation | Exit success, no owner data deletion | Installer exited 0 | Local installer exit | PASS |
| I2 | Human window observation | Owner present | Observe PowerShell, CMD and black windows | Owner confirmation | Not supplied; silent mode cannot prove absence | N/A | NOT_TESTED |

## 8. Runtime and Port State

| ID | Name | Prerequisite | Method | Expected | Actual | Evidence | Conclusion |
|---|---|---|---|---|---|---|---|
| R1 | Managed Runtime | Installed Desktop | Inspect process tree and listeners | One Desktop, Control and MCP child | Observed one Desktop and two correctly parented sidecar processes | Private process snapshot | PASS |
| R2 | Loopback binding | Running Runtime | Inspect 8766/8767 listeners | 127.0.0.1 only | Both listeners bound to 127.0.0.1 | Private port snapshot | PASS |
| R3 | Sidecar integrity | Installed files | SHA256 of installed `lingji-core.exe` | Manifest hash | Matched `bece787b…54722` | Private hash record | PASS |
| R4 | Runtime health | Control token | Authenticated `/api/runtime/ping` | `ok` | `ok` | Private API result | PASS |

## 9. P0-A Start Center

NOT_TESTED. The UI automation helper could not operate the Desktop window, and
owner visual observation was not supplied.

## 10. First-Time User Experience

NOT_TESTED. Owner answers about clarity, workflow terms and recommended next
action were not provided.

## 11. MCP Gateway

| ID | Name | Prerequisite | Method | Expected | Actual | Evidence | Conclusion |
|---|---|---|---|---|---|---|---|
| M1 | Bearer rejection | Running MCP | POST with no or wrong token | 401 | Both returned 401 | Private API result | PASS |
| M2 | Real MCP session | Correct local token | `initialize` then `tools/list` | Session and required tools | Session created; required memory tools listed | Private API result | PASS |

## 12. Codex Connector

NOT_TESTED. A real new Codex client session, LingJi-managed preview/apply,
candidate submission and rollback were not completed.

## 13. Claude Code Connector

NOT_TESTED. No installed-client acceptance was completed.

## 14. WorkBuddy / CodeBuddy Connector

NOT_TESTED. No official client UI acceptance was completed.

## 15. ChatGPT Export Import

NOT_TESTED. No synthetic fixture was imported through the installed UI.

## 16. Codex Report Import

NOT_TESTED. No synthetic fixture was imported through the installed UI.

## 17. Failure-Path Import

NOT_TESTED.

## 18. Candidate and Permanent-Memory Boundary

NOT_TESTED. No candidate was approved or rejected in Acceptance Workspace.

## 19. Three Core Restarts

NOT_TESTED. The mandatory three UI-triggered restarts were not completed.

## 20. Windows Reboot Recovery

NOT_TESTED. No reboot checkpoint or owner-confirmed Windows reboot was completed.

## 21. Previous-Bug Regression Matrix

| Regression | Result |
|---|---|
| Runtime managed, loopback ports, non-C DataRoot | PASS |
| PowerShell/CMD/black window regression | NOT_TESTED |
| Core restart, Windows reboot, duplicate Core, orphan MCP | NOT_TESTED |
| UI navigation, Start Center clarity and imports | NOT_TESTED |
| Token redaction, configuration rollback and review boundary | NOT_TESTED |

## 22. Production / Acceptance Isolation

Acceptance DataRoot was confirmed non-system-drive. Production write isolation,
token difference and cross-workspace data separation were not fully tested.

## 23. Security and Secret-Redaction Audit

The public report and evidence summary contain no token, Authorization header,
private chat, database body, user name, absolute path, configuration content or
private screenshot. MCP authentication rejection was verified.

## 24. Evidence Index and Hashes

Public summary: `docs/TEST_REPORTS/evidence/PR60_PUBLIC_EVIDENCE_SUMMARY_255153c6.json`.
Public hashes: `docs/TEST_REPORTS/evidence/PR60_PUBLIC_HASHES_255153c6.txt`.
Private command and API records remain local only.

## 25. Known Non-Blocking Limitations

The authenticated health endpoint reported `degraded`, consistent with the
documented inactive-Embedding limitation. This did not prevent Runtime or MCP
operation.

## 26. Blocking Defects

1. The required Python full suite failed (541 passed, 1 failed, 11 skipped).
2. Mandatory owner/UI, Codex-client, import, review and lifecycle acceptance
   remains unexecuted.

## 27. Final Merge Recommendation

**FAIL — PR #60 owner-machine acceptance did not pass; do not merge.**
