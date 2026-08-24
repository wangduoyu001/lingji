# SB-0 Work Fact Contract Repair Step 3 — 2026-08-24

## Completed

继续修复 Work Fact Control boundary。

### Fixed

`src/control/work_service.py`

问题：

```text
WorkControlService
 -> WorkProjector
 -> state_db
```

但 `WorkProjector` 要求接收 `WorkStore`，不是裸 StateDatabase。

修复：

```text
StateDatabase
 -> WorkStore
 -> WorkProjector
 -> WorkControlService
 -> API/Desktop
```

同时统一返回结构：

- current_work -> items
- pending_actions -> items
- work_timeline -> events

## Added test

- `tests/test_work_control_service.py`

验证 Control 层能够读取真实 Work Fact 投影。

## Status

```text
SB-0: IN PROGRESS

Work persistence: DONE
Projection layer: DONE
Control adapter: DONE
API registration: PENDING
Desktop contract: PENDING
Focused validation: PENDING
```

## Next

- 注册 `/api/work/*` 到 create_control_app。
- 增加 API smoke test。
- 完成 SB-0 acceptance checklist。
