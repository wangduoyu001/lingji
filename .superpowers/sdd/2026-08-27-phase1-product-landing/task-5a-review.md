# Task 5A 独立审查

日期：2026-08-28
审查基线：`522d41ba42534ea9c00992acf20e6980ad28b454`
被审产品提交：`f799b8aed526b52b259a360b7162ceef9b86b0a3`
范围：既有 WorkStore、WorkProjector、WorkControlService、认证 8766 Work Fact 路由及 Task 5A 测试。未启动服务，未访问 Artifact、Production/Vault 或主人数据。

## 结论

- Spec Compliance：**FAIL**
- Task Quality：**NEEDS_FIXES**
- 处置：**REPAIR_REQUIRED**
- Critical：0
- Important：2

分页边界、稳定排序、总数/`has_more`、重启后的事件身份与升序时间线、认证、未知 action 404、重复 resolve 幂等和 SQLite 持久化均有实现并通过当前 focused matrix。但以下两个 Important 问题阻止 Task 5A 被接受为 Task 5B 的可靠后端基础。

## Findings

### I1 — 已解决待办仍把主人显示为下一执行者

严重级别：Important
位置：`src/work/store.py:resolve_pending_action`、`src/work/projector.py:_friendly_summary`

`resolve_pending_action()` 只把 `pending_actions.resolved` 更新为 1，不清除或替换关联的 `work_next_actions`。因此一个由主人确认的 action 在 resolve 成功后，事实中 `pending_actions` 已为空，但 `next_action` 仍然是原来的 `actor=owner` 和“等待主人确认”。`_friendly_summary()` 优先读取 `next_action`，所以 resolve 前后摘要仍返回 `next_actor=主人`。

独立临时探针复现：

```text
resolve -> {action_id: a, work_id: w, resolved: True}
pending_actions -> []
next_action -> {description: 等待主人确认, actor: owner, action_id: a}
summary before/after -> next_actor: 主人
```

这违反 Task 5A 要求的 pending/current/history 一致性，也会让 Desktop 在主人刚点击完成后继续暗示“需要主人”。修复必须在同一既有 WorkStore 事实链内完成：resolve 后要么持久化真实的系统下一步，要么明确清除已解决的 owner action；重复 resolve、并发 resolve、重启读取都必须得到同一结果，并新增断言证明 current/history/pending 一致。

### I2 — friendly summary 的 source 字段是泛化文案，不是来源身份

严重级别：Important
位置：`src/work/projector.py:_friendly_summary:70`

当前实现为所有带 `source_id` 的工作返回固定字符串 `"已关联来源"`，没有返回来源显示名、来源类型、标题或至少可读的稳定来源标识。原始 `work.source_id` 虽然仍存在于技术事实中，但 Task 5A 明确要求主人可读的 phase/result/time/source/next-actor，且技术 ID 只能作为次要详情。固定文案不能回答“这次工作来自 Codex、ChatGPT 导出、Obsidian 还是哪条 Capture”。

独立临时探针：`source_id=codex-session-abc` 的摘要仍为 `source=已关联来源`；不同来源会得到完全相同的 source 字段。这不是来源事实的忠实投影，而是占位文案。

修复应复用现有 `WorkItem.title`、`source_id` 和已有来源类型/显示名（不新增数据源），对有来源和无来源分别给出明确中文结果；必须保留原始 ID 作为 secondary diagnostic，并补充不同来源名称的断言。

## 已验证通过的部分

- `GET /api/work/history` 通过认证依赖；`limit` 为 1–100、`offset` 非负，超界由 FastAPI 422 拒绝。
- history 使用 `COALESCE(updated_at, created_at), work_id` 稳定排序；`total` 和 `has_more` 来自持久化 WorkStore，分页项不重复。
- timeline 保留 `event_id`、`work_id`、`event_type` 和 detail，按 `created_at,event_id` 升序返回；重启后仍可读取。
- pending action resolve 成功返回稳定 `action_id/work_id/resolved=true`；未知 action 返回 404；重复请求不产生重复记录。
- 路由注册在正式认证 `create_control_app`，不是未装配的 `/v1/work` 草稿入口。
- `sqlite3.Error` 映射为 503，未知工作/action 映射为 404；不返回工作区路径。

## 未发现但需要保持的边界

- 本轮没有修改产品代码。
- 没有启动 live 8766、Desktop、Artifact、Qdrant、Production/Vault，也没有触碰主人数据。
- timeline 当前固定默认最多 100 条，直接 projector 调用的正数 limit 能传递到持久层；本轮没有扩大接口为新的分页 API。若后续需要暴露 timeline limit，应继续沿用现有认证路由和同一稳定排序。

## 验证证据

- focused Task 5A：`36 passed, 2 warnings`

  `./.venv/bin/python -m pytest -q tests/test_work_control_api.py tests/test_task8_work_fact.py tests/test_work_store.py tests/test_work_control_service.py tests/test_task8_extraction_work_lifecycle.py tests/test_task8_work_transition_matrix.py`

- Work/Task8/Capture/automatic-memory Work Fact 回归：`98 passed, 2 warnings`

  `./.venv/bin/python -m pytest -q tests/test_work\* tests/test_task8\* tests/test_capture\* tests/test_automatic_memory_work_fact.py`

- `compileall`：PASS
- `git diff --check 7d4e4e1bbeeaf24f5000bac2944a1e6c3502bc48..HEAD`：PASS
- `scripts/check_acceptance_sync.py`：PASS（product-impacting files 0）
- `scripts/check_local_execution_handoff.py`：PASS

上述绿灯不能覆盖 I1/I2，因为现有测试没有断言 resolve 后的下一执行者和具体来源身份。
