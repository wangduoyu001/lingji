# Task 7N3 — Promotion evidence and thin quality orchestration

日期：2026-08-28（Asia/Shanghai）
基线：`e5f2b0d1b2ed26f8255b33ccecf26b3a9675d437`
产品/测试提交：`75ee0c6c997326c2045b667c84e6a7707a45c558`

## 范围与结论

本轮只处理 Task7M 审查中的 promotion/duplicate evidence、两个历史直接回归和
quality runner 的职责拆分。不修改 retrieval/ranking、冻结题集、N1 scale admission、
N2 corruption isolation、UI、runtime 或真实数据。

结论：`IMPLEMENTED_FOCUSED_PASS / QUALITY_GATE_STILL_MEASURED_FAIL`。

## TDD 与行为证据

- RED：新 promotion/thin focused 首次收集为 `4 failed`：缺少
  `quality_promotion` 模块、fail-closed promotion provenance 合同和 scale helper 单一
  实现边界。
- GREEN：`tests/test_task7n3_promotion_thin.py`、Task7N1/N2、Task7M、measurement repair、
  Task4 reset/evaluation 直接回归及历史 end-to-end/100k compatibility 矩阵：
  `156 passed, 1 skipped, 1 warning`。
- 历史 end-to-end 的两个直接调用方已迁移到 `evaluation_report=None`、
  `production_pollution=null` 和 raw measured counters；opaque memory IDs、SQLite 全值
  扫描、敏感信息拒绝和 quarantined promotion 断言保留。
- 质量 CLI 执行一次后仍诚实返回 `functional_status=FAIL`；实测 raw counters 为事实
  `0/106`、引用 `0/106`、严格 MCP `0/100`、Context baseline `NOT_MEASURED`，自动晋级
  `0/93`。未将失败改写为通过，也未执行 100k。

## 结构收口

- `quality_promotion.py` 逐条调用正式 `AutoMemoryPromotionService`，按冻结 record 显式
  字段记录 category、expected/actual status、reason，并从持久 projection、message link
  和 promotion audit 复算 missing/extra/duplicate；protected、assistant-only、authority
  conflict 的错误 active、非 active projection/link 和重复/孤儿证据 fail closed。
- semantic degradation 已移入 `quality_degradation.py`；100k fixture/run 实现已移入
  `scale_benchmark.py`，`quality_gate.py` 仅保留兼容导出与正式 quality composition。
  quality_gate 从约 1409 行降至约 1129 行。

## 验证与边界

`compileall`、`git diff --check`、acceptance sync、local handoff 均通过；无 live
8766/8767、Artifact、release、Production/Vault、100k 或主人数据。当前质量门禁仍为
`FAIL_MEASURED_QUALITY`，Task7 不得进入诊断、规模、release 或 Task8，须由独立审查确认
promotion provenance 和 thin orchestration 后再决定下一步。
