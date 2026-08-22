# PROJECT_STATUS.md — LingJi 当前状态

> Updated: 2026-08-22
> Formal/default branch: `master`
> Latest product-code baseline before this documentation cleanup: `3d7225f58fb5b5a9b035cfd72f92cb2267b48559`
> Last owner acceptance closeout: `e594e3f05e8726cbae7b0a590e6f515fb2cc67c5`
> Last rejected product candidate: `bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9`
> Current development stage: `WORK-FACT CONTRACT REPAIR / UI EXPANSION BLOCKED`
> Architecture: `docs/ARCHITECTURE.md`
> Code entry points: `docs/MODULES/CODE_MAP.md`
> Acceptance authority: `docs/ACCEPTANCE/README.md`

## 1. 当前结论

最后一次主人真实 M5 验收仍然是：

```text
FAIL / DO NOT MERGE
```

失败不是安装、签名、Sidecar、隔离或发布链问题。真正阻塞仍是：**主人无法从产品中清楚看见灵机正在接管什么、做过什么、结果是什么、下一步由谁执行。**

最后一次验收暴露的关键问题：

- 首页能暗示存在待确认事项，但“需要我”没有真实 `PendingAction`；
- 首页能暗示系统完成了工作，但“工作”没有真实履历；
- `Cmd+K` 的“记住”真实提交失败，没有形成 Capture → Work → Memory 闭环；
- 记忆缺少主人可读正文/摘要和清楚来源证据；
- 主动发现更像静态说明，而不是“发现 → 授权 → 接管 → 执行 → 结果”的真实状态；
- Window Recovery 的菜单 / 快捷键 / Dock Reopen 三路径仍缺最终主人肉眼验收。

自该验收之后，`master` 已开始补 `src/work/` 事实模型和 Desktop 投影，但截至 2026-08-22 **仍未形成可运行的端到端事实链，因此不能把当前 UI 接线视为已完成能力。**

## 2. 2026-08-22 代码审计：当前事实链实际进度

### 2.1 已经有的基础

当前已经出现以下真实代码骨架：

```text
src/work/models.py
- WorkItem
- ExecutionEvent
- Outcome
- NextAction
- PendingAction

src/work/store.py
- work_items
- execution_events
- work_outcomes
- pending_actions

src/work/capture_bridge.py
- Capture -> WorkItem
- Extraction completion -> Outcome / ExecutionEvent

src/work/projector.py
- current_work
- pending_actions
- timeline

src/control/work_routes.py
src/control/work_service.py

desktop/lingji-control/src/contracts/workFact.ts
desktop/lingji-control/src/components/CurrentWorkPanel.tsx
desktop/lingji-control/src/pages/ActivityPage.tsx
desktop/lingji-control/src/pages/AttentionPage.tsx
```

方向是正确的：UI 开始从“聚合猜状态”转向“投影真实工作事实”。

### 2.2 当前 P0 阻塞缺陷

这些问题必须在继续扩 UI 前修完。

#### A. Store 写接口不一致

`CaptureWorkBridge.create_from_capture()` 调用 `store.save_work()`，但当前 `WorkStore` 实际提供的是 `create_work()`。

结果：真实 Capture 一旦走入该 bridge，会在创建 WorkItem 时失败。

#### B. Projector 依赖的读取方法不存在

`WorkProjector` 调用：

```text
list_work()
list_pending()
list_events()
```

当前 `WorkStore` 没有这些读取方法。

结果：即便数据库已有记录，Desktop read model 也无法正常读取。

#### C. Work API 没接进正式 8766 应用

当前正式 `create_control_app()` 结尾注册了 Obsidian / Capture 路由，但没有注册 `work_routes`。

同时 `LocalControlService` 当前没有 `current_work()` / `pending_actions()` / `work_timeline()` 正式方法。

结果：Desktop 最新代码调用 `/api/work/*` 时，正式发布链上没有完整可用接口。

#### D. Python 与 TypeScript 合同不一致

当前典型差异包括：

```text
Python WorkItem:      work_id
Desktop WorkItem:     id

Python ExecutionEvent: event_id / event_type / detail(dict)
Desktop Event:         id / event / detail(string)

Python NextAction:     description
Desktop NextAction:    summary

Python PendingAction:  description / resolved
Desktop PendingAction: id / summary / reason

Python Work status:    pending / accepted ...
Desktop status:        queued / running / completed / failed
```

结果：就算接口注册成功，UI 也无法可靠消费当前 Python 对象。

#### E. 缺少针对新事实链的专门测试

现有测试覆盖 Capture、Control API、Memory、Desktop 等大量旧能力，但没有独立覆盖：

```text
WorkStore
-> WorkProjector
-> LocalControlService
-> /api/work/*
-> Desktop workFact contract
```

这也是上述合同错位能够进入 `master` 的直接工程原因。

## 3. 唯一主人事实链

后续所有产品 UI 只允许投影这一条链：

```text
SourceObject
    ↓
Discovery / Intent
    ↓
WorkItem
    ↓
ExecutionEvent * N
    ↓
Outcome
    ↓
NextAction
    ↓
PendingAction?      只有真正需要主人决定才存在
    ↓
MemoryRecord?       可读内容 + 来源 + 证据
```

硬规则保持不变：

1. 没有真实 `WorkItem`，UI 不得宣称“灵机正在做 / 已经做了”；
2. 没有真实 `PendingAction`，UI 不得宣称“需要主人确认”；
3. 不允许用 memory count、generic event、queue length 推断工作语义；
4. Capture 成功后必须有稳定关联的 `capture_id + work_id`；
5. Work 必须能追到事件、结果、下一 actor；
6. Memory 必须能追到来源和证据；
7. API 不可用时显示 unavailable/error，不得伪装成 `0` 或“无事项”；
8. 所有页面对同一个 WorkItem 必须使用同一个 `work_id`，不得各自制造本地状态。

## 4. UI 开发前置里程碑：WF-0 事实合同修复

**在 WF-0 通过前，暂停 Home / Work / Attention 的功能扩张和视觉重构。**

### WF-0.1 冻结外部 API DTO

内部 dataclass 可以保留实现细节，但 8766 对 Desktop 输出的 DTO 必须唯一、稳定、带版本意识。

最小合同：

```text
WorkItem
- work_id
- title
- status: pending | accepted | running | completed | failed | skipped
- source_id?
- owner_approved
- created_at
- updated_at?

ExecutionEvent
- event_id
- work_id
- event_type
- detail
- created_at

Outcome
- work_id
- status: success | failure | skipped
- summary
- evidence
- completed_at?

NextAction
- work_id
- actor: system | owner | external | none
- description

PendingAction
- action_id
- work_id
- description
- reason?
- resolved
- created_at
- resolved_at?
```

Desktop `workFact.ts` 必须由此合同一一对应，不再另起命名体系。

### WF-0.2 修通持久化与 read model

必须完成：

- 统一 `create_work/save_work`；
- 增加 `get_work/list_work/list_events/list_pending/get_outcome/get_next_action`；
- WorkItem 状态变化必须持久化；
- PendingAction 必须有稳定 `action_id`；
- 所有读取按时间稳定排序；
- 不可通过 UI 临时拼接 Outcome / NextAction。

### WF-0.3 接通正式 Control API

正式 8766 至少提供：

```text
GET /api/work/current
GET /api/work/recent?limit=N
GET /api/work/{work_id}
GET /api/work/timeline/{work_id}
GET /api/work/pending-actions
```

如需要主人完成确认，再增加受控 mutation endpoint，不允许 Desktop 直接改 SQLite。

### WF-0.4 Capture 串入事实链

真实流程：

```text
Capture accepted
-> create WorkItem
-> append capture.accepted
-> extraction queued/running events
-> extraction completed/failed
-> Outcome
-> optional MemoryRecord
-> NextAction
```

任何一步失败都必须落真实失败事件，而不是只 toast 一句错误后消失。

### WF-0.5 自动化门禁

至少新增：

```text
tests/test_work_store.py
tests/test_work_projector.py
tests/test_work_control_api.py
tests/test_capture_work_bridge.py
```

并增加 Desktop 合同/场景 smoke：

```text
desktop/lingji-control/scripts/work-fact-smoke.mjs
```

WF-0 Definition of Done：

- 一个真实 Capture 能产生 WorkItem；
- API 能读到同一 `work_id`；
- timeline 至少包含 accepted → processing → completed/failed；
- Desktop 合同与返回 JSON 完全一致；
- API unavailable 不会显示成空列表；
- focused tests 全绿后才进入 UI-1。

## 5. UI-1：首页 Home，先回答三个问题

首页第一屏只负责让主人 5 秒内知道：

```text
1. 灵机现在在做什么？
2. 最近真正完成了什么？
3. 现在有没有事情必须由我处理？
```

### 5.1 当前工作区

数据只来自 `/api/work/current`。

显示：

- Work title；
- 当前 status；
- 最近一个 ExecutionEvent；
- 已运行/等待时间；
- NextAction + actor；
- 进入 Work detail 的入口。

没有当前工作时明确显示：`当前没有正在执行的工作`，同时说明后台是否仍会继续发现/处理，而不是用空白卡片冒充正常。

### 5.2 最近完成

显示最近 3~5 个真实 completed/failed WorkItem：

- 标题；
- 结果摘要；
- 完成时间；
- 来源；
- 点击进入完整履历。

禁止从 generic events 反推“最近完成”。

### 5.3 需要主人

数量和内容只来自 `PendingAction`。

首页只做摘要，不复制 Attention 业务逻辑。

### UI-1 DoD

- Home 与 Attention 的待办数量严格一致；
- Home 与 Work 的当前工作严格指向同一 `work_id`；
- 断网/Sidecar 错误显示错误态，不显示 `0`；
- 空、加载、过期、错误四种状态均有明确视觉语义。

## 6. UI-2：Work 作为唯一工作履历

Work 页面不是“日志页”，而是灵机实际承担过的工作账本。

### 6.1 列表

首版只保留必要筛选：

- Active；
- Completed；
- Failed；
- All。

每行显示：标题、状态、来源、更新时间、Outcome 摘要、Next actor。

### 6.2 Detail

点击 WorkItem 后显示统一详情：

1. 工作标题和来源；
2. 为什么被接管；
3. 时间线 ExecutionEvent；
4. Outcome；
5. Evidence；
6. NextAction；
7. 若存在 PendingAction，则显示主人要做什么；
8. 若形成 MemoryRecord，则可跳到对应记忆。

### 6.3 Timeline

时间线只显示真实事件，不把前端生命周期状态写成执行事实。

事件默认显示人类可读标题；原始 JSON/detail 放到展开层，避免首页式技术噪音重新污染主人界面。

### UI-2 DoD

主人可以从任意完成记录回答：

```text
它为什么开始？
它做了哪几步？
最终结果是什么？
证据在哪里？
下一步谁负责？
```

## 7. UI-3：Attention 只呈现真实主人决策

Attention 的唯一数据源是未解决 `PendingAction`。

每项必须显示：

- 要主人决定什么；
- 为什么需要主人；
- 关联 WorkItem；
- 如果不处理会发生什么；
- backend 明确允许的 action。

不得继续出现“系统觉得你可能需要看”的软提示混入 PendingAction。

如只是通知，放 Activity/Work；如系统能自行处理，就继续执行，不得甩给主人。

### UI-3 DoD

- `pending_actions = 0` 时全产品都不得出现“待确认 1”；
- 解决一个 action 后 Home / Attention / Work 同步刷新；
- action mutation 有审计事件；
- UI 不自行决定 approve/reject 的业务后果。

## 8. UI-4：Capture / Cmd+K 变成可追踪入口

Capture 的产品反馈必须从“提交成功 toast”升级为“提交后可追踪”。

成功提交后立即显示：

```text
已接收
work_id: ...
当前阶段: accepted / queued / processing / completed / failed
```

主人可直接跳入 Work detail。

失败时：

- 保留输入；
- 显示真实失败原因；
- 若 backend 已创建 WorkItem，则显示失败履历；
- 未创建 WorkItem 时不得伪造 work_id。

### UI-4 DoD

真实执行一次“记住这段内容”：

```text
Cmd+K
-> Capture accepted
-> Work visible
-> Extraction events visible
-> Outcome visible
-> Memory visible or explicit Failure
```

这是下一次 M5 的必测主路径。

## 9. UI-5：Memory 变成可检查的第二大脑

Memory 首屏优先展示主人能读懂的内容，不再只显示泛化标题。

每条至少可查看：

- 可读摘要/正文；
- 来源 SourceObject；
- 创建/更新时间；
- 来源片段或证据；
- 若由灵机工作产生，显示 originating `work_id`；
- 向量/索引技术信息放到二级详情或 Diagnostics。

### UI-5 DoD

主人随机打开一条记忆，可以回答：

```text
灵机记住了什么？
从哪里来的？
为什么可信？
它和哪次工作有关？
```

## 10. UI-6：主动发现 / 授权 / 接管状态

在核心工作闭环稳定后再做主动发现，不提前造“机会发现”大屏。

同一对象必须能区分：

```text
discovered
needs_authorization
authorized
accepted
running
completed
failed
skipped
```

主人看到的不是“发现了 Codex”一句话，而是：

- 发现对象；
- 发现原因；
- 当前是否有权限；
- 是否已变成 WorkItem；
- 当前执行阶段；
- Outcome；
- 下一步。

如果只发现、没有授权，UI 必须明确停在 `needs_authorization`，不能写成“已接管”。

## 11. UI-7：跨页面连续性

完成前述页面后统一以下行为：

- 所有 Work 链接使用同一 `work_id`；
- Home / Attention / Capture / Memory 点击后进入同一 Work detail；
- 全局 Cmd+K 只负责入口与导航，不保存另一套临时状态；
- 共用 loading / empty / stale / error 组件；
- 共用 status label 与 actor label；
- 统一中文主人语义，技术字段放二级层；
- 页面刷新后仍能从后端恢复同一事实，不依赖前端内存。

## 12. UI-8：验收与发布门禁

顺序固定：

```text
A. backend contract tests
B. control API integration tests
C. desktop work-fact smoke
D. focused validation: work/capture/control/desktop
E. full validation
F. macOS + Windows release CI
G. 安装真实 Artifact
H. 主人 M5 肉眼验收
```

下一次 M5 至少必须真实走通：

1. 打开首页，看见真实当前工作或诚实空状态；
2. Cmd+K 提交一条“记住”内容；
3. 立即进入对应 WorkItem；
4. 看见执行事件推进；
5. 看见 Outcome；
6. 打开对应 Memory，看到可读内容和来源；
7. 制造一个真实 PendingAction，Home 与 Attention 一致；
8. 主人解决该 action，跨页面状态同步；
9. 验证一个失败 WorkItem，不能消失或伪装成功；
10. 完成 Window Recovery 菜单 / 快捷键 / Dock Reopen 三路径肉眼验收。

任何一步依赖 fixture 假装真实生产链，M5 不通过。

## 13. 开发顺序与并行边界

建议按以下提交序列推进，避免再次出现“UI 已接线但 API 根本不存在”的情况：

```text
Commit A  canonical work DTO + model/status normalization
Commit B  WorkStore read/write completion + migrations
Commit C  WorkProjector + LocalControlService + /api/work routes
Commit D  Capture -> Work -> Outcome integration
Commit E  backend tests + API contract tests
Commit F  Desktop workFact contract + shared resource states
Commit G  Home
Commit H  Work
Commit I  Attention
Commit J  Capture / Cmd+K traceability
Commit K  Memory provenance
Commit L  discovery/authorization projection
Commit M  cross-page smoke + full validation
Commit N  release candidate + new M5
```

可并行：

- backend store 与 DTO tests；
- UI loading/error/empty shared components；
- Memory inspector 现有 API 的只读梳理。

不可并行抢跑：

- DTO 未冻结前写页面字段；
- `/api/work/*` 未通过 contract tests 前扩 Home/Work/Attention；
- Capture 未形成真实 WorkItem 前做“已接管”视觉；
- 自动门禁未绿前创建新 M5 Artifact。

## 14. 已确认通过，不要重复返工

以下不是下一轮主要矛盾，只做必要回归：

- 精确产品/Artifact 身份；
- Apple Silicon arm64；
- strict codesign；
- whole-bundle replace；
- Acceptance / Production 物理隔离；
- AuthStatus / Secret 边界；
- `secret_export_count=0`；
- 两轮 exact-instance Runtime start/stop；
- 第一轮保存 PID 后验证 state/PID/8766 全释放；
- `production_pollution_count=0`；
- 记忆分页 `has_more=false` 正确停止；
- 高级技术信息下沉。

## 15. 权威失败证据

```text
Task: PR88-M5-OWNER-WORKBENCH-V4-BD1E7A17
Product: bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9
macOS Artifact: 9258682849 / lingji-macos-arm64
Report branch: acceptance/pr88-m5-owner-workbench-v4-bd1e7a17
Report commit: 5793e4ae22e17d1f4db2c57ecc66bf18ec65af2e
Cleanup receipt: 3011d796ff1bb5bff7d5e37c24e0c6236ee51d34
PR #88 comment: 5306178636
```

最终结构化结果见 `docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md`。

## 16. 技术边界保持不变

- `src/` 为长期平台主线；
- `desktop/lingji-control/` 为唯一正式 Desktop UI；
- `second_brain/` 只做兼容/迁移；
- Desktop 只通过认证的 `127.0.0.1:8766` Local Control API；
- Obsidian Vault + Git 为永久记忆正文权威；
- SQLite/Qdrant 为可重建索引与运行状态；
- Acceptance / Production 物理隔离；
- Secret 只留在系统安全凭据边界；
- Runtime stop 只处理精确实例；
- 不创建第二事实源来美化状态；
- AI 不能自动批准永久记忆；
- 不自动执行破坏性 Qdrant rebuild。

## 17. 历史失败 Artifact

以下均永久 `DO NOT RETRY`：

```text
9258682849 / bd1e7a17
9250384637 / 1d99d10c
9249367672 / f3cba413
9224368022 / 2c96b3ec
9102748834 / 171091fe
```

下一候选必须产生新的产品 Commit 和新 Artifact，并重新完成真实事实链自动门禁与主人 M5。