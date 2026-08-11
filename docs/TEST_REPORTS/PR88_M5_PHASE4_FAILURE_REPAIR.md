# PR #88 M5 Phase 4 Failure Repair

## Current state

```text
Status: ROOT_CAUSE_REPAIR_PENDING
Product commit under repair: 171091fe764c6653cdc7325b4a1a71e0b7800822
Physical M5 verdict for rejected Artifact 9102748834: FAIL
Merge recommendation: DO NOT MERGE
```

## Failure-report handoff

The reconstructed source report is `docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_171091fe.md` on this same acceptance branch at commit `602d5326e8990796e8e9206f82d6fd9a37366adc`. GitHub branch, commit, and report-body reads succeeded before this repair report was started.

The repair scope is fixed by the three real defects:

| Defect | Required closure evidence |
|---|---|
| `M5-IDENTITY-002` | Final-DMG metadata, executable, Sidecar, and copied-App identity all equal the new exact product Head. |
| `M5-UX-003` | First-run UI regression proves the ordinary path prepares automatically and hides technical path selection. |
| `M5-ISOLATION-002` | Packaged-chain integration regression proves all acceptance state remains in the task root on first and second launch. |

No product code has been changed in this report branch. The rejected Artifact will not be retried.
