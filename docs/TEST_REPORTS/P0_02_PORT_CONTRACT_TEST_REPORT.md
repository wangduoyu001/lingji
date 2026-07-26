# P0-02 Port Contract Implementation and Test Report

Updated: 2026-07-20
Branch: `feature/second-brain-memory`
Status: repository implementation complete; real Windows multi-process validation pending

## 1. Goal

Remove the default `8765` conflict between the unified `src` MCP HTTP transport and the `second_brain` compatibility API without changing memory, vector, database or dependency behavior.

## 2. Port Contract

Before:

```text
second_brain compatibility API = 8765
src MCP Streamable HTTP        = 8765
Local Control API              = 8766
```

After:

```text
second_brain compatibility API = 8765
Local Control API              = 8766
src MCP Streamable HTTP        = 8767
src MCP default transport      = stdio
```

Tauri continues to use only the Local Control API on `8766`.

## 3. Implementation

Added:

- `src/runtime/ports.py`
- `src/runtime/__init__.py`
- `tests/test_mcp_server.py`

Modified:

- `src/config.py`
- `run_mcp_server.py`
- `src/control/api.py`
- `tests/test_control_api.py`

No changes were made to:

- memory schemas
- Qdrant data or configuration
- dependencies
- `second_brain` database behavior
- Tauri API base URL
- the formal startup chain

## 4. Behavior

The new runtime contract:

- validates MCP, Local Control and compatibility ports are distinct on overlapping bind hosts
- preserves environment/config overrides
- checks MCP HTTP port availability before CLI startup
- performs no TCP availability check for stdio mode
- exposes authenticated read-only `GET /api/mcp/status`
- adds the MCP contract to `GET /api/settings` under `runtime_contracts.mcp`
- returns `running: null` instead of pretending the MCP process state has been detected
- keeps compatibility API `8765` separate from Tauri

## 5. Tests Added

`tests/test_mcp_server.py` covers:

- default ports `8765/8766/8767`
- default stdio transport
- HTTP endpoint on `8767`
- environment port override
- runtime override resolution
- collision rejection
- occupied-port error
- truthful unknown running state
- Tauri default gateway remains `8766`

`tests/test_control_api.py` now covers:

- authenticated MCP status endpoint
- settings response contains the MCP runtime contract
- status does not fabricate running state

## 6. Tests Executed Here

A dependency-light isolated contract suite was executed in the assistant container:

```text
5 tests passed
```

Covered:

- default contract
- environment override
- collision validation
- occupied TCP port failure
- truthful status output

This was not the user's Windows runtime and was not a full repository checkout.

## 7. Tests Still Required Locally

Run on the real development machine:

```text
python -m pytest tests/test_mcp_server.py tests/test_control_api.py -v
python -m pytest tests/ -v
```

Then verify:

1. MCP stdio starts without opening an HTTP listener.
2. MCP Streamable HTTP binds `127.0.0.1:8767`.
3. Local Control binds `127.0.0.1:8766`.
4. Compatibility API binds `127.0.0.1:8765`.
5. All three can coexist.
6. Occupying `8767` causes a clear non-zero startup failure.
7. Tauri continues to use only `8766`.

No claim of full test completion is made until those checks pass.

## 8. Known Limitations

- The status endpoint reports configuration truth, not live MCP process discovery.
- Runtime Settings does not yet provide editable MCP fields; it exposes the read-only contract. Editable workspace/MCP settings remain part of the next runtime-contract work.
- Direct library callers of `src.mcp_server.run_mcp_server()` do not receive the CLI preflight port check; the supported startup entry `run_mcp_server.py` does.
- Real Windows socket, FastMCP and Tauri behavior has not been executed in this task.

## 9. Rollback

Rollback requires only reverting the P0-02 commits. No data migration or database rollback is required.

Restoring `src.config.Settings.mcp_port` to `8765` would reintroduce the original conflict and is not recommended except as a temporary code rollback.

## 10. Next Task

After local validation passes, proceed to:

```text
P0-03 WorkspaceContext and Memory Capability Contract
```

Do not start Qdrant integration before the workspace contract exists.
