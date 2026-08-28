# Task 7 — Existing Quality and Scale Gate

日期：2026-08-28  
状态：`FAIL_MEASURED_QUALITY`

## 范围

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
