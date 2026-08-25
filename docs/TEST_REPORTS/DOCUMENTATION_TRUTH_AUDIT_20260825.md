# LingJi 文档事实审计记录 — 2026-08-25

> 文档角色：本次文档治理的审计与验证证据，不是新的项目状态权威。
> 当前状态仍以 `docs/PROJECT_STATUS.md` 为准。

## 1. 审计身份

```text
Repository: wangduoyu001/lingji
Remote default branch: master
Audited commit: ced1128e50d3b3758585573042ea6bcc6f315384
Documentation branch: codex/docs-project-truth-audit
Product-status comparison baseline: 3d7225f58fb5b5a9b035cfd72f92cb2267b48559
Latest physical owner acceptance: COMPLETED / FAIL / DO NOT MERGE
Current local execution task: IDLE
```

GitHub 只读核对显示，开始任务时原本打开的验收分支比远程 `master` 落后 81 个提交并额外带有 8 个旧验收提交；本审计因此从远程 `master` 单独创建隔离工作区，未修改原验收分支。

## 2. 全量文档人口

审计基线包含 403 个受 Git 跟踪的 Markdown、MDX、RST、TXT、README/AGENTS 类文件。统计使用 `git ls-tree -z` 读取原始路径，避免中文文件名被 Git 转义后漏计。

| 类别 | 数量 | 当前状态职责 |
|---|---:|---|
| PEMIS 生成数据 | 125 | 历史生成快照，不是工程进度权威 |
| `docs/TEST_REPORTS` 历史证据 | 70 | 证明特定 Commit/测试/验收，不覆盖当前状态 |
| `docs/ACCEPTANCE` | 9 | 验收治理、专项协议与当前回执混合目录；只有 README 指定的 canonical 文件承担当前权威 |
| 其他 `docs/` | 66 | 当前权威、稳定说明、未来 Backlog、历史实施/研究混合 |
| 知识库与采集内容 | 118 | 主人知识/素材，不承担工程进度；本次只读检查，不改正文 |
| 根目录、模板、依赖/约束文本 | 15 | 入口、协作规则或机器依赖，不承担阶段进度 |

历史测试报告、结果回执、失败证据、哈希文件和 120 个 PEMIS opportunity 记录均保留，不做批量删除。

## 3. 发现的当前进度偏差

### 已经进入 `master`、但权威状态尚未同步的部分

- `WorkStore` 已增加 `list_work()`、`list_events()`、`list_pending()`。
- `CaptureWorkBridge.create_from_capture()` 已改用正式 `WorkStore.create_work()`。
- `WorkControlService` 已按 `StateDatabase → WorkStore → WorkProjector` 接线。
- 已新增 `test_work_store.py`、`test_capture_work_bridge.py`、`test_work_control_service.py`、`test_work_control_api.py` 四个合同测试文件。

这些事实只证明代码和测试文件已经存在；截至审计开始，仓库记录仍显示测试未在本机执行。

### 仍然阻塞正式能力的部分

- `create_control_app()` 没有注册 `src/control/work_routes.py` 的 `/api/work/*`。
- `LocalControlService` 没有正式共享 `WorkControlService` / `WorkStore`。
- Python 与 TypeScript 的 ID、状态、事件和 PendingAction 字段不一致。
- 后端返回 `items/events`，Desktop 页面期待 `work/events/pending_actions`，响应形状不一致。
- Outcome 和 NextAction 没有完整读取/API/Desktop 投影。
- `tests/test_work_control_api.py` 当前只验证 Control service，不是正式 FastAPI 路由测试。
- 缺少 `tests/test_work_projector.py` 和 `work-fact-smoke.mjs`。
- focused/full/release、发布版 UI 遍历和主人验收均未完成。

因此准确状态是：`SB-0 IN PROGRESS / PARTIALLY IMPLEMENTED / NOT VALIDATED`，Phase 1 仍未完成。

## 4. 审计初始发现与本次处理

- P1（已修复）：`PROJECT_STATUS.md` 和 `CODE_MAP.md` 曾把已经实现的 store/bridge/read/control 子项继续写成未开始。
- P1（已修复）：8 月 24 日产品代码变化没有进入 `CHANGE_ACCEPTANCE_LOG.md`。
- P1（已修复）：Desktop 与 Python 合同差异没有在当前进度中写清楚。
- P2（已修复）：`CHANGELOG.md` 曾停在 7 月 26 日，没有记录 SB-0 部分进展。
- P2（已修复）：模块实施文档、顶层旧报告、M5 研究文档和 PEMIS `NORMAL/current` 快照容易被当成当前状态；现已增加历史或生成数据标识。
- P2（已修复）：`DOCUMENTATION_MAINTENANCE.md` 与 `AI_COLLABORATION_RULES.md` 曾引用已删除的旧权威文件。

全量搜索仍会在历史实施记录、历史测试报告和本执行计划中命中旧路径；这些文件已经明确标为历史证据，不参与当前治理路由，因此不构成当前冲突。

## 5. 验证状态

```text
acceptance sync: PASS
local execution handoff: PASS
git diff check: PASS
current-tree conventional Markdown inline-link scan: PASS (407 files, 6 links, 0 broken links)
stale current-authority reference scan: PASS
pytest: NOT RUN (baseline python3 environment did not contain pytest)
independent Luna review: PASS AFTER CHANGES (0 Critical, 0 blockers; 3 Important and 2 Minor findings addressed before commit)
```

链接扫描只覆盖常规 Markdown inline 本地链接，不覆盖 863 个 Obsidian `[[wikilink]]`。Wikilink 依赖 Vault 根目录、别名和 Obsidian 解析规则，不能用本次仓库相对路径扫描冒充完整验证。

本次没有产品代码变化，focused/full/release 和 UI 真机验收不在范围内；未执行项目不得写成 PASS。
