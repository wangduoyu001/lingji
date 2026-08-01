# PR60 Memory Quality Trial — Day 0 Failure Report

## Executive verdict

```text
Task: PR60-MEMORY-QUALITY-TRIAL-3E24E65C
Verdict: FAIL
Blocking defect: FAIL_DATA_ROOT_ISOLATION
Product commit: 3e24e65ce12bfa22b5c9193d65500648ebf45729
Artifact: 8820695386 / lingji-windows-0.1.0-3e24e65c
Merge recommendation: DO NOT MERGE
```

Day 0 must run only against `D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-3e24e65c\product` in the `acceptance` workspace. After the initial isolated startup screen, a later reinspection of the Desktop showed that its running Runtime was bound to a pre-existing acceptance root outside the task root. The exact external path is intentionally omitted. This is not the task-scoped DataRoot, so the trial stopped immediately and did not enter Stage 1.

The evidence does not establish whether that binding resulted from an owner action between checkpoints or from the Desktop process sandbox not retaining the temporary environment. Neither explanation is assumed. Regardless of cause, the observed root does not meet the task identity contract.

## Identity and package checks

| Check | Expected | Actual | Result |
|---|---|---|---|
| Product branch | `feature/unified-ai-memory-connectors` | `3e24e65ce12bfa22b5c9193d65500648ebf45729` | PASS |
| PR #60 | Draft, matching Head | Draft, matching Head | PASS |
| Artifact | `8820695386`, `lingji-windows-0.1.0-3e24e65c` | Exact match | PASS |
| ZIP SHA256 | `649de2e03bde0ec491f8c828fdfac73d1a9539877c72ecd5199c7be407ee0e98` | Exact match | PASS |
| Installer / portable / manifest | Task hashes | Exact match | PASS |
| Installed sidecar | Task hash | Exact match | PASS |
| Build metadata | commit `3e24e65…`, version `0.1.0`, channel `pr`, NSIS, unsigned | Exact match | PASS |
| Historical Artifact reuse | Prohibited | Not performed | PASS |

## Day 0 evidence

```text
Pre-cleanup task target and legacy task directories: absent
8766 / 8767 before launch: unused
LingJi process before launch: none
Bootstrap pointer: backed up by SHA256 only; contents not read
Bootstrap pointer after stop: same SHA256 as backup
Installer: fixed Artifact installer, isolated task-root installation, exit 0
Initial UI: no black console; version 0.1.0 / pr / 3e24e65c visible; non-C DataRoot configuration clearly required
Owner observation: no black console and non-C requirement confirmed; owner also reported no clear one-click import / automatic AI-memory discovery entry on the unconfigured first screen
Later runtime root: external pre-existing acceptance root, not the task root
Post-stop 8766 / 8767 listeners: none
Post-stop LingJi / Sidecar / MCP processes: none
Real-data body reads: 0
Stage 1: NOT_RUN
Stage 2: NOT_RUN
```

The only data exposed in the later UI reinspection was status metadata (workspace label, runtime health, model inventory and count). No scripts, chats, Obsidian documents, Codex sessions, JSONL, or other real bodies were opened or read. Because an external acceptance root was started, the task cannot assert zero external-acceptance runtime side effects; this is part of the blocking condition.

## Blocking defect

```text
Defect ID: FAIL_DATA_ROOT_ISOLATION
Severity: P0
Affected scope: Day 0 Desktop bootstrap and Runtime binding
Expected: Desktop and Runtime bind only to the task-scoped non-C acceptance root.
Actual: Later Desktop reinspection showed a Runtime bound to an existing acceptance root outside the task root.
Data/security impact: no real body was read, but task isolation is not provable and external acceptance side effects cannot be ruled out.
Required fix: make the Desktop startup path deterministically bind to an explicitly selected task root, expose that binding before Runtime start, and prevent reuse of an external bootstrap root.
Retest scope: a new current ACTIVE Day 0 task with fresh Artifact identity and an owner checkpoint.
```

## Final status

```text
Day 0: FAIL
Owner checkpoints: not completed
Real-data authorization: false
Stage 1 / Stage 2: NOT_RUN
Production body reads: 0
Merge recommendation: DO NOT MERGE
```

## Report readback and cleanup

The initial failure report commit `b201dc9edeae8c178ae17c04530f409dbd5ebd16` and PR #60 comment [`#5152376424`](https://github.com/wangduoyu001/lingji/pull/60#issuecomment-5152376424) were remotely reread before cleanup. The approved task cleanup then removed the exact current task root after a dry-run whose 317 entries were all under that root; it removed 217 files and 100 directories. The shared parent directory was retained.

After cleanup there was no listener on `8766` or `8767`, and no LingJi Desktop, Sidecar, or MCP process. The report-only worktree is retained just long enough to push and reread this final receipt, then is unregistered.
