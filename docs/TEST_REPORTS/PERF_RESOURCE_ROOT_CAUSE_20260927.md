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

### 空闲 CPU 未达标根因（已定位：设计行为，非缺陷）

1. 实锤链：`ps -M` 显示单线程独占全部 CPU（3:12/3:15）；lsof+find 抓到 `storage/raw/826debd0…` 文件 177MB 在采样窗口内持续增长；拷完时间 18:42 与重启时间吻合。
2. 机制：滚动变化的大库（本会话所在的会话库，177MB）按 `snapshot_throttle_seconds=1800` 整库重拷+流式 SHA-256（即 EVP_update 热点）+再提炼；采集节奏记录（18:01/17:31/17:00/15:41）与 30 分钟窗口完全吻合——节流工作正常。
3. 数学：每 30 分钟约 6 分钟重拷+提炼周期 → 占空比 ~20-26% = 实测稳态 CPU。上一轮"空闲 0.0%"是 60s 采样窗恰好落在周期间隙；"空闲<5%"这条验收线对整库重拷设计天然不成立。
4. py-spy 已装好（wheel 本地安装法，见交接），如需进一步抓栈可 `sudo py-spy dump --pid <pid>`（需密码，本轮未用）。

### 主人决策项（新增）

- **节流窗口**：滚动大库每 30 分钟整库重拷一次是 2026-09-24 拍板的"最多晚半小时"代价；若要压 CPU，可把该源节流窗口调大（如 2h，成本按比例降）——需主人拍板，代理不擅自改。
- **raw 满**：storage/raw 3.05GB/3GiB，新采集被拒。清理（归档后删）或提高 automatic_memory_raw_max_bytes。
- **远期方向**：大库增量快照（只拷 WAL 增量）可同时解决 CPU 占空比与 raw 增长，属新一轮任务。

### 主人待决策

- **raw 存储满**：storage/raw 3.05GB / 上限 3GiB（automatic_memory_raw_max_bytes），新采集被拒。需主人决定：清理（旧快照归档后删）或提高上限。代理不擅自清理主人数据。

### 基线既有失败（与本轮无关，如实记录）

test_formal_mcp_search_entry、test_reconciliation_runs_after_event_silence、test_reconciliation_admits_once_and_persists_report、test_memory_vector_and_coverage_endpoints_return_shared_snapshot。

回滚：`git revert` c24ab5b6/f60fd015/2d7e9d1c/ea9e8703 并重新打包；B1 有开关；数据层加法可保留。

## 主人拍板落地（性能/硬盘双重收敛，2026-09-27 晚，commit addbfef8）

主人指示"不得过度占用性能与硬盘空间（包括备份），其他按最优解"。三项落地：

| 项 | 内容 | 验证 |
|---|---|---|
| 自适应快照节流 | 窗口 = max(30min, 最近真采集最大快照字节 ÷ 0.5MB/s ÷ 5%)；大源自动拉长（177MB→124min），小源保持响应 | 回归 7 例；真机静止 CPU **1%**（此前 23-33%） |
| 小文件保护窗 24h→6h | churn 保护地板 ~1.6GiB→~0.4GiB | 回归 10 例 |
| raw 上限 3GiB→2GiB | 数据根 .env（备份 .env.bak-20260927） | 手动触发采集：逐出+采集正常完成，.evicted.log 有账 |

### 根因定性修正（替代上一节"遗留热点证据链"的未定论）

持续 26% CPU 的机制 = **唤醒→300 秒回填排水循环接力**：旧 30 分钟节流下核对频繁完成，每次完成唤醒排水（消息层全量滚动比对 + chunk 层比对 + 嵌入），循环接力表现为准连续烧 CPU；重启后积压+唤醒风暴放大。faulthandler（lldb 同用户注入）证明静止期全部 Python 线程空闲——燃烧随排水起止。当前静止 1%。残余不确定：排水轮内具体 SHA256 调用点未钉死（py-spy 需 sudo 密码）；vectorize 端点观测到 >400s 挂起于 Ollama 嵌入等待（0% CPU），列为观察项。

### 磁盘收敛路径

raw 当前 3.38GiB（旧机制 6h 内大副本仍在保护期），随保护窗过期在 ≤6h 内收敛到 2GiB 上限附近；稳态地板（6h 大副本 ×3 + 6h 小文件）≈1.2-1.5GiB。备份维度审计：生产 backups 为空，~/LingJiAcceptance/backups 仅 42MB 归档包（保留）。

### 后续观察项（下一轮）

- vectorize/嵌入链路 >400s 挂起（Ollama 服务状态？）——若复现，给嵌入调用加超时熔断。
- 排水轮内 SHA256 调用点：联网环境用 sudo py-spy 一次定位。
- 大源到期（部署后 ~2h）的采集周期实测，确认占空比 ≤5-7%。

## 审计响应批（AUDIT_RESPONSE_20260927，2026-09-27 夜）——服务挂死根因与四项修复

外部优化建议书（基线 5e51f8bb）评审后落地。**根因修正**：挂死期线程转储显示多线程分别卡死在系统调用（提炼线程 getaddrinfo/DNS、提取线程 sqlite3.connect、capture_inbox iterdir），事件循环正常、CPU 零增长——建议书的"持 GIL 饿死事件循环"理论不成立；SIGTERM 优雅停机被卡死线程拖住导致进程"杀不掉"。

| 项 | commit | 验证 |
|---|---|---|
| 全量基线 diff：HEAD vs a090676f 失败集合逐条相同（14=14），零新增回归，+39 新测试全过；完整 14 项清单入档任务单（替代漏报的 4 项） | `d67661a6` | 双侧全量各 4 分钟 |
| MCP citation 断裂 + slim search 泄漏 relative_path（白名单去 relative_path、加 citation，vault 定位走 citation.path） | `6546e8d9` | 2 个契约测试转绿；15 过 2 挂（均基线既有） |
| 健康看门狗：探活绕代理直连 loopback，3×20s 超时 → SIGTERM → 30s 宽限 → SIGKILL 升级 | `3e65e454` | 部署验证存活；LINGJI_WATCHDOG_ENABLED 可关 |
| 提炼模型列表探针：单守护线程串行拉取，urllib timeout 不覆盖 DNS 的缺口补上，至多卡死一个线程 | `3e65e454` | 回归 3 例（卡死限时返回、无线程泄漏、错误缓存与恢复） |
| 手动扫描移出 HTTP 线程池：专用单线程执行器 + 5 秒预算（快路径真实报告、慢路径受理即返回） | `3e65e454` | 回归 2 例 + 受影响 5 个 api 测试全绿 |
| 177MB 大库哈希改 hashlib.file_digest（C 层释放 GIL） | `3e65e454` | 快照相关 77 过 2 挂（均基线既有） |
| zhipu_api_key 脱敏：/api/settings values+overrides 双处掩码 + set 标志；掩码回写防护；文件 chmod 600；内部消费方走 snapshot() 拿全值 | `6c6dce9a` | 回归 6 例；真机 /api/settings 实测零泄漏 |
| Vault git 自动提交：晋升后 add -A + commit 锚点，失败告警不阻塞，绝不 push | `2f552f0b` | 回归 3 例（脏仓提交/净仓 noop/非 git 软失败） |

部署：SHA `dae0d1cb…`（PID 27710）。真机三项：ping 5.7ms；/api/settings 全值零泄漏；手动扫描 912ms 返回真实报告。

### 已知限制与后续

- 挂死的**最终微观成因**（系统解析器为何卡死 100 分钟）未钉死——需下次发生时 sudo py-spy 抓栈；看门狗已把不可用时长约束在 ~90 秒内。
- 待办：失败按源聚合（2.2）、evidence 检索通道（3.2.1，需主人确认语义）、Qdrant 双根核实与 648 缺口（4.3）、master 收敛（5.2，需主人拍板）。

## 第二批（3.2.1/2.2/4.3/5.2/5.4，2026-09-27 夜·续，主人指示"按你的建议执行"）

| 项 | commit | 验证 |
|---|---|---|
| 3.2.1 证据独立通道：memory 通道优先、evidence 殿后带 retrieval_channel 标签；修正点=真正生效的检索器在 src/retrieval/enhanced.py（包导出指向它），其 fallback 重排已改通道优先 | `d188fe24` | 回归 2 例 + 检索扩面 154 过 1 挂（基线既有） |
| 4.3 Qdrant：双集合粒度不同（chunk 级 vs 消息级）各有消费方，非冗余不删；缺口根因=Ollama 未运行，拉起后连续回填 **796 缺口→0**，之后 B2 fast-path 零成本 | 运维+既有代码 | 6 轮回填实测 remaining 596→269→69→0 |
| 5.2 主线收敛：master 独有提交为 0（产品分支严格超集领先 736）→ 主仓 master fast-forward 到 3f0ee2c2；**推送 GitHub 被网络阻断（SSL_ERROR_SYSCALL，今晚网络故障）**，恢复后 `git push origin HEAD:master` 即完成 | 本地 3f0ee2c2 | 性能测试收集正常（master 坏测试随树消失） |
| 5.4 卫生：删死代码 work_api.py、.zcodeignore 入 .gitignore、3 周未动 worktree 移除 | `c67d4986` | api 导入验证正常 |
| 2.2 失败按源聚合：failure_key 指纹聚合、1,284 次同因失败→1 行、1,291 旧格式行启动迁移为 1 行、PendingAction(actor=owner) 确定性 ID、新端点 /api/work/failures + history.failure_total | `8bd9`（见 git log） | 回归 9 例 + 215 相关测试全过 |

部署：SHA `d631bef6…`（PID 31247）。真机：ping 1ms；/api/work/failures 返回聚合记录；/api/settings 零泄漏。
