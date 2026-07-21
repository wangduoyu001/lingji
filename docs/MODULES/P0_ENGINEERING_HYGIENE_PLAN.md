# P0 Engineering Hygiene Plan

> Updated: 2026-07-21
> Status: REQUIRED_BEFORE_P2_05
> Formal branch: `feature/second-brain-memory`

## 1. Purpose

P0 is a bounded engineering-hygiene gate inserted after the validated P2-04 merge and before P2-05 implementation.

It does not redesign the product and does not pause the roadmap indefinitely. It removes infrastructure defects that would otherwise be copied into every later stage.

## 2. Scope

P0 covers exactly four areas:

1. authority and architecture documentation alignment
2. machine-specific path removal
3. dependency and clean-install validation
4. startup-test and test-baseline repair
5. Obsidian CLI migration registration

The architecture and memory authority documents were aligned before this plan was created. Remaining code and validation work belongs to the P0 implementation branch.

## 3. Non-Goals

P0 must not implement:

- P2-05 Capture Control API
- Manual Capture Center UI
- system watchers
- clipboard or folder monitoring
- browser extension
- mobile sharing client
- full Obsidian CLI migration
- Schema v2
- Evidence Layer
- conflict review
- GraphRAG or reranker
- production Qdrant rebuild
- production model switch

## 4. Path Cleanup

### 4.1 Backup Path

Current defect:

```text
src/config.py
backup_dir = D:/codex/backups/pemis
```

Required contract:

- no machine-specific absolute default
- backup path derives from Workspace or Runtime Settings
- explicit environment override remains supported
- owner-selected external backup destination remains supported
- production and acceptance backup paths must remain isolated

Recommended default:

```text
<workspace storage>/backups
```

### 4.2 Obsidian CLI Path

Current compatibility implementation includes machine-specific installation paths.

Required P0 behavior:

- preserve environment-variable override
- detect executable through PATH
- use platform-standard application locations through a dedicated discovery function
- do not encode a specific drive letter or owner directory
- expose discovery result and source
- keep implementation in `second_brain/` only as compatibility during P0
- register final target under `src/obsidian/`

Full command migration is not part of P0.

## 5. Dependency Baseline

Required outputs:

- one documented dependency ownership model
- reproducible core install
- reproducible UI install
- optional media dependencies remain separate
- locked or constrained versions with an explicit update process
- clean virtual-environment installation validation

The implementation may use a constraints file, lock file or another repository-standard mechanism, but it must not create competing dependency systems.

Validation environments:

```text
core
ui
optional media dependency resolution check
```

Real PaddlePaddle, OCR, ASR, Ollama or Qdrant execution is not required for P0.

## 6. Startup Test Repair

Tests that compare complete startup files as literal text must be replaced with behavior or contract checks.

Required checks include:

- startup entry imports the expected runtime builder
- host and port come from Settings
- Local Control and compatibility services remain separated
- startup does not hardcode production paths
- optional providers degrade safely

Do not assert exact whitespace, comments or complete file contents.

## 7. Test Baseline Accounting

P0 must create a baseline report containing:

- clean-environment Python version
- dependency installation commands
- collected test count
- passed, failed, skipped and xfailed counts
- reasons for count changes compared with the previous report
- focused P0 gate
- full-repository result, reported separately
- environment-specific failures by exact test file

No result may be called all-green when failures remain.

## 8. Obsidian CLI Migration Registration

P0 must add a migration contract for the future target:

```text
src/obsidian/
  config.py
  discovery.py
  client.py
  models.py
  service.py
```

Expected future integrations:

```text
Local Control API :8766
Runtime Settings
Tauri status and settings
Workspace Vault path
```

P0 may add interfaces, Protocols or documentation-only target files if they do not duplicate the existing implementation. It must not migrate the full command surface.

## 9. Branch Order

Only the P0 branch starts now.

The existing P2-05 branches remain paused and contain no implementation commits:

```text
work/p2-05a-capture-control-api
work/p2-05b-manual-import-wiring
work/p2-05c-capture-center-ui
```

After P0 is tested and merged:

1. move or recreate all three P2-05 branches from the new formal HEAD
2. update their task instructions with the new base commit
3. start P2-05A, P2-05B and P2-05C in parallel

P0 must not be developed concurrently with P2-05 because it may change Settings, dependency files and test infrastructure shared by all three branches.

## 10. Required Documentation

P0 implementation must add:

```text
docs/MODULES/P0_ENGINEERING_HYGIENE_IMPLEMENTATION.md
docs/TEST_REPORTS/P0_ENGINEERING_HYGIENE_TEST_REPORT.md
docs/MODULES/OBSIDIAN_CLI_MIGRATION_PLAN.md
```

Shared status documents are updated only after the focused P0 gate passes and coordinated review is complete.

## 11. Completion Gate

P0 is complete only when:

- hardcoded production defaults are removed
- Obsidian CLI discovery has no machine-specific drive default
- dependency baseline is reproducible in a clean environment
- startup tests validate behavior rather than literal files
- test-count changes are explained
- focused tests pass
- documentation describes the final ownership and migration path

Completion status:

```text
P0_ENGINEERING_HYGIENE_FOCUSED_TESTED
READY_TO_REBASE_P2_05_BRANCHES
```
