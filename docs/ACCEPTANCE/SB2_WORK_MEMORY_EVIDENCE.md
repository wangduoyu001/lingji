# SB-2 — Work → Memory / Evidence 验收合同

> Status: `ACTIVE ACCEPTANCE CONTRACT`  
> Phase: `PHASE 1 — SECOND BRAIN COMPLETION`  
> Engineering node: `SB-2 — WORK → MEMORY / EVIDENCE`  
> Product branch: `feat/sb0-work-fact-contract`  
> Product baseline: `f23c20c6692d0390ae3c6930b5eba1882bbffb22`  
> SB-1 verified repository head: `441d1d2ed50a38f4e6dfb7e9c7c3d28e4404e66a`  
> Opportunity Center: `FROZEN`

## 1. Node goal

SB-2 answers one owner-visible question:

> 当灵机说一条 Capture 工作“完成”或“记住了”，能否证明它最终形成了什么可读记忆、来源是什么、证据在哪里，并从 Work 与 Memory 两边找到同一条链？

Target chain:

```text
Capture / Source
-> WorkItem(work_id)
-> ExtractionEvent / Outcome
-> Memory candidate or explicit no-memory/failure
-> MemoryRecord(memory_id)
-> readable body/summary
-> source/citation/provenance
-> Work <-> Memory bidirectional trace
```

SB-2 does **not** redesign retrieval/vector ranking, AI shared-memory access, or the whole Desktop information architecture. Those remain SB-3/SB-4/SB-5.

## 2. Hard architecture boundaries

1. `Obsidian Vault + Git` remains the permanent-memory/formal-knowledge body authority.
2. `lingji_state.db` remains runtime Work/audit state; it must not become a second permanent-memory body store.
3. `lingji_memory.db` and Qdrant remain rebuildable indexes/derived read models.
4. AI may not silently approve permanent personal memory or bypass owner review/Core Memory rules.
5. SB-2 must extend existing `src/project_memory/`, extraction/structured read model, MemoryGateway and source provenance paths. No second memory subsystem, second queue, second Desktop memory page family or duplicate database.
6. Desktop continues to use authenticated `127.0.0.1:8766`; it must not read SQLite/Qdrant/Vault directly.
7. A missing memory is not equivalent to success. The Work outcome must truthfully distinguish produced-memory, no-memory/not-applicable and failure states where relevant.

## 3. Required data contract

For a WorkItem that produces memory, the system must be able to prove:

```text
work_id
memory_id
source_id or equivalent provenance root
readable memory content/summary
memory lifecycle/status
citation/provenance data sufficient to locate the source
```

Minimum bidirectional behavior:

```text
Work detail/outcome
-> memory_id/ref(s)
-> Memory detail

Memory detail
-> originating work_id when the memory came from a WorkItem
```

The reverse link may be persisted in the existing canonical memory metadata/provenance structure or another existing authoritative field. It must not be reconstructed from UI-local state or fuzzy text matching.

## 4. Automatic acceptance requirements

### 4.1 Work → Memory

- [ ] A real supported Capture/Extraction fixture that produces memory yields a stable `work_id` and at least one stable `memory_id`/memory reference in the canonical Work evidence/result contract.
- [ ] `GET /api/work/{work_id}` exposes enough canonical evidence to navigate to the produced memory without guessing.
- [ ] Runtime restart does not break the Work → Memory link.
- [ ] Multiple produced memories, if supported by the existing extraction result, are represented without silently dropping all but one.

### 4.2 Memory → Work

- [ ] The canonical memory detail/read model exposes the originating `work_id` for Work-produced memory.
- [ ] Runtime restart/reindex does not fabricate or lose the durable origin link when the authoritative metadata exists.
- [ ] Memory not created by a WorkItem remains valid with `work_id = null/not_applicable`; no fake WorkItem is created.

### 4.3 Readable memory and provenance

- [ ] Memory detail contains owner-readable body or summary, not only IDs/counts/vector metadata.
- [ ] Source/citation/provenance is present and points to the correct captured source/raw/structured object according to existing privacy/path rules.
- [ ] `source_id`, `conversation_id`, `message_id` or equivalent structured provenance remains consistent with the extraction result when applicable.
- [ ] Missing/deleted/unavailable source is reported explicitly; UI/API must not present an empty body as successful provenance.

### 4.4 Lifecycle/governance

- [ ] Candidate/owner-review/Core Memory behavior is not bypassed by SB-2 wiring.
- [ ] A Work success may mean “extraction completed” without claiming permanent memory approval unless a memory was actually produced through the governed lifecycle.
- [ ] Failure to persist/index/project memory is visible in Work/Memory evidence and is not converted into a false success claim.
- [ ] No automatic destructive Qdrant rebuild is introduced.

### 4.5 Desktop continuity, limited to SB-2

- [ ] From an exact Work detail with a produced memory, the owner can open the exact Memory Inspector/detail target by stable ID/reference.
- [ ] From that Memory detail, the originating `work_id` is visible or navigable when applicable.
- [ ] unavailable/error is distinct from an actual empty/no-memory state.
- [ ] No broad Home/Work/Attention/Memory visual redesign is required in SB-2; that is SB-5.

## 5. Required focused tests

Audit existing tests first. Extend them rather than creating duplicate suites where practical.

Expected coverage areas:

```text
tests/test_capture_work_lifecycle.py
existing project-memory lifecycle/review tests
existing structured read-model/source tests
existing MemoryGateway/Memory Inspector API tests
new focused Work<->Memory trace tests only where no existing suite owns the behavior
Desktop Memory Inspector / Work handoff smoke
```

Development validation target:

```powershell
.\scripts\validate.ps1 -Mode focused -Area capture
.\scripts\validate.ps1 -Mode focused -Area memory
.\scripts\validate.ps1 -Mode focused -Area control
.\scripts\validate.ps1 -Mode focused -Area desktop
python scripts/check_acceptance_sync.py
```

If an area name does not exist in the current validation script, use the nearest existing focused contract and record the exact command/result rather than inventing a PASS.

## 6. Failure-path fixtures

At minimum test:

1. supported input -> memory produced -> both directions traceable;
2. extraction completes but no memory is applicable/produced -> explicit truthful state;
3. memory write/projection failure -> Work retains explicit evidence/failure, not a fake memory ID;
4. source/provenance unavailable -> Memory remains identifiable but provenance state is explicit;
5. pre-existing/non-Work memory -> no fabricated origin WorkItem.

## 7. Node exit gate

SB-2 may become `AUTOMATED_PASS` only when all automatic requirements above are backed by executed tests on the current product tree and repository commander is updated.

SB-2 `AUTOMATED_PASS` does **not** mean Phase 1 or owner M5 passes.

After SB-2 automatic pass, activate only:

```text
SB-3 — RETRIEVAL / VECTOR / MEMORY INSPECTOR VERIFICATION
```

Opportunity Center remains frozen.

## 8. Human/real-machine acceptance deferred to Phase 1 M5

- [ ] Owner can start from a newly captured remembered item, see what was actually stored, read it, verify its source, and return to the exact Work that produced it.
- [ ] Owner can distinguish “work finished but no permanent memory was produced” from “memory was produced”.
- [ ] Owner can recognize a genuine memory/provenance failure without the UI disguising it as empty/success.

These observations remain `NOT RUN` until a later same-SHA packaged Phase 1 candidate is explicitly activated for real-machine/owner acceptance.