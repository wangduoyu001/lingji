# Task 7M-Reset 独立审查：Runtime Evidence Composition

日期：2026-08-28（Asia/Shanghai）  
审查工作树：`/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`  
审查基线：`f74d798b6a7b296b7c17983090cd3af2be471c3f`  
审查 HEAD：`28bdec3ddab4aba239d38e687dda57a7ea519805`

## 结论

```text
Spec Compliance: FAIL
Task Quality: NEEDS_FIXES
Critical: 2
Important: 3
Disposition: MEASUREMENT_NOT_ACCEPTED / NO_DIAGNOSTIC_LUNA
```

Task7M 的实测失败数字本身是诚实的，但测量组合仍不能作为 4R2 或规模准入的
可信证据。尤其是 scale loader 可以接受缺少真实证据细节的伪造 envelope；在
修复前不得进入 retrieval/structured-evidence 诊断、100k、release 或 Task8。

## 独立验证

- `./.venv/bin/python scripts/automatic_memory_quality_gate.py --output output/validation/automatic-memory-quality-task7m-review.json`：退出码 `1`；`functional_status=FAIL`、`phase_status=FAIL`；事实 `0/106`、引用 `0/106`、严格 MCP `0/100`；Context baseline `not_measured`（0 字符）；Qdrant degradation `failed`；corruption 报告 `attempted=2/completed=1/failed=1/continued=1/retrievable=1`。
- `./.venv/bin/pytest -q tests/test_task7m_reset.py tests/test_task7_measurement_repair.py tests/evaluation/test_task4_reset_readiness.py tests/evaluation/test_task4r1_round5_final_red.py tests/evaluation/test_automatic_memory_end_to_end.py tests/performance/test_automatic_memory_100k.py --tb=short`：`145 passed, 2 failed, 1 skipped, 1 warning`。失败为历史 `test_real_quality_gate_reports_measured_result` 和 `test_real_promotion_uses_opaque_memory_ids_and_scans_all_temporary_sqlite_values`，仍要求旧的非空 `evaluation_report`/Production 数字 0 合同。
- 独立 scale loader 探针：构造 `run_id=forged-run`、伪造 fixture hashes、功能 readiness 全 ready（Production 为 `not_measured`）、`measured_quality=PASS` 且 MCP `100/100`、baseline `ready/1`，不提供 import/qdrant/corruption/promotion/gateway 细节；`readiness_from_envelope()` 返回 `scale_ready=True`，即 `FORGED_ACCEPTED`。
- `./.venv/bin/python -m compileall -q src tests`：PASS。
- `./.venv/bin/python scripts/check_acceptance_sync.py`：PASS（product-impacting files 0）。
- `./.venv/bin/python scripts/check_local_execution_handoff.py`：PASS。
- `git diff --check`：PASS；`git ls-remote origin refs/heads/codex/phase1-automatic-memory` 与 GitHub API 均复读远程 HEAD `28bdec3ddab4aba239d38e687dda57a7ea519805`。
- 未运行 100k、release、Artifact、live 8766/8767、Production/Vault 或真实主人数据；未修改产品代码、测试或权威文档。

## Critical findings

### C1 — scale loader 可接受缺少真实组成证据的伪造 READY envelope

位置：`src/automatic_memory/scale_benchmark.py:18-92`。

loader 只要求非空 `run_id`/fixture hashes、顶层功能/阶段状态、`measured_quality.status=PASS`、MCP 计数 `100/100` 和 baseline `ready`；对 `import_audit`、`promotion_provenance`、`gateway_selection`、Qdrant degradation、corruption isolation 等 readiness 为 `ready` 时并不要求对应 detail 存在，也不校验 detail 计数与 readiness 的一致性。它同样不验证 run identity 是否由当前 fixture/code 组成，或 fixture hashes 是否是当前冻结输入。

独立探针已经在没有任何这些细节的情况下得到 `scale_ready=True`。因此一个旧文件、手写文件或字段互相矛盾的 envelope 仍可进入 `ensure_4r2_ready_for_scale()` 并构造 100k scale 环境，直接违反“inconsistent/FAIL/NOT_EVALUATED 均 BLOCKED”。这是规模准入的 Critical 阻断。

### C2 — corruption isolation 的 `ready` 不包含规定的 Gateway/lexical 可检索终态

位置：`src/automatic_memory/quality_degradation.py:159-243`。

该实现已经走了授权来源、正式 scan admission、SQLite queue、worker 和 Work Fact，
但 `retrievable` 仅由 `bool(valid_messages)`（第 228–231 行）决定，只证明
read-model 中存在有效来源消息；没有调用正式 lexical/Hybrid/Gateway 检索，也没有
验证检索结果的来源身份、内容 hash 或权限过滤。因此 Gateway/lexical 链路完全失效
时仍可能报告 `status=ready`。此外终态条件使用 `completed >= 1`/`failed >= 1`，
没有要求 queue 的目标 job 集合恰好为两个且不存在额外 queued/running/unknown，
也没有断言损坏来源没有产生结构化消息。该证据不足以满足规定的“scan → durable
queue claim/worker → Work Fact → read-model → lexical/Gateway retrieval”全链路。

## Important findings

### I1 — Context baseline 在 NOT_MEASURED 时仍发布可被误读的数值 0

位置：`src/automatic_memory/quality_gate.py:905-910, 987-993, 1026-1030`。

本次运行有问题无选择前候选，正确地将 readiness/context baseline 标为
`not_measured`，但 envelope 的 `measured_quality` 仍写入
`baseline_context_chars=0`、`context_reduction=0.0`。这没有保持“不可用只能是
NOT_MEASURED、不能以 0 表示测量结果”的严格语义，并且下游若读取 measured_quality
而非 readiness 可能把 0 当作可比较的实测值。应使用 nullable/status 分离并在没有
完整 pre-bound payload 时不发布 reduction 数值。

### I2 — promotion/duplicate 证据仍不足以关闭上次的产品结果门禁

位置：`src/automatic_memory/quality_gate.py:619-704, 832-856`。

`_promote_fixtures()` 仍由 runner 以 `risk != high and authority == owner-confirmed`
重建 eligibility；它没有按 `memory_kind`、Core/protected、assistant-only、authority
conflict 等冻结类别让产品 outcome 逐类决定。当前类别输出只有 conflict/high-risk/
low-risk user，没有完整记录每类的 expected/actual/pending/rejected/error 与错误
晋级数量。重复数虽读取 projection，但没有把 message link、promotion audit、
missing/extra/duplicate 的完整产品结果汇入统一门禁。故 `promotion_provenance=ready`
不能证明 protected/Core 错误晋级为 0，也不能关闭此前 I2。

### I3 — 历史直接调用方仍未迁移，当前直接回归不全绿

`test_automatic_memory_end_to_end.py` 的两个直接测试仍要求旧的
`evaluation_report is not None` 与 `production_pollution == 0`，而当前 Task7M 合同
明确 Production 为 nullable/`NOT_MEASURED`、实测失败不生成冻结 report。无论最终选择
是迁移测试合同还是明确 quarantine，都必须让当前直接回归的预期与权威文档一致；
不能以新 focused `131 passed` 取代这两个真实失败，也不能把它们静默 skip。

## 通过与未发现问题

- `measure_mcp_parity()` 对空包返回 `retrieval_empty`，对身份/顶层 schema 不一致返回 `schema_mismatch`；runner readiness 使用严格 `successes == attempts == 100`，本次实测为 `0/100` 且为 failed，没有被伪报通过。
- `observe_candidates()` 与正式 `build()` 共用 `_collect_sections()`；本次没有发现单独的 ranking/filter 实现。由于本次所有问题没有完整候选，baseline 仍然不可用，不能据此声称缩减率。
- corruption 的两个 source、scan、queue 与 Work Fact 终态确实来自临时持久存储；本次输出 `queue_status_counts={'completed': 1, 'failed': 1}`，没有把该场景静态写成 `2/1`。
- 未发现本轮重新引入旧的 scorer 吞异常或 expectation-blind query 改写；未知 evidence 会阻止 runner 完成。

## 最小后续边界

仍然只允许一个 bounded measurement repair，不允许 retrieval/ranking/model/UI 或真实数据改动：

1. scale loader 必须要求每个 `ready` functional field 的对应 detail、真实计数、实测 verdict、fixture hash 与 run identity 全部存在且一致；任何缺失、矛盾、FAIL 或 NOT_MEASURED 一律阻断。
2. corruption 必须从持久 queue/Work/Read Model 终态读取恰好两个目标任务，并用正式 lexical/Hybrid/Gateway 查询确认有效源可检索、损坏源无泄漏；不能只看 message 行。
3. baseline unavailable 时所有 baseline/reduction 数值使用 nullable 并保持 `NOT_MEASURED`，不得发布 0 作为测量值。
4. 迁移或明确隔离两个历史直接调用方，保持拒绝测试语义，不删除/降低断言。
5. 将 quality_gate 收敛为薄编排，保留 `quality_degradation`/`scale_benchmark` 单一实现边界，并把 promotion/duplicate 产品 outcome 完整接入。

在新的独立审查达到 Critical=0、Important=0 且质量门禁仍诚实反映当前失败之前，
不得授权诊断、100k、release、Artifact 或 Task8。

