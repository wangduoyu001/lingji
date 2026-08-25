# P2-06 Obsidian CLI Formal Migration — Implementation Report

> 文档角色：历史实施/验证快照，不是当前进度或当前架构权威。
> 当前状态看 `docs/PROJECT_STATUS.md`；当前代码入口看 `docs/MODULES/CODE_MAP.md`。

> Status: `MERGED_AND_VALIDATED`
> Formal Branch: `feature/second-brain-memory`
> Source Branch: `work/p2-06-obsidian-cli-migration`
> Validated Implementation Commit: `4b0ad577eb396030ee6baa5c3bb217e990385475`
> Final Validated Head: `6dfa31148585e2cb78c83af52b752550962820c9`
> Formal Merge Commit: `5ce10ed8be98784f57e8723ffc27e40e3abaffbc`
> Date: 2026-07-21

## 1. Objective

P2-06 moves the Obsidian CLI implementation out of the deprecated `second_brain/` compatibility runtime and into the long-term `src/` product mainline.

The migration keeps:

- one CLI command implementation;
- one Workspace and Runtime Settings contract;
- one authenticated Local Control API entry on port 8766;
- one Desktop status and configuration surface.

It does not create a second Vault writer, database, queue, or schema.

## 2. Formal Package

```text
src/obsidian/
  __init__.py
  models.py
  discovery.py
  config.py
  client.py
  service.py
  management.py        # existing formal Vault management
  system_ui.py         # existing formal Obsidian UI generation
```

Responsibilities:

| Module | Responsibility |
|---|---|
| `models.py` | Stable states, errors and public data models |
| `discovery.py` | Runtime, environment, PATH and platform discovery |
| `config.py` | Workspace-aware CLI/Vault configuration |
| `client.py` | Typed arguments, subprocess execution, encoding, timeout and verification |
| `service.py` | Runtime Settings wiring, status, sanitization, validation and audit |
| `management.py` | Existing safe note metadata and relationship management |
| `system_ui.py` | Existing managed Obsidian system UI generation |

## 3. Compatibility Boundary

`second_brain/obsidian_cli.py` is now a deprecated facade.

It:

- re-exports the stable `src.obsidian` API;
- preserves old import names and monkeypatch surfaces used by tests;
- contains no `_run` implementation;
- contains no independent discovery or write logic.

This prevents the formal and compatibility implementations from silently diverging.

## 4. Configuration Contract

Runtime Settings adds:

```text
obsidian_cli_enabled
obsidian_cli_path
obsidian_vault_path
obsidian_vault_name
obsidian_cli_timeout_seconds
obsidian_cli_dry_run
```

CLI discovery priority:

```text
Runtime Settings explicit CLI path
-> OBSIDIAN_CLI_PATH
-> PATH: Obsidian.com / obsidian
-> platform-standard locations
-> not_found
```

Vault priority:

```text
Current Workspace Vault
-> Runtime Settings explicit Vault fallback
-> OBSIDIAN_VAULT_PATH
-> SECOND_BRAIN_OBSIDIAN_DIR compatibility fallback
-> configuration_required
```

The current Workspace Vault remains authoritative. Production and Acceptance isolation is not bypassed by a Runtime Settings value.

## 5. Client Safety

`ObsidianCliClient`:

- passes an argument list directly to `subprocess.run` and never uses a shell string;
- supports UTF-8 and UTF-8 BOM output;
- maps timeout, missing CLI and non-zero exit codes to stable errors;
- applies the Windows no-console flag only on Windows;
- rejects absolute paths, drive-qualified paths and `..` traversal;
- verifies create and append operations by reading the note back;
- supports Dry Run without launching a subprocess for write commands.

Migrated command surface:

```text
version / help
vault info / vault list
search / read
create / append
files / file count
tags / tasks
daily read / append / path
```

## 6. Local Control API

Authenticated 8766 routes:

```text
GET  /api/obsidian/status
POST /api/obsidian/validate
POST /api/obsidian/refresh
```

`/api/obsidian/validate` checks draft values without persisting them.

The status DTO returns:

- state and availability;
- CLI version;
- discovery sources;
- Vault name;
- timeout and Dry Run state;
- capabilities;
- stable issue codes;
- masked path displays.

It does not return raw `cli_path` or `vault_path` fields.

## 7. Desktop UI

The Tauri Desktop application now has an `Obsidian` page.

It shows:

- healthy, degraded, disabled, unavailable or configuration-required state;
- version and discovery sources;
- masked CLI and Vault paths;
- stable issues;
- compatibility-forwarding state.

It allows the owner to:

- enable or disable the CLI integration;
- select a CLI executable with the official Tauri dialog plugin;
- select a Vault directory;
- set Vault name, timeout and Dry Run;
- validate draft values before saving;
- save through the existing authenticated `/api/settings` endpoint.

The Desktop never starts the CLI directly and never reads SQLite.

## 8. Data and Scope Safety

```text
Production Vault test read/write: NO
Production SQLite read/write: NO
Production Qdrant access: NO
Production Ollama access: NO
Database Schema change: NO
New database: NO
New queue: NO
Automatic watcher: NO
Mobile client: NO
Browser extension: NO
force push: NO
rebase: NO
```

## 9. Follow-up Boundaries

P2-06 completes the formal CLI migration and status/configuration surface. Later work may add owner-confirmed higher-level Obsidian workflows, but must reuse `ObsidianService` and the existing safe Vault management layer rather than introducing another command runner.
