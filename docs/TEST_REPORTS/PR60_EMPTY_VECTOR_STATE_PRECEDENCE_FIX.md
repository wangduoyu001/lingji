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
| Complete Python suite | PENDING |
| Desktop smoke/build | PENDING |
| Rust/Tauri | PENDING |
| Unified release | PENDING |
| Fresh Artifact Day 0 | PENDING |

No real owner content, Production data, external AI-client configuration, permanent memory or Qdrant collection is modified by this repair.
