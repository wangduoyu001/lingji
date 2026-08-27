# Task 6L — Structured Evidence Lexical Wiring

日期：2026-08-28
工作树：`/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`
分支：`codex/phase1-automatic-memory`
基线：`81ffaec967cf65a55ea692161b3c16ecd7d6d6e0`
状态：`IMPLEMENTED_FOCUSED_PASS / WAITING_FOR_INDEPENDENT_REVIEW`

产品/测试提交：`9ced68b` (`fix: index structured chat evidence for lexical retrieval`)

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

授权 registry 的 revoke 状态位于 `lingji_state.db`，structured source status 位于
`lingji_memory.db`。本任务仅在 read-model source status 已更新时把 evidence archive
出 current retrieval；没有新增跨库状态桥接或扩展状态模型。因此真实授权撤销到
structured read-model 状态同步的实时闭环仍是残余限制，交由根代理/独立终审判断。

## 修改与提交边界

产品/测试文件：`src/extraction/structured_sink.py`、`src/retrieval/{memory_db.py,incremental_sync.py,index_coordinator.py,hybrid.py,context_pack.py}`、`tests/test_structured_evidence_lexical.py`。
文档/证据文件：`docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`、`docs/PROJECT_STATUS.md`、`docs/MODULES/CODE_MAP.md`、本报告。

未执行 Artifact、release、live service、Production/Vault、owner acceptance；Task 6
总报告仍保持 `IN_PROGRESS / NOT_ACCEPTED`，等待 Task 6H heartbeat、crash 矩阵及完整
独立终审。
