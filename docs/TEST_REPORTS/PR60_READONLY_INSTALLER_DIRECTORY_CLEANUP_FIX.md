# PR60 Read-only Installer Directory Cleanup Fix

## Failure

The new `623d3c9d` task began by dry-running the product cleanup utility against the exact previous `PR60-MEMORY-TRIAL-05376996` root. Authorization passed and listed 11,401 entries. Explicit execution partially progressed, then stopped with:

```text
failed to remove .../profile/User/AppData/Roaming/Microsoft/Windows/Start Menu/Programs: [WinError 5] Access denied
```

Read-only inspection showed that the empty normal directory had `ReadOnly, Directory` attributes. No port or LingJi process was active. The old root remained present, so cleanup was correctly not reported as PASS.

## Root Cause and Repair

The cleanup utility made regular files writable before unlinking but called `os.rmdir` on normal directories without first removing their Windows read-only attribute.

The repair calls the existing narrow `_make_writable` helper immediately before `os.rmdir` for normal directories only. Reparse points and links remain in their existing branch and are never traversed or chmod-followed. Authorization, exact-root validation, direct-child validation, task identity, and manifest-first behavior are unchanged.

## Acceptance

| Gate | Result |
|---|---|
| Read-only installer-directory regression | PASS — `13 passed` |
| Complete Python suite | PENDING |
| Desktop smoke/build | PENDING |
| Rust/Tauri | PENDING |
| Unified release | PENDING |
| Exact old-root cleanup retry | PENDING |

No manual recursive delete, wildcard, production path, Vault, neighboring directory, or unknown worktree is in scope.
