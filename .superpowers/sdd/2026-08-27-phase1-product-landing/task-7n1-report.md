# Task 7N1 — Scale admission and nullable context baseline

日期：2026-08-28（Asia/Shanghai）  
产品/测试提交：`0ddb70b2451eb7224196bfefc4718ae8601aef7e`

## 范围

本轮只收口 4R2 scale admission 与 Context baseline 的证据语义；未修改
corruption isolation、promotion、retrieval、UI、100k 或 release。

## RED / GREEN

- RED：旧 loader 可接受缺少 import/promotion/Qdrant/corruption 细节且 run identity
  任意的 `FORGED_ACCEPTED` envelope；未测量 baseline 也可用 0 表示。
- GREEN：准入现在要求冻结 corpus/questions hash、code commit 与 run identity 一致，
  所有 functional READY 细节和动态计数齐全，MCP 严格 100/100，Qdrant lexical
  fallback identity、corruption 双终态、promotion links 与 context reduction 均可复算；
  缺失、矛盾、旧 hash/run、布尔数字、NaN 或额外字段统一 `BLOCKED_4R2_REQUIRED`。
- 未测量 baseline 在 runner 输出、envelope 和 round-trip 中保持 `null`，不会写成 0。

## 验证

`.venv/bin/pytest -q tests/test_task7m_reset.py tests/test_task7_measurement_repair.py
tests/test_task7_quality_scale.py tests/test_task7n1_scale_admission.py
tests/evaluation/test_task4_reset_readiness.py --tb=short`：`128 passed, 1 warning`。

`compileall`、`git diff --check` 通过。未运行 quality full CLI、100k、release、真实
数据、Artifact、live 8766/8767、Production/Vault 或主人验收；当前质量实测失败仍未被
改写为通过。
