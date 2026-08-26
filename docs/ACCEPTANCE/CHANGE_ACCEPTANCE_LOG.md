# 验收要求变更记录

> 每个包含产品代码、运行时、UI、连接器、数据链路、脚本、依赖或发布流程变化的 PR，都必须在本文件顶部追加一条记录。
>
> 记录描述“本次代码变化后，验收必须新增、修改或回归什么”。历史记录不得删除，只能更正明显错误并说明原因。

## 2026-08-26 · Phase 1 Automatic Memory · Task 7 repair round 3 · why scope isolation

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`2b8ca4eb9724f3f75b23d797a109847b3c42f4c8`
- 影响模块：why lexical/semantic candidate scope, project/tag/agent filtering, short-Chinese history fallback memory-type filtering
- 风险等级：P0
- 用户可感知变化：`why` 的排除候选现在复用完整检索范围；跨项目、未授权 Agent、标签或 memory type 不匹配的证据不会出现在解释中，也不会泄露来源引用。
- 数据或安全边界变化：只收窄解释候选，不改变历史证据保存或 current 检索语义；不新增事实源。

### 新增或修改的自动验收

- [x] `tests/test_task7_timeline_retrieval.py`：13 passed，新增 Project/Memory Type scope 与短中文 history fallback 隔离回归。
- [x] Task 7 相关检索/Gateway/MCP/Project Context 回归：87 passed，2 warnings（既有依赖弃用警告）。
- [x] 涉及文件 `py_compile`、`git diff --check`：PASS。
- [ ] Task 1–6 回归、`scripts/check_acceptance_sync.py`、`scripts/check_local_execution_handoff.py`：根代理在双提交后复读。
- [ ] Qdrant unavailable、真实 Production Vault、主人 UI/M5 真机验收：仍不在本轮范围。

### 回滚

- 回滚：回退产品 Commit `2b8ca4eb9724f3f75b23d797a109847b3c42f4c8` 与本条文档提交；不触碰 Vault、原始聊天证据、Qdrant 正式数据或主人配置。

## 2026-08-26 · Phase 1 Automatic Memory · Task 7 repair round 1 · temporal and why hardening

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`f045cdfe3a124de7ea4ed3fa61b41c24ffa00a55`
- 影响模块：timezone-aware temporal parsing, stable current cache identity, bounded why exclusions, explicit authority-conflict handling, project refresh interval closure
- 风险等级：P0
- 用户可感知变化：无时区查询和记忆有效期不再被猜测为 UTC；默认 current cache 不因每次读取时间变化而产生伪造新键；`why` 现在展示同一查询候选集中被状态/时间/权威规则排除的记忆及引用；项目替代会在新决定生效时刻关闭旧决定区间。
- 数据或安全边界变化：保持历史证据和原始正文不删除；当前输出仍只允许安全候选，why 解释有数量上限且不改变当前检索可见性。

### 新增或修改的自动验收

- [x] `tests/test_task7_timeline_retrieval.py`：12 passed，新增 per-result why 排除隔离、显式冲突主题与无关结果回归、非法 temporal mode fail-closed。
- [x] Task 7 相关检索/Gateway/MCP/Project Context 回归：86 passed，2 warnings（既有依赖弃用警告）。
- [x] 涉及文件 `py_compile`、`git diff --check`：PASS。
- [ ] Task 1–6 回归、`scripts/check_acceptance_sync.py`、`scripts/check_local_execution_handoff.py`：根代理在双提交后复读。
- [ ] Qdrant unavailable、真实 Production Vault、主人 UI/M5 真机验收：仍不在本轮范围。

### 回滚

- 回滚：回退产品 Commit `f045cdfe3a124de7ea4ed3fa61b41c24ffa00a55` 及其前置 Task 7 修复提交与本条文档提交；不触碰 Vault、原始聊天证据、Qdrant 正式数据或主人配置。

## 2026-08-26 · Phase 1 Automatic Memory · Task 7 · unified timeline retrieval

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`344bef7ff1b88c23c0979b113a354bc3148bda6e`
- 影响模块：统一 temporal query contract、MemoryDatabase lexical、Qdrant semantic payload/filter boundary、hybrid post-filter、Core/ContextPack、MemoryGateway、Project Context、MCP
- 风险等级：P0
- 用户可感知变化：检索入口统一支持 `current`、`as_of`、`history`、`why`；当前结果排除被替代/失效/归档内容，历史可按时间找回，`why` 提供权威级别、来源引用、有效期和替代原因。时区偏移和损坏时间元数据按规范化瞬时处理并 fail-closed；语义结果经过同一 SQLite 权威记录复核，不能绕过当前过滤。
- 数据或安全边界变化：保留原始证据和历史记录；项目刷新只在可重建 Memory DB 中写替代/失效链接，不删除 Vault/原始证据；不新增 gateway、retriever、temporal database 或事实源。

### 新增或修改的自动验收

- [x] `tests/test_task7_timeline_retrieval.py`：8 passed，覆盖 current/history/as_of/why、半开区间边界、时区偏移、损坏时间 fail-closed、幂等项目刷新、Gateway/ContextPack 模式传播、语义 stale-only 泄漏阻断、显式冲突键下的权威排序与无关同项目记录保留。
- [x] Task 7 相关检索/Gateway/MCP/Project Context 回归：80 passed，2 warnings（既有依赖弃用警告）。
- [x] Task 1–6 回归：241 passed，3 warnings（既有 zip duplicate、Pydantic、依赖弃用警告）。
- [x] 涉及文件 `py_compile`、`git diff --check`：PASS。
- [ ] `scripts/check_acceptance_sync.py`、`scripts/check_local_execution_handoff.py`：根代理在文档提交后复读。
- [ ] Qdrant unavailable、真实 Production Vault、主人 UI/M5 真机验收：仍不在本轮范围。

### 回归与回滚

- [x] 既有 privacy/project/agent-scope、Core、ContextPack、MCP 和 Qdrant/semantic wiring 回归保持通过。
- [x] SQLite 只作为可重建 lexical/read model；Qdrant 仍为可重建 semantic projection，当前状态由 Memory DB temporal predicate 最终裁决。
- 回滚：回退产品 Commit `344bef7ff1b88c23c0979b113a354bc3148bda6e` 及其前置 Task 7 产品提交与本条文档提交；不触碰 Vault、原始聊天证据、Qdrant 正式数据或主人配置。

## 2026-08-26 · Phase 1 Automatic Memory · Task 6 final repair · candidate-owned evidence self-reference

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`2663a4cf40c267767036c1e18a90df0f8bd10036`
- 影响模块：derived-memory evidence resolver and candidate promotion policy
- 风险等级：P0
- 用户可感知变化：候选自身 ID、内容哈希、决定/晋级 ID 即使被伪装成既有 evidence event，也不会被当作可验证来源；该候选保持主人审核状态。

### 新增或修改的自动验收

- [x] 预置 `evidence_recorded(entity_id=candidate_id)` 的自引用回归：保持 `pending_owner_review` 并返回 `evidence_reference_unverifiable`。
- [ ] Task 6 focused、Task 1–5 回归、`py_compile`、`git diff --check`、acceptance sync、local handoff：根代理在双提交后复读。

### 回滚

- 回滚：回退 `2663a4cf40c267767036c1e18a90df0f8bd10036` 与对应文档提交；不触碰 Vault、原始证据或主人配置。

## 2026-08-26 · Phase 1 Automatic Memory · Task 6 repair round 1 · fail-closed promotion and replay

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`939407fc47b4f374bb52de146348180e808a395a`
- 影响模块：promotion risk/confidence policy, existing StateDatabase evidence resolution, derived projection replay and recovery idempotency
- 风险等级：P0
- 用户可感知变化：所有高风险 memory type、非有限/非数值置信度、无法从既有来源/证据事件验证的引用均停留在主人审核；伪造 content hash 被拒绝。清空可重建索引后可从既有候选/决定事件恢复当前派生记忆，失败重试不会重复激活或恢复审计。
- 数据或安全边界变化：证据验证只读取既有 StateDatabase/source read model，不创建第二事实源；重建只恢复 active derived projection，不写 Vault/Core/原始证据。

### 新增或修改的自动验收

- [x] `tests/test_auto_memory_promotion.py`：41 passed，覆盖高风险类型矩阵、bool/字符串/NaN/Infinity 置信度、不可验证证据、真实性哈希、失败后成功恢复幂等和事件重放重建。
- [ ] Task 6 focused、auto-review、memory/retrieval/lifecycle 与 Task 1–5 回归、`py_compile`、`git diff --check`、acceptance sync、local handoff：根代理在双提交后复读。
- [ ] Qdrant/真实 Production Vault/主人 UI 与 M5 真机验收：仍不在本轮范围。

### 回滚

- 回滚：回退 `939407fc47b4f374bb52de146348180e808a395a` 与对应文档提交；不触碰 Vault、原始聊天证据或主人配置。

## 2026-08-26 · Phase 1 Automatic Memory · Task 6 · safe derived-memory promotion

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`63ee78fb4bcbb7034926356026907fa0c6fd12e0`
- 影响模块：`src/auto_review/promotion.py`, automatic-review candidate provenance, rebuildable `MemoryDatabase` derived projection
- 风险等级：P0
- 用户可感知变化：聊天证据先保存为带来源、置信度、权威、提取器版本和风险标记的候选；只有 `confidence >= 0.90`、有直接用户/当前权威项目证据、可验证来源且无冲突/高风险时，才自动进入可重建 current projection。Core、身份、秘密、权限、医疗/法律/金融/安全及不可逆内容必须主人明确确认。
- 数据或安全边界变化：自动激活只写可重建 `lingji_memory.db` 派生投影，不写 Obsidian Vault、Core Memory 或正式知识；决定和审核事件追加写入既有 `StateDatabase`。主人审批/拒绝使用 expected content hash 防止过期操作；失败投影保持 `error`，不假报激活，原始证据保留。

### 新增或修改的自动验收

- [x] `tests/test_auto_memory_promotion.py`：覆盖阈值、证据、冲突/重复、高风险类别、持久化来源链、幂等、版本重算、主人 hash 确认和投影失败。
- [x] `tests/test_auto_review_core.py` 与相关 memory lifecycle/retrieval 回归不得回归（focused 40 passed）。
- [ ] Task 1–5 focused 回归、涉及文件 `py_compile`、`git diff --check`、`scripts/check_acceptance_sync.py`、`scripts/check_local_execution_handoff.py` 全部 PASS；由根代理在产品/文档双提交后复读。
- [ ] Qdrant/真实 Production Vault/主人 UI 与 M5 真机验收：由根代理另行执行；本任务不读取真实 Vault、不宣称 Phase 1 完成。

### 回滚

- 回滚：回退 Task 6 产品 Commit；只删除可重建派生索引和测试临时数据，不触碰 Vault、原始聊天证据、主人配置或第三方 AI 软件。

## 2026-08-26 · Phase 1 Automatic Memory · Task 5 final closeout · Qdrant retry truth and raw TOCTOU

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`2fb0d7a4b2a81b1248bf1d81b783e2b26ee30e10`
- 影响模块：Obsidian managed-derived migration, Qdrant deletion retry state, raw ownership/hash/symlink validation
- 风险等级：P0
- 用户可感知变化：Qdrant 删除失败会持续显示 `planned/pending_rebuild`，重复执行会重试并在成功前不假报完成；raw copy 在 backup/unlink 前重新验证路径、regular-file、symlink、ownership 和内容哈希。
- 数据或安全边界变化：TOCTOU mismatch、symlink substitution、ownership change 或 hash change 均保留 raw source；审计保存 pending vector IDs 与真实错误，不删除 Vault 或非授权 raw。

### 新增或修改的自动验收

- [x] Qdrant flaky provider：首次/重复失败保持 `planned + pending_rebuild=true`，成功重试后才 `applied + pending_rebuild=false`，审计 pending IDs 清空。
- [x] Raw symlink substitution 与 changed-hash：两者均返回 planned/error 且源文件或 symlink 保留，外部目标不变。
- [x] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_obsidian.py tests/test_obsidian_memory_scope.py tests/test_obsidian_memory_migration.py tests/test_obsidian_service.py tests/test_vault_layout.py tests/test_memory_retrieval.py tests/test_incremental_index_sync.py`：31 passed。
- [x] Task 1–4 回归：`./.venv/bin/python -m pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_automatic_memory_watcher.py tests/test_automatic_memory_scheduler.py tests/test_state_db_scheduler.py`：重跑 108 passed（首次有 1 个既有 scheduler timing flake，重跑通过）。
- [x] Direct import、涉及文件 `py_compile`、`git diff --check`：全部 PASS。
- [x] `scripts/check_acceptance_sync.py`、`scripts/check_local_execution_handoff.py`：全部 PASS。

### 回滚

- 回滚：回退 `2fb0d7a4b2a81b1248bf1d81b783e2b26ee30e10`；不触碰 Vault、Production 数据或主人配置。

## 2026-08-26 · Phase 1 Automatic Memory · Task 5 repair round 9 · import/symlink/move-out hardening

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`d39372b4e791d514ff5a8c1b2858de4e2cf47278`
- 影响模块：Obsidian package exports, fail-closed scope path handling, scoped incremental lexical synchronization
- 风险等级：P0
- 用户可感知变化：直接导入 `MemoryDatabase` 不再触发 Obsidian migration import cycle；通过 `..` 或外部路径的 symlink 在 canonicalize 前即被拒绝；授权 Obsidian 文件删除或移出 scope 后退出 current lexical retrieval，同时保留非 Vault/chat 投影。
- 数据或安全边界变化：migration exports are lazy-only; scoped sync records an internal rebuildable scope reason and never uses it to retire non-Vault sources.

### 新增或修改的自动验收

- [x] Direct smoke: `./.venv/bin/python -c "from src.retrieval.memory_db import MemoryDatabase; print(MemoryDatabase.__name__)"`：`MemoryDatabase`。
- [x] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_obsidian.py tests/test_obsidian_memory_scope.py tests/test_incremental_index_sync.py`：10 passed，含 import cycle、dotdot symlink、move-out/stale lexical 与 non-Vault 保留。
- [x] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_obsidian.py tests/test_obsidian_memory_scope.py tests/test_obsidian_memory_migration.py tests/test_obsidian_service.py tests/test_vault_layout.py tests/test_memory_retrieval.py tests/test_incremental_index_sync.py`：29 passed。
- [x] Task 1–4 全回归：`./.venv/bin/python -m pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_automatic_memory_watcher.py tests/test_automatic_memory_scheduler.py tests/test_state_db_scheduler.py`：108 passed。
- [x] 完整涉及文件 `py_compile`、`git diff --check`、`scripts/check_acceptance_sync.py`、`scripts/check_local_execution_handoff.py`：全部 PASS。

### 回归与回滚

- [x] `src.obsidian` migration classes remain publicly importable through lazy `__getattr__`; retrieval imports do not load migration eagerly.
- [x] Vault canonicalization handles macOS `/var` → `/private/var` aliases without weakening lexical symlink checks.
- 回滚：回退 `d39372b4e791d514ff5a8c1b2858de4e2cf47278`；不触碰 Vault、Production 数据或主人配置。

## 2026-08-26 · Phase 1 Automatic Memory · Task 5 · Obsidian scope isolation and derived migration

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`e98b724266b3f1d89ffeaa283ef8656a00c70f1c`
- 影响模块：`src/obsidian/memory_scope.py`, `src/obsidian/memory_migration.py`, Obsidian discovery/service, Vault memory entry points, incremental lexical sync
- 风险等级：P0
- 用户可感知变化：普通旧 Obsidian Markdown 不再进入自动记忆投影；仅 `_LingJi/Memory Inbox`, `_LingJi/Memory Library` 或 `lingji_memory: true` 参与，`false` 最高优先级。修改/移入/移出使用同一 fail-closed scope 并刷新可重建 lexical/Qdrant 投影。
- 数据或安全边界变化：迁移仅清理 LingJi 自己的可重建 Memory DB/Qdrant/raw 投影，写入无正文审计标记；dry-run manifest 可校验和回滚。绝不写入、移动或删除 Vault；非 Vault/非 Obsidian raw 与 owner-confirmed/Core 记录保留。

### 新增或修改的自动验收

- [x] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_obsidian.py tests/test_obsidian_service.py tests/test_vault_layout.py tests/test_memory_retrieval.py tests/test_incremental_index_sync.py`：18 passed，Task 5 focused 与 Obsidian/retrieval 回归。
- [x] `./.venv/bin/python -m pytest -q tests/test_obsidian_memory_scope.py tests/test_obsidian_memory_migration.py`：scope、frontmatter/symlink fail-closed、manifest checksum、Vault hash/mtime/权限不变、managed raw ownership、idempotent apply/rollback、Core 保留。
- [x] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_automatic_memory_watcher.py tests/test_automatic_memory_scheduler.py tests/test_state_db_scheduler.py`：108 passed，Task 1–4 回归。
- [x] `./.venv/bin/python -m py_compile src/obsidian/memory_scope.py src/obsidian/memory_migration.py src/obsidian/discovery.py src/obsidian/service.py src/indexer/index.py src/retrieval/incremental_sync.py src/retrieval/memory_db.py src/memory/vault_layout.py`、`git diff --check`。
- [ ] Qdrant unavailable、真实 Production Vault、主人 UI/真机验收：需根代理在最终工作树执行；代码真实返回 `pending_rebuild`/错误，不假报成功。

### 回归与回滚

- [x] `VaultLayout.should_index()` 兼容语义保持不变；普通 PEMIS 索引仍可用，自动记忆入口改用独立 scope。
- [x] scoped incremental sync 不删除 chat/file/media 等非 Vault 投影；raw 仅接受 dedicated Obsidian root、显式 manifest 或 per-file Obsidian marker。
- 回滚：回退 Task 5 代码提交；不触碰 Production Vault 或主人配置。

## 2026-08-26 · Phase 1 Automatic Memory · Task 4 修复轮 4 · runner contract and terminal lease cleanup

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`b8808014062aafa0374e291ba694f276515cf5ab`
- 影响模块：automatic-memory scheduler runner invocation、scan terminal transitions and scheduler lease cleanup
- 风险等级：P0
- 用户可感知变化：真实 `SnapshotJobRunner.run(scan_id, crash_at=...)` 可由 scheduler 正确调用，不会把 source id 当作 crash control；来源失效、撤销、暂停、完成、失败路径都会清理 scheduler lease，授权恢复后 retry/reconcile 可立即继续。
- 数据或安全边界变化：继续复用既有 `automatic_memory_scans` 和 `StateDatabase`；不新增数据库、队列或事实源。通用二参 runner 仍按既有 `(scan_id, source_id)` 契约注入，SnapshotJobRunner 按参数名识别其 `crash_at` 控制参数。

### 新增或修改的自动验收

- [x] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_watcher.py tests/test_automatic_memory_scheduler.py tests/test_state_db_scheduler.py`：37 passed，含真实 SnapshotJobRunner scheduler 集成、paused 兼容路径、失效/撤销终态 scheduler lease 清理与恢复执行。
- [x] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_automatic_memory_adapters.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_worker.py`：137 passed，3 warnings（Task 1–3 与 queue/worker 回归）。
- [x] `./.venv/bin/python -m py_compile src/automatic_memory/watcher.py src/automatic_memory/scheduler.py src/scheduler/cron.py src/storage/state_db.py src/config.py`、`git diff --check`。
- [ ] `./.venv/bin/python scripts/check_acceptance_sync.py`、`./.venv/bin/python scripts/check_local_execution_handoff.py`：由根代理在文档提交后复读执行。

### 回归项与边界

- [x] 保持 Task4 前序跨实例 single-flight、scheduler lease heartbeat/过期恢复、direct revoke 快速停止、listener/watcher generation 隔离、普通二参/三参/可变参 runner 注入、SnapshotJobRunner paused resume、授权/symlink 安全。
- [x] 终态清理覆盖 `unsupported`、`degraded`、`expired` trigger、`revoke -> cancelled`、`pause -> paused`、`complete -> completed` 和 `failed` 路径；旧数据库 trigger 会在初始化时重建以应用最新清理逻辑。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK4_FIX4_`
- 测试仅使用 pytest 临时目录、脱敏 SourceRecord 和临时 SQLite/raw；无真实聊天、Vault、凭据或持久 Artifact。
- 回滚：回滚产品 Commit `b8808014062aafa0374e291ba694f276515cf5ab`，不触碰主人数据。

### 最终报告

- 报告路径：本地调度报告继续由 `.superpowers/` 忽略；正式证据为本条目与测试输出。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 4 修复轮 3 · cross-instance lease and lifecycle races

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`a9d5c680b6b5c0424aa83e98d6b5b39d3fe68049`
- 影响模块：automatic-memory scan scheduler lease、source lifecycle terminalization、watcher generation and non-blocking revoke
- 风险等级：P0
- 用户可感知变化：共享 `StateDatabase` 的多个 scheduler 只允许一个 scan runner；scheduler lease 支持 heartbeat 与过期恢复；来源在运行中进入 `unsupported`、`degraded` 或 `expired` 时不会遗留 `running` scan；旧 watcher/listener 的迟到清理或回调不会影响新生命周期，撤销通知不再等待阻塞 watcher。
- 数据或安全边界变化：复用既有 `automatic_memory_scans` 与 `StateDatabase`，不新增数据库、队列或事实源；SnapshotJobRunner 的既有 scan lease/终态保持兼容。

### 新增或修改的自动验收

- [x] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_watcher.py tests/test_automatic_memory_scheduler.py tests/test_state_db_scheduler.py`：30 passed，覆盖跨实例 single-flight、scheduler lease、来源中途终态化、watcher generation、非阻塞 revoke、listener generation 与既有 Cron 回归。
- [x] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_automatic_memory_adapters.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_worker.py`：137 passed，3 warnings（Task 1–3 与 queue/worker 回归）。
- [x] `./.venv/bin/python -m py_compile src/automatic_memory/watcher.py src/automatic_memory/scheduler.py src/scheduler/cron.py src/storage/state_db.py src/config.py`、`git diff --check`。
- [ ] `./.venv/bin/python scripts/check_acceptance_sync.py`、`./.venv/bin/python scripts/check_local_execution_handoff.py`：由根代理在文档提交后复读执行。

### 回归项与边界

- [x] 保持 backend 异常审计、single-flight、direct revoke 立即停止、failed retry、`None` fail-closed、scheduler_jobs lease/DB claim、普通 Cron、5/900/86400、授权/symlink 安全。
- [x] 修复轮 3 不把 focused 与 Task 1–3 回归合计为一条；两条命令分别记录为 30 passed 与 137 passed。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK4_FIX3_`
- 测试仅使用 pytest 临时目录和脱敏 SourceRecord；无真实聊天、Vault、凭据或持久 Artifact。
- 回滚：回滚产品 Commit `a9d5c680b6b5c0424aa83e98d6b5b39d3fe68049`，不触碰主人数据。

### 最终报告

- 报告路径：本地调度报告继续由 `.superpowers/` 忽略；正式证据为本条目与测试输出。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 4 · watcher and persistent reconciliation

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`c6d9ebecd6007c5b61f5d09aa5c1a9c85aa25194`
- 影响模块：`watchfiles==1.2.0` observation、existing `CronScheduler` lifecycle、automatic-memory source scan status and reconciliation events
- 风险等级：P0
- 用户可感知变化：已授权来源在启动时增量处理；文件事件经 5 秒防抖后进入现有授权快照/Extraction Queue 入口；事件丢失由 15 分钟 reconciliation 和每日 integrity 任务补偿；Desktop 后续可读取真实扫描报告、错误和下一步。
- 数据或安全边界变化：监听器仅观察授权 root，不读取第三方凭据、Cookie、Token、私有数据库或进程；不写入第三方目录，不新增队列、数据库或并行调度器。暂停、撤销、unsupported 和单来源故障均阻止新工作并保留审计事实。

### 新增或修改的自动验收

- [x] 修复轮 1 RED 后运行 `./.venv/bin/python -m pytest -q tests/test_automatic_memory_watcher.py tests/test_automatic_memory_scheduler.py tests/test_state_db_scheduler.py`：25 passed，覆盖 backend 创建/迭代异常、5 秒防抖、重复事件抑制、路径越界、单源 watcher 停止、暂停/撤销隔离、同源 single-flight、非完整报告落库、持久 start/stop/pause/resume、事件静默后的 reconciliation、每日 integrity、running scan 重启复用。
- [x] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_automatic_memory_adapters.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_worker.py`：137 passed，Task 1–3 与 queue/worker 回归；另含 3 个既有 warning（FastAPI/httpx、测试 ZIP duplicate、Pydantic Config）。
- [x] `./.venv/bin/python -m py_compile src/automatic_memory/watcher.py src/automatic_memory/scheduler.py src/scheduler/cron.py src/storage/state_db.py src/config.py`、`git diff --check`。
- [ ] `./.venv/bin/python scripts/check_acceptance_sync.py`、`./.venv/bin/python scripts/check_local_execution_handoff.py`：由根代理在文档提交后复读执行。

### 回归项与边界

- [x] `watchfiles==1.2.0` 的 MIT provenance 已记录在 `.research/local-ai-memory-architecture/FINDINGS.md`；监听事件只是低延迟提示，持久 scheduler reconciliation 才是完整性来源。
- [x] Cron job 的 `run_on_start` 在重启时重新置为 due；已有 running/paused scan 通过现有 `SourceRegistry.start_scan` 复用，不创建重复 scan；单来源失败不会阻塞其他来源。
- [x] 所有扫描回调继续由调用方注入现有 Task 2 `SnapshotJobRunner`/queue；Task 4 不 claim/execute `automatic_memory_snapshot`，不触碰 Obsidian 正文、Vault 或真实本机任务单。
- [x] 修复轮 1：watch backend 的创建/迭代异常调用持久错误回调；同源 reconciliation 以 Future single-flight 合并并发触发；撤销/过期/unsupported 停止该源 watcher、禁用该源 Cron，global resume 不会重新启用；不完整报告将 scan 标为 `failed` 并保存错误。
- [x] 修复轮 1：现有 `scheduler_jobs` 增加兼容性 lease/heartbeat 字段；SQLite 原子 claim 回收 stale `running` job，两个 Cron 实例不能同时执行同一 due job；普通 Cron job 继续使用原有表和模式门禁。
- [x] 修复轮 2：revoke 与 reconcile 完成提交使用 SQLite 授权条件原子化，撤销先提交时 scan 保持 `cancelled`；SourceRegistry 生命周期 listener 让 direct revoke/unsupported 立即停止 watcher 和 source jobs，scheduler stop 会解绑旧 listener。
- [x] 修复轮 2：failed scan 下次触发自动调用既有 `retry_scan`；runner 返回 `None` 或不支持结果会失败落库；若 runner 自身已通过现有 lease 完成 scan，scheduler 会复用其已持久化的 `completed` 状态。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK4_`
- 测试仅使用 pytest 临时目录和脱敏 SourceRecord；无真实聊天、Vault、凭据或持久 Artifact。
- 回滚：回滚产品 Commit `c6d9ebecd6007c5b61f5d09aa5c1a9c85aa25194`，不触碰主人数据。

### 最终报告

- 报告路径：本地调度报告继续由 `.superpowers/` 忽略；正式证据为本条目与测试输出。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 3 · fail-closed source adapters

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`2b987e4ac13401e92104ad70ca54d1c185ad6a71`
- 影响模块：官方 ChatGPT 导出、版本化 Codex transcript、Generic AI History Inbox、Claude Desktop capability boundary、Extraction Adapter Registry
- 风险等级：P0
- 用户可感知变化：只接受官方 ChatGPT ZIP/JSON、明确版本的 Codex JSONL 与主人选定并带 History Inbox 标记的 JSON/JSONL/Markdown；Claude Desktop 在无官方导出时准确显示 `unsupported` 或 `consent_required`。
- 数据或安全边界变化：未知、损坏、恶意或未标记格式 fail-closed 并留下安全审计原因；不读取浏览器 profile、Cookie、Token、认证配置、私有数据库、Claude opaque storage，不扫描任意目录，不联网，不新增队列/数据库/原始事实源。

### 新增或修改的自动验收

- [ ] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_adapters.py`：覆盖 ChatGPT 官方结构、重复/损坏记录、整批 fail-closed、根目录/重复 ZIP 成员、全成员大小/压缩比、异常编码、conversation/message ID；Codex schema v1、未知 schema 正式 Pipeline 队列审计（含 `codex` 兼容 source type）、敏感祖先/symlink/授权 root、重复 ID 与 timezone/order；Generic History Inbox JSON/JSONL/Markdown、重复 ID、边界与 scoped external_id；Claude capability、默认 bootstrap 注册与 Registry approved boundary。
- [ ] `./.venv/bin/python -m pytest -q tests/test_chatgpt_importer.py tests/test_structured_ingestion.py tests/test_capture_adapters.py tests/test_codex_writeback.py tests/test_mcp_extraction_submission.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_hardening.py tests/test_extraction_worker.py tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py`：Task 1/2 与既有 Extraction/旧 Codex adapter 回归。
- [ ] `./.venv/bin/python -m py_compile src/extraction/adapters/chatgpt.py src/extraction/adapters/codex.py src/extraction/adapters/generic_ai_history.py src/extraction/adapters/claude_desktop.py src/extraction/registry.py`、`git diff --check`、`./.venv/bin/python scripts/check_acceptance_sync.py`、`./.venv/bin/python scripts/check_local_execution_handoff.py`。

### 回归项与边界

- [ ] 所有 adapter 继续复用 `ExtractionAdapter`、`ExtractionRequest`、`ExtractionBatch`、现有 raw snapshot/Extraction Queue；通用 pipeline 不 claim/execute `automatic_memory_snapshot`。
- [ ] 未知输入只进入明确失败/审计原因，不猜测、不生成消息；不修改 Production/Vault，不创建 ACTIVE 本机任务或 Artifact。
- [ ] 修复轮验证：不得通过 conversation 静默去重、跳过损坏消息、放宽路径敏感组件、移除授权 root、降低时间/ID校验或绕过旧 adapter 回归。
- [ ] 修复轮 2：ChatGPT 预解析校验 metadata object 与 ZIP 全成员安全后才读取 root；单会话 normalize 失败时整批拒绝且错误不泄漏本地路径；Codex 未知 schema 通过正式 enqueue/process 记录具体 reason；Claude 只暴露 capability、不读取 opaque storage。
- [ ] 修复轮 3：ChatGPT 对 ZIP 全成员（含目录）执行兼容的成员数上限，并预验证 title/current_node/parent、metadata model 与附件字段类型；`source_type=codex` 的显式 schema JSON 不再回退到旧工作报告 adapter，未知 schema 通过正式队列失败审计，旧无 schema JSON 工作报告保持兼容。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK3_`
- fixture 仅为脱敏结构样例，无真实聊天、密钥或个人数据；pytest 临时路径结束后自动清理。
- 回滚：回滚 Task 3 产品 Commit，不触碰主人数据、Production Vault 或历史验收 Artifact。

### 最终报告

- 报告路径：本地调度报告继续由 `.superpowers/` 忽略；正式证据为本条目与测试输出。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 2 fix round 9 · terminal snapshot cleanup precedence

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`b979b66f14d6e64e40049ee6f7258c259bfceb30`
- 影响模块：snapshot staging cleanup terminal-state and lease ownership decision
- 风险等级：P1
- 用户可感知变化：合法 owned snapshot temp 在 scan 明确进入 completed/cancelled/failed/paused 终态时可确定性回收，即使当前 lease_id 为 NULL；running temp 只有编码 lease 与当前 lease 匹配且 expiry 明确过期时才可回收。
- 数据或安全边界变化：scan 缺失、查询异常、字段异常、未知状态、NULL/非法 expiry、mismatched lease、malformed 或超长 owned token 均 fail-closed 保留；普通 legacy `.snapshot-*.tmp` 仍按 24 小时策略处理。

### 新增或修改的自动验收

- [ ] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_extraction_queue.py tests/test_extraction_worker.py`：76 passed，覆盖终态 NULL lease 回收、running mismatch/NULL expiry 保留、unknown/overlong/malformed owned 保留、legacy 24h、跨来源 active temp、protected snapshot job、lease/crash/idempotency。
- [ ] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_hardening.py tests/test_extraction_worker.py tests/test_structured_ingestion.py`：47 passed，Task 1/extraction/queue/worker 回归（含 1 个既有 FastAPI deprecation warning；更正历史 round 8 条目误写的 104）。
- [ ] `./.venv/bin/python -m py_compile src/automatic_memory/snapshot.py src/automatic_memory/checkpoint.py src/extraction/pipeline.py src/extraction/queue.py src/extraction/sink.py src/storage/state_db.py`、`git diff --check`、`./.venv/bin/python scripts/check_acceptance_sync.py`、`./.venv/bin/python scripts/check_local_execution_handoff.py`。

### 回归项与边界

- [ ] 保持 non-UTC/invalid expiry fail-closed、unknown/overlong owned 保留、普通 legacy `.snapshot-*.tmp` 24 小时策略、活跃跨来源保护、protected snapshot job 边界、lease/crash/idempotency、source/raw 不改动。
- [ ] 不扩展 Task 3 或其他架构；不新增数据库、队列、raw archive、watcher、适配器或消费者。
- [ ] Full-suite 既有 Desktop assertion mismatch 与缺少 `python` executable 的 `test_second_brain` baseline failures 不修改、不掩盖；内部 SDD 报告继续 ignored。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK2_FIX9_`
- 本轮 pytest 临时授权 root、SQLite、raw、queue 与 crash marker 自动清理；未创建持久 debug 目录或日志。
- 回滚：回滚产品 Commit `b979b66f14d6e64e40049ee6f7258c259bfceb30`，不触碰主人数据。

### 最终报告

- 报告路径：本地调度报告继续由 `.superpowers/` 忽略；正式证据为本条目与测试命令输出。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 2 fix round 8 · unknown owned snapshot retention

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`78979cbf3852b22a9a8152f35f115eae3adf3f18`
- 影响模块：snapshot staging cleanup parsing and unknown owned-file retention
- 风险等级：P1
- 用户可感知变化：合法但无法关联到现有 scan 的 owned snapshot 临时文件不再因 24 小时 age 策略被删除；超长或异常 scan/lease/token 文件名按 unknown owned 保留。普通 legacy `.snapshot-*.tmp` 仍按 24 小时阈值清理。
- 数据或安全边界变化：只有明确找到 scan 且状态为 completed/cancelled/failed/paused，或当前 running lease 已明确过期时，owned staging 才允许回收；scan 查询异常、缺失或 owner 编码不可信均 fail-closed 保留。

### 新增或修改的自动验收

- [ ] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_extraction_queue.py tests/test_extraction_worker.py`：71 passed，覆盖不存在 scan 的有效编码 stale owned temp 保留、超长 token stale owned temp 保留、malformed/异常 DB、lease expiry、legacy 24h 与既有 Task 2 lease/crash/idempotency 边界。
- [ ] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_hardening.py tests/test_extraction_worker.py tests/test_structured_ingestion.py`：47 passed，Task 1/extraction/queue/worker 回归（含 1 个既有 FastAPI deprecation warning；原记录的 104 为计数错误，已按真实命令输出更正）。
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
