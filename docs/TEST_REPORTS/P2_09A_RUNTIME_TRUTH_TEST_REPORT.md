# P2-09A Runtime Truth Test Report

## Environment

Development was performed through the GitHub connector against branch `work/p2-09a-runtime-truth`.

No local Windows, NVIDIA, Ollama or Qdrant runtime was attached to this conversation. Local test execution must not be inferred from this report.

## Tests added

`tests/test_runtime_truth.py` covers:

- distinct `bge-m3` primary and `nomic-embed-text` fallback defaults;
- preservation of a genuinely measured GPU utilization value of zero;
- unavailable telemetry remaining `null` rather than becoming zero;
- stale and warning propagation;
- unknown model inventory values remaining `null`.

## Existing safeguards reviewed

The existing `QdrantSemanticProvider` checks collection dimensions before upsert and search, sets `rebuild_required`, and raises `VectorDimensionMismatchError` on mismatch. The existing embedding provider keeps `active_model` unset until a successful request.

## Execution status

Status at document creation: `TESTS_ADDED_NOT_EXECUTED`.

After the PR is opened, GitHub Actions results must be attached to the PR. A passing generic CI run does not replace real-machine validation for NVIDIA telemetry, Ollama fallback behavior or a live Qdrant dimension mismatch.

## Required real-machine checks

1. Start the control API on Windows with an RTX 4060.
2. Confirm a real idle GPU reports measured `0`, not an inferred value.
3. Temporarily make `nvidia-smi` unavailable and confirm dynamic fields become `null`/`unavailable`.
4. Verify `bge-m3` primary success.
5. Verify fallback to `nomic-embed-text` when the primary model is absent.
6. Verify both models absent leaves semantic retrieval unavailable while lexical retrieval remains usable.
7. Verify a mismatched Qdrant collection is not written and reports rebuild required.
8. Verify `run_service.py` states that port 8766 is not started by that process.

## Database and data impact

- Database schema modified: no.
- Qdrant collection modified automatically: no.
- Model downloaded automatically: no.
- Obsidian or memory lifecycle modified: no.

## Final commit

Record the final PR head SHA after all CI-driven fixes are complete.
