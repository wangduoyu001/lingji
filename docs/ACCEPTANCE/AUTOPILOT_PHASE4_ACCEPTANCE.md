# LingJi Phase 4 Autopilot Engine 验收合同

> 日期：2026-08-11
> PR：#88
> 分支：`feature/owner-autopilot-ui-codexpp`
> 产品 Commit：以本轮最终 CI Head 为准
> 实施报告：`docs/TEST_REPORTS/AUTOPILOT_ENGINE_PHASE4_IMPLEMENTATION.md`

## 1. 目标

本轮不再验收“页面写着自动处理”这种装饰性自动化，而是验证真实闭环：

```text
诊断 → 风险分类 → 安全自动修复 → 重新验证 → 审计记录 → 必要时才打断主人
```

## 2. 自动动作白名单

Autopilot 只允许自动执行：

1. 补齐 LingJi 自己缺失的 `storage/logs/backup` 运行目录；
2. `vault_auto_init=true` 时补齐默认 Vault 目录；
3. 调用既有 `SQLiteExtractionQueue.release_stale()` 释放失去心跳的任务 lease；
4. 自动动作完成后再次执行只读 Health 检查；
5. 把脱敏动作结果写入现有 `lingji_state.db/events`。

如果 `data_root_policy`、`state_db` 或 `memory_db` 出现 error，本轮必须停止一切自动写修复，只允许诊断并升级给主人。

## 3. 强制禁止

以下行为出现任意一项即 FAIL：

- 自动 `queue.retry()` 已失败或已取消任务；
- 自动删除/重建 Qdrant Collection；
- 自动修复损坏 SQLite；
- 自动批准永久记忆；
- 自动读取未授权 AI 正文；
- 自动安装 Ollama、ffmpeg、模型或其他第三方依赖；
- 自动修改 Codex / Claude / WorkBuddy 等第三方配置；
- 自动删除主人数据解决磁盘空间问题；
- 新增第二套任务队列、第二个状态数据库或旁路 Runtime。

## 4. 自动测试

必须通过：

```text
python -m pytest -q tests/test_autopilot_engine.py tests/test_autopilot_api.py
npm run test:smoke
npm run build
```

以及仓库现有：

```text
tests
P0 Windows Gate
Windows Desktop Release Baseline
macOS Desktop Gate
acceptance-doc-sync
local-execution-handoff
```

### 单元测试至少覆盖

- 缺失运行目录自动创建并复验；
- stale lease 自动释放；
- failed/cancelled job 不被自动无限重试；
- SQLite integrity error 不触发写修复；
- vector `rebuild_required=true` 只升级给主人；
- watchdog disabled 时零动作；
- Autopilot 后台线程启动、周期执行和停止；
- `/api/autopilot/status` 必须认证且只读。

## 5. 双平台真机回归

macOS 与 Windows 必须使用同一 `src/autopilot/` 实现。

### Runtime

```text
启动 Desktop
→ 8766 healthy
→ /api/autopilot/status running=true
→ cycle_count 自动增长
→ 正常退出 Desktop
→ Autopilot/8766/Core 一起停止
```

不得残留独立 Autopilot 进程或第二个 Core。

### 安全自动修复

只在 task-scoped Acceptance DataRoot 中制造可恢复故障：

1. 删除本轮任务创建的一个可重建 LingJi 运行目录；
2. 等待一个 Autopilot cycle；
3. 目录应自动恢复；
4. `recent_actions` 出现对应动作；
5. `verified=true`；
6. 任务根外文件变化数量为 0。

### stale lease

构造本轮 fixture 的 stale extraction lease：

- 应恢复到原有 Queue retry 合同；
- 不得创建重复 job；
- 不得绕过 max_attempts；
- 已最终 failed/cancelled 的任务不得被 Autopilot 重新排队。

### owner escalation

构造测试状态：

- SQLite integrity error；
- vector rebuild required。

预期：

```text
owner_action_count > 0
自动写修复 = 0
自动 Qdrant rebuild = 0
```

## 6. 首页验收

新增 Engine 后首页仍必须保持 Owner-first：

- 没有 owner action 时明确“无需操作”；
- 后台问题只显示简短结论；
- 最近真实自动修复可显示“刚自动处理 / 已自动复验”；
- 不增加线程、端口、SQLite、Qdrant、scheduler 等技术 Metric 大面板；
- 普通异常不冒充“需要我决定”。

主人最终要能直接感知：

```text
灵机自己发现了问题
灵机自己修了安全可修的问题
灵机自己确认修好没有
只有它不该替我决定的事情才找我
```

## 7. 安全与污染门禁

```text
未授权真实正文读取 = 0
永久记忆自动批准 = 0
第三方 AI 配置自动修改 = 0
自动 Qdrant destructive action = 0
Production 污染 = 0
任务根外测试写入 = 0
```

任一不为 0：FAIL / DO NOT MERGE。

## 8. 报告与清理

每次真机任务仍按当前 M5/Windows task-scoped 临时根执行。

验收后必须：

- 正常停止 App/Core/Autopilot；
- 释放 8766/8767；
- 删除本轮 fixture、临时数据库、Qdrant、日志、截图和临时 DataRoot；
- 保留最终 Markdown 报告和必要脱敏证据；
- 不删除 Production DataRoot、Vault、正式记忆和第三方应用配置。

Phase 4 在双平台 CI 和真实 M5 Owner 体验通过前，PR #88 保持 Draft。
