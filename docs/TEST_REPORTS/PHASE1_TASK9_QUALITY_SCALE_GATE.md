# Phase 1 Task 9 — Quality and Scale Gate

日期：2026-08-26  
分支：`codex/phase1-automatic-memory`

## 结果

功能门禁：`FAIL`。真实链路执行 100/100 问题，导入完整率 100%，角色/顺序 100%，自动激活 98.4%，FastMCP 100%，ContextPack 压缩 91.56%，保护性误晋级 0，当前态过期泄漏 0，重复记录 0；但事实召回率 18.87%、引用准确率 18.87%，低于 90%/95% 阈值。按计划停止，不调整冻结评测或检索排序。

完整阶段门禁：`BLOCKED`，另受 owner review、重启恢复和 Mac M5 物理证据限制。

验证命令：`.venv/bin/python scripts/automatic_memory_quality_gate.py --output /tmp/automatic-memory-quality.json`；相关回归 57 passed。100k 压测必须在 release 阶段以 `LINGJI_RUN_100K=1` 单独运行，不能用默认 skip 代替。未接触 Production/Vault，临时 Acceptance 根已清理。

冻结输入：corpus `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94`；questions `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`。

当前阻塞是实际检索对冻结问题语义召回不足，而非测试造假或数据不完整。后续应单独审查 Task 3 检索链路，不得修改冻结评测以提高分数。

## 4R1 修复记录

初始 draft 明确标记为 `TDD_ORDER_NOT_MET`。本轮先运行真实 RED（`ModuleNotFoundError: quality_evidence`），再实现并达到 `46 passed, 1 warning`。新增证据审计与 protected-tree sentinel；删除原问题改写，评分异常 fail-closed，实测失败优先于物理证据 BLOCKED。MCP/degradation/100k 仍属于 4R2，未在本轮宣称通过。
