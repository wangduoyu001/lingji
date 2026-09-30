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

## 迭代 #6：2026-09-30 主人拍板落地——74 条记忆批量解锁 + 真实召回率 0%→96.7% + 词法检索缺陷修复 + Codex 质感设计稿

主人指令：质量门自行决定推进、保证数据准确稳定、有问题必须修；UI 先调研 Codex 皮肤质感再出稿。

1. **74 条 core 记忆批量解锁（数据准确性修复）**：Vault 中 74 个晋升文件仅改 frontmatter `agent_scope` 一行（lingji-auto → all，正文零改动，Vault git 可回滚），走生产同款 `IncrementalMemorySynchronizer.sync_core` 重同步。核验：core scope=all 79 条、仍锁 0、Vault 与索引 79/79 一致。codex/zcode 双身份 gateway 实测命中。
2. **词法检索两个真实缺陷修复（commit b0f7d173）**：①FTS5 语法字符（`#` `·` `/`）让裸整句 MATCH 直接 OperationalError；②trigram 跨空白整句连续匹配在 chunk 分行后必然 MISS。`_fts_expression` 重写为按空白拆词、短语 AND、丢弃 <3 字符 token（trigram 引擎约束），回归测试锁定（特殊符号标题自命中 + 多词跨行命中）。
3. **真实召回率标定结果（60 题生产抽样）**：修复前 0%，修复后 **Top1 = 96.7%（58/60）**。两条长尾：全角标点分词残余、BM25 排序被高频词压过——记录在案不阻塞。这是灵机第一个真实数据召回基线；标定方法（scope-aware 抽样 + AI 同路径检索）已沉淀可复用。
4. **UI 方向 D（Codex 质感）**：调研 Codex 桌面端主题系统（codex-theme-v1：深蓝灰 #303841 底 / #d8dee9 冷灰白 / #5c99d6 低饱和蓝强调 / 语义色 Nord 系 / 侧栏半透明）。设计稿新增方向 D「Codex Nord 质感」——零发光、零渐变、小圆角细边框、低饱和冰蓝点缀，设计稿更新为四选一（浏览器 4173/design.html）。等主人选向。

---

## 迭代 #5：2026-09-30 真实召回标定——发现并修复"晋升记忆对 AI 全盲"批量缺陷 + UI 设计稿待主人选向

主人指令：真实数据质量试运行先干、UI 先出设计稿通过后再写代码。

**真实召回标定（只读生产库，60 题抽样）**：从生产 78 条正式记忆（knowledge/preference，core 层）抽样 60 条，以记忆主题为查询、走与 AI 完全相同的检索路径（gateway → HybridRetriever）测命中。**结果 Top1/Top5 全零——这不是检索器坏了，而是揪出一个批量产品缺陷**：

- **缺陷**：自动晋升管线（9-22 上线）propose 阶段以管线内部身份 `lingji-auto` 写入 `agent_scope=["lingji-auto"]`，promote 沿用该 scope。`lingji-auto` 不在 AIProfileRegistry 中——**74 条已批准晋升的 core 记忆对所有 AI（codex/zcode）完全不可见**，检索权限过滤把它们全部拦下。晋升管线在正常工作，但晋升成果被锁进了 AI 打不开的抽屉。
- **修复（commit 1b17b662）**：`_promote_row` 显式传 `agent_scope=["all"]`（晋升 = 主人门槛批准 → 全域可见；proposed_by 审计字段保留 lingji-auto）。新增回归测试锁定（16 passed），晋升管线既有 60 测试全绿。
- **存量处置待主人批准**：74 条已锁记忆需一次性批量开放（改 scope 为 all + 索引重同步），一条命令可完成，等主人点头。
- 附带发现：74 条记忆是「标题即内容主题」型知识；标定方法学已验证可复用（scope-aware agent 选择 + trigram 友好查询），修复存量后重跑即可得真实召回基线。

**UI 设计稿（主人裁定：先设计通过、再写代码）**：三个科技感暗色方向高保真稿已放主人浏览器（`desktop/lingji-control/dist/design.html`，端口 4173 预览），数据全部来自真实生产库：A 极光玻璃（青绿渐变/发光数字/玻璃拟态）、B 赛博终端（紫罗兰辉光/网格线/等宽字体）、C 指挥舱（深蓝+琥珀高亮/双色水位）。**等主人选向后再动产品代码**；先前调研结论（shadcn dark 生态/Horizon UI）已融入三稿。Tauri 桌面构建已中止避免白干。

**质量门大白话**（主人问"看不懂"）：质量门 = 一场 100 题的考试，考灵机的记忆系统：①答案对不对 ②每句话能否指出出处（引用）③AI 用的检索和主人看的界面是否同一份事实。9-8 那场考试 106 个引用全没对上、判了不及格。本轮已确认不及格的两个技术原因（对照通道坏掉已修 + 记忆被锁进 AI 看不见的抽屉已修），需要在真实数据上重考——即"翻案"。重考在存量 scope 批准后与召回标定合并执行。

---

## 迭代 #4：2026-09-30 Phase 1 收官执行——基线失败 14→2、新 sidecar 装机、真机复测达标

主人指令"把你能干的干了"。本轮执行收官路径的工程部分：

1. **基线既有失败甄别清零：14 → 2**（最终全量 1929 passed / 2 failed / 22 skipped）：
   - **产品缺陷修复 1 项**：`scheduler.py::_snapshot_throttle_deferral` 的节流短路曾**先于授权检查**——撤销/过期的源被 defer 返回 complete=True，授权边界被掩盖；修复后授权边界优先于节流（revoke 立即拒绝）。
   - **测试契约更新 9 项**（每项均有在案产品变更依据，非降断言）：①scheduler ×2 + task8e ×3 + packaged_flow 节流变体——9-27 F 项自适应节流（同源 30 分钟最小重拍）为新契约，测试显式 `snapshot_throttle_seconds=0` 隔离两个契约；②context_pack reason_code——WorkBuddy 9-17 R1"结果层解释优先"（双 0 报 no_matches，通道故障仍由 semantic=degraded 标注）；③control_api ×2——9-17 R5 vector/status 的 Qdrant live 计数修正是有意设计（快照之上叠加，测试环境空 qdrant 确定性 0）；④heartbeat——9 月批次 `run_on_start` 启动即对账合法，契约收紧为"heartbeat 刷新不触发 reconciliation"（基线取首拍后）；⑤repair_round1——9-22 晋升管线的 VaultLayout 骨架初始化合法，基线移到 start() 后。packaged_flow 额外把 75s 超时放宽到 150s（60s clamp + 采集 + 裕度，忠实"一个周期内"语义）。
   - **剩 2 项如实记录**：packaged_flow（throttle 变体已修、失败点已推进至 reconciliation 事件 reason 匹配深水区，在案时序类）；stop_error（flaky 抖动：stop 超时 vs run_once 状态竞争，本轮某次全量曾通过）。
   - **22 skipped 逐条登记**：全部为条件性 skip——symlink 平台能力 ×6、PowerShell host 缺失 ×1、frontend dist 未构建 ×1、100k 基准显式 opt-in ×1、条件导入/兼容守卫其余——无失败伪装。
2. **新 sidecar 打包装机**：SHA `9da34027…`（含 quality gate MCP 适配、ping 日志过滤、授权边界优先），覆盖安装至 /Applications/灵机.app 并重启（PID 41524，ping 200/4.8ms）。**真机复测：ping 401 噪音清零**（新实例 65 秒 0 条 access log，过滤器生效）、CPU 1.2%/RSS 829MB 达标。
3. **质量门（frozen 100 题）**：隔离根重跑确认管线健康（MCP parity 不再永久 failed、selector 计数恢复）；但 `report=None` + corpus 导入失败表明**完整测量需按 MEMORY_QUALITY_TRIAL 协议的真实数据环境**，快速隔离跑无法复现 9-8 的测量口径——列入主人拍板项（Phase 1 收官的关键一步）。
4. master fast-forward 合并随本轮提交执行。

---

## 迭代 #3：2026-09-30 全面验收（重启后复验）+ Phase 1→Phase 2 差距评估

**复验（raw 修复 + sidecar 重启后）**：memory/vector/embedding 全 healthy（vector degraded 自愈）、管线零降级、队列无积压、meta.json 无 acceptance 残留（B3 守卫重启窗口验证 ✓）、静止 CPU 13.9%→恢复期结束后应继续回落、raw 1.31GiB 稳定在 2GiB 纪律内、Desktop 存活。master 落差收敛：产品分支领先 20、master 独有 0（可 fast-forward）。

**距离 Phase 2（机会中心）的差距清单**（Gate = Phase 1 自动门禁+真机+主人观察+报告清理全闭环 PASS）：

A. 工程收尾（阻塞 Phase 1 PASS）：
1. 质量门 MEASURED_FAIL 未翻案——frozen 100 题诊断（9-8 产物）`citation_hits 0/106`、phase FAIL；4r2-readiness NOT_REACHED。本轮已修 quality gate MCP parity 降级路径，需在隔离根用当前代码重跑质量门（预期显著改善或暴露真差距）。
2. 全量 11 个基线既有失败未甄别清零（scheduler 超时类 ×2、control_api 快照类 ×2、task8e fallback 类 ×3、packaged_flow、context_pack、repair_round1、heartbeat）；22 skipped 未逐条登记。
3. 装机滞后：quality gate 修复、ping 日志过滤等源码改进未重打包装机，运行实例仍是 663277f2 的包。
4. master fast-forward 合并（20 commit，零冲突风险）。

B. 主人体验收尾（阻塞 Phase 1 PASS）：
5. 两个 ACTIVE 任务（审计响应批、资源收尾批）的主人体验确认从未完成——按规矩不确认不收口。
6. Evolving 时间线文件待主人审阅；晋升管线待主人最终确认。
7. 主人体感验收轮从未执行（M5"看不出灵机做了什么"结论后的系列修复只有技术验收）。

C. 平台与流程（Phase 1 范围内）：
8. Windows 双平台构建/真机验收从未执行（Mac 是唯一开发机）——需主人拍板 Phase 1 内做或顺延。
9. full/release 门禁未在当前代码树完整跑过（最近一次 release gate 是 8 月底 FAIL）。

D. 记忆质量长期项（不阻塞）：
10. 真实问题集召回率标定（当前质量门仅合成语料）；raw 引用回收；JSONL 字节游标。

**建议收官路径**：重打包装机 → 隔离根重跑质量门 → 基线失败甄别清零 → full 门禁 + master 合并 → 主人体感验收轮 + 两个 ACTIVE 任务收口 → Phase 1 PASS → Phase 2 启动（第一步：审计现有机会代码，禁止第二套存储/UI）。

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
