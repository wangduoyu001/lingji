# Task8E Owner-facing Plain UI Repair Report

## 1. Executive Verdict

```text
Verdict: PASS (focused implementation and rendered/behavior smoke)
Merge recommendation: ALLOW owner observation
Product commit: 6a84c49
Artifact: NOT_BUILT_BY_SCOPE
Artifact ID: NOT_APPLICABLE
Report commit: the commit containing this report (see final delivery SHA)
Owner observation: PENDING
Disposition: READY_FOR_OWNER_EXPERIENCE
```

本轮针对主人反馈“仍然看不懂”简化 Desktop 普通首屏、记忆来源、活动记录、需要我处理和主导航。普通页面现在直接回答灵机是否正常、正在记住什么、最近一次检查结果/时间，以及主人是否需要做事。没有修改 backend、数据模型、队列、自动化、永久记忆权威或 Acceptance/Production 数据。

## 2. Product and Artifact Identity

| 项目 | 实际 | 结论 |
|---|---|---|
| Repository | 灵机 | PASS |
| Product Commit | `99343ec` (`feat: simplify owner-facing primary UI`) | PASS |
| Artifact | 未打包、未安装；按任务边界不生成 | NOT_BUILT_BY_SCOPE |
| Artifact ID / hashes | `NOT_APPLICABLE` | NOT_APPLICABLE |
| Report Commit | the commit containing this report | PASS |

## 3. Change Acceptance Source

- `docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md`：当前仓库版本。
- `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`：`2026-08-29 · Task 8E · Owner-facing plain UI repair`。
- 受影响模块：`desktop/lingji-control` primary owner UI、现有 Playwright owner fixture 与既有 Desktop smoke。
- 风险等级：UI 文案/展示与测试 fixture；API 动作调用保持原有接线。
- 明确不在范围：backend、数据模型、scheduler/automation、队列、Vault、Production、Acceptance 数据、打包、安装和 live app 操作。

## 4. Environment Cleanup

- 未创建或操作 live app、Acceptance root、Production、Vault、真实聊天或主人配置。
- 自动测试使用现有 synthetic/Playwright fixture；未留下运行中的测试进程。
- 未执行停止服务、端口释放、覆盖安装或 Artifact 清理动作，因为本轮未启动/安装/打包。

## 5. Environment and Workspace

```text
OS: macOS host
Workspace: /Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/task8e-safe-polling-fallback
Runtime state: not changed by this task
Control/MCP ports: not exercised by scope
```

## 6. CI and Automated Tests

| 测试 | 结果 | 证据 |
|---|---|---|
| TDD rendered/behavior RED | PASS (RED evidence) | 变更前 `npm run test:e2e:memory` 在新按钮“现在检查”断言处按预期失败 |
| Owner rendered/behavior GREEN | PASS | `npm run test:e2e:memory`；覆盖 0 来源、1 来源、失败/重试、主人待办/解决、Obsidian/Claude 文案、隐藏技术字段与真实按钮动作 |
| Desktop 23-script smoke | PASS | `npm run test:smoke` 输出 `[smoke] PASS (23 scripts)` |
| Desktop build | PASS | `npm run build`；Vite/TypeScript 编译完成 |
| Memory source focused smokes | PASS | `npm run test:memory-sources`、`npm run test:memory-sources-repair`、`npm run test:work-fact` |
| Backend focused regression | PASS | `pytest -q tests/test_task8e_safe_polling_fallback.py tests/test_automatic_memory_scheduler.py tests/test_automatic_memory_runtime.py tests/test_automatic_memory_control_api.py --tb=short`：`56 passed, 1 warning` |
| Compile/diff/docs handoff | PASS | `python3 -m compileall -q src && git diff --check && python3 scripts/check_acceptance_sync.py && python3 scripts/check_local_execution_handoff.py` |
| Full/release validation | NOT_RUN_BY_SCOPE | 本轮禁止打包/安装/live 操作；未伪报通过 |

## 7. Desktop and First-Time UX

- 首页顶层状态使用“灵机运行正常”等口语；无待办时直接显示“你现在不用做任何事”。有待办时只显示当前唯一需要主人处理的事项。
- 首页显示“正在记住什么”“最近一次检查”和“需要你处理”，不再堆叠授权数、接管数、Work Fact、SYSTEM POSTURE 或 internal status。
- 定期文案读取 runtime/API 的真实 interval：有效 900 秒显示“打开灵机时会检查，之后每15分钟自动检查一次”；缺失/非法 interval 显示“检查时间尚未获得”，不伪造 0。
- Managed Obsidian 显示为“Obsidian 长期记忆区”；Claude 限制显示为“Claude 暂不支持自动导入旧记录”。
- 来源动作使用“现在检查”“停止记忆”“查看这次检查”；授权、检查、暂停/恢复、重试仍调用既有 API 并以新 snapshot 验证结果。
- source_id、work_id、internal status、原始 JSON、技术事件仅保留于默认折叠的“技术详情”；普通页面空态使用口语，未知值不显示为 0。
- 未进行主人真机观察；因此不宣称最终 owner acceptance。

## 8. Regression Matrix

| 回归项 | 结果 | 说明 |
|---|---|---|
| UI 按钮无响应 | PASS | owner fixture 真实 mock API 接线验证授权、扫描、停止记忆、重试、待办解决 |
| 假成功或未知值伪造 | PASS | DTO/helper 与四状态 fixture 验证失败、缺失时间和空来源不伪造成功/0 |
| 技术字段泄露到普通卡片 | PASS | rendered assertions 验证 source/work/internal ID、技术标签和 JSON 不在普通视图 |
| Backend safe polling | PASS | 既有 Task8E focused 56 项通过；本轮未改 backend |
| Production/Vault/Acceptance 数据 | NOT_TOUCHED | 未访问、未修改 |
| 打包/安装/live app | NOT_RUN_BY_SCOPE | 明确禁止且未执行 |

## 9. Test Cases

```text
ID: OWNER-PLAIN-0
Name: 0 来源空态
Method: Playwright owner fixture rendered smoke
Expected: 普通页面说明目前没有可接入内容，不显示 0/未知字段伪装
Actual: PASS
Evidence: desktop/lingji-control/tests/e2e_owner_memory_flow.mjs

ID: OWNER-PLAIN-1
Name: 1 来源与 Obsidian 文案
Method: Playwright fixture rendered/behavior smoke
Expected: 显示 Obsidian 长期记忆区和可理解的检查状态
Actual: PASS
Evidence: desktop/lingji-control/tests/e2e_owner_memory_flow.mjs

ID: OWNER-PLAIN-FAIL
Name: 检查失败与再次检查
Method: Playwright fixture action matrix
Expected: 说明这次检查未完成、原记忆不删除，并提供再次检查/查看结果
Actual: PASS
Evidence: desktop/lingji-control/tests/e2e_owner_memory_flow.mjs

ID: OWNER-PLAIN-ATTENTION
Name: 主人待办与解决
Method: Playwright fixture action matrix
Expected: 只显示需要主人处理的事项，完成处理仍调用既有 resolve API
Actual: PASS
Evidence: desktop/lingji-control/tests/e2e_owner_memory_flow.mjs
```

## 10. Owner-Plain Repair Round 1

独立 review `dd86df8` 提出 I1–I5/M1。本轮以新增 rendered 断言先取得有效 RED，再以最小展示修复取得 GREEN：`work:null` 的明确“目前空闲”；真实 completed/running/failed 的 summary 与 scan 详情状态；缺失计数不补默认 0；pending error/stale 的“待办状态暂时无法确认，正在重试”；Claude-only/零可用来源空态；Codex、ChatGPT、generic 与 unknown 来源中文名；以及侧栏普通态隐藏 raw last_error、development、commit、version、工作区路径。原有 API 动作接线、advanced 入口与 900px 检查保持。

Round1 RED 证据包括 fixture 自身参数错误修正后，running 详情断言失败、侧栏断言精度失败、summary/source 切页时序断言失败；调整为真实 UI 文案/等待后，`npm run test:e2e:memory` GREEN。最终 product/tests commit 为 `6a84c49`。

## 11. Known Non-Blocking Limitations

- Owner 尚未在最终候选真机上观察本轮 UI；当前 disposition 只能是 `READY_FOR_OWNER_EXPERIENCE`。
- 未执行 release、打包、安装、live 8766/8767、重启/Windows 验收；这些不属于本轮被授权范围。

## 12. Blocking Defects

None found in focused rendered/behavior or regression checks. Final owner acceptance remains pending by design.

## 13. Final Merge Recommendation

```text
Product commit: 6a84c49
Verdict: PASS (focused implementation and rendered/behavior smoke)
Merge recommendation: ALLOW owner observation
Owner observation complete: NO
Required clients covered: synthetic owner fixture only
Skipped clients: live app / installed clients / release artifact
Blocking defects: None in scoped checks
Acceptance docs synchronized: YES (pending report commit)
Temporary evidence cleaned: YES (no live/temporary acceptance data created)
```

## 14. Sign-off

```text
Codex executor: Task8E Owner-facing Plain UI implementation agent
Owner confirmation: PENDING
Acceptance date: 2026-08-29 (focused checks)
Report branch: codex/task8e-safe-polling-fallback
Report commit: the commit containing this report (see final delivery SHA)
```
