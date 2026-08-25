# P2-08B Auto Review SHADOW API

> 文档角色：历史实施/验证快照，不是当前进度或当前架构权威。
> 当前状态看 `docs/PROJECT_STATUS.md`；当前代码入口看 `docs/MODULES/CODE_MAP.md`。

## Goal

Expose owner-visible Auto Review SHADOW decisions through the existing loopback 8766 Control API and its existing token authentication. This API records and explains suggestions; it does not execute memory changes.

## Registration

`run_control_api.py` registers `register_auto_review_routes()` on the same FastAPI application used by the Tauri desktop. No second port, process, token, database or authority is introduced.

## Endpoints

### Read

- `GET /api/auto-review/status`
- `GET /api/auto-review/decisions`
- `GET /api/auto-review/decisions/{decision_id}`
- `GET /api/auto-review/metrics`

### SHADOW evaluation and audit

- `POST /api/auto-review/evaluate/{subject_id}`
- `POST /api/auto-review/feedback`
- `POST /api/auto-review/audit/verify`

All routes require the existing `X-LingJi-Token` when a token is configured.

## Deliberately absent endpoints

There is no endpoint for:

- approve
- reject
- delete
- forget
- merge
- append evidence
- promote to Core Memory
- enable ACTIVE
- execute a decision

The absence is intentional rather than an unfinished UI button wearing a promising label.

## Evaluation flow

1. Validate subject/candidate identity.
2. Resolve OFF or SHADOW mode; reject ACTIVE.
3. Run the deterministic evaluator.
4. Optionally run local Ollama risk assessment.
5. Add non-negative AI risk without changing deterministic action.
6. Build optional audit hash-chain metadata.
7. Append `auto_review_shadow_decision` through the existing `StateDatabase` event stream.
8. Return `mutation_performed=false`.

## Decision queries

Decision lists are reconstructed from existing audit events. No second decision table is introduced. Metrics aggregate actions, risk levels, AI assessment availability and a fixed mutation count of zero.

## Feedback

Feedback records owner comparison outcomes such as agreement or disagreement as `auto_review_feedback` audit events. It does not replay or execute the decision.

## Audit verification

The verify endpoint recomputes the deterministic decision hash fields and reports whether the payload is intact. Extra display fields such as the concise AI assessment are not treated as a second audit authority.

## Errors

- Unknown decisions return 404.
- Invalid mode, identity mismatch or invalid payload returns 422.
- Invalid token returns 401.
- ACTIVE mode is forbidden and returns an error.

## Compatibility

The API is additive. Existing Memory Review endpoints and owner-confirmed lifecycle methods are unchanged.
