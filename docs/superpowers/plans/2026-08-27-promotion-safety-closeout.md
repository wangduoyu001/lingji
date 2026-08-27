# Promotion Safety Closeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用一个最终、独立、可审查的实现单元关闭 promotion 事件脱敏、非有限数值和真实事务/重启恢复证据三个阻塞；不增加功能，不重构检索或记忆架构。

**Architecture:** 保留现有 `AutoMemoryPromotionService`、`StateDatabase`、`MemoryDatabase`、`SourceReadModel` 和 temporal/Gateway 路径。普通 promotion 事件必须使用一个安全持久化入口；没有该入口时直接 fail-closed。恢复验收使用真实 SQLite 事务、重新打开数据库和真实 Gateway/temporal 读取，不以方法级 mock 代替事务或崩溃边界。

**Tech Stack:** Python 3、SQLite、pytest、现有 promotion/read-model/MemoryGateway 实现。

## Global Constraints

- 实现基准：`3227a279990e3977b73a8f0ba7463aeed13deeb2`。
- 这是用户授权的独立安全收口，不是旧 Task 5 的继续轮次；只允许一名全新 `gpt-5.6-luna` 实现和一名全新 Luna 审查。
- 不修改 `quality_gate.py`、runner/CLI、Task 4R2、冻结 fixtures/questions/thresholds、retrieval ranking/query/filter、Desktop、Artifact、Production、Vault 或 `LOCAL_EXECUTION_TASK.md`。
- 不增加数据库、队列、服务、端口、依赖、记忆类型、检索算法或 UI。
- 不降低断言、不使用 skip、不用 method-level mock 冒充 SQLite 事务、进程重启或 post-commit crash。
- 所有测试只使用 `tmp_path` Acceptance 数据；不得读取主人数据。
- 必须保留之前通过的 duplicate/provenance/payload/prepare 行为和固定 fixture hashes。
- 代码和文档分别提交；审查要求 Spec PASS、Quality APPROVED、零 Critical、零 Important。
- 本计划不允许修复轮。首次独立审查仍失败时，关闭自动晋级并转 owner-review-only 隔离方案；不得再次修补本状态机。

---

### Task 0: Fail-Closed Promotion Persistence and Recovery Proof

**Files:**
- Modify: `src/auto_review/promotion.py`
- Modify: `src/storage/state_db.py`
- Modify only when a RED recovery test proves a defect: `src/retrieval/memory_db.py`
- Modify only when a RED recovery test proves a defect: `src/sources/read_model.py`
- Modify only when a RED Gateway assertion proves a defect: `src/gateway/memory_gateway.py`
- Test: `tests/test_task4_reset_promotion_transaction.py`
- Create if the existing test file would exceed one clear responsibility: `tests/test_promotion_recovery_matrix.py`
- Docs: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Docs: `docs/PROJECT_STATUS.md`

**Interfaces:**

```python
def AutoMemoryPromotionService._append(
    self,
    event_type: str,
    entity_id: str,
    payload: Mapping[str, Any],
) -> None:
    """Persist through append_promotion_event or raise a stable fail-closed error."""
```

```python
def StateDatabase.append_promotion_event(
    self,
    event_type: str,
    entity_id: str | None,
    payload: Any,
) -> int:
    """Reject non-finite values and persist only allowlisted/redacted JSON."""
```

Required stable outcomes:

- A state backend without callable `append_promotion_event` cannot persist an ordinary promotion event and raises a stable owner-safe error without passing the raw payload to `append_event`.
- Any nested `NaN`, positive infinity or negative infinity is rejected before JSON persistence; no `NaN`/`Infinity` token exists in `events.payload_json`.
- Raw or escaped tokens, owner paths, fixture/evaluator labels and exception text remain absent from all promotion event payloads.
- Crash/restart tests reopen `StateDatabase`, `SourceReadModel` and `MemoryDatabase` from disk before reconciliation; an in-memory service reuse does not count as restart evidence.

- [ ] **Step 1: Write and run RED serialization tests.**

```python
def test_append_requires_safe_promotion_event_boundary():
    class AppendOnlyState:
        def __init__(self) -> None:
            self.calls: list[tuple[object, ...]] = []

        def append_event(self, *args: object) -> None:
            self.calls.append(args)

    state = AppendOnlyState()
    service = object.__new__(AutoMemoryPromotionService)
    service.state_db = state
    with pytest.raises(RuntimeError, match="safe promotion event recorder unavailable"):
        service._append("memory_candidate_recorded", "candidate-1", {"token": "sk-secret"})
    assert state.calls == []

@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_ordinary_promotion_event_rejects_non_finite_nested_values(tmp_path, bad):
    database_path = tmp_path / "state.db"
    state = StateDatabase(database_path)
    with pytest.raises(ValueError, match="non-finite promotion payload value"):
        state.append_promotion_event(
            "memory_candidate_recorded",
            "candidate-1",
            {
                "structured_content": {"confidence": bad},
                "promotion_evidence": {"score": bad},
            },
        )
    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM events WHERE entity_id = ?",
            ("candidate-1",),
        ).fetchone()[0]
    assert count == 0
```

Run:

```bash
./.venv/bin/python -m pytest -q \
  tests/test_task4_reset_promotion_transaction.py \
  -k 'safe_promotion_event_boundary or non_finite_nested_values'
```

Expected RED: behavioral assertion failures showing the unsafe fallback call and persisted non-finite payload; no collection error.

- [ ] **Step 2: Implement the minimum fail-closed persistence change.** Remove the raw `append_event` compatibility path. Reject non-finite numbers recursively inside the promotion serializer before calling the generic JSON writer. Do not change generic event serialization for unrelated event types.

- [ ] **Step 3: Re-run the serialization tests to GREEN.** Require all selected cases pass and query SQLite to prove no forbidden row was inserted.

- [ ] **Step 4: Add the real transaction/recovery RED matrix.** Each case must assert durable row/event/link/projection counts before and after a newly opened set of database objects:

1. Second link row fails inside the batch: zero new links remain and the projection is not active.
2. Links commit, a later activation attempt fails, and the same decision retries: exactly one canonical link set and one terminal outcome remain.
3. Two independent SQLite connections race activation under `BEGIN IMMEDIATE`: one durable terminal wins; no contradictory active/rollback/repair terminal is possible.
4. Restart after durable start but before prepare: reconcile produces the documented terminal/repair result.
5. Restart after prepare but before links: reconcile removes or marks the incomplete projection according to the existing contract, never current-active.
6. Restart after link commit but before activation: reconcile verifies ownership and links before any visible outcome.
7. Restart after activation commit but before terminal event: complete canonical links preserve active and one terminal is repaired.
8. Active with missing terminal plus incomplete/extra/wrong-owner links: restart persists `repair_required` and never downgrades it on a second reconcile.
9. Projection deletion with `NULL` ownership and foreign ownership: FK cascade/cleanup cannot remove links it does not own.
10. Stale semantic payload says active while authoritative SQLite says non-current: `current` excludes it; `why` explains exclusion; `as_of` and `history` follow existing temporal rules.
11. The same current/why/as_of/history assertions run through raw retrieval and the formal `MemoryGateway`, with identical memory identities.
12. Promotion persistence audit separately measures missing expected IDs, extra IDs and duplicate durable rows; no primary-key or mapping assumption manufactures zero.

Run the new matrix before any recovery implementation change. Expected RED: only cases that expose actual missing behavior fail; a test that already passes is recorded as baseline evidence and must not trigger product edits.

- [ ] **Step 5: Implement only defects demonstrated by the RED matrix.** Keep changes inside the allowed promotion/storage/read-model/Gateway files. Do not add new lifecycle states, ranking logic, fixtures or acceptance policy.

- [ ] **Step 6: Run the complete focused GREEN command.**

```bash
./.venv/bin/python -m pytest -q \
  tests/test_task4_reset_promotion_transaction.py \
  tests/test_promotion_recovery_matrix.py \
  tests/test_auto_memory_promotion.py \
  tests/test_source_read_model.py \
  tests/test_memory_retrieval.py \
  tests/test_memory_lifecycle.py \
  tests/test_task7_timeline_retrieval.py \
  tests/test_automatic_memory_context_pack.py
```

If the recovery matrix remains in the existing file, omit only the nonexistent new filename from the command. Test output may contain only the two previously documented dependency deprecation warnings; no new warning or skip is accepted.

- [ ] **Step 7: Verify fixed identities and governance.**

```bash
shasum -a 256 tests/evaluation/fixtures/automatic_memory_corpus.jsonl
shasum -a 256 tests/evaluation/fixtures/automatic_memory_questions.jsonl
./.venv/bin/python -m py_compile \
  src/auto_review/promotion.py src/storage/state_db.py \
  src/retrieval/memory_db.py src/sources/read_model.py \
  tests/test_task4_reset_promotion_transaction.py
./.venv/bin/python scripts/check_acceptance_sync.py
./.venv/bin/python scripts/check_local_execution_handoff.py
git diff --check
```

Required hashes remain:

```text
bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94
338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612
```

- [ ] **Step 8: Commit and report.** Product/tests commit subject: `fix: close promotion safety boundary`. Documentation commit subject: `docs: record promotion safety closeout`. The report records every RED/GREEN command, exact counts, each recovery case outcome, full commit SHAs, hashes, warnings and scope statement.

**Acceptance:** Safe-recorder fallback and non-finite payload probes are closed; all twelve recovery cases have real durable/reopen/Gateway evidence; previous focused regressions remain green; fixtures unchanged; scope clean; independent Luna returns Spec PASS and Quality APPROVED with zero Critical/Important.

## Self-Review

- Spec coverage: unsafe fallback, non-finite JSON and every missing transaction/recovery seam each have a named behavioral case.
- Scope: no UI, runtime scheduler, quality runner, retrieval ranking, vector provider, fixture, Production/Vault or Artifact work is authorized.
- Loop prevention: this plan has one implementation and one review; failure routes to owner-review-only quarantine, not another repair.
- Type consistency: the existing `append_promotion_event` and `_append` signatures remain unchanged; no parallel persistence API is introduced.
