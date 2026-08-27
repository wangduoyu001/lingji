# Task 5A Repair Round 1 — Independent Final Review

日期：2026-08-28
审查基线：`157b0f5`（Task 5A initial independent review）
被审修复范围：`157b0f5..289d663`
产品修复提交：`5e71cda68edfb86eac99804bc66fbfb6540bcb9c`
证据/文档提交：`289d663b619e20df0b5dcd933cc97f11c92679f0`

本轮为只读独立审查。未修改产品代码或测试，未启动 UI、live 8766、Artifact、Qdrant，未访问 Production/Vault 或主人数据。

## 结论

- Spec Compliance：**PASS**
- Task Quality：**PASS**
- 处置：**ACCEPT_FOR_5B**
- Critical：0
- Important：0

## 复核结果

### I1：主人待办与下一执行者一致

`WorkStore.resolve_pending_action()` 在既有 `StateDatabase` 锁和单一事务中读取 action、标记已解决，并只删除同一 `(work_id, action_id, actor='owner')` 的 `work_next_actions`。因此：

- 已解决 owner action 不会继续显示为主人下一步；
- 同一 work 的更新 system action 不会被误删；
- replay 和并发 resolve 返回相同结果；
- 重启后 current、history、pending 与 next_action 投影收敛一致。

对应测试覆盖清除 owner next action、保留 system next action、并发 replay、重启及 history/current/pending 一致性。

### I2：来源摘要可读且身份不混淆

`WorkProjector._friendly_summary()` 使用已有 `WorkItem.title` 作为可读来源名；不同来源标题保持不同，未生成泛化的“已关联来源”假身份。精确 `source_id` 继续保留为次要诊断字段；无来源工作返回空值。没有新增路径推断、虚构来源或把内部 ID 充当主要展示文案。

### 原始 Task 5A 合约

- history 使用稳定 `work_id` 排序，`limit` 为 1–100，`offset` 非负，`total/has_more` 来自持久化 WorkStore；分页不重叠。
- timeline 保留 `event_id/work_id/event_type/detail`，按 `created_at,event_id` 升序读取，重启后仍可读。
- current/history/timeline/pending 均来自同一 WorkStore/read projection。
- resolve 路由受认证保护；缺少 token 返回 401，未知 action 返回 404，重复请求保持幂等成功。
- SQLite 异常继续由正式 Work 路由转换为 503，不泄露工作区路径。
- 既有 phase/result 映射覆盖 pending、accepted、running、retrying、completed/success、failed；未知值不被伪装成成功。

## 自动验证

- Task 5A focused：`40 passed, 2 warnings`
- Work/Task8/Capture/automatic-memory Work Fact matrix：`102 passed, 2 warnings`
- `./.venv/bin/python -m compileall -q src/work src/control tests/test_work_control_api.py tests/test_task8_work_fact.py`：PASS
- `git diff --check 157b0f5..289d663`：PASS
- `./.venv/bin/python scripts/check_acceptance_sync.py`：PASS（product-impacting files 0）
- `./.venv/bin/python scripts/check_local_execution_handoff.py`：PASS
- final worktree：clean

Warnings are existing Pydantic/Starlette deprecation warnings and are not Task 5A failures.

## 边界

本结论仅接受 Task 5A Owner Work API 作为 Task 5B UI 的后端基础。它不表示 Desktop UI、真实 8766、Artifact、Production/Vault、发布链或主人验收已完成；`LOCAL_EXECUTION_TASK.md` 仍为 `IDLE`。
