# LingJi 验收权威入口

> 本目录只维护**当前验收治理**。历史实施过程、旧任务和旧失败保留在 Git 历史与 `docs/TEST_REPORTS/`，不得重新冒充当前任务。

## 1. 唯一权威文件

| 文件 | 职责 |
|---|---|
| `LOCAL_EXECUTION_TASK.md` | 唯一当前本机任务单；只有 `status: ACTIVE` 才允许执行 |
| `LOCAL_EXECUTION_RESULT.md` | 当前/最近一次本机任务的权威结果回执 |
| `CHANGE_ACCEPTANCE_LOG.md` | 产品变化对应的增量验收要求与历史追踪 |
| `CODEX_ACCEPTANCE_INSTRUCTIONS.md` | 通用本机验收规则 |
| `MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md` | Apple Silicon / M5 专项协议，仅在当前任务要求 macOS 时读取 |
| `MEMORY_QUALITY_TRIAL.md` | 真实数据记忆质量试运行专项协议，仅在任务明确引用时执行 |
| `REPORT_TEMPLATE.md` | 报告固定结构 |

**不存在第二份“当前任务单”。** 任何旧阶段计划、聊天摘要、PR 评论或历史报告都不能覆盖 `LOCAL_EXECUTION_TASK.md`。

## 2. 固定读取顺序

```text
AGENTS.md
→ docs/PROJECT_STATUS.md
→ docs/ACCEPTANCE/README.md
→ docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md
→ docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
→ 当前任务明确引用的专项协议
→ docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md
→ docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md 当前相关条目
→ docs/ACCEPTANCE/REPORT_TEMPLATE.md
```

若任务单为 `IDLE`，立即停止，不下载 Artifact、不安装、不启动、不创建报告分支，也不得从历史文档推断下一任务。

若任务单为 `ACTIVE`，只执行其中给出的精确产品 Commit、Artifact、哈希、报告路径和清理规则。

## 3. 当前仓库状态

截至 2026-08-16，PR #88 的 Owner Workbench V4 已完成真实 M5 复验：

```text
product commit: bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9
task: PR88-M5-OWNER-WORKBENCH-V4-BD1E7A17
result: COMPLETED / FAIL
current local task: IDLE
product PR: DRAFT / DO NOT MERGE
macOS Artifact: 9258682849 / DO NOT RETRY
```

主人明确观察：看不出灵机实际做了什么、接管了什么，与旧版没有明显差异。

主要阻塞：

- 首页候选与“需要我 0 待办”矛盾；
- 工作履历为空；
- `Cmd+K` 真实记录失败；
- 记忆缺少可读正文/摘要和可验证来源；
- 自动发现缺少真实接管/执行链；
- Window Recovery 三路径没有全部完成主人确认。

技术上已经确认：产品/Artifact 身份、arm64、strict codesign、Acceptance 隔离、两轮 exact-instance Runtime 生命周期、分页终点、Secret 边界与 Production pollution=0 均通过。

## 4. 当前无可执行 Artifact

以下 macOS Artifact 均已由最终失败结论淘汰，永久 `DO NOT RETRY`：

```text
9258682849 / bd1e7a17
9250384637 / 1d99d10c
9249367672 / f3cba413
9224368022 / 2c96b3ec
9102748834 / 171091fe
```

Codex 不得因为文件仍存在、CI 曾经通过或 PR 仍为 Draft 而重跑这些 Artifact。

## 5. 下一轮进入 M5 的前置条件

下一轮不得先做新的首页外观。必须先建立并自动证明同一真实事实链：

```text
SourceObject
→ Discovery / Intent
→ WorkItem
→ ExecutionEvent
→ Outcome
→ NextAction + actor
→ PendingAction（如确实需要主人）
→ MemoryRecord（如产生日常永久记忆）
```

首页、工作、需要我、记忆、Capture 只能投影这条同一事实链。

新的 M5 任务只能在以下条件全部完成后激活：

```text
搜索学习成熟 Agent / Task / Trace / Knowledge 产品
→ 审计当前真实数据合同
→ 实现统一 WorkItem / Event / Outcome / PendingAction / MemoryRecord 链
→ 真实端到端场景测试
→ 更新 CHANGE_ACCEPTANCE_LOG + 实施报告
→ focused + full + release CI
→ 新产品 Commit
→ 同 SHA macOS / Windows Artifact
→ 哈希锁定
→ 新 task_id + status: ACTIVE
```

## 6. 本机任务硬门禁

每个 ACTIVE 任务必须明确 repository / PR / branch / 精确 product commit、Artifact 名称与 ID、必要哈希、execution mode、报告路径、清理规则、远程复读、主人确认范围与 PASS/FAIL 判定。

禁止：

- 用短 SHA、版本号或“看起来一样”替代精确身份；
- 重跑已被失败结论淘汰的 Artifact；
- 在验收分支偷偷修产品；
- force push、`reset --hard`、`clean -fdx` 处理主人环境；
- 为了绿灯降低断言、隔离、Secret 或生命周期要求。

## 7. 平台专项协议

专项文档是**协议**，不是任务单。macOS/M5 读取 `MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md`；具体身份永远以 `LOCAL_EXECUTION_TASK.md` 为准。Memory Quality Trial 只在任务显式引用时执行。

## 8. 报告与回执

最近一次失败证据：

```text
Report branch: acceptance/pr88-m5-owner-workbench-v4-bd1e7a17
Report commit: 5793e4ae22e17d1f4db2c57ecc66bf18ec65af2e
Cleanup/result commit: 3011d796ff1bb5bff7d5e37c24e0c6236ee51d34
PR #88 comment: 5306178636
```

原报告中的自引用 `PENDING` 占位不覆盖最终回执；最终状态以 `LOCAL_EXECUTION_RESULT.md`、验收分支最终结果和 PR 评论为准。

验收结论只允许 `PASS / FAIL / BLOCKED / NOT_TESTED / SKIPPED_NOT_INSTALLED`。`git push` 不等于完成，必须远程重新确认报告分支、报告 Commit、证据、结果回执和 PR 评论均可读取。

## 9. 清理与恢复

开始前只处理确认属于当前任务的临时目录、进程和端口；Production、Vault、正式记忆、主人配置与未知文件不可删除。

PASS 按任务要求保留正式安装并清理临时材料；FAIL 必须恢复任务规定的旧安装/配置并保留最小失败证据；清理失败不得写 COMPLETED PASS。

## 10. 主人与代理边界

Codex 负责命令、安装、进程、端口、哈希、日志、Git、报告、远程复读和清理。主人只负责机器无法自动证明的体验与内容判断。Codex 不得替主人宣称肉眼体验 PASS。

## 11. 合并边界

产品 PR 只有在当前候选对应的精确自动门禁、同 SHA Artifact、真机、主人观察、Production 隔离、报告闭环和清理全部通过后，才允许进入最终合并判断。

**PR #88 当前仍是 Draft / DO NOT MERGE。当前没有 ACTIVE 本机任务。**
