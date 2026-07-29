# PR #53 Windows Desktop Validation Report

## Scope

This report is the authority for the PR #53 product-code and automated-validation boundary. The detailed owner-machine result and evidence audit are maintained in:

`docs/TEST_REPORTS/PR53_WINDOWS_OWNER_ACCEPTANCE_ad4bc02e.md`

PR #53 remains Draft, open and unmerged.

## Product revision identity

```text
Product commit: ad4bc02ee2ea996492efe136c71fda901a8eebd3
Artifact: lingji-windows-0.1.0-ad4bc02e
Artifact ID: 8710133143
Artifact ZIP SHA256: 558db826c79260b589a392c9dcf25c10655154243323c8873b4b985b45726667
Installer SHA256: f51884dc37c1aac428a36aab03a111fcfe2b685111d7dab0baa65baec2bf9658
```

The report commit after `ad4bc02e` changes Markdown only and does not change the validated installer.

## LingJi PowerShell defect

The rejected earlier build showed LingJi launching:

```text
lingji-control-center.exe
-> lingji-core.exe
-> powershell.exe
-> conhost.exe
```

Command:

```text
Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name
```

The fixed product commit retains these remediations:

- CPU model detection reads Windows registry `ProcessorNameString` through Python `winreg`;
- physical-disk PowerShell/WMI probing is removed;
- permitted diagnostic executables use hidden/no-window Windows flags;
- Desktop and packaged Sidecar use the Windows GUI subsystem;
- Rust starts the packaged Core with `CREATE_NO_WINDOW`;
- regression tests reject the removed hardware PowerShell probes.

## Zero-Shell gate removal

By owner decision, the separate in-application zero-Shell gate was deleted. There is no zero-Shell button, process blacklist, two-phase observer, Tauri command, Rust module or zero-Shell merge requirement.

The actual product requirement is narrower: normal LingJi startup, hardware inspection and managed Runtime lifecycle must not open visible console windows or invoke unnecessary PowerShell probes.

## Runtime and storage boundary

```text
%LOCALAPPDATA%\LingJi\desktop-bootstrap.json
= small Desktop bootstrap pointer only

<owner-selected non-C base>\production
= production Runtime data

<owner-selected non-C base>\acceptance
= physically separate acceptance Runtime data
```

Runtime databases, vectors, raw data, logs, cache, token files, lifecycle state and backups must not silently fall back to C.

Installed Desktop startup requires bootstrap schema `2` with `owner_confirmed=true`. Inherited `LINGJI_OWNER_DATA_ROOT` and `LINGJI_WORKSPACE` values are quarantined and cannot satisfy first-run configuration.

## Automated validation

```text
tests #933: SUCCESS
P0 Windows Gate #183: SUCCESS
Windows Desktop Release Baseline #72: SUCCESS
```

Automated validation covered repository tests, Desktop smoke/build, Rust check/tests, packaged Runtime health/managed-stop, Windows GUI PE checks, NSIS packaging, metadata and checksums.

## Owner-machine result

```text
BLOCKED
MERGE ALLOWED: NO
```

Original evidence package:

```text
PR53_WINDOWS_ACCEPTANCE_EVIDENCE_ad4bc02e_20260729-114932.zip
SHA256: 2FC937DECC5B382B4D64B361EC8CEAB563EC2C8E95C161A8045D54DDE6E153EA
Entries: 48
```

The supplied ZIP was independently audited and its calculated SHA256 matches the owner-machine record.

Supported by the audited package:

- exact artifact identity and package metadata;
- installation;
- first-run `DATA ROOT REQUIRED` boundary and no pre-confirmation Core/8766 listener;
- managed Runtime and isolated acceptance DataRoot;
- CPU source `windows_registry` and no physical-disk PowerShell probe;
- 706 parsed process-start events with zero LingJi ancestor-chain Shell events;
- no recorded `Get-CimInstance Win32_Processor` or `Get-PhysicalDisk` command;
- read-only acceptance with `error_count=0` and unchanged inputs;
- application restart;
- same-version reinstall;
- uninstall marker preservation with matching SHA256.

Evidence limitations:

- the visible-page/control matrix was incomplete;
- the visible DataRoot configuration path was not fully exercised;
- three UI-driven Core restart cycles were not completed;
- a real Windows reboot was not performed;
- production mutation remains `UNKNOWN`;
- 21 screenshot filenames contain only 8 unique PNG payloads;
- Core-restart screenshots are byte-identical;
- Windows-reboot screenshots are byte-identical to a non-reboot UI capture;
- several overview, compute, diagnostics, read-only and app-restart screenshot names are also byte-identical.

The duplicate screenshots do not establish deliberate fabrication. They are consistent with the recorded Tauri WebView automation failure, but they cannot prove the named stages.

The raw ZIP contains local machine identity, absolute paths, full-desktop screenshots and copied acceptance-Vault files. It should not be attached publicly without redaction. No API key, GitHub token or LingJi control-token value was found in the audited text files.

A public-safe summary derivative was generated outside GitHub:

```text
PR53_PUBLIC_EVIDENCE_SUMMARY_ad4bc02e.zip
SHA256: 8E88465B60244E0A3ED752AE8D3D4A6EAD7F3A9C1E6B07EC35A9F08033EBA263
Bytes: 9240
```

The derivative is intentionally not committed as a binary repository file.

## Remaining acceptance

1. complete the visible-page and visible-control matrix;
2. perform three UI-driven Core restart cycles with PID and managed/authenticated recovery evidence;
3. perform a real Windows reboot, system-compute check and one additional Core restart;
4. classify production mutation as `NONE` only when supported by evidence.

## Status

```text
LINGJI_POWERSHELL_ROOT_CAUSE_FIXED
ZERO_SHELL_PRODUCT_GATE_REMOVED
PRODUCT_COMMIT_AD4BC02E_AUTOMATED_VALIDATION_PASSED
OWNER_EVIDENCE_PACKAGE_INDEPENDENTLY_AUDITED
OWNER_MACHINE_COMPLETED_PHASES_DID_NOT_REPRODUCE_POWERSHELL
OWNER_MACHINE_ACCEPTANCE_BLOCKED
PR_DRAFT_AND_UNMERGED
```
