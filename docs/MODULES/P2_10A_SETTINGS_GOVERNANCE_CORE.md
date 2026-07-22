# P2-10A Owner-visible Settings Governance Core

## Goal

Make the backend settings catalog the only owner-visible authority for defaults, recommendations, grouping, risk, impact and availability. The Desktop consumes that contract instead of copying default values or group labels.

## Root problems

- `RuntimeSettingsStore` contained literal defaults that could diverge from validated `Settings` values.
- Desktop copied group labels and performed direct PATCH writes without a server-side impact preview.
- High-risk settings had no explicit confirmation contract.
- Capability-dependent settings did not explain why a local Provider was unavailable.
- Resetting one setting could overwrite unrelated unsaved Desktop drafts.
- Auto Review settings added in P2-08 were not present in the owner-visible Registry.

## Backend architecture

### Base compatibility store

`src/control/runtime_settings.py::RuntimeSettingsStore` remains the persistence and validation compatibility layer.

### Governance layer

`src/control/settings_governance.py::OwnerSettingsRegistry` extends the compatibility store and adds:

- defaults derived from the validated Settings object when the field exists;
- complete recommendation and impact metadata;
- backend-owned group metadata;
- capability availability and disabled reasons;
- effective-change preview;
- cross-setting validation;
- high-risk confirmation enforcement;
- high-risk audit events.

### Current catalog

`src/control/settings_catalog.py::CompleteOwnerSettingsRegistry` adds settings introduced after P2-05, currently:

- `auto_review_mode`
- `auto_review_ai_enabled`
- `auto_review_timeout_seconds`

The Auto Review mode choices are only `OFF` and `SHADOW`. ACTIVE is not exposed.

### Formal service

`src/control/governed_service.py::GovernedLocalControlService` is used by the formal 8766 launcher. It:

- installs the complete owner Registry;
- rewires Obsidian and model inventory to the same Registry;
- applies supported runtime values to the current Settings object;
- exposes preview and confirmed commit methods;
- avoids running an external Obsidian CLI command merely to load the Settings page.

## API contract

Existing endpoints remain:

- `GET /api/settings`
- `PATCH /api/settings` for backward-compatible low-risk updates
- `POST /api/settings/reset`

New authenticated endpoints:

- `POST /api/settings/preview`
- `POST /api/settings/commit`

A preview returns:

- normalized effective changes only;
- old/new/default/recommended values;
- performance, storage, cost and privacy impact;
- risk level;
- restart/task behavior;
- availability state and reason;
- warnings and cross-setting errors;
- whether explicit confirmation is required.

High-risk changes require the exact backend confirmation phrase. The phrase is an interaction contract, not a secret or an authorization replacement. 8766 token authentication remains mandatory.

## Cross-setting validation

The Registry rejects invalid combinations such as:

- automatic transcription with ASR Provider set to `off`;
- automatic OCR with OCR Provider set to `off`;
- scene detection with Scene Provider set to `off`;
- cold storage enabled without a selected path.

## Desktop code structure

- `settingsTypes.ts`: backend-driven contract types.
- `settingsApi.ts`: settings API client.
- `useSettingsController.ts`: load, draft, preview, confirm, commit, reset and unload protection.
- `SettingsPage.tsx`: filtering and presentation only.
- `SettingField.tsx`: one field renderer using backend metadata.

Desktop no longer contains a `GROUP_LABELS` copy.

## Draft safety

- Only dirty values are sent for preview and commit.
- Page unload warns when unsaved changes exist.
- Manual reload requires confirmation when drafts exist.
- Restoring one setting or group preserves unrelated unsaved drafts.

## Risk policy

High-risk examples in the current Registry include:

- enabling automatic cleanup;
- changing the cold-storage path;
- changing the explicit Obsidian Vault path.

Restoring defaults remains available without high-risk confirmation because it moves the system back to the backend-defined baseline.

## Compatibility

- Existing runtime settings JSON schema remains unchanged.
- Existing low-risk PATCH clients continue to work.
- Existing service components still read the same runtime settings file.
- No new database or settings file is introduced.
- No production data migration is performed.

## Changed files

- `src/control/settings_governance.py`
- `src/control/settings_catalog.py`
- `src/control/governed_service.py`
- `src/control/settings_api.py`
- `src/control/__init__.py`
- `run_control_api.py`
- `desktop/lingji-control/src/pages/settingsTypes.ts`
- `desktop/lingji-control/src/pages/settingsApi.ts`
- `desktop/lingji-control/src/pages/useSettingsController.ts`
- `desktop/lingji-control/src/pages/SettingsPage.tsx`
- `desktop/lingji-control/src/components/settings/SettingField.tsx`

## Out of scope

This task does not perform the visual redesign of the full Desktop shell. It establishes the code and governance contract the later UI refinement must use.
