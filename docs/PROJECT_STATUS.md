# PROJECT_STATUS.md — LingJi 当前状态

> Updated: 2026-08-20
> Formal/default branch: `master`
> Current product PR: `#88`
> Current development PR: `#105 / fix/pr88-owner-fact-chain-v5`
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

技术发布链不是上一轮主要阻塞。精确产品/Artifact 身份、arm64、strict codesign、Acceptance 隔离、Secret 边界、两轮 Runtime 生命周期、分页终点、Production pollution=0、失败回滚与清理均通过。

真正阻塞是：**灵机没有形成主人可见、可追踪、可验证的“接管并完成工作”闭环。**

主人最终观察：

> 看不出灵机实际做了什么、接管了什么，与旧版没有明显差异。

当前正在 PR #105 修复该问题。PR #105 仍为开发中 / Draft；没有新的可执行 M5 Artifact，也不得提前激活本机任务。

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

## 3. PR #105 当前修复状态

状态：`IN_PROGRESS / SELF_REVIEW_REQUIRED / NO_M5`

当前架构决定：

```text
CaptureEnvelope.capture_id
        ↓ 持久化
extraction_jobs.job_id = WorkItem identity
        ↓
Capture Control sanitized WorkItem DTO
        ↓
shared ownerWorkFeed projector
        ↓
Home + Work
```

主人待办继续走独立且具体的对象边界：

```text
Memory Review candidate(memory_id)
Assistant import candidate(candidate_id)
Irreversible vector rebuild object
        ↓
ownerWorkbenchModel shared PendingAction projector
        ↓
Home + 需要我
```

当前已落地：

- 纯文本使用一等 `source_type=text`，不再冒充网页；
- `capture_id` 持久进入已有 extraction job payload，进程重启后仍可追踪；
- `job_id` 直接作为现有 Capture/Extraction WorkItem，不新建第二套工作数据库；
- `/api/capture/jobs` 输出安全白名单 WorkItem：真实状态、结果、下一动作、下一执行者、稳定结果引用；
- Owner DTO 不输出 captured body、raw payload、原始错误、绝对输入路径或 worker 原始进度文案；
- Cmd+K 返回真实 `capture_id/job_id/status`，不再提前宣称“已经记住”，快速记录标题不复制正文；
- 首页与“工作”共享同一 WorkItem projector，不再通过 `relative_path`、记忆数量、generic event 或 Codex 当前状态猜“灵机做了什么”；
- 主动发现明确区分“发现”与“已授权/已接管/已执行”；
- Home 与“需要我”共享 concrete PendingAction projector；没有真实对象不创建主人动作；
- 新增 V5 计划、自测和隐私回归测试；旧 V3/V4 smoke 正在按新事实合同收口，而不是删除测试换绿灯。

尚未允许宣称完成：

- PR #105 精确 Head 的完整自动门禁仍需全部绿；
- 必须完成独立代码自审并生成 `PR88_OWNER_FACT_CHAIN_V5_IMPLEMENTATION.md`；
- 必须检查代码地图、状态、验收记录和变更日志同步；
- PR #105 合入产品分支后，产品 exact SHA 必须重新跑六道门并生成同 SHA Mac/Windows Artifact；
- M5 仍不得激活，Window Recovery 三路径和主人 10 秒理解检查仍属于未来真机门禁。

## 4. 已确认通过，不要重复返工

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

## 5. 唯一主人事实链

产品目标仍是：

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
3. “工作”必须能看到每个真实 WorkItem 的状态、结果、下一 actor；
4. Capture 成功必须创建真实 WorkItem，并最终落到 Outcome / Memory 或明确 Failure；
5. MemoryRecord 必须给主人可读内容和来源证据，而不是只给标题；
6. 自动发现必须如实显示停在哪一阶段；只完成“发现”时不得写“已接管”；
7. 空状态必须解释为什么空，不得通过统计或静态事件制造活动感。

## 6. 验收前开发顺序

```text
1. 审计当前后端真实表/API/事件
2. 复用 extraction_jobs 建立稳定 Capture → WorkItem 身份
3. 建立单一安全 WorkItem projector
4. Home/Work 共享 WorkItem；Home/Attention 共享 PendingAction
5. 用真实 fixture 验证重启、重复、成功、失败、隐私和未知状态
6. 更新对应 Desktop smoke / Python tests
7. 独立自审并记录发现的问题与修复
8. self-review verdict 必须为 PASS_FOR_M5_PREPARATION
9. focused/full/release 与双平台产品门禁
10. 新产品 Commit + 同 SHA Mac/Windows Artifact
11. 最后才允许新 ACTIVE M5 任务
```

下一轮 M5 不接受“页面看起来有内容”作为前置，必须先通过自动端到端事实链和独立自审门禁。

## 7. 权威失败证据

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

## 8. 技术边界保持不变

- `src/` 为长期平台主线；
- `desktop/lingji-control/` 为唯一正式 Desktop UI；
- `second_brain/` 只做兼容/迁移；
- Desktop 只通过认证的 `127.0.0.1:8766` Local Control API；
- Obsidian Vault + Git 为永久记忆正文权威；
- SQLite/Qdrant 为可重建索引与运行状态；
- `extraction_jobs` 继续承担 Capture 工作状态，不新增第二套 WorkItem 数据库；
- Acceptance / Production 物理隔离；
- Secret 只留在系统安全凭据边界；
- Runtime stop 只处理精确实例；
- 不创建第二事实源来美化状态；
- AI 不能自动批准永久记忆；
- 不自动执行破坏性 Qdrant rebuild。

## 9. 历史失败 Artifact

以下均永久 `DO NOT RETRY`：

```text
9258682849 / bd1e7a17
9250384637 / 1d99d10c
9249367672 / f3cba413
9224368022 / 2c96b3ec
9102748834 / 171091fe
```

## 10. 合并与 M5 边界

PR #88 当前仍是：

```text
DRAFT / DO NOT MERGE
```

PR #105 当前仍是开发 PR。不得因部分 CI 通过而激活 M5。新的 M5 只能在独立自审 `PASS_FOR_M5_PREPARATION`、产品同 SHA 六道门、双平台新 Artifact 和哈希锁定后创建。