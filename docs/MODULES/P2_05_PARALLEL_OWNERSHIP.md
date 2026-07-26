# P2-05 Parallel Ownership

> Updated: 2026-07-21  
> Status: `READY_FOR_PARALLEL_IMPLEMENTATION`  
> P0 Formal Merge Commit: `d2a605e463552cb982342bdb2376da8aad1b36b5`  
> Start condition: all three P2-05 branches must point to the same final formal base recorded in Issue #10.

## Engineer 1: Capture Control API

Owns:

- `src/control/capture.py`
- Capture endpoints in `src/control/api.py`
- Capture orchestration in `src/control/service.py`
- capture-mode settings in `src/control/runtime_settings.py`
- `src/extraction/queue.py` user operations
- user-facing queue projection, pagination, cancel, retry, pause, and resume

Must not modify:

- `src/capture/models.py`
- `src/capture/service.py`
- Adapter implementations
- Desktop files
- shared project-status documents

## Engineer 2: Manual Import Wiring

Owns:

- `src/capture/manual.py`
- manual capture methods and classification
- `src/capture/models.py`
- `src/capture/service.py`
- minimal Adapter mapping changes required by the manual-input contract

Must not modify:

- `src/control/`
- `src/extraction/queue.py`
- Desktop files
- shared project-status documents

## Engineer 3: Desktop Capture Center

Owns:

- `desktop/lingji-control/`
- Capture Center page and components
- Capture API client and DTO types
- Tauri Dialog Plugin integration
- frontend smoke tests

Must not modify:

- Python backend
- database schema
- shared project-status documents

## Integration Engineer

Starts only after the three implementation branches have stable pushed commits.

Owns:

- integration branch
- conflict resolution
- shared contract corrections
- full targeted Python test set
- complete Desktop build gate
- full Windows CI verification
- `docs/PROJECT_STATUS.md`
- `docs/MODULES/CODE_MAP.md`
- `docs/CHANGELOG.md` after formal merge

The integration engineer must not add new product scope.

## Shared Hotspots

Only one branch may own each hotspot during P2-05:

- `src/control/api.py`: Engineer 1
- `src/control/service.py`: Engineer 1
- `src/control/runtime_settings.py`: Engineer 1
- `src/extraction/queue.py`: Engineer 1
- `src/capture/models.py`: Engineer 2
- `src/capture/service.py`: Engineer 2
- Adapter mapping changes: Engineer 2
- Desktop navigation and common API types: Engineer 3
- shared project-status documents: Integration Engineer

Implementation branches must not merge one another.

## Parallel Limit

```text
Active implementation writers: 3
Integration/validation engineer: 1 after branch stabilization
Maximum effective P2-05 team: 4
```

Running more writers during P2-05 is not recommended because it would split shared contracts without adding independent product scope.

## Scope Exclusions

P2-05 does not include:

- system listener
- clipboard listener
- folder listener
- mobile share client
- browser extension
- platform-specific automatic capture client
- new PDF/DOCX parser
- new database
- second capture queue
