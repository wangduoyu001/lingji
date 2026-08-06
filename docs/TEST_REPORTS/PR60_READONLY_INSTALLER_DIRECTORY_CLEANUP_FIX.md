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
| Complete Python suite | PASS — unified release `python-full` |
| Desktop smoke/build | PASS / PASS |
| Rust/Tauri | PASS |
| Unified release | PASS — `15/15`, exact commit `018e7d25327846cce08bb9f25cd3faf1db13c2ac` |
| Exact old-root cleanup retry | PENDING |

No manual recursive delete, wildcard, production path, Vault, neighboring directory, or unknown worktree is in scope.

The first unified-release attempt stopped after Python full because the new worktree had not yet installed its lock-file Desktop dependencies (`tsx` was absent). After `npm ci`, the complete unified release was rerun from the beginning and passed; the incomplete attempt is not counted as acceptance evidence.

Release identity and artifacts:

- Summary branch: `codex/pr60-cleanup-readonly-dir-623d3c9d`
- Summary commit: `018e7d25327846cce08bb9f25cd3faf1db13c2ac`
- Installer SHA-256: `fb10b6d2da39efff5161a14f332193ed2f1579b91ddf9a8540b41cf21c000d85`
- Portable executable SHA-256: `aca0e5b2787e2cb8870ae34af238b914677feaaf39814013c249d764a92fae24`
- Sidecar manifest SHA-256: `4dc8db745065f16c13a565e78e8129ebd2ad123ccf20175f49eee5f7f37b3479`
- Build metadata SHA-256: `52e2fee0fb3d7e78f6ead84809950c1d71906503ab94cd39698bfc3bf9632d3c`
- SHA256SUMS SHA-256: `c57969d2aa9fd2d540302dddf2a14606cefc4b2ad68ff183ba0007922546ac71`
