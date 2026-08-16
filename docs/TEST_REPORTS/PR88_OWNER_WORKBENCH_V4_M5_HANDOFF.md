# PR88 Owner Workbench V4 · M5 Handoff Report

- Date: 2026-08-16
- Repository: `wangduoyu001/lingji`
- Product PR: `#88`
- Product branch: `feature/owner-autopilot-ui-codexpp`
- Product commit: `bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9`
- Handoff task: `PR88-M5-OWNER-WORKBENCH-V4-BD1E7A17`
- Handoff verdict: **READY FOR PHYSICAL M5 / PRODUCT PR STILL DO NOT MERGE**

## 1. Scope

This report records only the handoff into physical M5 acceptance. It does **not** claim owner UX PASS and it does not modify product Runtime/UI code.

Owner Workbench V4 was implemented and tested on PR #102, then squash-merged into the PR #88 product branch. The merged product SHA was treated as a new candidate and all release gates were rerun from that exact SHA.

## 2. Exact product gate matrix

All required product gates completed successfully for the exact product SHA:

| Gate | Run | Result |
|---|---:|---|
| tests | `31928631115` | PASS |
| P0 Windows Gate | `31928631099` | PASS |
| macOS Desktop Gate | `31928631105` | PASS |
| Windows Desktop Release Baseline | `31928631101` | PASS |
| acceptance-doc-sync | `31928631103` | PASS |
| local-execution-handoff | `31928631118` | PASS |

No gate from the pre-squash development SHA is reused as product evidence.

## 3. macOS Artifact

```text
Artifact ID: 9258682849
Name: lingji-macos-arm64
Workflow: 31928631105
Product: bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9
GitHub ZIP digest:
  c26408c350bf35701bdf6aa97e75f65e7bead42fb6ed92d11838334274e1a888
Independent downloaded ZIP SHA256:
  c26408c350bf35701bdf6aa97e75f65e7bead42fb6ed92d11838334274e1a888
DMG:
  灵机_0.1.0_aarch64.dmg
Independent DMG SHA256:
  a5d54cba4f99411541527be7230d568f32a8fba90efed14ff9756df6b393bb46
```

The macOS workflow passed exact source identity, native Apple Silicon Python, static release smoke, frontend build, Apple Silicon Sidecar build, Rust tests, App Bundle build, embedded product identity, packaged Sidecar contract, authenticated packaged Control API, DMG creation, final DMG mount and installed-App Acceptance isolation.

## 4. Windows same-SHA release evidence

```text
Artifact ID: 9258675881
Name: lingji-windows-0.1.0-bd1e7a17
Workflow: 31928631101
GitHub ZIP digest:
  0696ae6615d8afc44f46efc264fd7852e7d971866efc1285f2397d87a36ce4b1
Independent downloaded ZIP SHA256:
  0696ae6615d8afc44f46efc264fd7852e7d971866efc1285f2397d87a36ce4b1
NSIS SHA256:
  b9341ae7982375cac1a771ad7082b8ba76014b60c4a1c300de5791ce77a84339
Portable SHA256:
  2435fcbfbc0e211c76c64ec5556c9f36fef84c12cd603c421ef0607c8da5f3b3
Manifest SHA256:
  4815fcb4403cfd29dc08a1d4fa099fc1d1ab0700b6aa0dbf2e3c347a6b508cdd
```

Independent extraction confirmed `SHA256SUMS.txt` matches all three release files. `build-metadata.json` reports:

```text
commit=bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9
version=0.1.0
channel=pr
target=x86_64-pc-windows-msvc
installer_format=nsis
signed=false
control_api=http://127.0.0.1:8766
python_sidecar_included=true
workspace_profiles=production,acceptance
c_drive_runtime_data_allowed=false
updater_included=false
```

Windows is evidence for same-SHA cross-platform release health; this handoff task installs only the macOS Artifact on M5.

## 5. Owner Workbench V4 physical acceptance targets

Physical M5 must specifically prove the four historical P1 failures are closed:

1. owner can understand actual work/result/next step;
2. owner actions are backed by concrete objects and never lead to an empty action page;
3. pagination reaches a real end and never guesses another page from page fullness;
4. Workbench, Need Me, permanent memory and automation point to the same real object chain.

V4 adds additional must-pass owner checks:

- daily navigation is `首页 / 记忆 / 工作 / 需要我 / 高级`;
- Memory is a first-class browse/search/evidence surface;
- memory candidate action carries exact `memory_id` into its review detail;
- global `Cmd/Ctrl+K` performs truthful capture/navigation and refuses unsupported actions instead of faking success;
- technical Runtime details stay under Advanced;
- Window Recovery passes menu, shortcut and Dock Reopen paths.

## 6. Technical M5 requirements retained

Physical acceptance must also retain all previous technical boundaries:

```text
exact artifact / exact commit
arm64
strict codesign
whole-bundle replace
Acceptance / Production physical isolation
sanitized AuthStatus only
secret_export_count = 0
production_pollution_count = 0
two launch/stop cycles
first stop saves Sidecar PID before stop
state gone + saved PID gone + 8766 free
no global Python/Node/Codex kill
remote report verification
safe cleanup / rollback
```

## 7. Rejected artifacts

Do not retry:

```text
9250384637 / Owner Work Feed v3
9249367672
9224368022
9102748834
```

Artifact `9258682849` is the sole current M5 package. If this physical M5 returns a final P0/P1 owner FAIL, it also becomes `DO NOT RETRY`.

## 8. Handoff result

```text
AUTOMATIC PRODUCT GATES: PASS 6/6
ARTIFACT INTEGRITY: PASS
SAME-SHA CROSS-PLATFORM EVIDENCE: PASS
PHYSICAL M5: PENDING
OWNER UX: PENDING
PR #88: DRAFT / DO NOT MERGE
```

The canonical execution authority is `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`. This handoff report is evidence only and cannot override that task file.
