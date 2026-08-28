# Task8E Mac Experience Candidate — blocked before Desktop packaging

## 1. Verdict

```text
Verdict: BLOCKED
Product code changes: none
Product commit: ffc2d8851dc91b5f09b14d31a34c1e6988358933
Candidate: lingji-macos-arm64-local-task8e / LOCAL-TASK8E-FFC2D885
Final release: NO — candidate only
Owner experience: NOT_TESTED (no Tauri app could be built)
Task7 quality gate: BLOCKED_AT_MEASUREMENT_CAP (unchanged)
```

The macOS arm64 sidecar was built and directly exercised in an isolated Acceptance root. The
Tauri app/DMG could not be produced because this machine has no `cargo`/`rustc` toolchain and
`npx tauri build` fails at `cargo metadata`. Installing a new Rust toolchain is outside this
bounded acceptance preparation and was not attempted. No product code was changed.

## 2. Identity and scope

| Item | Value |
|---|---|
| Repository | `wangduoyu001/lingji` |
| Product branch | `codex/phase1-automatic-memory` |
| Product commit | `ffc2d8851dc91b5f09b14d31a34c1e6988358933` |
| Acceptance branch | `acceptance/task8e-mac-experience-ffc2d885` |
| Task instruction/report prep commit | `2c2381f2ee502bbea51c95f2893e7b747baeea3f` |
| Acceptance root | `/tmp/LingJiAcceptance/TASK8E-ffc2d8851` |
| Data root | `/tmp/LingJiAcceptance/TASK8E-ffc2d8851/data/acceptance` |
| Report | `docs/TEST_REPORTS/MACOS_TASK8E_EXPERIENCE_CANDIDATE_ffc2d885.md` |

The acceptance branch was pushed and re-read from `origin` at `2c2381f2ee502bbea51c95f2893e7b747baeea3f`.

## 3. Cleanup and environment

- Start盤点：macOS 26.5.1, `arm64`, CommandLineTools present, Gatekeeper assessments enabled.
- No LingJi process or 8766/8767 listener existed at start.
- Only the task-scoped `/tmp/LingJiAcceptance/TASK8E-ffc2d8851` root was created.
- No Production DataRoot, Vault, owner configuration, or third-party AI data was read or written.
- Direct sidecar test was stopped by its exact PID; no 8766 listener remains.
- Because no App was built/installed, whole-bundle replacement and owner UI preservation did not
  occur. Existing `/Applications/灵机.app` was not touched.
- Current task root is retained as minimal blocked evidence; it must not be deleted before root
  confirms handoff/cleanup policy.

## 4. Automated checks

| Check | Result | Evidence |
|---|---|---|
| `npm run test:macos-release` | PASS | `macos-release-smoke: PASS` |
| `npm run build` | PASS | Vite production build, 92 modules |
| `npm run test:work-fact` | PASS | `work-fact-smoke: PASS` |
| `npm run test:memory-sources` | PASS | `automatic-memory-sources-smoke: PASS` |
| `npm run test:e2e:memory` | PASS | `e2e_owner_memory_flow: PASS` |
| `npm run build:sidecar:macos` default Python | FAIL | `No module named PyInstaller` |
| Sidecar dependency preparation | PASS | PyInstaller 6.21.0 in existing project `.venv` |
| `build:sidecar:macos` with arm64 `.venv` | PASS | PyInstaller arm64 target, onedir |
| Tauri app bundle | BLOCKED | `cargo metadata ... No such file or directory` |
| `check_acceptance_sync.py` | PASS | changed files product-impacting count 0 |
| `check_local_execution_handoff.py` | PASS (prep) | ACTIVE task schema valid before blocked result |
| `git diff --check` | PASS | no whitespace errors |

The Task7-blocked `release` gate, 100k benchmark, real artifact download, and quality trial were
not run by design.

## 5. Sidecar artifact and direct runtime evidence

The isolated sidecar artifact is retained at:

```text
/tmp/LingJiAcceptance/TASK8E-ffc2d8851/artifact/sidecar-resources/
```

| Artifact | Value |
|---|---|
| Binary | `lingji-core-aarch64-apple-darwin` |
| Binary SHA-256 | `8a7f41f6c019286e9a1b4dcd8baef168c03d05373cdbcd5ac70b98c0b6da75b4` |
| Binary size | `13404624` bytes |
| Runtime directory | 189 files, approximately 66 MiB |
| Mach-O | `arm64`, PIE executable |
| Manifest SHA-256 | `6660fbc64e6a46e8b8c7f4b3aada3a64f31ad1a43d71cc6a288930ff72847e1a` |

Direct Acceptance runtime command used the task-scoped data root and loopback host only. Fresh
evidence showed authenticated `/api/runtime/ping` HTTP 200, `/api/automatic-memory/runtime` 200,
`/api/work/current` 200, and `/api/work/pending-actions` 200. Runtime reported `running: true`,
`scheduler_state: running`, `worker_state: true`, queue counts all zero, and no cleanup error.
Token material was not copied into the report or public evidence; only `secret_export_count: 0`
is recorded.

## 6. Tauri packaging blocker

The exact command was:

```text
LINGJI_BUILD_COMMIT=ffc2d8851dc91b5f09b14d31a34c1e6988358933 \
LINGJI_BUILD_CHANNEL=task8e-mac-experience \
LINGJI_BUILD_TARGET=aarch64-apple-darwin \
LINGJI_BUILD_SIGNED=false \
npx tauri build --config src-tauri/tauri.sidecar.conf.json --bundles app --target aarch64-apple-darwin
```

Actual result:

```text
failed to run 'cargo metadata' command to get workspace directory:
failed to run command cargo metadata --no-deps --format-version 1:
No such file or directory (os error 2)
```

Read-only search found no executable `cargo` or `rustc` in standard locations; therefore no app,
DMG, bundle ID for a new candidate, strict app codesign result, or Desktop PID can be truthfully
reported.

## 7. Owner observation and next action

```text
Owner observation: NOT_TESTED
UI kept open: NO Tauri app exists
Owner's unique next action: after Rust/Cargo is provisioned on this machine, rerun this exact
Task8E candidate build from product commit ffc2d885..., then install/launch the resulting app for
the owner's real observation. Do not claim final release until that observation and Task7 gate
are separately resolved.
```

