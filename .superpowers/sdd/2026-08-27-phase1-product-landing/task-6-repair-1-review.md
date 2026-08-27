# Task 6 Repair Round 1 — Independent Security / Quality Review

日期：2026-08-28  
审查代理：Luna（独立只读审查）  
工作树：`/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`  
分支：`codex/phase1-automatic-memory`  
Reviewed HEAD：`b225a74`  
Diagnostic：`361733b3c660e1b5dc36e5500e1f2436da41572e`  
Repair commits：`04eb1d3`、`b6e8c77`、`31f40a3`、`3265ae3`、`b225a74`  
权威 Task 6 报告：`docs/TEST_REPORTS/PHASE1_AUTOMATION_UI_GATE.md`

本轮只读审查。除本报告外不修改产品、测试、任务单、正式 Vault 或主人数据。
当前 `LOCAL_EXECUTION_TASK.md` 为 `IDLE`，未启动真实 8766/8767、Artifact、release、Production/Vault
或主人验收。

## 1. 最终结论

```text
Spec: FAIL
Quality: NEEDS_FIXES
Critical: 0
Important: 5
Minor: 3
Task 6 disposition: NOT_ACCEPTED
```

修复已正确关闭诊断中的旧 scan fallback 和 `ReconciliationReport` 身份缺失，且把 scan/work identity 写入
reconciliation event。可是 packaged 十场景仍不能形成可发布 receipt：独立运行在真实 sidecar kill 后的恢复
断言失败；Qdrant 场景仍没有 packaged ingestion 产生的正式 lexical record；idle heartbeat 仍为诚实的
`NOT_MEASURED/BLOCKED`。按 Task 6 规则，任一核心场景阻塞或 heartbeat 未满足都不能 ACCEPT。

## 2. 独立命令与证据

### 2.1 Packaged focused gate

命令：

```text
./.venv/bin/python -m pytest -q tests/integration/test_automatic_memory_packaged_flow.py --tb=short
```

结果：

```text
1 failed, 1 passed, 1 warning, 126.80s
```

失败位置 `tests/integration/test_automatic_memory_packaged_flow.py:728`：真实 sidecar 已在持久 progress barrier
后通过 `process.kill()` 终止，重启后恢复 POST 返回的 `scan_id` 与 crash barrier 的 `scan_id` 不一致。该测试
在生成两轮完整场景结果和 receipt 前失败，因此没有可发布的 30%/70% recovery receipt。

### 2.2 直接 52 项回归

命令：

```text
./.venv/bin/python -m pytest -q tests/test_automatic_memory_scheduler.py tests/test_automatic_memory_runtime.py tests/test_automatic_memory_repair_round1.py --tb=short
```

首次独立运行：`51 passed, 1 failed, 1 warning`；失败为
`test_real_two_scan_flow_reports_reuse_and_exact_structured_identity_set` 的异步 Work Fact 终态读取，发生在队列
已空但 Work Fact 尚未完成投影。单测单独重跑及完整命令随后为 `52 passed, 1 warning`。因此回归最终可重复通过，
但该 timing-sensitive failure 记录为 Minor 稳定性风险，不作为成功证据的替代。

### 2.3 Rendered Desktop / static gates

```text
cd desktop/lingji-control && npm run test:e2e:memory
→ e2e_owner_memory_flow: PASS

./.venv/bin/python -m compileall -q ...
→ PASS

git diff --check 361733b3..HEAD
→ PASS

./.venv/bin/python scripts/check_acceptance_sync.py
→ PASS (changed files: 5, product-impacting files: 0)

./.venv/bin/python scripts/check_local_execution_handoff.py
→ PASS
```

Rendered E2E 使用 fake 8766-like server，只证明 UI 合同，不替代真实 packaged backend 十场景。

## 3. 已验证通过的边界

### 3.1 scan/work identity、single-flight、兼容性

通过项：

- `ReconciliationReport.scan_id`、`work_id` 作为尾部可选字段追加，旧的五/六参数 positional 构造保持兼容。
- `AutomaticMemoryScheduler._reconcile_once()` 在正常、already-claimed、失败和异常路径都绑定本次 `scan.scan_id`，
  并通过 `dataclasses.replace()` 返回 `automatic-memory:<scan_id>`。
- `AutomaticMemoryRuntime.scan_now()` 对 dataclass 只保留 scheduler 返回的身份；dict 仅从该结果中的 `scan_id`
  派生 work ID，不再调用 `list_automatic_memory_scans()` 选择第一条旧记录。
- reconciliation success/failure event 同时保存 `reason`、`scan_id`、`work_id`；测试等待器按 source、scan identity
  和 trigger reason 关联，不再使用旧 scan fallback。
- 同一进程的 `_inflight[source_id]` Future 合并 concurrent trigger；StateDB 的 one-active-scan transaction 和
  scheduler lease 在跨线程/跨进程场景继续提供 admission 保护。

这部分 Spec/Quality 为 PASS；它不覆盖 packaged crash harness 对自动 startup reconciliation 与手动 recovery
竞态的处理（见 I1）。

### 3.2 正式 composition 与生命周期

`run_packaged_control_api.py` → `run_control_api.py` → `build_extraction_pipeline()` → `AutomaticMemoryRuntime`
仍共用一个 canonical `lingji_state.db` / queue wrapper；automatic snapshot consumer、StructuredReadModelSink、
Work Fact callback 和已有 watcher/Cron composition 均保持。没有新增 DB、queue、API family、promotion seam 或
retrieval algorithm。Task 6A 已有的 scheduler cleanup/start-stop serialization 在本轮未被回退。

## 4. Important findings

### I1（A）— 30%/70% crash matrix 仍不形成可发布 receipt，且恢复身份断言遇到自动 reconciliation 竞态

位置：`tests/integration/test_automatic_memory_packaged_flow.py:679-750`，独立失败 `:728`。

当前确实启动真实 packaged sidecar，并在持久 `progress >= ceil(total * 0.3/0.7)`、scan lease 和 scheduler lease
字段存在后 kill sidecar。问题是重启时 scheduler 的 `run_on_start` reconciliation 与显式 recovery POST 竞态：原 scan
可能由 startup reconciliation 完成，随后显式 POST 合法地开始一个新 scan，或反过来由 POST 完成原 scan 后 Cron 开始
新 scan。当前断言把 recovery response 必须等于 crash barrier scan 固定为唯一合法路径，因而独立运行失败；它没有
将“startup 已恢复原 scan”与“POST 选择新 scan”区分开，也没有生成完整 receipt。

即使该断言调整，当前 parity 仍只比较 30%/70% 的 set 长度（`len(...)`），不比较规范化后的 source/scan/job/raw/
structured identity 集合、终态 status、terminal scan 与所有 job 的对应关系；`terminal_before` 未参与终态断言，
crash matrix 也没有断言 duplicate counts 为零。`>=` barrier 允许跨过目标点，且未把 kill 前后的完整 lease/owner
证据落成独立 receipt 文件。

结论：真实 kill 已发生，但 30%/70% recovery、terminal identity/count parity、无 queued/duplicates 和 receipt
仍未证明。该项必须判 FAIL/NOT_ACCEPTED，不可用 exploratory output 或内存 dict 代替发布证据。

最小修复范围：只改 packaged integration harness/证据文档；建立明确 crash barrier 后的单一恢复协调方式，绑定
原 scan 的 terminal（无论由 startup reconciliation 还是 explicit recovery 完成），记录两者的 response/event；
使用各自 `run_root`，严格比较规范化 identity/status/queued/duplicate 集合，并写出脱敏 receipt。不得改 DB、lease
字段释放方式或产品 retrieval/promotion。

### I2（A）— Qdrant 场景没有 packaged ingestion → memory_documents/FTS 的正式接线

代码链事实：


```text
SnapshotJobRunner
→ ExtractionPipeline._execute_internal_snapshot
→ StructuredReadModelSink.upsert_bundle()
→ source_records / conversation_records / message_records
```

automatic snapshot 明确构造 `indexed=False`，并写入“Vault/index document publishing unavailable”。Structured sink
只写 structured source read model；没有把 message content materialize 为 `memory_documents`/`memory_chunks`，
也没有调用 `MemoryIndexCoordinator.sync()`。

正式检索链是：`MemoryGateway.search_memory()` → `HybridRetriever` → `MemoryDatabase.search_fts()` 与可选 semantic
provider；MCP `search_memory` 复用 Gateway；`ContextPackBuilder` 也复用 Hybrid，再通过 SourceQueryService 只为
已有 memory link 添加 evidence。它们不会把 `SourceReadModel.list_messages(q=...)` 的结构化消息结果纳入统一
Gateway/Hybrid/MCP/ContextPack 检索。`MemoryInspector` 的 `/api/memory/messages?q=...` 是现有结构化 message
LIKE 查询入口，但绕过 Gateway/Hybrid/Qdrant，不足以证明 Task 6 scenario 8。

因此这不是简单的测试遗漏，也不是应新增检索算法的问题：这是当前阶段 automatic-memory extraction/indexing
wiring 与统一检索合同之间的设计/接线缺口。现有 `memory_documents`/FTS 仍是正式 Hybrid lexical authority，
而 packaged ingestion 只停留在结构化 read model。当前 test 正确地把 scenario 8 标为 `BLOCKED`，没有被预置
Vault fact 自证污染。

最小接线边界（另开 bounded brief）：复用现有 extraction/indexing 和 `MemoryIndexCoordinator`/`MemoryDatabase`
合同，让 automatic structured rows 产生可重建、带 source/raw/message provenance 的正式 lexical projection，随后
由现有 Gateway/Hybrid semantic failure path 消费；不新增 store、queue、API、retrieval ranking/model、Qdrant
替代方案或自动 promotion。需要明确保持“不写主人 Vault Markdown”，memory DB/Qdrant 仍为可重建投影。

### I3（A / gate blocker）— scheduler idle heartbeat 仍无法满足 <=10s

`AutomaticMemoryRuntime.status()` 和 `/api/automatic-memory/runtime` 返回 `scheduler_heartbeat_age: null`，并给出
`unavailable: existing scheduler exposes no trustworthy idle heartbeat`。现有 scheduler lease heartbeat 只在 active
reconciliation 期间存在，SnapshotJobRunner scan lease heartbeat 只在 active scan 期间存在，终态会清空；CronScheduler
没有 loop heartbeat timestamp，ExtractionWorker 只有 per-job heartbeat。Work Fact `updated_at` 是事件/Outcome 投影
时间，不能代表 scheduler idle liveness。

该 `null` 是诚实行为而非通过信号；当前报告正确写为 `NOT_MEASURED/BLOCKED`，不能用终态 timestamp 冒充。
仅复用持久 active lease 可覆盖“扫描中”的 age，无法覆盖 idle scheduler，因此 <=10s gate 必须有新的真实 idle
heartbeat source。最小方案是扩展现有 CronScheduler loop（或其已有持久 runtime 状态）暴露/更新 last-heartbeat，runtime
从该 source 计算 age 并投影到现有 runtime DTO；若合同还要求 Work Fact DTO，只增加该现有字段映射，不能周期性伪造
Work Fact `updated_at`。不应另起 heartbeat daemon。

### I4（A）— raw evidence harness 对 metadata/body guard、Work Fact 和 cleanup 的若干断言仍不足

- packaged scenario 1 仅观察 `discovered`、StateDB sources=0、raw=0；没有在 packaged path 对 candidate file 安装
  body-read guard/hash sentinel。静态 `discover_source_metadata()` 的“只用路径”实现可信，但 raw evidence 没有独立
  证明 body 未读。
- scenario 7 断言 bad extraction job failed、healthy job completed 和 source identity isolation，但未读取两个
  `work_id` 的 terminal Outcome/next actor；因此不能证明失败/成功均投影到 Work Fact。
- scenario 6 记录 pause/resume、expiry/revoke source status，但未断言 revoke 后对应 scan/job 的 cancellation、
  watcher cleanup 或 owner-visible next action。
- `PackagedSidecar.stop()` 记录 `child_inventory_after_exit`，但没有断言其为空；只对主 PID wait 并用 port bind
  验证可重绑定，无法排除孤儿 child。该证据不足在 crash 场景尤为重要。

这些缺口使十场景“raw evidence”不完整，必须在下轮 harness bounded 修复中补齐，不能把当前 clean-run 表述升级为
全部 PASS。

### I5（A / cleanup/security）— start 失败路径可能泄漏 sidecar，且进程库存检查在 Windows 不可用

`PackagedSidecar.start()` 启动子进程后，token 文件不存在、token 为空或 ping 失败会直接 `assert`/抛异常；因为
`_sidecar()` 的 context manager 尚未 yield，`finally: sidecar.stop()` 不会执行，已启动的 process 可能遗留。该路径
也没有在失败时保留并复核 stderr 尾部。

此外 `_process_inventory()` 固定调用 Unix `ps -axo`；Windows/PowerShell 5.1 下异常被吞掉并返回空列表，测试会把
“无法检查”当成空库存。`child_inventory` 也未在场景断言中要求为空。这不改变当前 macOS 试跑结果，但不满足
跨平台 PID/child cleanup 的安全证据合同。

最小范围：仅改 harness 的启动异常清理、可移植的 PID/child inventory fallback 和显式 unknown/fail-closed 断言；
按 PID/实例停止，禁止全量杀 Python，不改产品进程管理。

## 5. Minor findings

### M1 — same-root idempotency raw set 被记录但未断言

`idempotency_before["raw"]` 与 `idempotency_after["raw"]` 均写入 evidence，但只断言 structured identity set 相等，
没有 `raw` 集合相等断言；报告“raw SHA set unchanged”因此属于未验证描述。补一个 exact equality，不得用数量替代。

### M2 — Qdrant failure injection helper 的参数未使用

`PackagedSidecar(..., qdrant_failure=False)` 的参数未被 `start()` 或 scenario 调用；scenario 8 的正式 semantic failure
是在 sidecar 停止后进程内替换 provider。由于 scenario 当前明确 BLOCKED，这没有伪造 PASS，但命名和证据接口容易
误导，应删除未用参数或在后续 lexical bridge 后接正式 client failure seam。

### M3 — 52 项回归存在异步 Work Fact timing flake

首次组合运行在 queue 已为空时立即检查 Work Fact，出现一项终态未完成；单独重跑和再次完整命令通过。该测试应等待
对应 work outcome，而不是把 queue empty 等同于 Work Fact projection complete；当前只列稳定性风险，不改变 Task 6
整体 NOT_ACCEPTED。

## 6. TDD、范围、安全与兼容审计

- TDD：repair 文档保留了 race/old-scan RED（旧 `ReconciliationReport.scan_id` 缺失）和 focused GREEN `52 passed`；
  本轮未见删测试、skip、降断言或修改失败为通过。可是 fresh packaged RED/receipt 未闭环。
- 产品范围：实际产品 diff 仅 `src/automatic_memory/runtime.py` 与 `scheduler.py`；没有 DB schema、queue、retrieval、
  promotion、UI 或 API family 变化。测试改动集中在 packaged harness 与直接 identity regressions；同步门禁报告
  product-impacting files=0。文档改动与 CHANGE_ACCEPTANCE_LOG、PROJECT_STATUS、CODE_MAP 已同步。
- single-flight/race：已通过 per-source Future、StateDB atomic one-active-scan、scheduler lease/heartbeat 和 exact
  ID event binding；发现 failure 是 crash harness 与 startup Cron 的协调问题，不应再退回 list-first fallback。
- 权限/数据隔离：当前 packaged 测试使用 pytest temp roots，automatic snapshot 不写 Vault Markdown；sentinel 以显式
  VaultLayout bootstrap allowlist 比较，第三方树不允许排除。未访问 Production/Vault/主人数据。
- Secret/path：未发现提交 API key/token/cookie、个人绝对路径、任意 host/path 放宽；token 为临时 Acceptance root
  本地文件。报告证据应继续脱敏。
- PowerShell 5.1：本轮没有修改 PowerShell 产品入口；但 packaged evidence 使用 Unix `ps`，因此跨平台 cleanup
  检查目前不具备可移植性（I5）。
- 异常：正式产品已有宽边界 lifecycle cleanup 保护；本轮新增 harness 的 `_wait_until` 只吞网络/OSError，不能将
  crash failure 伪装成 PASS。start exception cleanup 缺口仍需修。

## 7. Per-scenario disposition

| 场景 | 当前判断 | 依据 |
|---|---|---|
| 1 metadata-only/body guard | NEEDS_FIXES | metadata-only code PASS；packaged raw body-read guard 未证明（I4） |
| 2 authorization/startup + same-root idempotency | PARTIAL PASS | exact identity/reuse/structured set PASS；raw set assertion 缺失（M1） |
| 3 file event | PASS（证据级） | event reason + exact scan ID + measured latency |
| 4 suppressed event/reconciliation | PASS（证据级） | 无 manual POST；生产 reconciliation reason + exact ID |
| 5 30%/70% crash/restart | FAIL | fresh run identity mismatch；无完整 parity/receipt（I1） |
| 6 pause/resume/revoke/expiry | NEEDS_FIXES | source status 证据在；job/scan cancellation与Work Fact证据不足（I4） |
| 7 corrupt isolation | NEEDS_FIXES | job/source isolation 在；Work Fact terminal 未证明（I4） |
| 8 Qdrant outage + lexical fallback | BLOCKED | packaged ingestion 无 memory_documents/FTS lexical projection（I2） |
| 9 sleep/wake equivalent | PASS（证据级） | restart + mtime jump，生产 reconciliation reason + exact ID |
| 10 recursive sentinel/cleanup | NEEDS_FIXES | sentinel diff 通过；child/start-failure cleanup evidence不足（I4/I5） |

## 8. 后续 bounded briefs（最多两个）

### Task6H — measured idle heartbeat（独立 brief）

只允许修改现有 scheduler/runtime status 所需的最小产品/测试/报告范围：在现有 CronScheduler loop 或等价既有
持久 runtime 状态中暴露真实 last-heartbeat；由 AutomaticMemoryRuntime `/api/automatic-memory/runtime` 投影
`scheduler_heartbeat_age`，补 active/idle/restart/stale 的 <=10s 测试。可把该字段映射到现有 Work Fact DTO（若合同
要求），但禁止用 Work Fact terminal `updated_at`，禁止另建 heartbeat daemon、DB、queue、API 或第二状态源。
不得改 retrieval、Qdrant、promotion、Vault 或 Desktop feature。

### Task6L — formal lexical bridge + packaged recovery harness（独立 bounded brief）

先以 RED 固定两类失败，再在一个有界变更中完成：

1. 复用现有 extraction/indexing 合同，把 packaged automatic structured rows 投影为可重建
   `memory_documents`/`memory_chunks`/FTS 记录，并保留 source/raw/message provenance；接入现有
   `MemoryIndexCoordinator`，让 Gateway → Hybrid → MCP/ContextPack 正式消费；不写主人 Vault Markdown，不新增
   retrieval 算法、store、queue、API、Qdrant provider 或 promotion。
2. 仅改 integration harness 证明 scenario 5 的真实 sidecar kill、startup-vs-explicit recovery 选择、精确
   terminal identity/status parity、queued/duplicate=0、独立 receipt；补 scenario 1 body guard、scenario 6/7
   Work Fact/cancellation、scenario 10 child/start-failure cleanup，并修 idempotency raw set assertion。Windows
   inventory 不可用时必须 fail closed，不能返回空列表冒充 clean。

若 root 认为 lexical bridge 与 crash harness 应完全分离，则先拆为两个更小 brief；在两者完成前 Task 6 仍
`NOT_ACCEPTED`。不得通过预置 Vault fact、fallback/default、skip 或手工 DB lease mutation 绿灯。

## 9. Final disposition

```text
Reviewed HEAD: b225a74
Spec: FAIL
Quality: NEEDS_FIXES
Critical: 0
Important: 5
Minor: 3
Task 6: NOT_ACCEPTED
Task 6H: REQUIRED
Task 6L: REQUIRED
Rendered Desktop E2E: PASS (UI-only evidence)
52 regression: final rerun PASS; first combined run 51/1 timing failure recorded
Packaged ten-scenario gate: FAIL (1 failed, 1 passed)
Qdrant packaged lexical evidence: BLOCKED
Idle heartbeat <=10s: NOT_MEASURED/BLOCKED
Release/Artifact/live 8766/8767/Production/Vault/owner acceptance: NOT_TESTED / unclaimed
Acceptance sync: PASS
Local handoff: PASS
```

