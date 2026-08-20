# Local Execution IDLE Handoff Contract

## 任务目标

修复 `local-execution-handoff` 对 `IDLE` 状态的自相矛盾：验证器虽然声明 task status 支持 `ACTIVE / IDLE`，却仍无条件要求 ACTIVE Artifact、report、cleanup、product SHA 等字段，导致仓库在尚未生成新产品 Artifact 时只能保留一个过期 ACTIVE 任务才能保持 CI 绿色。

## 根因

`scripts/check_local_execution_handoff.py` 原逻辑：

1. `validate_task()` 无条件要求完整 ACTIVE 字段；
2. 随后才允许 `status in {ACTIVE, IDLE}`；
3. `validate_result()` 不支持 `IDLE / NOT_RUN`；
4. 因此“当前没有可执行真机任务”无法被机器表达。

这与项目验收边界冲突：新的 product exact SHA 与同 SHA Artifact 未锁定前，本机任务必须保持不可执行，而不是复用历史 PR60/PR88 Artifact。

## 修改文件

- `scripts/check_local_execution_handoff.py`
- `tests/test_local_execution_handoff.py`
- `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`
- `docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md`

## 新合同

### IDLE

最小 task：

```text
task_id = NONE
status = IDLE
repository
product_pr
product_branch
local_execution_allowed = false
```

最小 result：

```text
task_id = NONE
status = IDLE
verdict = NOT_RUN
repository
product_pr
```

IDLE 明确禁止：

- `local_execution_allowed=true`
- result `RUNNING`
- result `PASS`
- 在 `acceptance/*` 报告分支冒充完成验收

### ACTIVE

原有严格合同完全保留：

- 40 位 product SHA；
- Artifact identity；
- report/public evidence paths；
- cleanup before/after；
- remote verification；
- owner confirmation；
- trial 阈值与 Production pollution=0 等硬门禁。

没有删除、skip 或弱化任何 ACTIVE 验收断言。

## 测试新增

- IDLE minimal task/result 可通过；
- IDLE 不能允许本地执行；
- IDLE task_id 必须为 NONE；
- IDLE result 不能 RUNNING/PASS；
- ACTIVE 仍必须提供 Artifact/验收字段；
- 原有 trial/cleanup/remote/quality 阈值测试全部保留。

## 数据流

```text
无新 Artifact
→ LOCAL_EXECUTION_TASK = IDLE
→ handoff validator PASS
→ 不允许本机 Codex 执行

新 product exact SHA + 同 SHA Artifact 锁定
→ LOCAL_EXECUTION_TASK = ACTIVE
→ 完整 strict contract
→ 本机 M5 执行
→ COMPLETED / PASS|FAIL|BLOCKED
```

## 回滚

如果需要回滚，仅恢复本提交前的 `check_local_execution_handoff.py` 与对应测试；不会影响产品数据、数据库、Qdrant、Vault 或 Artifact。

## 已知限制

本修改只修复任务状态机合同，不生成新的产品 Artifact，也不代表 M5 已通过。

## 下一步

PR #105 全部自动门禁通过后 squash merge 到 `feature/owner-autopilot-ui-codexpp`，对新的产品 exact SHA 跑完整双平台门禁并生成同 SHA Artifact，然后把 canonical local task 从 IDLE 切换为新的 ACTIVE M5。
