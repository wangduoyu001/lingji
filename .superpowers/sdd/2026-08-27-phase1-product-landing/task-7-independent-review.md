# Task 7 独立审查：质量与规模门禁

日期：2026-08-28（Asia/Shanghai）  
审查工作树：`/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`  
审查基线：`19e5824986c80145279847e0b637d69a7c2740e1`  
审查 HEAD：`621182004adbbe7f97067603b3fb10ed7354be04`

## 结论

```text
Spec Compliance: FAIL
Task Quality: NEEDS_FIXES
Critical: 4
Important: 5
Minor: 1
Disposition: MEASUREMENT_NOT_ACCEPTED / NO_DIAGNOSTIC_LUNA
```

本轮没有修改产品、测试或权威文档。质量结果的失败数字本身可复算，但用于
证明 4R2 readiness、生产无污染、损坏源隔离和规模入口的测量仪器仍有阻断缺陷，
因此不能进入单一诊断 Luna，也不能把 4R2 或 scale 标记为 READY。当前 `FAIL`
仍然是诚实的产品结果：事实召回和引用已经失败；本报告不把它改写为
`NOT_EVALUATED`。

## 可复核证据

- `./.venv/bin/pytest -q tests/test_task7_quality_scale.py tests/evaluation/test_automatic_memory_end_to_end.py tests/evaluation/test_task4_reset_readiness.py tests/evaluation/test_task4r1_round5_final_red.py --tb=short`：`142 passed, 1 warning`。
- `./.venv/bin/python scripts/automatic_memory_quality_gate.py --output output/validation/automatic-memory-quality.json`：退出码 `1`，`functional_status=FAIL`，刷新了正式输出。
- 复算值：导入 `145/145`，角色/顺序 `145/145`，重复 `0`，自动激活 `121/125`，MCP `100/100`，事实召回 `0/106`，引用 `0/106`，ContextPack `baseline=65990`、`rendered=29512`、缩减 `55.28%`。
- Qdrant 故障探针实际得到 `semantic=degraded`，但 lexical 与 degraded 均为 `0` 个结果，状态为 `failed`，没有被伪报成通过。
- `python -m compileall -q src tests scripts`、`git diff --check 19e5824986c80145279847e0b637d69a7c2740e1..HEAD`、`python scripts/check_acceptance_sync.py`、`python scripts/check_local_execution_handoff.py` 均通过；工作树在写本报告前 clean。
- 远程分支复读：`git ls-remote origin refs/heads/codex/phase1-automatic-memory` 返回 `621182004adbbe7f97067603b3fb10ed7354be04`；远程 Task7 报告可读。

## Critical findings

### C1 — 生产无污染被错误地作为数字 0 进入正式 EvaluationReport

位置：`src/automatic_memory/quality_gate.py:768-775, 946-985`。

本轮只在临时 Acceptance root 内创建 `protected-boundary`，报告也写明
`acceptance_protected_boundary_only`；这不是 Production/Vault 或第三方目录的
递归哨兵。因此它只能证明临时树未被修改，不能证明生产无写入。更严重的是调用
`evaluate_run()` 时把 `production_pollution` 硬编码为 `0`（约第 985 行），没有传入
前面实际计算的值。任何哨兵变化都可能让 readiness 与 EvaluationReport 分裂，且
生产污染门禁仍会显示 0。要求是不可用时 nullable/NOT_MEASURED，不能以临时树替代
生产边界。

### C2 — corruption isolation 不是两个授权来源的真实隔离测试，计数被硬编码

位置：`src/automatic_memory/quality_gate.py:553-582, 939-945`。

`_measure_corruption_isolation()` 只在已经导入的单个 fixture 旁写入一个无效文件，
直接执行它，然后固定返回 `attempted=2`、`completed=1`；没有创建或授权第二个
有效来源，也没有读取第二个来源的真实成功/失败 Work/queue 结果。唯一动态依据是
异常和原来那批 145 行是否仍存在。因此当前报告的
`attempted=2, completed=1, other_source_completed=1` 不是两个来源的测量，不能
证明“一个源损坏时另一个授权源仍继续并可检索”。这可以在产品不满足隔离时仍制造
`ready`。

### C3 — ContextPack baseline 不是完整相关会话的未压缩真实 payload

位置：`src/automatic_memory/quality_gate.py:883-916`，以及
`src/retrieval/context_pack.py:72-140, 326-343`。

runner 先调用正式 Gateway 的 `build_context_pack(max_chars=4000)`；该构建器已经
筛选、排序并在 `render_markdown()` 中按 4000 字符截断/修改 sections。随后 runner
从这个已经 bounded、已经选择过的 pack 删除 `markdown`，再把剩余 JSON 长度当成
“未压缩 baseline”。这不是每道原问题对应的完整相关会话，也不是选择前的真实
payload；因此 `baseline=65990` 与 `55.28%` 不能作为计划要求的 baseline，且可能
夸大缩减率。测量必须在正式检索结果选择前取得完整相关会话，另行计算最终 pack。

### C4 — scale/release 入口是不可达的，功能门禁通过后仍无法运行 100k

位置：`src/automatic_memory/quality_gate.py:1267-1275`、
`scripts/automatic_memory_quality_gate.py:36-46`。

`run_100k_benchmark()` 内部总是构造所有 functional 字段为 `NOT_MEASURED` 的
`QualityEvidenceReadiness`，随后立即调用 `ensure_4r2_ready_for_scale()`，所以该
函数没有任何能接收已测 readiness 的成功路径。PowerShell release 入口调用
`scripts/automatic_memory_quality_gate.py --check-4r2`，CLI 又固定传入
`run_release_preflight(None)`，同样始终阻断。Task7 当前因质量失败而不运行 100k
是符合停止规则的；但这条死路径意味着即使将来质量通过，也不能执行要求的 scale
验收。该阻断必须在任何 READY/diagnostic 或 release 声明前解决。

## Important findings

### I1 — MCP parity 只比较选中 fact/citation，不是完整 Gateway/FastMCP 身份与边界 parity

位置：`src/automatic_memory/quality_gate.py:918-931`。

runner 通过正式 `src.mcp_server.create_mcp_server()` 注册工具，调用路径本身是
真实的；但成功条件只比较 `SelectedEvidence.fact_ids` 和 `citation_ids`，没有比较
Gateway/MCP 的完整 ordered sections、source/conversation/message/content hash、
memory identity、scope、lifecycle、query mode、`max_chars` 和 `used_chars` 的
同一性。并且两次调用共享同一个 Gateway，100/100 主要证明同一实现被调用，不能
独立证明工具返回完整身份与权限边界 parity。

### I2 — duplicate_records 永远不含 memory duplicates，activation eligibility 由 runner 自己重建

位置：`src/automatic_memory/quality_evidence.py:759-764`、
`src/automatic_memory/quality_gate.py:665-712, 975-980`。

`StableDuplicateSummary.memory_records` 固定为 `0`，最终 `duplicate_records` 只取
source/conversation/message audit；派生 memory projection 的实际重复没有进入门禁。
同时 `_promote_fixtures()` 用 `record.risk != high and record.authority ==
owner-confirmed` 自己决定 eligible，再以 active 数量计算 `121/125`，没有逐项记录
产品 promotion decision/outcome（protected/Core/high-risk/assistant-only）。这两处都
可能在真实产品重复或错误晋级时报告 0/通过。

### I3 — 100k fixture 默认 seed 与冻结计划不一致，且测试没有稳定重生成 hash/真实峰值采样

位置：`src/automatic_memory/quality_gate.py:1173-1227, 1336-1370`、
`tests/test_task7_quality_scale.py:63-74`。

计划要求默认 `seed=41041`、第二次生成同 seed 的 SHA 一致、实际 peak RSS 或明确的
resident-message 采样；实现默认 `seed=20260826`，测试只检查单次文件的数量和存在
hash，`peak_message_count` 只是导入总量而非峰值采样（虽标为 measured）。本轮 100k
没有执行，故不能把这些缺口改写成当前运行失败，但它们阻断未来 scale 证据。

### I4 — quality_gate.py 已达 1420 行，承担第二套 fixture/import/degradation/scale/scoring 编排

本轮新增约 454 行，仍把 `_history_fixture`、导入/晋级编排、MCP 解析、降级注入、
corruption 计数、baseline/scoring、100k fixture/benchmark 全放在一个模块；计划要求
的 `quality_degradation.py`、`scale_benchmark.py` 未建立。它不是简单的薄编排，增加了
与正式产品路径并行的判定实现，正是上述 hardcode 与 parity 缺口的来源。该质量结构
问题在当前召回失败诊断前必须先收敛，否则后续数字不具备长期可维护的可信度。

### I5 — 成功质量运行没有把实际 Acceptance cleanup inventory 保留下来

`run_quality_gate()` 返回的成功 `QualityRunEnvelope.cleanup_inventory` 默认为空；
临时 root 由 context manager 删除，CLI 只调用 `verify_acceptance_cleanup()`，却没有
把清理前后实际库存写入发布 envelope。公开结果因此无法复核“本轮实际清理了什么”，
与计划要求的 cleanup inventory 不一致。该项不改变本轮 FAIL 数字，但阻断完整证据链。

## 历史 reset 测试修改审查

`62a769d` 将 `run_release_preflight()` 在 `scale=NOT_MEASURED` 时的旧阻断断言改为
允许执行，并把 `test_round5_report_keeps_unmeasured_4r2_fields_explicit` 的预期改为
Task7 的 measured `ready/FAIL` 语义。结合 Task7 明确重新接管 4R2、并且当前质量报告
真实为 `FAIL_MEASURED_QUALITY`，这是有文档依据的状态迁移，不是删除测试或把失败改
skip；其余“functional field 未测时不得调用 gate”的拒绝测试仍在回归中通过。因此本项
不单独列为缺陷。但后续应把历史测试重命名或增加明确的 Task7 测试，避免旧
`test_task4r1_round5_final_red.py` 名称继续暗示它仍验证旧拒绝合同。

## 其他判定

- 原始 100 问 hash 与问题正文未被修改；runner 没有重写 query，也没有从 expected/
  forbidden 字段选题。`score_question()` 对 unknown/forbidden/extra/citation mismatch
  fail-closed，当前没有发现吞异常把这些变成 miss 的回归。
- import audit 使用持久化复合 external key、ingestion ordinal、role、sequence、
  timestamp 和 content hash，当前 `145/145` 不是从输入 map 自算；这部分证据可信。
- Qdrant 故障使用正式 `QdrantSemanticProvider` 加 Acceptance-only client 注入，
  `semantic=degraded` 且 lexical 结果为空时诚实为 `failed`；问题是产品探针没有
  lexical 可召回材料，不应把它算作 outage fallback PASS。
- `ProtectedTreeSentinel` 本身是递归、内容 hash、模式和 TOCTOU 感知的；当前问题是
  它只测临时 protected boundary，不能替代生产/Vault sentinel。
- 当前状态 `functional_status=FAIL`、`phase_status=FAIL`，未运行 100k/release/
  Artifact/live/Production/Vault/owner acceptance；不允许进入 Task8 或单一诊断 Luna。

## 有界后续修复要求（供主代理调度）

只授权一个“Task7 measurement repair”任务，不授权 retrieval/ranking/model 或
100k/release/owner 工作。它必须先补 RED，再最小修复：

1. 将生产哨兵不可用表示为 nullable/NOT_MEASURED，并确保 evaluator 不接收硬编码
   `production_pollution=0`；Acceptance boundary 只能作为单独的测试隔离证明。
2. 用两个明确授权的临时来源做真实损坏隔离，持久化读取两源的 attempted/completed/
   failed/continued/retrievable 计数。
3. 从正式检索/会话结果的选择前 payload 计算 baseline，并逐项记录 MCP 完整身份、
   bounds、scope 与 lifecycle parity。
4. 让 scale 接收经过质量门禁的 readiness，修复真实 release dispatch；固定 seed、
   第二次生成 hash、实际峰值/样本和 cleanup inventory。质量失败期间仍不得运行 100k。
5. 把 degradation/scale 测量拆成薄模块，保留原始问题和测量失败，禁止硬编码成功。

完成上述测量修复并由全新独立审查达到 Critical=0、Important=0 后，才能授权一次
“已有 retrieval/structured-evidence 绑定失败的诊断任务”。

