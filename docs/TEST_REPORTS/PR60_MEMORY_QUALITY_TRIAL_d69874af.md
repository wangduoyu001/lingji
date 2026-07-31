# PR60 Memory Quality Trial — Codex Acceptance Report

## 1. Executive Verdict

```text
Verdict: FAIL
Merge recommendation: DO NOT MERGE
Product commit: d69874afd8def42a40c4a5cc5e678a71921d44b5
Artifact: lingji-windows-0.1.0-d69874af
Artifact ID: 8762312712
Report commit: PENDING
```

Day 0 stopped at the mandatory local `release` gate. No installer was run, no desktop UI was opened, and no real data was read or imported.

## 2. Product and Artifact Identity

| Item | Expected | Actual | Verdict |
|---|---|---|---|
| Repository / PR | wangduoyu001/lingji / #60 | Matched | PASS |
| Product commit | d69874afd8def42a40c4a5cc5e678a71921d44b5 | PR head and product worktree matched | PASS |
| Artifact / ID | lingji-windows-0.1.0-d69874af / 8762312712 | Remote metadata matched | PASS |
| ZIP SHA256 | 6bf1f591502617c400ce482f6beb0d5e430a172cd036137bb4a39cae2cbf4cb4 | Matched | PASS |
| Installer SHA256 | d62867b7b7c90bee8273b3cf5720f53099c266897ce95d0e42224deae31bf262 | Matched | PASS |
| Portable EXE SHA256 | a852079b43b2f4020cb66942f44f1a5035633b65d3ff4122c2613c5ea7440a69 | Matched | PASS |
| Manifest SHA256 | d78a91153b62bcf641bcbbdbc41819283fe0dbc5deff2cdab64cdffcea3e6c87 | Matched | PASS |
| Sidecar EXE SHA256 | 20fe548e1be5cff5d1a34852f4fc0e223abb218eef1e51418724a6723e180599 | Declared in matched manifest; executable extraction not reached after gate failure | NOT_TESTED |

## 3. Environment Cleanup and Isolation

- Historical task root was dry-run then deleted with the allowlisted cleanup tool: 15,628 files and 2,227 directories; no reparse points were removed.
- The second historical target was absent.
- Ports 8766 and 8767 were free before testing.
- Product and report worktrees were isolated from the main worktree.
- No Production DataRoot, Vault, Core Memory, user client configuration, or real data was accessed.

## 4. CI and Automated Tests

| Test | Result | Evidence |
|---|---|---|
| Required remote workflows | PASS | acceptance-doc-sync #43, local-execution-handoff #35, tests #1138, P0 Windows Gate #258, Windows Desktop Release Baseline #142 succeeded for the product commit. |
| Cleanup tool unit tests | PASS | 6 passed. |
| Acceptance sync and handoff checks | PASS | Both repository checks passed. |
| `release` gate, initial attempt | SETUP BLOCKER RESOLVED | Desktop smoke lacked local `tsx`; dependencies were installed only in the isolated product worktree. |
| `release` gate, rerun | FAIL | `python-full`: 1 failed, 575 passed, 10 skipped, 2 warnings, 3 subtests passed. |

## 5. Blocking Defect

```text
Defect ID: D0-AUTO-001
Severity: P1
Affected scope: Mandatory release validation / Day 0 entry gate
Reproduction: Run .\scripts\validate.ps1 -Mode release in the exact product worktree after installing its declared local npm dependencies.
Expected: The full Python suite passes.
Actual: tests/test_brain_status_e2e.py::TestBrainStatusApiContract::test_frontend_dist_exists requires at least two JavaScript bundles, while the built dist contains one index-*.js bundle.
Evidence: 1 failed, 575 passed, 10 skipped; public summary and hash manifest in this report commit.
Data/security impact: No data was accessed or changed because installation and Day 0 UI work were not started.
Required fix: Align the frontend build output with the enforced test contract, or correct the contract with a separately reviewed product change and passing release gate.
Retest scope: Full release gate, Artifact integrity, Day 0, owner checkpoints, then explicitly authorized real-data stages.
```

## 6. Day 0 and Trial Result

```text
Day 0: FAIL
Stage 1: NOT_RUN
Stage 2: NOT_RUN
Real-data authorization: false
Quality questions: 0
Owner sample questions: 0
quality_score: NOT_RUN
source_accuracy: NOT_RUN
false_positive_rate: NOT_RUN
Codex MCP success rate: NOT_RUN
Production pollution: 0 observed (no Product runtime started)
```

All owner checkpoints were not requested because the mandatory automatic gate failed before installation. D0-UX-001, D0-CODEX-002, Embedding/Qdrant diagnostics, MCP calls, candidate review, restart, and Windows reboot remain untested and must be repeated after the blocking gate is fixed.

## 7. Security and Cleanup

- Public evidence contains only identities, test counts, and the failed assertion; no token, private content, configuration, screenshot, database, or absolute local path is committed.
- Temporary Artifact, logs, fixture directories, npm cache, and both task worktrees must be removed after this report receives its first remote confirmation.

## 8. Final Recommendation

```text
Product commit: d69874afd8def42a40c4a5cc5e678a71921d44b5
Verdict: FAIL
Merge recommendation: DO NOT MERGE
Owner observation complete: NOT_REQUIRED (automatic Day 0 gate failed before installation)
Required clients covered: none
Skipped clients: all, due to D0-AUTO-001
Blocking defects: D0-AUTO-001
Acceptance docs synchronized: YES
Temporary evidence cleaned: PENDING
```

