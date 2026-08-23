# SB-0 Work Fact Contract Repair Progress — 2026-08-24

## Scope

按照 `docs/PROJECT_STATUS.md` 当前 Phase 1 目标，执行 SB-0 Work Fact Contract Repair：修复 Capture → Work Fact 基础合同缺口。

## Completed

### Code changes

- 修复 `src/work/capture_bridge.py`
  - `CaptureWorkBridge.create_from_capture()` 使用正式 `WorkStore.create_work()` 写入 WorkItem。
  - 消除 Capture 成功但无法进入 Work Fact 持久化链的问题。

- 修复 `src/work/store.py`
  - 增加 WorkProjector 所需读取能力：
    - `list_work()`
    - `list_events()`
    - `list_pending()`
  - 保持 WorkStore 作为 Work Fact 唯一持久化入口。

## Current status

```text
SB-0: IN PROGRESS
Code changes: DONE
Focused validation: PENDING
Full acceptance: NOT RUN
Owner acceptance: NOT RUN
```

## Required next validation

- [ ] `tests/test_work_store.py`
- [ ] `tests/test_work_projector.py`
- [ ] `tests/test_work_control_api.py`
- [ ] `tests/test_capture_work_bridge.py`
- [ ] `python -m pytest -q --tb=short -k "work or capture_work"`
- [ ] control focused validation
- [ ] capture focused validation

## Not completed

本次未声明：

- Work API 已正式完成
- Desktop 已完成闭环
- Capture → Memory 已完成
- Phase 1 PASS

以上需要后续验收确认。
