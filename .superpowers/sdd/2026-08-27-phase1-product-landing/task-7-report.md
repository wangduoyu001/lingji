# Task 7 — Existing Quality and Scale Gate

日期：2026-08-28
状态：`MEASUREMENT_REPAIR_COMPLETE / QUALITY_FAIL_NOT_ACCEPTED`

## Task7 Measurement Repair（本轮）

本轮修复了质量测量边界，不重写质量结果：新增 `quality_degradation.py` 与
`scale_benchmark.py`，并让 runner 使用选择前正式检索结果、MCP 完整身份/边界比较、
两个实际授权来源的损坏隔离计数、真实清理库存和持久 readiness 文件。Acceptance-only
保护树明确标记为隔离证据；本轮无法安全读取 Production/Vault，因此
`production_pollution=null`、生产哨兵为 `NOT_MEASURED`，不会伪造进入冻结
`EvaluationReport`。

修复后质量 CLI 仍诚实失败：原始 100 问执行 100/100，导入 145/145，自动激活
121/125；严格 MCP parity `0/100`，损坏隔离 `attempted=2, completed=1, failed=1,
continued=1, retrievable=1`；选择前 baseline 因正式检索没有完整相关会话而为
`NOT_MEASURED`；事实召回与引用仍为 `0/106`。状态为 `FAIL`，未执行 100k、release、
Artifact、Production/Vault 或主人验收。

TDD RED：新增测量契约首次收集失败 `ModuleNotFoundError: quality_degradation`；GREEN：
测量修复聚焦 `6 passed`，Task4R reset/readiness/runner/scale 及历史回归 `146 passed,
1 warning`，compileall 与 diff-check 通过。该报告只记录 measurement repair 完成，
不代表 Task7 quality accepted；须经独立审查 Critical/Important 均为 0 后，才允许一次
既有 retrieval/structured-evidence 绑定失败诊断。

## 范围

下方“结果”段为 measurement repair 前的历史记录，已被本报告后续修复段落 supersede，
不得作为当前 MCP/baseline/生产污染证据；冻结问题、质量失败与未执行 100k 的结论仍然保留。

本轮只运行冻结 corpus/questions 的既有质量门禁，未修改 retrieval、ranking、evaluator、promotion policy、runtime、UI 或数据模型。问题原文逐题执行，正式 MCP 通过 `src.mcp_server.create_mcp_server` 注册路径调用。

## 结果

- 导入：145/145；角色与顺序：145/145；重复：0。
- 自动激活：121/125（96.80%）。
- 正式 MCP：100/100，ContextPack 身份与边界校验通过。
- Qdrant 真实适配器故障注入：diagnostics 为 semantic degraded，但该探针问题没有 lexical 结果，因此降级证据不计通过。
- 单源损坏：attempted=2、completed=1、failed=1，其他源继续=1。
- 事实召回：0/106（0.00%），低于 90%。
- 引用准确率：0/106（0.00%），低于 95%。
- ContextPack：baseline=65990、rendered=29512，实际压缩 55.28%，低于 90%。

结论：正式结果为 `FAIL`。首个既有边界在 retrieval/structured-evidence 到冻结事实身份的召回绑定，引用随之失败；上下文压缩也未达到门槛。按照计划，停止产品修改，不运行 100k、release、Artifact、live 服务、Production/Vault 或主人验收。Task 8 不得开始。

## 验证

- `.venv/bin/pytest -q tests/test_task7_quality_scale.py tests/test_automatic_memory_acceptance_gate.py tests/test_00_task4_reset_validation_guard.py`：52 passed。
- `scripts/automatic_memory_quality_gate.py`：真实运行，退出码 1，发布 envelope `functional_status=FAIL`。
- 100k 未执行，因为冻结质量门禁已实测失败。
