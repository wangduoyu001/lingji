# PR #60 Memory Quality Trial Acceptance Report

## 1. Executive Verdict

```text
Verdict: FAIL
Merge recommendation: DO NOT MERGE
Product commit: 1c5148779624910f1c6072d95d6c6f6822f631e6
Artifact: lingji-windows-0.1.0-1c514877
Artifact ID: 8723868744
Report content commit: recorded in LOCAL_EXECUTION_RESULT.md after first remote push
```

Day 0 stopped before any real-data access because the required owner Checkpoint A
failed: the owner reported that the first-use screen did not make the next action
clear. No real data was read or imported; Stage 1 and Stage 2 were not run.

## 2. Product and Artifact Identity

| Item | Expected | Actual | Verdict |
|---|---|---|---|
| Repository | wangduoyu001/lingji | Matched | PASS |
| PR | #60 | Matched task identity | PASS |
| Product Commit | `1c5148779624910f1c6072d95d6c6f6822f631e6` | Matched local and Artifact metadata | PASS |
| Artifact | `lingji-windows-0.1.0-1c514877` | Matched | PASS |
| Artifact ID | `8723868744` | Matched | PASS |
| ZIP SHA256 | GitHub digest `de895289aa8cbef65c27bdf5c298c7f105b8037e34a1e2167208a9e85ab16538` | Matched authenticated binary download | PASS |
| Installer SHA256 | `21ef1825f58845e246695c966032ef9326ba5de8bde4a55e4efe8ec516b7b3a3` | Matched `SHA256SUMS.txt` and metadata | PASS |
| Portable Desktop SHA256 | `91d6cc32c1e1770062cad7b6dde1200196e69f216b0828b18c366a7886bb273f` | Matched `SHA256SUMS.txt` and metadata | PASS |
| Sidecar SHA256 | `81e623d47f7b66b675bbf195bd5bc3b70c2716e7cd890c1572b3b98043304ea4` | Installed Sidecar matched Manifest | PASS |

## 3. Change Acceptance Source

- Task instruction commit: `715c8fe73126227beb9a5378e5fd8e63d742941c`
- Current change entry: 2026-07-30 PR #60 Day 0 safety gate and real-data memory-quality trial.
- Affected scope: guided first-use UX, AI memory connectors, authenticated MCP, acceptance governance.
- Risk level: P0.
- Out of scope after Day 0 failure: reading or importing owner real data, Stage 1, Stage 2, quality scoring and owner quality sampling.

## 4. Environment Cleanup

- Dedicated non-system-drive task root and isolated product/report worktrees were created.
- No old LingJi process, orphan MCP process, or listener on 8766/8767 was present before startup.
- Fixed installer performed a direct cover install with exit code 0; no uninstall was run.
- Production data, owner Vault, formal memory and owner AI-client configuration were not deleted or edited.
- End cleanup is pending remote report confirmation.

## 5. Environment and Workspace

```text
LingJi version: 0.1.0
Workspace: acceptance
Runtime: one Desktop, one managed Control Core and one MCP child observed
Control port: 127.0.0.1:8766
MCP port: 127.0.0.1:8767
```

The UI displayed the fixed PR Commit and an Acceptance workspace. The health
endpoint reported `degraded`; the UI identified inactive embedding while keeping
full-text retrieval available. This state was not represented as healthy.

## 6. CI and Automated Tests

| Test | Result | Evidence |
|---|---|---|
| Product full validation | PASS | Unified `validate.ps1 -Mode full` completed: Python, Desktop smoke/build, Tauri Rust, contracts and MCP creation passed |
| Acceptance documentation gate | PASS | `check_acceptance_sync.py` |
| Local execution handoff gate | PASS | `check_local_execution_handoff.py` |
| Acceptance governance tests | PASS | 30 tests passed |

## 7. Installation and Upgrade

The fixed NSIS installer completed a cover install with exit code 0. The installed
Sidecar matched the artifact Manifest. No owner-data deletion or uninstall was
performed. Window behavior is recorded at Checkpoint A below.

## 8. Runtime, Processes and Ports

| Check | Actual | Verdict |
|---|---|---|
| Process tree | One Desktop, one Control Core, one MCP child | PASS |
| Control port | 8766 bound only to loopback | PASS |
| MCP port | 8767 bound only to loopback | PASS |
| Control authentication | Missing token rejected; correct token ping returned `ok` | PASS |
| MCP authentication | Missing token rejected; authenticated Streamable HTTP session listed 21 tools | PASS |
| Required MCP tools | `get_core_memory`, `search_memory`, `build_context_pack`, `memory_health`, `propose_memory` all present | PASS |

## 9. Desktop and First-Time UX

The released Desktop showed the Start Center, a single recommended next action,
AI-connection entry points, import/review flow and a truthful degraded semantic
retrieval state. Owner Checkpoint A nevertheless failed because the owner did not
know what to do next after scanning AI clients.

## 10. Workspace, DataRoot and Vault Isolation

The UI declared the active workspace as Acceptance and the process data root was
outside the system drive. No Production write was performed. This is partial
Day 0 evidence only; no Stage 1 data boundary was entered.

## 11. Memory and Permanent-Knowledge Boundary

NOT_RUN. No test candidate was proposed because Day 0 stopped at Checkpoint A;
therefore no approval, rejection or formal-memory write was attempted.

## 12. Capture, Import and Queue

NOT_RUN. No fixture or owner real data was imported after Day 0 failure.

## 13. Retrieval, Embedding and Qdrant

The UI and authenticated overview represented embedding as inactive/degraded and
stated that full-text retrieval remained available. No real-data retrieval trial
was run.

## 14. Local Control API and MCP

API and MCP authentication passed as listed above. A real new Codex-client call
was not completed: the locally installed `codex.exe` returned an operating-system
access-denied error before a new session could start. HTTP verification is not
counted as a substitute for the required real Codex call.

## 15. AI Client Connectors

| Client | Verdict | Notes |
|---|---|---|
| Codex | BLOCKED | New local Codex CLI session could not start due to OS access denial |
| Claude Code | NOT_TESTED | Day 0 stopped before connector trial |
| WorkBuddy / CodeBuddy | NOT_TESTED | Day 0 stopped before connector trial |

## 16. Core Restart and Windows Reboot

NOT_RUN. Day 0 failure stopped remaining lifecycle steps. Windows reboot was not
initiated.

## 17. Regression Matrix

| Regression | Result | Evidence / note |
|---|---|---|
| PowerShell/CMD/black window | PASS at Checkpoint A | Owner reported no black window |
| Runtime unmanaged / duplicate Core / orphan MCP | PASS at initial startup | Process tree and ports |
| UI next-action clarity | FAIL | Owner Checkpoint A |
| Token exposure | PASS in public evidence | No token included |
| Automatic Core Memory write | NOT_RUN | No candidate proposed after Day 0 stop |
| Production pollution | PASS for executed scope | No Production write performed |

## 18. Security and Secret-Redaction Audit

The public report and evidence contain no token, Authorization value, private
chat, real-data content, database body, owner configuration body, or full local
path. Auth tokens were read only in process memory for loopback checks.

## 19. Evidence Index and Hashes

- Public summary: `docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_SUMMARY_1c514877.json`
- Public hashes: `docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_HASHES_1c514877.txt`
- Private evidence is temporary local-only and will not be uploaded.

## 20. Test Cases

```text
ID: D0-ARTIFACT
Name: Fixed artifact identity and hashes
Preconditions: Authenticated GitHub Artifact available
Method: Download, metadata, Manifest and SHA256SUMS verification
Expected: Exact product Commit and hashes
Actual: All required artifact identities and hashes matched
Verdict: PASS

ID: D0-AUTOMATION
Name: Product and acceptance automatic gates
Preconditions: Isolated product worktree and venv
Method: Unified full validation and acceptance gates
Expected: All pass
Actual: Full validation PASS; governance tests 30 passed
Verdict: PASS

ID: D0-UX-A
Name: Owner first-use observation
Preconditions: Fixed Desktop installed and open
Method: Owner Checkpoint A
Expected: Owner knows the next action
Actual: Owner reported: no black window; homepage normal; next action unknown after scanning; semantic retrieval message visible
Verdict: FAIL

ID: D0-CODEX-LIVE
Name: New Codex session real MCP call
Preconditions: Authenticated MCP running
Method: Start local Codex CLI and call required tools
Expected: All required tool calls complete
Actual: Local Codex CLI could not start because the OS denied access
Verdict: BLOCKED
```

## 21. Known Non-Blocking Limitations

None. The first-use clarity failure is blocking for Day 0.

## 22. Blocking Defects

```text
Defect ID: D0-UX-001
Severity: P0
Affected scope: Day 0 first-use experience and real-data trial gate
Reproduction: Install fixed build, scan AI clients, then ask owner for the next action
Expected: Owner can identify and follow the next recommended action
Actual: Owner reported the next action was unknown despite the displayed recommendation
Evidence: Owner Checkpoint A
Data/security impact: Real-data trial must not start before owner understands the workflow
Required fix: Make the post-scan next action explicit and actionable, then repeat Checkpoint A and the full Day 0 scope
Retest scope: D0-UX-A, real Codex call, candidate review, restart, Windows reboot and all downstream trial stages
```

```text
Defect ID: D0-CODEX-002
Severity: P1
Affected scope: Required new Codex-client MCP call
Reproduction: Start the installed local Codex CLI for a new session
Expected: CLI starts and can use authenticated LingJi MCP tools
Actual: OS access denied before the CLI could start
Evidence: Local command result; no secret retained in public evidence
Data/security impact: No data write; real-client interoperability remains unproven
Required fix: Restore executable access, then repeat the real-client MCP portion of Day 0
Retest scope: D0-CODEX-LIVE and Checkpoint B
```

## 23. Final Merge Recommendation

```text
Product commit: 1c5148779624910f1c6072d95d6c6f6822f631e6
Verdict: FAIL
Merge recommendation: DO NOT MERGE
Owner observation complete: NO (Checkpoint A completed and failed; B-E not reached)
Required clients covered: MCP protocol verification only
Skipped clients: Claude Code, WorkBuddy / CodeBuddy
Blocking defects: D0-UX-001, D0-CODEX-002
Acceptance docs synchronized: YES
Temporary evidence cleaned: PENDING remote confirmation
```

## 24. Sign-off

```text
Codex executor: Codex
Owner confirmation: Checkpoint A received; result FAIL
Acceptance date: 2026-07-30
Report branch: acceptance/pr60-memory-quality-trial-1c514877
Report commit: recorded in LOCAL_EXECUTION_RESULT.md after first remote push
```
