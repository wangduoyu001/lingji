# Task 7 Measurement Repair 独立审查

日期：2026-08-28（Asia/Shanghai）  
审查工作树：`/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`  
审查基线：`40ccc89c553d3c03d37549cb91409b9f785ddb0a`  
审查提交：`f868b4f`、`03a0845`、`e5770a5`  
当前 HEAD：`e5770a59ab27dc3692d6ce97e1b527cf042fbe0c`

## 结论

```text
Spec Compliance: FAIL
Task Quality: NEEDS_FIXES
Critical: 4
Important: 3
Minor: 0
Disposition: MEASUREMENT_NOT_ACCEPTED / NO_DIAGNOSTIC_LUNA
```

本审查未修改产品、测试或权威文档；仅新增本报告。未运行 100k、release、Artifact、
Production/Vault、live 服务或主人验收。当前质量数字可以复算，但测量器仍可能把不可用
或错误的证据送入规模准入，因此不能进入 retrieval/structured-evidence 诊断，也不能
宣称 4R2 或 scale ready。

## 独立复算

- `./.venv/bin/python scripts/automatic_memory_quality_gate.py --output output/validation/automatic-memory-quality-review.json`：退出码 `1`，`functional_status=FAIL`、`phase_status=FAIL`；事实 `0/106`、引用 `0/106`、MCP 严格成功 `0/100`、baseline `0`、ContextPack `29512` 字符；corruption 报告 `attempted=2/completed=1/failed=1/continued=1/retrievable=1`；Production pollution 为 `null`。
- `./.venv/bin/python -m pytest -q tests/test_task7_measurement_repair.py tests/test_task7_quality_scale.py tests/test_automatic_memory_acceptance_gate.py tests/evaluation/test_task4_reset_readiness.py --tb=short`：`163 passed`。
- 直接回归 `tests/evaluation/test_task4_reset_readiness.py tests/evaluation/test_task4r1_round5_final_red.py tests/performance/test_automatic_memory_100k.py`：`116 passed, 2 failed, 1 skipped`。两个失败均来自未同步的新合同：历史测试仍要求 `evaluation_report` 非空或 `production_pollution == 0`，而当前实现明确使用 nullable Production evidence 并不生成冻结 report。
- `compileall`、`git diff --check 40ccc89..HEAD`、`check_acceptance_sync.py`、`check_local_execution_handoff.py`：均 PASS；工作树在报告提交前 clean。`git ls-remote` 与 GitHub API 均复读当前远程 SHA `e5770a59ab27dc3692d6ce97e1b527cf042fbe0c`。

## Critical findings

### C1 — corruption isolation 没有走 durable queue / Work Fact，ready 不是规定的生产组合证据

位置：`src/automatic_memory/quality_gate.py::_measure_corruption_isolation`。

该函数确实用 `SourceRegistry` 注册两个不同的授权来源，并使用真实 `ExtractionPipeline`
和 `SourceReadModel`。但它随后直接调用 `pipeline.execute(...)`；该 API 是同步下游执行，
不会创建或消费 `SQLiteExtractionQueue` job，也不会创建/检查 `WorkStore` 的 WorkItem、
ExecutionEvent 或 Outcome。`valid_rows > 0` 就增加 `completed/continued/retrievable`，
没有从持久 queue/work/read-model 三者的终态统计计数。故当前 `ready` 只能证明一次同步
函数调用和 read model 有行，不能证明“损坏源失败而另一个授权源继续”的规定运行时边界；
测量器可在队列或 Work Fact 链损坏时仍报告 ready。

### C2 — selection-before-bound baseline 不可用时仍写入 `context_baseline=ready`

位置：`src/automatic_memory/quality_gate.py:849-850, 970-973, 1092, 1122-1126`。

运行中 100 道问题都没有完整 pre-bound payload，`baseline_available` 被设为 `False`，
`baseline_context_chars` 为 `0`，但该变量没有被使用；readiness 仍按
`gateway_calls_completed == 100` 设置 `context_baseline=READY`，公开 evidence 状态也写
为 `ready`。当前测量结果中的 baseline 数值为 `0`、reduction 为 `0.0`，报告文字却说
baseline `NOT_MEASURED`。这违反“缺少完整选择前 payload 必须 NOT_MEASURED”，并且未来
Production sentinel 或其他字段变为 ready 时，scale admission 可能把未测 baseline 当作
已测证据。

### C3 — strict MCP parity 失败仍被标为 readiness ready，且空 pack 没有明确失败原因

位置：`src/automatic_memory/quality_gate.py:1079,1121`、
`src/automatic_memory/quality_degradation.py:51-104`。

独立复算中正式 Gateway 和正式 `create_mcp_server` 均返回空 sections；严格 parity 结果
为 `0/100`，但 readiness 只检查 `mcp_attempts == 100`，因此写成 `mcp_parity=READY`。
`measure_mcp_parity` 对空 pack 返回 `ordered_identity_mismatch`，没有独立的
`empty_pack`/`retrieval_empty` 原因，导致产品检索为空与 parity 测量器无法比较被混在同一
个失败类型中。更重要的是，若其他 functional fields 通过，`functional_ready` 可以在
严格 MCP 成功率为 0 时成立。新增单测只用 synthetic section（带产品当前 section 不一定
存在的 `fact_id`/`citation_id`）和空 pack，不验证实际正式 section schema 的成功或 schema
错配分类。

### C4 — scale readiness 只信任持久 envelope 的字段值，不验证 envelope verdict/measurement

位置：`src/automatic_memory/scale_benchmark.py::readiness_from_envelope`、
`src/automatic_memory/quality_gate.py::load_quality_readiness`。

loader 只读取 `quality_evidence_readiness`，不校验持久 envelope 的
`functional_status`、`phase_status`、`evaluation_report`、严格 MCP 成功计数、baseline
状态、`measured_quality.status` 或 envelope 是否是本次真实发布的完整结果。独立探针构造
一个 `functional_status=FAIL`、`phase_status=FAIL`、`evaluation_report=null` 但所有
readiness 字段为 `ready` 的 JSON；`load_quality_readiness` 返回 `functional_ready=True`，
`ensure_4r2_ready_for_scale` 接受，输出 `scale admission ACCEPTED`。因此即使质量结果失败
或 envelope 被旧文件/不一致字段污染，`--check-4r2`/100k 仍可能被放行，不能算“从持久化
真实 envelope 可达”。当前本次真实 envelope 因 qdrant failed/production not_measured
仍被挡住，但准入缺陷本身必须先关闭。

## Important findings

### I1 — `quality_gate.py` 仍不是薄编排，新增模块没有成为唯一职责边界

`src/automatic_memory/quality_gate.py` 当前为 1523 行，仍同时包含 fixture 序列化、导入、
promotion 编排、Gateway/MCP 调用、degradation 注入、corruption 计数、baseline/scoring、
scale fixture 和 benchmark。`quality_degradation.py` 与 `scale_benchmark.py` 虽已新增，
但主 runner 仍保留上述第二套编排；`generate_100k_history` 与 `_validate_scale_fixture`
还保留 `return` 后的旧实现死代码。该结构继续制造 readiness 与真实计数分裂，不满足本轮
“薄编排、复用正式合同”的质量要求。

### I2 — activation/duplicate 门禁仍部分由 runner 自判，缺少逐项产品 outcome 证据

`_promote_fixtures` 以 `record.risk != "high" and record.authority == "owner-confirmed"`
自建 eligibility，再把实际 service 的 `active` 数量与该自建集合比较。它确实调用了正式
`AutoMemoryPromotionService`，也记录 `active/pending_owner_review` outcome；但没有按
Core/protected/high-risk/assistant-only/authority-conflict 等冻结类别逐项记录 expected
与 actual decision，也没有把 rejected/error/owner-review-required 的每类结果纳入门禁。当前
`promotion_outcomes` 仅为 `active=121, pending_owner_review=24`，不足以证明 protected
false promotion 和错误自动晋级为 0。`count_memory_projection_duplicates` 只核对派生
projection memory_id，未把完整 promotion audit（missing/extra/duplicate/link 状态）纳入
主 runner 的结果合同。

### I3 — 旧拒绝/历史质量测试未同步，直接回归不绿

`tests/evaluation/test_automatic_memory_end_to_end.py::test_real_quality_gate_reports_measured_result`
以及 `tests/evaluation/test_task4r1_round5_final_red.py` 的两个用例仍断言旧的
`evaluation_report is not None` 或 `production_pollution == 0`。这些断言与当前文档锁定的
Production nullable/`NOT_MEASURED` 语义冲突，但实现提交没有同步、重命名或明确 quarantine，
所以当前 direct regression 有真实失败。不能用“新 focused tests 全绿”替代这组直接调用方
的合同迁移，也不能把旧失败写成通过。

## 通过项

- Production/Vault 在本轮自动 runner 中已改为 nullable `null`，Acceptance protected tree
  被单独标记，不再硬编码为 Production pollution=0；`EvaluationReport` 在该证据不可用时
  不被伪造填充。
- import audit 使用持久复合 external key、顺序、角色、sequence、时间戳和 content hash；
  本次 `145/145` 不是从 map 长度自算。
- corruption 入口不再固定返回 `attempted=2` 的静态数字；两个授权 source ID 是实际注册
  结果，成功/失败数字来自各次调用（但 C1 仍指出调用层次不合格）。
- cleanup inventory 已在正常 cleanup 后发布文件/目录/字节和剩余数量，并在 cleanup
  failure path 生成 fail-closed envelope；该项本次未发现独立 Important。
- 100k fixture 默认 seed 已为 `41041`，生成过程检查 message ID/content hash 数量，测试
  同 seed 重生成 SHA 稳定；本审查遵守停止规则，没有运行 100k。

## 最小后续边界

当前不是 retrieval 诊断；仍是同一 bounded measurement repair 未完成。下一步只应授权
一次新的、有界 measurement repair（不改 retrieval/ranking/model/UI/产品数据）：

1. 让 corruption scenario 通过正式授权来源、持久 queue admission/worker、Work Fact
   outcome 和 read model 读取真实终态计数，验证好源可检索且坏源失败；
2. 将 `context_baseline` readiness 与实际 pre-bound payload 绑定，没有完整 seam 就写
   `NOT_MEASURED`；将 MCP readiness 与 strict successes/attempts 绑定，记录空 pack 与
   schema mismatch 的可区分原因，并以实际正式 sections 做 parity；
3. scale loader 必须验证 envelope 的成功/失败 verdict、readiness、measured-quality 和
   当前 run identity 一致后才放行；保留 100k 未测期间的阻断；
4. 把历史直接调用方迁移到当前 nullable/NOT_MEASURED 合同或明确 quarantine，并保持
   原始拒绝测试不被删除或弱化；
5. 把 runner 收敛为薄编排，删除死代码，继续使用现有产品 service/queue/Gateway/MCP。

在上述修复获得全新独立审查的 Critical=0、Important=0 之前，不允许进入单一
retrieval/structured-evidence 诊断，不允许运行 100k/release/Artifact/Task8。
