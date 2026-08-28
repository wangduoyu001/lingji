# Phase 1 Task 9 — Quality and Scale Gate

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
