# 当前本机任务：外部优化审计响应

## 本轮：外部优化审计响应（2026-09-27 夜）

```yaml
task_id: AUDIT_RESPONSE_20260927
status: ACTIVE
baseline_commit: 37ea8711
product_branch: codex/owner-source-intake-mac-repair
execution_mode: AUDIT_RESPONSE_BATCH
```

外部优化建议书（基线 5e51f8bb）评审后落地。**建议书机制修正**：其"同步拷贝持 GIL 饿死事件循环"与现场证据不符（挂死期零 CPU 增长、无持 GIL 帧）；真实机制 = 多后台线程分别卡死在系统调用（DNS/sqlite open/iterdir）+ SIGTERM 优雅停机被拖死。修复清单方向采纳、看门狗设计升级。

### 已完成

- [x] **0.1 服务恢复 + 日志归位**：挂死 110 分钟进程 SIGKILL 终止；sidecar stdout/stderr 归位 `logs/runtime-sidecar.log`；挂死证据归档 `logs/runtime-sidecar-hung-20260927.log`；手动重启一律剥离代理环境变量。
- [x] **5.1 全量基线 diff**：HEAD 与基线 a090676f 失败集合逐条相同（14=14），**本轮零新增回归**；完整清单入档（此前只列 4 个系漏报）。MCP citation 断裂 + slim search 泄漏 relative_path 两个契约级缺陷已修（commit 6546e8d9，白名单去 relative_path 加 citation，vault 定位迁至 citation.path）。
- [x] **0.2 健康看门狗**：进程内探活绕代理直连 loopback，任何 HTTP 响应（含 401）算活；连续 3 次 × 20s 超时 → SIGTERM，30s 宽限未退 → **SIGKILL 升级**（优雅停机会被卡死线程拖住，仅 SIGTERM 不够）。开关 LINGJI_WATCHDOG_ENABLED，默认开。
- [x] **提炼 DNS 卡死修复**：`_available_models` 改进程级单线程探针（urllib timeout 管不住 getaddrinfo），至多卡死一个线程；调用方限时 8s 拿最近结果，探不动按空退避。
- [x] **1.1 扫描移出 HTTP 线程池**：scan_now 走专用单线程执行器，5 秒预算内返回真实报告（快路径契约不变），超预算转"已受理"（进度走 /scans 轮询）；177MB 大库哈希改 `hashlib.file_digest`（C 层释放 GIL）；源级并发由既有调度器 single-flight 管辖。
- [x] **4.2 密钥脱敏**：/api/settings 的 values 与 overrides 两处一律掩码（dac0…Tuqn）+ `*_set` 标志；掩码回写被识别为未修改绝不覆盖真值；runtime_settings.json chmod 600；内部消费方（提炼真实调用）继续走 snapshot() 拿全值。
- [x] **4.1 Vault git 自动提交**：晋升落库后 `_vault_git_autocommit` 补版本锚点（add -A + commit，绝不 push）；失败只告警不阻塞；回归 3 例。
- [x] **部署验证**：SHA `dae0d1cb…`，ping 5.7ms，/api/settings 全值零泄漏，手动扫描 912ms 返回真实报告。

### 第二批已完成（2026-09-27 夜·续，主人指示"按你的建议执行"）

- [x] **3.2.1 证据独立通道**（commit d188fe24）：检索分通道重排——memory 通道（knowledge 等）优先、evidence 通道殿后并带 `retrieval_channel` 标签；证据永不丢弃仍可引用展开。修正点：真正生效的检索器是 `src/retrieval/enhanced.py`（包导出指向它而非 hybrid），其 fallback 路径在 _fuse 后会按分数重排——排序键已改为通道优先。回归 2 例 + 检索扩面 154 过。
- [x] **4.3 Qdrant 双根核实 + 缺口收敛**：两集合粒度不同（lingji_memory_production=chunk 级正式语义、lingji_automatic_memory=消息级 MCP 召回），各有消费方，**非冗余，不删**。缺口根因=Ollama 未运行（嵌入不可用）——已拉起 Ollama，连续回填 796 缺口 → 0，之后 B2 快路径零成本待命（status=fast-path）。
- [x] **5.2 主线收敛（本地完成，推送受阻）**：master 独有提交为 0（产品分支是严格超集，领先 736）→ 主仓 master 已 fast-forward 到 3f0ee2c2，master 的收集报错/坏测试随树更新消失。**推送 GitHub 被网络阻断**（SSL_ERROR_SYSCALL，今晚代理/网络故障延续）——按治理规则如实记录为阻塞项，网络恢复后 `git push origin HEAD:master` 一条命令完成。
- [x] **5.4 卫生**：删除无引用死代码 src/control/work_api.py（与 work_routes.py 重复定义，api.py 实际用 work_routes）；.zcodeignore 入 .gitignore；3 周未动的 owner-memory-detail-drilldown worktree（干净）已移除。
- [ ] 2.2 失败按源聚合 + PendingAction(owner)：子代理实现中，完成后单独提交。

### 待办（下一轮）

- [ ] 2.2 失败按源聚合（1291→≤3）+ PendingAction(actor=owner) + 可行动信息。
- [ ] 3.2.1 evidence 移出 owner 检索主通道（独立 rank 通道，语义需主人确认）+ 价值门扩展到证据入库 + knowledge 增长 KPI。
- [ ] 4.3 Qdrant 双根消费者核实（chunk 级 vs 消息级，并非简单冗余）+ 648 chunk 缺口回填 + coverage 诚实化 + >20k 点容量决策。
- [ ] 5.2 主线收敛（master 726 commit 脱节，需主人拍板合入策略）+ master 坏测试修复。
- [ ] 5.4 卫生：worktree 归档、死代码删除、文档归档索引。

回滚：0.2/1.1/4.1/4.2 均可独立 revert；看门狗有 LINGJI_WATCHDOG_ENABLED=0 关闭；不改 Vault 语义、不删 raw、不动主人数据。

---

# 当前本机任务：资源占用根治优化·收尾批

## 本轮：资源占用收尾批（2026-09-27 晚）

```yaml
task_id: PERF_RESOURCE_CLOSEOUT_20260927B
status: ACTIVE
baseline_commit: f5fd11f2279912b8a6926185df43f37fab5a6c4d
product_branch: codex/owner-source-intake-mac-repair
execution_mode: PERF_ROOT_CAUSE_CLOSEOUT_BATCH
```

上一轮 PERF_RESOURCE_ROOT_CAUSE_20260927 真机验收通过（空闲 CPU 0.0%），但本会话复核发现运行中 sidecar 在持续 ingestion 时仍突发高 CPU（瞬时实测 ~15-95%，突发型）——每批 ingestion 触发 read model 全量重插 → sync 全量重 chunk 21k 消息，正是 A1 收尾要根治的残余热点。本轮完成四项收尾。

### 落地计划及完成标准

- [x] **A1 收尾**（2026-09-27 晚，commit c24ab5b6）：`sync_structured_evidence` content-addressed 增量重构——两阶段：①轻量行扫描（不含 content 列）逐行算 memory_id（hash(source|conv|msg|content_hash)）→ 临时表主键批量比对；②只对"文档不存在 / content_hash·status·title 需变"的行读 content + chunk + upsert。watermark/covered-digest 机制删除；`structured_evidence_document_count/chunk_count` meta 改为真实全量口径；title 漂移传播修复（现行为：title 变化永不落投影文档）；消息内容被清空时旧投影归档。回归：增量两轮零 chunk 调用、批量等价性（增量 vs rebuild 投影一致）、revoke/孤儿/空内容语义不回退。
- [x] **B1 收尾**（2026-09-27 晚，commit f60fd015）：阈值（value_gate_enabled/min_turns/min_chars）进 RuntimeSettingsStore 设置目录并对运行中 runner 动态生效；gated skip 的 manifest_status 从误导性的 "queued" 改为独立值域 `skipped_by_value_gate`（值域核对）；新增 GET `/api/automatic-memory/value-gate/skipped`（滚动样本+计数）与 POST `/api/automatic-memory/value-gate/rescan`（按来源撤销 skip，下次扫描重采集重判定）；observability 状态映射补大白话。
- [x] **B3 守卫**（2026-09-27 晚，commit 2d7e9d1c）：根因实锤——上轮归档只删集合目录，`<data-root>/qdrant/meta.json` 注册表仍登记 `lingji_memory_acceptance`，qdrant-local 每次打开按注册表重建空目录（12KB storage.sqlite）。修复：embedded 客户端池打开路径时自动注销"非本工作区且点数为 0"的外来集合注册（幂等守卫，有数据的集合只告警不删）；meta.json 实际清理随下次重启窗口执行。
- [x] **C**（2026-09-27 晚，commit ea9e8703）：vector_backfill 死 SQL（`_pending_message_rows`，NOT EXISTS 无法跨 qdrant 的残留）删除；run_once 增量 diff 默认不拉向量本体（payload-only scroll）；退化向量/坍缩治理改为显式 deep 检查路径（语义保留、不再每轮全量拉向量）；`create_collection` 从逐条循环提前到集合缺失时一次性创建。extraction_jobs.status 索引已核实由 idx_extraction_jobs_due 前缀覆盖，无需新建。
- [x] **E（真机复测追加，后又回滚：commit 3fb2f1d6 → revert 45c5bb59）**：空闲 CPU 未达标（持续 ~23-33%，队列空、日志静默）。最初假设 dir-usage stat 风暴，缓存修复后无改善即回滚——真实 raw 为 `storage/raw`（3.05GB、507 顶层文件，扫描微秒级）。【已定位，见下】最初误判为待查热点，后经 lsof+文件增长+节流记录实锤：这是滚动大库（本会话所在的 177MB 会话库）按 1800s 节流整库重拷+流式 SHA-256 的设计行为，见「真机结果」节。
- [x] **F（主人拍板落地，2026-09-27 晚，commit addbfef8）**：主人指示"不得过度占用性能与硬盘（含备份），其他按最优解"。落地：①自适应快照节流——窗口 = max(基准 30 分钟, 最近一次真采集最大快照字节 ÷ 0.5MB/s ÷ 5% 目标占空比)，大源自动拉长间隔（177MB 库 → ~124 分钟），小源保持基准响应，单源 CPU 占空比自限 ~5%；②小文件保护窗 24h→6h（churn 地板从 ~1.6GiB 降到 ~0.4GiB）；③raw 上限 3GiB→2GiB（数据根 .env，备份 .env.bak-20260927）。回归：test_snapshot_adaptive_throttle.py 7 例 + test_raw_retention.py 10 例全绿。
- [x] **真机验证（SHA df8c9f96，PID 22173）**：静止 CPU **1%**（此前 23-33%）；手动触发采集 → 逐出+采集链路在 2GiB 上限下正常完成（.evicted.log 有账）。**根因定性修正**：持续 26% CPU = 唤醒→300 秒回填排水循环接力（旧核对风暴高频唤醒），非单一缺陷；静止期的具体 SHA256 调用点未最终钉死（py-spy 需 sudo），时间线相关性已实锤。vectorize 端点观测到 >400s 挂起于 Ollama 嵌入等待（0% CPU），列为观察项。

### 验收标准

1. 相关 focused 测试全绿（含新增回归）；存量失败如实报告，不得 skip 掩盖。
2. 改动完成后 PyInstaller 重打包重启 sidecar，真机复测：空闲 CPU<5%、内存<1GB、ingestion 批处理突发峰值显著下降（对比本轮实测基线）。
3. meta.json 中 acceptance 注册消失、生产 qdrant 无 acceptance 集合目录重建。
4. PROJECT_STATUS/TEST_REPORTS/CHANGE_ACCEPTANCE_LOG 同步。
6. **全量基线 diff（2026-09-27 晚，外部审计质疑后的补测）**：HEAD `37ea8711` 与基线 `a090676f` 各跑全量（HEAD 14 failed/1858 passed；基线 14 failed/1819 passed，+39 新测试全过），**失败集合逐条 diff 为空——本轮零新增回归**。基线既有失败完整清单（14 个，替代此前只列 4 个的漏报）：
   - tests/integration/test_automatic_memory_packaged_flow.py::test_automatic_memory_packaged_flow_runs_twice_from_clean_acceptance_roots
   - tests/test_automatic_memory_context_pack.py::test_hybrid_diagnostics_are_per_call_and_semantic_failure_is_safe
   - tests/test_automatic_memory_repair_round1.py::test_automatic_snapshot_never_mutates_configured_vault_or_calls_document_sink
   - tests/test_automatic_memory_runtime.py::test_stop_error_keeps_cleanup_pending_and_allows_retry
   - tests/test_automatic_memory_scheduler.py::test_reconciliation_admits_once_and_persists_report
   - tests/test_automatic_memory_scheduler.py::test_reconciliation_runs_after_event_silence
   - tests/test_codex_mcp_tools.py::test_slim_search_results_keeps_agent_fields_and_drops_metadata
   - tests/test_control_api.py::ControlApiTests::test_memory_vector_and_coverage_endpoints_return_shared_snapshot
   - tests/test_control_api.py::ControlApiTests::test_settings_can_be_read_updated_and_reset
   - tests/test_structured_evidence_lexical.py::test_formal_mcp_search_entry_returns_structured_message_citation
   - tests/test_task6h_heartbeat.py::test_idle_runtime_persists_instance_bound_heartbeat_and_refreshes_without_reconciliation
   - tests/test_task8e_safe_polling_fallback.py::test_fallback_manual_scan_and_revoke_stop_admission
   - tests/test_task8e_safe_polling_fallback.py::test_fallback_pause_resume_restart_preserve_reconciliation_without_starting_watcher
   - tests/test_task8e_safe_polling_fallback.py::test_fallback_stays_quiet_for_two_reconciliation_periods_and_discovers_on_schedule
   修复排期见外部优化建议评审（MCP citation/slim search 为契约级，优先）。
5. 最终状态（2026-09-27 晚）：A1/B1/B3/C 四项全部落地、focused 全绿（基线既有失败如实记录：test_formal_mcp_search_entry、test_reconciliation_runs_after_event_silence、test_reconciliation_admits_once_and_persists_report、test_memory_vector_and_coverage_endpoints_return_shared_snapshot）、PyInstaller 重打包重启 sidecar 完成。**真机复测：B3 守卫实锤生效（meta.json 仅剩 production 注册）；A1 重放 0.0247s/2000 消息零 chunk。空闲 CPU 持续 23-33% 的根因已定位：不是本轮代码缺陷，而是滚动大库（177MB 会话库）按 1800s 节流整库重拷+流式哈希+再提炼的设计行为——每 30 分钟一个约 6 分钟的周期，占空比恰为实测值；上一轮"空闲 0.0%"是采样窗口落在周期间隙。E 试错（dir-usage 缓存）已回滚。整体状态：代码完成，真机验收 PARTIAL，不得写 PASS；"空闲<5%"验收线对当前节流设计不成立，需主人决策（见下）。**

回滚：全部为代码层改动可独立 revert；meta.json 清理只删 acceptance 注册条目不动数据；不改 Vault、不删 raw、不动主人数据。

---

## 上一轮：资源占用根治优化（2026-09-27，COMPLETED）

```yaml
task_id: PERF_RESOURCE_ROOT_CAUSE_20260927
status: COMPLETED
baseline_commit: a090676fa3afb921bca2ab27ed2fd5376e461018
product_branch: codex/owner-source-intake-mac-repair
execution_mode: PERF_ROOT_CAUSE_FIX_BATCH
```

诊断已实锤（sample 采样 + SQLite 执行计划验证）：lingji-core 持续烧满一核（~98%）的根因是 `sync_structured_evidence` 全量同步 21k 消息（每条重新 chunk + 逐条 json_extract 溯源全表扫描，memory_db.py:433）；UI 每秒轮询 discovery 端点全量重扫文件系统（持 GIL，卡 UI）；chunk 回填每次唤醒 O(N) 双向比对；acceptance 集合驻留生产进程。

### 落地计划及完成标准

- [x] A1 溯源物化+批量预取（2026-09-27，commit 5aea694e）：rel_* 三键 VIRTUAL 生成列 + 复合部分索引已进 schema（table_xinfo 检测，幂等防并发 duplicate）；溯源查询改临时表批量预取（走新索引）；孤儿归档 SQL 化（三键 NOT EXISTS）；已覆盖输入指纹（消息 hash + 已投影 source 状态 + conversation title）漂移自动回退全量，保证 revoke/改写正确性。**关键发现：read model 是全量重建型（每批 DELETE 三表重插），updated_at 水位不成立——彻底增量化需 content-addressed 重构（memory_id 本身就是内容寻址：轻量行扫描 → 主键比对跳过未变行 → 只对变化行 chunk+upsert），列为下轮首选**。新增回归测试 4 例全绿；存量相关测试与基线一致（仅既有失败 test_formal_mcp_search_entry，与本轮无关）。
- [x] A2 UI 轮询节流（2026-09-27，commit 42cae364）：discovered/apps/processes 三端点 60s TTL 进程级缓存（cached_discovery_snapshot）；MemorySourcesPage 轮询 8s→30s；缓存命中/TTL 过期/key 隔离 3 例单测全绿。
- [x] B1 入口价值预判（2026-09-27，commit 34777239）：value_gate.py 纯规则引擎（<2 轮且 <300 字符且零信号才拒；代码/链接/决策词/命令/路径为信号）；SnapshotJobRunner admit 处接入（gate_admission 合成走既有状态机，sentinel 照记防重复捕获）；审计 JSONL runtime/value_gate_skipped.jsonl（滚动 200 条，绝不静默）；config 默认开（value_gate_enabled=True），测试路径经 getattr 缺省关闭；单测 6 例全绿。**UI skipped 展示端点与 RuntimeSettingsStore 阈值调节列下轮**：入队前三层规则（轮数/字数门槛 + 价值信号保底 + 阈值进 RuntimeSettingsStore），skipped 计数与滚动样本 UI 可见、可按来源重扫撤销；默认只拦 1-2 轮且零信号；绝不静默丢弃。
- [x] B2 回填 O(1) 预检（2026-09-27，commit cef08131）：MemoryDatabase.semantic_chunk_count() + run_once 计数相等即 fast-path 跳过三次 O(N) 扫描；计数漂移回退全量修复，回归测试覆盖。
- [ ] B3 摘除 acceptance 集合：生产进程不驻留 acceptance 集合。
- [ ] C（下轮）：vector_backfill 死代码 SQL 重写（增量 diff、不拉向量本体）；extraction_jobs.status 索引经核实已由 idx_extraction_jobs_due 的 status 前缀覆盖，无需新建。

### 验收总指标（真机实测）

1. 空闲态 CPU < 5%（无新会话产生时采样 60s）
2. 内存 < 1GB
3. UI 无体感卡顿（轮询频率日志下降 90%+）
4. 存量测试全绿 + 新增回归单测（批量等价性、增量水位、孤儿归档、生成列索引 EXPLAIN）
5. 混库守卫回归验证通过

流程：focused 测试 → PyInstaller 重打包重启 sidecar → 真机指标实测 → PROJECT_STATUS/TEST_REPORTS 同步。

### 真机结果（2026-09-27，详见 docs/TEST_REPORTS/PERF_RESOURCE_ROOT_CAUSE_20260927.md）

- [x] 空闲 CPU 0.0%（改前 96-98% 持续）
- [x] 内存 810MB RSS（改前 1.74GB）
- [x] 轮询日志 14 行/分钟（改前 120-300）
- [x] 混库守卫：部分达成——acceptance 集合移除后被启动逻辑重建（12K 空），创建点待查
- sidecar SHA-256 `78732387…`，PID 13751，8766 监听正常，MCP 词法检索正常回滚：索引为加法可保留；缓存/预判/预检有开关可独立 revert；不改 Vault、不删 raw、不动主人数据。

---

## 历史：个人记忆实用优化（2026-09-19）

```yaml
task_id: PERSONAL_MEMORY_PRACTICAL_OPTIMIZATION
status: COMPLETED
baseline_commit: 264b14d3a3a3690b2ba768f2844660abd87f16f9
product_branch: codex/owner-source-intake-mac-repair
execution_mode: BOUNDED_BACKEND_REPAIR_AND_HYGIENE
```

主人本轮明确授权剩余优化与卫生清理，覆盖下方旧任务范围限制；旧任务只作历史背景。本轮不新增平台、模型、队列或数据库，不重写 UI，不合并远程主线。

### 落地计划及完成标准

- [x] 召回：将原始语义分数门槛接入当前 HybridRetriever；保留权限/时态/全文通道。低分语义剔除、低分但精确全文仍命中、MCP 正负例一致。
- [x] 启动与访问：已有 MemoryDatabase 初始化不请求写锁；MCP 通过认证的现有后端共享索引，避免跨进程打开 Qdrant。用真实锁与跨入口样本测试。
- [x] Core：复用现有索引读写，启动时只对账已批准 Core 文件；已有聊天索引非空仍补入 Core，不重复，不丢聊天证据，不修改 Vault。
- [x] 扫描与增长：复用既有 scan manifest 跨轮跳过未变且可复用快照；变化、原始快照丢失时重新采集；原始快照容量限制给出可解释停止，不删除真实资料。
- [x] 验证与清理：先记录失败测试，再做最小实现；对应模块测试与隔离后端/MCP 验证，后端安装验证（含一次直接相关的 Core 显示收尾）；保留现有 UI，不要求无关组件变绿。

测试入口为新增实际行为测试及相关既有模块测试，结果写现有 OWNER_SOURCE_INTAKE_MAC_REPAIR.md。本机数据只用于既有已批准内容的索引对账与只读回验，不批准新记忆、不删除 raw/Vault、不修改其他软件。安装前保留一个完整旧应用回滚副本，测试通过后清理临时数据库、构建中间产物与本轮缓存。失败证据保留到原因已记录，不进入无限修复。

---

## 以下为已被本轮替代的历史任务

# LingJi 本机执行任务单

> **当前状态：ACTIVE（`OWNER_SOURCE_INTAKE_MAC_REPAIR`）。**
>
> 本文件仍是本机 Codex 的唯一任务入口；下方第 0 节是当前唯一可执行的有界修复任务。

## 0. 当前 ACTIVE 任务

```yaml
task_id: OWNER_SOURCE_INTAKE_MAC_REPAIR
status: SUPERSEDED
execution_mode: OWNER_SOURCE_INTAKE_PRODUCT_AND_MAC_REPAIR
repository: wangduoyu001/lingji
product_branch: codex/owner-source-intake-mac-repair
baseline_commit: 1d4cd95bcbe73455507bc32c969f6eab5923bd86
product_commit: 234690b89f671e328bd610966af73e74684434bd
product_pr: NONE_NOT_A_RELEASE_GATE
release_gate: OWNER_EXPERIENCE_CANDIDATE_ONLY
artifact_name: lingji-macos-arm64-app
artifact_id: LOCAL_BUILD_osimr_7e7f0707
report_branch: acceptance/owner-source-intake-mac-repair
report_path: docs/TEST_REPORTS/OWNER_SOURCE_INTAKE_MAC_REPAIR.md
public_summary_path: PENDING
public_hashes_path: PENDING
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
live_8766_8767_forbidden: false_for_isolated_mac_acceptance_only
install_forbidden: false_for_whole_bundle_isolated_mac_acceptance
owner_data_forbidden: true
full_release_forbidden: true
owner_confirmation_required: true
maximum_repair_rounds: 3
```

本任务按 `docs/superpowers/plans/2026-09-04-owner-source-intake-mac-repair.md` 执行。范围只包括
automatic-memory 本地 AI 元数据发现、主人目录授权、扫描/处理/导入真实阶段 DTO、来源页反馈、
动作可用性及其 focused/真实 Mac 验收；不得新增第二套数据库、队列、状态中心或端口，不修改记忆算法。

基线候选 `1d4cd95bcbe73455507bc32c969f6eab5923bd86` 的 Mac packaged、安装和全页技术遍历保留为历史
`PASS_WAITING_OWNER_EXPERIENCE`，但主人最新观察已将该候选判为 `REPAIR_REQUIRED`：扫描后缺少
可见闭环、确认按钮不可用、官方导出目录选择后无结果提示，并存在把扫描/排队描述为接管/导入完成的
错误语义。本轮必须先用合成 fixture 复现，再做最小修复；不得读取主人真实 AI 软件数据。

模型清单、模型运行/兼容状态、灵机自检、系统健康和记忆健康字段必须原样保留，来源状态只能扩展，
不能覆盖或删除。只读扫描不得启动/停止/写入目标 AI 软件，不得修改配置、读取 secrets 或越过授权根。
完成 focused 后，新产品 SHA 必须从全新隔离根重跑完整 Mac package/install/真实 UI；代理通过后保持
App/sidecar 打开等待主人确认。Mac 技术验收与主人确认均通过前，Windows、push、PR、merge、结束清理
继续禁止。上一候选当前运行实例和失败证据必须保持不动，直至新候选准备完成。

## 0B. 追加 bounded 修复：WorkBuddy 复检 P0（2026-09-16，主人指令）

```yaml
task_id: OWNER_WORKBUDDY_RECHECK_PIPELINE_RECALL_REPAIR
status: SUPERSEDED
execution_mode: FOCUSED_PRODUCT_REPAIR_ONLY
parent_task: OWNER_SOURCE_INTAKE_MAC_REPAIR
trigger: 主人 2026-09-16 指令"按 WorkBuddy 复检报告做一轮修复，然后做一轮卫生清理"
scope:
  - FIX1 codex_rollout 适配器白名单扩充：识别 Codex 0.154.x 新遥测信封 token_usage_record
    （9-13 起全部快照提取 failed 的根因；严格 fail-closed 语义不变，遥测内容不入对话流）
  - FIX2 /api/observability/recall 召回护栏：低于分数下限的命中丢弃；满分(>=0.999)仅允许
    查询词与命中内容互为子串的真重复（退化向量不得冒充实命中、不得回填 1.0）
  - FIX3 VectorBackfill 向量自愈：零范数/跨点重复的退化向量在 run_once 中识别并以 DB 内容
    重嵌入修复；重嵌入仍退化的不落库
out_of_scope:
  - chat_model=qwen3:8b 空挂配置（主人已裁定不纠结；仅文档记录）
  - settings 明文 Key 复核（已复核：/api/settings 不回显，无修复项）
  - ffprobe/Obsidian 环境补装、备份/验收报告为 0（沙箱预期）
forbidden: 不改记忆算法与蒸馏提示词；不动 Vault/Production；不改扫描只读边界；
  不删除既有测试或断言；live 仅限隔离验收实例 8766
verification: RED 先行（三个新测试在旧代码上失败）→ GREEN → 上述三文件 focused 全绿 →
  cargo/npm 不涉及（纯 Python）→ 重建 sidecar → 整包重装 → 真机复验
  （新扫描导入恢复、召回探测、记忆状态刷新）→ 验收文档同步


## 0A. 上一 focused runtime 任务（停止继续扩张）

```yaml
task_id: OWNER_MEMORY_DETAIL_RELEASE_FULL_REPAIR_RUNTIME_GROUP
status: IDLE
execution_mode: FOCUSED_RUNTIME_REGRESSION_REPAIR_ONLY
repository: wangduoyu001/lingji
product_branch: codex/owner-memory-detail-drilldown
baseline_commit: eca5b811
product_commit: fde399849eb6b440ef37c977ff76ac280fdd80ab
product_pr: NONE_NOT_A_RELEASE_GATE
release_gate: NOT_A_RELEASE_GATE
artifact_name: NOT_APPLICABLE
report_path: docs/TEST_REPORTS/OWNER_MEMORY_DETAIL_RELEASE_FULL_REPAIR_RUNTIME.md
live_8766_8767_forbidden: true
install_forbidden: true
owner_data_forbidden: true
full_release_forbidden: true
```

本任务不再作为当前开发入口。已完成的 promotion recovery 与 structured evidence 隔离修复保留；
packaged automatic-memory clean-root 双轮尚未形成最终收口证据，已转入当前主人体验任务，作为
“真实导入可靠性”阻断门禁继续验证。原任务范围为：promotion recovery case 06、
structured evidence lexical 两个顺序相关节点、packaged automatic-memory clean-root 双轮流程。
必须先逐项复现并定位产品缺陷、测试隔离、时序或资源泄漏的真实根因；不得修改断言以掩盖
失败，不得删除或 skip 测试。禁止触碰记忆详情 UI、Task4R2 质量语义、Production/Vault、
真实聊天、live 服务、安装、full/release。修复后只运行指定节点、直接调用方小矩阵、
compile/diff/acceptance-sync/handoff，并如实记录 RED/GREEN 与未处理边界。

## 0A. 最近 focused 修复任务（已收口）

```yaml
task_id: OWNER_MEMORY_DETAIL_RELEASE_FULL_REPAIR_GROUP_1
status: IDLE
execution_mode: FOCUSED_TEST_AND_ENVIRONMENT_CONTRACT_REPAIR_ONLY
repository: wangduoyu001/lingji
product_branch: codex/owner-memory-detail-drilldown
baseline_commit: b3427d26b6b192461290a167495c8720ff4835f4
product_commit: 0b35123402dbda57b2ab19896a0b6d95d3cbaefa
product_pr: NONE_NOT_A_RELEASE_GATE
release_gate: NOT_A_RELEASE_GATE
artifact_name: NOT_APPLICABLE
artifact_id: NOT_APPLICABLE
report_branch: acceptance/owner-memory-detail-release-full-repair-group1
report_path: docs/TEST_REPORTS/OWNER_MEMORY_DETAIL_RELEASE_FULL_REPAIR_GROUP1.md
public_summary_path: NOT_APPLICABLE
public_hashes_path: NOT_APPLICABLE
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
acceptance_root: NOT_APPLICABLE
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
live_8766_8767_forbidden: true
install_forbidden: true
owner_data_forbidden: true
full_release_forbidden: true
```

本任务只收口上轮 full 的五项测试/环境契约：当前 Python 解释器传递、真实
PowerShell entry-only 解释器传递、Desktop `dist/index.html` 实际 JS 入口契约，以及
Attention 当前 `/api/work/pending-actions` + `usePollingResource` 契约。禁止修改记忆详情产品、
降低安全/业务断言、删除测试或改为 skip；禁止运行 full/release/live、安装工具或读取
Production/Vault/真实聊天和主人数据。必须先复现 RED，再做最小修复，最后运行五个失败项
及直接回归、compile/static/diff/acceptance-sync/handoff。

本任务已按范围收口：产品/测试提交为
`0b35123402dbda57b2ab19896a0b6d95d3cbaefa`。五个指定节点为 `5 passed`；直接回归为
`37 passed, 11 deselected, 2 warnings`，11 个 deselected 是本组明确不处理的 Task4R stage-exception
参数矩阵。本结论不表示 full/release 已通过，上轮 release 仍是 `COMPLETED / FAIL`。

## 0A. 最近 release gate（已收口）

```yaml
task_id: OWNER_MEMORY_DETAIL_DRILLDOWN_RELEASE_GATE
status: IDLE
execution_mode: RELEASE_VALIDATION_ONLY
candidate_label: OWNER_MEMORY_DETAIL_DRILLDOWN_RELEASE_CANDIDATE_4F0D2A77
release_gate: RELEASE_INCLUDES_FULL
repository: wangduoyu001/lingji
product_pr: NONE_NOT_A_RELEASE_GATE
product_branch: codex/owner-memory-detail-drilldown
product_commit: 4f0d2a7738c6cba12d0766cb7ed6b38cbd32e543
product_tests_commit: 81256c4242a6bb8062f1b591832a3313948e9ff9
artifact_name: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
artifact_id: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
artifact_workflow_run_id: LOCAL_ONLY_RELEASE_VALIDATION
artifact_zip_sha256: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
dmg_sha256: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
report_branch: acceptance/owner-memory-detail-drilldown-release-gate-4f0d2a77
report_path: docs/TEST_REPORTS/OWNER_MEMORY_DETAIL_RELEASE_GATE.md
public_summary_path: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
public_hashes_path: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
acceptance_root: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
acceptance_data_root: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
acceptance_vault_root: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
acceptance_source_root: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
acceptance_backup_root: NOT_APPLICABLE_RELEASE_VALIDATION_ONLY
acceptance_evidence_root: /tmp/LingJiAcceptance/owner-memory-detail-release-gate
production_roots_untouched: true
backup_before_install_required: false
whole_bundle_replace_required: false
rollback: no installation or runtime mutation is permitted
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
product_code_changes_forbidden: true
secret_export_count_required: 0
production_pollution_count_required: 0
live_8766_8767_forbidden: true
install_forbidden: true
owner_data_forbidden: true
full_is_included_by_release: true
duplicate_full_run_forbidden: true
power_shell_scope: isolated portable arm64 macOS tar.gz under acceptance_evidence_root/tooling
python_command: python3
keep_app_and_sidecar_open_for_owner: false
owner_observation_required: false
preserve_old_failed_evidence: true
quality_gate: automatic-memory-4r2-readiness MEASURED_FAIL; release must not be reported PASS if blocked
```

本轮是纯 release validation gate（已 `COMPLETED / FAIL`）：候选固定为当前 HEAD `4f0d2a7738c6cba12d0766cb7ed6b38cbd32e543`，产品/测试代码提交为
`81256c4242a6bb8062f1b591832a3313948e9ff9`，不修改产品代码，不创建 Artifact，不安装，不启动 Desktop/sidecar，
不接触 live 8766/8767、Production/Vault、真实聊天/数据库或主人数据。`scripts/validate.ps1 -Mode release` 自含
full，不得另行重复运行 `-Mode full`。由于当前 Mac 没有系统 `pwsh`，只能在新的隔离临时根下载并记录微软官方
PowerShell GitHub release 的 arm64 macOS portable tar.gz URL、版本和 SHA256，解压后以该绝对路径执行真实
PowerShell；不得全局安装、修改系统 PATH 或用 Python 冒充 PowerShell。执行后必须确认无服务监听，并只读取
`output/validation/latest-summary.json|md` 与失败日志尾部；automatic-memory-4r2-readiness 已知 measured fail
时必须如实记录 release 阻断，不得写 PASS。

## 0. 最近收口任务（当前无 ACTIVE 任务）

```yaml
task_id: OWNER_MEMORY_DETAIL_DRILLDOWN_IMPLEMENTATION
status: IDLE
execution_mode: FOCUSED_PRODUCT_IMPLEMENTATION_ONLY
candidate_label: OWNER_MEMORY_DETAIL_DRILLDOWN_IMPLEMENTATION_BASELINE
release_gate: NOT_A_RELEASE_GATE
repository: wangduoyu001/lingji
product_pr: NONE_NOT_A_RELEASE_GATE
product_branch: codex/owner-memory-detail-drilldown
product_commit: c7388c08b495b1fbf1598358d76fe4176552f9ab
artifact_name: NOT_APPLICABLE_FOCUSED_ONLY
artifact_id: NOT_APPLICABLE_FOCUSED_ONLY
artifact_workflow_run_id: LOCAL_ONLY_FOCUSED_IMPLEMENTATION
artifact_zip_sha256: NOT_APPLICABLE_FOCUSED_ONLY
dmg_sha256: NOT_APPLICABLE_FOCUSED_ONLY
report_branch: acceptance/owner-memory-detail-drilldown-implementation
report_path: docs/TEST_REPORTS/OWNER_MEMORY_DETAIL_DRILLDOWN_IMPLEMENTATION.md
public_summary_path: NOT_APPLICABLE_FOCUSED_ONLY
public_hashes_path: NOT_APPLICABLE_FOCUSED_ONLY
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
acceptance_root: NOT_APPLICABLE_FOCUSED_ONLY
acceptance_data_root: NOT_APPLICABLE_FOCUSED_ONLY
acceptance_vault_root: NOT_APPLICABLE_FOCUSED_ONLY
acceptance_source_root: NOT_APPLICABLE_FOCUSED_ONLY
acceptance_backup_root: NOT_APPLICABLE_FOCUSED_ONLY
acceptance_evidence_root: .superpowers/sdd/2026-08-31-owner-memory-detail-drilldown
production_roots_untouched: true
backup_before_install_required: false
whole_bundle_replace_required: false
rollback: no installation or runtime mutation is permitted; revert only this focused implementation branch if explicitly authorized
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
product_code_changes_forbidden: false
secret_export_count_required: 0
production_pollution_count_required: 0
quality_gate: MEASURED_FAIL_NOT_RELEASE_READY_DEFERRED
keep_app_and_sidecar_open_for_owner: false
owner_observation_required: false
preserve_old_failed_evidence: true
```

本任务负责的 Owner memory detail drilldown 产品代码、测试与验收文档已完成 focused 收口，具体实施计划为
`docs/superpowers/plans/2026-08-31-owner-memory-detail-drilldown.md`，已收束为 3 个实现任务 + 1 个
收口任务，共 4 个任务。允许修改产品代码，但
本轮仅运行 focused/product implementation 和合成 fixture；未启动 live 8766/8767、未进行 package/install、
未读取真实聊天/Vault/数据库、未操作主人数据。不得据此宣布主人体验/release/Phase 1 PASS。

范围固定为：四项普通导航和 current-only 列表不变；单卡详情通过现有 `/cards/{id}`、bounded
`/memories/{id}`、`/vector`、`/source` 与唯一新增的
`/api/memory/inspector/memories/{memory_id}/evidence` 按需显示 canonical 正文、当前结论、稳定
时间线、来源原文、raw/structured/vector/permanent 状态与主人处理语义。evidence 默认 20、最大
50，每 item excerpt<=240/content<=4000、单页 content<=24000 并带 truncated；不能暴露无界
`memory_evidence()`；不新建数据库、projector、状态源或 DELETE。`/memories/{id}` 仅可增加
`chunk_limit`/`max_chars`/`cursor` 且保留原 response fields；conversation-only 由前端依据
card kind/source conversation_id 显示“这是原始会话，尚未形成长期记忆”并使用现有 conversation
messages 分页，不调用 canonical。

旧 Mac 候选 `OWNER_UI_SOURCE_FILTER_REPAIR_4CE1E00A`（product SHA
`4ce1e00acb17bc5e4e4c183f58d30551ef76b101`）明确记录为 `COMPLETED / FAIL`，不再 ACTIVE；其
failure evidence、backup、fixture、DB、logs 与 Acceptance 根必须原样只读保留，不能复用或冒充
通过。该旧候选的主人结论为 `OWNER_UI_REPAIR_REQUIRED`，质量事实仍为
`MEASURED_FAIL / NOT_RELEASE_READY`。

本任务产生的新产品 SHA 为 `c7388c08b495b1fbf1598358d76fe4176552f9ab`；只有该 SHA 通过根代理的
full/release 门禁后，才允许创建新的 Mac acceptance task。新任务须使用新隔离根、同 SHA arm64 全包构建/安装和 Computer Use 全页遍历，至少打开五种
不同类型记忆并展开多个来源原文；主人明确确认前不得写完成。

## 1. 最近一次任务

```yaml
task_id: PR88-M5-OWNER-WORKBENCH-V4-BD1E7A17
status: IDLE
execution_mode: MACOS_M5_PHYSICAL_REACCEPTANCE
repository: wangduoyu001/lingji
product_pr: 88
product_branch: feature/owner-autopilot-ui-codexpp
product_commit: bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9
artifact_name: lingji-macos-arm64
artifact_id: 9258682849
artifact_workflow_run_id: 31928631105
artifact_zip_sha256: c26408c350bf35701bdf6aa97e75f65e7bead42fb6ed92d11838334274e1a888
dmg_sha256: a5d54cba4f99411541527be7230d568f32a8fba90efed14ff9756df6b393bb46
report_branch: acceptance/pr88-m5-owner-workbench-v4-bd1e7a17
report_commit: 5793e4ae22e17d1f4db2c57ecc66bf18ec65af2e
cleanup_receipt_commit: 3011d796ff1bb5bff7d5e37c24e0c6236ee51d34
report_path: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_bd1e7a17.md
public_summary_path: docs/TEST_REPORTS/evidence/PR88_M5_OWNER_WORKBENCH_V4_SUMMARY_bd1e7a17.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR88_M5_OWNER_WORKBENCH_V4_HASHES_bd1e7a17.txt
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
pr_receipt_comment: 5306178636
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
product_code_changes_forbidden: true
same_sha_artifacts_required: true
secret_export_count_required: 0
production_pollution_count_required: 0
retry_rejected_artifact: false
```

## 2. 最终结论

```text
status: COMPLETED
verdict: FAIL
merge: DO NOT MERGE
PR #88: KEEP DRAFT
Artifact 9258682849: DO NOT RETRY
```

技术项通过：精确产品/Artifact 身份、arm64、strict codesign、whole-bundle replace、Acceptance 隔离、认证与 Secret 边界、两轮 Runtime 精确生命周期、分页终点、Production pollution=0、失败回滚与清理。

主人体验失败：

- 首页声称存在待确认候选，但“需要我”显示 `0` 个真实待办，事实链互相矛盾；
- “工作”履历为 `0`，无法说明真实做了什么、结果、下一步和执行者；
- `Cmd+K` 的真实“记住”提交失败，没有进入可追踪 Capture 流程；
- “记忆”只有泛化标题，缺少可读正文/摘要与可验证来源链；
- 主动发现只能看到静态说明，看不出接管了什么、已执行什么、下一步自动做什么；
- Window Recovery 三条路径未全部获得主人肉眼确认，保持 `NOT_TESTED`。

主人总评：**看不出灵机实际做了什么、接管了什么，与旧版没有明显差异。**

## 3. 当前禁止事项

以下 macOS Artifact 均永久禁止重跑：

```text
9258682849 / bd1e7a17
9250384637 / 1d99d10c
9249367672 / f3cba413
9224368022 / 2c96b3ec
9102748834 / 171091fe
```

当前没有本机验收任务。下一轮必须先完成新的产品级真实对象链修复，至少形成：

```text
真实资料 / 任务对象
→ 自动发现或主人输入
→ 真实执行事件
→ 可读执行结果
→ 下一动作 + 下一执行者
→ 真实待办（仅在需要主人时）
→ 可读永久记忆正文 / 摘要 + 可验证来源
```

首页、需要我、工作、记忆、Capture 必须读取同一条事实链，不允许再通过各自的投影/模板拼出互相矛盾的状态。

完成新的产品代码、focused/full/release CI、新产品 Commit、同 SHA macOS/Windows Artifact 与哈希锁定后，才允许创建新的 `ACTIVE` M5 任务。

不得在 acceptance 分支修改产品代码；历史报告只作为证据，不承担当前任务职责。
