# Task 6L — Structured Evidence Lexical Wiring

日期：2026-08-28
工作树：`/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`
分支：`codex/phase1-automatic-memory`
基线：`81ffaec967cf65a55ea692161b3c16ecd7d6d6e0`
状态：`REPAIR_ROUND_1_IMPLEMENTED_FOCUSED_PASS / WAITING_FOR_INDEPENDENT_REVIEW`

产品/测试提交：`9ced68b` (`fix: index structured chat evidence for lexical retrieval`)

Repair Round 1 产品/测试提交：`5258ecef98e2b58dfb9c12af585a4fbd44c260dd`

## 范围与边界

本 bounded landing task 关闭 Task 6 审查确认的缺口：自动导入聊天已进入
structured source/conversation/message rows，但没有进入正式 lexical retrieval。
原始 raw 与 structured rows 仍是证据权威；`lingji_memory.db` 的
`memory_documents`/FTS 只是可重建检索投影。没有新增数据库、FTS、retriever、API、
向量设计或 promotion seam；没有写入 Obsidian、Core Memory、候选或主人数据。

## 实现

- `MemoryDatabase.sync_structured_evidence()` 从同库 structured rows 生成确定性的
  `memory_type=structured_evidence`、`memory_tier=evidence` 文档和 FTS chunks。
- 每条非空消息保留 source/conversation/message 内部及 external identity、role、
  sequence、content hash、raw reference、occurred time、privacy/project/scope；
  同源重扫幂等，跨 source 相同 external IDs 不折叠。
- source 非 active 时投影为 archived，current 检索隔离而 history 仍保留；空正文
  不物化。普通 Obsidian full/incremental rebuild 不会删除 structured evidence，且可
  由 `rebuild_structured_evidence()` 从 structured rows 恢复。
- Hybrid citation、ContextPack section 和正式 MCP `search_memory` 入口暴露同一
  message identity/citation；semantic/Qdrant 查询失败不影响 lexical 结果，并返回
  `semantic=degraded` / `reason_code=semantic_query_failed`。

### Repair Round 1（审查 `c69afdc`）

本轮严格限制为审查确认的 I1/I2，并顺手修复直接相关 M1/M2：

- `SourceRegistry` 的既有 lifecycle listener 将 StateDB 的 `authorized` 状态投影为
  structured source/evidence `active`，将 revoke、expired、unsupported、degraded 和
  未知状态 fail-closed 投影为 `archived`；`AutomaticMemoryRuntime.start()` 在重启时
  从持久 StateDB 列表重新投影。现有 `MemoryDatabase.revision` 在投影事务中递增，
  使 Hybrid 缓存不保留授权变更前的 current 结果。
- automatic Generic AI source scope 改由稳定授权 `source_id` 命名，不再包含 raw
  bytes digest；因此同一 source/conversation/message 更新 v1→v2 会在既有 read model
  与 evidence document 上幂等 upsert，same-bytes replay 不新增文档/FTS chunks，跨
  source identity 仍独立。raw snapshot hash 继续只作 provenance。
- Structured evidence projection 显式携带 `raw_reference`，Hybrid citation 和
  ContextPack citation/section 保留 message `role` 与 `sequence`。没有改变排名、
  embedding、vector 或 evaluator threshold。

## TDD 与验证

先新增真实 Generic AI History `ExtractionPipeline.execute()` RED：正式 Gateway lexical
结果为空（1 failed），未直接塞入 `memory_documents`。实现后：

| 验证 | 结果 |
|---|---|
| `tests/test_structured_evidence_lexical.py` | 7 passed, 1 existing Pydantic warning |
| Structured/extraction/retrieval/context/MCP matrix | 48 passed |
| Automatic-memory runtime/discovery/Obsidian/API/worker matrix | 24 passed |
| `python -m compileall` | PASS |
| `git diff --check` | PASS |
| `scripts/check_acceptance_sync.py` | PASS（changed files 10；product-impacting 6） |
| `scripts/check_local_execution_handoff.py` | PASS（LOCAL_EXECUTION_TASK remains IDLE） |

Qdrant outage focused evidence：正式 `MemoryGateway.search_memory` 在 semantic client
抛出 `RuntimeError` 时返回同一 `structured_evidence` lexical hit；diagnostics 为
`semantic=degraded`, `reason_code=semantic_query_failed`。同一 Gateway 的
`build_context_pack` 保留该 message citation；正式 MCP `search_memory` wrapper
返回同一 citation identity。没有启动 live 8766/8767 或 Artifact。

## 回归与限制

通过的回归覆盖 structured ingestion、Task 3 automatic runtime/discovery/Obsidian、
Task 5 provenance/context temporal filters、Task 6 packaged Qdrant helper 所依赖的
Hybrid fallback、MCP 与 promotion-compatible read paths。既有一次把 queue-empty
立即等同 Work Fact 完成的 timing-sensitive 测试曾在组合运行中失败，单独复跑通过；本
任务未改变 Work Fact 生命周期。

授权 registry 的 revoke 状态仍位于 `lingji_state.db`，structured source status 仍位于
`lingji_memory.db`；本轮仅通过现有 SourceRegistry lifecycle listener 做事务性
read-model 投影，没有新增状态存储或 API。listener 失败处理仍遵循既有 observer
运行时语义，需独立终审继续检查生产错误处置；未知状态本身 fail-closed。Task 6
H heartbeat、crash 最终矩阵和完整 Task 6 packaged acceptance 仍未完成。

## Repair Round 1 验证

| 验证 | 结果 |
|---|---|
| `tests/test_structured_evidence_lexical.py` | 9 passed, 1 warning |
| focused structured/extraction/retrieval/context matrix | 57 passed, 1 warning（修复前基线 55；新增 I1/I2 两项） |
| review candidate/source/temporal matrix | 46 passed, 2 warnings |
| runtime/discovery/Obsidian/worker matrix | 36 passed, 1 warning |
| formal Gateway/MCP/ContextPack/Obsidian/promotion matrix | 75 passed, 1 warning |
| packaged Qdrant lexical helper | 1 passed, 1 warning |
| compileall / diff-check | PASS |

I1 的真实 pipeline 测试证明 revoke/expired 后 Gateway、正式 MCP 与 ContextPack
current 结果为空，history/as_of 仍能读取同一 structured evidence，runtime 重启后
仍隔离。I2 证明 v1→v2 current 仅一份、旧内容不再命中、same-bytes replay added/updated
均为 0。Qdrant semantic client 抛错时正式 Gateway/ContextPack 仍返回 lexical
structured evidence，diagnostics 为 `semantic=degraded` / `semantic_query_failed`。
所有断言均使用 pytest 临时根；没有 live 8766/8767、Artifact、Production/Vault 或
主人数据。

## 修改与提交边界

产品/测试文件：`src/automatic_memory/runtime.py`、`src/extraction/adapters/generic_ai_history.py`、`src/retrieval/{memory_db.py,hybrid.py,context_pack.py}`、`src/sources/read_model.py`、`tests/test_structured_evidence_lexical.py`。
文档/证据文件：`docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`、`docs/PROJECT_STATUS.md`、`docs/MODULES/CODE_MAP.md`、`docs/TEST_REPORTS/PHASE1_AUTOMATION_UI_GATE.md`、本报告。

未执行 Artifact、release、live service、Production/Vault、owner acceptance；Task 6
总报告仍保持 `IN_PROGRESS / NOT_ACCEPTED`，等待 Task 6H heartbeat、crash 矩阵及完整
独立终审。
