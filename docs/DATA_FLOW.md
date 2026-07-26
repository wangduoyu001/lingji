# DATA_FLOW.md — Data Flow Authority

The former dual-system diagram is obsolete. It described independent PEMIS and second-brain products, the old bounded watcher, the 8765 API and acceptance-header behavior as the primary architecture.

The current stable data flow is maintained in:

```text
docs/ARCHITECTURE.md
```

Current implementation entry points are maintained in:

```text
docs/MODULES/CODE_MAP.md
```

Current high-level flow:

```text
Approved inputs
-> src/capture contracts
-> src/extraction adapters and persistent queue
-> raw provenance snapshot
-> Vault source documents and Structured Read Model
-> lexical index + Qdrant semantic index
-> HybridRetriever / ContextPackBuilder / MemoryGateway
-> authenticated Local Control API, MCP and internal jobs

Tauri Desktop
-> authenticated 127.0.0.1:8766 Local Control API
-> shared Python Service Layer
```

Data authority remains:

- Obsidian Vault + Git: formal knowledge and permanent-memory text.
- Raw archive: original imported material.
- SQLite: runtime state and rebuildable structured read/index data.
- Qdrant: rebuildable semantic index.

Do not copy module-level flows, scheduler intervals, workspace headers or database paths into this file. Historical diagrams remain available in Git history.
