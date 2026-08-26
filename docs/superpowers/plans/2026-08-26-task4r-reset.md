# Task 4R-Reset Architecture Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild Task 4's evidence contracts so LingJi can distinguish import correctness, retrieval misses, malformed evidence, provenance consistency and unavailable safety evidence before any memory-quality score is trusted.

**Architecture:** Preserve the real Generic History adapter, extraction pipeline, SourceReadModel, MemoryDatabase, ContextPack, MemoryGateway, MCP and frozen evaluator. Add one ingestion-order read contract, one in-memory evaluation identity registry, one readiness envelope outside the frozen `EvaluationReport`, and a preparing→visible promotion state machine over the existing databases. Replace the rejected monolithic quality runner with thin orchestration; do not tune retrieval in this reset.

**Tech Stack:** Python 3.12, SQLite/WAL, existing Generic History adapter and extraction queue, FTS5/Qdrant/HybridRetriever/ContextPack/MemoryGateway/FastMCP, pytest, PowerShell 5.1-compatible validation.

## Global Constraints

- Root agent only writes plans, dispatches Luna, reviews evidence and runs independent acceptance. Root does not write product code or repair Luna changes.
- Each implementation task uses a fresh `gpt-5.6-luna` implementer, authentic RED/GREEN evidence, a focused commit set and a fresh Luna spec-and-quality review.
- The rejected Task 4 implementation is audit history, not a compatibility authority. Remove or replace its APIs when this plan says so; do not preserve defective behavior merely to reduce the diff.
- Frozen inputs remain immutable: corpus SHA-256 `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94`; questions SHA-256 `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`.
- Do not modify `src/automatic_memory/evaluation.py`, `EvaluationReport`, `evaluate_run`, `score_question`, `AutomaticMemoryAcceptanceGate`, fixture rows, question expectations or thresholds.
- Do not modify Task 3 retrieval ranking, query text, temporal/scope filters or ContextPack ordering to improve scores.
- Do not add a second database, queue, retriever, gateway, MCP server, promotion policy, evaluator, scheduler, API or permanent-memory fact source.
- `LOCAL_EXECUTION_TASK.md` remains `IDLE`: do not install/launch an Artifact, touch Production/Vault, claim owner/reboot/M5 evidence or run 100k/4R2 acceptance. Reset sentinels operate only on explicit temporary Acceptance storage/vault roots created by tests; real Production/Vault evidence remains `NOT_MEASURED`.
- Ordinary Obsidian notes remain excluded; no Task 4R-Reset code may read or rewrite the owner's Vault.
- Stable-record duplicates mean duplicate source/session/message/memory identities. Distinct records intentionally sharing content are dedup groups, not database duplicates.
- A missing/unreadable/escaped protected root is `NOT_MEASURED`, never numeric zero. No acceptance gate runs until every required functional evidence field has been measured as `READY` or `FAILED`; `NOT_MEASURED` and `INVALID` are never evaluator input.
- A well-formed empty Gateway response is a measured retrieval miss. Malformed, unknown, contradictory or duplicate evidence aborts scoring.
- A derived memory is visible as active only after all required message provenance links are committed. Incomplete or unverifiable provenance cannot appear in current retrieval.
- Same-plan repair loops stop after five reviewed rounds. A remaining load-bearing finding blocks dependent tasks.

---

### Task 1: SourceReadModel Ingestion-Order Contract

**Purpose:** Give the quality gate a real, batch-scoped persistence order without changing the newest-first UI query.

**Files:**
- Create: `src/sources/identities.py`
- Modify: `src/sources/__init__.py`
- Modify: `src/sources/read_model.py`
- Modify: `src/extraction/structured_sink.py`
- Modify only where construction call sites require the new optional arguments: direct `StructuredReadModelSink.write_batch()` callers
- Create: `tests/test_task4_reset_ingestion_order.py`
- Modify: `tests/test_source_read_model.py`
- Modify: `tests/test_structured_ingestion.py`
- Update: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Report: `docs/TEST_REPORTS/PHASE1_TASK4R_RESET_INGESTION.md`

**Interfaces:**

```python
@dataclass(frozen=True)
class ExternalMessageKey:
    source_external_id: str
    conversation_external_id: str
    message_external_id: str

@dataclass(frozen=True)
class ResolvedMessageRef:
    message_id: str
    external_key: ExternalMessageKey
    content_hash: str

SOURCE_READ_MODEL_SCHEMA_VERSION = "2"

def upsert_bundle(
    self,
    bundle: Mapping[str, Any],
    *,
    ingestion_batch_id: str | None = None,
    ingestion_ordinal_start: int = 0,
) -> dict[str, int | str]: ...

def list_ingestion_messages(
    self,
    ingestion_batch_id: str,
    *,
    limit: int = 200,
    offset: int = 0,
) -> dict[str, Any]: ...
```

- Schema v2 adds nullable `ingestion_batch_id TEXT` and `ingestion_ordinal INTEGER` to `message_records`, plus index `(ingestion_batch_id, ingestion_ordinal, message_id)`.
- `ExternalMessageKey` and `ResolvedMessageRef` are the one shared typed identity contract for import audit and promotion. They perform no case folding or inference and are exported by `src.sources`; quality and promotion code must not invent parallel tuple formats.
- Initialization migrates v1→v2 additively. Existing rows remain `NULL`; no timestamp-based or guessed backfill is allowed. Unknown versions fail closed.
- `StructuredReadModelSink.write_batch()` passes `execution_id` as the batch ID and maintains one monotonically increasing ordinal across all sources, conversations and messages in the batch.
- `upsert_bundle()` returns `next_ingestion_ordinal`. Replaying the same external message reuses its primary ID and updates the current batch/ordinal without creating another row.
- A legacy `upsert_bundle()` call with `ingestion_batch_id=None` preserves existing batch/ordinal fields and does not assign new ones. Replaying the same `execution_id` is idempotent. A later execution ID becomes the row's current ingestion owner; historical batch history remains in raw material/Work Fact audit and is not invented in this rebuildable read model.
- `list_ingestion_messages()` uses only `ORDER BY ingestion_ordinal ASC, message_id ASC`. It validates the complete selected batch before applying pagination and returns `{"items": ..., "pagination": {"limit": ..., "offset": ..., "total": ..., "has_more": ...}}`; an unknown/empty batch returns zero items with valid pagination. Missing, duplicate or non-contiguous ordinals raise `SourceReadModelError`. `list_messages()` remains newest-first, never exposes the internal batch/ordinal columns and is never used for import acceptance.

- [ ] **Step 1: Add RED migration tests that create a v1 database, reopen it with v2 code, assert the two columns/index exist, old rows remain readable with `NULL` batch fields, and schema versions other than 1/2 raise `SourceReadModelError`.**
- [ ] **Step 2: Add RED ingestion tests with two conversations and two sources whose timestamps conflict with adapter order. Assert `list_messages()` remains newest-first while `list_ingestion_messages()` returns global ordinals `0..N-1`. Add missing/duplicate/non-contiguous ordinal failure cases.**
- [ ] **Step 3: Run `./.venv/bin/python -m pytest -q tests/test_task4_reset_ingestion_order.py tests/test_source_read_model.py tests/test_structured_ingestion.py`; preserve the exact failures caused by absent v2 columns/API.**
- [ ] **Step 4: Implement the additive migration, batch/ordinal writes and dedicated read API. Do not change source/conversation/message stable-ID generation or the UI pagination contract.**
- [ ] **Step 5: Re-run the focused tests to GREEN, then run `tests/test_source_service.py`, Generic History adapter tests and extraction resume/idempotency tests. Require fixture hashes unchanged, `git diff --check`, acceptance sync and local handoff PASS.**
- [ ] **Step 6: Commit code/tests as `feat: add ingestion order evidence contract`, then docs/report as `docs: record task4 reset ingestion evidence`.**

**Acceptance:** A 145-message batch is returned once in adapter persistence order; replay creates zero duplicate source/session/message rows; newest-first product reads remain unchanged; v1 user databases migrate without data loss; independent Luna reports no Critical/Important issue.

### Task 2: Stable Import Audit and Intentional Dedup Groups

**Purpose:** Compare adapter output with persisted rows without writing fixture labels or treating equal content as duplicate database records.

**Files:**
- Refactor: `src/automatic_memory/quality_evidence.py`
- Refactor: `src/automatic_memory/quality_gate.py`
- Create: `tests/evaluation/test_task4_reset_import_audit.py`
- Modify: `tests/evaluation/test_automatic_memory_gate_integrity.py`
- Update: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Report: `docs/TEST_REPORTS/PHASE1_TASK4R_RESET_IMPORT_AUDIT.md`

**Interfaces:**

```python
@dataclass(frozen=True)
class ExpectedImportedRow:
    source_external_id: str
    conversation_external_id: str
    message_external_id: str
    ingestion_ordinal: int
    sequence: int
    role: str
    content_hash: str
    occurred_at: str

    @property
    def stable_external_key(self) -> ExternalMessageKey: ...

@dataclass(frozen=True)
class ContentHashGroup:
    content_hash: str
    member_external_keys: tuple[ExternalMessageKey, ...]

@dataclass(frozen=True)
class StableDuplicateSummary:
    source_records: int
    conversation_records: int
    message_records: int
    memory_records: int

    @property
    def total(self) -> int: ...

@dataclass(frozen=True)
class ImportedEvidenceAudit:
    expected_rows: int
    actual_rows: int
    missing_external_keys: tuple[ExternalMessageKey, ...]
    extra_external_keys: tuple[ExternalMessageKey, ...]
    stable_duplicates: StableDuplicateSummary
    ordered_external_key_matches: int
    role_matches: int
    sequence_matches: int
    timestamp_matches: int
    content_hash_matches: int
    source_matches: int
    conversation_matches: int
    intentional_content_hash_groups: tuple[ContentHashGroup, ...]

    @property
    def ready(self) -> bool: ...

    @classmethod
    def from_read_model(
        cls,
        read_model: SourceReadModel,
        *,
        ingestion_batch_id: str,
        expected_rows: Sequence[ExpectedImportedRow],
    ) -> "ImportedEvidenceAudit": ...
```

- Expected rows are flattened from adapter `ExtractionBatch.structured_sources` before persistence, using the same global ordinal contract as Task 1. External identities are exact, case-sensitive adapter strings; no trimming, case folding or Unicode rewriting occurs after adapter validation.
- Actual rows come only from `list_ingestion_messages(batch_id)` and are compared positionally without sorting.
- Missing/extra/duplicate message comparison uses `ExternalMessageKey`, never message external ID alone.
- `ready` requires equal positive counts, zero missing/extra/stable duplicates and exact count matches for ordered IDs, role, sequence, timestamp, content hash, source and conversation.
- `ImportedEvidenceAudit.stable_duplicates` supplies source/conversation/message counts and sets memory count to zero. Task 5 supplies the real promoted-memory duplicate count; Task 6 creates a final `StableDuplicateSummary` and passes only its `total` to the frozen evaluator. Repeated `content_hash` among distinct stable messages is recorded only in `intentional_content_hash_groups`.
- The frozen corpus must produce exactly five two-message intentional groups whose source/conversation/message/fact/citation identities differ.
- Each content group is ordered deterministically by content hash and then stable external key; group order cannot depend on SQLite row order. Fact/citation identities are evaluation-only labels, so they are asserted for uniqueness directly from the frozen corpus rows and never added to the persistence audit or storage.
- Delete `_apply_fixture_metadata()` and any mutation of persisted content, role, time, privacy, project, agent scope or `metadata.fixture_*`. Fixture labels live only in evaluation-process memory.

- [ ] **Step 1: Write RED tests for extra/missing persisted rows, duplicate external message identity, swapped ingestion order, wrong role/sequence/timestamp/hash/source/conversation and batch leakage. Each defect must make `audit.ready` false.**
- [ ] **Step 2: Write RED tests proving two distinct messages with the same content hash yield stable duplicate count `0`, and the frozen corpus yields exactly five valid intentional groups. Assert persisted SourceReadModel rows are byte-for-byte unchanged by the audit.**
- [ ] **Step 3: Run `./.venv/bin/python -m pytest -q tests/evaluation/test_task4_reset_import_audit.py tests/evaluation/test_automatic_memory_gate_integrity.py`; preserve the exact false-duplicate/newest-first failures.**
- [ ] **Step 4: Implement the batch-scoped positional audit and remove fixture metadata mutation. Do not add labels to MemoryDatabase, SourceReadModel, candidate metadata or relationship JSON.**
- [ ] **Step 5: Run focused tests and Task 1 regression; verify actual `145/145`, all field matches `145/145`, stable duplicates `0`, intentional content groups `5`, fixture hashes exact and `git diff --check` clean.**
- [ ] **Step 6: Commit code/tests as `fix: separate import identity from content dedup`, then docs/report as `docs: record task4 reset import audit`.**

**Acceptance:** Import readiness reflects every stored field and order; intentional equal-content scenarios do not fail the duplicate gate; no fixture label or lifecycle override is written to product storage; independent Luna reports no Critical/Important issue.

### Task 3: Typed ContextPack Identity Registry and Selector

**Purpose:** Validate memory and raw-message sections using their real identities while keeping question expectations out of selection.

**Files:**
- Create: `src/automatic_memory/evidence_identity.py`
- Refactor: `src/automatic_memory/quality_gate.py`
- Modify: `src/automatic_memory/__init__.py`
- Create: `tests/evaluation/test_task4_reset_section_identity.py`
- Modify: `tests/evaluation/test_automatic_memory_end_to_end.py`
- Update: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Report: `docs/TEST_REPORTS/PHASE1_TASK4R_RESET_SECTION_IDENTITY.md`

**Interfaces:**

```python
@dataclass(frozen=True)
class MessageIdentity:
    source_id: str
    conversation_id: str
    message_id: str
    content_hash: str
    memory_id: str

@dataclass(frozen=True)
class EvaluationIdentityRegistry:
    memory_to_fact: Mapping[str, str]
    message_to_fact_citation: Mapping[MessageIdentity, tuple[str, str]]

@dataclass(frozen=True)
class SelectedEvidence:
    fact_ids: tuple[str, ...]
    citation_ids: tuple[str, ...]
    stable_identities: tuple["SectionIdentity", ...]

@dataclass(frozen=True)
class MemorySectionIdentity:
    kind: Literal["core_memory", "retrieved_memory", "project_authority_memory"]
    memory_id: str

@dataclass(frozen=True)
class RawMessageSectionIdentity:
    kind: Literal["raw_message_evidence"]
    source_id: str
    conversation_id: str
    message_id: str
    content_hash: str
    memory_id: str

SectionIdentity = MemorySectionIdentity | RawMessageSectionIdentity

class EvidenceIdentityError(ValueError): ...

def build_identity_registry(
    *,
    corpus: Sequence[CorpusRecord],
    persisted_messages: Sequence[Mapping[str, Any]],
    promotion_bindings: Mapping[str, str],
    message_links: Sequence[Mapping[str, Any]],
) -> EvaluationIdentityRegistry: ...
def select_context_evidence(
    pack: Mapping[str, Any],
    registry: EvaluationIdentityRegistry,
    *,
    limit: int = 2,
) -> SelectedEvidence: ...
```

- `core_memory`, `retrieved_memory` and `project_authority_memory` require `memory_id`; citation memory ID, when present, must agree. They do not require message identity.
- `raw_message_evidence` requires `memory_id`, `source_id`, `conversation_id`, `message_id`, `content_hash`; section and citation fields must agree, content hash must match the returned text, and message-bound fact must equal memory-bound fact.
- Unknown kind/identity, duplicate canonical identity, missing field or contradiction raises `EvidenceIdentityError`; it is never converted to an empty retrieval miss.
- The registry is built once after real import/promotion and before questions. It maps opaque persisted memory IDs and canonical message identities to evaluation labels only in memory. The selector signature cannot accept an `EvaluationQuestion`.
- `limit` counts distinct fact IDs. A raw-message citation attached to an already-selected memory fact enriches that fact without consuming another fact slot. A memory section and its linked raw section are not duplicate identities; repeating either canonical section identity is an error.
- Delete rejected `select_retrieval_evidence`, fixture metadata lookup and identity-only `_pack_identity` exports.

- [ ] **Step 1: Write RED table tests for all four section kinds. Prove memory sections without message IDs succeed; raw sections missing any canonical field fail; citation/section/hash/fact contradictions fail.**
- [ ] **Step 2: Write RED tests for unknown identities, duplicate canonical identities and a pack containing both a memory fact and its raw citation. Require one fact plus the correct citation, not two facts or a silent drop.**
- [ ] **Step 3: Write a mutation test that changes every question expected/forbidden/citation ID after the registry is frozen and proves selector output unchanged; then change actual Gateway output and prove selector output changes.**
- [ ] **Step 4: Run `./.venv/bin/python -m pytest -q tests/evaluation/test_task4_reset_section_identity.py tests/evaluation/test_automatic_memory_end_to_end.py`; preserve RED failures from the current all-sections-require-message selector.**
- [ ] **Step 5: Implement typed registry/selector, delete rejected helpers, run focused tests and ContextPack/Gateway/MCP Task 3 regressions, fixture hashes, `git diff --check`, acceptance sync and local handoff.**
- [ ] **Step 6: Commit code/tests as `refactor: type automatic memory evidence identities`, then docs/report as `docs: record task4 reset section identity`.**

**Acceptance:** Every returned identity is verified by kind; 100 well-formed empty packs remain valid misses; any malformed/unknown/duplicate/contradictory item aborts scoring; expectation mutation cannot affect selection; independent Luna reports no Critical/Important issue.

### Task 4: Readiness Envelope and Protected-Tree Gate Eligibility

**Purpose:** Keep unavailable evidence outside the frozen evaluator and prevent partial evidence from becoming PASS, FAIL or zero pollution.

**Files:**
- Refactor: `src/automatic_memory/quality_evidence.py`
- Refactor: `src/automatic_memory/quality_gate.py`
- Modify: `scripts/automatic_memory_quality_gate.py`
- Create: `tests/evaluation/test_task4_reset_readiness.py`
- Update: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Report: `docs/TEST_REPORTS/PHASE1_TASK4R_RESET_READINESS.md`

**Interfaces:**

```python
class EvidenceState(str, Enum):
    NOT_MEASURED = "not_measured"
    INVALID = "invalid"
    FAILED = "failed"
    READY = "ready"

@dataclass(frozen=True)
class QualityEvidenceReadiness:
    import_audit: EvidenceState
    promotion_provenance: EvidenceState
    gateway_selection: EvidenceState
    production_sentinel: EvidenceState
    mcp_parity: EvidenceState
    qdrant_degradation: EvidenceState
    corruption_isolation: EvidenceState
    context_baseline: EvidenceState
    scale: EvidenceState
    owner_review: EvidenceState
    reboot_recovery: EvidenceState
    mac_release: EvidenceState
    windows_release: EvidenceState

    @property
    def functional_measured(self) -> bool: ...

    @property
    def functional_ready(self) -> bool: ...

    @property
    def mac_release_ready(self) -> bool: ...

    @property
    def windows_release_ready(self) -> bool: ...

@dataclass(frozen=True)
class QualityRunEnvelope:
    readiness: QualityEvidenceReadiness
    production_pollution: int | None
    evaluation_report: EvaluationReport | None
    functional_status: Literal["NOT_EVALUATED", "PASS", "FAIL"]
    phase_status: Literal["NOT_EVALUATED", "PASS", "FAIL", "BLOCKED"]
    windows_status: Literal["NOT_EVALUATED", "PASS", "FAIL", "BLOCKED"]
    blocked_reasons: tuple[str, ...]

def finalize_quality_envelope(
    *,
    readiness: QualityEvidenceReadiness,
    production_pollution: int | None,
    evaluation_report: EvaluationReport | None,
    acceptance_gate: AutomaticMemoryAcceptanceGate,
    blocked_reasons: Sequence[str] = (),
) -> QualityRunEnvelope: ...
```

- `NOT_MEASURED` means a scenario was not attempted. `INVALID` means its evidence is structurally unusable. `FAILED` means the scenario ran with valid evidence and demonstrated an acceptance breach. `READY` means it ran and met its local invariant. `functional_measured` requires every functional field to be `READY` or `FAILED`; `functional_ready` requires every one to be `READY`. `mac_release_ready` additionally requires scale, owner review, reboot recovery and Mac release evidence `READY`; `windows_release_ready` requires Mac readiness plus Windows evidence. Windows never blocks the earlier Mac phase.
- If sentinel capture fails for missing/unreadable/symlink escape, envelope uses `production_pollution=None`, `evaluation_report=None`, `functional_status="NOT_EVALUATED"`, `phase_status="NOT_EVALUATED"`, `windows_status="NOT_EVALUATED"`, and neither functional nor full gate is called.
- If any functional field is `NOT_MEASURED` or `INVALID`, the same no-gate rule applies. A `FAILED` field is measured evidence: its real counts/booleans enter the unchanged report and must yield `FAIL`; it must never be downgraded to `NOT_EVALUATED` or an empty miss. Numeric defaults, identity-only MCP rates and synthetic context baselines must not be placed in an `EvaluationReport`.
- Only when all functional evidence is measured (`READY` or `FAILED`) does the runner construct the unchanged `EvaluationReport`. Every readiness outcome must be derived from the same real values placed in that report. It obtains the functional verdict by calling the unchanged `AutomaticMemoryAcceptanceGate` on a dataclass copy whose owner/reboot values are `100.0` and whose external blocked reasons are empty; it calls the same unchanged gate on the original report for the full verdict. A measured `FAILED` field must therefore produce frozen-gate `FAIL`; a contradictory PASS is an invalid envelope and fails closed as `NOT_EVALUATED`. No second threshold implementation is allowed.
- The Mac phase can never be `PASS` unless `mac_release_ready` is true. If functional evidence passes but scale/owner/reboot/Mac evidence is absent, phase status is `BLOCKED` with named reasons. Precedence is: `NOT_MEASURED`/`INVALID` functional evidence → `NOT_EVALUATED`; complete measured evidence containing `FAILED` or a frozen-gate threshold miss → functional/full `FAIL`; measured pass plus release evidence absent → functional `PASS`, phase `BLOCKED`; all Mac evidence passes → Mac phase `PASS`. `windows_status` is independently `BLOCKED` with `WINDOWS_AFTER_MAC` until the later Windows phase, then follows `windows_release_ready`; it never blocks the Mac phase.
- Atomic JSON publication uses a unique same-directory temporary file, flush+fsync, `os.replace`, cleanup on failure and output-path rejection inside protected roots.
- Every fail-closed runner exception publishes an envelope with `evaluation_report=None`, all three statuses `NOT_EVALUATED`, a stable reason code and cleanup inventory; it never emits a partial numeric report.

- [ ] **Step 1: Write RED tests with spy gates for every `NOT_MEASURED`/`INVALID` functional field. Assert zero gate calls, nullable pollution/report and `NOT_EVALUATED`. Add a real measured `FAILED` case and prove the frozen gate is called and the result is `FAIL`, not suppressed.**
- [ ] **Step 2: Write RED protected-tree tests for nested mutation, missing root, root/descendant symlink and unreadable descendant. Only valid before/after snapshots may yield numeric pollution.**
- [ ] **Step 3: Write RED ready-state tests that build a valid unchanged `EvaluationReport`, prove measured miss returns `FAIL`, and prove owner/reboot absence returns `BLOCKED` only after measured fields pass.**
- [ ] **Step 4: Run `./.venv/bin/python -m pytest -q tests/evaluation/test_task4_reset_readiness.py`; preserve failures showing sentinel absence or 4R2 constants currently reach the report.**
- [ ] **Step 5: Implement envelope/gate eligibility and atomic writer without changing evaluation.py. Run focused tests, frozen evaluator tests, fixture hashes, `git diff --check`, acceptance sync and local handoff.**
- [ ] **Step 6: Commit code/tests as `fix: gate quality on complete evidence readiness`, then docs/report as `docs: record task4 reset readiness`.**

**Acceptance:** Unavailable evidence never becomes zero or an evaluator input; gates are called only when all functional evidence is real; sentinel failures are explicit and safe; independent Luna reports no Critical/Important issue.

### Task 5: Promotion Provenance Preparing-to-Visible State Machine

**Purpose:** Prevent active current memory from appearing before exact message provenance is committed, and report incomplete compensation truthfully.

**Files:**
- Modify: `src/auto_review/models.py`
- Refactor: `src/auto_review/promotion.py`
- Modify: `src/automatic_memory/quality_evidence.py`
- Modify: `src/retrieval/memory_db.py`
- Modify: `src/sources/read_model.py`
- Modify: `src/storage/state_db.py`
- Modify: `src/retrieval/temporal.py`
- Create: `tests/test_task4_reset_promotion_transaction.py`
- Modify: `tests/test_auto_memory_promotion.py`
- Modify: `tests/test_automatic_memory_context_pack.py`
- Update: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Report: `docs/TEST_REPORTS/PHASE1_TASK4R_RESET_PROMOTION.md`

**Interfaces:**

```python
class PromotionProjectionState(str, Enum):
    PREPARING = "preparing"
    VISIBLE_ACTIVE = "active"
    ROLLED_BACK = "rolled_back"
    REPAIR_REQUIRED = "repair_required"

@dataclass(frozen=True)
class ProvenanceRef:
    kind: Literal["message", "event", "source", "conversation", "evidence"]
    value: str
    content_hash: str | None = None

@dataclass(frozen=True)
class ResolvedProvenance:
    linkable_messages: tuple[ResolvedMessageRef, ...]
    context_only_refs: tuple[ProvenanceRef, ...]

@dataclass(frozen=True)
class BatchLinkResult:
    created_messages: tuple[ResolvedMessageRef, ...]
    reused_messages: tuple[ResolvedMessageRef, ...]

@dataclass(frozen=True)
class ProjectionWriteResult:
    memory_id: str
    decision_id: str
    created: bool
    state: PromotionProjectionState

@dataclass(frozen=True)
class PromotionEvidence:
    candidate_id: str
    decision_id: str
    memory_id: str
    state: PromotionProjectionState
    resolved_messages: tuple[ResolvedMessageRef, ...]
    context_only_refs: tuple[ProvenanceRef, ...]
    projection_created: bool
    created_links: tuple[ResolvedMessageRef, ...]
    reused_links: tuple[ResolvedMessageRef, ...]
    removed_links: tuple[ResolvedMessageRef, ...]
    rollback_verified: bool
    error_codes: tuple[str, ...]

@dataclass(frozen=True)
class PromotionPersistenceAudit:
    expected_memory_ids: tuple[str, ...]
    persisted_memory_ids: tuple[str, ...]
    missing_memory_ids: tuple[str, ...]
    extra_memory_ids: tuple[str, ...]
    duplicate_memory_records: int

    @property
    def ready(self) -> bool: ...

def audit_promotion_persistence(
    memory_db: MemoryDatabase,
    *,
    promotion_evidence: Sequence[PromotionEvidence],
) -> PromotionPersistenceAudit: ...

def resolve_provenance_refs(
    refs: Sequence[ProvenanceRef],
    *,
    state_db: StateDatabase,
    read_model: SourceReadModel,
) -> ResolvedProvenance: ...

def link_message_memory_batch(
    self,
    messages: Sequence[ResolvedMessageRef],
    memory_id: str,
    *,
    relation_type: str = "derived_from",
    confidence: float | None = None,
) -> BatchLinkResult: ...

def prepare_derived_projection(
    self,
    *,
    memory_id: str,
    title: str,
    content: str,
    content_hash: str,
    evidence_refs: Sequence[ProvenanceRef],
    confidence: float | None,
    authority: str,
    source_kind: str,
    policy_version: str,
    decision_id: str,
    candidate_metadata: Mapping[str, Any] | None = None,
) -> ProjectionWriteResult: ...
def activate_derived_projection(
    self,
    memory_id: str,
    *,
    decision_id: str,
    required_messages: Sequence[ResolvedMessageRef],
) -> ProjectionWriteResult: ...
def remove_preparing_projection(self, memory_id: str, *, decision_id: str) -> bool: ...
def unlink_message_memory_batch(
    self,
    messages: Sequence[ResolvedMessageRef],
    memory_id: str,
) -> tuple[ResolvedMessageRef, ...]: ...
def verify_message_memory_links(
    self,
    messages: Sequence[ResolvedMessageRef],
    memory_id: str,
) -> bool: ...
def get_event(self, event_id: str) -> dict[str, Any] | None: ...
def record_promotion_event_once(
    self,
    *,
    decision_id: str,
    event_type: str,
    entity_id: str,
    payload: Mapping[str, Any],
) -> str: ...
def reconcile_incomplete_projections(self) -> dict[str, int]: ...
```

- `ReviewCandidate.source_refs` is normalized to `tuple[ProvenanceRef, ...]`. `from_mapping()` preserves mapping fields (`kind`, `value`, `content_hash`) instead of stringifying them; legacy strings normalize once at the boundary to `kind="evidence"` unless they exactly resolve as a message primary/external ID. Relationship JSON serializes the typed `{kind,value,content_hash}` records, never `repr()` or a bare string list.
- `resolve_provenance_refs(refs, *, state_db, read_model) -> ResolvedProvenance` separates linkable messages from context-only refs. Exact message primary/external refs may create links only after their content hash matches. An event ref uses new `StateDatabase.get_event(event_id)` and may create a link only when the exact event payload contains canonical message ID plus matching hash and SourceReadModel verifies it. Source/conversation/evidence refs are context-only and are never expanded into guessed message links. A resolved message always carries its primary ID, full `ExternalMessageKey` and verified content hash; every later link, activation and reconciliation comparison uses that complete identity.
- An otherwise auto-eligible candidate without exact message provenance remains `PENDING_OWNER_REVIEW` with reason `structured_message_provenance_required`; it does not become active or error.
- MemoryDatabase first writes a derived projection with persisted `memory_documents.status="preparing"`. SourceReadModel validates every `(message_id, content_hash)` and commits all new links in one SQLite transaction. MemoryDatabase changes the projection to persisted status `active` only after `verify_message_memory_links()` proves the complete canonical link set. These interfaces use the same configured `lingji_memory.db`; if their resolved paths differ, promotion stops before mutation with `REPAIR_REQUIRED` and never claims atomicity.
- Any pre-activation failure leaves no current-visible projection. Successful rollback is `ROLLED_BACK`; any unlink/remove/verification failure is `REPAIR_REQUIRED`, never `compensated`.
- `reconcile_incomplete_projections()` verifies decision ID, content hash, projection state and canonical link set; it either activates a complete preparing projection, removes verified partial state or retains `REPAIR_REQUIRED`. Repeated promotion/reconciliation is idempotent.
- `ProjectionWriteResult.created` and `BatchLinkResult.created_messages/reused_messages` are the rollback authority. Rollback removes only objects created by the current decision; it never deletes a reused projection or link.
- `audit_promotion_persistence()` derives expected visible memory IDs only from `PromotionEvidence(state=VISIBLE_ACTIVE)`, reads raw derived-projection identity rows from `MemoryDatabase` without a join, and computes `duplicate_memory_records = persisted_row_count - distinct(memory_id)_count`; it also reports missing/extra IDs. Task 6 copies this real count into `StableDuplicateSummary.memory_records`. It must not infer zero from a primary-key assumption, a mapping, or the number of promotion calls.
- Add `preparing` and `repair_required` to the temporal lifecycle vocabulary as explicitly non-current states. Gateway/ContextPack current mode exposes only persisted status `active`, including when an explicit status filter is supplied.
- StateDB must record `memory_promotion_preparing` before product mutation, then exactly one of `memory_projection_activated`, `memory_projection_rolled_back` or `memory_projection_repair_required`. `record_promotion_event_once()` uses stable event ID `promotion:{decision_id}:{event_type}` in one StateDB transaction: identical retries reuse it; the same ID with a different entity or canonical JSON payload raises and fails closed. Failure to append the start event prevents mutation; a missing terminal event is repairable from decision ID/projection/link state during reconciliation.

- [ ] **Step 1: Write RED policy tests for exact message, exact event+hash, source-only, conversation-only, ambiguous, unknown and hash-contradictory refs. Assert only exact message evidence can auto-activate.**
- [ ] **Step 2: Write RED transaction tests: second link failure rolls back the whole batch; activation failure leaves preparing/non-current state; rollback failure produces `REPAIR_REQUIRED`; reused links are never deleted.**
- [ ] **Step 3: Write RED restart/reconcile tests for crashes immediately after the start event, projection prepare, link commit, activation, and before the terminal event; cover PREPARING complete, PREPARING partial, REPAIR_REQUIRED and repeated reconciliation. Assert stable event IDs are idempotent, conflicting payload retries fail closed, no duplicate event/link/projection appears, `PromotionPersistenceAudit` reads the real projection rows and reports memory duplicates/missing/extra, and no state leaks into current ContextPack before `VISIBLE_ACTIVE`.**
- [ ] **Step 4: Run `./.venv/bin/python -m pytest -q tests/test_task4_reset_promotion_transaction.py tests/test_auto_memory_promotion.py tests/test_automatic_memory_context_pack.py`; preserve the failures from sequential links and unconditional `compensated`.**
- [ ] **Step 5: Implement typed normalization, batch links, preparing/activation/reconciliation and truthful evidence. Run promotion, source, memory lifecycle, temporal and ContextPack regressions, fixture hashes, `git diff --check`, acceptance sync and local handoff.**
- [ ] **Step 6: Commit code/tests as `refactor: make promotion provenance visibility atomic`, then docs/report as `docs: record task4 reset promotion evidence`.**

**Acceptance:** No active memory exists without its exact committed message links; ambiguous/non-message evidence does not invent a link; compensation failure remains visible as repair-required; repeated runs create no duplicate projection/link/event; independent Luna reports no Critical/Important issue.

### Task 6: Thin Quality Runner Reset and Authority Reconciliation

**Purpose:** Replace the rejected all-in-one runner with thin orchestration over Tasks 1–5 and establish a trustworthy pre-4R2 baseline.

**Files:**
- Refactor: `src/automatic_memory/quality_gate.py`
- Modify: `src/automatic_memory/__init__.py`
- Modify: `scripts/automatic_memory_quality_gate.py`
- Modify: `scripts/validate.ps1`
- Replace obsolete assertions in: `tests/evaluation/test_automatic_memory_end_to_end.py`
- Modify and preserve historical-rejection coverage in: `tests/evaluation/test_task4r1_round5_final_red.py`
- Modify and preserve historical-rejection coverage in: `tests/evaluation/test_task4r1_takeover_red.py`
- Create: `tests/evaluation/test_task4_reset_runner.py`
- Create: `tests/test_task4_reset_validation_guard.py`
- Update: `docs/PROJECT_STATUS.md`
- Update: `docs/MODULES/CODE_MAP.md`
- Update: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Replace current-result claims in: `docs/TEST_REPORTS/PHASE1_TASK9_QUALITY_SCALE_GATE.md`
- Report: `docs/TEST_REPORTS/PHASE1_TASK4R_RESET_RUNNER.md`

**Interfaces:**

```python
@dataclass(frozen=True)
class AcceptanceRoots:
    root: Path
    storage_root: Path
    vault_root: Path
    output_root: Path
    lease_marker: Path

    def validate_temporary_isolation(self) -> None: ...

@contextmanager
def temporary_acceptance_roots(
    *,
    base_directory: Path | None = None,  # tests only
) -> Iterator[AcceptanceRoots]: ...

def run_quality_gate(
    corpus_path: Path,
    questions_path: Path,
    *,
    output_path: Path,
    acceptance_roots: AcceptanceRoots,
) -> QualityRunEnvelope: ...

def publish_quality_envelope(
    envelope: QualityRunEnvelope,
    *,
    repository_output_path: Path,
) -> None: ...
```

- The public CLI does not accept arbitrary roots: it calls `temporary_acceptance_roots()` without `base_directory`. The factory uses `TemporaryDirectory(prefix="lingji-task4r-")`, creates all children itself, writes a random lease marker, and yields the typed object. Tests may inject only their own `tmp_path` as `base_directory`. Validation requires the root to have the prefix and live beneath the resolved OS temp directory (or injected test base), requires marker ownership/content, requires every child and `output_path` to resolve strictly beneath that root, and rejects all symlinks/escapes. The runner receives no settings object and must never read `settings.vault_path`, `settings.storage_path` or their contents.
- `run_quality_gate()` writes only its temporary machine JSON beneath `AcceptanceRoots.output_root`. The CLI retains the returned envelope in memory, exits the Acceptance context, verifies storage/vault/raw/temporary JSON/lease marker and the root no longer exist, and only then calls `publish_quality_envelope()` for the repository's fixed `output/validation/automatic-memory-quality.json`. That function accepts no raw DB/Vault paths or source payloads. If context cleanup raises `AcceptanceCleanupError`, the CLI replaces the in-memory result with a cleanup-failure envelope whose three statuses are `NOT_EVALUATED`, then publishes that final failure envelope; a pre-cleanup PASS/BLOCKED envelope is never published. Test-injected roots follow the same lifecycle.
- Orchestration order is fixed: verify fixture hashes → build Generic History input → adapter parse → build expected import rows → real pipeline/sink persistence → persisted audit → promotion state machine → in-memory identity registry → 100 verbatim Gateway calls → typed selection → readiness envelope → optional unchanged evaluator/gates → atomic report → cleanup.
- Remove rejected local `AutomaticMemoryFunctionalGate`, `_measured_gate_passes`, `_register_fastmcp`, `_apply_fixture_metadata`, `select_retrieval_evidence`, fixture metadata selectors and guessed/static context baseline.
- The runner does not implement 4R2. MCP parity, Qdrant degradation, corruption isolation and measured context baseline remain `NOT_MEASURED`; therefore this task's official functional/phase status is `NOT_EVALUATED` even if import/Gateway/promotion evidence is valid.
- Gateway execution audit records expected calls `100`, actual calls, structure checks, selector calls/failures, empty responses, selected items, unknown/duplicate/contradictory identities and per-question selected stable identities.
- A real Gateway vacuum is recorded as 100 retrieval misses, not selector failure. It becomes a product-quality diagnosis only after Task 4R2 completes the remaining readiness fields.
- `validate.ps1 -Mode focused -Area automatic-memory-quality` runs Reset deterministic tests. Release remains blocked and must not run 100k until Task 4R2 is approved.
- `validate.ps1 -Mode release` stops before setting `LINGJI_RUN_100K`, constructing a 100k command or invoking the scale test, with stable reason `BLOCKED_4R2_REQUIRED` while any MCP/Qdrant-degradation/corruption-isolation/context-baseline/scale readiness field is `NOT_MEASURED`; an executable guard test proves the scale test cannot silently skip or run during Reset. Task 4R2 may replace this guard only after its independent review passes.
- Update current authority docs to show Tasks 1–3 accepted, rejected Task 4 history, Task 4R-Reset result and precise remaining blockers. Preserve historical reports but remove statements that obsolete figures are current truth.

- [ ] **Step 1: Write a RED runner integration test that asserts the exact orchestration order, absence of fixture labels in storage, 145/145 import, final source/conversation/message/memory stable duplicates `0`, intentional groups `5`, 100 Gateway calls, selector execution, per-layer identities, nullable unmeasured fields and no gate calls. Monkeypatch any Production settings/Vault/storage accessor to raise and prove the runner never touches it.**
- [ ] **Step 2: Write adversarial RED cases for one persisted-order defect, one unknown Gateway identity, one missing sentinel root and one promotion repair-required state. Each must stop before scoring and publish a truthful envelope.**
- [ ] **Step 3: Run `./.venv/bin/python -m pytest -q tests/evaluation/test_task4_reset_runner.py tests/evaluation/test_automatic_memory_end_to_end.py tests/evaluation/test_task4r1_round5_final_red.py tests/evaluation/test_task4r1_takeover_red.py tests/test_task4_reset_validation_guard.py`; preserve failures caused by rejected runner APIs, missing Acceptance-root isolation, absent release guard and stale assertions. Migrate the two historical RED files to assert that their rejected behaviors remain impossible under the new contract; do not delete, skip or relabel their historical evidence. The guard test executes or instruments the PowerShell release entry and proves the stable block occurs before any 100k environment/command marker.**
- [ ] **Step 4: Rebuild `quality_gate.py` as orchestration only, update exports/script/focused validation and delete obsolete APIs. Preserve and migrate the two historical RED tests named above. Do not add retrieval tuning or 4R2 evidence.**
- [ ] **Step 5: Run `./.venv/bin/python -m pytest -q tests/test_task4_reset_ingestion_order.py tests/evaluation/test_task4_reset_import_audit.py tests/evaluation/test_task4_reset_section_identity.py tests/evaluation/test_task4_reset_readiness.py tests/test_task4_reset_promotion_transaction.py tests/evaluation/test_task4_reset_runner.py tests/evaluation/test_automatic_memory_end_to_end.py tests/evaluation/test_task4r1_round5_final_red.py tests/evaluation/test_task4r1_takeover_red.py tests/test_task4_reset_validation_guard.py tests/test_automatic_memory_acceptance_gate.py`; then run the Task 1–3 regression commands named in their reports, both fixture hashes, `git diff --check`, acceptance sync and local handoff. Confirm the machine report recomputes every aggregate from its rows and the worktree is clean.**
- [ ] **Step 6: Commit code/tests as `refactor: reset automatic memory quality orchestration`, then docs/report as `docs: reconcile task4 reset authority`.**

**Acceptance:** Reset runner uses only real product contracts and thin orchestration; no fixture label reaches storage; current documents no longer present rejected results as current truth; official status remains `NOT_EVALUATED` until Task 4R2; independent Luna reports no Critical/Important issue.

The Task 6 report and authority updates must preserve these exact historical facts as rejected/superseded evidence, never current PASS evidence: initial rejected product commits `63cf0fb` and `ec5977a` with `TDD_ORDER_NOT_MET`; round-4 product/docs commits `8743356` and `cf4f220` with authentic RED `7` targeted failures plus `2` baseline-safety failures and GREEN `57 passed, 1 warning`; round-5 product/docs commits `5be8d92997a3945dd7d83732a0350cac340c5320` and `d7fafd7` with RED `6 failed, 1 warning` and GREEN `63 passed, 1 warning`; breaker-plan commit `fafeeef`. Preserve the distinction `sentinel unavailable != pollution 0` and the final breaker ruling. Historical reports remain in Git; current documents must identify their figures as rejected or superseded rather than silently deleting them.

## Root Acceptance and Resume Gate

- [ ] Root independently re-runs each task's focused tests after its review is clean; an implementer report never substitutes for root evidence.
- [ ] Root verifies both frozen fixture hashes after every task.
- [ ] Root runs `git diff --check`, `scripts/check_acceptance_sync.py` and `scripts/check_local_execution_handoff.py` at every task boundary.
- [ ] After Task 6, a fresh high-reasoning Luna performs a whole-reset review from reset base to reset head, including all deferred Minor findings.
- [ ] Task 4R2 may resume only when all six tasks have clean independent reviews, the whole-reset review has no Critical/Important issue, the Reset machine envelope is internally consistent and the branch is clean.
- [ ] Task 4Q, macOS release and Windows remain blocked until Task 4R2 supplies real MCP/degradation/context-baseline/scale evidence and the frozen quality gate passes.

## Self-Review Checklist

- [ ] Every breaker finding maps to a task and a RED test: ingestion order (Task 1), duplicate semantics (Task 2), section identity (Task 3), sentinel readiness (Task 4), promotion consistency (Task 5), thin runner/docs truth (Task 6).
- [ ] No task modifies frozen evaluator/fixtures/thresholds or Task 3 retrieval ranking.
- [ ] No placeholder, guessed metric, fixture-label persistence, second system or physical acceptance appears in the plan.
- [ ] Interface names and status values are consistent across tasks.
- [ ] The plan stops before 4R2 and preserves Mac-before-Windows ordering.
