# PROJECT_STATUS.md — LingJi 当前状态

> Updated: 2026-08-16
> Formal/default branch: `master`
> Current product PR: `#88`
> Last rejected product candidate: `bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9`
> Current local task: `IDLE / NO ACTIVE LOCAL TASK`
> Architecture: `docs/ARCHITECTURE.md`
> Code entry points: `docs/MODULES/CODE_MAP.md`
> Acceptance authority: `docs/ACCEPTANCE/README.md`

## 1. 当前结论

PR #88 的 Owner Workbench V4 已完成真实 macOS M5 复验：

```text
FAIL / DO NOT MERGE
current local task: IDLE
product PR: Draft
Artifact 9258682849: DO NOT RETRY
```

技术发布链不是本轮阻塞。精确产品/Artifact 身份、arm64、strict codesign、Acceptance 隔离、Secret 边界、两轮 Runtime 生命周期、分页终点、Production pollution=0、失败回滚与清理均通过。

真正阻塞是：**灵机没有形成主人可见、可追踪、可验证的“接管并完成工作”闭环。**

主人最终观察：

> 看不出灵机实际做了什么、接管了什么，与旧版没有明显差异。

## 2. 当前 P1 blocker：M5-V4-WORKBENCH-001

V4 的问题不是某个页面少一个字段，而是同一件真实工作没有贯穿所有主人界面。

### 2.1 首页和待办互相矛盾

首页说存在“待确认候选”，但“需要我”页面显示 `0` 个真实待办。说明首页仍能从聚合/推导状态制造动作语义，而没有绑定同一真实对象。

### 2.2 工作履历没有真实执行事实

首页声称系统刚做过事情，但“工作”页面为 `0` 记录。主人无法确认：

```text
发生了什么
灵机具体执行了什么
结果是什么
下一步是什么
下一执行者是谁
```

### 2.3 Capture 没有进入真实工作链

`Cmd+K` 提交“记住”时真实失败，没有生成可追踪 Capture / Work / Memory 对象。入口存在，但能力没有闭环。

### 2.4 记忆不是可检查的第二大脑

“记忆”只有泛化标题，缺少主人可读正文/摘要与可验证来源链。对象存在不等于记忆能力成立。

### 2.5 主动发现没有体现接管

能看到发现 Codex / WorkBuddy 等静态说明，但看不出：

```text
发现了什么
是否获授权
是否已经接管
当前做到了哪一步
结果是什么
下一步系统会自动做什么
```

### 2.6 Window Recovery 仍未完整验收

快捷键仅有自动观察；菜单与 Dock Reopen 未完成主人三路径肉眼确认，最终保持 `NOT_TESTED`。

## 3. 已确认通过，不要重复返工

以下不是下一轮主要矛盾：

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
- 记忆分页 `has_more=false` 时正确停止；
- 高级技术信息已下沉。

后续只做必要回归，不应再把主要开发时间消耗在这些已稳定项上。

## 4. 下一轮产品方向：真实接管闭环

下一轮不再做“Owner Home / Work Feed / Workbench V5”式页面重命名，也不先画新首页。

先建立唯一主人事实链：

```text
SourceObject      真实资料 / 工具 / 主人输入
    ↓
Discovery/Intent  为什么系统注意到它
    ↓
WorkItem          灵机决定接管的具体工作
    ↓
ExecutionEvent    每一步真实执行事件
    ↓
Outcome           成功 / 失败 / 跳过及可读结果
    ↓
NextAction        下一步 + actor(system/owner/external)
    ↓
PendingAction?    只有真的需要主人决定才存在
    ↓
MemoryRecord?     可读正文/摘要 + 来源/证据
```

**首页、需要我、工作、记忆、Capture 只能投影这条同一事实链。**

硬规则：

1. 没有真实 `WorkItem`，首页不得宣称“灵机做了”；
2. 没有真实 `PendingAction`，任何地方不得宣称“需要你确认”；
3. “工作”必须能看到每个真实 WorkItem 的事件、结果、下一 actor；
4. Capture 成功必须创建真实 WorkItem，并最终落到 Outcome / Memory 或明确 Failure；
5. MemoryRecord 必须给主人可读内容和来源证据，而不是只给标题；
6. 自动发现必须显示从 `发现 → 授权 → 接管 → 执行 → 结果` 的真实阶段；
7. 空状态必须解释为什么空，以及系统会不会继续自动工作。

## 5. 下一轮开发顺序

遵守项目开发约束，禁止直接从 UI 开始：

```text
1. 搜索学习成熟 Agent / Task / Trace / Knowledge 产品的对象模型与交互
2. 审计当前后端真实表/API/事件，找出哪些事实已经存在、哪些根本没记录
3. 定义单一 WorkItem / ExecutionEvent / Outcome / PendingAction / MemoryRecord 合同
4. 先做后端真实链 + 端到端测试
5. 再让首页/工作/需要我/记忆/Capture 共享同一 projector
6. 用真实 fixture 跑“发现 → 接管 → 执行 → 结果 → 记忆/待办”场景测试
7. 每个大功能完成后生成对应 `docs/TEST_REPORTS/*.md`
8. focused + full + macOS/Windows release CI
9. 新产品 Commit + 同 SHA 双平台 Artifact
10. 新 ACTIVE M5 任务
```

下一轮 M5 不再接受“页面看起来有内容”作为前置，必须先通过自动端到端事实链门禁。

## 6. 权威失败证据

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

## 7. 技术边界保持不变

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

## 8. 历史失败 Artifact

以下均永久 `DO NOT RETRY`：

```text
9258682849 / bd1e7a17
9250384637 / 1d99d10c
9249367672 / f3cba413
9224368022 / 2c96b3ec
9102748834 / 171091fe
```

## 9. 合并边界

PR #88 当前仍是：

```text
DRAFT / DO NOT MERGE
```

不得因六道自动门禁曾通过而合并。下一候选必须先产生新的产品 Commit 和新 Artifact，并重新完成真实接管闭环的自动验收与 M5 主人体验。
