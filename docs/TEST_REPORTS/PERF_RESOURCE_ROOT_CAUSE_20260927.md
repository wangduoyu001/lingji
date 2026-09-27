# PERF_RESOURCE_ROOT_CAUSE_20260927 真机验证报告

- 日期：2026-09-27
- 分支：`codex/owner-source-intake-mac-repair`（HEAD 至 `6c04e65d`）
- 诊断方法：`sample` 调用栈采样 + SQLite `EXPLAIN QUERY PLAN` + lsof + 日志频率统计
- sidecar：PyInstaller 重打包，可执行 SHA-256 `78732387fc7ef120dd86f54608a0cf65cd6384335c7c8bde028c65393af28d61`，已部署 `/Applications/灵机.app/Contents/Resources/lingji-core.exe` 并重启（新 PID 13751，127.0.0.1:8766 监听正常）

## 已实现并真机验证

| 改动 | commit | 验证 |
|---|---|---|
| A1 溯源三键生成列+部分索引、批量预取、孤儿 SQL 化、输入指纹回退 | `5aea694e` | 新增回归 4 例全绿；相关测试 28 过 1 挂（基线既有 `test_formal_mcp_search_entry`）；真机稳态 CPU 归零 |
| A2 discovery 三端点 60s TTL 缓存 + MemorySourcesPage 轮询 8s→30s | `42cae364` | 缓存单测 3 例；真机日志 14 行/分钟（改前 120-300 行/分钟，降 90%+ 达标） |
| B1 会话价值门（value_gate.py + admit 接入 + JSONL 审计） | `34777239` | 单测 6 例；存量 124 过 2 挂（与基线完全一致）；生产默认开启、测试路径经 getattr 缺省关闭 |
| B2 回填计数预检 fast-path | `cef08131` | 回归测试覆盖（含计数漂移回退修复路径） |
| B3 acceptance 集合归档移除 | 本轮 | 已归档 `backups/lingji-acceptance-qdrant-collection-20260927.tar.gz` 并移除；**被启动逻辑重建（12K 空目录）**，创建点待查，内存影响趋零 |

## 真机四指标（对照任务单验收线）

| 指标 | 改前（旧 sidecar PID 852） | 改后（新 sidecar PID 13751） | 结论 |
|---|---|---|---|
| 空闲 CPU | 持续 96-98% 单核，累计 100+ 分钟 | **稳态 0.0%**（四连采样；启动后偶发 43% 为一次性批处理尾巴） | ✅ 达标 |
| 内存（RSS） | 1.74 GB | **810 MB** | ✅ 达标（<1GB） |
| 轮询日志频率 | 每 0.2-0.5s 一行（120-300 行/分钟） | **14 行/分钟** | ✅ 降 90%+ 达标 |
| 混库守卫 | acceptance 集合驻留生产 | 移除后被启动逻辑重建（12K 空） | ⚠️ 部分达成，创建点待查 |

功能验证：重启后 MCP `search_memory` 词法通道正常返回（semantic: degraded 与重启前一致）；8766 认证、control-center、Desktop 轮询链路全部正常。

## 已实现未真机单测 / 仅规划 / 已知限制

- **A1 收尾（下轮首选）**：content-addressed 增量重构。当前每批 ingestion 仍全量重刷（带索引+批量预取，主热点已消）；read model 为全量重建型（DELETE 三表重插），updated_at 水位不成立，方案已写任务单。
- **C-big（下轮）**：vector_backfill 死代码 SQL 重写（手动触发路径，非热点）。extraction_jobs.status 索引经核实已由 `idx_extraction_jobs_due` status 前缀覆盖，无需新建。
- **B1 UI 增强（下轮）**：skipped 审计的 UI 展示端点、RuntimeSettingsStore 阈值调节、manifest_status=skipped:value-gate 的 UI 值域核对。
- acceptance 集合重建点待查（config.py `acceptance_qdrant_collection` 是唯一字面量引用，创建经由 workspace 配置链）。
- 回滚：`git revert` 四个 perf/feat 提交并重新打包即可；B1 有 `value_gate_enabled` 开关；数据层（生成列/索引/归档）均为加法或已归档。

## 收尾批（PERF_RESOURCE_CLOSEOUT_20260927B，2026-09-27 晚）——代码完成，真机验收 PARTIAL

分支 `codex/owner-source-intake-mac-repair`，HEAD `45c5bb59`。

### 已实现并本机测试（未全部真机达标）

| 改动 | commit | 验证 |
|---|---|---|
| A1 收尾：sync_structured_evidence 两阶段 content-addressed 重构（水位机制删除、title 漂移修复、空内容归档、真实全量 count meta） | `c24ab5b6` | 新增回归 4 例；相关 27 过 1 挂（基线既有）；2000 消息重放 0.0247s 零 chunk |
| B1 收尾：阈值进 RuntimeSettingsStore（owner override > 静态配置 > 目录默认）、skipped_by_value_gate 值域、skipped/rescan 两端点 | `f60fd015` | 新增 5 例；相关 38 过（曾打破 3 个存量 api 测试，precedence 修复后全绿） |
| B3 守卫：客户端池首次打开注销非本工作区空集合注册 | `2d7e9d1c` | 5 例回归；**真机实锤生效：重启后 meta.json 仅剩 lingji_memory_production，acceptance 注册与目录消失** |
| C：vector_backfill payload-only 增量 diff（deep_check 显式体检）、死 SQL 删除、集合创建移出循环 | `ea9e8703` | 9 例全绿（含既有退化治理用例显式 deep_check） |
| E：dir-usage TTL 缓存（错误假设） | `3fb2f1d6` → revert `45c5bb59` | 回滚，见下 |

### 真机复测（新 sidecar SHA `02bf7346…`，PID 20282，8766 正常）

- ✅ B3：acceptance 集合不再被重建（守卫自动注销注册，上轮遗留问题闭环）。
- ✅ A1 单元基准：重放零 chunk（改前每批 ingestion 全量重 chunk 21k）。
- ❌ 空闲 CPU <5% 未达标：队列空、日志静默下仍持续 23-33%（四连窗口）。
- ❌ 内存 <1GB 未达标（活动期 RSS 峰值 2GB；前一日构建曾稳定到 108MB，波动原因未明）。
- ⚠️ E 修复试错记录：假设 reconciliation 的 raw stat 扫描是热点 → TTL 缓存无改善 → 回滚。真实 raw=`storage/raw`（3.05GB/507 文件）。

### 遗留热点证据链（下轮首选诊断）

1. sample 采样：一个 worker 线程 ~45% 采样在 SHA256（EVP_update/sha256_block_armv8）。
2. 事件：structured_ingestion_completed 14 次/10 分钟、distill_failed 4、automatic_memory_reconciliation 92 次/10 分钟（不同时段波动）。
3. 队列空、capture 因 raw 满被拒——热不在采集，疑似重复再提取 × read model 全量重建 × 提炼重试复合。
4. 工具缺口：py-spy 本机离线安装失败（No matching distribution），下轮需联网安装后 `py-spy dump --pid <pid>` 抓 Python 层栈。

### 主人待决策

- **raw 存储满**：storage/raw 3.05GB / 上限 3GiB（automatic_memory_raw_max_bytes），新采集被拒。需主人决定：清理（旧快照归档后删）或提高上限。代理不擅自清理主人数据。

### 基线既有失败（与本轮无关，如实记录）

test_formal_mcp_search_entry、test_reconciliation_runs_after_event_silence、test_reconciliation_admits_once_and_persists_report、test_memory_vector_and_coverage_endpoints_return_shared_snapshot。

回滚：`git revert` c24ab5b6/f60fd015/2d7e9d1c/ea9e8703 并重新打包；B1 有开关；数据层加法可保留。
