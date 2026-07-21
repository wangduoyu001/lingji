# P2-08B Local AI Reviewer

## Goal

Add an optional local-only AI risk reviewer to the deterministic Auto Review SHADOW path. The AI component is advisory and may only add risk. It cannot approve, reject, merge, mutate memory, or override a deterministic hard rule.

## Model roles

Models are resolved from the existing model inventory assignments:

- `auto_review_primary`
- `auto_review_fallback`

No model name is hardcoded in the reviewer. If neither role is configured, deterministic review remains available and the AI assessment reports `model_not_configured`.

## Local-only boundary

`LocalOllamaReviewer` accepts only loopback Ollama URLs:

- `127.0.0.1`
- `localhost`
- `::1`

Remote hosts are rejected before a request is made. No cloud API, token, or remote fallback is supported.

## Strict response contract

The local model must return JSON with exactly:

- `risk_points`: integer 0-40
- `flags`: array of short strings
- `summary`: one short sentence

Malformed JSON, additional/missing fields, invalid flags or an empty summary cause safe fallback. The deterministic result remains authoritative.

The prompt asks only for additional risk. It does not ask for hidden reasoning, approval, rejection, merge or execution. Stored data contains only the concise assessment fields, never private chain-of-thought.

## Risk ceiling

AI findings are appended after the deterministic decision. They can increase the score and risk level, but the deterministic action is unchanged. In particular, a hard owner-review result cannot be reduced to an automatic suggestion.

## Failure behavior

The reviewer tries the primary model, then the distinct fallback. If both fail, it returns an unavailable assessment with zero additional points and a concise local error. Review continues deterministically.

## Runtime settings

- `auto_review_mode`: defaults to `OFF`; only `OFF` and `SHADOW` are accepted.
- `auto_review_ai_enabled`: defaults to `False`.
- `auto_review_timeout_seconds`: local Ollama timeout.

`ACTIVE` raises an error. No MCP tool or API endpoint can enable or execute ACTIVE behavior.

## Data and authority impact

- Direct Obsidian write: no.
- Candidate/Core Memory mutation: no.
- Qdrant write: no.
- Second model registry: no.
- Remote provider: no.
- Automatic model download: no.
