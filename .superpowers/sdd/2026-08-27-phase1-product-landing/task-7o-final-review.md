# Task 7O Final Independent Review — Measurement Contract Closure

日期：2026-08-28（Asia/Shanghai）
审查工作树：`/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`
审查 HEAD：`8d3dd937cedae188cee2417f54986bda38030d7a`
审查基线：`ce0a125448445b26252aadbb6aa4f0afad6ef720`

## 结论

Spec Compliance：`FAIL`
Task Quality：`NEEDS_FIXES`
Critical：1
Important：3
Disposition：`BLOCKED_AT_MEASUREMENT_CAP / NO_DIAGNOSTIC`

Task7O 的主要收口方向有效：真实 runner 已把 `evidence_details` 送入
`CanonicalFunctionalEvidence`，失败测量仍诚实发布为 `FAIL`，当前 automatic activation
仍 quarantine，N2 corruption 仍使用正式运行链，历史 Task4 断言已迁移，质量 CLI 未把失败
伪装成可进入规模门禁的成功结果。但本轮独立对抗发现 loader 对 duplicate wire views
和 promotion link 集合仍有可利用的证据盲区，且 activation/category 原因没有形成持久的
可审计合同。因此不能授权 retrieval diagnosis、100k、release、Artifact、真实数据或
Task8。

## 独立验证

### Focused 与 direct regression

命令：

```text
./.venv/bin/pytest -q \
  tests/test_task7o_contract_closure.py tests/test_task7m_reset.py \
  tests/test_task7_measurement_repair.py tests/test_task7_quality_scale.py \
  tests/test_task7n1_scale_admission.py tests/test_task7n2_corruption_retrieval.py \
  tests/test_task7n3_promotion_thin.py tests/test_task4_reset_ingestion_order.py \
  tests/test_task4_reset_promotion_transaction.py tests/evaluation/test_task4_reset_import_audit.py \
  tests/evaluation/test_task4_reset_readiness.py tests/evaluation/test_task4_reset_runner.py \
  tests/evaluation/test_task4_reset_section_identity.py \
  tests/evaluation/test_task4r1_round5_final_red.py tests/evaluation/test_task4r1_takeover_red.py \
  --tb=short
```

结果：`316 passed, 1 warning`。

Task7O 合同子集：`167 passed, 1 warning`。

### 真实质量 CLI

仅执行一次，未执行 100k、release、真实数据、Artifact、8766/8767 或主人验收：

```text
./.venv/bin/python scripts/automatic_memory_quality_gate.py \
  --output output/validation/task7o-final-review/quality.json
```

结果：退出码 `1`；机器结果为 `functional_status=FAIL`、`phase_status=FAIL`，事实
`0/106`、引用 `0/106`、严格 MCP `0/100`，Context baseline=`NOT_MEASURED`，
activation=`NOT_APPLICABLE`，production=`null`。随后直接调用
`readiness_from_envelope` 返回 `BLOCKED_4R2_REQUIRED`。

### 其他门禁

- `python -m compileall -q src tests`：PASS。
- `python3 scripts/check_acceptance_sync.py`：PASS。
- `python3 scripts/check_local_execution_handoff.py`：PASS（`LOCAL_EXECUTION_TASK` 仍 IDLE）。
- `git diff --check ce0a125448445b26252aadbb6aa4f0afad6ef720..HEAD`：PASS。
- `git ls-remote origin refs/heads/codex/phase1-automatic-memory` 与 GitHub API：均确认
  远程为 `8d3dd937cedae188cee2417f54986bda38030d7a`。
- 审查前工作树 clean；本报告是唯一新增文件。

## Critical findings

### C1 — loader 接受未知顶层字段并忽略 duplicate wire views / evidence detail 冲突

位置：`src/automatic_memory/quality_evidence.py:124-214`、
`src/automatic_memory/scale_benchmark.py:201-220`。

`readiness_from_envelope()` 通过 `CanonicalFunctionalEvidence.from_runner_payload()` 读取
artifact，但该入口只挑选已知字段，不拒绝未知顶层字段；同时当顶层 convenience projection
与 `evidence_details` 同时存在时，`pick()` 优先使用顶层值，不比较两份内容是否一致。
因此 loader 不是对唯一 wire artifact 的严格解析器，而是一个带兼容归一化和优先级覆盖的
解析器。

独立对抗（以现有 `_complete_payload()` 为可通过的基准）得到：

- 添加未知顶层 `unknown=1`，`readiness_from_envelope()` 仍返回 `scale_ready=True`；
- 顶层 `mcp_parity` 为成功值、`evidence_details.mcp_parity` 为失败/99 次，仍返回
  `scale_ready=True`；
- 顶层 `context_baseline` 为 1000/50/95%，`evidence_details.context_baseline` 为
  1000/500/50%，仍返回 `scale_ready=True`；
- 独立的 `CanonicalFunctionalEvidence.from_mapping()` 会拒绝未知字段，但实际 scale
  loader 走的是宽松的 `from_runner_payload()`，所以该测试不能证明落盘 artifact 的
  unknown/conflict 防护。

这允许手工或被篡改的 artifact 通过一份可接受的 projection 掩盖另一份矛盾证据，直接
破坏“unknown/missing/evidence detail conflict 必须 BLOCKED”的 4R2 门禁。最小修复只应
统一 loader 与 canonical wire contract：未知字段拒绝，duplicate views 要么不再发布，要么
逐字段等价校验；不得改 retrieval、ranking、model、scale 或 release。

## Important findings

### I1 — promotion measurement 过滤非候选 memory ID，仍无法发现所有 imported-message orphan link

位置：`src/automatic_memory/quality_promotion.py:200-219`。

实现虽然从每个 imported message 调用 `message_links()`，但随后只保留
`memory_id in candidate_memory_ids` 的 link。因而挂在任意非候选 memory ID 上的孤儿 link
会被静默丢弃，不会进入 `validate_promotion_measurement()` 的 extra/link mismatch 计算。

独立 fake read-model probe：一个 pending candidate、一个 imported message，以及该消息
对应的 `orphan-external` link；投影为空、候选 audit 完整。`measure_promotion_fixtures()`
仍返回 `status=ready`、`links_actual=0`。直接把同一 orphan link 交给
`validate_promotion_measurement()` 会正确失败，证明盲区来自 measurement 的过滤，而不是
验证器本身。

这违反“所有 imported messages link scan 能发现 orphan；pending/rejected/error 不得有
projection/link”。最小修复是扫描全部 imported-message links，再按本次 candidate 集合
计算 active/non-active/extra；不得读取 evaluator expected IDs 来补结果或新增 policy。

### I2 — promotion outcome 缺少非空 memory identity 校验

位置：`src/automatic_memory/quality_promotion.py:59-68, 95-126`。

`_ids()` 会删除空 memory ID，`validate_promotion_measurement()` 没有要求每个 outcome
拥有非空 identity。对单条
`{status: pending_owner_review, memory_id: ""}`、空 projection/audit/link 输入，独立
probe 得到 `status=ready`、`expected=1`。这使 malformed/missing candidate identity 可以
被报告为完整测量，违反 missing evidence 必须 fail-closed，也会让后续 projection/link
差异无法按稳定 ID 解释。

最小修复是逐条要求 memory ID 非空且唯一，并让 invalid outcome 进入明确 failed/blocked
结果；不改变 promotion policy。

### I3 — activation quarantine 只检查 expected status，未验证 actual status / reason / category

位置：`src/automatic_memory/quality_promotion.py:37-46, 236-242`。

`activation_measurement()` 只断言每条 `expected_status` 是
`pending_owner_review`，随后无条件返回 `not_applicable` 和三个 null 计数。独立 probe
中，以下所有输入均被接受为相同 NA：

- actual=`active`；
- actual=`pending_owner_review` 且无 reason；
- actual=`pending_owner_review` 且 reason=`other`；
- actual=`pending_owner_review` 且 reason=`automatic_activation_quarantined`。

当前真实 service 的正常结果包含 quarantine reason，但 measurement 没有在 artifact 中
保存逐条 outcomes/reason；`promotion_category_outcomes` 只有 expected/actual/状态计数。
所以报告无法独立证明每个 category 都是正确的 pending 状态、正确的 quarantine reason，
也无法在 service 回归为 active 或 reason 错误时阻断。最小修复是保留 NA accuracy/null
计数，同时逐条/逐 category 持久化并校验 expected、actual、reason；不得恢复 auto approve。

## 已通过及边界

- N2 corruption measurement 仍在正式 SourceRegistry → scan → queue → worker → Work Fact
  → read-model → Gateway 链路上；本轮没有发现把 bool 或硬编码成功改作真实检索证据的新问题。
- 当前真实失败优先：MCP 0/100、事实/引用 0/106、baseline 未测量仍进入 FAIL/blocked，
  没有授权从失败指标进入 retrieval diagnosis。
- Task4/Task7 直接回归本轮为全绿；未发现历史 readiness 断言重新污染当前合同。
- `quality_gate` 未发现 `_all_messages` 死 helper；`_promote_fixtures` 仅是委托到
  `quality_promotion.measure_promotion_fixtures()` 的兼容 shim，未发现第二套 promotion
  测量实现。
- 没有运行真实 100k、release、Artifact、生产 Vault、主人数据或主人验收。

## 最小后续边界

只允许一次有界的 measurement-contract repair，范围为 C1/I1/I2/I3 的 schema、观测与
测试；修复前禁止 retrieval/ranking/model/vector 诊断、自动晋级恢复、100k、release、
Artifact、真实数据与 Task8。修复后必须由全新独立代理重新运行本报告的全部 focused/direct
矩阵、真实质量 CLI 一次及同样的对抗 probe；只有 Critical=0、Important=0 且真实质量 CLI
仍诚实报告当前 retrieval failure，才能进入一次有界诊断。
