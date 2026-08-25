# P2-08A Auto Review Deterministic Shadow Core

> 文档角色：历史实施/验证快照，不是当前进度或当前架构权威。
> 当前状态看 `docs/PROJECT_STATUS.md`；当前代码入口看 `docs/MODULES/CODE_MAP.md`。

## Goal

Add a pure deterministic review layer that can reduce future owner review volume without changing the existing authority chain. The implementation supports OFF and SHADOW. ACTIVE exists only as a contract enum and is rejected by the evaluator.

## Authority boundary

Existing candidate creation remains unchanged. `MemoryReviewService` and `MemoryLifecycleService` remain the only approval/rejection and lifecycle authorities. The Auto Review package never:

- supplies `owner_confirmed=True`;
- promotes or rejects a candidate;
- writes Obsidian files;
- changes SQLite candidate rows;
- writes Qdrant vectors;
- mutates MCP state;
- creates Core Memory.

## Contracts

Contract head for P2-08B:

`1a428d57451ec0d8adfc1c297a0c64b928593173`

The contract defines:

- `AutoReviewMode`: OFF, SHADOW, ACTIVE;
- allowed SHADOW actions;
- immutable candidate/context/finding/decision structures;
- evaluator, duplicate detector and audit sink protocols.

ACTIVE is not implemented and raises an error.

## Deterministic evaluator

`DeterministicAutoReviewEvaluator` is a pure function over `ReviewCandidate` and `ReviewContext`. It returns one of:

- `would_auto_approve`
- `would_append_evidence`
- `would_auto_reject_noise`
- `requires_owner_review`
- `blocked`

Every decision has an explanation list, risk score/level, reversible metadata and `mutation_performed=false`.

## Hard manual rules

The evaluator forces owner review for:

- Core Memory decisions;
- delete/forget/archive/remove operations;
- permission or privacy changes;
- restricted content;
- cross-project review/merge;
- knowledge conflicts;
- evidence-insufficient durable knowledge;
- failed or unverified development reports;
- owner-authored memory edits.

Invalid candidate schema is blocked.

## Duplicate and evidence handling

Normalized exact duplicate detection uses a hash of case/spacing/punctuation-normalized content. It does not create a second store. A duplicate may only produce `would_append_evidence` when it is same-project, same-type and explicitly evidence-only.

The link helper returns proposal metadata only; it never executes the append.

## Risk

Risk scoring is monotonic. Deterministic findings add points. External/AI reviewers can only add non-negative points. They cannot erase findings or lower a hard-rule result.

## Audit

`build_shadow_audit_payload()` adds optional SHA-256 chain metadata over the decision payload and previous hash. `ShadowAutoReviewService` appends a normal `auto_review_shadow_decision` event through the existing `StateDatabase.append_event()` interface. The hash does not create a second audit authority.

Only decisions and concise rule explanations are stored. Private reasoning or chain-of-thought is not stored.

## Changed files

- `src/auto_review/models.py`
- `src/auto_review/interfaces.py`
- `src/auto_review/security.py`
- `src/auto_review/risk.py`
- `src/auto_review/duplicate.py`
- `src/auto_review/evidence.py`
- `src/auto_review/project.py`
- `src/auto_review/link.py`
- `src/auto_review/evaluator.py`
- `src/auto_review/audit.py`
- `src/auto_review/service.py`
- `src/auto_review/__init__.py`
- `tests/test_auto_review_core.py`

## Out of scope

Local LLM review, 8766 API endpoints, Desktop dashboard, runtime settings and all automatic mutation are P2-08B/P2-09D work.

## Rollback

Revert the P2-08A branch commits. The package introduces no schema, file-layout or data migration.
