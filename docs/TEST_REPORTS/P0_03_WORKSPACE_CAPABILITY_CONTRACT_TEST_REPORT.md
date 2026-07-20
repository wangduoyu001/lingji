# P0-03 Workspace and Memory Capability Contract Test Report

Updated: 2026-07-20  
Branch: `feature/second-brain-memory`  
Baseline: `39b754d940658fc6ae3bf7af29be2b1596335b2b`  
Status: repository implementation complete; full local regression validation pending

## 1. Task Goal

Establish one immutable and serializable workspace contract for `production` and `acceptance`, then add a directory-independent Memory Capability Contract adapter that executes the current formal `src` MemoryGateway in lexical-only mode.

This task does not implement an Embedding Provider, Qdrant Provider, Memory Inspector, database migration, schema change, or compatibility-runtime retirement.

## 2. State Before The Change

Before P0-03:

- `src/runtime/ports.py` defined the P0-02 port contract.
- runtime services still resolved Vault and SQLite paths independently from `Settings`.
- no unified `WorkspaceContext` or `WorkspaceResolver` existed.
- production and acceptance path isolation was not represented in the long-term `src` runtime.
- memory tests existed per implementation feature, but there was no reusable capability-level contract adapter.
- `build_memory_gateway()` remained lexical-only with `semantic_provider=None`.

## 3. WorkspaceContext Fields

`src/runtime/workspace.py` defines the only long-term workspace data object:

```text
name
vault_path
raw_path
storage_path
state_db_path
memory_db_path
qdrant_mode
qdrant_path
qdrant_url
qdrant_collection
log_path
cache_path
runtime_settings_path
queue_db_path
backup_path
derived_path
temp_path
reports_path
```

The object is a frozen dataclass, uses `pathlib.Path`, is serializable through `to_dict()`, exposes local mutable resources through `mutable_paths()`, and validates configuration through `validate()`.

Construction and resolution do not create directories, read databases, start services, import a Qdrant client, or use the compatibility runtime.

## 4. WorkspaceResolver Priority

Resolution order is explicit:

```text
explicit call override
>
LINGJI_* environment value
>
formal Settings field
>
safe workspace default
```

Workspace selection follows:

```text
explicit workspace argument
>
override name/workspace
>
LINGJI_WORKSPACE
>
Settings.workspace_name
```

Unknown names fail with `WorkspaceValidationError`; they never fall back to production.

Supported workspace-specific environment variables include:

```text
LINGJI_PRODUCTION_VAULT
LINGJI_PRODUCTION_STORAGE
LINGJI_PRODUCTION_RAW
LINGJI_PRODUCTION_STATE_DB
LINGJI_PRODUCTION_MEMORY_DB
LINGJI_PRODUCTION_QDRANT_MODE
LINGJI_PRODUCTION_QDRANT_PATH
LINGJI_PRODUCTION_QDRANT_URL
LINGJI_PRODUCTION_QDRANT_COLLECTION

LINGJI_ACCEPTANCE_VAULT
LINGJI_ACCEPTANCE_STORAGE
LINGJI_ACCEPTANCE_RAW
LINGJI_ACCEPTANCE_STATE_DB
LINGJI_ACCEPTANCE_MEMORY_DB
LINGJI_ACCEPTANCE_QDRANT_MODE
LINGJI_ACCEPTANCE_QDRANT_PATH
LINGJI_ACCEPTANCE_QDRANT_URL
LINGJI_ACCEPTANCE_QDRANT_COLLECTION
```

Logs, cache, runtime settings, queue DB, backups, derived files, temp and reports also support workspace-prefixed environment overrides.

## 5. Production Default Path Graph

With no per-resource override:

```text
<project>/<storage>/workspaces/production/
├── vault/
├── raw/
├── state/lingji_state.db
├── index/lingji_memory.db
├── qdrant/
├── logs/
├── cache/
├── runtime/runtime_settings.json
├── backups/
├── derived/
├── temp/
└── reports/
```

The current extraction queue uses the workspace `lingji_state.db`; therefore `queue_db_path` intentionally resolves to the same database within one workspace, while remaining physically different across workspaces.

## 6. Acceptance Default Path Graph

```text
<project>/<storage>/workspaces/acceptance/
├── vault/
├── raw/
├── state/lingji_state.db
├── index/lingji_memory.db
├── qdrant/
├── logs/
├── cache/
├── runtime/runtime_settings.json
├── backups/
├── derived/
├── temp/
└── reports/
```

Acceptance does not default to the existing production Vault and can be deleted or backed up as one workspace tree.

## 7. Isolation Rules

`WorkspaceResolver.validate_isolation()` rejects:

- equal paths across workspaces
- parent/child containment across workspaces
- case-only aliases
- normalized `..` aliases
- duplicate workspace names
- identical Qdrant collection names, including case-only differences
- acceptance paths that resolve into the production Vault or any other production mutable resource

Remote Qdrant URLs may match. Qdrant collection names may not match.

The resolver rejects explicit Windows `C:` paths before any write and rejects resolved paths on `C:`. It does not silently create a fallback path on another drive.

## 8. Lexical Memory Capability Contract

`tests/fixtures/memory_capability.py` is the implementation adapter. The contract test imports this adapter rather than depending on implementation directory labels.

Current capability declaration:

```text
lexical_enabled = true
semantic_enabled = false
compatibility_database_required = false
compatibility_api_required = false
qdrant_required = false
```

The lexical contract covers:

1. stable `memory_id` after repeated rebuilds
2. stable `chunk_id` after repeated rebuilds
3. full-text keyword retrieval
4. Chinese short-term fallback retrieval
5. citation presence
6. relative citation path and valid line range
7. project filtering
8. tag filtering
9. privacy filtering
10. Agent Scope filtering
11. archived and superseded exclusion by default
12. Core Memory through the unified Gateway
13. Context Pack character budget
14. Context Pack memory revision
15. production data not visible in acceptance
16. acceptance data not visible in production
17. lexical retrieval with no semantic provider
18. no compatibility database requirement
19. no compatibility API requirement
20. no Qdrant package requirement

Future semantic contracts are stored as an explicit list and are not represented as passing or skipped tests.

## 9. Modified Files

Functional code:

- `src/runtime/workspace.py`
- `src/runtime/__init__.py`
- `src/config.py`
- `src/gateway/bootstrap.py`

Tests:

- `tests/fixtures/__init__.py`
- `tests/fixtures/memory_capability.py`
- `tests/test_workspace_contract.py`
- `tests/test_memory_capability_contract.py`

Documentation:

- `docs/TEST_REPORTS/P0_03_WORKSPACE_CAPABILITY_CONTRACT_TEST_REPORT.md`
- `docs/PROJECT_STATUS.md`
- `docs/MODULES/CODE_MAP.md`
- `docs/CHANGELOG.md`

## 10. Test Commands

Requested focused commands:

```text
python -m pytest tests/test_workspace_contract.py -v
python -m pytest tests/test_memory_capability_contract.py -v
```

Requested related regression:

```text
python -m pytest \
  tests/test_memory_retrieval.py \
  tests/test_permanent_memory_gateway.py \
  tests/test_memory_lifecycle.py \
  tests/test_incremental_index_sync.py \
  -v
```

Requested full suite:

```text
python -m pytest tests/ -v
```

## 11. Test Results

Executed in the assistant isolated Python environment:

```text
python -m pytest tests/test_workspace_contract.py -q
8 passed, 1 warning
```

The warning is the existing Pydantic v2 deprecation warning for class-based `Settings.Config`; no assertion failed.

Also executed:

```text
python -m py_compile <all new and modified Python files>
```

Result: passed.

## 12. Tests Not Run Or Incomplete

The GitHub connector does not provide a checked-out worktree or shell, the assistant container cannot resolve `github.com`, and the repository has no workflow run available for this branch. Therefore the following were not executed against a complete repository checkout:

- `tests/test_memory_capability_contract.py`
- the four related memory regression files
- `python -m pytest tests/ -v`
- real Windows path and symlink behavior
- P0-02 simultaneous process binding

The tests remain present with full assertions. They were not deleted, weakened, converted to unconditional skips, or reported as passing.

## 13. Known Limitations

- Existing services are not yet forced to resolve every path through `WorkspaceContext`; this task adds the contract and one explicit Gateway wiring seam only.
- Existing callers of `build_memory_gateway()` retain the current Settings transition mapping until later migration tasks opt in explicitly.
- Runtime Settings UI/API exposure is deferred.
- Qdrant mode/path/URL/collection are configuration contracts only; no client is imported and no collection is created.
- The current `src` Gateway remains lexical-only.
- The inherited absolute `backup_dir` default in old Settings remains a separate known issue; the new workspace defaults do not use it.

## 14. Data Migration State

No data migration was performed.

No existing Vault, raw archive, SQLite database, Qdrant directory, log, cache, backup or runtime setting was moved, copied, rebuilt, deleted or modified.

No database schema or dependency changed.

## 15. Rollback

Revert these implementation commits:

```text
7242e6a7d105b8fe7ba35a7020ab735d7798a4b5
337203032c575f2f8a4654bcae530cc97711b25e
```

Rollback requires no data restoration because the task did not migrate or modify runtime data.

## 16. Next Task

P1-01 may begin only after the pending local validation gates are recorded:

1. run the lexical capability contract against a complete checkout
2. run the related memory regression
3. run the full suite when dependencies are available
4. complete P0-02 real-machine port validation

The next code task remains the unified Embedding Provider contract. Qdrant Semantic Provider work must not be folded into this P0-03 change.

## 17. Submission SHAs

```text
feat(runtime): add isolated workspace context
7242e6a7d105b8fe7ba35a7020ab735d7798a4b5

test(memory): add lexical capability contract
337203032c575f2f8a4654bcae530cc97711b25e
```

The documentation commit is the Git commit containing this report.
