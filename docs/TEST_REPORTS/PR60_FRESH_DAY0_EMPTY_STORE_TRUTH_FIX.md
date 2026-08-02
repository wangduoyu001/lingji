# PR60 Fresh Day 0 Empty-Store Truth Fix

## Scope

- Base product Head: `053769965cf767cfe5221ffa4334b189bedb4d7d`.
- Repair branch: `codex/pr60-vector-snapshot-truth-05376996`.
- Trigger: independent packaged Day 0 on freshly downloaded Artifact `8832376546`.
- Blocking defect: `LJ-05376996-P0-NONEMPTY-DAY0-STORE`.

No old Artifact, task directory, database, fixture, or report conclusion was used as execution evidence. The new isolated task root reported 2 documents, 11 chunks, 1 Core Memory item, and 11 healthy vectors before any source fixture or authorized content read.

## Root Cause

`MemoryLifecycleService` correctly creates owner-facing Obsidian files on first startup:

```text
00-System/Permanent-Memory.md
00-System/Templates/核心记忆模板.md
```

The shared `VaultLayout.should_index` rule did not distinguish these generated operation surfaces from owner knowledge. Fresh gateway bootstrap therefore indexed both Markdown files. The template frontmatter declared `memory_tier: core`, and the two files chunked into exactly the false 2 documents / 11 chunks / 11 vectors observed through the MCP-published snapshot and packaged UI.

## Repair

- Exclude the exact generated permanent-memory dashboard.
- Exclude all files under the existing generated `00-System/Templates` operation directory.
- Keep the files generated and visible in Obsidian.
- Preserve indexing for `00-System/Rules`, formal knowledge, and owner-approved Core Memory.
- Reuse the existing single-Vault indexer and MCP-owned Qdrant path; no parallel store or status path was added.

## Regression Evidence

| Command | Result |
|---|---|
| `python -m pytest -q tests/test_vault_layout.py tests/test_semantic_runtime_wiring.py tests/test_permanent_memory_gateway.py` | PASS — 18 passed |
| `python -m pytest -q --tb=short` | PASS — 623 passed, 10 skipped, 3 subtests passed |
| `python scripts/check_acceptance_sync.py` | PASS |
| `npm ci --no-audit --no-fund` | PASS |
| `npm run test:smoke` | PASS — 22 scripts |
| `npm run build` | PASS |
| Rust/Tauri and exact-tree release validation | PENDING |

The fresh-gateway regression proves the generated dashboard and template still exist while memory documents, chunks, Core Memory, semantic points, and vectors remain zero. It also requires vector state `empty`, reason `collection_empty`, semantic search unavailable, and lexical search available.

## Remaining Gates

1. Commit the exact repair tree and execute unified release validation, including Rust/Tauri and Windows packaging.
2. Open a product PR targeting `feature/unified-ai-memory-connectors`; keep PR #60 Draft.
3. Merge only after required remote checks, then build a new Artifact for the merged product Head.
4. Safely remove only the named acceptance root, reinstall the new Artifact, and repeat Day 0 from a clean DataRoot.

This report does not claim packaged experience PASS; that requires the new Artifact and real-machine rerun.
