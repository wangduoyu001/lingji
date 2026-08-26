# Phase 1 Task 4R-Reset — Repair Round 2

## Repair Round 4 (2026-08-27)

Repair 4 binds each admitted root's no-follow `lstat` identity to the first
anchored root descriptor before enumeration, requires exact guarded readiness
values, validates each frozen-gate verdict immediately without invoking hostile
object behavior, and normalizes ordinary late directory-fsync and cleanup
exceptions. The finite snapshot-point contract remains unchanged.

- Authentic RED: **7 failed, 95 deselected** on the new R4 probes.
- GREEN focused: `tests/evaluation/test_task4_reset_readiness.py` — **102 passed**, **102 collected**.
- Frozen gate + Task 1–3 primitive regression — **118 passed**.
- Current e2e visibility — **20 passed, 1 warning**.
- Historical Task4R1 visibility — **4 failed, 2 passed, 1 warning** in
  `test_task4r1_round5_final_red.py`; **4 failed, 5 passed, 1 warning** in
  `test_task4r1_takeover_red.py`. These remain rejected-caller compatibility
  blockers deferred to Task 6 and were not modified.
- Fixture SHA-256 remains corpus
  `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94` and
  questions `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`.
- POSIX dir-FD/no-follow is the supported anchored guarantee; unsupported
  platforms fail closed. No Production/Vault, Artifact, 100k, release, UI,
  Task 5/6 or Task4R2 work was performed.

## Repair Round 3 (2026-08-27)

Repair 3 is limited to `quality_evidence.py`, its focused adversarial tests and
this existing Task 4 report. Anchored directory helpers now poison ownership
before propagating a close failure, root identity observations have stable
path-redacted errors, report validation requires exact built-in values and
fails closed around validation exceptions, and all writer stream/replace
exceptions are stable publication errors. The sentinel contract explicitly
defines the snapshot point as the successful final no-follow root identity
observation and comparison inputs; later mutations are deferred to the next
capture/diff.

- Authentic RED: **6 failed, 77 deselected** on the six new R3 boundary probes.
- GREEN focused: `tests/evaluation/test_task4_reset_readiness.py` — **95 passed**, **95 collected**.
- Frozen gate + Task 1–3 primitive regression — **118 passed**.
- Current e2e visibility — **20 passed, 1 warning**.
- Historical Task4R1 visibility — **4 failed, 2 passed, 1 warning** in
  `test_task4r1_round5_final_red.py`; **4 failed, 5 passed, 1 warning** in
  `test_task4r1_takeover_red.py`. These remain rejected-caller compatibility
  blockers deferred to Task 6 and were not modified.
- Fixture SHA-256 remains corpus
  `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94` and
  questions `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`.
- POSIX dir-FD/no-follow is the supported anchored guarantee; unsupported
  platforms fail closed. No Production/Vault, Artifact, 100k, release, UI,
  Task 5/6 or Task4R2 work was performed.

## Scope

Repair Round 2 closes the remaining Task 4 C1/I1/I2/I3 and descriptor-ownership
gaps: child-directory identity checks before recursion, final root path identity
revalidation, version-stable double hashing, hostile reason handling and safe FD
ownership/closure. No runner, CLI, Task 5/6, 4R2, release/100k, Production/Vault,
frozen evaluator/fixtures or retrieval behavior changed.

## TDD and verification

- Authentic RED before the repair changes: focused **18 passed, 6 failed**,
  reproducing the prior C1/C2/I1–I5 failures.
- Expanded GREEN: `tests/evaluation/test_task4_reset_readiness.py` — **77 passed**,
  **77 collected**.
- Frozen gate + Task 1–3 primitive regression — **118 passed**.
- Current e2e visibility — **20 passed, 1 warning**.
- Historical Task4R1 visibility — **8 failed, 7 passed, 1 warning**; unchanged
  rejected-caller compatibility gaps deferred to Task 6.

## Repair evidence

- Child directories are opened and immediately fstat-checked against the
  no-follow parent enumeration before any descendant scan/read. Root identity is
  reopened component-by-component at completion and compared with the admitted
  descriptor.
- Regular files include mtime/ctime in version checks and require equal digests
  across two complete reads. Descriptor ownership transfer and close failures
  use stable typed errors.
- Hostile reason elements/iterators never invoke arbitrary `__str__`; unknown
  values collapse to `UNTRUSTED_BLOCKED_REASON`.

## Integrity and platform limits

- Corpus SHA-256: `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94`.
- Questions SHA-256: `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`.
- `git diff --check`, acceptance sync and local handoff: PASS.
- POSIX dir-FD/no-follow support is required; unsupported platforms fail closed
  with stable unavailable/unsafe-publication codes. Windows reparse-handle
  support remains deferred.
- No owner Production/Vault, Artifact, 100k, release, Task 5/6 or 4R2 work.

## Commits

- Product/tests: `ab5a73f4fdc79f20c78803d0069a15e5a78aa4b9` — `fix: close remaining readiness snapshot races`.
- Documentation commit follows final verification.
