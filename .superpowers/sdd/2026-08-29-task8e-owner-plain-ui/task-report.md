# Task8E Owner-facing Plain UI Repair Report

## 1. Executive Verdict

```text
Verdict: PASS (focused implementation and rendered/behavior smoke)
Merge recommendation: ALLOW owner observation
Product commit: 58e12ca
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
| Product Commit | `58e12ca37b321075445c49057c54851f55539baf` (`fix: preserve early scan outcomes`) | PASS |
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
| Owner rendered/behavior GREEN | PASS | `npm run test:e2e:memory`；覆盖 Round1 四状态与 Round2 accepted/retrying、Claude consent 空路径、详情默认计数、隐藏技术字段与真实按钮动作 |
| Desktop 23-script smoke | PASS | `npm run test:smoke` 输出 `[smoke] PASS (23 scripts)` |
| Desktop build | PASS | `npm run build`；Vite/TypeScript 编译完成 |
| Memory source focused smokes | PASS | `npm run test:memory-sources`、`npm run test:memory-sources-repair`、`npm run test:work-fact` |
| Backend focused regression | PASS | `pytest -q tests/test_task8e_safe_polling_fallback.py tests/test_automatic_memory_scheduler.py tests/test_automatic_memory_runtime.py tests/test_automatic_memory_control_api.py --tb=short`：`56 passed, 1 warning` |
| Compile/diff/docs handoff | PASS | `python3 -m compileall -q src`; `git diff --check`; `python3 scripts/check_acceptance_sync.py`; `python3 scripts/check_local_execution_handoff.py` |
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

## 11. Owner-Plain Repair Round 2

独立复审 `27ff136` 提出剩余 I1–I3。本轮先在 owner fixture 中增加 `accepted`/`retrying`、正式 Claude `consent_required + 空路径` 与详情 model-default 计数 0，取得 RED；随后最小修改 WorkStatus 中文映射、来源可连接判定和 scan detail 计数展示，取得 `npm run test:e2e:memory` GREEN。既有动作 API 与 backend 均未修改。

Round2 最终证据：rendered E2E `PASS`；23-script smoke 输出 `[smoke] PASS (23 scripts)`；build PASS；backend focused `56 passed, 1 warning`；compile、diff-check、acceptance-sync、local-handoff PASS。产品/测试 commit 为 `f2f4843`。

## 12. Owner-Plain Repair Round 3

最终复审 `task-repair-2-review.md` 仅剩 I1：正式 `ScanRun` 模型对 StateDB 未提供的计数字段使用模型默认 0，completed detail 因而可能把未知显示成 0。本轮先在 rendered fixture 增加 completed 缺字段、legacy/default 0、明确 0、明确正数四态，RED 断言确认 legacy default 0 被误显示；随后在 Desktop `memorySourcesApi.ts` 建立 `scanCountValue` adapter 边界，只有数值为正或 DTO 明确通过 `counts_present` 标记该字段存在时才保留数字，缺字段/无标记默认 0 统一为 `undefined`。Home 摘要与检查详情共用该 helper，后端、API、数据模型和真实数据均未改动。

Round3 GREEN 证据：`npm run test:e2e:memory` `PASS`；`npm run test:smoke` 输出 `[smoke] PASS (23 scripts)`；`npm run build` `PASS`；Task8E focused backend `56 passed, 1 warning`；`python3 -m compileall -q src`、`git diff --check`、`python3 scripts/check_acceptance_sync.py`、`python3 scripts/check_local_execution_handoff.py` 均 `PASS`。产品/测试 commit 为 `ea87ebe41ab37d44789ec68a126629fc074a483a`。

## 13. Known Non-Blocking Limitations

- Owner 尚未在最终候选真机上观察本轮 UI；当前 disposition 只能是 `READY_FOR_OWNER_EXPERIENCE`。
- 未执行 release、打包、安装、live 8766/8767、重启/Windows 验收；这些不属于本轮被授权范围。

## 14. Blocking Defects

None found in focused rendered/behavior or regression checks. Final owner acceptance remains pending by design.

## 15. Final Merge Recommendation

```text
Product commit: 33b730ec8de1b7b545da7c5eecdb70cdcf67e30e
Verdict: PASS (focused implementation and rendered/behavior smoke)
Merge recommendation: ALLOW owner observation
Owner observation complete: NO
Required clients covered: synthetic owner fixture only
Skipped clients: live app / installed clients / release artifact
Blocking defects: None in scoped checks
Acceptance docs synchronized: YES (pending Round2 report commit)
Temporary evidence cleaned: YES (no live/temporary acceptance data created)
```

## 16. Owner-Plain Repair Round 4

Round4 closes the Round3 formal evidence gap instead of adding another UI-only
marker. StateDB now migrates nullable `queued_count`/`reused_count` columns
additively, preserving `NULL` for old rows. Snapshot completion and scheduler
completion write counts atomically only when the completed scan has measured
them; an actually empty completed scan records explicit zero, while paused,
failed, crashed, unmeasured and legacy rows remain unknown. `ScanRun`, the
Local Control API list/summary/detail/action responses, and the rendered owner
fixture use the same `counts_present` contract. A compatibility dictionary with
model-default zero and no presence marker is treated as unknown. Same-second
scan transitions use SQLite insertion order as a deterministic latest tie-break.

TDD evidence: the initial backend run exposed the same-second latest ordering
failure (`1 failed`); a dedicated legacy-default-zero test then exposed the
compatibility projector gap (`1 failed`). The focused repair matrix is now
`47 passed, 1 warning`. Owner rendered E2E is PASS; Desktop smoke is PASS for
23 scripts; build is PASS with 92 modules transformed; Task2–5 related backend
regressions are `183 passed, 3 warnings`; compileall, diff-check, acceptance
sync and local handoff are PASS. The broad repository run was not repeated in
Round5; the independent Round4 review records 24 failures (including quality-
evaluation/environment and unrelated legacy contracts), rather than the
previous report's stale count of 22. None were changed or reclassified as
Round4 failures.

Round4 remains limited to scan evidence and its owner-facing projection. It
does not change watcher strategy, introduce a second queue/database, or touch
live/Acceptance/Production/Vault/owner data. Product/tests are committed at
`33b730ec8de1b7b545da7c5eecdb70cdcf67e30e`; docs/report are committed
separately. Owner observation and a new Mac artifact remain pending.

## 17. Owner-Plain Repair Round 5

Round5 addressed the two Important findings from the independent Round4 review.
The scheduler now preserves `queued`/`reused` as unknown for legacy, paused,
failed, crashed, and otherwise unmeasured scans. Internal progress arithmetic
uses a local zero fallback only; reconciliation events, Work Facts, and API
projections retain the unknown state. A completed scan with measured zero or a
positive count still persists and exposes that real value.

The single Local Control API projector now gives action, list, summary, and
detail responses the same stable `automatic-memory:<scan_id>` `work_id`, and
action responses retain real non-admitting outcomes such as `complete=false`,
errors, and next action when no durable scan row exists. No UI-local ID was
introduced. New tests cover legacy count absence, Work Fact unknown counts,
cross-endpoint work identity, and non-admitting action results.

TDD evidence: the two requested I1/I2 RED cases failed before implementation;
the focused GREEN checks passed. Direct backend focused regression is
`69 passed, 1 warning`; Round5 repair tests are `17 passed, 1 warning`; the
Task2–5 affected matrix is `184 passed, 3 warnings`. Packaged flow with an
explicit compatibility event-watcher setting passed `2 passed, 1 warning` in
291.19 seconds, after reaching event, expiry, pause/resume, and crash-recovery
contract checks. Desktop rendered E2E, all 23 smoke scripts, and the 92-module
build passed. `compileall` and diff-check passed.

The first packaged attempt on the Mac default periodic policy correctly did
not produce the old event-triggered scan; a second attempt reached the same
flow but stopped because the system Python lacked the optional `mcp` package.
These were environment/policy observations, not suppressed product failures;
the required dependency was installed from `requirements-mcp.txt` and the
packaged test passed. No live App, Acceptance/Production/Vault root, or owner
data was started or touched. Product/tests are committed at
`ca6b8ea40cf6d95974639af213ca6ee41e08bdee`; this Round5 report and authority
docs are committed separately. Final owner observation and a Mac artifact
remain pending.

## 18. Owner-Plain Repair Round 6

Round6 closes the two Important findings from the independent Round5 review.
`ReconciliationReport.counts_measured` now defaults to `False`, and all direct
scheduler early exits preserve unknown `queued`/`reused` values. Paused,
unsupported, degraded, expired, contended, and unexpected-exception paths also
avoid publishing unmeasured `discovered`/`unchanged` zeroes. Only internal
progress arithmetic uses a local zero fallback; measured completed scans retain
their real zero or positive counts.

The formal report now carries `next_action`. Real scheduler/runtime/API paths
return a truthful action for paused, unsupported, expired, degraded, lease
contention, and exceptions. The authenticated API tests use real
`AutomaticMemoryRuntime`, `SourceRegistry`, scheduler, and StateDB; they do not
use a fake runtime for these cases. Existing Round5 stable work identity and
packaged contract behavior remain unchanged.

Verification: Round6 early-exit/API focused checks `7 passed, 1 warning`; the
full backend focused set is `65 passed, 1 warning`; the Task2–5 affected matrix
is `229 passed, 3 warnings`. Desktop rendered E2E passed; all 23 smoke scripts
passed; the build transformed 92 modules; compileall, diff-check,
acceptance-sync, and local-handoff passed. The 291-second packaged flow was not
repeated because its directly affected contract had already passed in Round5.

No live App was started or installed and no Acceptance, Production, Vault, or
owner data was touched. Product/tests are committed at
`58e12ca37b321075445c49057c54851f55539baf`; this report and authority docs are
committed separately. Final Mac artifact and owner observation remain pending.

## 19. Sign-off

```text
Codex executor: Task8E Owner-facing Plain UI implementation agent
Owner confirmation: PENDING
Acceptance date: 2026-08-29 (focused checks)
Report branch: codex/task8e-safe-polling-fallback
Report commit: the commit containing this report (see final delivery SHA)
```

## 20. 真实发布版主人可读性修复

根代理在当前真实 `/Applications/灵机.app` 候选上观察到普通页面仍然难以理解，
因此本轮只补齐对应的展示语义，不改后端、自动化、队列、数据模型、记忆权威或
运行中的 App。修复内容如下：

- Claude 受限卡片现在明确说明“Claude 暂时无法自动导入旧记录；灵机不会读取它的内部数据库。”，不提供误导性的授权按钮。
- 普通来源和活动卡片使用“Obsidian 长期记忆区”，目录名不再出现在普通文案中；精确路径仍只留在技术详情/API。
- 空扫描显示“检查完成，未发现新内容”，系统下一步显示“灵机会继续自动检查”。
- 同一来源连续/近期的成功且无变化检查在活动页合并为一条，并显示例如“近期已检查102次”；失败、处理中和待主人处理的事项仍逐条展示。
- 启动、自动恢复和高级诊断的眉标改为中文；技术详情和高级页面的技术内容仍可访问。

TDD 证据：新增真实 Playwright rendered fixture 后，首次运行在空扫描结果断言处
按预期 RED；随后最小实现 GREEN。`npm run test:e2e:memory` PASS，
`npm run test:smoke` PASS（23 scripts），`npm run build` PASS（92 modules）。
构建期间发现并修复一个新增可空类型错误后重新构建通过；`git diff --check`
通过。产品/测试提交为 `77eeacb`。

本轮未打包、未安装、未停止或修改真实 App，未访问 Acceptance/Production/Vault/
主人数据；父任务要求保留的 `desktop/lingji-control/src-tauri/binaries/`
未跟踪打包产物保持原样。主人仍需在新的 macOS 候选上确认“能看懂”，因此本报告
状态仍为 `READY_FOR_OWNER_EXPERIENCE`，不能据此宣称 Phase 1 或最终发布通过。

## 21. Real UI Repair Round 1 — 活动事实边界

独立审查发现上一轮活动压缩逻辑存在两项重要问题：读取了错误的结果字段，
无法识别正式自动扫描的 `outcome.summary`；并且会把所有 quiet 条目集中合并，
跨越失败、不同来源和分页边界。本轮仅在 Desktop 活动展示层修复。

- 新增受控 `normalizeActivityResult`：优先读取正式 `outcome.summary`；严格匹配
  “扫描完成，已检查 0 个来源文件（新增 0，复用 0）”（及受控 ASCII 括号等价形状）
  才显示“检查完成，未发现新内容”。真实新增/更新文本、失败文本和处理中状态不会
  被归类为空扫描，也不会被 `summary.result=成功` 覆盖。
- 新增稳定来源身份判定：优先使用 `summary.source_id`，否则使用
  `work.source_id`；没有身份的条目不参与压缩。合并只发生在输入顺序中相邻、
  同一身份的成功空扫描连续段，连续段长度至少为 2；失败、处理中、变化记录、
  不同来源和跨页记录都不会合并。次数只来自该段实际条数，不使用 API `total` 或
  `has_more` 推断。单条空扫描仍显示友好结果，但不虚构“近期已检查1次”。
- Activity WorkCard 与压缩逻辑共用同一结果归一化 helper；正式技术数据仍保留在
  原始对象/折叠详情中。

TDD 证据：真实渲染 fixture 先以正式 WorkProjector shape（`summary.result=成功`、
`outcome.summary` 为实际扫描结果）复现 RED；随后通过空/失败/空、同名不同来源、
变化、跨页、单条和处理中矩阵取得 GREEN。`npm run test:e2e:memory` PASS，
`npm run test:smoke` PASS（23 scripts），`npm run build` PASS（92 modules），
API 回归 `25 passed, 1 warning`，`compileall`、`git diff --check`、验收同步和
本机交接检查均完成；产品/测试提交为 `c6edcd2`。

本轮没有打包、安装或操作 live App，没有访问 Acceptance/Production/Vault/主人数据；
父任务预先存在的 `desktop/lingji-control/src-tauri/binaries/` 未跟踪打包产物未修改。
独立复审和主人最终可读性确认仍然是后续门槛。

## 22. Real UI Repair Round 2 — 压缩活动完整审计

独立审查发现上一轮活动页将连续的安静扫描折叠成一张普通卡片时，只保留首条
Work Fact 的技术详情，其余成员的工作 ID、来源、原时间、状态和执行事件无法从
页面找回。本轮仅修复 Desktop 展示视图模型，未修改后端 DTO、自动化、队列、数据
模型、永久记忆权威或运行中的 App。

- `collapseQuietActivity` 现在返回显式 `ActivityCardModel`：普通页使用首条作为
  展示锚点，`compactedItems` 保存连续段内全部原始 `WorkHistoryItem`，不向后端
  DTO 增加私有字段。
- 合并仍只允许输入顺序中相邻、同一稳定 `source_id` 的成功空扫描；失败、处理中、
  有新增/更新、不同来源和不同分页响应不会合并。次数只使用当前连续段的真实成员
  数量，单条不显示虚假的“近期已检查1次”。
- 技术详情逐条显示每个成员的工作 ID、来源 ID、原始时间、状态码和完整执行事件
  JSON；普通标题、结果和元信息不泄露这些内部字段。原始审计仍可通过折叠详情访问。

TDD 证据：渲染 fixture 使用正式 WorkProjector 形状，并为三条连续记录提供不同的
 原始时间与事件 detail。新增断言先在旧实现上于“第二条审计必须保留”处失败；最小
实现后 `npm run test:e2e:memory` PASS。测试还验证失败分隔后的两段审计互不串联、
同名不同来源不合并、分页总数不影响次数、单条和处理中状态保持原样。

验证结果：

- `npm run test:e2e:memory`：PASS（`e2e_owner_memory_flow: PASS`）。
- `npm run test:smoke`：PASS（23 scripts）。
- `npm run build`：PASS（92 modules transformed）。
- 受影响后端：`62 passed, 1 warning`。
- `python3 -m compileall -q src`、`git diff --check`、
  `python3 scripts/check_local_execution_handoff.py`：PASS。
- 本轮不打包、不安装、不停止或操作 live App，不访问 Acceptance/Production/Vault/
  主人数据；预先存在的未跟踪 `desktop/lingji-control/src-tauri/binaries/` 保持原样，
  不属于本轮提交。

产品/测试提交为 `5fbe9db6d6be93d32c3b57cea0ea7ef3e4f6bef4`。本报告和验收日志在独立
文档提交中记录；主人最终观察仍需根代理在当前候选上完成，本报告不能单独宣布 Mac
发布版或 Phase 1 通过。

## 23. Real UI Live-shape Repair Round 3 — Claude 与当前工作结果

根代理在真实发布版抓到两类正式数据形状。本轮只修复对应的 Desktop 展示适配，未修改
后端、自动化、队列、数据模型、Activity 审计逻辑、永久记忆权威或运行中的 App。

- Claude 的 `claude_desktop + consent_required + 空路径 + 英文 reason` 与
  `unsupported` 均显示“Claude 暂时无法自动导入旧记录；灵机不会读取它的内部数据库。”；
  下一步显示“请等待 Claude 提供受支持的官方导出，或暂不接入。”，英文 reason 不进入
  普通页面，且没有授权按钮。
- 新增受控 `formatWorkFactResult`，优先解释正式 `outcome.evidence`：completed 且
  `jobs=0、queued=0` 显示“检查完成，未发现新内容”；queued 为正且摘要只是通用“成功”
  时显示准确的“检查完成，新增 N 条内容”；失败、未知或未测量状态不会误判为空扫描。
  原始 outcome summary/evidence 只在“查看技术详情”中保留。
- Overview 对明确的 `queued=0` 不显示“新增 0 条”；若无其他实际变化则显示“未发现新内容”，
  正数与未知值继续分别显示准确数量或不造数。

TDD 证据：真实形状 rendered fixture 先在旧 UI 上于当前工作空扫描文案处失败；修复后
  `npm run test:e2e:memory` PASS。fixture 还覆盖 Claude 两态、正数 queued、技术详情原文
  和首页明确 zero；此前 Round2 的连续压缩审计断言保持在同一 E2E 中。

产品/测试提交为 `b8035f030a558bb990fb256004e89a98f3151d50` 与
`4b2708a8f940fb4ef2a5e26832088486ec885134`。本报告与验收日志在独立
文档提交中记录；主人最终观察仍需根代理完成，本报告不能单独宣布 Mac 发布版或 Phase 1
通过。
