# Task 7N Combined Independent Review — N1/N2/N3

日期：2026-08-28（Asia/Shanghai）
审查工作树：/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory
审查 HEAD：43665b4c8b2bf5dc03b301b63c0ec096b4e8c0c2
审查基线：1cc785d3
关键实现：0ddb70b、eca289e、21e4db9

## 结论

Spec Compliance: FAIL
Task Quality: NEEDS_FIXES
Critical: 2
Important: 2
Minor: 1
Disposition: FAIL / NO_DIAGNOSTIC

本轮没有修改产品代码、测试或权威文档；仅新增本审查报告。N2 的真实 corruption
流程、MCP fail-closed 比较、选择前 baseline seam 与 runner 失败封装有实质收口，
但 N1 的 scale admission 仍不能接收真实 runner 输出，且 N3 的 automatic_activation
0/93 并不是当前产品合同下的有效质量失败。因此不能授权下一轮
retrieval/structured-evidence 诊断、100k 或 release。

## 独立验证

### Focused 矩阵

命令：
./.venv/bin/pytest -q tests/test_task7n1_scale_admission.py tests/test_task7n2_corruption_retrieval.py tests/test_task7n3_promotion_thin.py tests/test_task7m_reset.py tests/test_task7_measurement_repair.py tests/evaluation/test_task4_reset_readiness.py tests/evaluation/test_task4r1_round5_final_red.py tests/evaluation/test_automatic_memory_end_to_end.py tests/performance/test_automatic_memory_100k.py --tb=short

结果：156 passed, 1 skipped, 1 warning。

scale 对抗子集和完整一致测试 envelope callback：
3 passed。缺 detail、旧 hash/run、FAIL、bool、NaN、零 baseline 均为
BLOCKED_4R2_REQUIRED；完整自洽测试 envelope 可调用两个 callback。

### Task4 reset / Task7 direct regression

命令：
./.venv/bin/pytest -q tests/test_task4_reset_ingestion_order.py tests/test_task4_reset_promotion_transaction.py tests/evaluation/test_task4_reset_import_audit.py tests/evaluation/test_task4_reset_readiness.py tests/evaluation/test_task4_reset_runner.py tests/evaluation/test_task4_reset_section_identity.py tests/evaluation/test_task4r1_round5_final_red.py tests/evaluation/test_task4r1_takeover_red.py --tb=short

结果：284 passed, 1 failed, 1 warning。失败：
tests/evaluation/test_task4_reset_runner.py::test_runner_restores_readiness_enums_before_finalizing_envelope。
它仍硬断言 mcp_parity/context_baseline 为 READY；当前真实质量运行分别是
0/100 和 NOT_MEASURED。

### 真实质量 CLI（一次；未运行 100k/release）

命令：
./.venv/bin/python scripts/automatic_memory_quality_gate.py --output output/validation/task7n-review-20260828/quality.json

退出码：1。结果保持诚实：functional_status=FAIL、phase_status=FAIL、事实
0/106、引用 0/106、严格 MCP 0/100、context baseline NOT_MEASURED、
corruption attempted=2/completed=1/failed=1/continued=1，production 为 null。
没有将失败或不可用证据改写为 PASS/0。

### 其他门禁与远程复读

compileall PASS
check_acceptance_sync PASS
check_local_execution_handoff PASS
git ls-remote 与 GitHub API 均复读远程 HEAD 43665b4c8b2bf5dc03b301b63c0ec096b4e8c0c2。

git diff --check 1cc785d3..HEAD 未通过：N1、N2 报告日期行存在尾随空格。
审查前产品工作树 clean；本报告新增后只包含本报告文件。

## Critical findings

### C1 — scale loader 与真实 runner 发布 envelope 不兼容

位置：src/automatic_memory/scale_benchmark.py:75-178、
src/automatic_memory/quality_gate.py:909-945、991-1007。

N1 的测试 helper 手工补入 import_counts、role_order_counts、gateway_selection，
并使用 promotion_provenance.missing_links/extra_links、Qdrant lexical_ids/degraded_ids、
corruption terminal_tasks/bad_source_messages/bad_source_leaks。这些字段不是当前
真实 runner 最终发布的 QualityRunEnvelope.evidence_details 合同：

- 实际 CLI 输出没有顶层 import_counts、role_order_counts 或 gateway_selection，
  evidence_details 也没有 gateway_selection。
- 实际 promotion_provenance 只有 missing_projection/extra_projection 与
  missing_audit/extra_audit，没有 loader 强制要求的 missing_links/extra_links。
- 实际 semantic_degradation 只有 lexical_results/degraded_results，没有 loader
  强制要求的 lexical_ids/degraded_ids。
- 实际 corruption_isolation 没有 loader 强制要求的 terminal_tasks、
  bad_source_messages/bad_source_leaks。

对实际 CLI JSON 直接调用内部 validators：
promotion FAIL: promotion_provenance schema mismatch
gateway FAIL: missing evidence detail: gateway_selection
qdrant FAIL: qdrant_degradation schema mismatch
corruption FAIL: corruption_isolation schema mismatch

因此即使未来功能字段全 READY，当前发布格式也无法通过 readiness_from_envelope；
N1 的 callback 证明只是测试自定义 payload，不是真实 runner 输出可达。该问题是
scale/release 关键门禁阻断，不是当前 retrieval 失败的诊断理由。

最小修复边界：只统一 canonical QualityRunEnvelope.evidence_details 与
readiness_from_envelope 的字段合同，并增加由真实 run_quality_gate 发布 JSON 进入
loader 的集成测试；不改 retrieval/ranking/model、100k、release 或产品数据。

### C2 — N3 将全局自动晋级隔离误计为低风险自动晋级失败 0/93

位置：src/automatic_memory/quality_promotion.py:37-43,159-180、
src/automatic_memory/quality_gate.py:698-704、src/auto_review/promotion.py:113-120。

当前权威产品状态明确规定 automatic activation quarantine，只有显式主人审批才
能激活。正式 AutoMemoryPromotionService.evaluate() 在没有其他 policy reason 时
也追加 automatic_activation_quarantined，返回 pending_owner_review，不写
projection/link。独立复现一条 frozen low-risk owner-confirmed record：

expected_status=active（runner expected_status）
actual=pending_owner_review
reason=automatic_activation_quarantined
projection/link=none

本次真实 CLI 逐类结果：core/protected 12 pending、authority-conflict 20 pending、
low-risk-user 113 pending；runner 随后把 lifecycle active 的低风险 93 条作为
expected_status=active，发布 automatic_activation 0/93。这不是产品错误晋级，也
不是 owner-confirmation wiring 失败，而是当前安全隔离策略的预期结果。N3 的
expected_status 仍把低风险记录定义为 active，并且用该结果影响 candidate
confidence，因此该指标不能作为 retrieval 诊断输入。category_outcomes 也只记录
每类总数和实际状态，没有逐类记录冻结合同期望状态。

最小修复边界：将 quarantine 作为当前合同的 expected pending，或在未来
owner-approved recovery gate 前把 activation accuracy 标为 NOT_APPLICABLE/
NOT_MEASURED；保留正式 service 的 projection/link/audit 检查。不得通过自动
approve 恢复旧 121/125，也不得因此改 retrieval。

## Important findings

### I1 — promotion provenance 不能发现无 projection 的孤儿 link，且 rejected audit 未纳入

位置：src/automatic_memory/quality_promotion.py:197-215。

测量先读取 projection IDs，再只对这些 IDs 调用 read_model.memory_links。因此
pending/rejected/error candidate 没有 projection 但存在 message link 时，该 link
不会进入 memory_link_keys，validator 无法发现违反“非 active 不得有 link”。
同时 audit_ids 只收集 memory_promotion_decision、memory_promotion_owner_approved
和 memory_promotion_projection_error，没有 memory_promotion_owner_rejected；包含
真实 rejected outcome 的冻结样本会缺少 audit，不能完成正确 rejected 闭环。当前
frozen corpus 没有 rejected 行，所以 focused tests 未暴露。

最小修复边界：复用现有 read-model/state 查询取得本次 candidate 集合的全部 link
与所有终态 audit，按 candidate ID 动态计算 missing/extra/duplicate；不新增数据库、
promotion policy 或产品流程。

### I2 — 当前直接回归仍有一项与现行 measured-failure 合同冲突

tests/evaluation/test_task4_reset_runner.py::test_runner_restores_readiness_enums_before_finalizing_envelope
仍要求 MCP 与 context baseline 为 READY。真实 CLI 明确输出 MCP 0/100、baseline
NOT_MEASURED，所以命中的是旧断言而非产品异常。N3 报告的 156 passed 矩阵没有
包含该直接调用方，不能替代 284 passed/1 failed 的事实。

最小修复边界：只迁移该历史断言到现行 measured-failure/nullable baseline 合同，
保留“enum 恢复且非 INVALID_EVIDENCE”意图；不降低质量门禁断言。

## Non-blocking observations

### M1 — quality_gate 仍有未使用的旧编排 helper

src/automatic_memory/quality_gate.py 的 _all_messages() 与 _promote_fixtures()
在仓库内只有定义没有调用；后者还重复构造 promotion measurement、activation
计数和 outcome 统计。正式运行使用 _run_quality_gate_impl() 内另一份编排。
没有制造伪 PASS，但与“quality_gate 仅薄编排、无 dead duplicate implementation”
目标不一致。应在下一次只读清理窗口删除或改为唯一调用入口，兼容导出保持不变。

## 已通过/未发现

- A 对抗 probe 中缺 detail、数值矛盾、NaN、bool、旧 hash/run、FAIL 均拒绝；
  完整测试 envelope 可到达 callback；但不能抵消 C1。
- B N2 focused test 通过；两个授权 source 经 scan、queue、worker、Work Fact、
  read model，以 lexical 与 Gateway 复合身份交集检查有效源，坏源泄漏与额外/
  非终态任务会失败。真实 CLI 当前 retrieval 未达到 ready，没有硬编码成功。
- C 观察 seam 与 ContextPackBuilder._collect_sections() 共用正式过滤/排序路径；
  无候选时 baseline/reduction 为 nullable/NOT_MEASURED。
- D MCP 使用正式 create_mcp_server 注册路径，比较有序 identity、top-level schema
  和 used/max bounds；空包与 mismatch fail-closed，当前 0/100 为 FAILED。
- G runner-stage failure 发布新的脱敏 NOT_EVALUATED envelope；CLI cleanup
  inventory path-free 且 cleaned=true，production 保持 null。

## 最小后续边界

只授权一次 measurement-contract repair，不授权 retrieval/ranking/model/vector、
自动晋级恢复、100k、release、Artifact 或主人验收。修复完成后必须重新独立复核：

1. 真实 runner 发布 JSON 与 scale loader 使用同一 canonical detail schema，并由
   真实 runner 输出驱动一次完整一致 envelope loader/callback 测试。
2. activation quarantine 的期望口径与当前权威状态一致，逐类记录 expected/actual；
   pending/rejected/error 的 projection/link/audit 由持久查询动态证明。
3. 迁移历史 runner readiness 断言，确保 Task4 reset/Task7 direct regression 全绿。

在上述修复达到 Critical=0、Important=0，且质量 CLI 仍诚实显示当前 retrieval
失败之前，不得授权诊断、100k、release 或 Task8。
