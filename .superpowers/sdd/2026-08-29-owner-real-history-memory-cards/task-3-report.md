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
