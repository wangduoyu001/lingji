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

The result remains BLOCKED because the complete visible-control matrix, three UI-driven Core restart cycles and a real Windows reboot were not completed.

## Evidence identity

```text
Original evidence ZIP:
PR53_WINDOWS_ACCEPTANCE_EVIDENCE_ad4bc02e_20260729-114932.zip
SHA256: 2FC937DECC5B382B4D64B361EC8CEAB563EC2C8E95C161A8045D54DDE6E153EA
Entries: 48
```

A public-safe summary derivative was generated:

```text
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
- Core-restart screenshots are byte-identical and do not prove three restart cycles.
- Windows-reboot screenshots are byte-identical to a non-reboot UI capture and do not prove a reboot.
- Several overview, compute, diagnostics, read-only and app-restart screenshot names are also byte-identical.
- The UI matrix records that Runtime configuration was achieved by writing an equivalent bootstrap and restarting, so the visible DataRoot configuration path is only partially validated.

Duplicate screenshots do not establish deliberate fabrication. They are consistent with the recorded Tauri WebView automation failure, but they cannot be used as stage-specific evidence.

## Completed checks

| Check | Result |
|---|---|
| Artifact identity | PASS |
| Installation | PASS |
| First-run boundary | PARTIAL PASS |
| Runtime/DataRoot | PASS |
| Hardware PowerShell regression in completed phases | NOT REPRODUCED |
| Read-only acceptance | PASS |
| Application restart | PASS |
| Same-version reinstall | PASS |
| Uninstall data protection | PASS |
| Complete UI matrix | BLOCKED |
| Three UI Core restarts | BLOCKED |
| Windows reboot | BLOCKED |
| Production mutation | UNKNOWN |

## Merge decision

```text
DO NOT MERGE
```

Minimum remaining acceptance:

1. complete the visible-page and visible-control matrix;
2. perform three UI-driven Core restart cycles with PID and managed/authenticated recovery evidence;
3. perform a real Windows reboot, system-compute check and one additional Core restart;
4. classify production mutation as `NONE` only when supported by evidence.
