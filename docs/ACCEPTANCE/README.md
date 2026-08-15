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
→ docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md 当前相关条目
→ docs/ACCEPTANCE/REPORT_TEMPLATE.md
```

若任务单为 `IDLE`，立即停止，不下载 Artifact、不安装、不启动、不创建报告分支，也不得从历史文档推断下一任务。

若任务单为 `ACTIVE`，只执行其中给出的精确产品 Commit、Artifact、哈希、报告路径和清理规则。

## 3. 当前仓库状态

截至 2026-08-16，PR #88 当前候选：

```text
product commit: 1d99d10cdcb151c0a0257f7d0a93937cdb817b49
task: PR88-M5-OWNER-WORK-FEED-V3-1D99D10C
result: PENDING / PENDING
current local task: ACTIVE
product PR: DRAFT / DO NOT MERGE
```

六道同 SHA 产品门禁均 PASS；新的 macOS / Windows Artifact 已独立下载复核身份与哈希。当前只代表**可以进入真实 M5 复验**，不代表产品已经 PASS。

本轮 Owner Work Feed v3 重点验证：

- 至少 2 份具体资料能被主人直接认出；
- 每份资料明确“灵机已做”；
- 每份资料明确“下一步”；
- 明确哪些需要主人行动，哪些不需要；
- 资料行与顶部主人待办不得互相矛盾；
- 明细不可读时必须诚实降级，禁止只显示数量；
- Window Recovery 菜单、快捷键、Dock Reopen 本轮必须真实验证。

上一轮 `f3cba413... / 9249367672` 已 `FAIL / DO NOT RETRY`。更早的 `9224368022` 与 `9102748834` 同样永久禁止重跑。

## 4. 开发与验收流程

```text
理解需求和现有实现
→ 搜索/核对相关实现与外部依赖（需要时）
→ 定义验收标准
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

## 5. 本机任务硬门禁

每个 ACTIVE 任务必须明确：

- repository / product PR / product branch / 精确 product commit；
- Artifact 名称、ID、必要哈希；
- execution mode；
- report branch / report path / evidence path；
- 开始前与结束后清理；
- 远程复读要求；
- 主人肉眼确认范围；
- PASS / FAIL / BLOCKED 判定；
- 数据、Secret、Production 与回滚边界。

禁止：

- 用短 SHA、版本号或“看起来一样”替代精确身份；
- 重跑已被失败结论淘汰的 Artifact；
- 在验收分支偷偷修产品；
- force push、`reset --hard`、`clean -fdx` 处理主人环境；
- 为了绿灯降低断言、隔离、Secret 或生命周期要求。

## 6. 平台专项协议

专项文档是**协议**，不是任务单。

- macOS / Apple Silicon / M5：读取 `MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md`；具体 Commit、Artifact、路径和 task_id 永远以 `LOCAL_EXECUTION_TASK.md` 为准。
- 真实数据记忆质量试运行：只有任务单显式指定 `DAY0_THEN_REAL_DATA_TRIAL` 时才读取 `MEMORY_QUALITY_TRIAL.md`。
- Windows 或普通本机验证：以 `CODEX_ACCEPTANCE_INSTRUCTIONS.md` 和任务单为准。

专项协议若与当前任务单的示例身份冲突，以任务单为准；若安全边界冲突，采用更严格规则并在报告记录。

## 7. 报告与回执

验收结论只允许：

```text
PASS
FAIL
BLOCKED
NOT_TESTED
SKIPPED_NOT_INSTALLED
```

不得使用“应该可以”“基本正常”“代码看起来没问题”。

最终报告必须区分自动检查、主人肉眼观察、未测试项、已知限制、清理与回滚，以及精确产品/Artifact/报告身份。

`git push` 不等于完成。必须远程重新确认报告分支、报告 Commit、报告、结果回执和 PR 评论均可读取。

## 8. 清理与恢复

开始前只处理确认属于当前任务的临时目录、进程和端口；Production、Vault、正式记忆、主人配置与未知文件不可删除。

结束后：

- PASS：按任务要求保留正式安装，清理本轮临时材料；
- FAIL：停止本轮精确 Runtime，恢复任务规定的旧安装/配置，保存最小失败证据并清理临时数据；
- 清理失败：不得写 COMPLETED PASS。

## 9. 主人与代理边界

Codex 负责命令、安装、进程、端口、哈希、日志、Git、报告、远程复读和清理。

主人只负责机器无法自动证明的体验与内容判断，例如首页是否看懂、具体资料是否可识别、下一步是否清楚、窗口行为是否符合预期。

Codex 不得替主人宣称肉眼体验 PASS。

## 10. 合并边界

产品 PR 只有在当前候选对应的精确自动门禁、同 SHA Artifact、真机、主人观察、Production 隔离、报告闭环和清理全部通过后，才允许进入最终合并判断。

**PR #88 当前仍是 Draft / DO NOT MERGE。** 本轮 M5 若失败，必须先把任务转回 `IDLE`，淘汰当前 Artifact，再形成新 Commit + 新 Artifact + 新 ACTIVE task，禁止沿用失败候选。
