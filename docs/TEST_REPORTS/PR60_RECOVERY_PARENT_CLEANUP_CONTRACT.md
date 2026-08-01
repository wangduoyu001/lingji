# PR #60 Recovery Parent Cleanup Contract Correction

Status: IMPLEMENTED

## 1. Problem

The code-release validation for product commit `a90a18a66ffba157c01367ba70bfec98f58798e2` passed all required code, build and release checks. The recovery task also removed the task-specific validation root and recovery worktree.

The task nevertheless ended `BLOCKED_POST_CLEANUP` because it additionally required deletion of the empty shared parent directory:

```text
D:\codex\LingJiRecovery
```

The execution environment correctly refused to delete that root.

## 2. Root Cause

The recovery task confused two different concepts:

1. task-owned directories that must be removed;
2. a shared external root that only hosts temporary recovery worktrees.

A shared root may remain empty after all task-owned children are removed. Its presence is not task residue.

## 3. Correct Contract

Cleanup passes when all task-owned resources are absent:

```text
D:\codex\LingJiValidation\PR60-CODE-a90a18a6
D:\codex\LingJiRecovery\PR60-CODE-a90a18a6-report
```

The corresponding Git worktree registrations, task processes, listeners and orphan MCP instances must also be absent.

The shared parent may remain:

```text
D:\codex\LingJiRecovery
```

No cleanup tool or task should attempt to delete that shared root merely because it is empty.

## 4. Safety Decision

The repository must not broaden the cleanup tool to delete a configured root directory. Refusing root deletion is a required safety property.

The previous `BLOCKED_POST_CLEANUP` therefore reflects an incorrect acceptance criterion, not a product failure, release failure or cleanup-tool failure.

## 5. Evidence Used

Remote report branch:

```text
acceptance/pr60-code-release-validation-a90a18a6
```

Current report head at the time of correction:

```text
808bcfb30aff04ac1cd05ce9fcf2fe3c48eaf59d
```

The report confirms:

- 15 release suites passed;
- focused cleanup tests passed;
- the original task temporary root was removed;
- the task-specific recovery worktree was removed;
- `local_temp_root_absent` is true;
- only the empty shared recovery parent remained.

## 6. Files Updated

```text
docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md
docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
docs/TEST_REPORTS/PR60_RECOVERY_PARENT_CLEANUP_CONTRACT.md
```

## 7. Finalization Rule

Codex must not rerun product tests or release packaging. It only updates the existing report branch and PR comment to record:

```text
status: COMPLETED
verdict: PASS
cleanup_after: PASS
local_temp_root_absent: true
```

The report must state that retaining the shared recovery parent is compliant with the corrected safety boundary.

## 8. Product and Data Impact

None.

No product code, Desktop UI, runtime, installer, Vault, database, Qdrant collection, user configuration or real user material is changed.

## 9. Regression Prevention

Future tasks must distinguish:

```text
task_temp_root
recovery_worktree_path
shared_recovery_root
```

Only task-owned paths are cleanup requirements. Shared roots must never be required deletion targets.
