# Owner UI / Menu Fast-Track Task 2 — 本机交接报告

## 结论

本报告对应唯一 ACTIVE 任务 `OWNER_UI_MENU_FAST_TRACK_TASK_2_6BAF4EE6`，执行模式
`MACOS_OWNER_UI_EXPERIENCE_ONLY`。候选只命名为 `OWNER_UI_EXPERIENCE_CANDIDATE`，固定产品
HEAD `6baf4ee6d15256e44164bcbe3f7ce227af0b5d07`；本任务是 `NOT_A_RELEASE_GATE`。旧质量事实
仍为 `MEASURED_FAIL / NOT_RELEASE_READY`，没有 release、Phase 1、merge 或主人体验 PASS 结论。

技术准备已完成，当前真实候选与 sidecar 保持打开，已交给根代理用 Computer Use 做主人体验
观察。真实主人初验结论为 `OWNER_UI_REPAIR_REQUIRED`：候选仍是 `NOT_A_RELEASE_GATE`，不能
宣布 release、Phase 1、merge 或主人 PASS。本报告记录该失败事实，不替主人补充通过结论。

## 环境、隔离与安装

- 主机：macOS Darwin 25.5.0，arm64；候选分支 `codex/owner-real-history-memory-cards`。
- Acceptance 根（`/tmp` 在本机 canonical path 为 `/private/tmp`）：
  `/tmp/LingJiAcceptance/owner-ui-menu-fast-track-task-2-6baf4ee6`。
- active packaged DataRoot：
  `/tmp/LingJiAcceptance/owner-ui-menu-fast-track-task-2-6baf4ee6/data-root/acceptance`。
  packaged sidecar 的 canonical storage/vault 是该根下的 `storage/` 与 `vault/`；不是非 packaged
  workspace resolver 的 `storage/state`、`storage/index` 嵌套路径。
- source fixture home：
  `/tmp/LingJiAcceptance/owner-ui-menu-fast-track-task-2-6baf4ee6/source-fixture-home`；授权的
  exact Codex root 是其 `.codex/sessions`，没有读取真实 `$HOME/.codex`。
- 安装备份：`installed-app-backup/灵机.app` 为安装前整包备份；安装前在同一备份根保留了
  `灵机-live-preinstall.app`，没有卸载、删除主人数据或覆盖旧备份。
- 整包安装：先将 `/Applications/灵机.app` 移入本轮备份根，再用 `ditto` whole-bundle 替换，
  未执行删除式卸载。回滚只允许从上述本轮备份整包恢复。
- Production 根 `/tmp/.../data-root/production` 不存在；Production/Vault pollution count = 0。
  本机未访问真实聊天、真实 Vault、真实数据库、真实用户配置、凭证或模型。

## 完整执行命令与结果

### 权威激活与自动验证

权威文档先提交为 `f31174fabec4a7e8c554a485fab954e3dc116f74`：

```text
git diff --check
python3 scripts/check_acceptance_sync.py
python3 scripts/check_local_execution_handoff.py
git commit -m "docs: activate owner UI macOS acceptance task"
```

自动验证命令均通过：

```text
cd desktop/lingji-control
npm run test:macos-release                 # PASS
npm run test:owner-ui-menu-fast-track      # PASS
npm run test:e2e:memory                    # PASS
npm run test:smoke                         # PASS (23 scripts)
npm run build                              # PASS (96 modules; existing dynamic-import warnings)
cd ../..
python3 -m pytest -q tests/test_owner_memory_corrections.py tests/test_owner_memory_card_projector.py tests/test_owner_memory_card_api.py tests/test_memory_review_service.py tests/test_memory_inspector_api.py tests/test_memory_inspector_facade.py tests/test_project_memory_api.py tests/test_task3_round2_direct.py tests/test_task3_round3_integration.py tests/test_source_read_model.py tests/test_source_service.py --tb=short  # 87 passed, 1 warning
python3 -m compileall -q src tests                # PASS
git diff --check                                  # PASS
python3 scripts/check_acceptance_sync.py          # PASS
python3 scripts/check_local_execution_handoff.py  # PASS
```

### arm64 构建、签名与安装

初次构建发现 shell `PATH` 没有现有 Rust toolchain 的 cargo；没有改代码，显式使用已有
`/Users/wuhanwangduoyu/.cargo/bin` 后构建成功：

```text
export PATH="/Users/wuhanwangduoyu/.cargo/bin:$PATH"
cd desktop/lingji-control
LINGJI_BUILD_CHANNEL=local-acceptance LINGJI_BUILD_TARGET=aarch64-apple-darwin npx tauri build --config src-tauri/tauri.sidecar.conf.json --bundles app --target aarch64-apple-darwin
npm run build:sidecar:macos
LINGJI_BUILD_CHANNEL=local-acceptance LINGJI_BUILD_TARGET=aarch64-apple-darwin npx tauri bundle --config src-tauri/tauri.sidecar.conf.json --bundles dmg --target aarch64-apple-darwin
LINGJI_BUILD_CHANNEL=local-acceptance LINGJI_BUILD_TARGET=aarch64-apple-darwin npx tauri build --config src-tauri/tauri.sidecar.conf.json --bundles app --target aarch64-apple-darwin
```

DMG 成功生成；其 SHA256 为 `c5cc7c73fc9753ae4cb580494101ddfeaeb14baeede62beeed87f794f809aff6`。
最终 installed whole bundle `/Applications/灵机.app` 的关键 SHA256：

| 文件 | SHA256 |
| --- | --- |
| `Contents/MacOS/lingji-control-center` | `97be4f769b87b3c359b3b590eac707715f0c98796a587be0886149b9f2bb5c49` |
| `Contents/MacOS/lingji-core` | `8d4a0db1a5b6d6ef0e45711af0d3ff2f69cdd58beb9eb6b149526d0772cdcdf9` |
| `Contents/Resources/lingji-core-manifest.json` | `be3ffc1bb4c82cf455fbc513e4a7763f031b331d6f1a3cb3f7f86927b695d5fe` |
| sorted installed-bundle file inventory | `2c8a34dcf3250f46e23e538f03762053624d9887be722b3ba517b886a9631939` |

```text
file /Applications/灵机.app/Contents/MacOS/lingji-control-center  # Mach-O 64-bit arm64
file /Applications/灵机.app/Contents/MacOS/lingji-core            # Mach-O 64-bit arm64
otool -hv /Applications/灵机.app/Contents/MacOS/lingji-core       # ARM64
codesign --verify --deep --strict --verbose=2 /Applications/灵机.app  # PASS
```

Installed app is ad-hoc signed with runtime flags; strict verification passed. Pre-install backup
sidecar hash was `da60670373f62d4e2a3f9a0d1838b3741154f23a8a0173200a348e048944d968` and remains in
both backup copies.

### 隔离 fixture、真实 API 与进程

Fixture seed command（脚本只在 Acceptance 根内，未加入产品树）：

```text
PYTHONPATH=. python3 /tmp/LingJiAcceptance/owner-ui-menu-fast-track-task-2-6baf4ee6/seed_acceptance.py
```

Seed 结果：6 个可读 Vault memory documents（`current`、`superseded`、`stale`、`conflict`、
`permanent`、`candidate`），1 个 private Codex source，1 个 seeded conversation、6 条 seeded
messages，并创建真实 `action-owner-review` pending action。raw fixture 为 2 个 rollout JSONL；
sidecar 启动后的真实扫描为 `total=2`、`completed=2`，raw snapshot 文件数为 2。向量未伪造，
当前 API 如实报告 configuration required / unavailable。

为保证进程不受 terminal process-group 回收，使用用户 GUI launchd 的隔离提交 job：

```text
launchctl submit -l com.lingji.acceptance.task2 -- /usr/bin/env LOCALAPPDATA="/tmp/LingJiAcceptance/owner-ui-menu-fast-track-task-2-6baf4ee6/desktop-config" HOME="/tmp/LingJiAcceptance/owner-ui-menu-fast-track-task-2-6baf4ee6/source-fixture-home" /Applications/灵机.app/Contents/MacOS/lingji-control-center
```

当前进程：Desktop PID `44824`，sidecar PID `44832`，sidecar 命令行明确为：

```text
/Applications/灵机.app/Contents/Resources/lingji-core.exe --data-root /tmp/LingJiAcceptance/owner-ui-menu-fast-track-task-2-6baf4ee6/data-root/acceptance --host 127.0.0.1 --port 8766
```

认证探测使用 acceptance token（token 未写入报告）：

```text
curl --fail-with-body -sS -H "X-LingJi-Token: <acceptance-token>" http://127.0.0.1:8766/api/runtime/ping
```

结果：HTTP `200`，`{"status":"ok"}`；`/api/health` 与 `/api/overview` 也为 HTTP `200`。
sidecar 运行态为 `running`，scheduler/worker heartbeat 健康；health 的 3 个 warning 仅为本机
无 ffmpeg/ffprobe/Ollama，不是本任务 blocker。

认证 API 证据（均保存于 Acceptance `evidence/`，不含 token）：

- cards：8 张（6 个 memory cards + 2 个未晋级 conversation cards），summary `cards=8`、
  `conversations=3`、`messages=12`、`permanent=1`、`owner_review=6`。
- memory cards：current、superseded、stale、conflict、permanent、candidate 均有 raw/structured
  可用状态；vector 为 unavailable；permanent 为 available 或 pending_owner_review；conflict
  card 的 trust conflict 为真实 `conflict`，candidate action 为 `confirm`，current action 为
  `none`。
- source：`codex_rollout` authorized source 与 structured source 均可见；source fixture exact
  root 在 `/tmp/.../source-fixture-home/.codex/sessions`。
- scans：2 个 completed scan，`last_error=null`；runtime running，worker `thread_alive=true`。
- work：至少 1 条真实 owner pending action，`action_id=action-owner-review`，`resolved=false`；
  同时存在 completed scan Work Fact 与 owner review Work Fact，均从当前 sidecar state DB 读取。

## 证据文件

关键证据保存在 `/tmp/LingJiAcceptance/owner-ui-menu-fast-track-task-2-6baf4ee6/evidence/`：

`runtime-ping.json`、`health.json`、`overview.json`、`cards-after-links.json`、
`cards-summary-after-links.json`、`automatic-sources.json`、`scans.json`、`pending.json`、
`history.json`、`automatic-summary.json`、`automatic-runtime.json`、`vector.json`、
`installed-bundle-files.sha256`、`installed-codesign-verify-now.log`、`installed-main-signing-now.log`、
`seed-summary.json`、`desktop.pid`、`sidecar.pid` 以及构建二进制备份。

## 当前交接边界

- 当前页面：根代理已完成首页/普通菜单/高级诊断/较窄窗口的初验；高级诊断折叠/打开及较窄
  窗口布局正常。Desktop 与 sidecar 仍保持打开，供后续修复重验。
- 主人观察结论：`OWNER_UI_REPAIR_REQUIRED`。本轮没有主人通过结论。
- 真实主人观察（与本机 API 证据并列记录）：
  1. 首页在运行正常且已有来源/卡片时仍显示“需要先完成设置”；pending/source 轮询在普通页面间出现“暂时无法确认/尚未获得”的矛盾。
  2. 记忆来源页持续显示“尚未获得来源信息”，但认证 `discovered`/`sources`/`scans`/`summary`/`runtime` API 均 HTTP 200 且有数据。
  3. 需要我页显示 0 项，但认证 `/api/work/pending-actions` 返回 1 项；首页先显示待办后又变为不可确认。
  4. 8 张记忆卡有主题、发展、来源和层状态，但全部 `conclusion=null`；普通卡与详情均显示“最新结论尚未获得”，详情不能回答当前结论/过时后的现状。
  5. 修正入口可打开并填写原因，但 Mac 随后因物理输入锁定，提交未完成；高级诊断折叠/打开及较窄窗口布局正常。
- 这些是候选的真实 UI/事实链缺口，不得把 fixture、轮询或 API HTTP 200 误写成体验通过。
- 不关闭 `/Applications/灵机.app`、Desktop PID `44824`、sidecar PID `44832` 或 8766；不清理
  Acceptance fixture、raw、Vault、DB、日志、备份和失败证据，直到根代理完成交接并收到主人明确
  PASS/FAIL；当前已收到 `OWNER_UI_REPAIR_REQUIRED`，仍按要求保持运行与保留证据。

## Task 2 Repair Round 1 追加记录（2026-08-30）

### 范围与实现

本轮严格限制在 Desktop 普通页面、既有 polling hook、owner-facing 纯函数及真实 rendered
tests：

- 首页以现有 Core `health.status` 优先于局部 `memory_runtime.state`，因此整体健康而向量配置
  不完整时仍显示整体可用，向量数字继续按现有卡片摘要事实展示。
- 既有 `usePollingResource` 在页面 active 且文档 hidden 时执行一次真实激活读取，随后继续暂停
  隐藏轮询；手动 pause 不触发这次 hidden 激活读取。Overview、Attention、MemorySources
  继续共用该 hook。
- 首页与“需要我”通过同一 `pendingActionsFrom` 读取事实；缺少列表、错误或过期均保持“暂时无法
  确认”，不会把未加载误报为 0。
- `ownerFacingConclusion` 是卡片与详情共用的纯函数：优先真实 `conclusion`，否则只使用已有的
  lifecycle/trust/development/evidence 字段生成“当前状态”或“当前可确认”，没有事实时显示
  “当前结论：尚未获得”；freshness 时间缺失时回退至 source 最新证据时间。
- 未修改 backend/API/data model/retrieval/vector/quality gate，未新增功能；未改变现有修正、确认、
  来源读取、关闭/Escape/focus 或四菜单动作接线。

### TDD RED / GREEN

- RED：先在真实 `owner-ui-menu-fast-track-smoke.mjs` 将 fixture 设为
  `health.status=healthy`、`memory_runtime.state=configuration_required`，并等待首页真实渲染的
  `灵机运行正常`；`npm run test:owner-ui-menu-fast-track` 首次失败为
  `locator.waitFor: Timeout 30000ms exceeded`，精确 `1 failed` assertion。该失败复现了 active
  页面第一次读取后把整体健康误判为设置缺失。
- GREEN：最小修复后，真实 rendered `npm run test:owner-ui-menu-fast-track` 为
  `owner-ui-menu-fast-track-smoke: PASS`；`npm run test:e2e:memory` 为
  `e2e_owner_memory_flow: PASS`。fixture 同时覆盖 hidden active-route 首次来源读取、pending=1
  首页/需要我一致性、pending outage unknown、current/superseded/stale/conflict null conclusion
  卡片与详情、source 时间回退和现有动作/焦点/技术字段脱敏。
- 中间一次详情断言失败仅为测试期望漏写共享函数产生的“当前状态：”标签，已改为直接按渲染
  contract 断言；另一次 outage 分支等待了不存在的 Panel 标题，已改为断言首屏 unknown 文案，
  均不是产品 blocker。最终 E2E 已重跑通过。

### 验证命令计数与结果

- 真实 rendered focused：`npm run test:owner-ui-menu-fast-track` 最终 PASS（最终修复后 1 次）；
  `npm run test:e2e:memory` 最终 PASS（最终修复后 1 次）。
- 来源/相关 Desktop smoke：`npm run test:memory-sources` PASS、
  `npm run test:memory-sources-repair` PASS、`npm run test:work-fact` PASS。
- 23-script：`npm run test:smoke` PASS（23 scripts，包含 owner rendered E2E）。
- build：`npm run build` PASS（TypeScript/Vite，97 modules；仅保留既有 dynamic-import warnings）。
- Python focused：
  `python3 -m pytest -q tests/test_owner_memory_corrections.py tests/test_owner_memory_card_projector.py tests/test_owner_memory_card_api.py tests/test_memory_review_service.py tests/test_memory_inspector_api.py tests/test_memory_inspector_facade.py tests/test_project_memory_api.py tests/test_task3_round2_direct.py tests/test_task3_round3_integration.py tests/test_source_read_model.py tests/test_source_service.py --tb=short`
  → `87 passed, 1 warning`。
- 其它门禁：`python3 -m compileall -q src tests` PASS、`git diff --check` PASS。另有一次先在
  worktree 根执行 npm 的错误目录命令，得到 3 个 ENOENT；未接触服务，随后在
  `desktop/lingji-control` 目录按上列命令全部重跑通过。

### 提交与未运行项目

- 产品/tests 提交：`0b0e2fcf4881deea9803c51280e6e3fd8d4f26a4`。
- 本追加报告及验收同步条目在产品提交后单独提交 docs/evidence；本轮不更新、不执行
  `LOCAL_EXECUTION_TASK.md` 中的候选 SHA。
- 未运行或触碰：`/Applications/灵机.app`、Desktop PID `44824`、sidecar PID `44832`、8766/8767、
  Acceptance root/fixture、Production/Vault、主人真实数据、真实 API、打包/安装、live owner
  observation；未宣称主人验收或 release 通过。独立审查及后续候选重建由根代理调度。

## Task 2 Repair Round 2 追加记录（2026-08-30）

### 审查问题与范围

本轮仅处理独立审查指定的两个 Important，不扩大至 Minor 或其它页面：

- I1：既有 hidden activation 分支只看合并后的 `effectivelyPaused`，无法区分 hidden pause 与
  manual pause；本轮增加可执行的 `shouldScheduleHiddenActivation` 行为契约，并使 manual pause
  取消/阻止激活 timer，resume 在 hidden 时按契约只允许一次读取，不恢复热轮询。
- I2：既有 `pendingActionsFrom` 只检查数组，`null`/缺少非空 `action_id` 的成员可能进入 UI 并
  生成无效 resolve URL；本轮让任一 malformed 成员返回 `null`，Overview/Attention 保持同一
  “暂时无法确认”文案。合法 action 的其它字段仍不新增约束，缺少 description 继续由既有 UI
  fallback 处理。

未修改 backend/API/data model/retrieval/vector/quality gate，未增加功能，未触碰 live app、PID、
8766/8767、Acceptance 或主人数据。

### TDD RED / GREEN

- I1 RED：先在 `automatic-memory-sources-repair-smoke.mjs` 写入 manual pause + hidden + 未完成
  activation 的行为断言；`npm run test:memory-sources-repair` 以
  `SyntaxError: ... does not provide an export named shouldScheduleHiddenActivation` 精确失败。
- I2 helper RED：先在 `work-fact-smoke.mjs` 写入 `[null]`、`[{}]`、空白 `action_id` 断言；
  `npm run test:work-fact` 精确 `1 failed`，实际返回 `[null]` 而非 `null`。
- I2 rendered RED：先将真实 owner fixture pending list 设为 `[null]`/`[{}]`，要求首页与“需要我”
  均显示 unknown；`npm run test:owner-ui-menu-fast-track` 精确 `1 failed`，首页等待
  `待办状态暂时无法确认，正在重试` 超时，复现 malformed action 被误当成有效待办。
- GREEN：增加严格成员校验与 hidden/manual pause 条件后，上述三项全部 PASS；真实 rendered fixture
  同时验证 malformed list 不渲染无效动作、不产生 resolve URL，并保持合法 pending、四菜单及
  Round 1 卡片/来源行为不回归。

### 命令计数与结果

- RED 命令：3 个（I1 repair smoke、I2 work-fact smoke、owner rendered smoke），均按预期失败。
- GREEN/回归命令：9 个——`npm run test:memory-sources-repair`、`npm run test:work-fact`、
  `npm run test:owner-ui-menu-fast-track`、`npm run test:e2e:memory`、
  `npm run test:memory-sources`、`npm exec -- tsx scripts/polling-data-smoke.mjs`、
  `npm run build`、`python3 -m compileall -q src tests`、`git diff --check`，全部 PASS；build
  为 TypeScript/Vite、97 modules，保留既有 dynamic-import warnings。
- 产品/tests 提交：`615585397f9bab3596f77e1eed39d2dc63d05f7e`。
- docs/evidence 提交将在本段追加及验收同步条目完成后单独生成；`python3 scripts/check_acceptance_sync.py`
  与 `python3 scripts/check_local_execution_handoff.py` 在 docs 提交后复跑。

### 未运行项目与交接

- 未运行 live App/Sidecar、未访问 8766/8767、Acceptance root、Production/Vault、主人真实数据或
  真实 API；未打包/安装、未更新或执行 `LOCAL_EXECUTION_TASK.md` 候选 SHA，未做主人观察。
- 两个 Minor 按根代理 ledger 延后 final review；独立审查、重建候选及后续 live 验收由根代理调度。
