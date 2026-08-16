# PR88-M5-OWNER-WORKBENCH-V4-BD1E7A17 Owner + Codex Full Acceptance Report

## 1. Executive Verdict

```text
Verdict: FAIL
Merge recommendation: DO NOT MERGE
Product commit: bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9
Artifact: lingji-macos-arm64
Artifact ID: 9258682849
Report commit: PENDING
```

主人确认不合格：看不出灵机实际做了什么、接管了什么，与旧版没有明显差异。已验证的 UI 也出现主页候选待确认与“需要我”空待办冲突、工作履历为空、全局记录真实失败、记忆证据不可读等 P1。当前 Artifact 不得重跑，PR #88 保持 Draft。

## 2. Product and Artifact Identity

| 项目 | 预期 | 实际 | 结论 |
|---|---|---|---|
| Repository / PR | wangduoyu001/lingji / #88 | 一致 | PASS |
| Product Commit | `bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9` | DMG 内嵌 metadata 一致 | PASS |
| Artifact | `lingji-macos-arm64` / `9258682849` | 指定唯一包 | PASS |
| ZIP SHA256 | `c26408…1a888` | 一致 | PASS |
| DMG SHA256 | `a5d54…bb46` | 一致 | PASS |
| Native binaries | Apple Silicon arm64 | 主程序与 packaged sidecar 均为 arm64 | PASS |
| Signature | strict codesign | DMG 与安装后均通过 | PASS |

## 3. Change Acceptance Source

- 当前任务：`master/docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`，任务 `PR88-M5-OWNER-WORKBENCH-V4-BD1E7A17`。
- 受影响范围：Owner Workbench、记忆工作区、需要我、工作履历、全局记录、分页、主动发现和 Window Recovery。
- 不在范围：不修改产品代码；不读主人真实资料正文；不安装 Windows Artifact。

## 4. Environment Cleanup and Isolation

- M5 / arm64 与 Gatekeeper 状态已检查；安装前无 LingJi Runtime、8766 或 8767 监听。
- 使用 whole-bundle replace；所有运行数据、fixture、日志和 Artifact 只进入任务专属 Acceptance 根。
- 两轮 Runtime 结束均验证 state 消失、已保存 Sidecar PID 消失、8766 释放。
- Production DataRoot 仅做只读污染检查；本轮新增文件数为 `0`。
- `secret_export_count=0`；公开证据未包含 Token、Authorization、私人路径或测试正文。
- 因 FAIL，已停止被测 Runtime，并整体恢复验收前的签名有效应用。

## 5. CI and Automated Tests

| 测试 | Commit | 结果 | 证据 |
|---|---|---|---|
| tests | `bd1e7a17` | PASS | Run `31928631115` |
| P0 Windows Gate | `bd1e7a17` | PASS | Run `31928631099` |
| macOS Desktop Gate | `bd1e7a17` | PASS | Run `31928631105` |
| Windows Desktop Release | `bd1e7a17` | PASS | Run `31928631101` |
| acceptance-doc-sync | `bd1e7a17` | PASS | Run `31928631103` |
| local-execution-handoff | `bd1e7a17` | PASS | Run `31928631118` |

自动门禁不覆盖本报告的真机与主人失败结论。

## 6. Test Cases

```text
ID: M5-V4-001
Name: 第一眼主人简报
Preconditions: 新鲜 Acceptance Runtime。
Method: 打开首页并阅读“需要我 / 已做 / 进行中 / 下一步 / 记忆 / 主动发现”。
Expected: 几秒内能回答现在要不要做事、实际完成内容和下一步。
Actual: 首页称已修复运行问题并要求确认候选；没有能读懂的对象、结果或证据。
Evidence: 主人确认“不合格；什么也不是；干了什么、接管什么完全看不出来”。
Verdict: FAIL

ID: M5-V4-002
Name: 日常一级导航
Preconditions: 首页已打开。
Method: 遍历首页、记忆、工作、需要我、高级。
Expected: 日常入口清晰，技术信息下沉。
Actual: 五个一级入口存在；技术细节位于高级折叠区。
Evidence: 真机 Accessibility/UI 逐页遍历。
Verdict: PASS

ID: M5-V4-003
Name: 可检查的永久记忆
Preconditions: Acceptance 中已有两条初始记忆对象。
Method: 打开记忆、选择对象、阅读详情与来源。
Expected: 可读正文/摘要、可验证来源与证据链；未知时清楚解释。
Actual: 只有“核心记忆标题”等泛化标题，正文不可安全展示，来源路径未公开、无行级引用；不构成主人可检查的第二记忆大脑。
Evidence: 记忆详情实测。
Verdict: FAIL

ID: M5-V4-004
Name: 需要我仅含真实对象
Preconditions: 首页显示“需要你确认这条候选是否保留”。
Method: 打开“需要我”。
Expected: 同一真实对象可处理，或首页不显示待确认。
Actual: “需要我”显示 0 真实待办，没有任何候选；与首页相互矛盾。
Evidence: 真机逐页比对。
Verdict: FAIL

ID: M5-V4-005
Name: 候选记忆精确直达
Preconditions: 首页声称存在候选。
Method: 进入需要我并尝试定位同一对象。
Expected: 以真实 memory_id 直接打开同一详情。
Actual: 不存在可验证的待审对象，无法精确直达。
Evidence: “需要我”0 真实待办。
Verdict: FAIL

ID: M5-V4-006
Name: 工作履历
Preconditions: 首页声称刚完成运行修复。
Method: 打开工作页。
Expected: 每项说明发生了什么、做了什么、结果、下一步和执行者。
Actual: 工作页为 0 记录，无法证明首页“真实结果”。
Evidence: 真机工作页。
Verdict: FAIL

ID: M5-V4-007
Name: Cmd+K 全局记录
Preconditions: Acceptance Runtime 在线。
Method: 使用 Cmd+K，提交“记住：M5 V4 验收测试记录”。
Expected: 进入可追踪的正式 Capture 流程，仅写入 Acceptance。
Actual: UI 明确显示“这次记录没有提交成功”；没有创建可追踪工作或记忆对象。
Evidence: 真机提交后的真实错误提示。
Verdict: FAIL

ID: M5-V4-008
Name: 分页终点
Preconditions: 记忆列表只有两项。
Method: 检查第一页的前后页控件。
Expected: 后端 `has_more=false` 时下一页不可用。
Actual: 上一页和下一页均禁用。
Evidence: 记忆页。
Verdict: PASS

ID: M5-V4-009
Name: 主动发现与自动化可见性
Preconditions: 首页已加载。
Method: 阅读主动发现与工作履历，并对比已授权边界。
Expected: 能清楚看到发现对象、实际自动动作和待授权对象。
Actual: 仅显示发现 Codex / WorkBuddy 的静态说明；不能看出接管什么、已做什么或下一步自动动作。
Evidence: 首页与主人观察。
Verdict: FAIL

ID: M5-V4-010
Name: 高级信息下沉
Preconditions: 日常首页。
Method: 检查日常区与高级区。
Expected: PID、端口、模型和日志不占据日常路径。
Actual: 日常区未要求理解技术指标；高级区提供显式入口。
Evidence: 首页布局。
Verdict: PASS

ID: M5-V4-011
Name: Window Recovery
Preconditions: 主窗口已启动。
Method: 自动尝试最小化后 Cmd+Shift+L 找回；菜单与 Dock Reopen 等待主人肉眼确认。
Expected: 三条路径均把窗口带到当前屏幕。
Actual: 快捷键自动观察到窗口回到前台，但主人未逐条肉眼确认；菜单和 Dock Reopen 未完成。
Evidence: 真机自动观察；主人未对三路径分别确认。
Verdict: NOT_TESTED

ID: M5-V4-012
Name: 两轮 Runtime 生命周期
Preconditions: 任务隔离根。
Method: 两次启动、authenticated Control API、保存 Sidecar PID、正常关闭并逐项验证 state / PID / 8766。
Expected: 两轮均无残留 Runtime、端口或孤儿进程。
Actual: 两轮均完成；第一轮保存 PID 后验证三项停止条件，第二轮重复通过。
Evidence: 私有 task-scoped state 与进程检查。
Verdict: PASS
```

## 7. Regression Matrix

| 回归项 | 结果 | 证据/说明 |
|---|---|---|
| UI 空待办或假动态 | FAIL | 首页候选与需要我 0 待办矛盾；工作履历为空 |
| 无限下一页 | PASS | 记忆 `has_more=false` 时下一页禁用 |
| Token 泄露 | PASS | `secret_export_count=0`，公开报告仅含哈希 |
| 自动写 Core Memory | PASS | 全局记录失败，未写入正式数据 |
| Production 被污染 | PASS | 只读检查新增文件为 0 |
| 重复 Core / 孤儿 Runtime | PASS | 两轮精确停止后 state、PID、8766 均释放 |
| Window Recovery | NOT_TESTED | 未获主人三路径肉眼确认 |

## 8. Blocking Defects

```text
Defect ID: M5-V4-WORKBENCH-001
Severity: P1
Affected scope: 首页、需要我、工作、记忆、自动化理解
Reproduction: 新鲜 Acceptance Runtime 打开首页后依次进入“需要我”“工作”“记忆”；用 Cmd+K 提交记住命令。
Expected: 可追溯真实对象统一解释灵机做了什么、接管什么、结果和下一步。
Actual: 首页与待办矛盾，工作为空，记忆不可读，记录失败，主动发现没有可理解的接管/执行链。
Evidence: 主人明确 FAIL；真机逐页结果。
Data/security impact: 未发现 Production 污染或秘密泄露；产品功能承诺不成立。
Required fix: 用同一真实对象模型串联首页、待办、工作和记忆；把自动发现、授权、排队、结果和下一执行者可见化；修复 Capture 提交。
Retest scope: M5-V4-001 至 M5-V4-010、Window Recovery 三路径、两轮生命周期。
```

## 9. Final Merge Recommendation

```text
Product commit: bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9
Verdict: FAIL
Merge recommendation: DO NOT MERGE
Owner observation complete: YES (FAIL)
Required clients covered: macOS M5 Desktop
Skipped clients: Windows（本轮不安装）
Blocking defects: M5-V4-WORKBENCH-001
Acceptance docs synchronized: YES
Temporary evidence cleaned: PENDING remote first read
```

## 10. Sign-off

```text
Codex executor: Codex
Owner confirmation: FAIL — “不合格，什么也不是；干了什么、接管了什么看不出来，跟以前没啥区别。”
Acceptance date: 2026-08-16
Report branch: acceptance/pr88-m5-owner-workbench-v4-bd1e7a17
Report commit: PENDING
```
