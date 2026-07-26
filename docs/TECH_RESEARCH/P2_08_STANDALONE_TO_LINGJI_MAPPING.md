# P2-08 Standalone Concept to LingJi Mapping

## Source limitation

The standalone auto-review source archive referenced during planning was not available in this development runtime. This integration therefore follows the architecture accepted in GitHub issue #23 and does not copy an unaudited package wholesale.

## Mapping principles

| Standalone concept | LingJi-owned implementation | Decision |
|---|---|---|
| Candidate store | Existing Obsidian candidate files and stable IDs | Reuse; no second store |
| Approval/rejection executor | `MemoryReviewService` | Reuse; Auto Review cannot call owner actions |
| Memory lifecycle | `MemoryLifecycleService` | Reuse as only writer |
| Audit database | `StateDatabase.append_event()` | Reuse existing event stream |
| OFF/SHADOW/ACTIVE mode | `AutoReviewMode` | Contract retained; ACTIVE rejected |
| Rule engine | `DeterministicAutoReviewEvaluator` | Reimplemented as pure LingJi module |
| Security/privacy checks | `auto_review.security` plus existing candidate metadata | Deterministic hard ceiling |
| Duplicate detection | `NormalizedDuplicateDetector` | Stateless comparison over supplied existing records |
| Evidence merge | `evidence_append_proposal()` | Proposal metadata only; no write |
| Risk score | `calculate_risk()` | Monotonic; plugins can only add risk |
| Audit hash chain | Optional fields in existing event payload | Verification metadata, not second authority |
| AI reviewer | Deferred to P2-08B | Local-only, advisory, risk-increasing |
| Production YAML policy store | None | Rejected |
| Direct Obsidian/SQLite/Qdrant mutation | None | Rejected |
| Automatic Core Memory promotion | None | Rejected |

## Hard-rule ownership

Hard manual-review policy is implemented inside LingJi and tested directly. No external plugin may downgrade or delete those findings.

## Deferred audit work

A line-by-line security audit of the standalone v0.2.0 archive remains impossible until the archive is supplied. Before any future feature is copied, its source, license, dependencies, persistence behavior, mutation paths and tests must be reviewed against this mapping.
