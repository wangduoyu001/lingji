# Owner-Review-Only Promotion Quarantine Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. This is a bounded safety fallback, not another promotion recovery repair round.

**Goal:** 在 promotion 恢复证据未获得独立放行时，明确关闭低风险候选的静默自动晋级；继续保留聊天归档、结构化提取、全文/向量检索、候选生成、主人批准/编辑批准/拒绝和既有有效记忆读取。

**Architecture:** 保留现有 `AutoMemoryPromotionService`、StateDB、MemoryDB、SourceReadModel 和主人审核 API。自动 `evaluate(...)` 只能写入 `pending_owner_review`，不能启动 prepare/link/activate saga；只有现有且带 `owner_confirmed=True` 的批准入口可以激活候选。不新增设置开关、数据库、队列、端口、生命周期状态或 UI。

## Global Constraints

- 实现基准：`f414a4f09cb92f0c30bc5124e34112263bbce84f`。
- 这是 closeout 审查失败后的既定隔离方案；不得修改或补写 `tests/test_promotion_recovery_matrix.py`，不得继续证明或修复十二案例。
- 不修改检索、向量、时间线、质量阈值、冻结 fixtures、runner、Desktop、自动扫描、Extraction、Artifact、Production 或 Vault。
- 旧聊天和原始证据仍自动归档；已有 active/superseded/history 记录不迁移、不删除、不改写。
- 自动候选必须保留证据、原因和内容哈希，UI 后续能显示并让主人确认。
- 不能以环境变量、调用方参数或隐藏配置绕过隔离。
- 先 RED、后最小实现；一名全新 Luna 实现，一名全新 Luna 独立审查；最多一轮修复。

---

### Task 0: Quarantine Automatic Activation Without Disabling Memory Intake

**Files:**
- Modify: `src/auto_review/promotion.py`
- Test: `tests/test_auto_memory_promotion.py`
- Test: `tests/test_task4_reset_promotion_transaction.py`
- Docs: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Docs: `docs/PROJECT_STATUS.md`
- Docs: `docs/MODULES/CODE_MAP.md` only if its current promotion description would otherwise be false

**Required behavior:**

1. A candidate that previously satisfied every automatic activation rule returns `pending_owner_review` with stable reason `automatic_activation_quarantined`.
2. Evaluation writes candidate/decision audit only. It writes no `memory_promotion_preparing`, activation, rollback or repair terminal event; it creates no projection and no message-memory link.
3. Re-evaluating the same candidate is idempotent and returns the same pending decision.
4. Existing explicit `approve(..., owner_confirmed=True)` still activates the same pending candidate through the existing provenance checks; missing confirmation, stale hash, malformed provenance and rejection remain fail-closed.
5. Existing active memories and current/history retrieval are unchanged. This task performs no migration and no deletion.
6. The acceptance/status documentation says exactly: automatic archival and candidate generation continue; automatic activation is quarantined; owner approval is required until a future independently approved recovery gate exists.

- [ ] **Step 1: Write RED quarantine tests.** Start with one fully eligible, real-provenance candidate and prove the current code activates it. Add assertions for pending status/reason, zero projection/link/saga rows, stable repeat evaluation, and successful explicit owner approval.
- [ ] **Step 2: Run the narrow RED command.** Require behavioral failure caused by current auto activation, not collection or fixture failure.
- [ ] **Step 3: Implement one policy boundary.** Add the quarantine reason before status selection so `evaluate(...)` cannot enter the automatic activation branch. Do not delete the owner approval path or the recovery implementation.
- [ ] **Step 4: Run focused promotion regressions.** Include candidate lifecycle, explicit approval/rejection, malformed provenance, serializer safety and current/history retrieval. Do not alter tests merely to conceal a failure.
- [ ] **Step 5: Verify governance.** Run fixture hashes, `py_compile`, acceptance sync, local handoff and `git diff --check`; commit product/tests and documentation separately.
- [ ] **Step 6: Fresh Luna review.** Require Spec PASS, Quality APPROVED, zero Critical/Important. Review must inspect for hidden bypasses and prove no ingestion/retrieval scope was changed.

**Acceptance:** No unconfirmed candidate can become active through automatic evaluation; explicit owner-confirmed approval remains functional; no projection/link/terminal saga row is created before approval; archival, evidence, retrieval and existing memories are unaffected; status and UI-facing semantics are truthful.

