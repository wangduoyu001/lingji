# MAINTENANCE_LOG.md — 排查优化总账（唯一迭代文档）

> Updated: 2026-09-30
> Status: CURRENT_AUTHORITY（排查优化/全面检查/修复轮的唯一滚动记录）
> 完整治理规则：`docs/DEVELOPMENT_RULES.md`、`docs/DOCUMENTATION_MAINTENANCE.md`

## 本文档的规则（主人 2026-09-30 拍板）

1. **后续所有"全面检查、排查、优化、修复"轮次只在本文件顶部追加/更新迭代记录，不再新建报告文件。**
2. 每条迭代记录覆盖写最新状态：结论、证据、发现、修复、遗留，旧细节被新记录替代后可压缩成一行。
3. 正式产品变更的验收要求仍走 `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`；任务单/回执仍是 `docs/ACCEPTANCE/` 的权威——本文件不替代它们，只收敛"排查优化类"的过程记录。
4. 一次性测试证据（哈希、命令、fixture）需要长期保留时放 `docs/TEST_REPORTS/` 并在本文件引用；纯过程记录不再进 TEST_REPORTS。

## 文档地图（2026-09-30 全面排查结论）

- **当前权威**：`PROJECT_STATUS.md`（状态）、`ARCHITECTURE.md`（架构）、`MODULES/CODE_MAP.md`（代码）、`ACCEPTANCE/`（验收）、`CHANGELOG.md`（用户可感知变化）、`DOCUMENTATION_MAINTENANCE.md`（文档角色契约）、本文件（排查优化总账）。
- **已核查合规的历史档案**（均有头部角色降级声明，不冒充当前状态，按契约默认保留，Git 历史可查）：`MODULES/P0_*、P2_*` 25 个实施记录（入口 `MODULES/README.md`）、docs 根 12 个阶段/设计报告（PHASE_02/03、MEDIA_EXTRACTION、WINDOWS_DB、REAL_ENVIRONMENT、RUNTIME_MEDIA、OBSIDIAN_*、AUTH_CREDENTIAL、PERMANENT_MEMORY_AND_RECALL 等）、`superpowers/plans/` 17 个实施计划（其中 owner-source-intake 计划被 AGENTS.md 引用）、入门存根 4 个（ENVIRONMENT/GETTING_STARTED/CONFIGURATION/DATA_FLOW，均已改为指向权威的重定向页）。
- **未发现过期冒充文档**。本次排查的处置决定：不批量删除（遵守 DOCUMENTATION_MAINTENANCE §5"历史证据默认保留"）；对历史档案的判断以本地图为准，不需要逐个打开。

---

## 迭代 #2：2026-09-30 raw 上限"又满了"排查——配置被静默还原，已恢复并回收 1.45GiB

主人追问"raw 2.3GB/2GiB 上限昨天不是解决了吗"。排查结论：**9-29 的写入放大修复有效（今日无新 186MB 级整库副本），"满"是配置被静默还原**——

- 9-27 主人拍板 raw 上限 3GiB→2GiB（F 项，备份 `.env.bak-20260927` 存改动前 3GiB 旧值）。
- **9-29 18:26（增量快照批验证期间，18:27 恰好写入 186MB 基线副本）`.env` 的 `automatic_memory_raw_max_bytes` 被改回 3GiB，验证后未复原**；19:56 sidecar 重启后 3GiB 生效至今。占用 2.76GiB 低于 3GiB → 自动淘汰从不触发 → 985MB 过 6h 保护窗的旧文件（含 186/130/125MB 旧整库副本）持续驻留。
- 此前验收轮报告引用 failures 历史拒绝记录里的"2,147,483,648"（2GiB）口径判定"已满"，未核对运行时实际值，属于口径疏漏（本轮修正）。
- 排除项（逐项验证过）：未终态任务保护名单未锁死大文件（failed 16 个引用的 raw_id 与过窗大文件零重叠）；`_dir_usage` 口径与实际一致；增量快照路径同样受限额检查约束。
- **修复**：`.env` 恢复 2147483648（2GiB，备份 `.env.bak-20260930` 存 3GiB 现场）；SIGTERM 旧实例（PID 2498）后手动重启（剥离代理环境变量，新 PID 38115，ping 200）；触发真实扫描 → 2GiB 上限生效 → **evict 自动回收 1,485MB（2.96GB→1.41GB，低于 70% 水位线）**，逐出账本 +325 条（186/130MB 旧副本入账）；"raw storage limit reached" 类失败 last_seen 全部停在 9-29（恢复后无新增），16 个 failed 提取任务的重试恢复有空间。
- **防再发**：改 `.env` 类生产配置必须在该轮报告记录"改了什么、为什么、何时复原"；验收轮核对限额类指标必须读运行时实际值（`/api/settings` 或 `.env`），不得引用历史失败消息里的冻结数值。

---

## 迭代 #1：2026-09-30 全面验收 + 三项修复（本轮）

### 验收结论：PASS_WITH_FINDINGS → 修复后核心项全部转绿

环境：分支 `codex/owner-source-intake-mac-repair`，验收起点 `1c737409`（运行中 sidecar SHA `16c023ca…` = Head 663277f2 装机，代码与实例一致），生产根 `LingJiAcceptance/osimr-7e7f0707/app-data/production`。

**验收通过项**：全量 pytest 验收轮 1915 passed / 修复后复跑 **1920 passed / 11 failed**（剩余 11 项全部为基线在案既有失败，零新增回归；对比验收轮净减 5：3 项本轮甄别修复 + test_formal_mcp_search_entry 同根修复 + test_stop_error 无 CPU 竞争后自然通过）；门禁双 PASS；compileall 零错；认证边界 401/401/200 + ping 2.5ms；`/api/settings` 递归扫描零密钥泄漏；失败聚合台账（occurrence_count=542 单条聚合实锤）；管线 8 环节真实数据；MCP 22 工具 + 单份化 + slim 契约；UI 真机截图跨投影一致（失败台账 9/15、记忆 27,969/分块 36,141/向量 36,127 与 API、库实测吻合；degraded 诚实展示）；静止 CPU 1.9% / RSS 967MB 达标（突发窗口为验收会话自摄入，队列零积压，摄入后回落）。

**验收发现并已修复（本轮）**：

1. **P1 产品行为缺陷（已修）**：9-29 MCP 单份化（`tool_result` → CallToolResult）消费方适配不完整——`quality_gate.py::_call_formal_mcp` 解不出 CallToolResult，每个问题的 MCP 对照分支抛异常走优雅降级（parity 永远 failed、每问题少一遍 selector，测试断言 100≠200 暴露）。修复：`_call_formal_mcp` 增加 `.content` 块列表解包（复用既有"仅接受 JSON 文本块"路径，不回退单份化）。修复后 `test_real_quality_gate_reports_measured_result` 通过。
2. **测试适配缺口（已修）**：`tests/test_structured_evidence_lexical.py` 三处 `server.tools["search_memory"](...)` 直接下标访问 CallToolResult → 加 `_tool_payload()` 解包 helper + 假 mcp 包挂真 `mcp.types`（对齐 test_automatic_memory_mcp 模式）。修复后全文件 9 passed，**基线既有失败 `test_formal_mcp_search_entry_returns_structured_message_citation` 一并修复**（同根）。
3. **陈旧测试（已修）**：`tests/test_p2_08_p2_09_integration.py` 断言已删除的 `AttentionPage.tsx`、过期导航契约（6 项 observe）→ 更新为当前契约：attention 路由由 `SystemStatusPage.tsx` 渲染（usePollingResource + failure_ledger 只读 + 零 fetch/POST）、observe 组 3 项主菜单（首页/记忆库/状态）。修复后 6 passed。
4. **ping 401 定性修正（上轮报告猜测错误）**：access log 中 2,492 次 401 ping（89%）不是 Desktop token 根问题——是进程内健康看门狗每 20s 的裸探针（`run_packaged_control_api.health_watchdog`，设计上不带 token、401 即"活着"的证据，注释明示）。**唯一缺陷是 access log 噪音**：已在 `run_control_api.py` 加 `_ProbePingAccessFilter` 过滤（含单测验证 ping 被滤、正常请求保留），下次打包装机后生效。
5. **文档治理（本轮新规）**：排查 docs 全目录 95+ 文档——全部带合规角色降级声明，无过期冒充；按主人指令建立本总账并并入验收报告，删除一次性报告文件 `docs/TEST_REPORTS/COMPREHENSIVE_ACCEPTANCE_20260930.md`。

**遗留观察项**：

- vector_state=degraded（覆盖缺口；backfill 正常运行、rebuild_required=false，待其自然追平后复核）。
- storage/raw 2.3GB / 2GiB 上限已满，新采集被拒——**待主人决策**（清理或提高上限）。
- `run_control_api.py` 的 access log 过滤需下次 PyInstaller 重打包后在真机生效（当前运行实例为旧包）。
- 全量测试 22 个 skipped 未逐条登记（-tb=no 模式），留待下轮核对。

### 历史索引

- 2026-09-29 MCP 单份化与状态页批：`docs/TEST_REPORTS/MCP_SINGLE_COPY_AND_RECENT_CHANGES_SLIM_20260929.md`
- 2026-09-27 审计响应批：`docs/TEST_REPORTS/AUDIT_RESPONSE_20260927.md`；资源占用根治：`docs/TEST_REPORTS/PERF_RESOURCE_ROOT_CAUSE_20260927.md`
- 更早轮次统一见 `docs/TEST_REPORTS/README.md` 索引。
