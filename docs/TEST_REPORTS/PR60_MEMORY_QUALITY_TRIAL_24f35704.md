# PR60-MEMORY-QUALITY-TRIAL-24F35704 Owner + Codex Full Acceptance Report

## 1. Executive Verdict

```text
Verdict: FAIL
Merge recommendation: DO NOT MERGE
Product commit: 24f3570440437f57b6a62e54d409577ed40b6c14
Artifact: lingji-windows-0.1.0-24f35704
Artifact ID: 8832010437
Report commit: PENDING
```

Day 0 stopped on P0 `LJ-24F35704-P0-QDRANT-LOCK`. The synthetic ChatGPT export was discovered without opening its body, then its single authorized import completed automatically. However, the MCP-published vector snapshot still reports `embedded_store_locked`; semantic retrieval is unavailable while the embedded Qdrant directory is accessed by another client. No real owner data was read, no permanent-memory decision was taken, and no Stage 1 or Stage 2 action ran.

## 2. Product and Artifact Identity

| Item | Expected | Actual | Verdict |
|---|---|---|---|
| Product commit | `24f3570440437f57b6a62e54d409577ed40b6c14` | Same | PASS |
| Artifact | `lingji-windows-0.1.0-24f35704` | Same | PASS |
| Artifact ID | `8832010437` | Same | PASS |
| ZIP SHA256 | `ac3c329e…f35fcd45` | Same | PASS |
| Installer SHA256 | `e89a10c1…772368ce` | Same | PASS |
| Portable SHA256 | `5139cef2…16d8341f` | Same | PASS |
| Sidecar SHA256 | `4cbf0a62…50061b03` | Same in build metadata and core manifest | PASS |
| Build metadata SHA256 | `fd32179b…248fb6c0` | Same | PASS |

Required CI for the exact product commit passed: `local-execution-handoff` 30743102211, `acceptance-doc-sync` 30743102181, `tests` 30743102183, `P0 Windows Gate` 30743102202, and `Windows Desktop Release Baseline` 30743102197.

## 3. Environment, Startup, and UI

- Previous `3739c42f` task-root cleanup: authorized dry-run and execute both `PASS / nothing_to_remove`.
- 8766 and 8767 were free before startup. The global bootstrap was only hash-recorded; its hash remained `73DD26CD96025F9CE0F6F009D4AB01E883BF5246040CA721ABD42D4EF0D0A`.
- The new Artifact installed into the isolated non-system-drive task root with exit code 0.
- First startup recovered within the 45-second gate: Desktop, authenticated 8766, and authenticated MCP 8767 were available; runtime ping returned the exact isolated DataRoot and `acceptance` workspace.
- Desktop observation showed `DataRoot绑定已验证`, `启动契约锁定`, binding `PR60-24f35704-DAY0`, runtime version `0.1.0 / pr / 24f35704`, and a single managed MCP child. The owner did not need to check a console window for this run.

## 4. Automatic Discovery and One-Step Import

| Check | Actual | Verdict |
|---|---|---|
| Synthetic files | ChatGPT JSON, Codex Work Report JSON, unrelated JSON, unrelated ZIP; all inside isolated Downloads | PASS |
| Pre-authorization safety | `metadata_only=true`, `content_read=false`, candidate count `2`, no absolute paths in returned candidates | PASS |
| Negative samples | Neither unrelated JSON nor unrelated ZIP became a candidate | PASS |
| Supported candidates | Exactly ChatGPT and Codex, one guided action each | PASS |
| Authorized ChatGPT import | One authorization created `LJ-JOB-DA524070DC52`; no path entry or second submission | PASS |
| Queue execution | Completed automatically on first attempt | PASS |

## 5. Blocking Defect

```text
Defect ID: LJ-24F35704-P0-QDRANT-LOCK
Severity: P0
Affected scope: embedded Qdrant ownership and semantic retrieval in the packaged acceptance runtime
Reproduction: install exact Artifact 8832010437 in a fresh isolated root; start with the locked startup contract; authorize one synthetic ChatGPT export; read the MCP-published memory status snapshot.
Expected: MCP is the sole embedded Qdrant owner; after import, vector and semantic status are coherent and no lock error occurs.
Actual: the snapshot producer identifies the MCP process, but vector state is `unavailable`, reason `embedded_store_locked`, semantic retrieval is false, and the Qdrant client reports that the embedded directory is accessed by another instance.
Data/security impact: semantic retrieval cannot be trusted; Day 0 must stop. No owner content was exposed.
Required fix: identify and eliminate the remaining second embedded-Qdrant opener, then rebuild a new Artifact and rerun a new task identity from Day 0.
Retest scope: fresh Artifact identity, first startup, one authorized synthetic import, MCP/Control snapshot consistency, and real Codex MCP gate.
```

The owner lock diagnostic is present and held by `packaged_mcp_http`; the lock therefore does not prove that no other client opened the embedded Qdrant storage.

## 6. Not Run After P0 Stop

- Synthetic Codex import, manual selected-file import, candidate approve/reject, lifecycle restarts, Windows reboot, and real Codex MCP call.
- All owner checkpoints A-F.
- Stage 1 and Stage 2.
- Any real ChatGPT, Codex, Obsidian, Vault, or other owner content.

## 7. Security, Cleanup, and Remote Verification

- Production pollution: `0` observed.
- Real-data authorization: `false`; real-data read: `0`.
- Report contains no token, private body, database, installer, or owner path inventory.
- First remote report verification and task-root cleanup: PENDING at this report commit; the result receipt will be updated only after those steps complete.

## 8. Final Merge Recommendation

```text
Product commit: 24f3570440437f57b6a62e54d409577ed40b6c14
Verdict: FAIL
Merge recommendation: DO NOT MERGE
Owner observation complete: NO (P0 stopped before checkpoint)
Required clients covered: packaged Desktop, Control API, MCP, synthetic ChatGPT discovery/import
Skipped clients: real Codex MCP and all owner-data clients
Blocking defects: LJ-24F35704-P0-QDRANT-LOCK
Acceptance docs synchronized: YES
Temporary evidence cleaned: PENDING
```
