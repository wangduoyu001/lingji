# PR #60 Autonomous Runtime Binding and UI Observability

Status: IMPLEMENTED, CI PENDING

## 1. Trigger

Day 0 for product commit `3e24e65ce12bfa22b5c9193d65500648ebf45729` and Artifact `8820695386` stopped with:

```text
FAIL_DATA_ROOT_ISOLATION
```

The installed Desktop initially showed the expected non-C-drive configuration boundary, but a later inspection found the running Runtime bound to a pre-existing acceptance root outside the task root. No real body was read, but isolation could not be proven.

The owner also clarified the intended product model:

```text
LingJi performs routine work proactively.
The UI is primarily an observability and intervention surface.
The owner should not manually drive every workflow step.
```

## 2. Root Cause

The previous implementation had three independent sources of truth:

1. the global Desktop bootstrap file;
2. mutable process environment variables and owner-directory fallbacks;
3. a Runtime health endpoint that returned only `{"status":"ok"}`.

A successful authenticated HTTP response therefore proved only that some Runtime answered on port 8766. It did not prove that the process used the Desktop-selected DataRoot and workspace.

The UI also exposed manual scanning and setup as primary workflow actions even though metadata discovery and status polling were already safe to run automatically.

## 3. Architecture

### 3.1 Startup binding contract

The Desktop now accepts an optional one-run startup contract through:

```text
LINGJI_BOOTSTRAP_CONTRACT_FILE
```

The JSON contract contains:

```json
{
  "schema_version": 1,
  "binding_id": "task-or-deployment-identity",
  "data_root": "D:\\absolute\\effective-root",
  "workspace": "acceptance"
}
```

A valid contract:

- must use an absolute non-C path;
- must use `production` or `acceptance`;
- is persisted as an exact effective DataRoot;
- is marked `binding_locked`;
- cannot be replaced from the UI while locked;
- is rejected if port 8766 is already occupied.

### 3.2 Automatic safe default

When there is no valid saved bootstrap and no startup contract, the installed Desktop automatically searches writable non-C drives from `D:` through `Z:` and selects:

```text
<drive>:\LingJiData\production
```

Manual directory selection remains available only when no safe writable default can be selected.

### 3.3 Runtime proof

The authenticated Runtime endpoint now returns:

```json
{
  "status": "ok",
  "binding_contract_version": 1,
  "data_root": "<actual resolved Runtime root>",
  "workspace": "<actual workspace>"
}
```

The Desktop compares the Runtime response against the persisted expected binding after start, restart and each connected-state poll.

A Runtime is accepted only when:

- it is managed by the current Desktop;
- its actual DataRoot equals the expected DataRoot after canonical normalization;
- its workspace equals the expected workspace;
- authenticated status is `ok`.

An unmanaged or mismatched Runtime is never shown as ready. A managed mismatched process is stopped before the Desktop reports the binding failure.

### 3.4 Single source of truth

The RuntimeManager no longer gets to silently legitimize a fallback directory. Credentials, Runtime start and API access are all gated by the same verified bootstrap binding.

## 4. Autonomy Contract

### L0: automatic observation

LingJi may automatically:

- inspect installed AI applications;
- inspect known history-directory metadata;
- refresh model and hardware status;
- poll task, vector and connector state;
- expose failures and retry state.

No real document or conversation body is read at this level.

### L1: automatic reversible work

LingJi may automatically:

- choose a writable non-C default when no owner configuration exists;
- start and recover its managed Runtime;
- retry failed status refreshes;
- queue already-authorized processing;
- deduplicate and maintain processing progress.

### L2: owner authorization boundary

LingJi must pause before:

- reading real conversation, script, Vault or export contents;
- modifying an external AI client configuration;
- enabling a new external integration;
- expanding an authorized content scope.

### L3: owner decision boundary

LingJi must require explicit confirmation before:

- approving or rejecting permanent-memory candidates;
- destructive cleanup outside an exact task-owned target;
- deletion, overwrite or irreversible migration;
- Production Qdrant rebuild or equivalent high-impact operation.

## 5. UI Contract

The UI is an observability surface first.

It now shows:

- current automatic action;
- completed and failed automatic actions;
- exact expected and actual DataRoot;
- workspace;
- binding source and binding id;
- whether the binding is verified;
- which operation is waiting for owner authorization.

Manual menus remain available for inspection, intervention and recovery. Routine scanning, status refresh and Runtime recovery are not presented as mandatory owner steps.

The previous ambiguous vector copy is prohibited:

```text
配置存在但尚未激活；全文检索仍可用，后续从向量中心处理
```

The UI must expose concrete model, Qdrant, index, error and repair-progress information instead.

## 6. Modified Files

```text
desktop/lingji-control/src-tauri/src/runtime_bootstrap.rs
desktop/lingji-control/src-tauri/src/main.rs
src/control/capture_api.py
desktop/lingji-control/src/runtimeTypes.ts
desktop/lingji-control/src/hooks/useLingJiConnection.ts
desktop/lingji-control/src/components/AutopilotStatusBar.tsx
desktop/lingji-control/src/components/AutopilotStatusBar.css
desktop/lingji-control/src/components/RuntimeBoundary.tsx
desktop/lingji-control/src/components/StartCenterPanel.tsx
desktop/lingji-control/src/pages/AssistantHubPage.tsx
tests/test_brain_status_e2e.py
desktop/lingji-control/scripts/observation-first-ui-smoke.mjs
desktop/lingji-control/scripts/assistant-hub-smoke.mjs
```

## 7. Validation

Required commands:

```powershell
python -m pytest -q tests/test_brain_status_e2e.py tests/test_assistant_hub_api.py tests/test_assistant_hub_discovery.py tests/test_packaged_mcp_runtime.py
python -m compileall -q src run_packaged_control_api.py

Set-Location desktop\lingji-control
npm ci --no-audit --no-fund
npm run test:smoke
npm run build
Set-Location src-tauri
cargo test
```

Required release validation:

```powershell
Set-Location <repository-root>
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/validate.ps1 -Mode release
```

Required new Day 0 proof:

1. create a task-specific startup contract;
2. start the installed Desktop without editing the global bootstrap manually;
3. verify the UI shows the exact task root and `startup_contract` source before real-content access;
4. verify `/api/runtime/ping` returns the same exact root and workspace;
5. place a different valid Runtime or bootstrap root on the machine and confirm the Desktop refuses to adopt it;
6. confirm automatic AI metadata scan, model refresh and hardware refresh run without owner clicks;
7. confirm no real body is read before authorization;
8. confirm the UI asks only at L2/L3 boundaries.

## 8. Safety

- No Production data was read or modified during implementation.
- No real conversation, script, Vault, Codex session or export body is accessed by automatic scanning.
- Port 8766 conflicts block rebinding.
- Locked task bindings cannot be changed from the UI.
- An external Runtime is not stopped unless it was managed by the current Desktop.
- An unmanaged external Runtime is refused rather than silently adopted.
- Old Artifacts remain invalid and must not be reused.

## 9. Rollback

Revert the commits that introduce startup contracts, authenticated Runtime identity, binding verification and UI autonomy. Do not restore the old behavior where HTTP 200 alone means the Runtime is trusted.

## 10. Completion Gate

This change is not complete until:

```text
focused tests PASS
Desktop smoke PASS
TypeScript/Vite build PASS
Rust/Tauri tests PASS
full release gate PASS
exact-head GitHub CI PASS
new Windows Artifact created
new Day 0 DataRoot isolation PASS
owner confirms the UI is observational rather than a manual workflow driver
```
