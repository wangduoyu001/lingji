# PR #53 Windows Owner Acceptance Report

## Final result

```text
BLOCKED
MERGE ALLOWED: NO
```

Product commit: `ad4bc02ee2ea996492efe136c71fda901a8eebd3`  
Artifact ID: `8710133143`

The independently audited owner evidence supports artifact identity, installation, Runtime/DataRoot behavior, hardware inspection, read-only acceptance, application restart, same-version reinstall and uninstall data preservation.

The original LingJi PowerShell defect was not reproduced during completed phases:

```text
LingJi ancestor-chain Shell events: 0
Get-CimInstance Win32_Processor commands: 0
Get-PhysicalDisk commands: 0
CPU model source: windows_registry
```

Owner clarification on 2026-07-29: all visible UI controls responded to clicks. The unresolved UI issue is operation comprehensibility and missing workflow guidance, not dead controls.

```text
Control responsiveness: PASS
Operation comprehensibility / workflow guidance: FAIL (P1 usability defect)
```

The overall result remains BLOCKED because a real Windows reboot has not yet been completed, visible console-window behavior during the three restart cycles still requires explicit owner confirmation, and production mutation remains `UNKNOWN`.

## Evidence identity

```text
Original evidence ZIP:
PR53_WINDOWS_ACCEPTANCE_EVIDENCE_ad4bc02e_20260729-114932.zip
SHA256: 2FC937DECC5B382B4D64B361EC8CEAB563EC2C8E95C161A8045D54DDE6E153EA
Entries: 48

Public-safe derivative:
PR53_PUBLIC_EVIDENCE_SUMMARY_ad4bc02e.zip
SHA256: 8E88465B60244E0A3ED752AE8D3D4A6EAD7F3A9C1E6B07EC35A9F08033EBA263
Bytes: 9240
```

The raw ZIP should not be attached publicly unchanged because it contains local machine identity, absolute paths, full-desktop screenshots and copied acceptance-Vault files. No API key, GitHub token or LingJi control-token value was found in audited text files.

## Independent audit findings

- Build metadata and package hashes match product commit `ad4bc02e` and Artifact ID `8710133143`.
- Process log contains 706 valid JSON events covering the completed acceptance window.
- LingJi ancestor-chain Shell event count is 0.
- No recorded `Get-CimInstance Win32_Processor` or `Get-PhysicalDisk` command was found.
- CPU model source is `windows_registry`; physical-disk probing returned an empty list.
- Read-only acceptance records `passed_with_warnings`, `error_count=0`, `inputs_unchanged=true`.
- Uninstall marker SHA256 is identical before and after uninstall.
- The archive contains 21 screenshot filenames but only 8 unique PNG payloads.
- Earlier Core-restart and Windows-reboot screenshots are byte-identical and cannot serve as stage-specific evidence.
- Duplicate screenshots are consistent with the recorded Tauri WebView automation failure and do not by themselves establish deliberate fabrication.

## Owner diagnostic snapshot after three Core restarts

The owner supplied a fresh copied diagnostic snapshot after using the installed UI:

```text
product=灵机
version=0.1.0
commit=ad4bc02ee2ea996492efe136c71fda901a8eebd3
connection_state=connected
control_service=connected
control_api_port=8766
runtime_state=healthy
runtime_healthy=true
runtime_managed=true
runtime_pid=28884
runtime_restart_count=3
runtime_last_exit_code=none
runtime_binary_available=true
bootstrap_configured=true
bootstrap_source=bootstrap_file
workspace=acceptance
runtime_data_root=D:\codex\LingJiAcceptance\DataRoot-PR53-ad4bc02e-20260729-114932\acceptance
c_drive_write_detected=false
system_health=degraded
system_health_errors=0
system_health_warnings=2
memory_state=healthy
memory_documents=2
memory_revision=2
vector_state=degraded
vector_collection=lingji_memory_acceptance
vector_count=11
vector_dimension=1024
vector_rebuild_required=false
embedding_state=unavailable
embedding_configured_model=bge-m3
embedding_active_model=unknown
tasks_pending=0
tasks_running=0
tasks_failed=0
scheduler_jobs=0
storage_free_bytes=180958908416
```

This snapshot establishes:

- the exact installed product commit remained unchanged;
- the Runtime recovered to `connected`, `healthy` and `managed`;
- three managed Runtime restarts were recorded;
- the last exit code remained `none`;
- the isolated `acceptance` DataRoot remained active;
- no C-drive Runtime write was detected;
- there were no pending, running or failed tasks.

The restart lifecycle requirement is therefore upgraded from `BLOCKED` to `PASS` for restart count and managed recovery. The diagnostic snapshot alone cannot prove whether a visible PowerShell, CMD or console window appeared during those three cycles; that requires explicit owner observation.

## Degraded health interpretation

```text
Runtime lifecycle: HEALTHY
System errors: 0
System warnings: 2
Memory: HEALTHY
Vector store: DEGRADED
Embedding: UNAVAILABLE
```

The degraded aggregate state does not indicate a Runtime crash. The likely warning sources are the unavailable configured embedding model `bge-m3` and the vector capability being marked degraded while the active embedding model is unknown. Existing vector data is present (`count=11`, `dimension=1024`) and no vector rebuild is required.

This embedding/vector condition is a separate capability/configuration issue. It does not invalidate the Windows console-window regression fix, but it should be tracked before claiming full end-to-end production readiness for new semantic-memory ingestion.

## UI usability finding

The owner can click the controls, but cannot reliably understand:

- what each page is for;
- which action should be performed first;
- what result a button is expected to produce;
- whether an action succeeded;
- what should be done after a warning or empty state.

This is not a control-function failure. It is a product usability and documentation defect. Recommended classification: `P1` for the current owner-facing Desktop.

Required remediation should include:

1. page-level purpose text;
2. one clear primary action per page;
3. inline descriptions for technical fields;
4. visible success, failure and next-step feedback;
5. a first-run guided path from DataRoot configuration to healthy Runtime and daily use;
6. a short in-application user guide using the actual page names and buttons.

## Current acceptance matrix

| Check | Result |
|---|---|
| Artifact identity | PASS |
| Installation | PASS |
| First-run boundary | PARTIAL PASS |
| Runtime/DataRoot | PASS |
| Hardware PowerShell regression in audited phases | NOT REPRODUCED |
| Read-only acceptance | PASS |
| Application restart | PASS |
| Same-version reinstall | PASS |
| Uninstall data protection | PASS |
| Visible control responsiveness | PASS |
| UI operation comprehensibility | FAIL / P1 |
| Three managed Core restarts | PASS |
| Restart-cycle visible console observation | PENDING OWNER CONFIRMATION |
| Windows reboot | BLOCKED |
| Production mutation | UNKNOWN |
| Embedding capability | UNAVAILABLE / separate issue |

## Merge decision

```text
DO NOT MERGE
```

Minimum remaining acceptance:

1. explicitly record whether any PowerShell, CMD or black console window appeared during the three completed Core restarts;
2. perform a real Windows reboot and verify Runtime/DataRoot/workspace persistence;
3. after reboot, open system compute and perform one additional UI Core restart;
4. classify production mutation as `NONE` only when supported by evidence.

The complete UI control matrix is no longer blocked on click responsiveness. Its remaining finding is tracked as a usability defect requiring product guidance improvements.