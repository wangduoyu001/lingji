# COMPREHENSIVE_ACCEPTANCE_20260930 — 灵机全面验收（2026-09-30）

## 结论

```text
verdict: PASS_WITH_FINDINGS
product_head: 1c737409 (codex/owner-source-intake-mac-repair)
deployed_sidecar_sha256_prefix: 16c023ca3d63a30c (对应装机记录 Head 663277f2，其后仅 docs 提交)
运行实例: /Applications/灵机.app sidecar PID 2498 (2026-09-29 11:56 UTC 启动) + Desktop PID 2479
生产根: /Users/wuhanwangduoyu/LingJiAcceptance/osimr-7e7f0707/app-data/production
```

产品运行时健康、无新增产品级回归；发现 1 个产品行为缺陷（9-29 MCP 单份化适配不完整导致 quality gate MCP 对照分支永久短路）+ 2 个测试树脱节项 + 1 个 Desktop ping 401 噪音疑点，均已定性并列入修复建议，本轮未改产品代码。

## 1. 门禁与静态检查

| 检查 | 结果 |
|---|---|
| `check_acceptance_sync.py` | PASS（product-impacting files: 0） |
| `check_local_execution_handoff.py` | PASS |
| `python3 -m compileall src/ scripts/` | PASS（exit 0） |
| 分支状态 | 本地 1c737409 领先远程 9 提交（本轮回推，见 §7） |
| 身份对齐 | 装机 sidecar `16c023ca…` = CHANGE_ACCEPTANCE_LOG 第七轮装机记录（Head 663277f2），HEAD 其后仅 2 个 docs 提交，代码与运行实例一致 |

## 2. 全量测试（基线 diff）

```text
python3 -m pytest tests/ -q --tb=no -p no:cacheprovider
→ 16 failed, 1915 passed, 22 skipped (303s)
基线（任务单 PERF_RESOURCE_CLOSEOUT_20260927B 验收标准 §6，基线 a090676f/37ea8711）: 14 failed
```

与基线逐条 diff：

- **修复生效 1 项**：`test_codex_mcp_tools.py::test_slim_search_results_keeps_agent_fields_and_drops_metadata` 基线失败、本轮通过（9-29 MCP 单份化修复的对应回归确认有效）。
- **基线 14 项中其余 13 项**：失败集合与基线完全一致，零漂移。
- **基线外新失败 3 项**（全部甄别定性，重跑复现一致）：

| 测试 | 根因 | 分类 |
|---|---|---|
| `tests/test_structured_evidence_lexical.py::test_state_db_revoke_and_expiry_are_excluded_from_current_gateway_context_and_mcp` | `TypeError: 'CallToolResult' object is not subscriptable` —— 9-29 `tool_result()` 单份化后测试调用点漏解包适配（同批 `test_automatic_memory_mcp`/`test_project_context_tools`/packaged_flow 均已适配，漏此文件） | 测试适配缺口 |
| `tests/evaluation/test_automatic_memory_end_to_end.py::test_real_quality_gate_reports_measured_result` | `selector_calls` 100≠200 —— quality_gate.py:830 的 MCP 分支（第二遍 `select_context_evidence`）被短路，即 MCP pack 获取/解析在该路径失败后走优雅降级，每问题只剩 gateway 一遍 | **产品行为缺陷**（MCP parity 永久 failed，降级未崩溃但功能失效），与上一条同根：9-29 变更返回类型变化的消费方适配不完整 |
| `tests/test_p2_08_p2_09_integration.py::test_desktop_uses_shared_polling_and_shadow_dashboard_without_execution_controls` | `FileNotFoundError: AttentionPage.tsx` —— dashboard 重构后该页面已移除，测试仍断言旧文件存在 | 陈旧契约测试 |

22 个 skipped 未逐条登记（`-tb=no` 模式），与既往全量轮次量级一致，留待修复轮核对。

## 3. Control API 真机验收（认证边界 + 15 端点）

- 认证边界：无 token → 401；错误 token → 401；正确 token → 200；ping 延迟 2.5ms。
- `/api/settings`（69.9KB）：递归扫描 **0 处疑似明文密钥**（sk-/40+hex 模式），掩码 + `_set` 标志机制在位。
- `/api/brain/status`（43.7KB）：`failure_ledger.total=9`、管线 0 降级、warnings 空、embedding healthy、vector degraded（rebuild_required=false）。
- `/api/work/failures`：聚合台账 9 条，`occurrence_count=542` 单条聚合实锤（failure_key 机制工作正常），字段完整（first/last_seen、requires_owner、detail）。
- `/api/observability/pipeline`：8 环节真实数据（原始获取 889 / 解析 886 / 去重 29 / 筛选拒绝 2 / 提炼 36,416 / 记忆层 19,554 / 向量化 27,891）+ 每环节大白话标注齐全。
- `/api/automatic-memory/value-gate/skipped`：enabled=true、thresholds {min_turns:2, min_chars:300}、total=0。
- `/api/memory/inspector/cards`：20 卡分页正常，字段完整（memory_id/kind/state/topic/conclusion/layers/trust/action）。
- 其余 observability/tasks、changes、feed、pending-actions、health 全部 200。

## 4. MCP 真机验收（stdio 探针）

- `tools/list`：**22 个工具**，与 9-23 记录一致（含 project_timeline）。
- `search_memory`：返回 content **1 块**（单份化修复生效），检索命中正常，citation 四字段契约在位。
- `recent_changes`：content 1 块；`relative_path` 出现在 `_RECENT_MEMORY_FIELDS` 白名单中——核对 src/mcp_server.py:44 确认为设计内字段（slim 契约收紧针对 search 通道的顶层 relative_path，recent_changes 白名单保留该字段供二跳定位），**不违例**。

## 5. 资源指标真机实测

- **突发窗口**（验收会话活跃摄入期，60s 采样 × 12）：CPU 92-177%、RSS 1.09GB。归因证据链：sample 采样热点 = SHA256（EVP_update/sha256_block_armv8）+ SQLite FTS5（fts5StorageIntegrityCallback/checkTreePage）+ GC；同一时刻 `storage/raw/` 持续写入新快照（10:09 多文件，内容寻址），`recent_events` 显示 `structured_ingestion_completed`（added 8/chunks 14——增量而非全量重建）+ reconciliation 正常。**即本验收会话本身正被灵机摄入**（活跃长会话每周期重导出该会话文本的既知设计语义），且 extraction_queue 无积压（queued=0/running=0/completed=1073）。
- **静止窗口**（摄入排空后）：CPU **1.9%**、RSS **967MB** —— 空闲 <5%、内存 <1GB 两项达标。
- 结论：突发型 CPU 与 PERF 收尾批定性一致（活跃摄入期突发、静止回落），本轮未见新的持续烧核缺陷。

## 6. Desktop UI 真机验收（截图）

- App/窗口存活（PID 2479），状态页真实渲染：3 项主导航（首页/记忆库/状态）、"运行中"徽标、每 15 秒自动刷新。
- **跨投影一致性实锤**：UI 显示"失败台账 9 条、失败任务 15 个、0 个管线降级"与 `/api/brain/status` 完全一致；记忆条数 27,969（分块 36,141）、向量 36,127（lingji_memory_production · 1024 维）、记忆库 251MB · 版本 2344、qwen3-embedding:0.6b healthy，与库实测（251MB、fts_rows=36141=chunk_rows）吻合。
- **诚实降级展示**：语义索引 `degraded`、"状态数据暂时过期，正在自动重试" 横幅如实呈现，无假绿。
- 自动记忆管线：distill / promotion / vector backfill 均正常（最近成功 2026-09-30 01:55-01:59，无失败记录）。

## 7. 发现与建议（本轮未修，留修复轮）

1. **P1（产品行为缺陷）**：9-29 MCP 单份化（`tool_result` → CallToolResult）消费方适配不完整——quality_gate 的 MCP pack 路径解析失败后永久走降级（parity 永远 failed、每问题少一遍对照），叠加 `test_structured_evidence_lexical` 一处测试漏解包。修复方向：适配 quality_gate.py MCP pack 消费 + 该测试解包；不得回退单份化（双份载荷是已实锤的契约缺陷）。
2. **P2（陈旧测试）**：`test_p2_08_p2_09_integration.py` 断言已移除的 `AttentionPage.tsx`，测试树与 dashboard 重构脱节，需按新导航契约重写或删除该断言。
3. **P2（log 噪音/疑点）**：runtime-sidecar.log 中 `GET /api/runtime/ping 401` 共 2,492 次（ping 总量 2,794 的 89%），日志周期 ~2.5 次/分钟——疑似 Desktop 主进程 runtime_manager 从错误的 data-root 读 token（`storage/control_api_token` 位置与实际部署根不一致），幸有"任何 HTTP 响应算活"语义兜底不影响可用性，但属身份配置缺陷 + 日志噪音，建议修复 token 根解析。
4. **观察项**：vector_state=degraded（覆盖缺口，backfill 正常运行中，rebuild_required=false）；storage/raw 2.3GB/2GiB 上限已满仍为既知主人待决策事项（本轮未动）。
5. 本地领先远程 9 提交（增量快照批等），本报告随本轮 docs 提交一并推送并对远程复读。

## 8. 边界

本轮为只读验收：未修改产品代码、未动 Vault/raw/生产库、未重打包、未安装；测试运行使用独立临时根与只读副本（quick_check 实测走 `mode=ro` 连接）。截图与采样为临时文件，报告落档后清理。
