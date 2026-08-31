# Task 0 报告：Owner memory detail drilldown 规划与任务激活

## 结果

```text
worktree: /Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/owner-memory-detail-drilldown
branch: codex/owner-memory-detail-drilldown
base_branch: codex/owner-real-history-memory-cards
base_commit: 94461d56c64f31e1af6c7cde51e959ddc0e8b1
product_code_baseline: 4ce1e00acb17bc5e4e4c183f58d30551ef76b101
scope: planning/docs-only
plan_tasks: 4 (3 implementation + 1 closeout)
implementation_commit: not created in Task 0
```

已完成正式 TDD 计划 `docs/superpowers/plans/2026-08-31-owner-memory-detail-drilldown.md`，覆盖后端
bounded linked-evidence、认证分页 API、selected canonical snapshot、Desktop selected-only 请求、
详情渲染、隐私/authority、分页/409/error、rendered 1024/1280 E2E、focused 门禁及未来 Mac
acceptance 交接。计划固定了接口名称、字段、RED/GREEN 命令和每个任务的提交边界。

## 权威文档变更

- `docs/PROJECT_STATUS.md`：将当前工程门禁切换为唯一 focused implementation task；明确旧
  `4ce1e00a` Mac 候选 `COMPLETED / FAIL`、不再 ACTIVE。
- `docs/MODULES/CODE_MAP.md`：登记 Owner memory detail drilldown 的后端/前端入口、测试入口和
  focused-only/未来 Mac acceptance 边界。
- `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`：新增 2026-08-31 变更条目，记录范围、TDD、
  focused 命令、禁止 live/安装/主人数据和后续 Mac 五类记忆/多来源原文要求。
- `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`：激活唯一任务
  `OWNER_MEMORY_DETAIL_DRILLDOWN_IMPLEMENTATION`，产品基线为 `94461d56...`，执行模式为
  `FOCUSED_PRODUCT_IMPLEMENTATION_ONLY`。
- `docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md`：建立对应 PENDING 回执；旧 Mac 4ce 候选明确 FAIL
  并与当前 implementation receipt 分离；未创建 Acceptance 根或运行进程。
- `.superpowers/sdd/2026-08-31-owner-memory-detail-drilldown/task-0-report.md`：本报告。

## 隔离与自检

- `.worktrees/` 忽略核验：`git check-ignore -v .worktrees` → `.git/info/exclude:7:.worktrees/`。
- 独立 worktree 已从 `codex/owner-real-history-memory-cards` 的 `94461d56` 创建；没有修改现有
  acceptance worktree 或根 checkout 的未提交文件。
- `rg -n -i 'TODO|TBD|占位|Similar to Task|write tests for the above' docs/superpowers/plans/2026-08-31-owner-memory-detail-drilldown.md`
  仅命中正常的“后续 Mac”措辞，不包含计划占位项；计划自评清单逐条覆盖用户范围。
- Task 0 未运行产品测试、live 服务、安装、Artifact、真实聊天/Vault/数据库或主人数据操作。

## 预期门禁

提交前运行并记录：`git diff --check`、`python3 scripts/check_acceptance_sync.py`、
`python3 scripts/check_local_execution_handoff.py`。本报告所在 docs-only 提交的 SHA 由最终 Git
提交返回值确定，并随交接消息回传。

## Plan Repair 1

根代理预检指出原计划过度拆分并混入接口冲突，已在同一 worktree 收束修订：

- 计划从 9 个任务改为 3 个实现任务 + 1 个收口任务，共 4 个任务。
- 删除 `get_memory_detail()` 及把 card conclusion/freshness/layers/action 混入
  `/memories/{id}` 的设计；Desktop 明确组合 `/cards/{id}`、bounded `/memories/{id}`、`/vector`、
  `/source` 与唯一 evidence route。
- evidence route 固定默认 20、最大 50、excerpt<=240、content<=4000、单页 content<=24000，
  带 `truncated`；完整单条正文继续走 `/messages/{id}`。
- conversation-only 由前端依据 card kind/source conversation_id 处理，不调用 canonical；安全测试
  改为未授权/撤销来源正文不泄漏、safe refs only、绝对路径/cookie/auth metadata 不出现。
- `.superpowers` 报告保持 ignored，不列为 git add 目标；正式 report 路径固定在 `docs/TEST_REPORTS/`。

本轮未运行产品测试、live 服务、安装、Artifact 或主人数据，仅执行文档自检与治理门禁。

Plan Repair 1 的 docs-only 修订提交为 `b03857fdd84675bf144b4ae8f240ecc0fe5d6471`；报告文件按
`.superpowers` ignored-workspace 规则保留在本机，不作为该提交的 git add 目标。
