# Task 7N2 — Corruption isolation retrieval evidence

日期：2026-08-28（Asia/Shanghai）
基线：`5d3192c3c5b69aad7eec80ebe5fec9d68ebbf98f`

## 范围

本轮只收口 corruption isolation 的真实检索证据。测量复用正式
`SourceRegistry → SnapshotJobRunner → SQLiteExtractionQueue → ExtractionPipeline →
WorkStore → SourceReadModel → MemoryDatabase → HybridRetriever → MemoryGateway`
组合；未修改 scale admission、promotion、baseline、检索算法或 Desktop。

## RED / GREEN

- RED：旧函数不接受正式 Gateway，且以 `bool(valid_messages)` 代替真实检索证明。
- GREEN：新增 `CorruptionIsolationMeasurement`，发布两个授权 source、scan、job 的
  精确身份，队列终态精确 `completed=1/failed=1`，Work Fact 的 outcome/event 与
  scan/job 复合关联，适配器期望的 source/conversation/message/content hash，坏源
  read-model 泄漏计数，以及 lexical、Hybrid/Gateway 交集命中身份。
- Gateway 空结果、错误 source、坏源泄漏、额外目标队列 job、缺失/错误/重复 Work
  Fact 终态、坏源 read-model 行都会保持 `status=failed`，并返回稳定 reason code；
  测量 reason 不携带正文、lease、绝对路径或异常文本。

## 验证

- `./.venv/bin/pytest -q tests/test_task7n2_corruption_retrieval.py tests/test_task7m_reset.py tests/test_task7_measurement_repair.py tests/test_task7_quality_scale.py tests/evaluation/test_task4_reset_readiness.py --tb=short`：`125 passed`。
- `./.venv/bin/python -m compileall -q src tests`：PASS。
- `git diff --check`：PASS。
- 未运行 100 题 CLI、100k、release、Artifact、live 8766/8767、Production/Vault
  或真实主人数据。

## 交付边界

本报告只证明 corruption measurement 的自动化证据组合已具备；当前总体质量门禁
仍须以真实评测结果为准，不能据此宣称 Task 7、release 或 Phase 1 通过。
