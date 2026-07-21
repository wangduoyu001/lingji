# P0 Engineering Hygiene Test Report

> Updated: 2026-07-21  
> Branch: `work/p0-engineering-hygiene`  
> Verified Code Commit: `08b507c2855e05a1d971cb2bcae5c8d2fea578eb`  
> Windows CI Run: `29800235688`  
> Status: `P0_ENGINEERING_HYGIENE_FOCUSED_TESTED`

## 1. Final Decision

```text
P0_ENGINEERING_HYGIENE_FOCUSED_TESTED
READY_TO_REBASE_P2_05_BRANCHES
```

P0 is complete. The Windows Python 3.12 clean-install gate, full Python repository suite, Desktop smoke tests, and Desktop build all passed.

## 2. Scope Delivered

### Portable paths

- Removed the machine-specific `D:/codex/backups/pemis` default.
- Unconfigured backups now resolve to `<storage_path>/backups`.
- Preserved explicit environment and owner configuration overrides.
- Preserved Production/Acceptance workspace isolation.

### Obsidian CLI compatibility discovery

Discovery order:

```text
OBSIDIAN_CLI_PATH
-> PATH: Obsidian.com
-> PATH: obsidian
-> platform locations
-> not_found
```

Windows candidates are derived from environment variables and include:

```text
%LOCALAPPDATA%\Programs\Obsidian\Obsidian.com
%LOCALAPPDATA%\Obsidian\Obsidian.com
%ProgramFiles%\Obsidian\Obsidian.com
%ProgramFiles(x86)%\Obsidian\Obsidian.com
```

Vault-name priority:

```text
OBSIDIAN_VAULT_NAME
-> selected Vault directory name
-> compatibility default: 本地知识库
```

No fixed developer drive or username directory remains in the implementation.

### Dependency ownership

```text
requirements.txt                  core runtime
requirements-ui.txt               Local Control API
requirements-media.txt            optional media providers
requirements-mcp.txt              optional MCP runtime
requirements-test.txt             test dependencies
constraints/python-3.13-linux.txt verified Linux CPython 3.13 constraints
constraints/python-3.12-windows.txt verified Windows CPython 3.12 constraints
```

Optional PaddleOCR, faster-whisper, and scenedetect dependencies remain outside the core runtime.

### Test infrastructure

- Replaced literal startup-source comparison with behavior-oriented AST and Settings contracts.
- Added a controlled test-only workspace path fixture for Windows system-drive temporary directories.
- Preserved the production `C:\` rejection contract and its dedicated test.
- Converted Qdrant provider tests to deterministic in-memory behavior where appropriate.
- Replaced fragile live-port Brain Status tests with deterministic FastAPI application-contract tests.
- Added a repeatable GitHub Actions Windows gate and retained pytest logs as workflow artifacts.

## 3. Verified Environment

```text
Runner: GitHub-hosted windows-latest
Operating System: Windows Server 2025
Python: CPython 3.12.10 x64
Node.js: 22
Workflow: .github/workflows/p0-windows-gate.yml
```

The workflow uses official GitHub setup actions and exact repository lock/constraint files.

## 4. Python Dependency and Clean-Install Gate

Commands represented by the CI workflow:

```text
python -m pip install --upgrade pip
python -m pip install \
  -r requirements-ui.txt \
  -r requirements-test.txt \
  -r requirements-mcp.txt \
  -c constraints/python-3.12-windows.txt
python -m pip check
python scripts/validate_clean_install.py --root . --import-check
```

Result:

```text
Dependency installation: PASS
pip check: PASS
Clean-install validator: PASS
Exit code: 0
```

The validator confirmed:

- required dependency files exist;
- core/optional dependency ownership is respected;
- constraints are exactly pinned;
- no editable or machine-local dependency is present;
- no private index URL, Token, or credential is present;
- frontend package and lock root metadata match;
- critical runtime imports succeed.

## 5. Full Compile Gate

Scope:

```text
main.py
run_service.py
run_control_api.py
run_mcp_server.py
run_extraction_worker.py
src/
second_brain/
tests/
scripts/
```

Result:

```text
compileall: PASS
Exit code: 0
```

## 6. Full Repository Pytest

Command:

```text
python -m pytest -q --tb=short
```

Result:

```text
passed: 359
failed: 0
skipped: 11
warnings: 2
duration: 63.24s
exit code: 0
```

Skipped tests are optional real-environment integrations, including Obsidian CLI/Vault integration and build-order-dependent frontend-dist inspection. They do not hide implementation failures.

Warnings:

1. Pydantic class-based `Config` deprecation.
2. Starlette TestClient/httpx transition warning.

Both warnings are pre-existing migration work and do not invalidate P0.

## 7. Desktop Gate

Commands:

```text
npm ci
npm run test:smoke
npm run build
```

Result:

```text
npm ci: PASS
Desktop smoke tests: PASS
TypeScript/Vite build: PASS
Exit code: 0
```

No React, Tauri, Vite, or TypeScript major upgrade was introduced by P0.

## 8. Failure Closure

### Historical baseline

```text
collected: 338
passed: 306
failed: 19
skipped: 13
```

Historical failures:

- Qdrant semantic provider: 7.
- Windows system-drive temporary paths: 12.

### P0 final result

```text
collected: 370
passed: 359
failed: 0
skipped: 11
```

Net collection change:

```text
370 - 338 = +32 tests
```

The increase comes from:

- expanded portable Obsidian CLI discovery and Vault-name tests;
- Obsidian behavior tests;
- backup/workspace contract tests;
- startup behavior contracts;
- deterministic Local Control API token contract;
- Windows workspace test-fixture coverage.

All 19 historical failures are now closed. Two historical skips became executable tests, while optional environment integrations remain explicitly skipped.

## 9. Security Verification

```text
Production ChatGPT content read: NO
Production Vault modified: NO
Production SQLite modified: NO
Production Qdrant accessed: NO
Qdrant server started: NO
Ollama started: NO
Production model switched: NO
Database schema modified: NO
P2-05 feature code modified: NO
Rebase: NO
Force push: NO
```

The test-only Windows workspace fixture is scoped to explicitly supplied temporary roots. Production `_reject_system_drive` and `_reject_system_drive_text` behavior remains active and verified.

## 10. Merge Recommendation

```text
READY_FOR_FORMAL_MERGE
```

After formal merge:

1. update `docs/CHANGELOG.md`;
2. close P0 Issue #9;
3. move all P2-05 branches to the same verified formal base;
4. start P2-05A, P2-05B, and P2-05C in parallel.
