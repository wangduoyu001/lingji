# MACOS-M5-PHYSICAL-ACCEPTANCE-C10D255 Final Report

## Executive Verdict

```text
Verdict: FAIL
Merge recommendation: DO NOT MERGE
Product commit: c10d25541ec8814179545e03f3c6709b7beeb283
Artifact: lingji-macos-arm64 / 灵机_0.1.0_aarch64.dmg
Artifact ID: 9030728866
```

The exact macOS arm64 artifact installs, starts an authenticated loopback Core, and cleans up correctly. It fails the mandatory first-use UX acceptance: the owner reported that the initial DataRoot configuration prompt was not understandable and that the remaining UI could not be understood. The live UI/API also reported `degraded` / `configuration_required`, not the required healthy state.

## Identity and Environment

| Item | Expected | Actual | Verdict |
|---|---|---|---|
| Repository | `wangduoyu001/lingji` | matched | PASS |
| Product commit | `c10d25541ec8814179545e03f3c6709b7beeb283` | matched Actions run 31288663236 | PASS |
| CI | macOS Desktop Gate success | success | PASS |
| DMG SHA256 | `65714a3eaab7d1a77a1dd5d1b8ce895daf3ba1a050970532afc5f9f805e2a45b` | matched | PASS |
| DMG size | `46204704` bytes | matched | PASS |
| Host architecture | arm64 | arm64; Python and Node arm64 | PASS |
| Gatekeeper | enabled | enabled | PASS |
| App / Core / Sidecar | arm64 | all verified arm64 | PASS |
| Code signature | `codesign --verify --deep --strict` | passed | PASS |

## Test Cases

### M5-01 — Isolated installation and first launch

```text
Preconditions: no existing LingJi app, process, DMG mount, or listener on 8765–8767.
Method: mounted the exact DMG, copied 灵机.app to /Applications, and started it with an isolated acceptance DataRoot.
Expected: clear first-use guidance and an understandable DataRoot workflow.
Actual: the owner reported that the initial DataRoot configuration prompt was not understandable and that the other UI was not understandable.
Evidence: owner observation during the physical M5 session.
Verdict: FAIL
```

### M5-02 — Packaged runtime and Local Control API

```text
Method: started the Desktop-managed Core using the isolated acceptance root; inspected process/port state and called the authenticated API.
Actual: one packaged Core listened only on 127.0.0.1:8766; /api/runtime/ping returned 200 with the isolated token; missing and invalid tokens returned 401. Runtime data, SQLite, Qdrant, vault, logs, and token stayed under the isolated root.
Actual health: /api/health returned degraded with configuration_required; Ollama was unavailable and ffprobe absent. The UI showed the same degraded/configuration-required state instead of a false success.
Verdict: FAIL for the required healthy runtime state; PASS for loopback, authentication, process ownership, and isolation.
```

### M5-03 — UI coverage

```text
Method: inspected Overview, Activity, Owner Attention, Advanced Diagnostics, and Brain Status in the installed Desktop.
Actual: navigation was responsive and backend-derived status was visible. The UI exposed the actual degraded state rather than a default-green success. Owner comprehension failed at the mandatory first-use check.
Verdict: FAIL
```

### M5-04 — Lifecycle

```text
Method: normal Desktop quit, process/port verification, then restart from /Applications and authenticated ping verification.
Actual: normal quit released 8766/8767 and left no LingJi process. Restart restored a single authenticated Core on 127.0.0.1:8766 and the Desktop returned to the running state.
Verdict: PASS
```

## Cleanup and Data Safety

```yaml
platform: macOS
architecture: arm64
physical_m5_checked: true
artifact_identity: PASS
preflight_environment: PASS
pre_cleanup: PASS
install: PASS
first_launch: FAIL
runtime: FAIL
control_api: PASS
ui: FAIL
restart_cycle: PASS
production_pollution_count: 0
post_cleanup: PASS
temp_root_absent: true
duplicate_app_count: 0
orphan_runtime_count: 0
final_verdict: FAIL
```

The mounted DMG was detached. The task-scoped temporary root and its generated bootstrap pointer were moved to the local Trash after confirming their exact ownership, so their original locations are absent and the operation remains recoverable. `/Applications/灵机.app` is retained as the current acceptance version. No pre-existing Production DataRoot, Vault, personal model, or user configuration was touched.

## Blocking Defects

```text
Defect ID: M5-UX-001
Severity: P1
Affected scope: first-use DataRoot configuration and general UI comprehension
Reproduction: install the exact DMG on a fresh Apple-Silicon Mac and open 灵机.app.
Expected: the first page should make the next step and the meaning of the DataRoot selection clear.
Actual: owner could not understand the first configuration prompt or the remaining UI.
Required fix: revise first-use copy, hierarchy, and guided next action; rebuild a new artifact and repeat this M5 acceptance.
```

```text
Defect ID: M5-RUNTIME-001
Severity: P1
Affected scope: required healthy runtime status on a fresh environment
Expected: required runtime state is healthy.
Actual: UI/API reported degraded/configuration_required because Ollama was unavailable and ffprobe was missing.
Required fix: clarify and validate the intended fresh-environment dependency contract, then rebuild and retest.
```

## Sign-off

```text
Codex executor: Codex
Owner observation: completed; FAIL
Acceptance date: 2026-08-11
Report branch: acceptance/macos-m5-physical-acceptance-c10d255
Report commit: 1b9a8cf3917183b2374e5743bf5cd48d75cb5739 (initial report commit)
```
