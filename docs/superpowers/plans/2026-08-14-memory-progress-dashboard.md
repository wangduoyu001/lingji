# 记忆进度看板 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use inline execution in this session; complete every task with its stated test cycle before starting the next.

**Goal:** 让首页成为可持续查看的记忆收纳、更新和可验证取回进度看板，而不是故障检修入口。

**Architecture:** 在 Local Control API 中增加只读的 `memory_progress` 合同，聚合既有队列、记忆统计、向量覆盖率、Autopilot 和来源发现状态；不创建第二个数据库或事实源。Desktop 首页只消费该合同并显示主人可理解的阶段、数量、最近变化和检索质量证据；技术诊断继续留在高级工具。

**Tech Stack:** Python Local Control API、MemoryStatisticsService、SQLiteExtractionQueue、React/TypeScript、现有 Node smoke、pytest。

## Global Constraints

- 所有数值必须来自现有 Runtime、队列或持久快照；未知值显示为“正在确认”，不得伪造 0 或成功。
- 自动收纳只能处理已授权或既有安全来源；不得自动批准 Core Memory、读取未经授权的正文或执行不可逆向量操作。
- “精准取回”必须显示 coverage 或验证样本的真实结论；没有验证样本时不得显示准确率。
- UI 首页服务于进度观察；设置、模型、向量与故障检修仅保留在高级工具。
- 任何产品改动同步更新 `CHANGE_ACCEPTANCE_LOG.md`、本机任务和最终 M5 验收要求。

---

### Task 1: 设计并提供只读记忆进度合同

**Files:**

- Modify: `src/control/service.py`
- Modify: `src/control/api.py`
- Test: `tests/test_control_api.py`

**Interfaces:**

- Produces: `LocalControlService.memory_progress() -> dict[str, Any]`
- Produces: `GET /api/memory/progress`，使用既有 `X-LingJi-Token` 认证。
- Contract fields: `state`, `as_of`, `intake`, `updates`, `retrieval`, `current_work`, `owner_action_count`。

- [ ] **Step 1: Write the failing service/API tests**

```python
def test_memory_progress_reports_real_counts_without_claiming_unknown_precision():
    progress = service.memory_progress()
    assert progress["intake"]["documents"] == 3
    assert progress["updates"]["queued"] == 2
    assert progress["retrieval"]["coverage_percent"] == 80
    assert progress["retrieval"]["precision_state"] == "not_measured"

def test_memory_progress_route_requires_local_token(client):
    assert client.get("/api/memory/progress").status_code == 401
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `python -m pytest -q tests/test_control_api.py -k memory_progress`

Expected: failure because `memory_progress` and `/api/memory/progress` do not exist.

- [ ] **Step 3: Implement the minimal aggregation**

```python
def memory_progress(self) -> dict[str, Any]:
    snapshot = self.memory_statistics.snapshot()
    queue = self.queue.stats()
    coverage = dict(snapshot.get("coverage") or {})
    return {
        "state": snapshot.get("state", "unknown"),
        "as_of": snapshot.get("as_of"),
        "intake": {"documents": documents, "chunks": chunks, "core_memories": core_memories},
        "updates": {"queued": queued, "running": running, "completed": completed, "failed": failed},
        "retrieval": {"coverage_percent": coverage_percent, "precision_state": "not_measured"},
        "current_work": {"state": current_state, "progress_current": progress_current, "progress_total": progress_total},
        "owner_action_count": owner_action_count,
    }
```

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run: `python -m pytest -q tests/test_control_api.py -k memory_progress`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/control/service.py src/control/api.py tests/test_control_api.py
git commit -m "feat: expose memory progress status"
```

### Task 2: 建立首页看板的纯展示合同

**Files:**

- Create: `desktop/lingji-control/src/pages/memoryProgressContract.ts`
- Test: `desktop/lingji-control/scripts/memory-progress-smoke.mjs`

**Interfaces:**

- Produces: `memoryProgressView(progress: Row): MemoryProgressView`
- Consumes: `/api/memory/progress` response from Task 1.
- Produces: `headline`, `intake`, `updates`, `retrieval` and `honestyNotice` display fields.

- [ ] **Step 1: Write the failing smoke test**

```javascript
assert.match(contract, /memoryProgressView/);
assert.match(contract, /not_measured/);
assert.match(contract, /尚未建立验证样本/);
```

- [ ] **Step 2: Run the smoke test and verify RED**

Run: `node desktop/lingji-control/scripts/memory-progress-smoke.mjs`

Expected: failure because the contract file does not exist.

- [ ] **Step 3: Implement display mapping with no fake precision**

```ts
if (retrieval.precision_state === "measured") return `${retrieval.precision_percent}%`;
return "尚未建立验证样本，暂不宣称准确率";
```

- [ ] **Step 4: Run the smoke test and verify GREEN**

Run: `node desktop/lingji-control/scripts/memory-progress-smoke.mjs`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add desktop/lingji-control/src/pages/memoryProgressContract.ts desktop/lingji-control/scripts/memory-progress-smoke.mjs
git commit -m "feat: add truthful memory progress contract"
```

### Task 3: 将首页替换为记忆进度看板

**Files:**

- Modify: `desktop/lingji-control/src/pages/OverviewPage.tsx`
- Modify: `desktop/lingji-control/src/AssistantAutopilot.css`
- Modify: `desktop/lingji-control/src/types.ts`
- Test: `desktop/lingji-control/scripts/observation-first-ui-smoke.mjs`
- Test: `desktop/lingji-control/scripts/memory-progress-smoke.mjs`

**Interfaces:**

- Consumes: Task 1 endpoint and Task 2 `MemoryProgressView`.
- Produces: 首页的“正在收纳”“自动更新”“可验证取回”三段进度，不将技术指标放在首屏。

- [ ] **Step 1: Extend the failing UI smoke**

```javascript
assert.match(overview, /正在收纳/);
assert.match(overview, /自动更新/);
assert.match(overview, /可验证取回/);
assert.equal(overview.includes("Embedding dimension"), false);
```

- [ ] **Step 2: Run the UI smoke and verify RED**

Run: `node desktop/lingji-control/scripts/observation-first-ui-smoke.mjs`

Expected: failure because the three progress sections do not exist.

- [ ] **Step 3: Add polling and dashboard sections**

```tsx
const progress = usePollingResource({ fetcher: signal => api.get("/api/memory/progress", { signal }), enabled: active, intervalMs: 8_000, staleAfterMs: 20_000, pauseWhenHidden: true });
<MemoryProgressBoard progress={progress.data} onNavigate={onNavigate} />
```

- [ ] **Step 4: Run focused UI tests and verify GREEN**

Run: `node desktop/lingji-control/scripts/observation-first-ui-smoke.mjs && node desktop/lingji-control/scripts/memory-progress-smoke.mjs`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add desktop/lingji-control/src/pages/OverviewPage.tsx desktop/lingji-control/src/AssistantAutopilot.css desktop/lingji-control/src/types.ts desktop/lingji-control/scripts
git commit -m "feat: show memory progress dashboard"
```

### Task 4: 把自动收纳、更新与检索质量纳入验收

**Files:**

- Modify: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Modify: `docs/ACCEPTANCE/MACOS_M5_LOCAL_EXECUTION_TASK.md`
- Modify: `desktop/lingji-control/scripts/run-smoke-suite.mjs`
- Test: `tests/test_memory_statistics.py`

**Interfaces:**

- Requires: Task 1–3 completed.
- Produces: 新 Artifact 的进度看板验收要求和统一 smoke 覆盖。

- [ ] **Step 1: Write the failing acceptance/snapshot test**

```python
def test_memory_snapshot_keeps_coverage_unknown_when_not_measured():
    assert status["coverage"]["coverage"] is None
```

- [ ] **Step 2: Run the test and verify RED if an unknown value is coerced**

Run: `python -m pytest -q tests/test_memory_statistics.py -k coverage`

Expected: PASS only after confirming unknown values remain unknown; otherwise fix the contract before declaring coverage.

- [ ] **Step 3: Add task-specific M5 checks**

```text
自动收纳数量、更新队列、索引覆盖率与质量测量状态必须来自 API；没有验证样本时，首页不得显示“精准/准确率已通过”。
```

- [ ] **Step 4: Run final focused gates**

Run: `node desktop/lingji-control/scripts/run-smoke-suite.mjs`, `python scripts/check_acceptance_sync.py`, and the focused Python tests.

Expected: PASS or record the exact unrelated environment blocker.

- [ ] **Step 5: Commit**

```bash
git add docs/ACCEPTANCE desktop/lingji-control/scripts/run-smoke-suite.mjs tests/test_memory_statistics.py
git commit -m "test: require truthful memory dashboard acceptance"
```

## Coverage Review

- 自动收纳：Task 1 exposes actual document/chunk/Core Memory counts; Task 3 makes them first-screen progress.
- 自动更新量化：Task 1 exposes queue states and timestamps; Task 3 displays them as work in progress, not manual repair.
- 精准取回：Task 1 exposes semantic coverage and explicitly separates coverage from unmeasured precision; Task 4 blocks false precision claims.
- 可理解 UI：Task 3 moves the primary mental model to three progress stages and retains diagnostics only behind Advanced.
- 安全：all tasks are read-only with respect to existing user knowledge and do not create a second fact source.
