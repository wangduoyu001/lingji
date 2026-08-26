# Phase 1 Task 4R-Reset — Repair Round 1

## Scope

This repair closes the independently reviewed Task 4 C1/C2/I1–I5 findings:
POSIX anchored no-follow descriptor traversal/publication, fail-closed platform
handling, same-size content race detection, structural report validation,
directory fsync error reporting, serialization normalization and finite reason
allowlisting. Runner lifecycle, CLI, Task 5/6, 4R2, release/100k and production
paths remain untouched.

## TDD evidence

- Authentic RED before product changes: focused file had **18 passed, 6 failed**.
  Failures reproduced missing anchored child descriptors, same-size race
  acceptance, malformed report gate calls, swallowed directory fsync failure,
  raw serialization exception and reason-path leakage.
- Expanded focused GREEN: `./.venv/bin/python -m pytest -q tests/evaluation/test_task4_reset_readiness.py`
  — **70 passed**; collection is **70 tests**.
- Frozen gate and Task 4 regression: **118 passed**.
- Current e2e visibility: **20 passed, 1 warning**.
- Historical Task4R1 visibility: **8 failed, 7 passed, 1 warning**; failures
  remain expected rejected-caller gaps for Task 6 and are not changed.

## Implemented contracts

- Sentinel roots are opened component-by-component with `O_DIRECTORY` and
  `O_NOFOLLOW`; descendants are enumerated/opened through held directory FDs,
  and regular files are hashed twice with held-handle metadata checks.
- Unsupported safe descriptor traversal/publication fails closed with stable
  `SAFE_TRAVERSAL_UNAVAILABLE` / `UNSAFE_PUBLICATION_PLATFORM` codes.
- Atomic publication uses an anchored parent FD for exclusive temp creation,
  target checks, replacement, cleanup and parent identity revalidation.
  Directory fsync unsupported errno values are narrowly skipped; other errors
  surface as `DIRECTORY_FSYNC_FAILED_AFTER_REPLACE` with post-replace truth.
- Evaluation reports are schema-validated before either gate call, including
  strict counters, finite bounded percentages, ratio/context consistency,
  optional owner/reboot values and blocked-reason tuple shape.
- Serialization catches ordinary exceptions with `SERIALIZATION_FAILED`, and
  public blocked reasons use a fixed allowlist with unknown values mapped to
  `UNTRUSTED_BLOCKED_REASON`.

## Integrity

- Corpus SHA-256: `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94`.
- Questions SHA-256: `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`.
- `git diff --check`: PASS.
- Acceptance sync and local handoff: PASS.
- No Production/Vault, Artifact, 100k, release or owner data touched.

## Commits

- Product/tests: `74477185dcf0f40957355c76659c75c4d8d5e923` — `fix: close readiness sentinel publication races`.
- Documentation: this report and acceptance log are committed after final
  visibility verification.
