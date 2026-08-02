# PR60-MEMORY-QUALITY-TRIAL-05376996 Owner + Codex Full Acceptance Report

## 1. Executive Verdict

```text
Verdict: FAIL
Merge recommendation: DO NOT MERGE
Product commit: 053769965cf767cfe5221ffa4334b189bedb4d7d
Artifact: lingji-windows-0.1.0-05376996
Artifact ID: 8832376546
Report commit: PENDING
```

Day 0 stopped before fixtures, imports, Codex client registration, candidate lifecycle, reboot, or any real-data read.  The isolated runtime started with an already healthy embedded collection containing 11 vectors, although no synthetic source had been created.  This violates the empty-store truth gate and is a P0 blocker.

## 2. Product and Artifact Identity

| Item | Expected | Actual | Verdict |
|---|---|---|---|
| Repository | wangduoyu001/lingji | wangduoyu001/lingji | PASS |
| PR | #60 (Draft) | #60 (Draft; not merged) | PASS |
| Product commit | 053769965cf767cfe5221ffa4334b189bedb4d7d | same | PASS |
| Artifact | lingji-windows-0.1.0-05376996 | same | PASS |
| Artifact ID | 8832376546 | same | PASS |
| ZIP SHA256 | abb116cbca8e7ccc2d23e206ed3fdc1a764f5b36bd4209864c628539bda33b4b | same | PASS |
| Installer SHA256 | 8f4719e610ddab037044dee364de6e3b4990c37c18a56da8f3fca6e6480b3b4e | same | PASS |
| Portable SHA256 | a28169265e3f6eb16f9cb6102d4142b5e5c6d82a97e9c0bd7778e16571caae5e | same | PASS |
| Sidecar SHA256 | 8be47b40acf703454ffbec315c58f7a0f9c0d5250ab2156f554fb5b4a1025fb2 | same | PASS |
| Manifest SHA256 | c9778ddd6f4f782be2bcc43aa6d573b3a76518416aa718529f17fa2a627f73a5 | same | PASS |
| Build metadata SHA256 | 167cd2dadddf8d2e3f822729d5d08a1f81080f0fb37a3da9d23b353c5b76721e | same | PASS |

Build metadata contract: schema 5, version 0.1.0, channel `pr`, x86_64 Windows target, NSIS, unsigned, no first-run configuration, safe non-system-drive selection, startup binding contract, locked runtime identity, no external runtime adoption, real-content authorization, and no C-drive runtime data were all present and correct.

## 3. Acceptance Source and Cleanup

- Task: `PR60-MEMORY-QUALITY-TRIAL-05376996` from remote `master` commit `dff85844ced40c42cd1becb5a15747e85eff3b33`.
- Incremental source: the current Control-only Qdrant ownership recovery entry in `CHANGE_ACCEPTANCE_LOG.md`.
- Previous failed trial root: absent; the repaired cleanup utility returned `PASS / nothing_to_remove` and authorized scope.
- Before launch: no residual LingJi process and ports 8766/8767 were free.  The pre-existing global bootstrap was absent; it was not read or changed.
- Installation: isolated silent overwrite only; no production DataRoot, Vault, SQLite, Qdrant, Codex, ChatGPT, or other private content was read or changed.

## 4. Day 0 Results

| Check | Result | Evidence |
|---|---|---|
| Isolated installer and sidecar identity | PASS | all required SHA256 values matched |
| Locked DataRoot / workspace | PASS | authenticated runtime ping returned the task-bound root and `acceptance` |
| Local Control and MCP listeners | PASS | 8766 and 8767 listening; MCP state published its loopback endpoint |
| MCP unique memory owner | PASS | `memory-owner.json` reported `packaged_mcp_http`, held by the MCP PID |
| Control-only Qdrant access | PASS | no `embedded_store_locked` error after the Desktop opened the control surface |
| Empty-store truth before any fixture | FAIL | MCP snapshot was `healthy` with collection present and `vectors: 11` |
| Synthetic discovery/import | NOT_TESTED | prohibited after P0 gate failed; no fixture was created |
| Codex real MCP call | NOT_TESTED | prohibited after P0 gate failed |
| Candidate approve/reject | NOT_TESTED | prohibited after P0 gate failed |
| Restart / Windows reboot | NOT_TESTED | prohibited after P0 gate failed |
| Owner checkpoints A-F | NOT_REQUIRED | Day 0 failed before a valid owner checkpoint |

The snapshot producer was the same MCP instance that held the owner lock.  It stated that the collection existed, embedding was verified, semantic and lexical search were available, and vectors equaled 11.  This is internally consistent but violates the task's required pre-import state (`empty` / `collection_empty`, semantic unavailable, lexical available).  No personal content was introduced by this trial.

## 5. Blocking Defect

```text
Defect ID: LJ-05376996-P0-NONEMPTY-DAY0-STORE
Severity: P0
Affected scope: fresh isolated packaged Desktop / MCP memory initialization
Reproduction: create the mandated empty task root; install the exact Artifact; start once with the locked acceptance startup contract; do not create any fixture; inspect the MCP-published memory status.
Expected: before any import, the collection is empty or absent; semantic search is unavailable and lexical search remains available.
Actual: the MCP-published status is healthy, collection_exists=true, vectors=11, embedded semantic search available, and verified embedding activity.
Evidence: authenticated runtime ping, MCP owner diagnostic, and MCP-published memory status, all from the same isolated task root; no token or content is included in this report.
Data/security impact: an empty acceptance environment cannot prove that retrieval originates only from authorized sources.  Continuing could conceal preloaded or cross-run state.
Required fix: identify why a freshly bound acceptance DataRoot obtains 11 vectors before fixture creation; preserve MCP-only ownership and make the pre-import state truthful.
Retest scope: issue a new ACTIVE task with a new exact Artifact after the repair; do not reuse this Artifact or trial result.
```

## 6. Security, Scope, and Final Recommendation

- Tokens, Authorization values, databases, logs, screenshots, fixtures, and private content are not committed.
- Real-data authorization remains `false`; Stage 1 and Stage 2 did not run.
- Production-pollution count is 0; no Core Memory mutation was requested or performed.
- PR #60 remains Draft and must not merge.

```text
Product commit: 053769965cf767cfe5221ffa4334b189bedb4d7d
Verdict: FAIL
Merge recommendation: DO NOT MERGE
Owner observation complete: NO (not requested after P0 stop)
Blocking defects: LJ-05376996-P0-NONEMPTY-DAY0-STORE
Acceptance docs synchronized: YES
Temporary evidence cleaned: PENDING_REMOTE_CONFIRMATION
```
