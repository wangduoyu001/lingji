# LingJi 验收权威入口

> 本目录只维护**当前验收治理**。历史实施过程、旧任务和旧失败保留在 Git 历史与 `docs/TEST_REPORTS/`，不得重新冒充当前任务。

## 1. 唯一权威文件

| 文件 | 职责 |
|---|---|
| `LOCAL_EXECUTION_TASK.md` | 唯一当前本机任务单；只有 `status: ACTIVE` 才允许执行 |
| `LOCAL_EXECUTION_RESULT.md` | 当前/最近一次本机任务的权威结果回执 |
| `CHANGE_ACCEPTANCE_LOG.md` | 产品变化对应的增量验收要求与历史追踪；当前产品 V4 条目应从任务指定的精确产品 Commit 读取 |
| `CODEX_ACCEPTANCE_INSTRUCTIONS.md` | 通用本机验收规则 |
| `MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md` | Apple Silicon / M5 专项协议，仅在当前任务要求 macOS 时读取 |
| `MEMORY_QUALITY_TRIAL.md` | 真实数据记忆质量试运行专项协议，仅在任务明确引用时读取 |
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
→ 精确 product_commit 的 docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md 当前相关条目
→ docs/ACCEPTANCE/REPORT_TEMPLATE.md
```

若任务单为 `IDLE`，立即停止，不下载 Artifact、不安装、不启动、不创建报告分支，也不得从历史文档推断下一任务。

若任务单为 `ACTIVE`，只执行其中给出的精确产品 Commit、Artifact、哈希、报告路径和清理规则。

## 3. 当前仓库状态

截至 2026-08-16，PR #88 的新 Owner Workbench V4 候选已完成自动产品门禁并进入真实 M5 复验：

```text
product commit: bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9
task: PR88-M5-OWNER-WORKBENCH-V4-BD1E7A17
result: PENDING
current local task: ACTIVE
product PR: DRAFT / DO NOT MERGE
macOS Artifact: 9258682849 / lingji-macos-arm64
```

同一精确产品 SHA 的六道自动门禁已全部 PASS：

```text
tests 31928631115
P0 Windows Gate 31928631099
macOS Desktop Gate 31928631105
Windows Desktop Release Baseline 31928631101
acceptance-doc-sync 31928631103
local-execution-handoff 31928631118
```

本轮 V4 重点验证上一轮真实 M5 暴露的四个 P1：主人动作语义、空待办、无限分页、记忆/自动化割裂；并强制补测 Window Recovery。

历史失败 Artifact `9250384637`、`9249367672`、`9224368022`、`9102748834` 永久 `DO NOT RETRY`。

## 4. 当前 Artifact 身份

macOS M5 本轮只能使用：

```text
Artifact ID: 9258682849
Name: lingji-macos-arm64
Workflow: 31928631105
ZIP SHA256: c26408c350bf35701bdf6aa97e75f65e7bead42fb6ed92d11838334274e1a888
DMG SHA256: a5d54cba4f99411541527be7230d568f32a8fba90efed14ff9756df6b393bb46
Product: bd1e7a17304d3f00967e2b3f5db425b0ab18d0e9
```

Windows 同 SHA 发布包只用于跨平台身份与发布链证据，本轮 M5 不安装：

```text
Artifact ID: 9258675881
Name: lingji-windows-0.1.0-bd1e7a17
ZIP SHA256: 0696ae6615d8afc44f46efc264fd7852e7d971866efc1285f2397d87a36ce4b1
```

## 5. 开发与验收流程

```text
理解需求和现有实现
→ 搜索/学习相关成熟项目与交互案例
→ 定义统一数据合同和验收标准
→ 修改代码和测试
→ 更新 CHANGE_ACCEPTANCE_LOG.md
→ focused 验证
→ 最终树 full / release / CI
→ 锁定单一产品 Commit
→ 同 SHA 生成 Artifact
→ 更新 LOCAL_EXECUTION_TASK.md 为新 task_id + ACTIVE
→ 本机 Codex 真机执行
→ 报告 + 结果回执 + 远程复读 + 清理
→ 决定修复、继续或合并
```

产品代码、Runtime、Desktop、连接器、数据链路、脚本、依赖或发布流程变化时，必须同步更新 `CHANGE_ACCEPTANCE_LOG.md`。

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

验收结论只允许 `PASS / FAIL / BLOCKED / NOT_TESTED / SKIPPED_NOT_INSTALLED`。最终报告必须区分自动检查、主人肉眼观察、未测试项、清理与回滚，以及精确产品/Artifact/报告身份。

`git push` 不等于完成。必须远程重新确认报告分支、报告 Commit、报告、证据、结果回执和 PR 评论均可读取。

## 9. 清理与恢复

开始前只处理确认属于当前任务的临时目录、进程和端口；Production、Vault、正式记忆、主人配置与未知文件不可删除。

PASS 按任务要求保留正式安装并清理临时材料；FAIL 必须恢复任务规定的旧安装/配置并保留最小失败证据；清理失败不得写 COMPLETED PASS。

## 10. 主人与代理边界

Codex 负责命令、安装、进程、端口、哈希、日志、Git、报告、远程复读和清理。主人只负责机器无法自动证明的体验与内容判断。Codex 不得替主人宣称肉眼体验 PASS。

## 11. 合并边界

产品 PR 只有在当前候选对应的精确自动门禁、同 SHA Artifact、真机、主人观察、Production 隔离、报告闭环和清理全部通过后，才允许进入最终合并判断。

**PR #88 当前仍是 Draft / DO NOT MERGE。当前唯一 ACTIVE 本机任务是 `PR88-M5-OWNER-WORKBENCH-V4-BD1E7A17`。**
