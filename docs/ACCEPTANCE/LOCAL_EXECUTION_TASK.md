# LingJi local execution task

> This file is the sole authority for the current local task. Older chat instructions, reports, artifacts, and temporary directories are historical evidence only.

```yaml
task_id: PR60-AUTONOMOUS-MEMORY-REPAIR-1860FA1
status: ACTIVE
execution_mode: DEVELOPMENT_REPAIR_AND_LOCAL_ACCEPTANCE
repository: wangduoyu001/lingji
product_pr: 60
product_branch: feature/unified-ai-memory-connectors
product_commit: 1860fa17c5de26b0ff4d54ace48158a6e343505a
working_branch: codex/pr60-autonomous-memory-repair
source_master_commit: adc175e1d7199e888caf49ba9a292ce8f85fd84d
baseline_failed_trial: PR60-MEMORY-QUALITY-TRIAL-4161807C
baseline_product_commit: 4161807ce4598cc1696093da4a703de101648280
report_path: docs/TEST_REPORTS/PR60_AUTONOMOUS_MEMORY_REPAIR_1860fa1.md
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
real_data_access: FORBIDDEN
production_data_mutation: FORBIDDEN
release_or_installer_execution: FORBIDDEN
deletion: FORBIDDEN
isolated_sidecar_build: ALLOWED_UNDER_D_CODEX_LINGJIREPAIRFIXTURE_ONLY
```

## Goal

Repair the existing assistant-hub experience without rebuilding the product or rerunning the historical release trial. LingJi must automatically perform only safe, metadata-only discovery for supported AI assistant exports and surface one understandable next action. It must never pretend that unsupported AI products or unpublished integrations have been taken over.

## Required product behavior

1. On entering the assistant hub, automatically refresh discovery and connection status without asking the owner for a path.
2. For a discovered supported import candidate, show one primary action: authorize and start import. After that authorization, queue processing directly; do not ask for a path or a second submit action.
3. When no automatic candidate exists but a supported manual export can be selected, show one file-selection action only. Selecting it must queue import directly; no path text field and no second submit action.
4. Show unsupported sources truthfully: Claude Code and WorkBuddy may be detected and can receive their supported connector guidance, but history import is not claimed unless an adapter actually exists.
5. Keep a visible manual/rollback route for connector configuration. Any connector configuration write requires an explicit owner action and exact confirmation. Never auto-write a third-party AI configuration.
6. Keep permanent-memory ownership intact: imports may create reviewable candidates only; Core Memory is never auto-approved.
7. Keep state evidence coherent: configuration presence, launchability, verified client registration, full-text search, semantic search, and vector-store health must be separate and must not show contradictory ready states.
8. Do not read real chats, exports, credentials, browser profiles, API keys, installed AI configuration bodies, or owner Vault material. Tests must use fixtures/mocks only.

## Permitted scope

```text
src/assistant_hub/**
src/control/capture_api.py
run_packaged_control_api.py
desktop/lingji-control/src/pages/AssistantHubPage.tsx
desktop/lingji-control/src/components/AssistantConnectorPanel.tsx
desktop/lingji-control/src/pages/AssistantImportFlow.css
direct tests and Desktop smoke scripts for these modules
docs/ACCEPTANCE/** and the task report
D:\codex\LingJiRepairFixture\sidecar-build\** (generated isolated test Sidecar only)
```

Use the existing one-action importer, evidence-based connector readiness, and launchable Codex command resolver. Make only a confirmed, minimal repair; do not create a second import system, memory store, or connector registry.

The packaged Sidecar must own an `ExtractionWorker` for its existing durable
queue. This task may add that lifecycle wiring and a direct regression test;
it must not add another queue or worker service.

The existing checked-in Sidecar may not be overwritten. If the current binary
does not expose the current Runtime ping contract, build a fresh Sidecar only
under `D:\codex\LingJiRepairFixture\sidecar-build`, point the debug Desktop to
that exact binary, and preserve its test evidence. Do not run an installer or
release bundle.

## Required verification

```powershell
python -m pytest -q tests/test_assistant_hub_imports.py tests/test_assistant_hub_api.py tests/test_ai_memory_connectors.py tests/test_ai_connector_readiness.py tests/test_executable_resolution.py tests/test_vector_truth_contract.py tests/test_memory_owner_lock.py
python scripts/check_acceptance_sync.py
Set-Location desktop\lingji-control
npm run test:smoke
npm run build
Set-Location ..\..
```

Start the real local Desktop application with isolated fixture-only data, use the UI to verify the automatic scan, one-action import presentation, connector status presentation, and visible manual/rollback entry. Do not select or authorize any real owner material. Preserve the UI open at the end if an owner observation is requested.

## Completion boundaries

- Do not rerun old release, artifact, reboot, real MCP, or real-data trial steps.
- Do not delete any directory or file, including the historical blocked cleanup root.
- Do not claim that every AI product is automatically importable or that LingJi can silently control another product.
- If the permitted behavior is already present and tests/UI demonstrate it, record that finding instead of rewriting it.
