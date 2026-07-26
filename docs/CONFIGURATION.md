# CONFIGURATION.md — Configuration Authority

This document no longer copies environment defaults. Copied defaults became stale and previously contradicted the running code, including the embedding model, backup path, ports and compatibility runtime.

Current authorities:

```text
src/config.py::Settings
= code defaults and environment parsing

src/control/runtime_settings.py::RuntimeSettingsStore
= persisted owner runtime settings

src/control/settings_governance.py::OwnerSettingsRegistry
src/control/settings_catalog.py::CompleteOwnerSettingsRegistry
= owner-visible metadata, recommendations, risk and capability state

Desktop Settings page
= formal owner editing surface
```

Stable contracts:

- Local Control API: authenticated `127.0.0.1:8766`.
- MCP: stdio by default; optional HTTP on 8767.
- 8765: compatibility API only.
- Primary embedding model and other defaults must be read from `Settings`, not repeated here.
- Backup paths derive from explicit configuration or the selected storage root; no developer-specific absolute path is a valid default.
- Production and acceptance paths must remain physically isolated.
- Secrets belong in local environment files and must never be committed.

Example environment templates may document available keys, but they do not override `Settings` or the governed runtime settings contract.

For code entry points and focused validation, use `docs/MODULES/CODE_MAP.md`.
