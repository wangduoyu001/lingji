# LingJi 验收权威入口

> 本目录只维护**当前验收治理**。历史实施过程、旧任务和旧失败保留在 Git 历史与 `docs/TEST_REPORTS/`，不得重新冒充当前任务。

## 1. 唯一权威文件

| 文件 | 职责 |
|---|---|
| `LOCAL_EXECUTION_TASK.md` | 唯一当前本机任务单；只有 `status: ACTIVE` 才允许执行 |
| `LOCAL_EXECUTION_RESULT.md` | 最近一次本机任务的权威结果回执 |
| `CHANGE_ACCEPTANCE_LOG.md` | 产品变化对应的增量验收要求与历史追踪 |
| `CODEX_ACCEPTANCE_INSTRUCTIONS.md` | 通用本机验收规则 |
| `MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md` | Apple Silicon / M5 专项协议，仅在当前任务要求 macOS 时读取 |
| `MEMORY_QUALITY_TRIAL.md` | 真实数据记忆质量试运行专项协议，仅在任务明确引用时读取 |
| `REPORT_TEMPLATE.md` | 报告固定结构 |

**不存在第二份“当前任务单”。** 任何旧的阶段计划、聊天摘要、PR 评论或历史报告都不能覆盖 `LOCAL_EXECUTION_TASK.md`。

## 2. 固定读取顺序

本机 Codex 收到“去看任务单干活”后只按以下顺序读取：

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

若任务单为：

```yaml
status: IDLE
```

立即停止，不下载 Artifact、不安装、不启动、不创建报告分支，也不得从历史文档推断下一任务。

## 3. 当前仓库状态

截至 2026-08-15，PR #88 对产品 Commit `2c96b3ec54b066204cad8db75455be24822852a9` 的 M5 真机复验已完成：

```text
verdict: FAIL
merge: DO NOT MERGE
current local task: IDLE
```

技术身份、签名、arm64、Acceptance 隔离和第二次 Runtime 生命周期通过；主人未通过首页自动化可见性、UI 可感知差异、信息层级、“找回主窗口”和 Memory Progress Dashboard。

权威证据：

```text
report branch: acceptance/pr88-m5-reacceptance-2c96b3ec
report commit: 9fdbacf52c22ecaac7eab3a4676f80a81e0dfa95
cleanup receipt commit: 33982e1d5d3d567369e56484ade733a8b7228408
```

Artifact `9224368022` 已完成失败验收，不得再次作为候选重跑。历史失败 Artifact `9102748834` 同样永久禁止重试。

## 4. 开发与验收流程

每次产品变化固定遵循：

```text
理解需求和现有实现
→ 搜索/核对外部依赖与规则（需要时）
→ 定义验收标准
→ 修改代码和测试
→ 更新 CHANGE_ACCEPTANCE_LOG.md
→ 跑 focused 验证
→ 最终树跑 full / release / CI
→ 锁定单一产品 Commit
→ 由同一精确 SHA 生成 Artifact
→ 更新 LOCAL_EXECUTION_TASK.md 为新 task_id + ACTIVE
→ 本机 Codex 真机执行
→ 报告 + 结果回执 + 远程复读 + 清理
→ 决定修复、继续或合并
```

产品代码、Runtime、Desktop、连接器、数据链路、脚本、依赖或发布流程变化时，必须同步更新 `CHANGE_ACCEPTANCE_LOG.md`。不得以“小改动”为理由跳过。

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
- 重跑已经被失败结论淘汰的 Artifact；
- 在验收分支偷偷修产品；
- force push、`reset --hard`、`clean -fdx` 处理主人环境；
- 为了绿灯降低断言、隔离、Secret 或生命周期要求。

## 6. 平台专项协议

专项文档是**协议**，不是任务单。

- macOS / Apple Silicon / M5：读取 `MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md`；具体 Commit、Artifact、路径和 task_id 永远以 `LOCAL_EXECUTION_TASK.md` 为准。
- 真实数据记忆质量试运行：只有任务单显式指定 `DAY0_THEN_REAL_DATA_TRIAL` 时才读取 `MEMORY_QUALITY_TRIAL.md`。
- Windows 或普通本机验证：以 `CODEX_ACCEPTANCE_INSTRUCTIONS.md` 和任务单为准。

专项协议中若存在示例值，与当前任务单冲突时以任务单为准；若安全边界冲突，采用更严格规则并在报告记录。

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

最终报告必须区分：

- 自动检查结果；
- 主人肉眼观察；
- 未测试项；
- 已知限制；
- 清理与回滚；
- 产品 Commit、Artifact 与哈希；
- 报告 Commit 与远程确认。

`git push` 不等于完成。必须远程重新确认报告分支、报告 Commit、报告、结果回执和 PR 评论均可读取。

## 8. 清理与恢复

开始前：

- 只处理确认属于当前任务的临时目录、进程和端口；
- Production、Vault、正式记忆、主人配置与未知文件不可删除；
- 不得使用全局 kill 处理 Python、Node、Codex 等进程。

结束后：

- PASS：清理本轮 Artifact、解压、普通日志、截图、fixture、checkpoint、临时配置、临时 worktree 和任务根；按任务要求保留正式安装。
- FAIL：停止本轮精确 Runtime，恢复任务规定的旧安装/配置，保存最小失败证据，清理本轮临时数据。
- 清理失败：不得写 COMPLETED PASS。

## 9. 主人与代理边界

Codex 负责命令、安装、进程、端口、哈希、日志、Git、报告、远程复读和清理。

主人只负责机器无法自动证明的体验与内容判断，例如：

- 第一次打开是否知道下一步；
- 首页是否能看懂；
- 自动化过程是否真的可见；
- 窗口行为是否符合预期；
- 真实内容答案和来源是否正确。

Codex 不得替主人宣称肉眼体验 PASS。

## 10. 合并边界

产品 PR 只有在当前候选对应的：

- 精确产品 Commit 自动门禁通过；
- 同 SHA Artifact 锁定；
- 当前任务真机 PASS；
- 主人观察 PASS；
- 无未披露 P0/P1 blocker；
- Production 污染为 0；
- 报告与回执远程可读；
- 清理完成；

之后才允许进入最终合并判断。

验收失败后必须先把任务转为 `IDLE`，完成产品修复并形成**新 Commit + 新 Artifact + 新 ACTIVE task**，不能继续沿用旧失败候选。
