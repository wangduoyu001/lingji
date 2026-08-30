# Task 3 Report — Owner Memory Cards and Safe Corrections

## Scope

基于产品基线 `9a3e560`，实现主人可读的“记忆内容”卡片页、四项普通导航、低强调高级诊断入口、首页同源卡片摘要，以及 owner-confirmed 的修正、失效和移出当前记忆动作。没有启动 live/App/Acceptance，没有读取真实聊天、主人数据或 Production/Vault。

## TDD evidence

- RED: 新增 `tests/test_owner_memory_corrections.py` 后，基线运行得到 3 failures，原因是 `MemoryReviewService` 尚无 `correct_core_memory` / `invalidate_core_memory`。
- GREEN: 实现最小 lifecycle/review/API 转换后，生命周期行为测试通过；候选确认、编辑确认、拒绝、修正 supersede、失效保留文件、stale hash 409 均有覆盖。
- UI rendered RED/GREEN: 卡片导航/21-card fixture 断言在旧导航和缺页实现时不可满足；实现后 `npm run test:e2e:memory` 通过。

## Implemented

- 普通菜单严格为 `首页 / 记忆内容 / 需要我 / 记忆来源`；活动记录保留 direct route，仅从首页摘要进入；高级诊断为单一低强调入口。
- 新增 OwnerMemoryCards API/types/page：默认每页 20 条；21 张合成卡覆盖两页，显示精确 total，1280px 两列、1024px 一列，卡片最多三条证据过程。
- 默认表面使用中文主题、结论、时效、来源、四层状态、可信提示和唯一建议动作；raw/structured/vector/permanent/chunk/hash/path/内部 ID/JSON 不在默认卡片文本中。
- “查看来源”只请求选中卡片的第一条 message detail；动作完成后 fresh GET；409 显示冲突提示且不覆盖。
- 新增 `/correct`、`/invalidate` lifecycle/API 语义；修正生成新 owner-confirmed 版本并 supersede 旧版，失效更新 valid_to/reason，archive 保留原始/历史/来源/审计，未增加 DELETE。
- Card projector detail-only 暴露 current hash，列表不暴露 hash，保证动作可校验且默认不泄漏技术字段。

## Verification

| Check | Result |
|---|---|
| Lifecycle + card projector/API + review/API regressions | `25 passed, 1 warning` |
| Rendered E2E | `e2e_owner_memory_flow: PASS` |
| Desktop smoke | `PASS (23 scripts)` |
| Desktop build | `tsc -b && vite build` exit 0 (既有 dynamic-import warnings) |
| Python compile | `python3 -m compileall -q src` exit 0 |
| Diff check | `git diff --check` exit 0 |
| Acceptance sync / local handoff | 待 docs 提交后执行 |

## Commits

- Product/tests: `21ad4ae` (`feat: add owner memory cards and safe corrections`)
- Docs/evidence: this docs/evidence commit (SHA recorded by the final git commit)

## Limits and risks

- 未执行真实 8766、发布版、Artifact、Mac/Windows、Production/Vault 或主人观察；本报告仅代表代码与合成 fixture 验证。
- 首页工作摘要继续复用现有 Activity/CurrentWork 投影；真实主人体验仍需后续任务按验收规则确认。
- 运行环境没有 `./.venv/bin/pytest`，使用系统 `python3 -m pytest` 完成同一测试集。

## Repair Round 1 — independent review closure

基于审查基线 `179bf3f88d4cb9daf86f2cbe46afefbe63478317`，保留前代理的全部工作树改动，逐项处理审查中的 I1–I8/M1–M2：

- 首页改为只读取完整 `cards-summary` 投影，补齐已导入对话/消息，并展示真实 `/api/work/history` 的最多三条 Work Fact；未知消息统计保持“尚未获得”，不以零代替。
- Core 卡按 lifecycle action 正确分流到 `correct`、`invalidate`、`archive`，永不把 Core ID 发送到 candidate API；修正继续复制 source refs、relationships、confidence 和 validity；archive 强制原因并返回可审计原因。
- 列表只使用 bounded `memory_sources` links/preview，完整 message detail 只在选中卡片后读取；无标题卡片使用不含内部 ID 的稳定中文 fallback；来源行显示最新证据时间，归档原因进入 freshness。
- 详情具备 dialog/aria 标记、打开聚焦标题、Esc 关闭并返回触发按钮、动作 aria-live 成功/失败/冲突反馈和 busy 文案；现有 `.button`/pager 命中区为 40px。
- 合成 rendered E2E 增加 Home 完整统计与无卡片正文请求、Work Fact、Core correct/invalidate/archive 真实 endpoint、fresh GET、409 保留、selected message request 计数、1280/1024 布局与键盘关闭验证；仍不启动 live/App/Acceptance、不读取真实聊天或 Vault。

### Repair TDD evidence

- 新增 projector/API/lifecycle 测试先在当前草稿复现 RED：核心 invalidated/archive 返回 `review`、缺失 message count 被求和、archive 空原因不报错、cards-summary 路由在旧基线为 404，以及 bounded preview 未从 memory links 取得。
- 将新增 projector 测试复制到 `179bf3f` 临时隔离树，旧基线得到 6 failures；将 cards-summary API 测试复制到同一基线得到认证请求 404。临时树未触及本工作树。
- 逐项补最小实现后 GREEN：`52 passed, 1 warning`（Task3 card/projector/API、corrections、review/inspector regressions）；`npm run test:e2e:memory`、`npm run test:smoke`（23 scripts）和 `npm run build` 均通过；`compileall`、`git diff --check` 通过。

### Repair commit

- Product/tests: `f34b6f9` (`fix: close owner memory card review gaps`)
- 本报告与 `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md` 作为独立 docs/evidence 提交；未执行真实 8766、发布版、Artifact、Mac/Windows、Production/Vault 或主人观察。

## Task 3 Repair Round 2 — re-review closure

基线为 `f41673f`（clean）；范围严格限于 `task-3-re-review-1.md` 的 I1–I9/M1–M2，未重做已通过的功能，也未新增数据库、设计系统、后端路由或物理删除。

### Disposition

| Item | Disposition |
|---|---|
| I1 | Fixed: summary 对 vector/permanent 的 unknown/unavailable 返回 `null`，Home 显示“尚未获得”，不把未知计为 0。 |
| I2 | Fixed: `get_card` 只返回 bounded evidence metadata/preview；详情打开不预取正文，只有选择证据行后才读取对应 message。 |
| I3 | Fixed: revoked card 使用现有 `memory_sources` 导航和授权流程，未新增后端。 |
| I4 | Fixed: correct 使用 canonical inspector 正文，mutation 返回 replacement id 后 fresh GET；复制 evidence/source relationships，并用现有 read-model links 保留 raw/history/source/audit。 |
| I5 | Fixed: `edit_and_approve` 在任何 candidate 读写前执行 owner gate；archive 要求 expected hash。 |
| I6 | Fixed: event-only 无标题时使用不含内部 ID 的中文 fallback。 |
| I7 | Fixed: 新增真实 `MemoryDatabase`/`SourceReadModel`/projector/lifecycle probe，并扩展 rendered E2E 覆盖 candidate、revoked、unknown、retention、409、request count、focus、keyboard、1024/1280。 |
| I8 | Fixed: nested card action 的 keydown 忽略事件目标不是 card 本身的情况，避免重复 detail GET；E2E 已验证。 |
| I9 | Fixed: direct API/service tests 覆盖认证、owner false、schema/content/reason、hash、stale 409、valid_to、archive reason/hash、response 和保留链路。 |
| M1 | Fixed: freshness 状态补齐人话标签；非法日期显示“时间尚未获得”，不显示 `Invalid Date`。 |
| M2 | Fixed: 每条 evidence preview 为可键盘选择的 button，`aria-pressed` 反映选择；source 只读取选中行。 |

### TDD and verification

- RED 已在基线隔离副本中确认：Round 2 direct projector/review tests 首轮为 `5 failed, 6 passed`（unknown summary、正文预取、ID fallback、owner gate、archive hash）；新增 read-model link test 首轮因缺少 evidence store 接口失败；API archive missing hash 首轮错误返回 200；rendered evidence-selection 断言在旧 UI 超时。工作树未被 reset/checkout/覆盖。
- GREEN（可复制命令）：`python3 -m pytest -q tests/test_owner_memory_corrections.py tests/test_owner_memory_card_projector.py tests/test_owner_memory_card_api.py tests/test_memory_review_service.py tests/test_memory_inspector_api.py tests/test_memory_inspector_facade.py tests/test_project_memory_api.py tests/test_task3_round2_direct.py tests/test_task3_round3_integration.py tests/test_source_read_model.py tests/test_source_service.py --tb=short` → `85 passed, 1 warning`。
- Rendered owner flow：`npm run test:e2e:memory` → `e2e_owner_memory_flow: PASS`。
- Desktop smoke：`npm run test:smoke` → `PASS (23 scripts)`。
- Desktop build：`npm run build` → TypeScript/Vite exit 0，96 modules，只有既有 dynamic-import warnings。
- Compile/diff：`python3 -m compileall -q src tests` 与 `git diff --check` 通过。
- 本轮未启动 live/App/Acceptance，未读取真实聊天、Production/Vault/主人数据，未执行打包、安装或 Artifact；因此仍需主人体验验收。

### Commits

- Product/tests：`10287c2`（`fix: close task3 repair round2 contracts`）。
- Docs/evidence：`e75d7cf`（报告与 acceptance log 独立提交；本行在后续 docs 校正提交中固定记录）。

## Task 3 Repair Round 3 — final re-review closure

基于复审 `task-3-re-review-2.md`，仅处理 I1–I4/M1：

| Item | Disposition |
|---|---|
| I1 | Fixed/verified：rendered fixture 补齐 superseded、not_permanent、rejected、rolled_back、repair_required、not_yet_current、unknown 人话状态；新增 `MemoryInspectorFacade`→production projector DTO probe。 |
| I2 | Fixed/verified：tmp Vault + 真实 `MemoryLifecycleService`/`MemoryReviewService`/`MemoryDatabase`/`SourceReadModel` 注册同一 mutation API，覆盖 candidate 三动作、correct canonical chunks/replacement/read-model links/old superseded/source/history/audit、invalidate/archive reason/valid_to/hash、auth/schema/stale 409。 |
| I3 | Fixed/verified：报告与 acceptance log 改为唯一可复制 focused pytest 命令，实际结果为 `85 passed, 1 warning`，不再引用不可复现的 181。 |
| I4 | Fixed/verified：archived 与 superseded core fresh DTO 改为 `review/查看历史记录`，不再显示会失败的 archive mutation；rendered fresh GET 断言无“移出当前记忆”按钮。correct 后同步旧 read-model row，fresh old/new 状态一致。 |
| M1 | Fixed/verified：`memory_sources`/link 查询异常标记 provenance unknown，禁止仅凭 metadata hash 变成 verified；conclusion 清空并建议 review。 |

### Round 3 verification

- RED：在只加入 Round3 projector tests 后，目标失败为 `2 failed, 25 passed, 1 warning`（archived core dead action、memory_sources 异常 provenance fail-open）；rendered E2E 新状态矩阵首轮以缺失 superseded 人话标签失败，归档 fresh-GET 断言首轮以仍显示 archive 按钮失败。修复后再进入 GREEN。
- Focused/integration：见上方精确命令，`85 passed, 1 warning`。
- Rendered owner E2E：`npm run test:e2e:memory` → `e2e_owner_memory_flow: PASS`。
- Desktop smoke：`npm run test:smoke` → `PASS (23 scripts)`；build → PASS（96 modules）。
- `python3 -m compileall -q src tests`、`git diff --check`、acceptance sync、local handoff → PASS。
- 全程未启动 live/App/Acceptance，未读取真实聊天、Production/Vault 或主人数据；未执行打包、安装或 Artifact。

### Round 3 commits

- Product/tests：`ae01b24`（`fix: close task3 repair round3 contracts`）。
- Docs/evidence：`8fea0ed`（报告与 acceptance log 独立提交；本行在后续 docs 校正提交中固定记录）。

## Task 3 Repair Round 4 — final detail-fixture closure

基于 `task-3-re-review-3.md`，本轮唯一范围是 E2E detail fixture fallback；未修改生产代码。

| Item | Disposition |
|---|---|
| I1 | Fixed/verified：detail fixture 复用与列表相同的 topic、freshness、action、kind、state、permanent 派生；card-7/8/9 及后续历史/unknown 状态不再默认回落 `correct`。 |
| I2 | Fixed/verified：rendered E2E 打开 superseded、not_permanent、rejected、rolled_back、repair_required、not_yet_current、unknown 卡，逐项断言不显示修正/过时/移出 mutation 按钮；归档 fresh GET 仍无死 archive action。 |

### Round 4 TDD and verification

- RED：旧 detail fixture 在 card-7 打开后错误显示“修正内容”，新增断言失败；修复后复跑 E2E 通过。
- Focused（唯一可复制命令）：沿用 Round3 精确命令，结果 `85 passed, 1 warning`。
- `npm run test:e2e:memory`：`e2e_owner_memory_flow: PASS`。
- `npm run test:smoke`：`PASS (23 scripts)`（包含该 rendered E2E）；`python3 -m compileall -q src tests` 与 `git diff --check`：PASS。
- 本轮无生产/TypeScript 变更，未重复 build；未启动 live/App/Acceptance，未读取真实聊天、Production/Vault 或主人数据。

### Round 4 commits

- Tests：`7ccbc02`（仅 `desktop/lingji-control/tests/e2e_owner_memory_flow.mjs`）。
- Docs/evidence：`93c1e1e`（报告与 acceptance log 独立提交；本行在后续 docs 校正提交中固定记录）。
