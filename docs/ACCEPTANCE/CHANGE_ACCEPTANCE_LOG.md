# 验收要求变更记录

> 每个包含产品代码、运行时、UI、连接器、数据链路、脚本、依赖或发布流程变化的 PR，都必须在本文件顶部追加一条记录。
>
> 记录描述“本次代码变化后，验收必须新增、修改或回归什么”。历史记录不得删除，只能更正明显错误并说明原因。

## 2026-08-26 · Phase 1 Automatic Memory · Task 2 fix round 8 · unknown owned snapshot retention

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`78979cbf3852b22a9a8152f35f115eae3adf3f18`
- 影响模块：snapshot staging cleanup parsing and unknown owned-file retention
- 风险等级：P1
- 用户可感知变化：合法但无法关联到现有 scan 的 owned snapshot 临时文件不再因 24 小时 age 策略被删除；超长或异常 scan/lease/token 文件名按 unknown owned 保留。普通 legacy `.snapshot-*.tmp` 仍按 24 小时阈值清理。
- 数据或安全边界变化：只有明确找到 scan 且状态为 completed/cancelled/failed/paused，或当前 running lease 已明确过期时，owned staging 才允许回收；scan 查询异常、缺失或 owner 编码不可信均 fail-closed 保留。

### 新增或修改的自动验收

- [ ] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_extraction_queue.py tests/test_extraction_worker.py`：71 passed，覆盖不存在 scan 的有效编码 stale owned temp 保留、超长 token stale owned temp 保留、malformed/异常 DB、lease expiry、legacy 24h 与既有 Task 2 lease/crash/idempotency 边界。
- [ ] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_hardening.py tests/test_extraction_worker.py tests/test_structured_ingestion.py`：104 passed，Task 1/extraction/queue/worker 回归（含 1 个既有 FastAPI deprecation warning）。
- [ ] `./.venv/bin/python -m py_compile src/automatic_memory/snapshot.py src/automatic_memory/checkpoint.py src/extraction/pipeline.py src/extraction/queue.py src/extraction/sink.py src/storage/state_db.py`、`git diff --check`、`./.venv/bin/python scripts/check_acceptance_sync.py`、`./.venv/bin/python scripts/check_local_execution_handoff.py`。

### 回归项与边界

- [ ] 保持普通 legacy `.snapshot-*.tmp` 24 小时策略、活跃跨来源保护、protected snapshot job 边界、lease/crash/idempotency 行为不变。
- [ ] 不扩展 Task 3 或其他架构；不新增数据库、队列、raw archive、watcher、适配器或消费者。
- [ ] Full-suite 既有 Desktop assertion mismatch 与缺少 `python` executable 的 `test_second_brain` baseline failures 不修改、不掩盖；内部 SDD 报告继续 ignored。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK2_FIX8_`
- 本轮调试临时目录 `.tmp-debug-19294/` 已清理；pytest 临时授权 root、SQLite、raw、queue 与 crash marker 自动清理。
- 回滚：回滚产品 Commit `78979cbf3852b22a9a8152f35f115eae3adf3f18`，不触碰主人数据。

### 最终报告

- 报告路径：本地调度报告继续由 `.superpowers/` 忽略；正式证据为本条目与测试命令输出。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 2 fix round 7 · fail-closed lease expiry cleanup

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`f0b639206f3274ade7ae115c2758c21006e69196`
- 影响模块：snapshot staging cleanup lease-expiry parsing and fail-closed ownership handling
- 风险等级：P1
- 用户可感知变化：owned snapshot temp 清理不再依赖时间字符串排序；带 offset、`Z` 和 UTC 的明确过期 lease 才会回收，naive/非法/查询异常均保守保留。格式异常的 `.snapshot-owned-*` 不会因 24 小时策略被误删；普通 legacy `.snapshot-*.tmp` 仍按 24 小时阈值处理。
- 数据或安全边界变化：`lease_expires_at` 使用 `datetime.fromisoformat` 后统一转换 UTC；无法证明 owner、scan、lease 或 expiry 的 owned temp 保留，避免误删活跃复制中的潜在敏感 staging。

### 新增或修改的自动验收

- [ ] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_extraction_queue.py tests/test_extraction_worker.py`：69 passed，覆盖 offset/`Z`/UTC/naive/非法 expiry、malformed owned temp、StateDatabase 异常 fail-closed、活跃跨来源 temp 和 legacy 24 小时清理。
- [ ] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_hardening.py tests/test_extraction_worker.py tests/test_structured_ingestion.py`：47 passed，Task 1/queue/extraction 回归。
- [ ] `./.venv/bin/python -m py_compile src/automatic_memory/snapshot.py src/automatic_memory/checkpoint.py src/extraction/pipeline.py src/extraction/queue.py src/extraction/sink.py src/storage/state_db.py`、`git diff --check`、`./.venv/bin/python scripts/check_acceptance_sync.py`、`./.venv/bin/python scripts/check_local_execution_handoff.py`。

### 回归项与边界

- [ ] Full-suite：632 passed，11 skipped；仅保留既有 Desktop assertion mismatch 与缺少 `python` executable 的 `test_second_brain` baseline failures，未修改或掩盖。
- [ ] 保持 Task 2 收缩边界：不恢复 generic pipeline 的 snapshot claim/execute，不实现 Task 3 专用 consumer、staging/outbox、下游 visibility transaction。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK2_FIX7_`
- malformed/unknown/活跃 owned temp 保留；合法 expired owner temp 确定性回收；普通 legacy temp 仅按 24 小时阈值回收；不删除 raw 正式对象、其他组件 temp 或第三方文件。
- 回滚：回滚产品 Commit `f0b639206f3274ade7ae115c2758c21006e69196`，不触碰主人数据。

### 最终报告

- 报告路径：本地调度报告继续由 `.superpowers/` 忽略；正式证据为本条目与测试命令输出。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 2 fix round 6 · lease-owned snapshot staging cleanup

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit(s)：`a16d10c392ecc8c7ba2080c5ae3c3d6ab64791fa`, `58ae897111d4ee665e0a8cf1ba2e11c6e8694c58`
- 影响模块：existing snapshot staging cleanup and Task 2 concurrency/recovery tests
- 风险等级：P1
- 用户可感知变化：一个活跃 runner 的 snapshot temp 不会被另一个来源/runner 构造时误删；不同来源可并行完成且 raw/queue exactly-once 保持。
- 数据或安全边界变化：owned temp 文件名绑定 `scan_id + lease_id`，清理以现有 state DB lease/status/expiry 为权威；未知 fresh temp 默认保留，legacy stale temp 仅按 24 小时安全阈值回收。正式 raw 对象、其他组件 temp 与第三方文件不受影响。

### 新增或修改的自动验收

- [ ] `pytest -q tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_extraction_queue.py tests/test_extraction_worker.py`：58 passed，覆盖活跃 temp 跨实例保留、expired/dead/legacy-null lease 回收策略、unknown fresh/legacy stale、不同来源真实并发、revoke/异常清理、generic snapshot claim/execute 隔离。
- [ ] `pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_hardening.py tests/test_extraction_worker.py tests/test_structured_ingestion.py`：47 passed。
- [ ] `py_compile`、`git diff --check`、`python scripts/check_acceptance_sync.py`、`python scripts/check_local_execution_handoff.py`。

### 回归项与边界

- [ ] Full-suite：622 passed，11 skipped；仅保留既有 Desktop assertion mismatch 与缺少 `python` executable 的 `test_second_brain` baseline failures。
- [ ] 保持 Task 2 收缩边界：不恢复 generic pipeline 的 snapshot claim/execute，不实现 Task 3 专用 consumer、staging/outbox、下游 visibility transaction。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK2_FIX6_`
- 未知 fresh/活跃 temp 不删除；成功、失败、revoke、lease loss 的本轮 temp 由 capture 确定性清理；SIGKILL 遗留按 lease/年龄策略处理。
- 回滚：回滚产品 Commit(s) `a16d10c392ecc8c7ba2080c5ae3c3d6ab64791fa`、`58ae897111d4ee665e0a8cf1ba2e11c6e8694c58` 及其父实现提交，不触碰主人数据。

### 最终报告

- 报告路径：本地调度报告继续由 `.superpowers/` 忽略；正式证据为本条目与测试命令输出。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 2 fix round 5 · protected snapshot admission boundary

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`b0bc0cc2b15112b0cae203dee3af445fca2b33b7`
- 影响模块：existing extraction queue claim policy/pipeline boundary, short snapshot raw/queue authorization checks, secure snapshot source opening, raw sink validation, Task 2 race/recovery tests
- 风险等级：P0
- 用户可感知变化：通用 ExtractionPipeline 不会执行或 claim 内部 `automatic_memory_snapshot` 作业；普通 job 保持原行为。快照作业仍由 Task 2 runner 负责授权快照、content-addressed raw 和 existing queue admission。
- 数据或安全边界变化：移除包围文件/Vault/索引 callback 的长 SQLite 事务；raw commit 与 queue admission 各自使用短授权检查。revoke 仍在现有 `lingji_state.db` 原子取消 snapshot queued/retrying/running jobs；raw 与 queue 之间的孤儿 raw evidence 通过 scan 状态错误记录保留、但不进入 current retrieval。lease/heartbeat/manifest/no-follow race 修复保持。

### 新增或修改的自动验收

- [ ] `pytest -q tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_extraction_queue.py tests/test_extraction_worker.py`：54 passed，覆盖内部 snapshot 不 claim/不 execute、revoke cancel、短 TTL、心跳生命周期、no-follow source/raw race、双 runner 最终 completed 与强杀恢复。
- [ ] `pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_hardening.py tests/test_extraction_worker.py tests/test_structured_ingestion.py`：47 passed，Task 1/queue/extraction/pipeline 回归。
- [ ] `py_compile`、`git diff --check`、`python scripts/check_acceptance_sync.py`、`python scripts/check_local_execution_handoff.py`。

### 新增或修改的真机验收

- [ ] 本轮不启动 Artifact；保持 `LOCAL_EXECUTION_TASK.md` 为 `IDLE`。

### 回归项

- [ ] Full-suite baseline limitation 保持原样：Desktop integration assertion mismatch 与 `python` executable unavailable 的 `test_second_brain` 在 `d12c1fb` 和当前树均复现；不修改、不掩盖。
- [ ] Task 3 待办：专用 snapshot parser/consumer、可恢复 staging/outbox、下游可见性事务；通用 ExtractionPipeline 禁止绕过此边界。Task 2 不实现 adapter、watcher、聊天解析、Obsidian 正文或 tombstone/reconcile。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK2_FIX5_`
- 覆盖安装或迁移方式：不安装、不启动；pytest 临时数据库/raw/queue/marker 自动清理。
- 冲突清理：不保留 `.conflict` 正文副本；仅在现有 scan `last_error` 保留无正文 hash/path 诊断。
- 回滚：回滚产品 Commit `b0bc0cc2b15112b0cae203dee3af445fca2b33b7` 及其父实现提交，不触碰主人数据。

### 最终报告

- 报告路径：本地调度报告继续由 `.superpowers/` 忽略；正式证据为本条目与测试命令输出。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 2 fix round 3 · revoke-safe downstream and lease hardening

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`1c55fd7822de6cc90dfea23736aced6b309b7a8d`
- 影响模块：existing StateDatabase lease/revoke/manifest, extraction queue/pipeline, raw sink, Task 2 process/concurrency tests
- 风险等级：P0
- 用户可感知变化：来源撤销在同一 `lingji_state.db` 事务内取消 snapshot queued/retrying/running jobs；worker 在执行、索引和结构化写入前复核授权，撤销来源不会完成下游结果。
- 数据或安全边界变化：SnapshotJobRunner 拒绝 state/queue 不同 SQLite 文件（含别名校验）；lease 使用 TTL/heartbeat、进程实例 UUID 与线程元数据，长复制期间续租；raw 已有对象通过 no-follow descriptor 校验，冲突删除临时正文，仅记录 expected/actual hash 与目标路径诊断；manifest 提供 retired scan 清理 API。

### 新增或修改的自动验收

- [ ] `pytest -q tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_extraction_worker.py`：撤销 admission 后取消队列、跨进程双 runner、同库边界、短 TTL 慢复制、旧 NULL lease、inode=0、冲突隐私诊断与强杀恢复。
- [ ] `pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_hardening.py tests/test_extraction_worker.py`：Task 1/queue/extraction 回归。
- [ ] `py_compile`、`git diff --check`、`python scripts/check_acceptance_sync.py`、`python scripts/check_local_execution_handoff.py`。

### 新增或修改的真机验收

- [ ] 本轮不启动 Artifact；保持 `LOCAL_EXECUTION_TASK.md` 为 `IDLE`。

### 回归项

- [ ] Full-suite 仍有两项 baseline limitation（Desktop integration assertion mismatch；`python` executable unavailable in `test_second_brain`），在 `d12c1fb` 与当前树均复现，不修改、不掩盖。
- [ ] 不实现 Task 3 adapter、watcher、聊天解析、Obsidian 正文或 tombstone/reconcile。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK2_FIX3_`
- 覆盖安装或迁移方式：不安装、不启动；pytest 临时数据库/raw/queue/marker 自动清理。
- 冲突清理：不保留 `.conflict` 正文副本；仅在现有 scan `last_error` 保留无正文 hash/path 诊断。
- 回滚：回滚 `1c55fd7822de6cc90dfea23736aced6b309b7a8d` 及其父实现提交与本条文档提交，不触碰主人数据。

### 最终报告

- 报告路径：本地调度报告继续由 `.superpowers/` 忽略；正式证据为本条目与测试命令输出。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 2 fix round 2 · revoke-safe atomic admission

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`3c890e1d0986707b802e3b0c629c8f99cef87c34`
- 影响模块：StateDatabase lease TTL/revocation, incremental scan manifest, atomic raw/queue admission, Task 2 concurrency tests
- 风险等级：P0
- 用户可感知变化：撤销、并发和进程中断不会把未获授权文件继续推进到 raw/queue；恢复只复核增量 per-path sentinel，不重写完整 manifest。
- 数据或安全边界变化：revoke 原子取消 scan 并清理 lease；raw commit 使用原子 no-overwrite hard-link；queue admission 与 revoke 共用现有 state DB SQLite writer lock；lease 由不可预测 UUID、owner 元数据和明确 TTL/heartbeat 共同约束。

### 新增或修改的自动验收

- [ ] `pytest -q tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py`：撤销 mid-copy/raw/queue 竞态、取消态不转 failed、TTL/死线程/心跳、多进程 raw 收敛、symlink/损坏 raw、per-path 2000 项 manifest、立即 lease 强杀、30%/70% queue-before-checkpoint 强杀。
- [ ] `pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_hardening.py tests/test_extraction_worker.py tests/test_chatgpt_importer.py tests/test_structured_ingestion.py tests/test_capture_control.py`：Task 1/extraction 回归。
- [ ] `py_compile`、`git diff --check`、`python scripts/check_acceptance_sync.py`、`python scripts/check_local_execution_handoff.py`。

### 新增或修改的真机验收

- [ ] 本轮不启动 Artifact；保持 `LOCAL_EXECUTION_TASK.md` 为 `IDLE`。

### 主人肉眼确认

- [ ] 不适用；Task 2 不修改 Desktop 或正式 Vault 正文。

### 回归项

- [ ] 保持现有 StateDatabase/source registry、extraction queue/sink/idempotency 行为。
- [ ] Full-suite 两项 baseline limitation（Desktop integration assertion mismatch；`python` executable unavailable in `test_second_brain`）保持原样，不修改、不掩盖。
- [ ] 不实现 Task 3 adapter、watcher、聊天解析、Obsidian 正文或 tombstone/reconcile。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK2_FIX2_`
- 覆盖安装或迁移方式：不安装、不启动；pytest 临时数据库/raw/queue/marker 自动清理。
- 临时备份删除条件：无。
- 测试数据清理方式：仅清理本轮 pytest 临时目录和 conflict diagnostic 文件。
- 回滚：回滚 fix round 2 实现与文档提交，不触碰主人数据。

### 最终报告

- 报告路径：本地调度报告继续由 `.superpowers/` 忽略；正式证据为本条目与测试命令输出。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 2 fix round 1 · lease-safe recovery

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`2ee5fbf7e7dac74f95e8ed7220261aee36ef51b1`
- 影响模块：existing StateDatabase scan leases/checkpoints, snapshot runner recovery, content-addressed raw sink, Task 2 focused tests
- 风险等级：P0
- 用户可感知变化：扫描在并发、进程中断和重启后只由当前 lease owner 推进，并会复核 cursor 之前文件的持久 sentinel。
- 数据或安全边界变化：checkpoint/progress/finalize/release 均按 lease ownership 条件更新；旧 lease 不能覆盖或清理新 lease；损坏或目录 raw 冲突显式失败并保留临时诊断文件。

### 新增或修改的自动验收

- [ ] `pytest -q tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py`：17 项，含线程/多进程 lease 竞争、旧 lease 隔离、早期 sentinel/新增早期路径、raw 冲突、30%/70% 子进程强杀后重启收敛及 queue-before-checkpoint 中断。
- [ ] `pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_hardening.py tests/test_extraction_worker.py tests/test_chatgpt_importer.py tests/test_structured_ingestion.py tests/test_capture_control.py`：Task 1 与 extraction 回归。
- [ ] `py_compile`、`git diff --check`、`python scripts/check_acceptance_sync.py`、`python scripts/check_local_execution_handoff.py`。

### 新增或修改的真机验收

- [ ] 本轮不启动 Artifact；保持 `LOCAL_EXECUTION_TASK.md` 为 `IDLE`。

### 主人肉眼确认

- [ ] 不适用；Task 2 不修改 Desktop 或正式 Vault 正文。

### 回归项

- [ ] 既有 `StateDatabase`/source registry 状态和 extraction queue/sink/idempotency 回归保持通过。
- [ ] Full-suite 两项既有失败（Desktop integration assertion mismatch；`python` executable unavailable in `test_second_brain`）已在基线 `d12c1fb` 与当前 HEAD 复现，记录为 baseline limitation，不修改、不掩盖。
- [ ] 不新增数据库、队列、raw archive、watcher、聊天解析或 Task 3 适配器。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK2_FIX1_`
- 覆盖安装或迁移方式：不安装、不启动；pytest 临时目录和子进程自动清理。
- 临时备份删除条件：无。
- 测试数据清理方式：只清理 pytest 临时授权 root、SQLite、raw、queue 与 crash marker。
- 回滚：回滚本 fix round 提交，不触碰主人数据。

### 不在范围

- 不解析聊天、不实现 watcher、不写 Obsidian 正文、不改变 Task 3 代码。

### 最终报告

- 报告路径：本地调度报告仍保留于 gitignored `.superpowers/sdd/2026-08-26-phase1-automatic-memory/task-2-report.md`；正式验收证据为本条目。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 2 · consistent snapshot and resume

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`pending`
- 影响模块：automatic-memory snapshot/checkpoint、extraction raw sink/idempotency/queue
- 风险等级：P0
- 用户可感知变化：授权来源文件可以以一致快照进入现有 raw/queue 流程，并在受控中断后从最后确认项目恢复。
- 数据或安全边界变化：仅允许 active owner-authorized source root 内的普通文件；拒绝 symlink、目录、root escape、revoked/expired source；raw 使用 content address；不修改源文件。

### 新增或修改的自动验收

- [ ] `pytest -q tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py`：stat-before/copy/stat-after、重试、路径边界、raw/queue 幂等、lease/checkpoint、30%/70% resume。
- [ ] `pytest -q tests/test_automatic_memory_source_registry.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_hardening.py`：Task 1 与 extraction 回归。
- [ ] `python scripts/check_acceptance_sync.py`、`python scripts/check_local_execution_handoff.py`、diff/compile/secret/absolute-path scans。

### 新增或修改的真机验收

- [ ] 本任务不启动 Artifact；保持 `LOCAL_EXECUTION_TASK.md` 为 `IDLE`。

### 主人肉眼确认

- [ ] 不适用；Task 2 不修改 Desktop 或正式 Vault 正文。

### 回归项

- [ ] 现有 `VaultExtractionSink`、`SQLiteExtractionQueue` 和 canonical extraction idempotency 行为保持兼容。
- [ ] 不创建第二 state DB、queue 或 raw archive；不读取真实聊天、Vault 或第三方 AI 目录。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK2_`
- 覆盖安装或迁移方式：不安装、不启动；pytest 临时目录自动清理。
- 临时备份删除条件：无。
- 测试数据清理方式：仅 pytest 临时授权 root、SQLite、raw 与 queue。
- 回滚：回滚本 Task 2 提交，不触碰主人数据。

### 不在范围

- 不解析聊天、不实现 watcher、不写 Obsidian 正文、不实现全目录发现。

### 最终报告

- 报告路径：`.superpowers/sdd/2026-08-26-phase1-automatic-memory/task-2-report.md`
- 报告分支：`codex/phase1-automatic-memory`

## 填写模板

```markdown
## YYYY-MM-DD · <PR/任务> · <短标题>

- 产品分支：`<branch>`
- 产品 Commit：`<sha 或 pending>`
- 影响模块：
- 风险等级：P0 / P1 / P2 / P3
- 用户可感知变化：
- 数据或安全边界变化：

### 新增或修改的自动验收

- [ ] `<测试命令或测试文件>`：验证什么

### 新增或修改的真机验收

- [ ] `<步骤>`：预期结果

### 主人肉眼确认

- [ ] `<必须人工观察的行为>`

### 回归项

- [ ] `<历史 Bug 或兼容承诺>`

### 清理与回滚

- 临时数据前缀：
- 覆盖安装或迁移方式：
- 临时备份删除条件：
- 测试数据清理方式：

### 不在范围

- `<本次没有实现且不得宣称已完成的能力>`

### 最终报告

- 报告路径：`docs/TEST_REPORTS/<REPORT>.md`
- 报告分支：`acceptance/<task>-<short-sha>`
```

## 2026-08-26 · Phase 1 Automatic Memory · Task 0 contract and plan封板（pending implementation）

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`pending — Task 0 docs-only baseline d12c1fb837257e83835a7cdb899bb29a9c675c3d`
- 影响模块：自动化第二大脑授权、官方 AI 记录导入、raw/provenance、Extraction Queue、时态 derived memory、RAG/ContextPack/MCP、Obsidian scope、Desktop Work Fact、macOS M5-first acceptance
- 风险等级：P0
- 用户可感知变化：本条目只封板后续开发和验收契约；Task 0 不改变产品运行行为。后续阶段必须让主人看见发现、接管、执行、结果、失败、下一动作与证据。
- 数据或安全边界变化：后续输入必须由一次中文主人授权和精确 allowlist 限定；禁止 Cookie、Token、凭证、浏览器资料、私有 DB、进程注入、应用目录写入、全盘扫描和网络上传。ChatGPT 只用官方导出，Codex schema-detect/fail-closed，Claude opaque storage 显示 `unsupported`/`consent_required`。

### 新增或修改的自动验收

- [ ] Task 1：`tests/test_automatic_memory_source_registry.py` 使用真实临时 SQLite 验证一次中文授权、精确 root allowlist、持久 source/scan 状态、cursor/progress/error/recovery 与 revoke；不得读取聊天正文。
- [ ] Task 1：`tests/test_automatic_memory_control_api.py` 使用真实 FastAPI app 验证 8766 现有 token 鉴权、authorize/revoke/scan/pause/retry/sources/scans 路由及未授权 401；未知状态不得伪造成 completed/0。
- [ ] Task 1 fix round 1：过期 grant 在持久 read/list/start/pause/retry 路径变为 `expired` 并拒绝扫描；revoke 在同一 SQLite 事务取消 running/paused/failed scan；register/start 的重复与并发调用保持单一 source/active scan，scope 冲突返回明确 4xx。
- [ ] Task 1 fix round 2：active grant 下 failed scan 允许 pause 并保留 recovery token/error；expired/revoked failed scan 与 cancelled scan 仍拒绝恢复。
- [ ] Task 1–2：授权 scope、根目录边界、客户端 capability 和拒绝原因。
- [ ] Task 3：ChatGPT 官方导出 ZIP、raw snapshot、message identity、幂等和 malformed export failure。
- [ ] Task 4：`watchfiles==1.2.0`、5 秒防抖、30 秒入队、15 分钟 reconciliation、每日完整性。
- [ ] Task 5–6：Codex schema fail-closed；Claude 不读取 opaque storage 并显示准确 unsupported/consent 状态。
- [ ] Task 7–9：SHA-256 raw/provenance、append-only audit、Obsidian allowlist、时态 validity、current filter、derived confidence `>= 0.90`。
- [ ] Task 10：ContextPack `<= 12000` 字符、citation、统一 MemoryGateway、MCP 与 Desktop 同一 Work Fact ID。
- [ ] Task 11：`quality_score >= 90%`、`source_accuracy >= 95%`、`false_positive_rate <= 5%`、Codex MCP `>= 95%`、duplicate formal content `0`、Production pollution `0`、owner review `100%`、reboot recovery `100%`。

### 新增或修改的真机验收

- [ ] Task 1：不启动 Artifact；仅确认代码路径只注册现有认证 8766 app，`LOCAL_EXECUTION_TASK.md` 保持 `IDLE`，并以临时 SQLite 重启后复读 registry/scan 状态。
- [ ] 仅在产生新产品 Commit 和同 SHA Artifact 后执行；Task 0 不下载、不安装、不启动 Artifact。
- [ ] macOS M5 first：覆盖安装、授权、发现、导入、Work/Memory/ContextPack/MCP、三轮 Core 重启、一次 macOS 重启、主人观察、清理和远程复读完成后，才进入 Windows。
- [ ] Production 与 Acceptance 的 Vault、raw、SQLite、Qdrant、日志和设置物理隔离；普通 Obsidian 文档不读不索引。

### 主人肉眼确认

- [ ] 首页、Work、Attention、Capture、Memory 能显示同一真实事实链；主人能理解系统接管了什么、做了什么、结果是什么、下一步由谁执行。
- [ ] unsupported、consent_required、degraded、unknown、failure 和空状态不伪造为成功、健康或零工作。

### 回归项

- [ ] Task 1：现有 StateDatabase/control API focused 回归通过；不新增数据库、8765 路由、客户端正文读取或未认证 8766 路由。
- [ ] 保持 `LOCAL_EXECUTION_TASK.md` 为 `IDLE`；不得创建本阶段真机任务或重跑淘汰 Artifact。
- [ ] 保持 Obsidian Vault + Git 为正式正文权威；derived current memory 不等于 Core/正式永久正文。
- [ ] Current retrieval 排除 `superseded`、`invalidated`、`archived`；历史记录仍可审计。
- [ ] Opportunity Center 保持冻结；不引入 Mem0、OpenMemory、Letta、Zep/Graphiti 或 LlamaIndex 第二系统。

### 清理与回滚

- Task 1：测试使用 pytest 临时目录和临时 SQLite，测试结束自动清理；失败仅回滚本提交，不触碰 Production/Vault。
- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_`
- 覆盖安装或迁移方式：未来验收直接覆盖安装；Task 0 不安装。
- 临时备份删除条件：报告远程第一次确认后删除；只保留脱敏哈希。
- 测试数据清理方式：只清理本阶段明确 allowlist 的 Acceptance fixture、raw、日志、截图、checkpoint 和配置副本，不触碰 Production/Vault。
- 回滚：回退 Task 0 文档提交；不得激活本机任务或改变历史失败结论。

### 不在范围

- Task 0 不修改产品代码、测试代码、依赖、Runtime、Desktop、数据库、Qdrant、Vault 或正式记忆。
- 不创建 `ACTIVE` 本机任务，不生成 Artifact，不进行真实客户端调用，不进入 Windows 验收。
- 不把任何计划入口、能力矩阵或文档契约写成已实现产品能力。

### 最终报告

- 报告路径：`logs/sdd/task-0-report.md`
- 执行计划：`docs/superpowers/plans/2026-08-26-phase1-automatic-memory.md`
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 0 fix round 1 · dependency and entry-point repair（pending implementation）

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`pending — documentation repair on d59658e52bbf75fc8e6fd26f6625610f7360793e`
- 影响模块：自动记忆计划依赖顺序、source registry/scan API、consistent snapshot/resume、adapter registry、scheduler lifecycle、Obsidian migration、temporal all-path filter、Work Fact/8766/Desktop、RAG/evaluation、macOS/Windows acceptance
- 风险等级：P0
- 用户可感知变化：本轮不改变产品行为；修复计划后，任何自动记忆能力都必须先有可恢复证据链和真实 Work Fact，再进入 RAG、Desktop 或平台验收。
- 数据或安全边界变化：source root、scan cursor/progress/error/recovery、stat-before/copy/stat-after、content hash、lease/retry 和 crash recovery 必须持久化；不读取秘密、私有 DB、opaque storage、进程或全盘路径。

### 新增或修改的自动验收

- [ ] Task 1–2：持久 registry、授权/扫描 8766 鉴权、cursor/progress/error/recovery、consistent snapshot、source sentinel、30%/70% crash resume、重复 raw/job 为 0。
- [ ] Task 3–4：ChatGPT/Codex/Claude/generic JSON/JSONL/Markdown adapters；watchfiles 5 秒防抖、15 分钟 reconciliation、每日完整性和 scheduler 生命周期。
- [ ] Task 5–8：Obsidian dry-run manifest/managed-derived rollback；derived promotion；lexical/Qdrant/hybrid/Core/ContextPack/MemoryGateway/MCP temporal modes；Work Fact/TS DTO/8766/Desktop smoke。
- [ ] Task 9：现有 `src/retrieval/context_pack.py` RAG 扩展、12,000 字符和 citations；独立 100 问评测与阈值 gate。
- [ ] Task 10–11：macOS M5 owner acceptance first，随后 PowerShell 5.1 Windows parity；不得把重启或主人观察写成 pytest/validate 自动 PASS。

### 回归项

- [ ] 不创建 `src/gateway/memory.py` 或 `src/automatic_memory/context_pack.py`；只扩展真实 `src/gateway/memory_gateway.py` 与 `src/retrieval/context_pack.py`。
- [ ] `LOCAL_EXECUTION_TASK.md` 保持 `IDLE`；Task 10 完成后由主代理另发 ACTIVE 本机任务。
- [ ] Opportunity Center 保持冻结；不引入第二记忆系统或新的永久事实源。

### 最终报告

- 报告路径：`logs/sdd/task-0-report.md`
- 执行计划：`docs/superpowers/plans/2026-08-26-phase1-automatic-memory.md`
- 报告分支：`codex/phase1-automatic-memory`

---

## 2026-08-25 · 文档事实审计 · 对齐 SB-0 实际进度并降级历史快照

- 产品分支：`codex/docs-project-truth-audit`
- 审计基线：`ced1128e50d3b3758585573042ea6bcc6f315384`
- 产品代码变化：无
- 影响模块：项目状态、代码导航、文档治理、历史实施/验收文档标识、PEMIS 生成快照标识
- 风险等级：P2
- 用户可感知变化：开发者和主人不再把已经修复的 SB-0 子项误判为尚未开始，也不会把旧模块报告、旧 M5 研究或 2026-06 PEMIS 快照误判为当前产品状态。
- 数据或安全边界变化：无；不修改 Runtime、API、Desktop、Vault、数据库、Qdrant、Credential、正式记忆、Artifact 或主人数据。

### 新增或修改的自动验收

- [x] `python3 scripts/check_acceptance_sync.py`：确认纯文档变更没有遗漏产品变化验收记录。
- [x] `python3 scripts/check_local_execution_handoff.py`：确认当前任务仍为 `IDLE`，最近结果仍为 `COMPLETED / FAIL`。
- [x] `git diff --check`：确认 Markdown 无空白错误。
- [x] 全量受跟踪文档本地链接扫描：确认当前权威没有缺失的相对链接。
- [x] 当前状态引用扫描：确认当前治理文档不再引用已删除的 `docs/AI_CONTEXT.md` 或 `UNIFIED_MEMORY_DEVELOPMENT_ROADMAP.md`。

### 新增或修改的真机验收

- [x] 不需要。本任务不安装、不启动 UI、不运行 Sidecar、不访问真实数据，也不改变产品行为。

### 主人肉眼确认

- [x] 不需要产品 UI 肉眼确认；最终向主人提供非技术化的“能做什么 / 缺什么 / 卡点”说明。

### 回归项

- [x] 保持 `PHASE 1 — SECOND BRAIN COMPLETION`，不得提前进入 Opportunity Center。
- [x] 保持最近 M5 `FAIL / DO NOT MERGE`，不得把 SB-0 部分实现写成 Phase 1 PASS。
- [x] 保持 `LOCAL_EXECUTION_TASK.md` 为 `IDLE`，不得激活或重跑旧 Artifact。
- [x] 保留 `docs/TEST_REPORTS/**`、验收结果回执、哈希与失败证据，不改写历史结论。
- [x] Work Fact 必须继续明确：正式 8766 路由、LocalControlService 共享接入、Desktop DTO/响应合同、Outcome/NextAction、端到端与真实验收仍未完成。

### 清理与回滚

- 临时数据前缀：无
- 覆盖安装或迁移方式：不适用
- 临时备份删除条件：不适用
- 测试数据清理方式：不创建产品测试数据
- 回滚：回退本次文档提交；不得恢复错误的当前进度或把历史快照提升为当前权威。

### 不在范围

- 不注册 `/api/work/*`。
- 不修改 Work Fact、Capture、Memory 或 Desktop 合同。
- 不执行 focused/full/release 产品门禁。
- 不创建新产品 Commit、Artifact、ACTIVE 本机任务或主人验收结论。
- 不删除 120 个 PEMIS opportunity 生成记录或任何历史测试/验收报告。

### 最终报告

- 报告路径：`docs/TEST_REPORTS/DOCUMENTATION_TRUTH_AUDIT_20260825.md`
- 执行计划：`docs/superpowers/plans/2026-08-25-documentation-truth-audit.md`
- 报告分支：不适用；本次不是 Artifact 真机验收报告分支

---

## 2026-08-01 · PR #60 后续 · 代码发布验证临时目录安全清理修复

- 产品分支：`fix/cleanup-code-validation-workspace`
- 产品 Commit：`pending`
- 来源阻塞：`PR60-CODE-RELEASE-VALIDATION-A90A18A6 / BLOCKED_POST_CLEANUP`
- 影响模块：本机任务治理、安全清理工具、代码发布链结果回执
- 风险等级：P1
- 用户可感知变化：不需要重跑已通过的 15 套 release 验证；修复后只补做安全清理、最终回执和远程复读。
- 数据或安全边界变化：不触碰产品 Runtime、UI、Vault、数据库、Qdrant、真实资料或用户 AI 配置；仍只允许删除任务 ID 推导出的精确临时目录。

### 新增或修改的自动验收

- [x] `python -m pytest -q tests/test_cleanup_acceptance_workspace.py`：本地隔离验证 `10 passed`。
- [ ] GitHub `tests`：验证 Python 3.11、3.12、Windows 和完整仓库回归。
- [ ] `acceptance-doc-sync`：验证脚本变化已同步本记录。

### 新增或修改的真机验收

- [ ] 使用 `PR60-CODE-RELEASE-VALIDATION-A90A18A6` 对 `D:\codex\LingJiValidation\PR60-CODE-a90a18a6` 先 dry-run。
- [ ] dry-run 清单必须只包含该任务创建的 product、report、release、日志、缓存和证据目录。
- [ ] 显式 `--execute` 后目标目录必须不存在，相邻目录和主人数据保持不变。
- [ ] 更新原报告与结果回执为最终 `PASS`，再次 push 并远程复读。

### 主人肉眼确认

- [x] 不需要主人参与；本任务不安装、不启动 UI、不读取真实数据。

### 回归项

- [ ] 不允许通配符删除。
- [ ] 不允许删除清理根目录本身。
- [ ] 不允许删除根目录外或非直接子目录。
- [ ] 任务类型、PR号和 8 位 Commit 身份必须与目录名精确匹配。
- [ ] 旧 `D69874AF` 记忆质量任务仍能清理两个明确登记的 `1c514877` 历史目录。
- [ ] 不跟随符号链接或 Windows reparse point。

### 清理与回滚

- 当前清理根：`D:\codex\LingJiValidation`
- 当前目标：`PR60-CODE-a90a18a6`
- 安全入口：`scripts/cleanup_acceptance_workspace.py`
- 回滚：回退本次策略和测试；不得恢复宽泛白名单或手工强删。

### 不在范围

- 不重跑产品代码、Desktop、Rust/Tauri 或 Windows release 验证。
- 不生成或安装正式 GitHub Artifact。
- 不解决 PR #60 与 master 的后续合并冲突。
- 不进入 Day 0、UI 或真实数据验收。

### 最终报告

- 修复报告：`docs/TEST_REPORTS/PR60_CODE_VALIDATION_CLEANUP_POLICY_FIX.md`
- 原验证报告：`docs/TEST_REPORTS/PR60_CODE_RELEASE_VALIDATION_a90a18a6.md`
- 原报告分支：`acceptance/pr60-code-release-validation-a90a18a6`

---

## 2026-07-31 · PR #60 · d69874af 引导修复复验与真实数据记忆质量试运行

- 产品分支：`feature/unified-ai-memory-connectors`
- 产品 Commit：`d69874afd8def42a40c4a5cc5e678a71921d44b5`
- 固定 Artifact：`lingji-windows-0.1.0-d69874af`
- Artifact ID：`8762312712`
- Artifact ZIP SHA256：`6bf1f591502617c400ce482f6beb0d5e430a172cd036137bb4a39cae2cbf4cb4`
- 安装器 SHA256：`d62867b7b7c90bee8273b3cf5720f53099c266897ce95d0e42224deae31bf262`
- 影响模块：首次使用引导、AI 软件与历史目录发现、Codex 连接状态机、Embedding/Qdrant 诊断、Day 0、真实数据试运行、报告提交和本地清理
- 风险等级：P0
- 用户可感知变化：页面必须给出唯一当前动作，主动解释扫描结果和可导入范围，不再同时显示“配置正常”和“命令不存在”，向量问题必须展示具体原因与处理入口。
- 数据或安全边界变化：Day 0 未 PASS 禁止读取真实资料；历史目录只读取元数据，读取内容前必须获得主人授权；Production 保持只读和物理隔离。

### 已通过的自动验收

- [x] `acceptance-doc-sync #43`
- [x] `local-execution-handoff #35`
- [x] `tests #1138`
- [x] `P0 Windows Gate #258`
- [x] `Windows Desktop Release Baseline #142`
- [x] 旧模糊文案“已设置，等待测试”回归断言。
- [x] 配置文件、客户端命令和真实连接三个状态分离。

### 新增或修改的真机验收

- [ ] 开始前使用 `scripts/cleanup_acceptance_workspace.py` 清理旧任务专用临时目录；脚本必须先 dry-run，再显式 `--execute`，且只能操作任务单允许的精确目录。
- [ ] Day 0 在任何真实数据导入前完成：固定 Artifact、覆盖安装、Runtime、8766/8767、MCP 鉴权、真实 Codex 调用、候选边界、A-01、三轮 Core 重启和 Windows 重启。
- [ ] 页面始终只有一个明确主要动作；扫描完成后主动说明发现的软件和历史目录元数据。
- [ ] 发现历史目录后主动询问是否查看或导入，明确说明当前支持与不支持的格式。
- [ ] 配置文件存在、`codex` 命令可用和真实 MCP 连接必须分别显示；缺少命令时不得显示 ready。
- [ ] Embedding/Qdrant 必须显示配置模型、激活模型、缺失模型、最近错误、Qdrant 状态、是否需要重建和当前可执行入口。
- [ ] 主人明确授权后，Stage 1 只导入 1 部剧本、1 份 Codex 报告、少量 ChatGPT 历史和 1 个明确 Obsidian 目录。
- [ ] Stage 1 无 P0/P1 后才逐步扩展到最多 10 部授权剧本和其他授权资料。
- [ ] 至少执行 20 道质量题：精确事实不少于 8、跨文档比较不少于 4、来源核验不少于 4、负面边界不少于 4。

### 主人肉眼确认

- [ ] Checkpoint A：安装和首次打开，无黑窗，首页正常，唯一下一步清楚，状态文案能区分。
- [ ] Checkpoint B：Codex 能看到 LingJi 工具、真实调用成功、返回内容正确。
- [ ] Checkpoint C：主人亲自批准一个测试候选、拒绝一个测试候选，页面可理解。
- [ ] Checkpoint D：Windows 重启后无黑窗，灵机恢复且页面可操作。
- [ ] Checkpoint E：主人至少抽查 10 道质量题，确认答案与来源评分。

### 强制回归项

- [ ] Day 0 未 PASS 时禁止导入真实资料。
- [ ] 未经主人授权不得读取或导入任何真实目录内容。
- [ ] 剧本人物、剧情和台词不得进入主人个人事实。
- [ ] 不存在的问题必须承认未知，不得拿相似资料冒充。
- [ ] 候选未批准前 Core Memory 不增加，拒绝候选不进入永久记忆。
- [ ] A-01 隔离不得读取或修改主人真实 `CODEX_HOME`。
- [ ] 覆盖安装和连接器回滚不得破坏主人数据或配置。
- [ ] Windows 重启后 Runtime、MCP、Workspace、DataRoot 和 Vault 恢复。
- [ ] 开始前和结束后临时目录必须清理；清理失败时只能 BLOCKED，不得绕过安全策略。

### 质量阈值

```text
quality_score >= 90%
source_accuracy >= 95%
false_positive_rate <= 5%
Codex MCP 真实调用成功率 >= 95%
重复正式内容 = 0
Production 污染 = 0
人工审核链成功率 = 100%
Windows 重启后恢复 = 100%
```

### 清理与回滚

- 当前临时数据前缀：`PR60_MEMORY_TRIAL_D69874AF_`
- 当前临时根目录：`D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-d69874af`
- 必须清理的历史临时目录：`D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-1c514877`、`D:\codex\LingJiAcceptance\PR60-1c514877`
- 安全清理入口：`python scripts/cleanup_acceptance_workspace.py --task-id PR60-MEMORY-QUALITY-TRIAL-D69874AF --target <精确目录>`；确认 dry-run 后追加 `--execute`。
- 清理工具拒绝验收根目录本身、根目录外路径、非白名单目录和不匹配任务身份；不跟随符号链接或 Windows reparse point。
- 覆盖安装方式：固定安装器直接覆盖，不卸载。
- 临时配置副本：每个客户端最多一个，哈希验证后删除。
- 主人授权的真实资料是否保留由主人选择，Codex不得擅自删除。
- 报告第一次远程确认后清理，更新结果回执，再次 push 和远程复读。

### 不在范围

- Codex 原始 Session / JSONL 自动导入。
- Claude Code 和 WorkBuddy 历史导入。
- 自动下载 Embedding 模型。
- 自动重建 Production Qdrant。
- 自动批准永久记忆。
- 远程或公网 MCP。

### 最终报告

- 专项协议：`docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md`
- 任务单：`docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`
- 报告路径：`docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_d69874af.md`
- 报告分支：`acceptance/pr60-memory-quality-trial-d69874af`
- 产品 PR 必须保持 Draft 且不得合并，直到 Day 0、Stage 1、质量指标、主人检查点、远程提交和清理全部满足 PASS。

---

## 2026-07-30 · PR #60 · 1c514877 首轮试运行（历史失败，禁止重跑）

- 产品分支：`feature/unified-ai-memory-connectors`
- 产品 Commit：`1c5148779624910f1c6072d95d6c6f6822f631e6`
- 固定 Artifact：`lingji-windows-0.1.0-1c514877`
- Artifact ID：`8723868744`
- 状态：历史 `FAIL / BLOCKED_SUBMISSION`，已被 2026-07-31 的 d69874af 条目取代。
- 已知缺陷：`D0-UX-001` 页面缺少统一引导；`D0-CODEX-002` 配置状态和命令状态矛盾；`BLOCKED_POST_CLEANUP` 旧临时目录未清理。
- 历史报告：`docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_1c514877.md`
- 历史报告分支：`acceptance/pr60-memory-quality-trial-1c514877`
- 当前不得再按该产品 Commit、Artifact 或报告路径执行。

---

## 2026-07-30 · 本机任务信箱与结果回执硬门禁

- 产品分支：`master`
- 产品 Commit：`governance-only`
- 影响模块：仓库治理、Codex 本机执行交接、报告提交、远程复读、本地垃圾清理、GitHub Actions
- 风险等级：P1
- 用户可感知变化：用户只需告诉 Codex 去看任务单，或告诉 ChatGPT Codex 已完成；不再复制长指令、解释 Git、上传报告或排查分支。
- 数据或安全边界变化：不改变产品数据；明确禁止清理主人 DataRoot、Vault、正式记忆和用户 AI 配置，只清理本轮临时验收垃圾。

### 新增或修改的自动验收

- [x] `python scripts/check_local_execution_handoff.py`：校验任务单、结果回执、身份一致性、开始/结束清理、远程确认和报告 Commit 字段。
- [x] `python -m pytest -q tests/test_local_execution_handoff.py`：覆盖 PENDING、COMPLETED、远程确认缺失、清理失败、身份不一致和阻塞提交。
- [x] `local-execution-handoff` Workflow：在 `master`、开发分支和 `acceptance/**` 报告分支执行；报告分支结果不是 `COMPLETED` 时失败。

### 新增或修改的真机验收

- [x] Codex 只读取 `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md` 中 `status: ACTIVE` 的任务，不从聊天或本机残留推断。
- [x] 每次开始前整体清理上一轮临时验收目录、Artifact、日志、截图、fixture、checkpoint、临时配置副本和 worktree，再释放 8766/8767。
- [x] 报告 push 后使用 `git ls-remote` 和 GitHub API 重新读取远程分支、Commit、报告、结果回执和 PR 评论。
- [x] 第一次远程确认后清理本轮本地垃圾，更新结果回执，再次 push 和远程复读。

### 主人肉眼确认

- [x] 用户只负责下达“去看任务单干活”或“Codex 已完成”，不负责 Git、上传、报告路径和清理操作。

### 回归项

- [x] 禁止把本机生成报告误写成已经上传。
- [x] 禁止 `git push` 命令执行后未复读远程就宣布完成。
- [x] 禁止长期堆积旧验收目录、重复安装包、日志、截图、fixture、checkpoint、配置副本和 worktree。
- [x] 禁止清理主人正式数据或其他任务数据。

### 清理与回滚

- 临时数据前缀：由 `LOCAL_EXECUTION_TASK.md` 每个任务单独声明。
- 覆盖安装或迁移方式：本次为治理变更，不涉及产品安装。
- 临时备份删除条件：远程报告第一次确认后删除；只保留哈希。
- 测试数据清理方式：本机任务结束时删除任务单指定临时根目录和带任务前缀的数据。

### 不在范围

- 不改变 LingJi 产品 Runtime、UI、数据库、记忆或连接器功能。
- 不代替具体任务的真机验收标准。
- 不要求用户学习 Git 或参与报告提交。

### 最终报告

- 规则权威：`docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md` 与 `docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md`
- 自动门禁：`.github/workflows/local-execution-handoff.yml`

---

## 2026-07-29 · PR #60 · P0-A 与统一 AI 记忆连接器重新真机验收（历史方案）

- 产品分支：`feature/unified-ai-memory-connectors`
- 产品 Commit：`1c5148779624910f1c6072d95d6c6f6822f631e6`
- 固定 Artifact：`lingji-windows-0.1.0-1c514877`
- Artifact ID：`8723868744`
- 状态：被后续真实数据试运行方案取代，保留为历史记录。
- 已通过自动验收：`tests #1081`、`P0 Windows Gate #240`、`Windows Desktop Release Baseline #129`、A-01 回归。
- 原计划报告：`docs/TEST_REPORTS/PR60_OWNER_CODEX_FULL_REACCEPTANCE_1c514877.md`
- 原计划分支：`acceptance/pr60-owner-1c514877`
- 当前不得再按该旧路径执行。

---

## 2026-07-29 · PR #62 · 建立统一 Codex 验收权威

- 产品分支：`docs/acceptance-governance`
- 治理实现与门禁验证基线：`e43da870bc755321f5bd0db4a40aca31df91124d`
- 影响模块：仓库治理、Codex 执行入口、CI 文档同步门禁
- 风险等级：P1
- 用户可感知变化：Codex 拉取代码后可直接从仓库读取当前验收指令，不再依赖聊天中复制的旧指令。
- 数据或安全边界变化：没有产品数据变更；新增规则要求临时证据和配置副本在报告提交后清理。

### 新增或修改的自动验收

- [x] `python scripts/check_acceptance_sync.py`
- [x] `python -m pytest -q tests/test_acceptance_sync.py`
- [x] GitHub Workflow `acceptance-doc-sync #1`
- [x] GitHub Workflow `tests #1082`
- [x] GitHub Workflow `P0 Windows Gate #241`

### 新增或修改的真机验收

- [x] Codex 从仓库读取验收权威，不依赖聊天历史。
- [x] 代码变化后必须同步验收标准。
- [x] 报告提交后清理临时 Artifact、日志、截图、fixture 和配置副本。

### 主人肉眼确认

- [x] 主人明确要求仓库成为验收指令权威。

### 回归项

- [x] 不允许代码变更后遗漏验收标准更新。
- [x] 不允许为了补报告移动已打包产品 Head。
- [x] 不允许长期堆积重复验收垃圾。

### 清理与回滚

- 临时数据前缀：`ACCEPTANCE_GOVERNANCE_`
- 不涉及产品安装或正式数据。

### 不在范围

- 不改变 LingJi 产品功能。
- 不替代模块测试报告。
- 不自动合并产品 PR。

### 最终报告

- 报告路径：`docs/TEST_REPORTS/ACCEPTANCE_GOVERNANCE_IMPLEMENTATION.md`
- 治理 PR：`#62`
