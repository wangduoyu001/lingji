# Owner Memory Detail Drilldown — Focused Implementation Report

## 结论

`OWNER_MEMORY_DETAIL_DRILLDOWN_IMPLEMENTATION` 已在 focused/product implementation 边界内完成。
最终产品/测试 HEAD 为
`c7388c08b495b1fbf1598358d76fe4176552f9ab`，分支为
`codex/owner-memory-detail-drilldown`。本报告只证明代码、合成 fixture、rendered 自动化与治理
检查通过；不代表 live、package/install、Mac、真实数据、主人观察、release 或 Phase 1 通过。

## Task 1–3 身份与独立复审

| 任务 | 最终产品/测试提交链 | 最终复审结论 |
|---|---|---|
| Task 1 | `b46229eb` → `b7f4829f` → `b7b70468` | Repair 2 scoped re-review：`ADDRESSED`，0 open findings，0 new Critical/Important breakages |
| Task 2 | `38f02686` → `734e1eb9` → `6102fb80` → `d974360c` → `ed5d5fa3` | Repair 2：`Spec Compliance: PASS / APPROVED / Critical 0 / Important 0 / Minor 0` |
| Task 3 | `bb2ff3e2` → `b865f087` → `22545e92` → `c7388c08` | Repair 3：`Spec Compliance: PASS / APPROVED / Critical 0 / Important 0 / Minor 0` |

复审依据保存在 `.superpowers/sdd/2026-08-31-owner-memory-detail-drilldown/` 的 Task 1 Repair 2、
Task 2 Repair 2、Task 3 Repair 3 report/review 文件中。

## 产品结果

- 普通 UI 仍只有 `首页 / 记忆内容 / 需要我 / 记忆来源`，普通列表保持 `state=current` current-only。
- 点击单卡后才读取该 ID 的 `/cards/{id}`、bounded `/memories/{id}`、`/vector`、`/source` 和 evidence；
  默认详情显示 canonical 正文、当前结论、按时间排序的发展、来源与原文、`原始记录 / 结构记录 /
  语义向量 / 长期记忆` 四层状态及主人处理语义。
- 唯一新增 route 为认证的
  `GET /api/memory/inspector/memories/{memory_id}/evidence?limit=20&offset=0`；分页默认/上限为
  `20/50`，稳定 UTC 排序，`excerpt<=240`、`content<=4000`、单页 content `<=24000`，并返回
  `truncated` 与真实 pagination/cursor。canonical 继续使用 bounded `chunk_limit`/`max_chars`/`cursor`。
- 技术/备用信息折叠；history 按需读取并保留替代原因、避免 current/latest 语义；修正、过时、移出、
  拒绝仅在底部折叠 `备用操作`，没有删除按钮、新菜单、新数据库、新状态源或新端口。
- conversation-only 使用确切文案“这是原始会话，尚未形成长期记忆”，并复用既有会话消息分页。
  来源权限、撤销/过期/受限过滤、safe reference、选中代际竞态与 evidence load-more 均由 focused
  fixture 覆盖。

## Task 4 最终验证

| 命令 | 结果 |
|---|---|
| `python3 -m pytest -q tests/test_owner_memory_detail_contract.py tests/test_owner_memory_card_projector.py tests/test_owner_memory_card_api.py tests/test_memory_inspector_api.py tests/test_memory_inspector_facade.py tests/test_source_service.py tests/test_owner_memory_corrections.py tests/test_project_memory_api.py --tb=short` | **88 passed, 1 warning**；仅既有 Starlette/httpx 弃用告警 |
| `cd desktop/lingji-control && npm run test:e2e:memory` | **PASS**，`e2e_owner_memory_flow: PASS` |
| `cd desktop/lingji-control && npm run test:owner-ui-menu-fast-track` | **PASS** |
| `cd desktop/lingji-control && npm run test:smoke` | **PASS**，23 scripts；该套件末尾再次运行 broad `e2e_owner_memory_flow`，同样 PASS |
| `cd desktop/lingji-control && npm run build` | **PASS**，97 modules；保留既有 Vite dynamic-import warnings |
| `python3 -m compileall -q src tests` | **PASS** |
| `git diff --check` | **PASS** |
| `python3 scripts/check_acceptance_sync.py` | **PASS**，无 product-impacting changes |
| `python3 scripts/check_local_execution_handoff.py` | **PASS** |

测试后复核：`8766`/`8767` 无监听；未发现 owner smoke、broad E2E、Vite、LingJi service 或 sidecar
残留进程。

## 边界与未测试项

本轮未启动 live `8766/8767`，未 package/install 或生成 Artifact，未访问 Production/Vault、真实聊天、
真实数据库、Qdrant 或主人数据，未执行 Mac/Computer Use/主人观察。因此 live、package/install、Mac、
owner acceptance 均为 `NOT_TESTED`；不写 `COMPLETED owner`，也不宣称 release 或 Phase 1 PASS。

旧 `OWNER_UI_SOURCE_FILTER_REPAIR_4CE1E00A`（product `4ce1e00acb17bc5e4e4c183f58d30551ef76b101`）
继续保持历史 `COMPLETED / FAIL`，其失败 evidence、backup、fixture、DB、日志与 Acceptance 根不重开、
不复用。

## 下一步

根代理需在最终树运行一次 full/release；只有新产品 SHA 通过后，才可另建全新的 Mac acceptance task。
该任务必须使用同 SHA 全包 arm64 构建/安装和新隔离根，由 Computer Use 全页遍历，至少打开五种不同类型
记忆并展开多个来源原文；主人确认前不得写完成。

## 本次文档变更

仅同步既有权威 `docs/PROJECT_STATUS.md`、`docs/MODULES/CODE_MAP.md`、
`docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`、`docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`、
`docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md`，并新增本报告；未修改功能代码。
