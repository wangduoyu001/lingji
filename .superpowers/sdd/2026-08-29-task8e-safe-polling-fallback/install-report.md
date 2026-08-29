# Task8E Safe Polling Fallback — macOS arm64 Build / Install Report

## Verdict

`READY_FOR_OWNER_EXPERIENCE`

This report covers the requested local macOS build and whole-bundle installation for the
review-approved Task8E head. The app remains open for owner observation. This is not a claim of
30-second event SLA, Phase 1 automatic-takeover acceptance, retrieval quality, or final release
acceptance.

## Identity and environment

| Item | Actual |
|---|---|
| Worktree | `/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/task8e-safe-polling-fallback` |
| Product HEAD | `02e85d35c82baff3d4570da8b6867b0fa210c95b` |
| Review | `task-repair-2-review.md`: APPROVED, Critical=0, Important=0 |
| OS | macOS 26.5.1 (25F80) |
| Host/Python | arm64 / arm64 |
| Bundle identifier | `com.lingji.controlcenter` |
| Build channel | `acceptance-macos` |
| Acceptance root | `/tmp/LingJiAcceptance/TASK8E-ffc2d8851/data/acceptance` |

The repository was clean at the requested HEAD before build. The acceptance task ledger in this
worktree still says `IDLE`; this physical run was performed under the explicit root-agent Task8E
installation authorization. No product source was edited.

## Automated verification

- `npm run test:macos-release`: PASS.
- `npm run test:smoke`: PASS (23 scripts).
- Backend Task8E/automatic-memory matrix: PASS, `80 passed, 1 warning`.
  One initial run had a transient existing runtime-flow race; the single test passed when rerun,
  and the complete matrix passed on the next run. The warning is Starlette/httpx deprecation.
- `npm run build`: PASS (Vite transformed 92 modules).
- Rust arm64 target build and Tauri app build: PASS.
- `npm run build:sidecar:macos`: PASS (PyInstaller on native arm64 Python, onedir).
- DMG creation: PASS; no DMG fallback was needed.

## Bundle checks

The generated and installed bundle passed `codesign --verify --deep --strict`. Both executables
are thin Mach-O arm64 binaries:

```text
/Applications/灵机.app/Contents/MacOS/lingji-control-center  Mach-O 64-bit executable arm64
/Applications/灵机.app/Contents/Resources/lingji-core.exe Mach-O 64-bit executable arm64
```

The installed main binary contains the exact 40-character product commit
`02e85d35c82baff3d4570da8b6867b0fa210c95b` and `acceptance-macos` build channel. The packaged
sidecar manifest is present and reports target `aarch64-apple-darwin`, PyInstaller `onedir`, and
131 runtime files.

Installed hashes:

```text
5ed6cb4051654d7a0ea016a3fd52f5a0df17b1372735925caf6365f0d055672a  /Applications/灵机.app/Contents/MacOS/lingji-control-center
5e85c79d0a1d32f1c75d697205987f55688b3f1a7f48c48ac3b33c99c1eb6daf  /Applications/灵机.app/Contents/Resources/lingji-core.exe
a44ae99fbd0fc5edbfe4838c650376f63016e53a1e6dcbf682e9a977ece0cf86  /Applications/灵机.app/Contents/Resources/lingji-core-manifest.json
098e3a280836a93f0e0012c99a6207acf4c99b129189197087b8a1a6886ebffa  灵机_0.1.0_aarch64.dmg
```

Installed sidecar contract check: `mode=packaged_sidecar`, `host=127.0.0.1`,
`owner_data_outside_install_dir=true`, `system_drive_runtime_data_allowed=false`,
`automatic_model_download=false`, `automatic_qdrant_rebuild=false`.

## Whole-bundle install and preservation

The old `/Applications/灵机.app` was not deleted or overlaid. After exact-PID graceful stop it was
moved as one bundle to:

```text
/tmp/LingJiAcceptance/TASK8E-be730084/backup-old/灵机.app
```

The old bundle was 117 MB and passed deep strict codesign before moving. The new app was mounted
from the generated DMG, checked, copied as a complete bundle to `/Applications/灵机.app`, and
checked again. The original Acceptance root was left in place; its SQLite databases, vault,
backups, Qdrant metadata, and runtime files remain present.

## Runtime and API

Old exact processes 4672 (Desktop) and 4682 (sidecar) received SIGTERM and exited gracefully;
8766 was released before installation. No unrelated process was stopped.

The installed app is intentionally still open:

```text
Desktop: 20263 /Applications/灵机.app/Contents/MacOS/lingji-control-center
Sidecar: 20274 child of 20263, --data-root /tmp/LingJiAcceptance/TASK8E-ffc2d8851/data/acceptance --host 127.0.0.1 --port 8766
8766: 127.0.0.1 listener owned by PID 20274
```

With the existing Acceptance token held only in the existing local protected file:

```text
authenticated /api/runtime/ping: HTTP 200
missing-token /api/runtime/ping: HTTP 401
automatic-memory sources: HTTP 200, 3 sources, all state=revoked
automatic-memory runtime: running=true, automation_mode=periodic_reconciliation,
  event_watcher_enabled=false, interval=900 seconds
automatic-memory summary: max_change_detection_delay_seconds=900,
  next_action=scheduled reconciliation at most 15 minutes
```

No token value, Authorization header, private database content, or personal data is included in
this report.

## Scope limits and owner handoff

No source authorization, owner UI clicks, Production/Vault writes, or data cleanup was performed.
The generated app remains open for owner observation. The fallback remains explicitly limited to
scheduled reconciliation; 30-second event SLA and Phase 1 automatic takeover remain blocked as
documented by the Task8E report.

