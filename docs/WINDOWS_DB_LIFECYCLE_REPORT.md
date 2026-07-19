# Windows DB Lifecycle Report

## Status

- Module: P0 Windows DB Lifecycle Fix
- Branch: `fix/windows-db-lifecycle`
- Draft PR: `#3`
- Verification workflow: `29690878755`
- Windows Python 3.12 job: passed before this documentation-only update
- Scope: SQLite fixture closure, scheduler shutdown, TestClient lifecycle, real regression test and demo

## Research Notes

### Official documentation

1. Python `sqlite3` connection context manager:
   - https://docs.python.org/3.12/library/sqlite3.html#how-to-use-the-connection-context-manager
   - It commits or rolls back a transaction but does **not** close the connection.
   - Python recommends `contextlib.closing()` when a closing context manager is required.
2. FastAPI lifespan testing:
   - https://fastapi.tiangolo.com/advanced/testing-events/
   - `TestClient` should be used with `with` when startup/shutdown lifespan must run.
3. Starlette lifespan and TestClient:
   - https://www.starlette.io/lifespan/
   - https://www.starlette.io/testclient/
   - The client context guarantees lifespan teardown before temporary files are removed.
4. Windows file deletion behavior:
   - https://github.com/python/cpython/issues/90161
   - Windows normally rejects deletion while another handle remains open.

### Similar implementation patterns

1. SQLAlchemy SQLite file connections and pool lifecycle:
   - https://docs.sqlalchemy.org/en/21/dialects/sqlite.html
   - The relevant design lesson is explicit connection ownership and disposal, not adding SQLAlchemy to LingJi.
2. SQLAlchemy connection-pool disposal:
   - https://docs.sqlalchemy.org/en/21/core/pooling.html
   - LingJi keeps its lightweight standard-library approach and does not introduce a pool dependency.
3. Starlette TestClient fixtures:
   - https://www.starlette.io/config/
   - Tests keep the application/client lifecycle inside a context before fixture directory cleanup.

### Adopted

- Explicitly close direct `sqlite3.connect()` test fixtures with `contextlib.closing()`.
- Keep the transaction context nested inside the closing context.
- Make scheduler shutdown interruptible and wait for both the polling thread and worker executor.
- Use `TestClient` through its context manager and register cleanup before deleting temporary directories.
- Test actual LingJi classes and actual file deletion on Windows.

### Rejected

- No database schema or WAL-mode changes.
- No retry loop that hides a leaked handle.
- No forced garbage collection as a lifecycle mechanism.
- No SQLAlchemy, filelock or other new dependency.
- No full scheduler or retrieval refactor.
- No fake test that loops over `pass` or prints a fixed success string.

## Root Cause

The Windows failures had two independent causes.

### 1. Direct SQLite test fixtures were not closed

`tests/test_acceptance_check.py` and `tests/test_backup_manager.py` used:

```python
with sqlite3.connect(path) as connection:
    ...
```

This controls commit/rollback only. It does not call `Connection.close()`. Linux allowed the temporary directory cleanup despite the remaining handle; Windows correctly raised `WinError 32` when deleting `lingji_memory.db`.

The fixtures now use:

```python
with closing(sqlite3.connect(path)) as connection:
    with connection:
        ...
```

### 2. Scheduler shutdown returned before workers stopped

`CronScheduler.stop()` previously called:

```python
executor.shutdown(wait=False)
```

and did not join the scheduler polling thread. A scheduled job could still be using `state.db` while the test removed its temporary directory.

The scheduler now:

1. Sets a stop event so the polling wait exits immediately.
2. Joins the polling thread.
3. Shuts down the executor with `wait=True`.
4. Verifies that no running jobs remain.

## Modified Files

- `src/scheduler/cron.py`
  - Interruptible stop event.
  - Named scheduler thread.
  - Thread join and blocking executor shutdown.
  - Active-job shutdown validation.
- `tests/test_acceptance_check.py`
  - Explicitly closes direct SQLite fixtures.
- `tests/test_backup_manager.py`
  - Explicitly closes direct SQLite fixtures.
- `tests/test_control_api.py`
  - Runs TestClient through the lifespan context and closes it before temp cleanup.
- `tests/test_control_api_extended.py`
  - Same lifecycle correction for extended API tests.
- `tests/test_memory_lifecycle.py`
  - Replaced the unconditional success test with real database, scheduler and TestClient deletion checks.
- `scripts/demo_windows_lifecycle.py`
  - Replaced fixed output with real LingJi database and scheduler operations.

## Tests Added

`tests/test_memory_lifecycle.py` verifies:

1. `MemoryDatabase` can be created, checked and deleted for 20 consecutive cycles.
2. `CronScheduler.stop()` waits for an in-flight job before `state.db` is deleted.
3. FastAPI `TestClient` context exits before its temporary SQLite state is deleted.
4. Main database, `-wal` and `-shm` files are actually removed.

A remaining Windows handle fails the test at `Path.unlink()` instead of being hidden by sleeps or retries.

## Test Commands

```powershell
python -m compileall -q main.py run_service.py run_control_api.py run_mcp_server.py run_extraction_worker.py src tests scripts
python -m unittest tests.test_memory_lifecycle -v
python -m unittest discover -s tests -v
python scripts/demo_windows_lifecycle.py

cd desktop/lingji-control
npm install --no-audit --no-fund
npm run build
```

## Verified CI Result

Workflow `29690878755` verified the code changes before this report update:

- Ubuntu Python 3.11: success
- Ubuntu Python 3.12: success
- Windows Python 3.12: success
- MCP smoke: success
- Browser capture smoke: success
- Obsidian plugin smoke: success
- Desktop UI build: success

The branch must remain unmerged until the latest post-documentation workflow is also green.

## Demo

```powershell
python scripts/demo_windows_lifecycle.py
```

The command performs real operations and exits non-zero on failure. Success output:

```text
Lifecycle test passed - 20 database cycles and scheduler shutdown are file-deletable
```

## UI

No new page was added. The existing Overview page already exposes startup health checks, including SQLite database health. This P0 change does not add a decorative duplicate status panel; it fixes the actual lifecycle and keeps the current UI observation path.

## Risks

- A process killed by the operating system cannot run graceful shutdown code.
- A future background service can reintroduce a lock if its `stop()` method does not join its thread or executor.
- Direct test or maintenance code can reintroduce the same bug by using `with sqlite3.connect(...)` without explicit closing.

## Known Limitations

- This change does not redesign SQLite access or add connection pooling.
- It does not change WAL or database schema.
- It validates graceful shutdown, not forced process termination.

## Rollback

Revert the commits in PR #3. No migration or data conversion is required. Both state and memory databases remain rebuildable derived stores.
