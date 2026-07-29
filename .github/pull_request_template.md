## Goal

Describe the user-visible outcome and the exact scope. Do not describe intentions as completed work.

## Architecture and data boundaries

- Affected modules:
- Existing authority reused:
- New database / queue / API / UI / config authority: `none` or explain
- Production / Acceptance impact:
- Security and privacy impact:

## Acceptance synchronization

- [ ] Read `docs/ACCEPTANCE/README.md`.
- [ ] Updated `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md` in this PR.
- [ ] Updated `docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md` when user flow, runtime, install, data, connector, security or release behavior changed.
- [ ] When local execution is required, updated `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md` with one exact ACTIVE task.
- [ ] Listed new automatic tests.
- [ ] Listed real-machine tests.
- [ ] Listed owner visual/UX observations.
- [ ] Listed regressions, cleanup and rollback.
- [ ] Declared capabilities not included in this PR.

## Local execution handoff

```text
Task ID:
Task document status: ACTIVE / NOT_REQUIRED
Product commit:
Artifact:
Report branch:
Report path:
Result receipt path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
Cleanup before required: YES / NOT_REQUIRED
Cleanup after required: YES / NOT_REQUIRED
Remote re-read required: YES / NOT_REQUIRED
```

- [ ] User is not required to copy commands, push Git, upload reports or clean temporary files.
- [ ] Codex must read the task document instead of chat history.
- [ ] `git push` is followed by remote branch, commit, report, receipt and PR-comment verification.
- [ ] Final result receipt records cleanup before and after execution.

## Validation

```text
Focused validation:
Full validation:
Release validation:
Exact tested commit:
Artifact:
Owner-machine acceptance:
Local execution handoff CI:
```

- [ ] No test was deleted, weakened or converted to skip to obtain PASS.
- [ ] Successful logs were reduced to summaries; failing evidence is retained only as needed.
- [ ] Old local validation outputs and temporary artifacts are cleaned before execution.
- [ ] Temporary artifacts, logs, screenshots, fixtures, checkpoints, config copies and worktrees are cleaned after remote report verification.

## Documentation

- [ ] Updated the existing authoritative document instead of creating a duplicate summary.
- [ ] Added or updated a Markdown test report for substantial tested changes.
- [ ] Updated `docs/PROJECT_STATUS.md` only when current project status changed.
- [ ] Updated `docs/CHANGELOG.md` only for user-visible or release-significant changes.

## Merge boundary

```text
Implemented and tested:
Implemented but not owner-tested:
Planned only:
Known blockers:
Remote report verified: YES / NO / NOT_REQUIRED
Result receipt COMPLETED: YES / NO / NOT_REQUIRED
Cleanup before: PASS / FAIL / NOT_REQUIRED
Cleanup after: PASS / FAIL / NOT_REQUIRED
Merge allowed: YES / NO
```

Do not mark the PR ready or merge it while mandatory owner-machine acceptance is pending, the remote report cannot be re-read, the result receipt is incomplete, or local cleanup has not passed.
