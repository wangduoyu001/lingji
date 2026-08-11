# Autopilot Engine 代码地图

> Updated: 2026-08-11
> Ownership: `src/` 正式产品主线
> Acceptance: `docs/ACCEPTANCE/AUTOPILOT_PHASE4_ACCEPTANCE.md`
> Test report: `docs/TEST_REPORTS/AUTOPILOT_ENGINE_PHASE4_IMPLEMENTATION.md`

## 1. 入口

```text
run_control_api.py
→ 创建 GovernedLocalControlService
→ 创建 AutopilotEngine
→ 注册 /api/autopilot/status
→ start
→ uvicorn 8766
→ finally stop + service.close
```

## 2. 核心

```text
src/autopilot/engine.py
```

职责仅包含：

```text
Health 诊断
→ 安全动作白名单
→ 重新 Health 验证
→ 风险分级
→ StateDatabase events 审计
```

不得承载：永久记忆审批、Qdrant 破坏性重建、第三方配置修改、任意 shell 执行、第二套任务队列。

## 3. API

```text
src/control/autopilot_api.py
GET /api/autopilot/status
```

只读、本机 token 鉴权。Phase 4 不提供 POST repair/execute API。

## 4. UI

```text
desktop/lingji-control/src/pages/OverviewPage.tsx
```

只消费 `summary / owner_action_count / background_issue_count / recent_actions`，不增加技术监控大面板。

## 5. 复用模块

```text
src/health.py                         StartupHealthChecker
src/extraction/queue.py              release_stale / retry contract
src/storage/state_db.py              events
src/gateway/memory_statistics.py     memory/vector/embedding status
```

## 6. 定向测试

```text
python -m pytest -q tests/test_autopilot_engine.py tests/test_autopilot_api.py
node desktop/lingji-control/scripts/assistant-autopilot-smoke.mjs
```

修改 Autopilot 行为时必须同时运行 Desktop full smoke、P0 Windows Gate、Windows Release 和 macOS Desktop Gate。
