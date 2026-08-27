# Task 6 Packaged Automation E2E — 独立诊断审查

日期：2026-08-28；审查：Luna（独立只读诊断）

工作树：/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory
分支/HEAD：codex/phase1-automatic-memory / fe7f526
Task6 commits：6a50859、1c71c14、d5e2560、fe7f526
权威报告：docs/TEST_REPORTS/PHASE1_AUTOMATION_UI_GATE.md，仍为 IN_PROGRESS / NOT_ACCEPTED。

## 1. 范围、命令与结论

已读取 AGENTS、PROJECT_STATUS、CODE_MAP、ACCEPTANCE 入口文档、Task6 plan、Task6/Task6A 报告与 Task6A 最终修复审查，并沿读 packaged integration、run_packaged_control_api、run_control_api、automatic-memory runtime/scheduler/source registry/checkpoint/snapshot/path policy、extraction pipeline/worker/queue、StateDB、正式 HybridRetriever/Gateway 及 Desktop smoke/E2E 注册。没有修改产品、测试、任务单或既有报告；本报告是唯一新增文件。未访问 Production/Vault、Artifact、真实 8766/8767 或主人数据。

必要复现：

~~~text
./.venv/bin/python -m pytest -q tests/integration/test_automatic_memory_packaged_flow.py --tb=short
→ 1 failed, 1 passed, 1 warning in 171.03s

tests/integration/test_automatic_memory_packaged_flow.py:556
assert all(run["final"]["queued"] == 0 for run in all_runs)
KeyError: 'queued'
~~~

独立 Desktop 命令：

~~~text
cd desktop/lingji-control && npm run test:e2e:memory
→ e2e_owner_memory_flow: PASS（约 75 秒）
~~~

该 E2E 使用 fake authenticated 8766-like server、Vite 和浏览器，只证明 UI rendered 合同，不能替代真实 packaged backend 十场景证据。

~~~
Spec compliance: FAIL
Task quality: NEEDS_FIXES
Critical: 1（A：gate harness 自身崩溃）
Important: 10（B：1；A：8；C+A：1）
Minor: 4
Task6: NOT_ACCEPTED
~~~

## 2. 直接产品链核对

正式组合的基本链是连通的：run_control_api 建立一个 StateDatabase 和由 build_extraction_pipeline 创建的 queue/pipeline，再注入 AutomaticMemoryRuntime；runtime 校验 state DB、queue、pipeline.queue、registry、scheduler 都解析到同一个 SQLite 文件。SnapshotJobRunner 使用已有 internal snapshot queue consumer，worker 的 process_pending 先处理 internal jobs，再处理普通 jobs，StructuredReadModelSink 写入可重建 lingji_memory.db。internal job 不能由普通 enqueue/execute 入口伪造；撤销/过期会重新做授权校验；automatic-memory 快照不向 Vault 发布 Markdown；HybridRetriever 在 semantic provider 抛错时保留 lexical 结果。这些不是当前 pytest 失败根因。

## 3. Critical

### C1（A）— 最终断言字段路径错误

位置：integration 第 477、556 行。_run_clean_acceptance 构造 final.state.queued，最终从 final.queued 读取，导致上述 KeyError。它证明 harness 不能收口，不证明产品队列失败或通过；两轮场景执行后仍没有可发布的完整证据。最小处理只改测试路径并重跑，不得使用默认值、skip 或删断言掩盖。

## 4. Important

### I1（B）— scan_id/work_id contract 丢失且存在旧 scan race

位置：scheduler.py 209–325、runtime.py 284–299、automatic_memory_api.py 86–94；harness fallback 在 integration 306–322。

Scheduler reconcile 已持有本次 scan，但 ReconciliationReport 没有 scan_id；runtime.scan_now 在 reconcile 返回后按同 source 的 list_automatic_memory_scans 第一条拼 work_id。列表虽按 updated_at DESC 排序，却不能保证这是本次调用：watcher/Cron 或并发同源 Future 可在返回前创建/更新另一条 scan。因而 /api/automatic-memory/scan 不返回本次 durable scan identity 是真实产品 wiring 缺口；测试按同 source 第一条 fallback 又会把旧 scan 当当前 scan，污染证据。

最小产品边界需 root-approved mini-brief：仅让现有 scheduler/runtime 传出实际创建或合并的 scan_id 与 automatic-memory:scan_id work_id，现有 route DTO 传播它；必要文件限 src/automatic_memory/scheduler.py、runtime.py、src/control/automatic_memory_api.py，不新增 store、queue、API family 或状态源。

### I2（A）— 30%/70% crash 不精确且 parity 断言无意义

位置：integration 485–537。被 kill 的 request_process 是立即退出的空 python 进程，与 sidecar 无关。真实 sidecar 只是轮询 durable progress >= 阈值后再 kill，可能跳过目标进度；没有 runner crash barrier，也没有保存 kill 前 lease/owner 的证据。results[percentage] 把 structured count 用 outer root（crash-run-*），真实数据库在 run_root/30pct 或 run_root/70pct，故路径错误，通常读到 0。30/70 只比较 job 数量，不比较 crashed scan_id、source/scan/job terminal identities、status、raw/structured identity sets；terminal 还从所有 scans 取第一条 completed。

这不能证明 30%/70% 崩溃后完全相同的 terminal 结果。只改测试：用正式 runner 的受控 progress seam 或 durable barrier，记录 kill 前后 scan_id、progress/total、lease owner/expiry、每个 job 状态和 structured identity set，并严格用 run_root；禁止 DB 篡改释放 lease。

### I3（A）— 两个 clean roots 不是 same-root idempotency

位置：integration 541–556。run-1/run-2 是两套全新目录、source IDs 和 SQLite；两轮之间没有同一 root 重扫与 inserted/reused/duplicate delta。_run_clean_acceptance 虽在同 root 内多次 scan，却每次改了输入，未保存重复输入前的 source/conversation/message/memory identity 基线，也未断言同内容第二次 queued=0、reused 增加且集合不变。零 duplicate 只能证明各自新 fixture 当前没有重复行，不能满足计划要求的同一 root 重扫证明。

最小处理：保留一套完整 root，在相同 bytes/mtime 语义下第二次重扫并比较 delta；另一套若保留，只作 fresh-run 稳定性，不作幂等性。

### I4（A）— scenario4/9 是手动 scan，不是自动 reconciliation

scenario4（407–414）pause 后写文件、resume 后立刻调用 _scan_until_terminal，而 helper 首先 POST /api/automatic-memory/scan；没有 suppressed watcher event、Cron/reconciliation reason 或对应 scan_id 证据。scenario9（452–460）mtime 跳变、重启后也立刻 POST /scan，只证明重启后手动扫描可完成，不证明 sleep/wake 等价路径自动恢复。生产 run_on_start/Cron 不能由手动 API 自证。

最小处理：scenario4 只等待生产 watcher/Cron reconciliation 并断言 reason；scenario9 只用允许的 clock-jump/restart seam 等待生产恢复，再绑定 durable identity。

### I5（A）— scenario8 不是 packaged Qdrant outage，lexical 数据来自预置 Vault

_formal_qdrant_fallback 明确 semantic_enabled=False，再直接把进程内 Gateway 的 semantic_provider 替换为抛错测试类；PackagedSidecar.qdrant_failure 参数从未使用。查询文本命中的是 sidecar 启动前手工写入的 vault/GatewayFact.md，而不是 automatic-memory ingestion 生成的 lexical record。它是有效的 HybridRetriever focused helper，但不是 packaged Qdrant unavailable 场景，也不证明自动摄取数据可被正式 lexical read model 检索。

最小处理：先由 packaged ingestion 产生带 source/raw/structured identity 的 lexical data，再对正式 semantic client 做失败注入并调用正式 retrieval orchestration。

### I6（A）— sentinel baseline 和 final 的时间点过宽

protected_before 在 sidecar.start 完成后才采集，隐藏了 VaultLayout.ensure/runtime bootstrap 的变更；protected_after 又在 _formal_qdrant_fallback 前采集，helper 的变更不会进入 diff。注释只说 bootstrap 是预期，没有精确 allowlist，因此任意启动/helper mutation 都可能被遮蔽。

最小处理：启动前记录主人 fixture baseline，显式列出允许的 bootstrap paths；所有 helper 完成后再做 final sentinel，第三方树不得有 bootstrap 排除。

### I7（C + A）— snapshot/extraction lease 分离且未设已有 stale 配置

代码事实：SnapshotJobRunner lease TTL 30s，scheduler scan lease 30s；extraction heartbeat 默认 30s，ExtractionPipeline stale_after 默认 1800s（pipeline 最低 clamp 30s），process_pending 每轮执行 release_stale。PackagedSidecar 未设置 LINGJI_EXTRACTION_STALE_AFTER_SECONDS，所以 worker 正在 claim job 时 crash，生产上可合法等待约 30 分钟才被 stale 回收；这属于 C 的保守但慢的生产租约，不应自动判为产品 bug。测试只等 30 秒 snapshot lease、再等 20/30 秒 queue，不能证明这种 recovery。

最小处理：Acceptance 环境可设置已有 stale-after（不低于 clamp），报告记录两类 lease/heartbeat/expiry；若要改默认 30 分钟另开生产时钟 brief。禁止直接 DB 改 lease。

### I8（A / deferred contract）— heartbeat <=10s 根本没有测量

计划要求 Work Fact heartbeat age <=10s，但 integration 没读取 Work Fact heartbeat，也没有断言。runtime.status 按 Task2 明确契约返回 scheduler_heartbeat_age=null，因现有 scheduler 没有可信 idle heartbeat；Task2 允许 Task6 在新 brief 下添加 measured source。该 null 是诚实的 deferred 状态，不能当 0 或 PASS；当前 Task6 不能宣称满足该门禁。

最小处理：本轮将其记为 NOT_MEASURED/BLOCKED；不以 scan/update timestamp 冒充。若必须满足门禁，另开只增加现有 Work Fact/scheduler measured source 的有界产品 brief。

### I9（A）— subprocess 输出被吞掉，子进程/端口收口不充分

sidecar 和 crash dummy 使用 stdout/stderr=DEVNULL，_output 无法恢复启动错误，故无法区分 bootstrap 早死、端口未监听或内部异常。stop 只等待 sidecar PID，没有保存脱敏 stderr 尾部、process-group/child inventory、端口重新绑定或非本轮 PID 不受影响的断言。本次复现未观察残留进程，但该证据缺口在 crash/restart 场景尤为严重。

最小处理：每个 root 保存日志并失败时只报告尾部，记录 PID/instance/port，验证 PID、端口和子进程库存收口；仍按 PID/实例清理，不能杀全量 Python。

### I10（A）— scenario3/crash terminal selector 可能采旧 scan

scenario3 选任意 completed 且不等于初始 scan；crash terminal 选所有 scans 第一条 completed；_scan_until_terminal 无 scan_id 时也按 source 第一条。授权时 Cron run_on_start、manual、watcher 存在竞态，旧 completed row 能满足等待。这与 I1 共同构成自证风险。

最小处理：所有等待器绑定本次 durable scan_id，并检查 source、trigger/time；没有 identity 应失败并披露 gap，不能 fallback 第一条。

## 5. Minor

M1（A）：scenario1 的实现静态看只做 resolve/is_dir/exists，没有打开 candidate file，但测试没有 body-read guard/hash/mtime sentinel，不能独立证明未读正文。

M2（contract ambiguity）：过期 source 的 registry 状态是 expired，reconcile report 是 complete=false 且带 errors，body 诚实；但 scheduler 捕获 PermissionError 后 route 仍 HTTP 200。若合同是操作报告可接受，若是授权动作拒绝则应 4xx。当前测试没有固定合同，不应无 brief 改状态码。

M3（A）：scenario7 检查 bad job failed、good job completed、两条 scan completed，符合“scan completed 但 extraction failed”的可能语义；但没有检查对应 Work Fact outcome、next actor 和 scan identity。

M4（A）：本机复现后的 pytest tmp_path 仍在 pytest retention 目录（不是 owner 数据），测试没记录显式删除 receipt；qdrant_failure 参数未使用。均非产品故障，但与清理/Qdrant 表述不完全一致。

## 6. 最小 bounded repair brief

可以做一次 bounded repair，但必须先重新记录 RED，且分层如下：

仅测试/文档：修 C1；精确 progress barrier、run_root、完整 terminal identity parity；same-root idempotency delta；scenario4/9 等待自动路径；scenario8 绑定 packaged ingestion lexical data；启动前/所有 helper 后 sentinel；保存 stderr/PID/port/cleanup；披露两类 lease 和 heartbeat NOT_MEASURED。不得删断言、skip、硬编码结果或改 DB lease。

经 root 批准的最小产品修复：只为 I1 传递本次 reconcile 实际 scan_id/work_id，限 scheduler/runtime/现有 route DTO 三文件；直接 race 测试。不要改 StateDB schema、queue、retrieval、promotion、UI、discovery、adapter 或架构。

不要并入本次 repair：Task2 deferred heartbeat、默认 1800s extraction stale policy、promotion/retrieval design、Artifact/release/owner acceptance。若要改变默认租约或增加 heartbeat，另开独立 brief。

## 7. 最终诊断

当前 failure 的直接 root cause 是 A 类 harness KeyError。即使修正一行，现有十场景仍不能证明自动 reconciliation、精确 crash recovery、same-root idempotency、packaged Qdrant fallback、完整 sentinel、heartbeat <=10s 或 identity parity。I1 是唯一从正式 composition 追出的真实 B 类 scan identity wiring defect。30s snapshot lease 与默认 1800s extraction stale 是 C 类可接受但慢的生产行为，不能用 DB 篡改释放。

保持 docs/TEST_REPORTS/PHASE1_AUTOMATION_UI_GATE.md 为 IN_PROGRESS / NOT_ACCEPTED。上述 bounded repair 可行，但必须先修 A 类证据污染，再由 root 决定是否批准 I1 产品接线；完成后重跑 packaged integration、rendered E2E、Task2–5 回归、compileall、diff-check、acceptance sync 和 local handoff。本报告不构成最终验收。
