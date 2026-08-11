# LingJi Phase 4 Autopilot Engine 实施与测试报告

> 日期：2026-08-11
> 分支：`feature/owner-autopilot-ui-codexpp`
> 产品 Commit：pending
> 范围：Autopilot Engine / Doctor-Repair-Verify / 8766 lifecycle / Owner-first Overview

## 1. 目标

Phase 3 已把首次启动和首页从“技术控制台”收敛为 Owner-first，但系统异常仍主要停留在“检测后告诉主人灵机会处理”的界面语义。本阶段把这句话变成真实 Runtime 行为：

```text
巡检
→ 风险分类
→ 仅执行低风险、可验证的修复
→ 修复后重新巡检
→ 记录动作
→ 只有权限、数据完整性或不可逆操作升级给主人
```

实现原则参考 Codex++ 的 silent launcher / Manager 分离思路，但 LingJi 不采用注入能力；只复用自身正式 Runtime、Health、Queue、StateDatabase 和 8766。

## 2. 实现

### `src/autopilot/engine.py`

新增薄编排层 `AutopilotEngine`，不新增数据库、不新增第二套任务队列。

复用：

- `StartupHealthChecker`
- `SQLiteExtractionQueue.release_stale()`
- `MemoryStatisticsService.snapshot()`
- `StateDatabase.events`
- `watchdog_enabled`
- `scheduler_poll_seconds`
- `extraction_stale_after_seconds`

自动动作仅包含：

1. 补齐 LingJi 自己缺失的 `storage/logs/backup` 运行目录；
2. `vault_auto_init=true` 时补齐本地默认 Vault 目录；
3. 释放失去心跳的 extraction lease，让原有队列按既有 retry 合同继续；
4. 每次自动动作后重新运行只读 Health 检查；
5. 将脱敏动作结果写入现有 `lingji_state.db/events`。

### 明确禁止自动执行

- 不调用 `queue.retry()` 重启已经耗尽尝试次数或被主人取消的任务；
- 不自动删除或重建 Qdrant Collection；
- 不自动批准永久记忆；
- 不自动读取未授权 AI 正文；
- 不自动安装模型、ffmpeg、Ollama 等外部组件；
- 不自动修改 Codex / Claude / WorkBuddy 等第三方配置；
- 不自动删除主人数据解决磁盘空间问题。

### 风险分类

直接升级给主人：

- DataRoot 策略异常；
- `lingji_state.db` 完整性异常；
- `lingji_memory.db` 完整性异常；
- Qdrant `rebuild_required=true`。

后台降级并持续复查：

- Ollama/ffmpeg/ffprobe 等可选能力缺失；
- 磁盘空间预警；
- 普通目录问题在安全创建后仍不可用；
- Embedding / Vector 暂时降级但无需重建；
- 已达到自动重试上限的失败任务。

## 3. 8766 生命周期

`run_control_api.py` 创建一个 Runtime-owned `AutopilotEngine`：

```text
create service
→ create AutopilotEngine
→ register authenticated read-only /api/autopilot/status
→ autopilot.start()
→ uvicorn.run()
→ finally autopilot.stop()
→ service.close()
```

TestClient / 普通 `create_control_app()` 不会隐式启动后台线程，避免测试和嵌入场景产生隐藏副作用。

## 4. Desktop

首页直接读取 `/api/autopilot/status`，继续沿用统一 polling hook。

首页不新增 Autopilot 技术面板，只消费：

- `summary`
- `owner_action_count`
- `background_issue_count`
- `recent_actions`
- `verified`

主人看到的是：

```text
有没有需要我确认
灵机正在自动处理什么
刚自动修了什么
是否已经自动复验
```

而不是新的端口、线程、数据库和调度器指标。

## 5. 本地测试

已执行隔离单元测试：

```text
python -m unittest -v test_autopilot_engine.py
4 tests PASS
```

覆盖：

- 缺失运行目录自动创建；
- stale extraction lease 自动释放；
- 自动动作后复验；
- SQLite 完整性异常升级给主人；
- Vector rebuild 只请求主人确认；
- 不调用 exhausted/cancelled job retry；
- watchdog disabled 时零动作；
- 后台线程启动/停止生命周期。

额外执行：

```text
python py_compile engine.py
python py_compile autopilot_api.py
python py_compile run_control_api.py
python py_compile test_autopilot_engine.py
python py_compile test_autopilot_api.py
```

结果：PASS。

## 6. 自动验收

本提交还必须由 GitHub 验证：

- Python 3.11 / 3.12；
- Windows Python；
- `tests/test_autopilot_engine.py`；
- `tests/test_autopilot_api.py`；
- Desktop full smoke；
- React production build；
- Tauri/Rust；
- P0 Windows Gate；
- Windows Desktop Release；
- macOS Apple Silicon Gate；
- acceptance-doc-sync / local-execution-handoff。

CI 未完成前不得把 Phase 4 标记为可真机验收。

## 7. 下一阶段边界

Phase 4 是确定性的安全 Autopilot 底座，不是自由 Agent。未来如果增加模型辅助策略，只允许模型提出候选动作，仍由确定性 policy/permission 层决定是否可自动执行。这样可以继续提升智能程度，而不需要推翻本轮 Runtime 生命周期和审计结构。
