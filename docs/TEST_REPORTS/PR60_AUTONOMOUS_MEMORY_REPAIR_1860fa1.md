# PR60 autonomous memory repair

## Scope and boundary

This repair follows `PR60-AUTONOMOUS-MEMORY-REPAIR-1860FA1`. It does not rerun
the historical `PR60-MEMORY-QUALITY-TRIAL-4161807C` release trial, does not
read or import owner material, and does not delete any path.

The existing product branch already contained the intended one-action import
flow, automatic metadata-only discovery, unsupported-source boundary, and
evidence-based connector presentation. The confirmed repair is an isolation
defect: an explicitly supplied empty environment was incorrectly replaced with
the host environment by several assistant-hub components.

## Implemented repair

- An explicit `env={}` remains empty in assistant discovery, import planning,
  connector services, executable enumeration, and Windows command invocation.
- Only an omitted environment inherits the current process environment.
- Isolated discovery therefore cannot inherit owner `USERPROFILE`,
  `CODEX_HOME`, `LOCALAPPDATA`, or `PATH` values.
- A missing Codex command is now reported as `CLIENT_NOT_FOUND`, rather than
  an unrelated access-denied state produced by a host command alias.
- New regression tests cover host-profile export isolation and host
  `CODEX_HOME` isolation.

This keeps the existing user flow intact:

1. The Assistant Hub automatically scans supported export metadata on entry.
2. A discovered supported package has one action: authorize and queue import.
3. Without a discovered package, a supported source has one file-selection
   action; selection queues it immediately.
4. Claude Code and WorkBuddy remain honestly unsupported for history import.
5. Connector writes, rollback, real-content import, and Core Memory approval
   still require explicit owner action.

## Verification

| Check | Result |
| --- | --- |
| Focused Python suite | PASS — 39 tests |
| Acceptance sync | PASS |
| Desktop smoke suite | PASS — 22 scripts |
| TypeScript/Vite production build | PASS |
| Manual Tauri Desktop isolation launch | BLOCKED — Rust/Cargo has no configured default toolchain |

Focused Python command:

```powershell
python -m pytest -q tests/test_assistant_hub_imports.py tests/test_assistant_hub_discovery.py tests/test_assistant_hub_api.py tests/test_ai_memory_connectors.py tests/test_ai_connector_readiness.py tests/test_executable_resolution.py tests/test_vector_truth_contract.py tests/test_memory_owner_lock.py
```

Desktop launch was attempted only with an explicit isolated acceptance contract
under `D:\codex\LingJiRepairFixture`; no Core sidecar started, no discovery ran,
and no owner data was read. The development launcher stopped before opening a
test window because `cargo metadata` reported that Rustup has no default Cargo
toolchain. No toolchain was installed and no deletion was performed.

## Limitations

This repair does not and must not claim that LingJi silently takes over every
AI product. It automates safe discovery, supported governed imports, and
standard MCP connection guidance. Products without a real official adapter
remain visible as unsupported rather than being falsely marked connected.

The only remaining validation blocker is a configured Rust/Cargo toolchain for
the isolated Tauri Desktop run. Installing one requires a separate user choice
because it changes the local development environment.

## Continued isolated Desktop and data verification

The installed Rust/Cargo toolchain was made visible to the isolated development
process without changing it. A current-source Sidecar was built only under
`D:\codex\LingJiRepairFixture\sidecar-build\worker-r1`; no installer or
checked-in Sidecar was overwritten.

The first live run exposed two real conditions:

1. The older checked-in Sidecar lacked the current Runtime binding ping fields.
   Desktop correctly refused to treat that response as healthy.
2. The Sidecar accepted governed imports but did not start an extraction worker,
   leaving authorised imports queued.

The repair starts one `ExtractionWorker`, owned by the packaged Sidecar and
using the existing durable queue. It does not add a queue, database, or memory
authority.

Live fixture-only evidence:

- Desktop verified the locked `D:\codex\LingJiRepairFixture\acceptance`
  DataRoot and reported all three automatic low-risk actions complete.
- Metadata-only scan found the synthetic `chatgpt-export.json` without reading
  its content; unsupported Claude Code and WorkBuddy remained non-importable.
- One explicit fixture authorization queued `LJ-JOB-1DFD358EADB6`; the worker
  moved the intentionally malformed sample to automatic retry.
- A valid synthetic ChatGPT export was authorized once as
  `LJ-JOB-ABB1A43FD2F8` and completed automatically on its first attempt.
- The live Desktop then showed one completed import, one retrying import,
  one synthetic source, one structured conversation, and no real source.

Regression after the worker repair:

```text
57 focused Python tests: PASS
acceptance sync: PASS
Desktop smoke suite: PASS (22 scripts)
Desktop production build: PASS
```

The real Desktop remains open on the isolated fixture workspace. This is a
development/local acceptance result, not a release or owner approval for a
production installation.
