# Task 6 Final Independent Security / Quality Review

日期：2026-08-28（Asia/Shanghai）
审查代理：Luna（独立只读审查）
工作树：`/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`
Reviewed HEAD：`7588a4fb8176f1e22e12b400518e2d6faff50ccc`
Task6C test commit：`6eb469fefafe0a33e6ac65f765c7663741883811`
权威报告：`docs/TEST_REPORTS/PHASE1_AUTOMATION_UI_GATE.md`

本轮没有修改产品代码、测试代码、任务单、既有报告、Production/Vault 或主人数据；只新增本报告。
未运行 Artifact、release、live 8766/8767 或 owner acceptance。

## 1. 结论

```text
Spec: FAIL
Quality: NEEDS_FIXES
Critical: 0
Important: 6
Minor: 2
Disposition: REPAIR_ROUND_1
Task 6: NOT_ACCEPTED
```

不能接受权威报告当前的 `PASS_AUTOMATED / READY_FOR_TASK7`。本次 fresh packaged gate
真实失败，且检查发现 receipt/parity、清理 fail-open、Task6S/Task6H packaged 集成仍有证据缺口。
因此不满足“零 Critical/Important 才 ACCEPT_TASK6_AUTOMATED / READY_FOR_TASK7”。

## 2. Fresh verification

### 2.1 Packaged ten-scenario gate

命令：

```text
./.venv/bin/python -m pytest -q tests/integration/test_automatic_memory_packaged_flow.py --tb=short
```

结果：

```text
1 failed, 1 passed, 1 warning in 267.42s
```

失败位置：`tests/integration/test_automatic_memory_packaged_flow.py:884`，30%/70% crash
terminal raw identity parity 为 `21 != 20`。失败前确实启动并重启了真实 packaged sidecar，
持久 scan 均到 `completed 20/20`，每个数据库均有 20 个 extraction jobs；但一侧的
`storage/raw` 在断言时仍含 `.snapshot-owned-...tmp`/`.automatic-memory-...json` 临时 marker，
另一侧 marker 已被清理。`_identity_sets()` 在第 244 行把 raw 目录所有文件都当作 domain raw hash，
所以该测试不是稳定 receipt，也没有完成第二轮 clean-root gate。

保留的失败 root 在证据提取后已删除；没有上传私有日志、数据库或原始 fixture。

### 2.2 Regression and UI checks

| 检查 | 结果 |
|---|---|
| Task6H/S/A、scheduler/snapshot/resume/source/watcher/runtime/Work Fact/context/MCP/structured/queue/worker/control/packaged 关键矩阵 | `208 passed, 6 warnings`，16.89s |
| Desktop `npm run build` | PASS |
| Desktop `npm run test:runtime` | PASS |
| Desktop `npm run test:memory-sources` | PASS |
| Desktop `npm run test:work-fact` | PASS |
| Desktop `npm run test:memory-review` | PASS |
| Desktop `npm run test:e2e:memory` | PASS (`e2e_owner_memory_flow`) |
| `python -m compileall -q src tests` | PASS |
| `git diff --check c1cd4453..HEAD` | PASS |
| `scripts/check_acceptance_sync.py` | PASS，changed files 6，product-impacting 0 |
| `scripts/check_local_execution_handoff.py` | PASS |

以上通过项不能覆盖 packaged gate 失败，也不能替代 packaged Task6S/Task6H 场景证据。

## 3. Important findings

### I1 — raw identity 集合包含 transient marker，fresh crash gate 不可重复

位置：`tests/integration/test_automatic_memory_packaged_flow.py:244`。

`_identity_sets()` 对 `storage/raw` 递归读取所有文件并计算 hash，没有排除/分类
`.snapshot-owned-*.tmp`、`.automatic-memory-*.json` 等运行时临时文件，也没有把 marker
生命周期作为独立 cleanup assertion。fresh run 中 30%/70% 均完成 20/20 和 20 jobs，但
raw 集合在断言时出现 21/20，直接重现了 gate failure。

**影响：** 30%/70% crash/restart terminal receipt 未通过，现有两次历史 `2 passed` 数字不能
在本轮复读；Task 6 不能 ACCEPT。

### I2 — cross-root parity 仍用长度而非身份/状态比较

位置：`tests/integration/test_automatic_memory_packaged_flow.py:883-886`。

30% 与 70% 的 `source/scan/job/raw/structured` 仅比较 `len(set)`，没有比较归一化后的
content-addressed raw、source/conversation/message/version/memory identity、job natural
identity/status、terminal scan/work identity、leases/owner/expiry 或 Work Fact outcome。
不同错误集合只要长度相同即可通过，与计划要求的 identity parity、版本和 receipt 复核不符。
同 root idempotency 也只断言 structured set 相等（第 589 行），没有断言 raw set 与版本元数据
相等；报告的“raw SHA set unchanged”因此不是由断言证明的。

### I3 — cleanup/process 证据 fail-open，且存在启动异常泄漏路径

位置：`tests/integration/test_automatic_memory_packaged_flow.py:42-53, 346-351, 379-383,
876-877`。

`_process_inventory()` 在 `ps` 不可用或失败时返回空列表；Windows/PowerShell 5.1 上这会把
“无法检查”当成“没有 child”。crash receipt 又无条件写入 `crashed_child_inventory: []`
和 `port_rebind_verified: True`，clean receipt 写入 `rebind_verified: True`，不是从 receipt
字段复读的测量结果。`PackagedSidecar.start()` 在 token 缺失/为空或 ping 失败时直接 assert，
由于 context manager 尚未 yield，已启动 process 不会进入 `finally: stop()`，可能遗留 sidecar。

**影响：** PID/child/port/log cleanup 与启动失败安全边界不能作为跨平台发布证据；违反不得吞异常、
不得硬编码布尔值、按 PID/实例清理的要求。

### I4 — packaged retrieval 只调用 Gateway/Hybrid，未覆盖 MCP/ContextPack 和真实 Qdrant client

位置：`tests/integration/test_automatic_memory_packaged_flow.py:478-518`。

`_formal_qdrant_fallback()` 构造 Gateway 后直接替换 `gateway.retriever.semantic_provider` 为
测试 `FailingVectorClient`，并只调用一次 `search_with_diagnostics()`。它没有调用正式 MCP
`search_memory` 或 `ContextPackBuilder`，也没有通过 Qdrant provider/client 的正式失败 seam；
`semantic_enabled=False` 后再替换 in-process provider 不能证明实际 Qdrant client outage。
虽然当前 packaged ingestion 已产生 `memory_documents` lexical records，但“Gateway/Hybrid/MCP/
ContextPack 全路径”的要求没有在 packaged gate 执行。

### I5 — Task6S authority/versioning 未在 packaged gate 实际覆盖

当前 packaged helper 只在 revoke 前查询一条 authorized/current lexical hit；没有在 packaged
composition 中复核 revoke/expiry 后 Gateway、Hybrid、MCP、ContextPack 的 current fail-closed，
也没有复读 v1/v2 `content_hash`、`valid_from/valid_to`、`superseded_by/supersedes` 和 history/
as_of 保留。Task6S focused report 的通过不能替代用户明确要求的 packaged 集成证据。

### I6 — Task6H packaged 只测一次 age，不测 failure/degraded 和 instance/restart 隔离

位置：`tests/integration/test_automatic_memory_packaged_flow.py:653-671, 663-665`。

packaged flow 只在 sleep/wake restart 后读取一次 heartbeat，并断言 age `<=10s`。它没有比较
重启前后的 `instance`/`generation`，没有注入 active Work Fact touch/write failure 并证明持久
`degraded`、`reason`、`last_error`、源隔离和后续恢复，也没有证明 heartbeat 失败不会被报告为
healthy running。Task6H focused 8-case 不能替代 packaged heartbeat integration；因此报告把
Task6H packaged 全覆盖写成 PASS 过度表述。

## 4. Minor findings

### M1 — metadata-only 没有 body-read guard

scenario 1 只检查 `/discovered` 返回、StateDB sources=0 和 raw 目录为空；没有对 candidate
文件安装 open/read guard、hash/mtime sentinel。`discover_source_metadata()` 静态实现确实只
做路径 metadata，但 packaged evidence 没有独立捕获一次正文读取。

### M2 — Work Fact failure/lifecycle 证据不完整

scenario 7 只检查 corrupt job failed、healthy job completed 和 source 隔离；没有在该 packaged
场景断言两个 scan 对应的 terminal Work Fact outcome、next actor。scenario 6 对 revoke/expiry
主要读取 source 状态和报告，不复核 queued/running job cancellation、current retrieval 隔离。

## 5. Existing reports and evidence consistency

- Task6C report/authority 声称两次 `2 passed`（265.89s、266.73s），但仓库只保留 prose/table，
  没有可复读的脱敏 receipt JSON、raw hash 清单、日志 hash 或持久 count artifact；本轮 fresh
  gate 在同一 HEAD 复现失败，故历史数字不能单独支持 READY。
- Task6S final review 和 Task6H Repair 1 review 本身可接受其 focused 边界，但两者均明确 Task6
  外部 packaged crash/live/owner gates 尚未完成；不能把 focused 旁证升级为本 gate 的 packaged
  acceptance。
- `scripts/validate.ps1` 已注册 `automatic-memory-landing`，缺少命令时 `Invoke-ValidationStep`
  以 exit code=1 失败，且 PowerShell 5.1 的原生 stderr 处理逻辑不会将 warning 当成功；此项静态
  合同 PASS。未在 macOS 强行运行 PowerShell。

## 6. Cleanup and scope

```text
LingJi packaged/core processes after test: none observed
8766 listener: none
8767 listener: none
Fresh pytest Acceptance root: removed after evidence extraction
Worktree product/test files: unchanged by this review
Production/Vault/owner data: untouched
```

本轮删除的仅是本次 fresh pytest 明确生成的失败临时 root；没有删除未知历史目录、工作区主人数据、
Production/Vault 或正式数据库。

## 7. Minimal bounded Repair Round 1

仅允许修改 packaged acceptance harness 与必要的脱敏 evidence/report 文档；不改产品 schema、
queue、scheduler/job system、promotion、ranking、embedding、API family、Vault/Core 或主人数据：

1. 将 raw domain identity 与 transient temp marker 分离；marker 必须单独记录并在 terminal/stop
   后真实断言清理。生成每轮真实 receipt（source/scan/work/job identity、raw hashes、structured
   version metadata、leases、Work Fact、queued/duplicates、process/port/child/log cleanup），
   不用默认值、长度代替身份或无条件布尔值。
2. 让 30%/70% cross-root parity 比较规范化身份集合、状态、原始 hash、版本关系、terminal
   Work Fact 和 lease 证据；same-root same-bytes 重扫显式比较 raw/structured/version 集合与
   inserted/reused/duplicate delta。所有启动/网络/进程盘点错误 fail-closed；start 失败也必须
   按 PID/实例清理。
3. 在 packaged composition 中用已摄取 lexical record 调用正式 Gateway/Hybrid、MCP search 和
   ContextPack，并通过正式 semantic/Qdrant failure seam 注入 outage；随后在同一 packaged
   StateDB 下复核 current/why revoke/expiry fail-closed、history/as_of、v1/v2 supersession。
4. 在 packaged restart 中保存并比较 heartbeat instance/generation；注入 active Work Fact
   touch/write failure，复核 degraded reason/error、source isolation、recovery、event count
   不增长；scenario 1 增加真实 body-read guard，scenario 6/7 增加 Work Fact 与 cancellation
   证据。

修复后必须从 clean Acceptance roots fresh 跑完整 packaged gate 至少一次并复核真实 receipt，
再跑关键回归、Desktop rendered/build/smokes、compile、diff、sync、handoff。Task6C 最多这一轮；
仍有 Critical/Important 时应 `BLOCKED_AT_REPAIR_CAP`，不得通过降低断言或改写权威报告放行。

## 8. Final disposition

```text
Product commit: 7588a4fb8176f1e22e12b400518e2d6faff50ccc
Task6C test commit: 6eb469fefafe0a33e6ac65f765c7663741883811
Spec: FAIL
Quality: NEEDS_FIXES
Critical: 0
Important: 6
Minor: 2
Verdict: REPAIR_ROUND_1
Merge recommendation: DO NOT MERGE
Owner observation complete: NO
Required clients covered: NOT_APPLICABLE (no Artifact/live owner run)
Skipped clients: Artifact/release/live 8766/8767/owner acceptance
Blocking defects: I1–I6
Acceptance docs synchronized: YES (checked against current HEAD)
Temporary evidence cleaned: YES
Production/Vault touched: NO
```
