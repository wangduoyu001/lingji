# P2-05 Parallel Ownership

> Status: blocked by P0 Engineering Hygiene final gate  
> Start condition: P0 merged and all P2-05 branches moved to the same verified base commit.

## Engineer 1: Capture Control API

Owns:

- `src/control/capture.py`
- Capture endpoints in `src/control/api.py`
- Capture orchestration in `src/control/service.py`
- capture-mode settings in `src/control/runtime_settings.py`
- user-facing queue projection, pagination, cancel, retry, pause, resume

Must not modify:

- `src/capture/models.py`
- Adapter implementations
- Desktop files

## Engineer 2: Manual Import Wiring

Owns:

- `src/capture/manual.py`
- manual capture methods and classification
- `src/capture/models.py`
- `src/capture/service.py`
- minimal Adapter mapping changes

Must not modify:

- `src/control/`
- `src/extraction/queue.py`
- Desktop files

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

## Integration Engineer

Starts only after the three implementation branches have stable pushed commits.

Owns:

- integration branch
- conflict resolution
- shared contract corrections
- full targeted test set
- complete Desktop build gate
- `docs/PROJECT_STATUS.md`
- `docs/MODULES/CODE_MAP.md`
- `docs/CHANGELOG.md` after formal merge

The integration engineer must not add new product scope.

## Shared Hotspots

Only one branch may own each hotspot during P2-05:

- `src/control/api.py`: Engineer 1
- `src/control/service.py`: Engineer 1
- `src/control/runtime_settings.py`: Engineer 1
- `src/capture/models.py`: Engineer 2
- `src/capture/service.py`: Engineer 2
- `src/extraction/queue.py`: Engineer 1
- Desktop navigation and common API types: Engineer 3
- shared project status documents: Integration Engineer

## Parallel Limit

- active implementation writers: 3
- integration/validation engineer: 1 after branch stabilization
- maximum effective team for P2-05: 4

Running more writers during P2-05 is not recommended because it would split shared contracts without adding independent product scope.
