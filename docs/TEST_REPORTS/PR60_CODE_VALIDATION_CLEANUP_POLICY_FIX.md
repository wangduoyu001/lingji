# PR #60 Code Validation Cleanup Policy Fix

Status: IMPLEMENTED, CI PENDING

## 1. Problem

`PR60-CODE-RELEASE-VALIDATION-A90A18A6` completed all 15 code, build and Windows release suites, but final cleanup was blocked.

The task used:

```text
root: D:\codex\LingJiValidation
target: PR60-CODE-a90a18a6
```

The cleanup tool only recognized three historical `LingJiAcceptance` directory names. It rejected the current code-validation directory before attempting deletion.

## 2. Root Cause

`scripts/cleanup_acceptance_workspace.py` used a static `ALLOWED_TARGETS` set tied to earlier memory-quality tasks. Adding each future task directory manually would keep producing the same failure and would turn task creation into a cleanup-code maintenance ritual.

## 3. Implementation

The cleanup policy now derives the exact authorized root family and target directory from a supported task ID.

Supported contracts:

```text
PR<pr>-CODE-RELEASE-VALIDATION-<8 hex>
→ root name: LingJiValidation
→ target name: PR<pr>-CODE-<lowercase 8 hex>

PR<pr>-MEMORY-QUALITY-TRIAL-<8 hex>
→ root name: LingJiAcceptance
→ target name: PR<pr>-MEMORY-TRIAL-<lowercase 8 hex>
```

The two historical PR #60 `1c514877` directories remain explicitly authorized only for the known `D69874AF` memory-quality cleanup task.

## 4. Safety Properties

The tool still refuses:

- unsupported task IDs;
- a root family that does not match the task type;
- deletion of the root itself;
- targets outside the supplied root;
- nested targets deeper than one direct child;
- target names that do not exactly match the task-derived identity;
- deletion without explicit `--execute`;
- following links or Windows reparse points.

No wildcard target deletion was introduced.

## 5. Modified Files

```text
scripts/cleanup_acceptance_workspace.py
tests/test_cleanup_acceptance_workspace.py
docs/TEST_REPORTS/PR60_CODE_VALIDATION_CLEANUP_POLICY_FIX.md
```

## 6. Tests

Focused test command:

```text
python -m pytest -q tests/test_cleanup_acceptance_workspace.py
```

Local isolated result before repository submission:

```text
10 passed
```

Coverage includes:

- current code-release validation directory accepted;
- mismatched code identity rejected;
- wrong root family rejected;
- unsupported task rejected;
- historical memory cleanup preserved;
- dry-run preserves files;
- execute removes only the authorized target and preserves adjacent data.

## 7. Recovery Plan for the Blocked Report

After this fix is merged to `master`, Codex must not rerun the 15 release suites. It must only:

1. pull the cleanup fix from `master` without changing the validated product worktree identity;
2. run a dry-run against `D:\codex\LingJiValidation\PR60-CODE-a90a18a6`;
3. verify the manifest contains only task-created files;
4. execute the cleanup;
5. verify the temporary root is absent;
6. update the existing report and result receipt to final `PASS`;
7. push and remotely reread the report branch and PR comment.

The successful release evidence from product commit `a90a18a66ffba157c01367ba70bfec98f58798e2` remains valid.

## 8. Data and Product Impact

No product runtime, UI, Vault, database, Qdrant collection, AI-client configuration or real user material is changed. This is a task-governance and cleanup-safety fix only.

## 9. Rollback

Revert the cleanup policy and its tests. Do not restore a broad wildcard or delete the existing safety checks.
