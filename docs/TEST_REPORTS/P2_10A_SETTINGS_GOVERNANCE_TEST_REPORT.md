# P2-10A Settings Governance Test Report

## Environment

Development was performed through the writable GitHub connector on branch `work/p2-10a-settings-governance-core`.

No local Python, Node, browser, Tauri or Windows runtime was attached to this conversation. Executable evidence comes from GitHub Actions.

## Python tests added

### `tests/test_settings_governance.py`

Covers:

- control package exports the complete governed Registry;
- validated Settings values override duplicated compatibility literals;
- Auto Review settings are owner-visible;
- ACTIVE is not an allowed Auto Review choice;
- an invalid ACTIVE environment default is clamped to OFF;
- every setting has recommendation, impact, risk and confirmation metadata;
- preview returns only effective changes;
- high-risk updates require explicit confirmation;
- confirmed high-risk updates create an audit event;
- invalid cross-setting combinations are rejected;
- unavailable capabilities include a visible reason;
- groups are backend-owned and ordered;
- formal 8766 startup uses the governed service and routes.

### `tests/test_settings_governance_api.py`

Covers:

- preview requires the existing 8766 token;
- preview returns a confirmation contract;
- high-risk commit without confirmation returns 403;
- confirmed commit records the `local_ui` actor.

## Desktop smoke added

`desktop/lingji-control/scripts/settings-governance-smoke.mjs` checks:

- Desktop does not contain a copied `GROUP_LABELS` map;
- groups and summary come from the backend snapshot;
- preview and commit endpoints are used;
- only dirty values are managed by the controller;
- high-risk confirmation is present;
- unload protection is present;
- unrelated drafts survive a setting reset;
- risk, availability and impact metadata are rendered.

The smoke is registered in the existing Desktop smoke suite. Existing modular and hardware smoke contracts were updated to verify backend-owned group metadata rather than requiring the Settings page to duplicate labels.

## GitHub Actions results

Validated head before this documentation-only result update:

`1654ed83df015e785178d15b1b6f999d06d1ad95`

Results:

- `tests` workflow #708: SUCCESS
- `P0 Windows Gate` #101: SUCCESS
- Python 3.11 unit tests: SUCCESS
- Python 3.12 unit tests: SUCCESS
- Windows unit tests and compile: SUCCESS
- clean-install validation: SUCCESS
- full Python entry-point compile: SUCCESS
- 14-script Desktop smoke suite: SUCCESS
- React/Vite production build: SUCCESS
- Tauri Rust check: SUCCESS
- MCP smoke: SUCCESS
- browser capture smoke: SUCCESS
- Obsidian plugin smoke: SUCCESS

## Manual checks recommended for the owner environment

1. Change a low-risk setting and verify preview then commit.
2. Change automatic cleanup and verify a visible high-risk confirmation appears.
3. Cancel high-risk confirmation and verify nothing is persisted.
4. Enable media AI with Provider set to off and verify commit is blocked.
5. Modify two settings, reset one, and verify the other unsaved draft remains.
6. Search across groups and verify group labels come from the backend.
7. Verify unavailable local Providers display their requirements/reason.
8. Change Auto Review OFF/SHADOW and verify ACTIVE is absent.
9. Verify Settings loading does not invoke a slow external Obsidian CLI probe.

## Data and authority impact

- Runtime settings JSON schema changed: no.
- New settings store introduced: no.
- Database schema changed: no.
- Production Vault/Qdrant/Ollama mutation: no.
- Master branch modified: no.
- High-risk settings can bypass confirmation through the formal Desktop flow: no.

## Status

`IMPLEMENTED_AND_CI_VALIDATED_AWAITING_MERGE`
