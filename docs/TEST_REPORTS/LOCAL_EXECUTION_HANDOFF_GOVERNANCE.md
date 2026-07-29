# Local Execution Handoff Governance

## Goal

Make repository documents the only communication channel between ChatGPT / the primary developer agent and local Codex for real-machine execution.

The owner only needs to say:

```text
去看任务单干活
```

or:

```text
Codex 已经完成
```

The owner is not responsible for copying commands, selecting Git branches, pushing reports, checking remote visibility or cleaning temporary files.

## Canonical documents

```text
docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md
docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
```

`LOCAL_EXECUTION_TASK.md` contains one exact ACTIVE task, including product identity, Artifact identity, report branch/path, required execution scope, cleanup-before rules, remote verification commands and cleanup-after rules.

`LOCAL_EXECUTION_RESULT.md` is the fixed receipt that Codex updates on the report branch. It records verdict, report-content Commit, owner observation, remote re-read checks, cleanup-before result, cleanup-after result and temporary-root removal.

## Hard gates

Added:

```text
scripts/check_local_execution_handoff.py
tests/test_local_execution_handoff.py
.github/workflows/local-execution-handoff.yml
```

The checker validates:

- task/result identity consistency;
- exact 40-character product and instruction Commit fields;
- canonical report branch and report paths;
- cleanup-before and cleanup-after requirements;
- remote branch, Commit, report, result receipt and PR-comment verification;
- owner-observation status;
- ISO 8601 execution timestamps;
- `COMPLETED` only when all mandatory fields pass;
- `acceptance/**` branches cannot finish with a pending receipt.

## Execution sequence

```text
read ACTIVE task
→ clean previous local acceptance garbage
→ verify processes and ports are clean
→ execute exact product task
→ generate report and public evidence
→ push report-content commit
→ re-read remote branch, commit and report
→ add and re-read PR comment
→ clean local artifacts, logs, screenshots, fixtures, checkpoints, config copies and worktrees
→ update result receipt
→ push and re-read remote receipt
→ remove temporary root
→ report completion to owner
```

Running `git push` alone is never considered successful submission.

## Data safety

Cleanup must never delete:

- Production DataRoot;
- owner formal Acceptance data;
- Obsidian Vault;
- formal memory;
- owner Codex, Claude or WorkBuddy configuration.

Only task-scoped temporary data and artifacts may be removed.

## Current active task

The current task document assigns PR #60 owner re-acceptance for product Commit:

```text
1c5148779624910f1c6072d95d6c6f6822f631e6
```

The report branch is created from current `master` governance so it contains the task/result protocol and CI gate, while the product worktree remains pinned to the exact product Commit.

## Validation

Required commands:

```powershell
python scripts/check_local_execution_handoff.py --ref-name master
python -m pytest -q tests/test_local_execution_handoff.py
python scripts/check_acceptance_sync.py
```

Required GitHub workflows:

```text
local-execution-handoff
acceptance-doc-sync
tests
```

## Conclusion

```text
TASK MAILBOX: IMPLEMENTED
RESULT RECEIPT: IMPLEMENTED
REMOTE RE-READ GATE: IMPLEMENTED
CLEANUP BEFORE/AFTER GATE: IMPLEMENTED
OWNER GIT RESPONSIBILITY: NONE
```
