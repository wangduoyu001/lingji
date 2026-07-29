# PR #53 Windows Owner Acceptance Report

## Final result

```text
PASS
MERGE ALLOWED: YES
```

Product commit: `ad4bc02ee2ea996492efe136c71fda901a8eebd3`  
Artifact ID: `8710133143`

Owner acceptance was completed on 2026-07-29 against the exact installed product commit and artifact.

## Product-scope conclusion

The Windows Desktop lifecycle and console-window regression scope passes owner-machine acceptance:

- exact artifact identity verified;
- installation completed;
- Runtime remained connected, healthy and managed;
- non-C isolated `acceptance` DataRoot persisted;
- three pre-reboot Core restarts completed and recovered;
- Windows reboot recovery completed;
- one post-reboot Core restart completed and recovered;
- no visible PowerShell, CMD or black console window appeared during startup or restart operations;
- no LingJi ancestor-chain Shell event was found in the audited process log;
- the removed CPU and physical-disk PowerShell probes were not observed;
- application restart, same-version reinstall and uninstall data preservation passed;
- visible controls responded to clicks.

## Evidence identity

```text
Original evidence ZIP:
PR53_WINDOWS_ACCEPTANCE_EVIDENCE_ad4bc02e_20260729-114932.zip
SHA256: 2FC937DECC5B382B4D64B361EC8CEAB563EC2C8E95C161A8045D54DDE6E153EA

Public-safe derivative:
PR53_PUBLIC_EVIDENCE_SUMMARY_ad4bc02e.zip
SHA256: 8E88465B60244E0A3ED752AE8D3D4A6EAD7F3A9C1E6B07EC35A9F08033EBA263
```

The raw archive contains owner-machine identity, absolute paths and full-desktop captures and should not be attached publicly unchanged.

## Automated validation

```text
tests #933: SUCCESS
P0 Windows Gate #183: SUCCESS
Windows Desktop Release Baseline #72: SUCCESS
```

## PowerShell regression evidence

```text
LingJi ancestor-chain Shell events: 0
Get-CimInstance Win32_Processor commands: 0
Get-PhysicalDisk commands: 0
CPU model source: windows_registry
Owner visible PowerShell observation: NONE
Owner visible CMD observation: NONE
Owner visible black-console observation: NONE
```

The original LingJi process chain was not reproduced:

```text
lingji-control-center.exe
-> lingji-core.exe
-> powershell.exe
-> conhost.exe
```

## Three pre-reboot Core restarts

Owner diagnostic after three UI-driven Core restarts:

```text
commit=ad4bc02ee2ea996492efe136c71fda901a8eebd3
connection_state=connected
control_service=connected
runtime_state=healthy
runtime_healthy=true
runtime_managed=true
runtime_pid=28884
runtime_restart_count=3
runtime_last_exit_code=none
workspace=acceptance
runtime_data_root=D:\codex\LingJiAcceptance\DataRoot-PR53-ad4bc02e-20260729-114932\acceptance
c_drive_write_detected=false
tasks_pending=0
tasks_running=0
tasks_failed=0
```

Owner visual confirmation: no PowerShell, CMD or black console window appeared during the three restart cycles.

## Windows reboot and post-reboot restart

Owner diagnostic after a real Windows reboot and one additional UI Core restart:

```text
commit=ad4bc02ee2ea996492efe136c71fda901a8eebd3
connection_state=connected
control_service=connected
runtime_state=healthy
runtime_healthy=true
runtime_managed=true
runtime_pid=4432
runtime_restart_count=1
runtime_last_exit_code=none
bootstrap_configured=true
bootstrap_source=bootstrap_file
workspace=acceptance
runtime_data_root=D:\codex\LingJiAcceptance\DataRoot-PR53-ad4bc02e-20260729-114932\acceptance
c_drive_write_detected=false
tasks_pending=0
tasks_running=0
tasks_failed=0
```

This confirms bootstrap persistence, workspace/DataRoot persistence, automatic managed Runtime recovery and a successful post-reboot Core restart. Owner visual confirmation again records no PowerShell, CMD or black console window.

## Data safety

```text
Active workspace: acceptance
C-drive Runtime write detected: false
Production intentionally accessed: no
Production mutation: NONE observed
Uninstall owner-data preservation: PASS
```

## Non-blocking follow-up findings

### UI comprehensibility

```text
Control responsiveness: PASS
Operation comprehensibility / workflow guidance: P1 usability defect
```

The controls work, but the Desktop does not sufficiently explain page purpose, action order, expected results or next steps. This should be handled in a separate UI-guidance task and does not block this Windows lifecycle/console-window PR.

### Embedding/vector capability

```text
system_health=degraded
system_health_errors=0
system_health_warnings=2
memory_state=healthy
vector_state=degraded
vector_count=11
vector_dimension=1024
vector_rebuild_required=false
embedding_state=unavailable
embedding_configured_model=bge-m3
embedding_active_model=unknown
```

This is a separate capability/configuration issue. Runtime lifecycle is healthy, existing vectors remain present and no rebuild is required. It does not invalidate the PR #53 Windows fix, but it must be resolved before claiming complete new semantic-memory ingestion readiness.

## Final acceptance matrix

| Check | Result |
|---|---|
| Artifact identity | PASS |
| Automated CI | PASS |
| Installation | PASS |
| Runtime/DataRoot | PASS |
| Hardware PowerShell regression | PASS |
| Read-only acceptance | PASS |
| Application restart | PASS |
| Three pre-reboot Core restarts | PASS |
| Windows reboot recovery | PASS |
| Post-reboot Core restart | PASS |
| Visible PowerShell/CMD/black console | NONE / PASS |
| Same-version reinstall | PASS |
| Uninstall data protection | PASS |
| Visible control responsiveness | PASS |
| Production mutation | NONE observed |
| UI guidance | P1 follow-up |
| Embedding capability | Separate follow-up |

## Merge decision

```text
OWNER ACCEPTANCE: PASS
PR #53 MAY ENTER MERGE
```

No product-code changes were made after product commit `ad4bc02e`; later commits are acceptance-report Markdown only.