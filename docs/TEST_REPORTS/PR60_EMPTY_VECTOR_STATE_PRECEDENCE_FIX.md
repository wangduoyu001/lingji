# PR60 Empty Vector State Precedence Fix

## Failure

Fresh Day 0 on product commit `6214ac4839f2a252f8714e7d14b6bf4ff6244e0a` and Artifact `8834478298` started the packaged Desktop in 14.488 seconds with the exact locked Acceptance DataRoot. Authenticated API and the packaged UI both reported 0 documents, 0 chunks, 0 Core Memory and 0 vectors, produced by the sole MCP process.

The vector state nevertheless reported `degraded / embedding_unavailable` instead of the ACTIVE task's required `empty / collection_empty`. Model refresh independently found the locally installed `bge-m3` model and reachable Ollama, but the MCP embedding provider had not made a real request and therefore correctly remained unverified. No real content was read and owner checkpoint A was not requested for the known-failing build.

## Root Cause

`MemoryStatisticsService._normalize_vector_truth` evaluated Embedding availability before checking whether the ready vector service had any Collection or vectors. The existing empty-store regression used an available fake Embedding provider, so it did not cover the packaged first-start state where an installed model remains unverified until its first real request.

This is a distinct status-precedence path from the earlier generated-scaffold indexing defect: counts are now correct, but the reason code is not.

## Repair

For a ready, unlocked, non-rebuild vector service, Collection/vector emptiness is normalized before Embedding availability. The higher-risk lock, rebuild-required and service-unavailable conditions retain priority. A non-empty index still requires a verified Embedding provider before semantic search can be advertised.

## Acceptance

| Gate | Result |
|---|---|
| Focused vector/runtime regression | PASS — 14 passed |
| Complete Python suite | PASS — unified release suite `python-full` |
| Desktop smoke/build | PASS — both suites passed |
| Rust/Tauri | PASS — 111.52 seconds |
| Unified release | PASS — 15/15 suites on `3807330e33be7577785bff920b9b7331a1be56a5` |
| Fresh Artifact Day 0 | PENDING |

The local release metadata is schema 5 and binds to the exact validated commit. The locally produced installer SHA-256 is `268d75062e172909a3d0961a7fe6c82b0d5e5e76f86bd32d66ce65e5d3fe161b`, portable executable SHA-256 is `4c1420018939444d0221303ce89fdad97eba6c3a41ba579c1f7dbbcfa0fc57aa`, sidecar executable SHA-256 is `a363eee05879cc71f4df0ce9ec9bd3f0cdf6048848d81bdcf656da69c122e39d`, and manifest SHA-256 is `cfda1a34c921dbd6d485c314f60be61d9d1d13b1d0846189dedbfab4680eb71d`.

No real owner content, Production data, external AI-client configuration, permanent memory or Qdrant collection is modified by this repair.
