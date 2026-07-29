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
- [ ] Listed new automatic tests.
- [ ] Listed real-machine tests.
- [ ] Listed owner visual/UX observations.
- [ ] Listed regressions, cleanup and rollback.
- [ ] Declared capabilities not included in this PR.

## Validation

```text
Focused validation:
Full validation:
Release validation:
Exact tested commit:
Artifact:
Owner-machine acceptance:
```

- [ ] No test was deleted, weakened or converted to skip to obtain PASS.
- [ ] Successful logs were reduced to summaries; failing evidence is retained only as needed.
- [ ] Old local validation outputs and temporary artifacts are cleaned automatically.

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
Merge allowed: YES / NO
```

Do not mark the PR ready or merge it while mandatory owner-machine acceptance is pending.