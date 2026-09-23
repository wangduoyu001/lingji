# TEST REPORT — chunk 向量回填自动化 + MCP project_timeline 工具（CHUNK_BACKFILL_AUTOMATION_AND_PROJECT_TIMELINE）

- 日期：2026-09-23
- 分支/HEAD：`codex/owner-source-intake-mac-repair`（起草时 HEAD `c0728ff8`）
- 执行环境：macOS（darwin 25.5.0 arm64）；chunk 语义集合 `lingji_memory_production` 位于数据根 `qdrant/` 目录（非 `storage/qdrant`）
- 最终装机：sidecar SHA-256 前 8 位 `b08eb38a`（PyInstaller，182 个运行时文件），全量 codesign 重签通过
- 验收条目：`docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md` 2026-09-23 `CHUNK_BACKFILL_AUTOMATION`、`MCP_PROJECT_TIMELINE_AND_AI_ONBOARDING`
- 结论：**自动测试与 MCP 真机实测通过；chunk 集合 qwen3 全量重建进行中、待验收后回填 coverage 数字**。待主人最终确认。

## 背景与根因

1. **chunk 层缺口从无自动触发**：`/api/vector/coverage` 显示的 chunks 层缺口此前只有手动 `/api/observability/vectorize` 会补，自动回填只覆盖消息层，chunk 层缺口持续滞留。
2. **指纹守卫对消息层点致盲**：消息层 `VectorBackfill` 写入的 payload 缺失 `embedding_model` 字段，导致嵌入模型切换后的集合指纹守卫无法对消息层点做一致性判断。
3. **AI 每次各自整理项目时间线**：Codex、ZCode 等多个 AI 在同一项目上工作，需要项目背景/历史结论时没有一站式按主题聚合的时间线查询，只能逐条 search 或反复问主人。

## 变更内容

### 变更一：chunk 向量回填自动化

- `src/automatic_memory/runtime.py` 新增 `semantic_provider` 注入参数与 `_build_chunk_backfill`：drain 线程（`lingji-vector-backfill`）在既有消息层回填的同一 300s 预算循环里并跑 `ChunkVectorBackfill`（每轮 200 条，两层都归零才停）。
- `run_control_api.py` 组装时传入网关 `retriever.semantic_provider`（同进程共享 Qdrant 客户端池，不自建第二客户端，避免单进程客户端锁冲突）。
- `src/retrieval/vector_backfill.py` 消息层写入 payload 补记 `embedding_model`（embed 成功后 active_model 必已就绪），消除集合指纹守卫对消息层点的致盲。

### 变更二：MCP project_timeline 工具 + AI 引导

- `src/mcp_server.py` 新增第 22 个 MCP 工具 `project_timeline`：按主题关键词聚合蒸馏层（`distilled_knowledge`，按对话发生时间）与记忆检索（`search_memory`）结果，时间倒序归并，逐条标注来源（`source_id`/`kind`/`category`），token 受控（摘要截断 220/180 字符、`max_chars` 总预算默认 6000、`limit` 默认 20 上限 50）。聚合逻辑为纯函数，位于 `src/mcp/timeline.py`。
- `distillation.py` `list_entries` 条目补 `source_id` 字段（纯增量）。
- 主人需求落地：`~/.codex/AGENTS.md` 与 `~/.zcode/AGENTS.md` 新增「灵机记忆检索优先」节——需要项目背景/历史结论先 `search_memory(limit=5)`，检索不到再问主人，检索结果不复述全文，长期结论用 `propose_memory` 沉淀。

## 自动测试

| 套件 | 结果 |
| --- | --- |
| `tests/test_runtime_chunk_backfill_drain.py`（3 例：drain 经网关 provider 补齐且幂等 / 无网关 provider 行为不变 / 消息层 payload 记录模型名） | 3 passed |
| 相关既有套件：`test_vector_backfill`、`test_chunk_vector_backfill`、`test_automatic_memory_runtime_flow`、`test_vector_status_probe_fallback`、`test_embedding_status_probe` | 21 passed |
| `tests/test_mcp_project_timeline.py`（4 例：list_entries 带 source_id / 双源时间倒序归并与来源标注 / limit 与字符预算截断 / 摘要归一化截断） | 4 passed |
| MCP 层：`test_mcp_server`、`test_automatic_memory_mcp`、`test_codex_mcp_tools` | 14 passed |

## 真机验收记录（装机 sidecar `b08eb38a` 后，经 stdio 桥）

1. **MCP 工具清单**：`tools/list` 返回 22 个工具，含新增 `project_timeline`。
2. **时间线真实查询**：主题「嵌入模型」返回 6 条；主题「晋升管线」返回 18 条（含 1 条 distilled 条目，带对话来源 `LJ-SRC-…` 与 `key_points`；17 条 memory 条目带 `memory_id`），时间倒序正确。
3. **AI 引导**：`~/.codex/AGENTS.md` 与 `~/.zcode/AGENTS.md` 的「灵机记忆检索优先」节就位，随下次会话自然生效。
4. **chunk 回填自动化**：不点手动 vectorize，观察 `/api/vector/coverage` missing 自动收敛——**qwen3 全量重建进行中，待验收后回填数字**。

## 真机验收中发现的既有缺陷（处理中 / 待观察）

- **现象**：嵌入模型切换（bge-m3 → qwen3-embedding:0.6B，同为 1024 维）时，chunk 语义集合 `lingji_memory_production`（位于数据根 `qdrant/` 目录，非 `storage/qdrant`）未按 0f 清单清空——22,401 条旧 bge-m3 点留存。防混库指纹守卫正确拒绝 qwen3 写入（手动 vectorize 报 failed=64、degraded；overview `vector_status.rebuild_required=true`）。混库期间语义检索用 qwen3 查询比 bge-m3 向量，结果不可信。
- **处置（2026-09-23）**：将该集合改名归档为 `lingji_memory_production.bge-m3-20260923`（含 `meta.json` 摘除），App 重启后由新的自动 chunk 回填以 qwen3 全量重建（26,582 chunks）。**重建进行中，待验收后回填数字；最终 coverage 数字待验收后回填。**

## 已知问题与回滚方式

1. **已知撞端口**：AutoClaw 进程绑定 `*:8766` 与灵机 sidecar 冲突（交接文档已知问题，本轮再次出现）。
2. **回滚（变更一）**：revert 对应提交；手动 `/api/observability/vectorize` 端点仍可用，行为退回手动补齐。
3. **回滚（变更二）**：revert 对应提交；AGENTS.md 删除「灵机记忆检索优先」节。
4. **回滚（嵌入模型）**：配置切回 bge-m3 并重建；归档集合 `lingji_memory_production.bge-m3-20260923` 保留可查。
5. 观察项：qwen3 全量重建完成后的 coverage 数字与语义检索质量（重校阈值 0.55/0.92 为 bge-m3 口径，见 2026-09-23 `EMBEDDING_MODEL_SWITCH_QWEN3` 条目）。
