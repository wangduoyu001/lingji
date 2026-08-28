# Task 6M 独立产品 / 安全审查

日期：2026-08-28（Asia/Shanghai）
审查范围：只读审查 Task6M 产品/测试提交 `1901628eee197e3d71d7e070c41c9e586d5468de`，基线 `8cc4d4aabce5a09e7db3754ed9197e33e0b5bf2a`。
审查 HEAD：`b65f81d659f787e349d545f51c4ddb94af770d4b`。
工作树：`/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`。

本轮没有修改产品或测试实现；仅写入本审查报告和既有计划/状态/验收变更记录中的 review disposition。Production、Vault、Artifact、live 8766/8767 和主人数据未触碰。

## 1. 结论

```text
Spec Compliance: FAIL
Task Quality: NEEDS_FIXES
Critical: 0
Important: 5
Minor: 2
Disposition: REPAIR_ROUND_1 authorized
Task 6M: NOT_ACCEPTED
Merge recommendation: DO NOT MERGE
```

Task6M 的新 v1 marker 在新鲜 focused 测试中能被正式 `ExtractionPipeline` 创建，并在真实子进程 SIGKILL 后由新的 pipeline 初始化回收；正常成功路径、active/expired lease、regular/symlink/directory 保护和 durable raw hash 保持均有证据。但它没有关闭已知旧 marker 的真实残留，也有 lease/DB-error fail-closed 边界、正式 UI 可见性和竞态安全缺口。因此不能把 Task6C blocker 宣称为已关闭，不能标记 `ACCEPTED_FOR_FINAL_VALIDATION`。

## 2. 新鲜验证

执行环境：Python 3.12，当前精确 HEAD；测试仅使用 pytest `tmp_path` / inline 临时目录。

| 检查 | 结果 |
|---|---|
| `./.venv/bin/python -m pytest -q tests/test_task6m_transient_lifecycle.py --tb=short` | **8 passed**, 0 failed，0.99s |
| Task6M + snapshot/resume/adapter/worker/runtime/scheduler matrix | **150 passed**, 3 warnings，10.27s |
| `./.venv/bin/python -m compileall -q src tests/test_task6m_transient_lifecycle.py` | **PASS**, exit 0 |
| `git diff --check 1901628^..1901628 -- src tests` | **PASS**, exit 0（产品/测试差异） |

另外运行了三个只读 inline probe：

1. 已知旧名 `.automatic-memory-1234567890abcdef.json` 返回 `unknown_marker`、`removed_count=0`，文件仍存在。
2. 已知 job 被置为 `queued` 后，名称带同一 job 但 `WRONG` lease 的 v1 marker 被返回 `lease_released` 并删除。
3. queue `get()` 抛出 `RuntimeError("db locked")` 时，reconcile 直接抛出异常，而不是返回带 `errors` 的 machine-readable receipt。

## 3. Important findings

### I1 — 旧版 marker 永久保留，已知 Task6C 残留无法回收

位置：`src/extraction/transient.py:22, 125-142`。

新的正则只接受 `.automatic-memory-v1-{job_id}.{lease_token}{suffix}`；历史产品在
`src/extraction/pipeline.py` 使用 `.automatic-memory-{uuid}{suffix}`。Task6C 的真实 blocker
正是这种旧 `.automatic-memory-{uuid}.json`（报告记录约 2,640,287 bytes）。当前 reconciliation
会把它分类为 `unknown_marker` 并永久保留；没有迁移、可证明归属的兼容回收或一次性 tombstone
策略。新 packaged runtime 启动时仍会看到该残留，terminal/stop inventory 因此不能清零。

**影响：** 已部署/已运行版本升级到 Task6M 后，已知 crash 残留污染不会自动收敛，直接违背
Task6C 的 terminal/stop cleanup receipt。保留而非误删是安全的，但目标生命周期未关闭。

**最小修复边界：** 在同一 transient 模块定义受限 legacy migration；只有能从既有 durable
raw/queue 关系证明归属时才迁移/回收，否则保持并把不可回收原因显式列入 receipt，且必须在
fresh packaged crash/restart/stop gate 中证明既有旧残留策略不会永远污染结果。不得用测试 harness
直接 unlink 掩盖问题。

### I2 — queued/retrying/terminal 分支未验证 marker lease，lease mismatch 可被删除

位置：`src/extraction/transient.py:148-160`。

对于 `completed/failed/cancelled`，代码无论 marker 中 lease 是否匹配都会删除；对于
`queued/retrying`，也完全不比较 marker lease 与队列记录（该状态通常 lease 为空），直接按
`lease_released` 删除。inline probe 已复现：同一已知 job、伪造 `WRONG` lease 的 marker 在
queued 状态被删除。用户锁定的“lease mismatch 必须 fail closed”未满足。

**影响：** stale/foreign dispatch marker 可能被错误归入可回收对象；虽然正常 hard-link marker
只减少临时链接、不删除其 content-addressed raw authority，但 ownership 证明不成立，且不能
作为并发 worker/重启安全证据。

**最小修复边界：** 对所有可删除状态统一要求 lease 归属证明；释放后若现有队列无历史 lease
可核对，应保留并报告 `lease_unverifiable`，或在既有 queue 状态中增加不改变事实源的受限
释放凭据读取，不新增第二队列/数据库。

### I3 — queue/StateDB error 直接逃逸，未形成现有 runtime 可见的 fail-closed receipt

位置：`src/extraction/transient.py:62-67, 143-147`；`src/extraction/pipeline.py:58-84`。

`_queue_job()` 仅捕获 `LookupError/KeyError`。SQLite lock/corruption 或 queue wrapper 的其他
读取异常会从 reconciliation 直接抛出；inline probe 得到 `RuntimeError: db locked`。这不会
删除 marker，动作层面是保守的，但 pipeline 构造函数在正式 runtime 组合前就失败，无法返回
`errors`、设置 `cleanup_pending`/`cleanup_error`，也无法通过既有 worker status、runtime status
或 authenticated API 告知“清理未验证”。

**影响：** “DB error fail closed”只完成了不删除，未完成现有 runtime/Worker 可观察的真实失败
语义；启动异常可能表现为无 runtime 而不是 degraded/cleanup_pending。

**最小修复边界：** 将可预期 queue/SQLite 读取异常收敛到 reconciliation receipt 的 `errors`
并保持所有 marker；由正式 pipeline/worker/runtime startup 传播该 receipt，且不得把未知 DB
状态当成 empty/clean。

### I4 — 产品接入虽存在，但没有 fresh packaged 30/70 crash gate 证明修复已覆盖正式 runtime

静态链路确认：`src/extraction/bootstrap.py:23-63` 构造正式 pipeline；`run_packaged_control_api.py`
转入 `run_control_api.main()`；`run_control_api.py:44-58, 66-91` 构造并启动
`AutomaticMemoryRuntime`；`ExtractionPipeline.__init__` 在该正式构造路径启动 reconciliation，
`ExtractionWorker.stop()` 也调用 reconciliation，`AutomaticMemoryRuntime.status()` 读取
worker 的 transient inventory。因此接入点不是测试专用 seam。

但本提交后未 fresh 重跑 Task6C 所要求的真实 packaged 30%/70% sidecar SIGKILL → startup
reconcile → pause/stop receipt。Task6M 的 real-crash 测试只启动 inline 子进程并重建
`ExtractionPipeline`，没有 30/70 scan、sidecar PID、runtime stop、两来源 sentinel 或同一
packaged report 的证据。Task6C 旧的两次 PASS 已被 `3fd8059` blocker supersede，不能自动继承。

**影响：** 代码接入可静态确认，但 Task6M 的用户锁定验收尚未被真实正式 packaged runtime
复读；Task6 仍必须保持 `IN_PROGRESS / NOT_ACCEPTED`。

**最小修复边界：** 不改产品范围；完成一次 fresh clean Acceptance roots 的 packaged 30/70
crash/restart/stop gate，分别记录 marker inventory、terminal/queued 状态、sidecar PID/port
清理和 source/Vault/raw sentinel。

### I5 — cleanup inventory 虽到达 API，Desktop 未消费具体错误/残留

位置：`src/control/automatic_memory_api.py:143-164`；
`desktop/lingji-control/src/pages/memorySourcesTypes.ts:60-74`、
`desktop/lingji-control/src/pages/MemorySourcesPage.tsx:125-149`。

正式 `/api/automatic-memory/runtime` 原样返回 `runtime.status()`，其中包含
`cleanup_pending`、`cleanup_error` 和嵌套 worker `transient_cleanup`；因此 API 层有字段。
但 Desktop `RuntimeSummary` 类型没有这些字段，来源页只根据 `state` 和 heartbeat reason
渲染“最近活动”，即使存在 transient `unlink_failed`，也不会显示具体 cleanup 错误、保留的
legacy/unknown marker 或下一步。`runtimeHeartbeatLabel()` 在 degraded 时优先返回 heartbeat
reason，可能只显示通用“后台状态不可用”。这满足不了“清理失败通过现有 runtime/WorkFact/API/
Desktop 真实可见”的锁定验收，当前字段对主人实质上是无人消费的内部投影。

**最小修复边界：** 复用现有 runtime API 和 Desktop 来源状态模型，增加有界错误/待清理
摘要（不展示原始路径或 token），并由 rendered smoke 覆盖 degraded/cleanup_pending 与恢复；
不得新增事实源。

## 4. Minor findings

### M1 — lstat 后 pathname unlink 没有抗 path-swap 的身份绑定

位置：`src/extraction/transient.py:128-137, 174-180`。

代码先 `entry.lstat()` 再对同一路径 `entry.unlink()`，没有目录 FD/openat 或再次身份校验。
路径在两步之间被替换时可删除替换后的 regular file；root 的 `exists/is_symlink/is_dir` 检查也
不是原子锚定。当前只处理 raw-root direct child 且不跟随 symlink，hard-link 正常 unlink 不
影响 durable raw；但没有 race 测试或更强的 pathname identity contract，故只能给 Minor，不能
宣称已覆盖用户要求的 TOCTOU 边界。

### M2 — failure cleanup 和 API/UI 可见性测试不完整

已有测试覆盖正式 success dispatch 和 SIGKILL/restart，但没有让 adapter 在 marker 创建后
抛异常并断言 `_execute_internal_snapshot` 的 `finally` 删除 marker；也没有真实 authenticated
8766/worker status 响应复读 `preserved/unknown/legacy` inventory。runtime 的字段投影代码存在，
但本轮 focused 证据仍停在 unit/in-process receipt。

## 5. 已验证的正向边界

- marker 版本显式为 `v1`；job/lease 每段最多 64 个安全字符，suffix 有界，文件名不含路径
  分隔符，适合 Windows 基本命名约束。
- 只扫描 raw root 直接子项；`lstat` 拒绝 symlink、目录和非 regular file；future/unknown/
  malformed marker 保留；不递归到 Vault 或 content-addressed raw 子树。
- running 且同 lease 的 active marker 保留；过期 heartbeat/locked 时间或可证明死亡的本机
  `hostname:pid` marker 可回收；当前进程、foreign host、非法 pid 不能被证明死亡时保留。
- `_execute_internal_snapshot` 的 temporary marker 在正常 success/failure 的 `finally` 语义
  上是正确方向；pipeline startup、`process_pending` 前后、worker stop 都调用现有 reconcile。
- marker 是 raw hard-link 的临时路径；测试验证回收后 durable raw 文件及 SHA-256 不变。产品提交
  仅修改现有 pipeline/worker/runtime 及一个 transient helper，没有新增 DB、队列、API、UI 或
  第二事实源。

## 6. 测试覆盖与用户锁定验收对照

| 要求 | 本轮结论 |
|---|---|
| bounded job/lease naming、Windows-safe segment | focused PASS |
| terminal/success、active/expired、重复 reconcile | focused PASS |
| released、lease mismatch、DB error | released/mismatch **FAIL**；DB error **FAIL（receipt）** |
| worker restart / real crash | inline pipeline SIGKILL PASS；packaged 30/70 **NOT_TESTED** |
| root direct-child、symlink/目录/foreign/future | focused PASS；path-swap 仅静态缺口 |
| hardlink durable raw count/hash | focused PASS |
| normal failure cleanup | code finally；专门回归 **NOT_TESTED** |
| two-worker isolation | focused PASS（仅 active markers） |
| 30/70 resume、stop/terminal、two sources/sentinel | 既有 Task6C 旧证据被 supersede；本提交后 **NOT_TESTED** |
| real runtime/API/Desktop visibility | composition static PASS；fresh live/API **NOT_TESTED** |

## 7. 最小修复及复验要求

本轮授权且最多一轮 `REPAIR_ROUND_1`，只允许：

1. 在现有 transient helper 内增加兼容旧 marker 的受限迁移/不可回收 receipt 语义；不得宽泛
   删除无法证明归属的旧文件。
2. 统一所有 status 分支的 job/lease ownership proof，mismatch/unverifiable 一律保留。
3. 捕获 queue/SQLite 读取错误，保留 marker 并通过现有 pipeline → worker → runtime/API
   status 暴露 `errors/cleanup_pending`；不新增状态存储。
4. 若采用目录 FD/身份复核，仍限定 raw root direct-child，且不改变 durable raw/Vault 边界。
5. 从 clean Acceptance roots fresh 跑 packaged 30/70 crash/restart/stop 至少一次，并复跑
   Task6M focused、直接回归、compileall、diff-check、acceptance sync、local handoff。

修复后仍有任何 Critical/Important，按用户规则标记 `BLOCKED_AT_REPAIR_CAP`；不得降低断言、
删除旧报告数字或由 harness 直接 unlink marker。

## 8. Final disposition

```text
Reviewed product/test commit: 1901628eee197e3d71d7e070c41c9e586d5468de
Reviewed HEAD: b65f81d659f787e349d545f51c4ddb94af770d4b
Spec Compliance: FAIL
Task Quality: NEEDS_FIXES
Critical: 0
Important: 5
Minor: 2
Disposition: REPAIR_ROUND_1 authorized
Task 6: IN_PROGRESS / NOT_ACCEPTED
Owner observation: NO
Artifact/release/live 8766/8767: NOT_TESTED
Acceptance docs: synchronized by docs-only follow-up
Temporary evidence: inline temp dirs cleaned
Product/test files modified by review: none
```
