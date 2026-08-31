# Old Acceptance Closeout — owner memory detail drilldown

Date: 2026-08-31
Repository: `wangduoyu001/lingji`
Acceptance branch: `acceptance/owner-ui-source-filter-repair-4ce1e00a`
Product commit: `4ce1e00acb17bc5e4e4c183f58d30551ef76b101`
Correction commit: `94461d56c64f31e1af6c7cdece51e959ddc0e8b1`
Task instruction commit: `8bc1bce20636135018df302ab931cb37707d6376`

## Final classification

```text
Task status: COMPLETED
Acceptance verdict: FAIL
Owner result: OWNER_MEMORY_DETAIL_DRILLDOWN_REQUIRED
Release status: NOT_RELEASE_READY
Merge: DO NOT MERGE
Task file status: IDLE
```

The exact-product macOS arm64 candidate was built, strictly signed, installed as a whole bundle,
started against an isolated synthetic root, and traversed by the root agent. The API/source-filter
contract passed its bounded checks: authenticated 8766 returned 200, unauthenticated access 401,
8767 was absent, current memory was 37 cards split 20+17, history was 3, permanent records 13,
conversations 3, messages 36, and there was exactly one high-risk owner pending action. Raw
discovery was 5 with one `not_found` archive; ordinary visible/found was 4 and Codex cards was 1.

The latest owner feedback did not accept the memory experience as sufficiently understandable.
The owner-facing detail drilldown must make the persisted conclusion, its development/context, and
its verifiable source clear. A bounded technical traversal is not a substitute for that owner
acceptance. This candidate therefore closes as a measured failure and must not be released or
merged.

## Runtime closeout

Before stopping, the following exact processes were verified by path and isolated DataRoot:

```text
37148 /Applications/灵机.app/Contents/MacOS/lingji-control-center
37132 /Applications/灵机.app/Contents/Resources/lingji-core.exe --data-root /tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a/data-root/acceptance --workspace acceptance --host 127.0.0.1 --port 8766
```

Only PIDs `37148` and `37132` were sent `TERM`. Their dedicated LaunchAgent labels were booted
out. A post-stop check found no 8766 or 8767 listener and no surviving target PID. No unrelated
process was terminated.

## Isolation and preservation

The new acceptance root remains intact:

`/tmp/LingJiAcceptance/owner-ui-source-filter-4ce1e00a`

It contains the isolated DataRoot, Vault, source fixture, evidence, and pre-install whole-app
backup. The failed first packaging attempt and displaced failed installation were also preserved.
The prior acceptance roots (`6ea11e4`, `43009a0`, `6baf4ee6`, and `b299e5b`) were not deleted,
overwritten, or reused. No production Vault, real chat, real credentials, or user configuration
was read or modified.

## Artifact evidence

```text
Installed main SHA256: 6fb5e44a27dc65108d4b91ddb5af83cb341a967a9fe9e88b1b1b5a6cec1291a3
Installed MacOS sidecar SHA256: fb83470f1b29c97cb40a342e82f4ee11ea4b7d897907964dd880b184b23f1dbb
Installed Resources sidecar SHA256: 9b857ed22bc9fcb2e3f99ec515880f17e0232d36424c94ece6dad398147b388c
DMG SHA256: 351557a1efd38c66941ba80ed65616a515852fe5e689a220428cd5363dd11991
Strict deep codesign: PASS
Architectures: main and both sidecars arm64
```

Private runtime and seed evidence is retained under the acceptance root's `evidence/` directory;
the public report contains no token, Authorization value, raw chat body, or private credential.

## Required next action

Implement and independently review the owner-facing memory detail drilldown at the product level,
then create a fresh acceptance task/root and rebuild from the successor product SHA. The next
acceptance must re-prove conclusion, development/context, source citation, current/history
filtering, and owner-readable next action before any release or merge decision.

Remote branch/content verification: `PENDING_UNTIL_CLOSEOUT_COMMIT_AND_PUSH`.
