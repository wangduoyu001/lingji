# Task 7M-Reset — Runtime Evidence Composition

日期：2026-08-28（Asia/Shanghai）
产品/测试提交：`b43401c2f241820e6ebf5d89b31dad8638224751`

## 范围

本轮只重置质量测量组合，不修改检索排序、过滤、冻结问题集、评测阈值、晋级政策、
产品 schema、UI 或真实 100k/release/Artifact。测量复用了正式 ContextPack、Gateway、
MCP、SourceRegistry、SnapshotJobRunner、SQLiteExtractionQueue、ExtractionPipeline、
WorkStore 与 StructuredReadModel。

## RED / GREEN

- RED：`tests/test_task7m_reset.py` 在旧实现上 `3 failed`，分别暴露 MCP 空包原因不明确、
  缺少完整 envelope 准入和 ContextPack 选择前观测 seam。
- GREEN：同一测试 `3 passed`；Task7/Task4R2 直接回归与 ContextPack 回归合计
  `131 passed, 1 skipped, 1 warning`。
- `compileall` 已通过。

## 已实现的测量边界

1. corruption isolation 改为真实双来源授权、正式 scan admission、queue claim、worker
   terminal 与 Work Fact/read-model 组合读取；本次 CLI 实测为
   `attempted=2, completed=1, failed=1, continued=1, retrievable=1`，并核对了
   `source_statuses`、`scan_statuses`、队列终态和 Work Fact 终态。
2. ContextPackBuilder 增加只读 `observe_candidates` seam；与最终 build 共用选择、范围和
   时间过滤，baseline 只接受该 seam 的未截断 payload；没有候选时为 `not_measured`。
3. MCP parity 比较完整有序 section identity、scope/lifecycle/mode/request 和 bounds；
   空包返回 `retrieval_empty`，身份或 schema 不一致返回 `schema_mismatch`，严格成功率未达
   100/100 时为 failed。
4. scale readiness 校验 run identity、fixture hashes、functional/phase verdict、持久
   readiness、measured quality、MCP 100/100、baseline payload 及详细证据一致性；scale
   只要求功能质量字段，Production sentinel 仍可为 nullable，owner/Mac/Windows 不参与
   scale admission。
5. 质量 runner 的 corruption 实现移至 `quality_degradation`；quality_gate 只调用该
   单一正式测量入口，不再保留旧的 callback 计数实现。

## 当前真实结果

命令：`./.venv/bin/python scripts/automatic_memory_quality_gate.py --output output/validation/automatic-memory-quality-task7m.json`

- `functional_status=FAIL`，这是当前检索事实召回/引用、Qdrant degradation、MCP 严格 parity
  与 baseline 未达到门槛的实测失败，不是测量器伪造的成功。
- MCP 严格结果为 `0/100`；Context baseline 为 `not_measured`；Production pollution
  未测量且为 `null`。
- 本轮未运行 100k、release、Artifact、live 8766/8767、Production/Vault 或主人验收。

## 未关闭项

Task7M 只完成测量组合的架构收口，尚未通过独立审查；当前不得进入 retrieval 诊断、
100k、release 或 Task8。需要新鲜独立审查确认 Critical/Important 均为 0 后，才可授权
一次有界的既有 retrieval/structured-evidence 绑定诊断。
