# Drama Memory V1 Implementation Report

## Scope

This report tracks the first usable vertical slice of the LingJi Drama Memory plugin:

```text
script import
normalization
source traceability
episode / scene / character parsing
Drama SQLite read model
independent Drama semantic collection
hybrid retrieval
8766 API
Desktop Drama workbench
```

Writer Agent and continuity checking are explicitly deferred until retrieval quality and source traceability pass acceptance.

## Architecture boundary

```text
src/plugins/drama_intelligence/
= domain implementation

src/control/drama_api.py
= authenticated 8766 routes

desktop/lingji-control/src/pages/DramaPage.tsx
= primary UI
```

The plugin must not modify the generic Memory Engine schema or write drama objects into general personal memory.

Permanent and derived data:

```text
Drama raw / normalized source files
= source authority

Drama SQLite
= structured authority and lexical index

Drama Qdrant collection
= rebuildable semantic index
```

## V1 acceptance target

- import one 50,000-character script;
- import ten scripts without duplicate rows;
- preserve source file, episode, scene and character offsets;
- return lexical and semantic results with source references;
- keep production and acceptance Drama collections physically isolated;
- expose truthful indexing and parse states in Desktop UI;
- do not claim scanned PDF support without OCR.

## Status

```text
IMPLEMENTATION_IN_PROGRESS
```
