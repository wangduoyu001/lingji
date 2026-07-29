# PR #60 Owner-machine full acceptance — 255153c6

## 1. Executive Verdict

**FAIL — do not merge.**

The exact source commit and GitHub checks were verified, but the Codex connector
does not isolate an explicitly supplied empty environment from the machine
`CODEX_HOME`. On this owner machine, the required connector test wrote a LingJi
managed block to the real Codex configuration before its assertion failed. The
configuration was restored byte-for-byte from the private pre-test backup.

The specified Actions artifact also could not be downloaded because GitHub
returned HTTP 401. Therefore the installer, Runtime, actual Desktop UI, MCP
gateway, import, lifecycle and owner-observation portions were not performed.
This is not a substitute-artifact acceptance.

## 2. Product and Artifact Identity

| ID | Name | Prerequisite | Method | Expected | Actual | Evidence | Conclusion |
|---|---|---|---|---|---|---|---|
| A1 | PR identity | Public GitHub API reachable | Read PR #60 metadata | Open, draft, unmerged, head `255153c6…` | All matched | Private API summary | PASS |
| A2 | CI identity | Public GitHub API reachable | Read checks for the fixed commit | tests #1075, P0 Gate #237 and Release #126 succeed on same commit | Matching checks completed successfully on `255153c6…` | Private API summary | PASS |
| A3 | Artifact identity | Artifact ID 8720375948 | Read artifact metadata | Exact name and unexpired state | `lingji-windows-0.1.0-255153c6`, unexpired | Private API summary | PASS |
| A4 | Artifact integrity | Downloaded ZIP | Download artifact, unpack and hash every required item | Six specified SHA256 values match | Download endpoint returned HTTP 401; ZIP unavailable | Private HTTP result | BLOCKED |

Expected artifact identity: `lingji-windows-0.1.0-255153c6`, ID `8720375948`,
commit `255153c6d5ecf65046089dc6b794e001422fcfa8`.

## 3. Environment

- Fixed product source: detached worktree created from `255153c6…`, then this
  report-only branch was created.
- Private evidence, test dependencies, temporary files and logs were kept on
  `D:` under the owner-local acceptance directory.
- Python validation used an isolated Python 3.12 virtual environment. Node was
  24.15.0 locally (the workflow specifies Node 22); this variance is recorded.
- No Production Vault, Production DataRoot, database body, token, API key or
  private conversation content was included in public evidence.

## 4. Source Documents Read

Read from the fixed commit: `AGENTS.md`, Desktop Quickstart, both PR60
implementation reports, Assistant Hub and connector module docs, CODE_MAP,
PROJECT_STATUS, CHANGELOG, and the tests, P0 Windows Gate and Windows Release
workflows.

## 5. CI and Local Automated Tests

| ID | Name | Prerequisite | Method | Expected | Actual | Evidence | Conclusion |
|---|---|---|---|---|---|---|---|
| T1 | Required connector tests, owner environment | Python 3.12 + workflow dependencies | Run the four required test modules with the machine `CODEX_HOME` | All pass without touching owner config | 18 passed, 2 failed; real Codex config was touched then restored | Private logs and backup hashes | FAIL |
| T2 | Full Python suite, owner environment | Same | `python -m pytest -q --tb=short` | Full suite passes | 539 passed, 3 failed, 11 skipped | Private log | FAIL |
| T3 | Full Python suite, CI-like environment | `CODEX_HOME` absent and Python 3.12 first on PATH | Same command | Full suite passes | 541 passed, 1 failed, 11 skipped; the startup-child test passes when rerun alone | Private log | FAIL |
| T4 | Compile | Python 3.12 | Workflow compileall target list | Pass | Pass | Private log | PASS |
| T5 | MCP server creation | Python 3.12 | Create `lingji-local` MCP server | Server created | Exit 0; created successfully; shutdown emitted a Qdrant destructor warning | Private log | PASS_WITH_WARNING |
| T6 | Packaged Runtime contract | Python 3.12 | `test_packaged_control_api.py` + `test_packaged_mcp_runtime.py` | Pass | 17 passed | Private log | PASS |
| T7 | Desktop smoke | npm dependencies | `npm run test:smoke` | Pass | 22/22 scripts passed | Private log | PASS |
| T8 | Desktop production build | npm dependencies | `npm run build` | Pass | Pass | Private log | PASS |
| T9 | Tauri Rust | Rust toolchain | `cargo check`; `cargo test` | Pass | Check passed; 9/9 tests passed | Private log | PASS |

### Blocking defect A-01 — Codex configuration isolation

`AiMemoryConnectorService.__init__` uses `dict(env or os.environ)`. An explicit
empty mapping is falsy, so it reads the real process environment rather than the
provided isolated environment. With `CODEX_HOME` configured, the Codex connector
targets the owner configuration instead of the test's temporary home. This
violates the required configuration-preservation and safe-test boundary.

The first failed test saved a private backup before the write. The original file
was restored from that backup and its SHA256 matched exactly. No configuration
content, token or path is published here.

## 6. Install and Runtime

| ID | Name | Prerequisite | Method | Expected | Actual | Evidence | Conclusion |
|---|---|---|---|---|---|---|---|
| B1–B4 | Specified installer, Runtime, ports and process tree | Verified artifact ZIP and installer | Cover-install exact NSIS package and inspect managed Runtime | Healthy loopback 8766/8767 and no console-window regression | Installer unavailable due HTTP 401 | Private HTTP result | BLOCKED |

## 7. P0-A Start Center and First-Time UX

| ID | Name | Prerequisite | Method | Expected | Actual | Evidence | Conclusion |
|---|---|---|---|---|---|---|---|
| C1–C4 | Installed Desktop and owner observation | Exact installer | Navigate all mandated routes and collect owner wording | Truthful Start Center and one recommended action | No exact installer; owner visual observation not performed | Artifact block | BLOCKED |

## 8. MCP Gateway

| ID | Name | Prerequisite | Method | Expected | Actual | Evidence | Conclusion |
|---|---|---|---|---|---|---|---|
| D1–D3 | Running installed gateway | Exact installer | 401 checks, initialize, tools/list and required tool calls | Authenticated loopback MCP | Package unavailable | Artifact block | BLOCKED |

## 9. Codex Connector

| ID | Name | Prerequisite | Method | Expected | Actual | Evidence | Conclusion |
|---|---|---|---|---|---|---|---|
| E1–E7 | Running installed Desktop and safe owner config handling | Exact installer | Preview, apply, new Codex-session calls, review and rollback | Only LingJi block changes; genuine tools work | A-01 failed before real connection acceptance; package unavailable | Private test evidence | FAIL |

## 10. Claude Code Connector

Not tested. The required installed artifact was unavailable. No claim is made
about Claude Code installation or connection state.

## 11. WorkBuddy / CodeBuddy Connector

Not tested. The required installed artifact was unavailable. No claim is made
about client installation, copying, configuration or tool calls.

## 12. ChatGPT Export and Codex Report Import

Not tested. Creating synthetic fixtures and importing them through a source or
different package would not meet the fixed-artifact requirement.

## 13. Candidate and Permanent-Memory Boundary

Not tested in the installed product. Static/source tests do not replace the
required owner-machine candidate, approval and rejection acceptance.

## 14. Core Restart and Windows Reboot

Not tested. No Windows reboot was requested because the exact package could not
be installed, and the required prior phases already failed.

## 15. Previous-Bug Regression Matrix

| Regression | Result |
|---|---|
| PowerShell/CMD/black console | NOT TESTED |
| Runtime managed/restart/reboot/duplicate-orphan processes | NOT TESTED |
| C-drive data, Workspace, Vault and cover-install protection | NOT TESTED |
| Detected shown as connected, dead UI buttons, Start Center clarity | NOT TESTED |
| Embedding status wording | NOT TESTED |
| Token leak | NOT TESTED |
| Import writes Core Memory directly | NOT TESTED |
| Rollback damages other configuration | FAIL — A-01 configuration-isolation defect |

## 16. Production / Acceptance Isolation

Production was not used. Acceptance dependencies and temporary data were placed
on `D:`. Actual Production/Acceptance service isolation could not be validated
without the specified installer.

## 17. Security and Secret-Redaction Audit

Public report and evidence contain no token, Authorization header, API key,
private chat, database body, full local path, screenshot or third-party backup.
The A-01 test side effect was reversed using the first private backup; only its
SHA256 is retained privately.

## 18. Evidence Index and Hashes

Public evidence: `docs/TEST_REPORTS/evidence/PR60_PUBLIC_EVIDENCE_SUMMARY_255153c6.json`
and `docs/TEST_REPORTS/evidence/PR60_PUBLIC_HASHES_255153c6.txt`.

Private evidence includes API summaries, HTTP download failure, command logs,
test logs and redacted configuration backup hashes. It remains owner-local.

## 19. Known Non-Blocking Limitations

- Local Node 24 differed from the workflow's Node 22; frontend smoke/build still
  passed and this did not determine the verdict.
- MCP creation emitted a Qdrant shutdown destructor warning after a successful
  process exit; the contract tests passed.

## 20. Blocking Defects

1. **A-01 Codex configuration isolation:** an explicitly empty environment leaks
   to `os.environ`, allowing test/connector behavior to target real `CODEX_HOME`.
2. The exact artifact could not be downloaded because GitHub required
   authentication (HTTP 401), so mandatory installed-product acceptance remains
   unexecuted.
3. The local full Python suite did not pass in either owner or CI-like process
   setup.

## 21. Final Merge Recommendation

**FAIL — PR #60 owner-machine acceptance did not pass; do not merge.**
