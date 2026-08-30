# Phase 1 Task 9 — Quality and Scale Gate

<!-- 4R2 Task 3 current evidence is recorded before retained historical sections. -->

## 4R2 Task 3 — Frozen 100-question diagnostic (2026-08-30)

产品提交：`191ffd6`（`test: add frozen automatic memory oracle`）。本节对应的唯一 frozen
quality CLI 运行绑定基线 commit `3cb45340de5afe1d8451aed41eece940954c0db3`，不是产品提交
本身；禁止为追随产品提交而重跑 CLI。

### Fixture audit

| 输入 | 行数 | SHA-256 |
|---|---:|---|
| `tests/evaluation/fixtures/automatic_memory_corpus.jsonl` | 145 | `2a3ea2c14af9e1705a39673efb50826579f35b484f9d6c5442cb40f5f8f2347a` |
| `tests/evaluation/fixtures/automatic_memory_questions.jsonl` | 100 | `35000a5cc56de84ef3caa82114a1b9168e46c1d3b31fd89ba0f2a740ce6f9e31` |

补齐的仅是原 corpus 可证明的元数据：corpus `sequence`（每个独立 conversation 为 0）；问题的
`expected_source_ids`/`expected_message_ids`、`disallowed_source_ids`/`disallowed_message_ids`、
`expected_answer_atoms`、`negative_expectation`、`mcp_expectation=strict_parity` 与
`max_chars=4000`。既有字段的逐行对比为 145/145、100/100 unchanged；没有改变 query、原有
expected/forbidden fact、citation、类别、mode、阈值或事实内容。类别计数为
`stable_preference=20`、`current_project_decision=20`、`superseded_decision=15`、
`cross_session=10`、`authority_conflict=10`、`protected_candidate=10`、`scope_negative=5`、
`temporal_explanation=5`、`context_dedup=5`；mode 为 current 94、history 3、as_of 2、why 1。
问题共绑定 expected facts/atoms/citations 106/106/106，forbidden/disallowed identities 100/100。

### TDD and focused evidence

RED 首先执行了 brief 指定命令：`./.venv/bin/pytest ...`，本机无 `.venv`，shell 退出 127；
等价 `python3 -m pytest` 首次在新增 oracle 前以
`ModuleNotFoundError: src.automatic_memory.quality_oracle` collection failure 结束。实现后
focused oracle + end-to-end 为 `28 passed, 1 warning`；direct Task7 matrix 为
`236 passed, 1 warning`。`python3 -m compileall -q src tests`、`git diff --check`、
`python3 scripts/check_acceptance_sync.py` 与 `python3 scripts/check_local_execution_handoff.py`
均 PASS。

### 唯一 quality run

命令：

```text
python3 scripts/automatic_memory_quality_gate.py --output output/validation/task-3-frozen-quality.json
```

本次运行约 2026-08-30 17:05（Asia/Shanghai）结束，exit 1，artifact SHA-256 为
`80503dc3c27ffbc981636623334faedbe3b290df82961a4b3babab9e83a58e01`。运行身份为
`quality:2a3ea2c14af9e170:35000a5cc56de84e:3cb45340de5afe1d`。artifact 顶层
`question_diagnostics` 含 100 条不含私有文本的逐题记录；没有使用/生成 `question_results`。

| 指标 | 实测 | 门槛/状态 |
|---|---:|---|
| answered questions | 100 | required 100 |
| exact valid fact | 0/106 (0%) | >=90% FAIL |
| citation accuracy | 0/106 (0%) | >=95% FAIL |
| formal MCP parity | 0/100 (0%) | >=95% FAIL；100 次 `retrieval_empty` |
| forbidden false positives | 0/100 | <=5% PASS |
| duplicate records | 0 | 0 PASS |
| Gateway calls / empty | 100 / 100 | selection path READY, retrieval miss |
| context baseline | NOT_MEASURED | required measurement FAIL |
| Qdrant degradation | FAILED | semantic query failed；未改 retrieval |
| corruption isolation | FAILED | attempted 2, completed 1, failed 1, continued 1 |
| Production pollution | NOT_MEASURED (`null`) | required measurement FAIL |
| automatic Core writes | 0 active promotions；145 pending owner review | no automatic Core write observed |

逐题结果的 artifact bucket 统计为 `retrieval=95`、`provenance=95`，5 个显式 negative
题通过；正式 parity aggregate 另有 `mcp=100` 次失败（原因均 `retrieval_empty`）。产品提交后
新增的 parity-to-`mcp` 逐题映射只由 focused test 验证，严格遵守不重跑 quality CLI，因此不会
改写上述唯一 artifact 的历史 bucket 数字。

失败 question IDs（不含 query 或私有文本）：

```text
question-001, question-002, question-003, question-004, question-005,
question-006, question-007, question-008, question-009, question-010,
question-011, question-012, question-013, question-014, question-015,
question-016, question-017, question-018, question-019, question-020,
question-021, question-022, question-023, question-024, question-025,
question-026, question-027, question-028, question-029, question-030,
question-031, question-032, question-033, question-034, question-035,
question-036, question-037, question-038, question-039, question-040,
question-041, question-042, question-043, question-044, question-045,
question-046, question-047, question-048, question-049, question-050,
question-051, question-052, question-053, question-054, question-055,
question-056, question-057, question-058, question-059, question-060,
question-061, question-062, question-063, question-064, question-065,
question-066, question-067, question-068, question-069, question-070,
question-071, question-072, question-073, question-074, question-075,
question-076, question-077, question-078, question-079, question-080,
question-081, question-082, question-083, question-084, question-085,
question-091, question-092, question-093, question-094, question-095,
question-096, question-097, question-098, question-099, question-100
```

### Decision and cleanup

结论：`MEASURED_FAIL`，不得运行 100k/full/release、Artifact、live 8766/8767、Production/Vault
或 owner acceptance。Acceptance 临时根已由 runner 清理：`root_exists=false`、`cleaned=true`、
`remaining_count=0`、`remaining_bytes=0`、260 files/119 directories；正式 DataRoot/Vault 未接触。
仍需有界 repair plan 处理 retrieval/provenance、MCP parity、context baseline、Qdrant degradation
与 corruption isolation；本任务不修这些失败桶。唯一质量 artifact 保留至远程确认后按任务单清理。

日期：2026-08-26  
分支：`codex/phase1-automatic-memory`

## 结果（历史 / 已被 Task 4R-Reset Task 6 supersede，不是当前结论）

功能门禁：`FAIL`。真实链路执行 100/100 问题，导入完整率 100%，角色/顺序 100%，自动激活 98.4%，FastMCP 100%，ContextPack 压缩 91.56%，保护性误晋级 0，当前态过期泄漏 0，重复记录 0；但事实召回率 18.87%、引用准确率 18.87%，低于 90%/95% 阈值。按计划停止，不调整冻结评测或检索排序。

完整阶段门禁：`BLOCKED`，另受 owner review、重启恢复和 Mac M5 物理证据限制。

验证命令：`.venv/bin/python scripts/automatic_memory_quality_gate.py --output /tmp/automatic-memory-quality.json`；相关回归 57 passed。上述历史 runner 与尺度结论不再作为当前权威，4R2 readiness 前新 release 入口必须在生成 100k 命令前返回 `BLOCKED_4R2_REQUIRED`。未接触 Production/Vault，临时 Acceptance 根已清理。

冻结输入：corpus `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94`；questions `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`。

该节保留冻结质量评测的 raw 观察值；其测量组合随后被 Task7O 最终独立审查判定为
`BLOCKED_AT_MEASUREMENT_CAP / NO_DIAGNOSTIC`，因此当前 measurement 未接受。不得把 raw
facts/citations/MCP 数字当作最终产品 retrieval 诊断，也不得修改冻结评测、问题或阈值以提高分数。

## Task 7 真实冻结评测（2026-08-28，测量组合未接受）

本轮使用原始 100 个问题、未改写 query，通过正式 `src.mcp_server.create_mcp_server` 注册的 `build_context_pack` 工具逐题调用。证据来自持久化 read model、正式 Gateway/ContextPack 和正式 MCP 返回值。

实测：导入 145/145；角色/顺序 145/145；重复 0；自动激活 121/125（96.80%）；正式 MCP 100/100；Qdrant 真实适配器故障注入后状态为 degraded，但本题 lexical 结果为空，故降级证据不计通过；损坏源隔离 attempted=2、completed=1、failed=1、其他源继续=1；事实召回 0/106（0.00%）；引用准确率 0/106（0.00%）；实际上下文压缩 55.28%（baseline 65990、rendered 29512）。

这些是本次运行观察到的 raw 数字，不是已接受的产品诊断。后续 Task7O 最终独立审查发现
measurement contract 仍有 Critical/Important 缺口，故正式状态为
`BLOCKED_AT_MEASUREMENT_CAP / NO_DIAGNOSTIC`；不得把 raw facts/citations/MCP 失败归因
为最终 retrieval 产品边界，也不得进入诊断、100k scale、release、Artifact、live
8766/8767、Production/Vault、Mac 或主人验收。

Tasks 2–6 的自动化/UI automated acceptance 不因本质量测量阻塞而回退。

## Task 7 最终独立审查状态（2026-08-28）

报告：`.superpowers/sdd/2026-08-27-phase1-product-landing/task-7o-final-review.md`，提交
`ce9807adb8aa9f4997819105ff3f1a949d93105b`。Focused/direct 矩阵 `316 passed, 1 warning`，
compileall、acceptance sync、local handoff 与 diff-check 通过；审查发现 1 Critical、3
Important（C1/I1/I2/I3），结论为 `BLOCKED_AT_MEASUREMENT_CAP / NO_DIAGNOSTIC`。当前
measurement 未接受；下一步只能是一次有界 measurement-contract repair，修复并重新独立
审查到 Critical/Important 均为零前，不得运行 100k/release/Mac/owner 或进入 retrieval
诊断。Tasks 2–6 的自动化/UI 状态保持不变。

## 4R1 修复记录

初始 draft 明确标记为 `TDD_ORDER_NOT_MET`。本轮先运行真实 RED（`ModuleNotFoundError: quality_evidence`），再实现并达到 `46 passed, 1 warning`。新增证据审计与 protected-tree sentinel；删除原问题改写，评分异常 fail-closed，实测失败优先于物理证据 BLOCKED。MCP/degradation/100k 仍属于 4R2，未在本轮宣称通过。
