# SB-0 Work Fact Contract Repair Step 2 — 2026-08-24

## Completed

继续执行 SB-0。

新增测试覆盖：

- `tests/test_work_store.py`
  - 验证 WorkStore 持久化 WorkItem。
  - 验证 ExecutionEvent 写入和读取。

- `tests/test_capture_work_bridge.py`
  - 验证 CaptureWorkBridge 创建真实 WorkItem。
  - 验证 Capture accepted event 进入事实链。

## Status

```text
SB-0: IN PROGRESS

Implementation: DONE
Contract tests added: DONE
Local test execution: PENDING
Control API integration: PENDING
Desktop contract validation: PENDING
```

## Remaining blockers

1. LocalControlService 尚需确认 WorkProjector 正式注入。
2. `create_control_app()` 尚需确认 work routes 注册。
3. Desktop Work Fact contract 尚需校验字段一致性。
4. focused validation 尚未执行。

## Not declared complete

- SB-0 未 PASS。
- Phase 1 未 PASS。
- Desktop 闭环未完成。
