# SB-0 Work Fact Contract Repair Step 4 — 2026-08-24

## Document alignment

依据：

- docs/PROJECT_STATUS.md
- docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md
- SB0 Step3 report

当前目标仍为 Work Fact Contract Repair。

## Completed

新增：

- `tests/test_work_control_api.py`

覆盖 Control boundary：

```text
WorkStore
 -> WorkControlService
 -> Work Fact response contract
```

## Current finding

`src/control/work_routes.py` 已存在正式路由定义：

- `/api/work/current`
- `/api/work/pending-actions`
- `/api/work/timeline/{work_id}`

下一阻塞点：

- 需要确认并接入 `create_control_app()` 的正式注册路径。

## Status

```text
SB-0: IN PROGRESS

Work persistence: DONE
Projection layer: DONE
Control adapter: DONE
API contract test: ADDED
API route registration: PENDING
Desktop contract: PENDING
Focused validation: PENDING
```

## Next

1. 将 work_routes 注册到 Local Control API。
2. 执行 work API focused validation。
3. 检查 TypeScript Work Fact contract。
4. 更新 acceptance log。
