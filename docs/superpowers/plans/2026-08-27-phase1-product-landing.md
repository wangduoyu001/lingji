# LingJi Phase 1 Product Landing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 不增加产品功能或替换现有技术栈，把已经实现的自动记忆组件接入正式运行时，并交付一个主人能看懂、无需代码操作、可完成 macOS 真机验收的灵机第一阶段产品。

**Architecture:** 保持 `src/`、认证的 `127.0.0.1:8766`、`desktop/lingji-control/`、SQLite、Obsidian、Qdrant、现有 Extraction/Work Fact/MemoryGateway 不变。新增代码仅承担现有组件的组合、状态投影和 UI 接线；不创建第二套服务、队列、数据库、检索器、配置中心或 UI。先结束当前 Task 4R-Reset 的证据边界，再完成正式 Sidecar 自动化生命周期、来源授权与扫描、主人界面、端到端恢复，最后运行质量、发布和真机验收。

**Tech Stack:** Python 3、FastAPI、SQLite、watchfiles、现有 Extraction Pipeline、Work Fact、React/TypeScript、Tauri、Qdrant、pytest、现有 Desktop smoke/e2e 脚本。

## Global Constraints

- 基准工作树：`codex/phase1-automatic-memory`；计划编写时 HEAD 为 `d0fe744fe30ba9a27822b39903c6b6146a5a1d3d`。
- 不增加 Opportunity Center、媒体、模型、云上传、第三方抓取或新的记忆算法。
- 不替换 Qdrant，不做向量重构；只验证现有向量路径、降级和重建边界。
- 不抓 Cookie、Token、浏览器缓存、Claude/Codex 私有数据库，不注入或控制第三方 AI 进程。
- 普通 Obsidian 文档默认不读；仅 `_LingJi/Memory Inbox`、`_LingJi/Memory Library`、`lingji_memory: true` 进入范围，`lingji_memory: false` 最高优先级。
- 正式 Desktop 只访问认证的 `127.0.0.1:8766`，打包 Sidecar 是唯一正式后台运行时。
- 每个实现单元由一名全新 `gpt-5.6-luna` 实现、一名全新 Luna 独立审查；根代理只拆分、调度、验收，不写功能代码。
- 每个单元先写失败测试，再写最小实现；每个实现与文档证据分别保持清晰提交。
- 一个单元最多两轮修复。第二轮仍有 Critical/Important 时停止继续修补，由根代理做边界重判，不进入无限循环。
- 当前 `LOCAL_EXECUTION_TASK.md` 为 `IDLE`；在发布候选身份、Artifact 与验收任务单锁定前，不得安装、启动真实发布版或访问主人 Production/Vault。
- 每个产品变化同步 `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`；当前状态同步到 `docs/PROJECT_STATUS.md` 和 `docs/MODULES/CODE_MAP.md`，不得把历史失败数字写成当前通过。

---

## File Map

### Existing components to compose, not rewrite

- `src/automatic_memory/source_registry.py`：授权、撤销、来源和扫描持久状态。
- `src/automatic_memory/snapshot.py`：一致性快照和内容寻址 raw。
- `src/automatic_memory/checkpoint.py`：lease、checkpoint、续扫和 snapshot queue admission。
- `src/automatic_memory/watcher.py`：文件事件与 5 秒防抖。
- `src/automatic_memory/scheduler.py`：启动扫描、15 分钟 reconciliation、每日完整性和单源隔离。
- `src/extraction/bootstrap.py`、`src/extraction/pipeline.py`、`src/extraction/worker.py`：唯一正式解析和提取链。
- `src/work/`：唯一 Work Fact 事实链。
- `src/control/api.py`、`src/control/automatic_memory_api.py`、`src/control/work_routes.py`：唯一 8766 API。
- `desktop/lingji-control/`：唯一正式 UI。

### New focused composition files allowed

- `src/automatic_memory/discovery.py`：只读元数据发现和来源候选 DTO；不得读取聊天正文。
- `src/automatic_memory/runtime.py`：组合 Registry、SnapshotJobRunner、Scheduler、Extraction 和 Work Fact；不包含业务规则副本。
- `src/automatic_memory/path_policy.py`：按来源类型枚举授权 root 内允许文件并映射到已有 adapter。
- `desktop/lingji-control/src/pages/MemorySourcesPage.tsx`：首次授权和来源接管状态的唯一主人页面。
- `desktop/lingji-control/src/pages/memorySourcesApi.ts`、`memorySourcesTypes.ts`：自动记忆 API/DTO。
- `desktop/lingji-control/tests/e2e_owner_memory_flow.mjs`：真实渲染的主人主流程验收。

---

### Task 0: Close the Promotion Boundary Once

**Purpose:** 只完成当前 Task 4R-Reset Task 5 的 Repair Round 2，关闭已经明确列出的 promotion provenance/state-machine 缺口；不进入 Task 6 runner。

**Files:**
- Modify: `src/auto_review/promotion.py`
- Modify: `src/auto_review/models.py`
- Modify: `src/storage/state_db.py`
- Modify: `src/retrieval/memory_db.py`
- Modify: `src/sources/read_model.py`
- Test: `tests/test_task4_reset_promotion_transaction.py`
- Docs: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`

**Interfaces:**
- Preserve all public evaluator thresholds and frozen corpus/question hashes.
- `AutoMemoryPromotionService.evaluate(...)` must return stable fail-closed outcomes for malformed provenance; it must not raise raw constructor errors.

- [ ] **Step 1: Write RED tests for the six open Repair Round 2 findings.** Cover duplicate canonical message refs, malformed `messages` payload shapes, malformed typed provenance, secret/path/fixture leakage through ordinary promotion events, noncanonical direct prepare calls, and the named crash/reconcile/rollback matrix.
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/test_task4_reset_promotion_transaction.py`; require behavioral failures, not collection errors.**
- [ ] **Step 3: Implement only the boundary repairs required by those failing tests.** Do not modify retrieval ranking, frozen fixtures, Desktop, Production/Vault, Task 4R2, 100k or release code.
- [ ] **Step 4: Run the Task 5 focused matrix, Task 1–4 reset regressions, direct source/memory/lifecycle/timeline regressions, fixture hash checks, `py_compile`, `git diff --check`, acceptance sync and local handoff.**
- [ ] **Step 5: Dispatch a fresh Luna review.** Acceptance requires `Spec PASS`, `Quality APPROVED`, zero Critical and zero Important. If Repair Round 2 fails, stop and re-plan; do not authorize Repair Round 3.
**Acceptance:** Task 5 promotion boundary has no open Critical/Important; no retrieval, runner, Desktop, Production/Vault, 100k or release scope is touched; Repair Round 2 is the final authorized repair round.

**Breaker and final composition quarantine (2026-08-27):** Repair Round 2 review at product/docs head `3227a279990e3977b73a8f0ba7463aeed13deeb2` returned Spec FAIL / Quality Needs fixes because the real recovery matrix was incomplete, the compatibility event path bypassed redaction, and non-finite ordinary payloads were persistable. The one-shot closeout implementation closed the two serialization blockers, but independent review at `f414a4f09cb92f0c30bc5124e34112263bbce84f` rejected the claimed twelve-case durable proof. The bounded owner-review quarantine then blocked fresh evaluation, legacy error recovery and unconfirmed preparing recovery, but its final review still found the public reconcile method can preserve an already-active legacy projection and append a terminal event without durable owner approval. Its repair cap is exhausted; there is no further state-machine patch. The production ruling is therefore composition-level isolation: packaged startup, scheduler, worker and recovery paths MUST NOT call `AutoMemoryPromotionService.evaluate/promote/submit/reconcile_incomplete_projections/rebuild_derived_projections`. Automatic archival, structured evidence, lexical/vector retrieval and pending-candidate display continue. Only the explicit authenticated owner-confirmed approve/reject actions may call the promotion service. Tasks 1–9 may proceed under this enforced isolation, and Task 2/3 tests must monkeypatch every forbidden background seam to raise so an accidental call fails the build.

### Task 1: Close the Thin Runner and Authority Boundary

**Purpose:** 完成现有 Task 4R-Reset Task 6 thin-runner 收口和 whole-reset review；完成后不再扩展证据框架，立即转入产品接线。

**Files:**
- Modify only the Task 6 files authorized by `docs/superpowers/plans/2026-08-26-task4r-reset.md`
- Modify: `src/automatic_memory/quality_gate.py`
- Modify: `src/automatic_memory/quality_evidence.py`
- Test: reset runner tests selected by `docs/superpowers/plans/2026-08-26-task4r-reset.md`
- Docs: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Docs: `docs/PROJECT_STATUS.md`
- Docs: `docs/MODULES/CODE_MAP.md`

**Interfaces:**
- `run_quality_gate(...)` remains a thin orchestrator and may publish only measured evidence.
- Missing or invalid evidence cannot become numeric zero, PASS or a synthetic boolean.
- Frozen evaluator thresholds, questions, corpus and retrieval behavior remain unchanged.

- [ ] **Step 1: Write RED tests for the Task 6 runner boundary.** Prove unavailable evidence never enters `EvaluationReport`, measured failures remain FAIL, cleanup failure replaces pre-cleanup verdict, and release refuses 100k before Task 4R2 readiness.
- [ ] **Step 2: Run the exact RED command recorded in the Task 6 brief and require behavioral failures.**
- [ ] **Step 3: Delete duplicate runner policy and reduce orchestration to existing product contracts.** Do not modify promotion, retrieval, fixtures, Desktop, Production/Vault, Task 4R2, 100k or release product behavior.
- [ ] **Step 4: Reconcile current authority docs.** Preserve rejected historical evidence as history, show the exact current head and keep functional status `NOT_EVALUATED` until Task 4R2 supplies real evidence.
- [ ] **Step 5: Run Task 6 focused tests, Tasks 1–5 reset regressions, fixture hashes, `py_compile`, `git diff --check`, acceptance sync and local handoff.**
- [ ] **Step 6: Dispatch a fresh Luna task review followed by a whole-reset review.** Both require zero Critical/Important. If the second repair round fails, stop and re-plan rather than authorizing another round.

**Acceptance:** Current evidence architecture is closed with no open Critical/Important; no new product capability is introduced; current docs are truthful; further work moves to runtime/UI.

**Final Task 1 disposition (2026-08-27):** Repair Round 2 passed the complete 336-test reset matrix and closed all data-admission, cleanup, measured-failure, history-coverage and evidence-integrity findings. The final independent review still found two Important acceptance gaps: this macOS environment cannot execute/instrument the actual PowerShell release entry, and runner-stage exceptions can escape without publishing a fresh truthful `NOT_EVALUATED` envelope. The two-repair cap is exhausted. Task 1 is composition-quarantined from Task 4R2, release, 100k and Artifact claims; those paths remain blocked. Runtime, authorized ingestion, Work Fact and Desktop Tasks 2–6 may proceed because they neither call this quality runner nor claim release acceptance. A later independent runner-error-envelope/release-entry task must close both gaps before Task 7/8.

### Task 2: Compose One Real Packaged Automatic-Memory Runtime

**Purpose:** 让正式 Sidecar 启动时真正启动现有 Extraction Worker、AutomaticMemory Scheduler、watcher 和 checkpoint runner，关闭时按同一实例停止。

**Files:**
- Create: `src/automatic_memory/runtime.py`
- Modify: `run_control_api.py`
- Modify: `run_packaged_control_api.py`
- Modify: `src/control/service.py`
- Modify: `src/control/api.py`
- Test: `tests/test_automatic_memory_runtime.py`
- Test: `tests/test_packaged_control_api.py`
- Test: `tests/test_automatic_memory_scheduler.py`
- Test: `desktop/lingji-control/scripts/runtime-sidecar-smoke.mjs`
- Docs: `docs/MODULES/CODE_MAP.md`
- Docs: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`

**Interfaces:**

```python
class AutomaticMemoryRuntime:
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def status(self) -> dict[str, object]: ...
    def scan_now(self, source_id: str) -> dict[str, object]: ...
    def pause(self) -> dict[str, object]: ...
    def resume(self) -> dict[str, object]: ...
```

- The runtime receives the existing `StateDatabase`, `SQLiteExtractionQueue`, extraction pipeline and settings; it does not construct alternate stores.
- Start/stop is idempotent and exact-instance scoped.
- The runtime never instantiates or invokes automatic promotion evaluation/reconciliation/rebuild. Tests replace all five forbidden background seams with raising sentinels. Explicit owner-confirmed review actions remain outside scheduler/worker startup.
- “One database/queue” means one canonical `lingji_state.db` path and one queue wrapper shared by the runtime/service/worker. Existing factories may hold multiple SQLite connections to that same file; object-identity of every connection is not required, and no second logical database/file is allowed.
- Existing scheduler/worker classes do not expose a trustworthy idle heartbeat timestamp. Task 2 returns `scheduler_heartbeat_age=null` with an explicit unavailable reason; it must not derive a fake value from scan/update timestamps or add a heartbeat daemon. Task 6 may add a real measured source under a new reviewed brief.
- Task 2 proves lifecycle and snapshot admission only. The `automatic_memory_snapshot` consumer, adapter dispatch and terminal raw→extraction outcome belong to Task 3; Task 2 must not claim a queued snapshot was fully imported.

- [ ] **Step 1: Write RED lifecycle tests.** Prove packaged start starts one worker and one scheduler, a second start is a no-op, stop releases watcher/cron/worker, and restart reuses persisted scans without a second database.
- [ ] **Step 1a: Write RED promotion-isolation tests.** Monkeypatch `evaluate`, `promote`, `submit`, `reconcile_incomplete_projections` and `rebuild_derived_projections` to raise; packaged startup, startup scan, scheduled reconciliation, restart and shutdown must complete without calling them.
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q tests/test_automatic_memory_runtime.py tests/test_packaged_control_api.py`; require failures showing missing production composition.**
- [ ] **Step 3: Implement `AutomaticMemoryRuntime` by composing existing classes.** Register shutdown through the packaged process lifecycle; do not create a second daemon or port.
- [ ] **Step 4: Add `/api/automatic-memory/runtime` to the existing secured 8766 router.** It reports `running/paused/degraded/stopped`, scheduler heartbeat age, worker state, authorized watcher count and last global error; unknown values remain `null`, never numeric zero.
- [ ] **Step 5: Run focused Python tests and `npm run test:runtime`.** Also assert the packaged process stops only the instance it started.
- [ ] **Step 6: Commit product and evidence separately, then dispatch independent Luna review.**

**Acceptance:** Launching the packaged Sidecar is sufficient to run the existing automatic-memory backend; no terminal or command line is needed; closing/stopping the instance leaves no watcher/worker thread owned by that instance.

**Final Task 2 disposition (2026-08-27):** The packaged runtime now owns one canonical state database/queue, starts the real scheduler, worker and watcher, attaches newly authorized sources without restart, exposes authenticated truthful runtime state, and passes its focused and broader runtime regressions. The final independent review retained one Important lifecycle edge: after an initially uncooperative watcher later exits, a stale scheduler cleanup error can keep the reported state at `degraded/cleanup_pending` instead of returning to `stopped`. The two-repair cap is exhausted. Task 2 is therefore accepted only as a development dependency for Tasks 3–5, not as release evidence. Those tasks must preserve truthful degraded/needs-restart presentation and must never translate this state to “已停止”. Exact sidecar process exit is the terminal cleanup boundary for this rare path. Task 6, release and Artifact acceptance remain blocked until a narrowly scoped lifecycle follow-up proves stale cleanup state is cleared or the shutdown contract is independently revised. Task 3 may continue because normal start, live authorization, scanning ownership and ordinary shutdown are verified; it must not modify this lifecycle edge or claim packaged shutdown acceptance.

### Task 6A: Close the Late Watcher Cleanup Lifecycle

**Boundary:** This is the separately approved, bounded closeout for the single Task 2 final-review lifecycle blocker. It is not Task 2 Repair Round 3 and does not reopen runtime composition, discovery, adapters, snapshot consumption, Work Fact, UI, promotion, retrieval/vector, data models or API families.

**Files:**
- Modify: `src/automatic_memory/scheduler.py`
- Test: `tests/test_automatic_memory_runtime.py`
- Docs/evidence: `docs/PROJECT_STATUS.md`, `docs/MODULES/CODE_MAP.md`, `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`, `.superpowers/sdd/2026-08-27-phase1-product-landing/task-6a-report.md`

- [x] Write and run a real-thread RED: bounded first stop/revoke observes a surviving watcher and reports `degraded/cleanup_pending`; after the event seam releases and the thread exits naturally, retry remains stale `degraded` before the fix.
- [x] Implement the smallest ownership correction: serialize concurrent scheduler cleanup retries and clear source/scheduler cleanup errors only after an empty survivor observation; preserve degraded status while any watcher survives.
- [x] Run focused Task 2 lifecycle/packaged composition, Task 3 admission/runtime, Task 4/5 API-contract regressions, packaged smoke, compileall, diff-check, acceptance sync and local handoff. Keep Task6/release/Artifact unclaimed.

**Acceptance:** Real watcher threads cannot be reported stopped while alive; a later stop/retry after their natural exit clears stale cleanup state and reports `stopped` consistently across runtime, scheduler and source registry. Process-exit cleanup remains covered by the existing packaged-wrapper subprocess boundary; no live service or Artifact is run.

**Status (2026-08-28):** Implementation/focused evidence `IMPLEMENTED_FOCUSED_PASS`, product/tests `15eb4433c9d6c3ba218e89d50bec84987ad35915`, independent Task6A review pending. Task 2's single lifecycle blocker is closed in code/tests for Task6 composition only; Task 6/release/Artifact/owner acceptance are not complete.

**Repair Round 1 status (2026-08-28):** Independent review `9ed229461165b748066b9cba3d2ed169af43db56` retained I1/I2. The sole authorized repair is product/tests `efde650e77a4ecda7f7266aefe48b29b9e8712de`: exact cleanup ownership with Cron retry and shared start/stop serialization, covered by real thread/barrier/event tests. This is the final Task6A repair; a remaining Critical/Important after re-review is `BLOCKED_AT_REPAIR_CAP`. Task 5B final review commit `bd2ff43` is recorded as `ACCEPTED_FOR_TASK6` / `ACCEPT_FOR_TASK6` (reviewed product head `8136374`).

### Task 6H: Add a Durable, Instance-Bound Runtime Heartbeat

**Boundary:** This is an independent bounded observability closeout for the Task 6 heartbeat gate. It reuses the existing StateDB, AutomaticMemoryScheduler/Cron loop, Runtime status route and WorkStore; it does not add a service, queue, API family, retrieval/promotion path, discovery behavior or UI feature.

- [x] Add RED tests for idle refresh, active Work Fact refresh without event growth, pause/stop state, restart instance isolation, clock-jump/DB-write fail-closed recovery and reconciliation cadence separation.
- [x] Persist one mutable `automatic_memory_heartbeats` row per `instance_id` with generation, UTC timestamp, lifecycle state, reason and error; update it from the existing Cron scheduler thread at a cadence no slower than 5 seconds.
- [x] Extend `/api/automatic-memory/runtime` with the heartbeat timestamp, computed age, reason, instance, generation, state and last error. Preserve nullable unavailable values when the scheduler is not composed.
- [x] Keep reconciliation polling independent from heartbeat wakeups; touch active scan Work Facts directly and never append heartbeat event rows or touch terminal/idle work.
- [x] Run focused heartbeat, Task2 lifecycle/API, compile/diff/sync/handoff checks. Do not run live 8766/8767, Artifact, Production/Vault or owner acceptance.

**Status (2026-08-28):** Focused `tests/test_task6h_heartbeat.py` `6 passed`; Task6H Repair Round 1 after independent review `8daf700f4dd5dbea90e32305a67c764420b147d7` adds source-isolated active Work Fact failure persistence/recovery and truthful UI fallback (`8 passed`). Task2 lifecycle/API `50 passed, 1 warning`; packaged/control `21 passed, 6 warnings`. Measured idle age remained `<=1s`; a `0.05s` heartbeat cadence produced one scheduler claim in `0.25s`, proving reconciliation is not heartbeat-frequency work. Task6 remains `IN_PROGRESS / NOT_ACCEPTED`; packaged crash 30/70 identity mismatch is an external Task6 gate and is not changed by this repair.

### Task 3: Connect Authorized Discovery, Snapshot and Extraction to Work Fact

**Purpose:** 让已有来源适配器从授权目录完成“发现 → 快照 → 队列 → 解析 → 索引/记忆候选 → Work Fact”，而不是只停留在 raw/job。

**Files:**
- Create: `src/automatic_memory/discovery.py`
- Create: `src/automatic_memory/path_policy.py`
- Modify: `src/automatic_memory/runtime.py`
- Modify: `src/automatic_memory/checkpoint.py`
- Modify: `src/extraction/queue.py`
- Modify: `src/extraction/pipeline.py`
- Modify: `src/work/capture_bridge.py`
- Modify: `src/work/store.py`
- Modify: `src/control/automatic_memory_api.py`
- Test: `tests/test_automatic_memory_discovery.py`
- Test: `tests/test_automatic_memory_runtime_flow.py`
- Test: `tests/test_automatic_memory_work_fact.py`
- Test: `tests/test_automatic_memory_obsidian.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class DiscoveredSource:
    kind: str
    display_name: str
    candidate_root: str
    status: str
    capability: str
    reason: str | None

def discover_source_metadata(settings: object) -> tuple[DiscoveredSource, ...]: ...
def enumerate_authorized_files(source: SourceRecord) -> tuple[Path, ...]: ...
```

- Discovery may inspect only install/path metadata; it must not read chat body before authorization.
- Snapshot queue metadata includes the existing adapter source type; the normal extraction worker consumes it through the existing registry.
- Every scan maps to one stable `work_id`; scheduler, 8766, Home, Activity and Attention reuse it.
- Candidate production in this phase stops at a pending owner-review record. Snapshot/extraction/work-fact code must not call the quarantined automatic promotion/reconcile/rebuild seams; only the authenticated explicit owner approval route may activate.

- [ ] **Step 1: Write RED discovery/path-policy tests.** Cover Codex supported transcript roots, ChatGPT official import/download directory, Generic Inbox, managed Obsidian paths, Claude unsupported/consent state, credential/auth/private DB exclusion, symlink escape and root-directory rejection.
- [ ] **Step 2: Write a RED end-to-end synthetic flow.** Authorize a temporary source, start runtime, create one supported file, and assert the chain reaches raw snapshot, extraction job terminal state, structured source/message rows, Work Outcome and next action.
- [ ] **Step 3: Implement metadata-only discovery and allowlisted enumeration.** Reuse `ChatGPTExportAdapter`, `CodexTranscriptAdapter`, `GenericAIHistoryAdapter`, `ClaudeDesktopAdapter` and `discover_memory_paths()`; do not invent another parser.
- [ ] **Step 4: Make internal snapshot jobs consumable by the existing extraction pipeline.** Ordinary workers must still reject malformed internal jobs; correct jobs must terminate as completed or failed, never remain permanently queued.
- [ ] **Step 5: Project scan lifecycle into Work Fact.** Persist start/progress/success/failure/retry/next actor with stable IDs and human-readable summaries; do not encode the primary UI in raw event JSON.
- [ ] **Step 6: Extend existing 8766 routes with discovery, scan list and scheduler-aware actions.** Required reads: discovered sources, authorized sources, recent scans, progress/counts, last error, next action. Required writes remain authorize/revoke/scan/pause/resume/retry.
- [ ] **Step 7: Run focused automatic-memory, extraction, Work Fact and Obsidian tests, then independent review.**

**Acceptance:** A supported file placed in an authorized root reaches a truthful terminal outcome without a manual API call; unsupported/malformed data fails closed; ordinary Obsidian notes remain unread; source failure does not block another authorized source.

**Task 3 Repair Round 1 ruling (2026-08-27):** Independent review at `0d7bb84` returned Spec FAIL / Quality Needs fixes with eight Important findings. The repair is limited to: terminal quarantine/failure for revoked or invalid internal jobs; zero full-body reads of ordinary Obsidian notes; robust sensitive filename exclusion; a real two-scan idempotency proof with truthful inserted/reused counts; scheduler-backed immediate scan API behavior; consistent source identity and terminal Work Fact status; exact evidence Commit metadata; and removal of automatic AI-chat Markdown publishing into the configured Obsidian Vault. The product boundary is binding: automatic chat ingestion persists the existing content-addressed raw evidence and structured read model only. It must not call the Vault document sink or create/update chat archive Markdown in the owner's configured Vault. Managed Obsidian memory input remains a separate explicitly authorized source. This repair must not add another store, parser, queue, API, indexer or UI, and must not change Task 2 lifecycle, promotion, retrieval/vector or release paths.

**Task 3 Repair Round 2 FINAL ruling (2026-08-27):** Repair Round 1 closed I1/I3/I5/I6/I8 and the normal same-source idempotency path, but independent re-review at `95cfc90` retained four Important findings. This is the final permitted repair and is limited to: recognize LF/CRLF with or without UTF-8 BOM while preserving bounded frontmatter reads and `lingji_memory:false` precedence; namespace Generic AI History structured source/conversation/message identities by the already-authorized source ID only for automatic-memory requests while preserving same-source replay idempotency and direct/manual adapter compatibility; carry truthful checked/admitted counts through 30%/70% pause-resume Work Fact projection; and record the exact three-Commit Repair Round 1 identity (`f2f7312`, `4e5d744`, `95cfc90`) before adding the Round 2 identities. No broader adapter rewrite, Task 2 repair, UI, retrieval/vector, release or architecture change is allowed. Any remaining Critical/Important after independent Round 2 review blocks Task 3 and triggers a boundary re-plan; no third repair round.

**Final Task 3 disposition (2026-08-27):** Product/test `7058da0`, evidence artifact `b83232d`, metadata correction `843b9cb`, and evidence closure `6a17ddb` are accepted as the Task 4 backend dependency. Final independent behavioral review reproduced 223 passing affected tests with zero Critical behavioral finding; its sole Important evidence-attribution finding was closed by a documentation-only follow-up and separately rechecked PASS. Task 3 therefore passes for Desktop integration. This does not authorize Artifact/release or claim Task 1 quality-runner and Task 2 rare shutdown-status quarantines are closed.

### Task 4: Deliver the One-Time Chinese Onboarding and Source Page

**Purpose:** 首次打开时让主人只需一次中文授权，并持续看见“发现了什么、是否授权、是否接管、正在扫描什么、失败后怎么办”。

**Files:**
- Create: `desktop/lingji-control/src/pages/MemorySourcesPage.tsx`
- Create: `desktop/lingji-control/src/pages/memorySourcesApi.ts`
- Create: `desktop/lingji-control/src/pages/memorySourcesTypes.ts`
- Modify: `desktop/lingji-control/src/AppPages.tsx`
- Modify: `desktop/lingji-control/src/navigation.ts`
- Modify: `desktop/lingji-control/src/pages/OverviewPage.tsx`
- Modify: `desktop/lingji-control/src/types.ts`
- Modify: `desktop/lingji-control/src/styles.css`
- Test: `desktop/lingji-control/scripts/automatic-memory-sources-smoke.mjs`
- Test: `desktop/lingji-control/tests/e2e_owner_memory_flow.mjs`

**Interfaces:**
- UI states map exactly to backend states: `detected`, `consent_required`, `authorized`, `scanning`, `current`, `degraded`, `unsupported`, `revoked`, `failed`.
- The main button set is fixed: `授权`, `撤销`, `立即扫描`, `暂停`, `继续`, `重试`, `查看结果`.
- Detection never appears as completed takeover.

- [x] **Step 1: Write RED contract tests for every source state and action.** Assert Chinese primary copy, a visible next step, disabled impossible actions, and no success copy before terminal backend evidence.
- [x] **Step 2: Write a RED rendered flow with a fake 8766 server.** First run must open source onboarding, authorize one candidate, show scanning progress, show completion counts, simulate one failure and retry it.
- [x] **Step 3: Implement the page using only existing 8766 endpoints from Task 3.** Do not add manual path text fields for detected sources; explicit folder selection remains available only for Generic Inbox/ChatGPT export location and must pass through authorization.
- [x] **Step 4: Make Home answer five questions in plain Chinese.** Show discovered sources, authorized/current sources, current activity, this-run added/updated/skipped/failed counts, and active/pending memories. Move model/vector/dimension details to Advanced Diagnostics.
- [x] **Step 5: Verify empty, loading, offline, expired authorization, unsupported Claude, revoked and failed states.** Unknown values display `尚未获得` or a specific reason, not `0` or `正常`.
- [x] **Step 6: Run TypeScript build, source-page smoke and rendered e2e, then independent review.**

**Acceptance:** A nontechnical user can finish first-run authorization and explain which sources are detected, authorized, current, unsupported or failed without reading IDs, JSON, logs or command output.

### Task 4C: Home Fact Closure (bounded follow-up)

**Boundary:** This is a new, narrowly scoped UI follow-up required by the final Task 4 review at exact commit `f3d70084e8dfb8a07e2fe46f7e1008e11cdf7c2d`. It is not a Repair Round 3 and does not reopen onboarding, backend/API, Task 2/3, CurrentWorkPanel, retrieval, vector, release or new feature work.

- [x] Add Home metrics `本次更新` and `本次跳过`; render numeric backend values when present and `尚未获得` when absent.
- [x] Replace unmeasured `后台自动运行` with neutral `尚未获得` when `queue.running` is unavailable; preserve measured running counts.
- [x] Add rendered/static RED assertions and verify the connected Home route after onboarding does not prevent the assertions.
- [x] Run focused UI/source/runtime/inspector/work-fact checks, build, rendered E2E, diff-check, acceptance sync and local handoff. Preserve the unchanged legacy smoke baseline failure in the evidence.

**Task 4C acceptance:** Home visibly asks both update/skip questions, never invents missing counts or queue activity, and the rendered fake-server flow proves both numeric and unavailable branches. Product/test commit and evidence are recorded in the Task 4 report; this follow-up remains deterministic/local evidence only and does not authorize Artifact, release, live 8766, Production/Vault or owner acceptance.

**Final Task 4 disposition (2026-08-28):** Task 4C independent review `3eaefc807402cc7bda8cc2e999189b6b483d5434` returned Spec PASS / Quality PASS with no findings. Task 4 is accepted for Task 5 composition. This ruling covers deterministic UI/build/fake-server evidence only; it does not authorize release, Artifact, live 8766, Production/Vault, real installation or owner acceptance, and it does not lift the Task 1/Task 2 quarantines.

### Task 5: Make the Existing Owner Workflow Understandable

**Purpose:** 修复上次 M5 失败的主人体验，不增加业务能力：能看见历史工作、处理真实待办、从候选记忆跳到可读证据，并只保留一个正式手动采集入口。

**Files:**
- Modify: `src/work/projector.py`
- Modify: `src/control/work_service.py`
- Modify: `src/control/work_routes.py`
- Modify: `desktop/lingji-control/src/pages/ActivityPage.tsx`
- Modify: `desktop/lingji-control/src/pages/AttentionPage.tsx`
- Modify: `desktop/lingji-control/src/pages/MemoryReviewPage.tsx`
- Modify: `desktop/lingji-control/src/pages/MemoryInspectorLoopPage.tsx`
- Modify: `desktop/lingji-control/src/pages/CaptureCenterPage.tsx`
- Modify: `desktop/lingji-control/src/navigation.ts`
- Modify: `desktop/lingji-control/src/pages/codexWorkspaceContract.ts`
- Modify: `desktop/lingji-control/src/styles.css`
- Test: `tests/test_work_control_api.py`
- Test: `tests/test_task8_work_fact.py`
- Test: `desktop/lingji-control/scripts/work-fact-smoke.mjs`
- Test: `desktop/lingji-control/scripts/memory-review-smoke.mjs`
- Test: `desktop/lingji-control/tests/e2e_owner_memory_flow.mjs`

**Interfaces:**

```text
GET  /api/work/history?limit=<n>&offset=<n>
GET  /api/work/timeline/{work_id}
POST /api/work/pending-actions/{action_id}/resolve
```

- The resolve route calls the existing `WorkStore.resolve_pending()` through `WorkControlService`; it does not invent a second task state.
- Capture Center remains the sole visible manual capture surface; the old `CapturePage` is removed from navigation or redirects to it.

- [x] **Step 1: Write RED API tests for work history pagination, friendly event summaries and pending-action resolution.** Assert stable `work_id`/`action_id`, restart persistence and no mismatch between current/history/pending projections. Task 5A initial product/tests commit: `f799b8aed526b52b259a360b7162ceef9b86b0a3`; initial RED: 4 failed behavioral tests. Repair Round 1 product/tests: `5e71cda68edfb86eac99804bc66fbfb6540bcb9c`; repair RED: 3 failed behavioral tests.
- [x] **Step 2: Write RED rendered tests for completed work, failed work, actionable pending item and readable memory provenance.**
- [x] **Step 3: Implement Activity as real recent history.** Replace raw `event_type + JSON` primary display with Chinese phase, result, time, source and next actor; keep technical codes in an expandable diagnostic area.
- [x] **Step 4: Implement Attention completion/jump behavior.** Every visible item must resolve through the backend or navigate to its related Work/Memory; no dead-end card is permitted.
- [x] **Step 5: Make memory provenance readable and clickable.** Show source name, conversation title, message excerpt, timestamp, current/history state and why it was promoted; preserve exact IDs only as secondary details.
- [x] **Step 6: Hide the duplicate legacy capture navigation entry and keep Capture Center as the single route.** Prove Capture → Work → Memory/Failure uses one identity chain.
- [x] **Step 7: Normalize state/error/empty copy and narrow-window layout.** At 900px width there is no horizontal clipping; copy actions visibly report success or failure.
- [x] **Step 8: Run focused backend, Desktop smoke, TypeScript build and rendered e2e, then independent review.**

**Acceptance:** The owner can answer: what happened, whether it succeeded, what needs action, what was remembered and which original content proves it. No primary page requires reading technical IDs or JSON.

### Task 6: Prove Automation, Recovery and Non-Interference End to End

**Purpose:** 在隔离验收目录中验证自动化长期运行，而不是只验证组件单元测试。

**Files:**
- Create: `tests/integration/test_automatic_memory_packaged_flow.py`
- Create: `desktop/lingji-control/tests/e2e_owner_memory_flow.mjs`
- Modify: `scripts/validate.ps1`
- Modify: `desktop/lingji-control/scripts/run-smoke-suite.mjs`
- Modify: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Modify: `docs/TEST_REPORTS/PHASE1_AUTOMATION_UI_GATE.md`

**Measured scenarios:**

1. Fresh install metadata discovery without content read.
2. One-time authorization and startup scan.
3. File event enters queue within 30 seconds.
4. Suppressed event is found by accelerated reconciliation using production-equivalent code.
5. Crash at 30% and 70%, restart to identical terminal counts.
6. Pause/resume/revoke and authorization expiry.
7. Corrupt source isolated while another source completes.
8. Qdrant unavailable with truthful lexical fallback.
9. Sleep/wake equivalent clock jump and process restart.
10. Third-party/Vault content, metadata and permissions sentinel unchanged.

- [x] **Step 1: Write the failing packaged-flow integration test against an Acceptance-only root.** RED includes the durable scan identity race/old-scan regression and launches the same packaged composition as release, not isolated classes directly.
- [x] **Step 2: Add a recursive file-tree sentinel.** Record relative path, SHA-256, size, mtime_ns, mode and symlink identity before sidecar startup; compare after all helpers with only explicit VaultLayout bootstrap directory paths allowlisted.
- [x] **Step 3: Make the smallest wiring fixes exposed by the integration test.** Repair Round 1 is limited to scheduler/runtime durable `scan_id/work_id` and reconciliation event identity; no retrieval, DB schema, queue, promotion or UI changes.
- [x] **Step 4: Register `focused -Area automatic-memory-landing` and one Desktop rendered test command.** A skipped core scenario remains a failure.
- [ ] **Step 5: Run and publish the ten scenarios twice from clean Acceptance roots.** Same-root idempotency and clean-root repeatability are implemented; Task6 remains NOT_ACCEPTED while Qdrant packaged lexical data, crash matrix receipt and heartbeat gate are unresolved.
- [ ] **Step 6: Dispatch independent security/quality review and record final raw counts in the single test report.**

**Acceptance:** All ten scenarios execute with real evidence; no permanent queued job, no hidden failure, no production pollution, no third-party mutation, zero duplicates, Work Fact heartbeat age at most 10 seconds.

### Task 6M: Close Adapter Dispatch Transient Lifecycle

**Boundary:** This is a new bounded product fix for the Task 6C Repair Round 1
transient-marker blocker. It is not a second Task 6C repair and does not reopen
the packaged harness, UI, retrieval, quality gate, promotion, discovery or API
surface.

- [x] Write RED behavior tests for bounded job/lease marker ownership, terminal/
  expired cleanup, active lease preservation, malformed/foreign/symlink/directory
  preservation, unlink-error receipts/retry, concurrent worker isolation and a
  real subprocess SIGKILL through `_execute_internal_snapshot`.
- [x] Bind adapter dispatch links to the existing extraction queue `job_id` and
  `lease_token`; reconcile only raw-root direct-child regular files and preserve
  durable content-addressed raw objects.
- [x] Reconcile at pipeline startup, process batch boundaries and worker stop;
  expose the existing machine-readable inventory through pipeline/worker status
  and stop outcomes, with no second observability store.
- [x] Run Task6M focused tests, affected snapshot/resume/adapter/worker/runtime/
  scheduler regressions, compileall and diff-check. Keep Task6 `IN_PROGRESS /
  NOT_ACCEPTED`; do not run live 8766/8767, Artifact, release or owner data.

**Status (2026-08-28):** Product/tests `1901628eee197e3d71d7e070c41c9e586d5468de`;
Task6M `8 passed`; affected regression `150 passed, 3 warnings`. The Task6C
transient marker defect is closed in code/tests for later independent review;
Task6 packaged final validation and release/owner acceptance remain unclaimed.

**Independent review disposition (2026-08-28):** Review report
`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6m-review.md` at reviewed
HEAD `b65f81d659f787e349d545f51c4ddb94af770d4b` is `Spec Compliance FAIL / Task
Quality NEEDS_FIXES` with 0 Critical, 5 Important and 2 Minor findings. The
authorized `REPAIR_ROUND_1` is limited to legacy-marker compatibility, complete
job/lease fail-closed proof, queue-error receipt visibility, cleanup inventory
Desktop visibility, TOCTOU hardening if needed, and a fresh packaged 30/70
crash/restart/stop receipt. Task 6 remains
`IN_PROGRESS / NOT_ACCEPTED`; do not mark `Task6M ACCEPTED_FOR_FINAL_VALIDATION`
or advance Task 6 to READY.

### Task 7: Run the Existing Quality and Scale Gate Without Expanding Product Scope

**Purpose:** 恢复 Task 4R2/100-question/100k 门禁，只评价已有产品，不把门禁继续发展成产品子系统。

**Entry gate:** Task 7 cannot start until a separately reviewed runner-error-envelope/release-entry integration task proves truthful envelope publication for every runner exception and executable/instrumented PowerShell release ordering. The current `BLOCKED_4R2_REQUIRED` quarantine remains authoritative.

**Files:**
- Modify only as authorized by existing `docs/superpowers/plans/2026-08-26-phase1-automatic-memory-followup.md` Task 4R2/4Q sections.
- Test: existing `tests/evaluation/` and `tests/performance/test_automatic_memory_100k.py`.
- Docs: `docs/TEST_REPORTS/PHASE1_TASK9_QUALITY_SCALE_GATE.md`.

- [ ] **Step 1: Supply real MCP, Qdrant outage, corrupt-source isolation, actual uncompressed context baseline and scale evidence from the production composition.** No booleans or zero counts may be hard-coded.
- [ ] **Step 2: Run the frozen 100 questions using original queries.** Exceptions, forbidden leakage and citation mismatch are measured failures, never empty misses.
- [ ] **Step 3: Run the opt-in 100k fixture outside Production/Vault.** Verify exactly 100,000 unique message identities, cleanup inventory, recursive sentinels, warm P95 samples and fixture removal.
- [ ] **Step 4: Apply the frozen gate once.** Required: recall `>=90%`, citation/activation/MCP `>=95%`, protected false promotions/stale leaks/duplicates/Production writes `0`, context reduction `>=90%`.
- [ ] **Step 5: If measured quality fails, dispatch one diagnostic Luna that classifies each failure by the first broken existing boundary.** Fix only confirmed defects; do not add reranking, models or new retrieval features in Phase 1.
- [ ] **Step 6: Independent review must confirm the report is measured, internally consistent and reproducible.**

**Acceptance:** Quality and scale pass with real production-path measurements, or the phase remains honestly FAIL/BLOCKED with a finite defect list. No synthetic evidence may unlock release.

**Task 7 measured disposition (2026-08-28):** Frozen 100-question execution is complete but
`FAIL_MEASURED_QUALITY`: facts 0.00%, citations 0.00%, and context reduction 55.28%.
Import, role/order, duplicate, formal MCP, semantic degradation and corrupt-source isolation
were measured. Per the stop rule, 100k scale and Task 8 release are not run until the
existing retrieval/evidence binding and context-size boundaries are diagnosed and repaired
under a separately authorized brief.

**Task 7 measurement repair disposition (2026-08-28):** The bounded repair added pure
measurement modules and closed the runner's false-evidence boundaries: Production/Vault is
nullable `NOT_MEASURED`, Acceptance-only sentinels are separate, corruption isolation uses two
registered temporary sources, MCP parity compares ordered identity/bounds, baseline refuses a
bounded pack, cleanup inventory is measured before/after deletion, and scale readiness is read
from the persisted quality envelope with seed `41041`. The repaired run remains
`FAIL / MEASUREMENT_NOT_ACCEPTED` (facts 0/106, citations 0/106, strict MCP 0/100, baseline
`NOT_MEASURED`; corruption isolation 2 attempted/1 completed/1 failed/1 continued/1
retrievable). 100k, release, Production/Vault and Task 8 remain prohibited until a fresh
independent review reports zero Critical/Important findings. This repair does not authorize a
retrieval diagnosis or any product feature expansion.

**Task 7O contract disposition (2026-08-28):** Task7N's bounded contract findings were repaired
without touching retrieval or activation policy. Runner and scale admission now share one strict
`CanonicalFunctionalEvidence` artifact; malformed/real FAIL output remains blocked. Automatic
activation is explicitly quarantined (`pending_owner_review`, accuracy `NOT_APPLICABLE`), promotion
audit scans all imported-message links including owner rejection, and the historical readiness test
uses current MCP failure/nullable baseline semantics. Task7O does not accept Task7 quality: the CLI
still reports measured retrieval/MCP failure and no baseline, so 100k, release, Artifact and Task8
remain prohibited until the final independent review authorizes the next bounded step.

### Task 8: Build and Perform macOS M5 Release Acceptance

**Purpose:** 交付同一 SHA 的真实发布版，并以主人是否看懂、是否无需代码操作作为最终产品门槛。

**Files:**
- Modify: `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`
- Modify: `docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md`
- Modify: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Modify: `docs/PROJECT_STATUS.md`
- Modify: `docs/CHANGELOG.md`
- Report: exact path required by the activated local task.

- [ ] **Step 1: Run `release` once on the final product tree; do not run `full` separately because release includes it.** Also run acceptance sync and local handoff checks.
- [ ] **Step 2: Build and hash-lock the macOS Sidecar/Tauri/DMG from the exact reviewed product SHA.** Activate a new local task only after Artifact identity is fixed.
- [ ] **Step 3: Install over the existing application without deleting owner data.** Verify exact-instance runtime, startup recovery, no black terminal and production/acceptance physical isolation.
- [ ] **Step 4: The root agent traverses every visible page and clicks every visible control.** Verify backend/file/process effects, loading/error/empty states, 900px layout, Cmd+K, Window menu, shortcut and Dock reopen.
- [ ] **Step 5: Run the owner flow with safe Acceptance data.** Authorize, observe automatic scan, add/modify one memory-inbox note, import one official-format ChatGPT fixture, observe Codex/generic source handling, inspect Work Fact, review one high-risk candidate and trace one memory to evidence.
- [ ] **Step 6: Keep the real UI open for owner observation.** The owner only judges whether the product is understandable and usable; all commands, hashes, logs and cleanup remain agent work.
- [ ] **Step 7: Record PASS/FAIL, push the report branch, remotely reread branch/commit/report/result/comment, clean temporary acceptance data, update receipt, push and reread again.**

**Acceptance:** Automatic gates PASS; every visible control has a real effect; no Production/Vault pollution; no third-party mutation; hot retrieval P95 `<=3s`; idle CPU average `<=3%`; owner explicitly confirms the UI is understandable and the one-time authorization flow is usable. Otherwise result is FAIL/BLOCKED, never partial PASS.

### Task 9: Windows Parity Only After macOS PASS

**Purpose:** 在不改变产品语义的前提下完成 Windows 等价运行与发布。

**Files:**
- Modify only platform-specific runtime/package/tests/docs identified after macOS PASS.
- Preserve shared Python API/DTO/data model and Desktop pages unchanged unless a cross-platform defect is proven.

- [ ] **Step 1: Confirm the remotely visible macOS result is PASS.** Any other result blocks this task before build/install.
- [ ] **Step 2: Run focused Windows path/event/Sidecar tests under PowerShell 5.1.** Verify no silent C-drive data writes.
- [ ] **Step 3: Build the same product SHA semantics into Sidecar/Tauri/NSIS and execute the same owner flow.**
- [ ] **Step 4: Verify API/DTO/state/citation semantics equal macOS and record a separate Windows result.**

**Acceptance:** Windows has the same automatic memory, UI and owner-flow semantics; NSIS, lifecycle and physical acceptance pass; unavailable Windows hardware yields BLOCKED, not a substituted CI PASS.

---

## Execution and Review Policy

For every task:

1. Root writes a bounded Luna brief with exact base/head, allowed files, forbidden scope, RED command, GREEN command and acceptance result format.
2. One fresh Luna implements and commits only that unit.
3. A different fresh Luna performs spec and quality review without modifying code.
4. Root verifies the diff, test summary, acceptance sync and clean worktree.
5. Findings are grouped into one repair brief. At most two repair rounds; after that, stop and re-plan the boundary.
6. No later task starts while the current task has an open Critical/Important finding.

Required skills during execution:

- `using-git-worktrees` for any new isolated execution tree.
- `subagent-driven-development` for fresh Luna implementation/review cycles.
- `test-driven-development` before product changes.
- `systematic-debugging` for any failing test or runtime anomaly.
- `receiving-code-review` before applying review findings.
- `requesting-code-review` after each implementation unit.
- `verification-before-completion` before every PASS/fixed claim.
- `computer-use` or the in-app browser skill for real rendered UI traversal.
- `finishing-a-development-branch` only after owner/Mac/Windows gates allow integration.

External `research` is not part of this plan because no dependency or architecture replacement is authorized. It becomes mandatory only if a Luna proposes a new third-party dependency; that proposal must stop the current task and receive root approval before research or implementation.

## Final Product Acceptance Checklist

- [ ] First launch requires one Chinese authorization flow and no code/terminal/config editing.
- [ ] Supported authorized sources are automatically scanned on startup and file changes.
- [ ] Normal file events enqueue within 30 seconds; reconciliation covers missed events within 15 minutes.
- [ ] Restart/crash/sleep recovery is visible and produces no duplicates.
- [ ] Home shows sources, current work, current run counts, failures/next action and current/pending memory.
- [ ] Activity shows real history, not only the latest item or raw JSON.
- [ ] Attention contains only actionable items and every item has a working completion/jump path.
- [ ] Memory candidates show readable source evidence; current/history status is understandable.
- [ ] Capture Center is the only visible manual capture route.
- [ ] All visible buttons are clicked in a real packaged build and have measured effects.
- [ ] Ordinary Obsidian documents, third-party AI files and credentials are untouched.
- [ ] Qdrant outage degrades truthfully to lexical retrieval; vector state remains rebuildable.
- [ ] Frozen quality and scale thresholds pass with real measurements.
- [ ] macOS owner acceptance passes before Windows begins.

## Self-Review

- Spec coverage: Tasks 0–1 close the current evidence blocker; Tasks 2–3 make existing automation real; Tasks 4–5 make it understandable; Task 6 proves stability/non-interference; Task 7 proves memory/RAG quality; Tasks 8–9 complete release acceptance.
- Scope check: no new product capability, database, queue, API service, retrieval algorithm, vector provider, cloud service or third-party scraping was added to the plan.
- Truth check: the plan explicitly corrects the current mismatch where scheduler/watcher/adapters exist but the packaged runtime and Desktop do not use them.
- Loop prevention: maximum two repair rounds per unit; unresolved important defects cause boundary re-plan rather than repeated patches.
- Owner burden: the owner performs only the one-time source authorization and final visual/usability judgment; agents perform code, commands, installation, verification, Git and cleanup.

Task 6M Repair Round 1 closure (2026-08-28): authorized review I1/I2/I3/I5 and
M1/M2 are closed by product/tests `4b51392fe448472e9099978ff2528f742dff887b`
with strict legacy/v1 hardlink ownership proof, queue-error receipts, lstat
identity protection and Desktop cleanup visibility. I4 fresh packaged 30/70 is
explicitly deferred to a new Task6V; Task6 remains `IN_PROGRESS / NOT_ACCEPTED`.
Task 6M Repair Round 1 final independent review (2026-08-28): report
`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6m-final-review.md` at docs HEAD
`28f798557459b7cd7a1187d462969e43c871450a` reviewed product/tests
`4b51392fe448472e9099978ff2528f742dff887b` and returned
`FAIL / BLOCKED_AT_REPAIR_CAP` (Critical=0, Important=2, Minor=2). Strict
terminal/queued/retrying WRONG-lease ownership and full filesystem scan
fail-closed/sanitization remain open. I4 packaged 30/70 is explicitly deferred
to a new Task6V and is not scored as a repair-product failure. Task6M remains
`NOT_ACCEPTED`; Task6 remains `IN_PROGRESS / NOT_ACCEPTED`; no further repair is
authorized.

Task 6L Durable Lease Ownership Receipt (2026-08-28) is a new bounded
architecture completion after the Task6M repair cap, not a Task6M repair. Product
and tests commits `4fd2386`, `382091b` add nullable `extraction_jobs.last_claim_lease_fingerprint`,
writes its SHA-256 lease receipt atomically on claim, preserves it through
complete/fail/release/stale-release, and clears it on retry/force generation
reset. v1 cleanup now requires marker lease hash + durable ownership + raw
hard-link identity (and current lease for running); NULL, wrong-generation and
foreign markers remain preserved. Reconciliation catches expected root,
iteration, lstat, raw-hash, queue and unlink failures at its boundary with
allowlisted codes only, while existing pipeline/worker/runtime cleanup pending
retry remains intact. Public service/MCP queue DTOs omit lease token/fingerprint,
and the existing Desktop rendered flow proves cleanup notice appearance and
recovery without fixture secrets. Focused Task6L tests: `11 passed`; required
backend regression: `218 passed, 2 warnings`; Desktop static/build/rendered
checks pass. Task6M remains `FAIL / BLOCKED_AT_REPAIR_CAP`, Task6 remains
`IN_PROGRESS / NOT_ACCEPTED`, and Task6V fresh packaged 30/70 remains deferred.

Task 6L independent review at HEAD `880bd8c1beeddfda0b0c76752038ca7da521adfe`
(`task-6l-review.md`) is `FAIL / NEEDS_FIXES`: Critical=0, Important=1,
Minor=0. Ordinary low-level queue `get()`/`list()` (and equivalent raw queue
reads) still return plaintext `lease_token` and
`last_claim_lease_fingerprint`, although Control/Capture/MCP DTOs redact them.
Task6L remains `NOT_ACCEPTED`; one bounded Repair Round 1 is authorized. Task6M
historical `FAIL / BLOCKED_AT_REPAIR_CAP` and Task6 `IN_PROGRESS / NOT_ACCEPTED`
remain unchanged.

Task 6P Queue Persistence Lease Redaction (new bounded task) is implemented in
product/tests `19525638ba3f33223fac005aa258f33dd2eb6091`; its independent review
at HEAD `815a3bb5c0d245f6f33a984e7349e927b0090418` is recorded in
`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6p-review.md` and returns
`FAIL / REPAIR_ROUND_1_AUTHORIZED` (Critical=0, Important=1, Minor=0). Queue
terminal/payload/error redaction, bounded scrubber behavior, ordinary
projections and worker ownership remain verified, but lifecycle callbacks still
receive plaintext internal claim tokens and direct execute callbacks can pass
explicit lease keys. At most one bounded lifecycle projection repair is
authorized. Task6P remains `NOT_ACCEPTED`; Task6 remains `IN_PROGRESS /
NOT_ACCEPTED`; Task6L/M history and Task6V packaged/live/Artifact gates remain
unchanged.

Task 6L Repair Round 1 (review record `9edb9eab98b5abf58999b0e16d09ece729c2e45e`,
reviewed product baseline `880bd8c1beeddfda0b0c76752038ca7da521adfe`) was limited
to I1 public queue projection leakage. Product/tests commit `2daac07` adds the
private `_get_claimed_job_internal()` lease-owner seam, keeps durable receipt
checks behind `ownership_receipt()`, and makes ordinary queue reads plus
Control/MCP projections recursively omit lease token/fingerprint material,
including nested result/error values. TDD RED was the new direct queue-read
assertion; focused repair coverage is `34 passed`, and the required backend
matrix is `219 passed, 2 warnings`. Desktop static/build/rendered checks and
compile/diff checks pass. Task6L remains `NOT_ACCEPTED` pending fresh review;
Task6M remains historical `FAIL / BLOCKED_AT_REPAIR_CAP`, Task6 remains
`IN_PROGRESS / NOT_ACCEPTED`, and Task6V packaged 30/70 remains deferred.

Task 6L Repair Round 1 final independent review (2026-08-28) is recorded in
`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6l-final-review.md`
against HEAD `d328e58926e0466a912bde8c73fbaa5f64633cf5` and repair product/tests
`2daac0733495798f3e576363a885c28e8c4ce392`: `FAIL / BLOCKED_AT_REPAIR_CAP`,
Critical=0, Important=1, Minor=0. The queue field names are now absent from
ordinary projections and all claim callers are pipeline-internal, but terminal
ordinary results can retain old lease-token values in arbitrary nested result
strings or `last_error` after the current lease is cleared. Fresh backend is
`219 passed, 2 warnings`; Task6L focused is `12 passed`; Desktop,
compile/diff/sync/handoff all pass. Task6L remains NOT_ACCEPTED and Task6
remains IN_PROGRESS / NOT_ACCEPTED; Task6M history and the Task6V deferral are
unchanged.
Task 6P Repair Round 1 (review `d61acdf39eefca8870b46b7a3172fe8ce20d5d6f`):
product/tests `924ac0c433a5d1029cce456cec1e6f24ef7dc7ba` applies the only
authorized lifecycle callback projection repair. `_notify_lifecycle` is the
single callback boundary; it sends fresh bounded safe job/result/error copies,
collects explicit lease-key values for sibling-string redaction, and falls back
to a minimal event on scrub failure without undoing committed terminal state.
Task6 remains `IN_PROGRESS / NOT_ACCEPTED`; Task6L/M blocked history is unchanged.

Task 6P Repair Round 1 final independent review (2026-08-28) is recorded in
`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6p-final-review.md`:
`FAIL / BLOCKED_AT_REPAIR_CAP`, Critical=0, Important=1, Minor=0. The callback
boundary now hides generated claimed leases, but its explicit-key collector
accepts arbitrary unbounded values and globally substitutes them, allowing
`lease_token: "a"` to corrupt ordinary callback正文. Fresh focused `10 passed`,
affected backend `266 passed, 7 warnings`, and full no-deselect `1359 passed,
11 skipped, 7 failed`; the two existing `vault_path` failures match base
`d61acdf`. Task6P remains NOT_ACCEPTED and Task6 remains IN_PROGRESS /
NOT_ACCEPTED; no further repair is authorized.

Task 6Q Trusted Lifecycle Projection Correctness is a new bounded follow-up to
the Task6P final-review I1; Task6P's historical `FAIL / BLOCKED_AT_REPAIR_CAP`
disposition is preserved. Product/tests commit
`de412d52df3478c9cfa09b11572cb3841095d897` removes the unsafe explicit-key
collector and routes the single callback projection API through explicitly
provided `trusted_known_materials`. Internal claimed paths pass only a
validated 32hex queue lease and its corresponding 64hex fingerprint (maximum
two materials); direct execute passes an empty list and only removes explicit
lease-key fields. RED covers malicious short/long/32hex payload values,
nested/list/tuple values, ordinary text preservation, trusted internal success/
failure, automatic paths, and direct execute. Task6 remains IN_PROGRESS /
NOT_ACCEPTED; Task6V packaged 30/70 and live/Artifact/owner acceptance remain
deferred.
