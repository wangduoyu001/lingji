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
