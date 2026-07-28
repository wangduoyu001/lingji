# Drama Memory V1 Implementation Report

## Scope

This report is the implementation authority for the first usable LingJi Drama Memory vertical slice:

```text
single and batch script import
normalization and raw preservation
source traceability
episode / scene / character parsing
Drama SQLite structured read model
independent Drama semantic collection
lexical + semantic hybrid retrieval
authenticated 8766 API
Desktop Drama workbench
```

Writer Agent, continuity checking and cross-script pattern mining remain explicitly deferred until retrieval quality passes owner-data acceptance.

## Architecture boundary

```text
src/plugins/drama_intelligence/
= isolated Drama domain implementation

src/control/drama_api.py
= authenticated 8766 routes

desktop/lingji-control/src/pages/DramaPage.tsx
= primary Desktop workbench
```

The plugin does not modify the generic Memory Engine schema and does not write Drama objects into personal long-term memory.

## Data authority

```text
<workspace storage>/drama/raw
= copied original source authority

<workspace storage>/drama/normalized
= normalized text and source maps

<workspace storage>/drama/knowledge
= structured export snapshots

<workspace storage>/drama/index/drama_read_model.db
= Drama structured authority and lexical index

lingji_drama_<workspace>
= rebuildable Qdrant semantic collection
```

Embedding vectors are not stored in Drama JSON objects. Production and acceptance resolve separate collection names.

## Import contract

Supported formats:

```text
txt
md
docx
pdf
srt
vtt
ass
```

Implemented behavior:

- source SHA256 provides idempotent duplicate detection;
- original files are copied into the active workspace;
- normalized UTF-8 text is preserved separately;
- source units retain file, DOCX block, PDF page or subtitle cue metadata;
- scanned or image-only PDF files produce an explicit OCR-required error;
- directory import processes supported files in deterministic order;
- one failed file does not cancel the remaining batch;
- batch results report imported, duplicate and failed files separately;
- a hard batch limit prevents an accidental unbounded directory crawl.

## Parsing and traceability

Deterministic V1 parsing produces:

```text
Drama
Episode
Scene
Character
DramaChunk
```

Every retrievable chunk includes:

```text
drama_id
chunk_type
episode_number
scene_number
characters
source_ref
start_offset
end_offset
```

Tests verify that slicing normalized source text with `start_offset:end_offset` returns the exact retrieved text.

V1 parsing is deliberately conservative. It does not claim that heuristic character and scene detection equals AI-reviewed Drama Profile accuracy.

## Retrieval contract

Lexical path:

```text
SQLite FTS5
-> Chinese substring fallback
```

Semantic path:

```text
LingJi EmbeddingProvider
-> independent lingji_drama_<workspace> collection
-> structured payload filters
```

Fusion:

```text
lexical candidates
+
semantic candidates
-> reciprocal-rank fusion
-> source-traceable results
```

Semantic failure degrades to lexical retrieval and is exposed in status instead of being reported as success.

Each result returns the source reference, episode, scene, characters, text and match reasons.

## Authenticated API

```text
GET  /api/drama/status
GET  /api/drama/library
GET  /api/drama/library/{drama_id}
POST /api/drama/import
POST /api/drama/import-directory
POST /api/drama/search
```

All routes use the existing authenticated loopback `127.0.0.1:8766` boundary.

## Desktop workbench

The primary Desktop navigation now includes `短剧编剧`.

Implemented controls:

- choose and import one script;
- choose and import a script directory;
- view structured and semantic status;
- browse imported Drama cards;
- filter search by Drama and chunk type;
- view source references, episodes, scenes, characters and match reasons;
- see explicit per-file batch failures.

The Writer Agent control is intentionally disabled and labeled as a later stage. V1 does not expose uncontrolled full-series generation.

## Automated acceptance

Python coverage includes:

- one source-traceable script import;
- exact normalized-source offset verification;
- one script longer than 50,000 characters;
- ten-script deterministic batch import;
- repeated batch import without duplicate rows;
- subtitle timing cleanup;
- scanned-PDF OCR-required classification;
- isolated Drama semantic payload and filters;
- authenticated single import, batch import and search routes.

Desktop smoke coverage includes:

- primary navigation and page route;
- single and batch import controls;
- supported format list;
- API route registration;
- independent collection contract;
- source-map and SQLite/FTS contracts;
- disabled Writer Agent boundary.

Focused development commands:

```powershell
python -m pytest -q --tb=short tests/test_drama_memory.py

Set-Location desktop\lingji-control
npm run test:drama
npm run build
```

Successful logs should not be loaded into AI context. On failure, inspect only the failing test and its bounded log tail.

## V1 acceptance target status

```text
50,000-character synthetic import: automated coverage implemented
10-script synthetic batch import: automated coverage implemented
idempotent duplicate prevention: automated coverage implemented
source offsets: automated exact-match coverage implemented
lexical fallback: automated coverage implemented
semantic collection/payload/filter contract: automated coverage implemented
real 10-script / 500k-word owner dataset: not yet run
retrieval accuracy >= 85% on 100 owner questions: not yet run
installed Desktop full-control acceptance: not yet run
```

## Deferred phases

### Phase 2

```text
Drama Profile
Character Profile
Episode Card
Scene Card
high-frequency narrative pattern extraction
pattern review and correction
```

### Phase 3

```text
project bible
character and secret state tracking
foreshadowing ledger
continuity checker
Writer Agent with retrieved references
```

## Status

```text
V1_CODE_IMPLEMENTED
AUTOMATED_CROSS_PLATFORM_VALIDATION_IN_PROGRESS
OWNER_DATA_RETRIEVAL_ACCEPTANCE_REQUIRED
WRITER_AGENT_DISABLED_BY_DESIGN
STACKED_DRAFT_PR_UNMERGED
```
