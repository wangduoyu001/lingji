# PR60 Fresh Day 0 Empty-Store Truth Fix

## Scope

- Base product Head: `053769965cf767cfe5221ffa4334b189bedb4d7d`.
- Repair branch: `codex/pr60-vector-snapshot-truth-05376996`.
- Main repair commit: `97504fb33c71f4dfef26ef9e32d7a9fdabfa03e5`.
- Integrated local release-validation commit: `d82f23517eb537473f141955173aba82d26f1ddc`.
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
| Combined-tree unified release | PASS — 15/15 suites on `d82f23517eb537473f141955173aba82d26f1ddc` |
| Rust/Tauri | PASS inside unified release |
| Windows Sidecar + NSIS + package | PASS inside unified release |
| Summary and package exact commit | PASS — both `d82f23517eb537473f141955173aba82d26f1ddc` |

The fresh-gateway regression proves the generated dashboard and template still exist while memory documents, chunks, Core Memory, semantic points, and vectors remain zero. It also requires vector state `empty`, reason `collection_empty`, semantic search unavailable, and lexical search available.

Local release artifacts from the integrated validation tree were independently hashed:

```text
installer sha256: 57b91ff48e105bca79a3fc70b2ebb6f43a8f01d4f08bbd5868858bb9b7190e59
portable sha256: c01a9ac4052e17024343ab59bfb65da3bfc5880155dd3f0adcf079278dbf7fc9
sidecar sha256: 7c2e554874d5230a8dc85f665a2cb69ee4d30e54ff0fa0a2df50a96be4f7a823
manifest sha256: cae2a7154161cfb4ea26973780713124245d7610ec1b12a34575978bd7a949a2
build metadata sha256: 0eb0a27ed5c370a1e17099b5260b171a1551aad4b53f3d5e6e6e8d925538d8ce
```

These are local validation artifacts, not the new formal Artifact used for the next Day 0. The formal Artifact must be built from the merged product Head by the required GitHub workflow and downloaded fresh by its new ID.

## Remaining Gates

1. Open a product PR targeting `feature/unified-ai-memory-connectors`; keep PR #60 Draft.
2. Merge only after required remote checks, then build a new Artifact for the merged product Head.
3. Safely remove only the named acceptance root, reinstall the new Artifact, and repeat Day 0 from a clean DataRoot.

This report does not claim packaged experience PASS; that requires the new Artifact and real-machine rerun.
