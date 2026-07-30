# 验收要求变更记录

> 每个包含产品代码、运行时、UI、连接器、数据链路、脚本、依赖或发布流程变化的 PR，都必须在本文件顶部追加一条记录。
>
> 记录描述“本次代码变化后，验收必须新增、修改或回归什么”。历史记录不得删除，只能更正明显错误并说明原因。

## 填写模板

```markdown
## YYYY-MM-DD · <PR/任务> · <短标题>

- 产品分支：`<branch>`
- 产品 Commit：`<sha 或 pending>`
- 影响模块：
- 风险等级：P0 / P1 / P2 / P3
- 用户可感知变化：
- 数据或安全边界变化：

### 新增或修改的自动验收

- [ ] `<测试命令或测试文件>`：验证什么

### 新增或修改的真机验收

- [ ] `<步骤>`：预期结果

### 主人肉眼确认

- [ ] `<必须人工观察的行为>`

### 回归项

- [ ] `<历史 Bug 或兼容承诺>`

### 清理与回滚

- 临时数据前缀：
- 覆盖安装或迁移方式：
- 临时备份删除条件：
- 测试数据清理方式：

### 不在范围

- `<本次没有实现且不得宣称已完成的能力>`

### 最终报告

- 报告路径：`docs/TEST_REPORTS/<REPORT>.md`
- 报告分支：`acceptance/<task>-<short-sha>`
```

---

## 2026-07-30 · PR #60 · Day 0 安全门槛与真实数据记忆质量试运行

- 产品分支：`feature/unified-ai-memory-connectors`
- 产品 Commit：`1c5148779624910f1c6072d95d6c6f6822f631e6`
- 固定 Artifact：`lingji-windows-0.1.0-1c514877`
- Artifact ID：`8723868744`
- 影响模块：本机安全验收、真实数据导入、来源追溯、幂等去重、候选审核、Codex MCP、质量问题集、远程报告与本地清理
- 风险等级：P0
- 用户可感知变化：不再单独重复做一套形式验收；先完成 Day 0 安全门槛，再直接进入小批量真实数据试运行和记忆质量评分。
- 数据或安全边界变化：真实资料必须由主人明确授权；Day 0 未 PASS 禁止导入；Production 只读；剧本和第三方资料不得被当作主人个人记忆。

### 新增或修改的自动验收

- [ ] `python scripts/check_local_execution_handoff.py`：校验执行模式、专项协议、Day 0、真实数据授权、题数、评分阈值、污染、重复、配置保持、远程确认和清理字段。
- [ ] `python -m pytest -q tests/test_local_execution_handoff.py`：覆盖 Day 0 未通过禁止真实数据、PASS 阈值、主人抽查题数、错误来源、Production 污染和结束清理。
- [ ] `local-execution-handoff` Workflow：精确树运行并拒绝缺少专项字段或弱化阈值的任务/回执。

### 新增或修改的真机验收

- [ ] Day 0 在任何真实数据导入前完成：固定 Artifact、覆盖安装、Runtime、8766/8767、MCP 鉴权、真实 Codex 调用、候选边界、A-01、三轮 Core 重启和 Windows 重启。
- [ ] Day 0 不是 PASS 时立即停止，不读取或导入主人真实资料。
- [ ] 主人明确授权后，Stage 1 只导入 1 部剧本、1 份 Codex 报告、少量 ChatGPT 历史和 1 个明确 Obsidian 目录。
- [ ] 验证 raw、provenance、adapter version、input hash、idempotency key、失败路径、重复导入和候选链。
- [ ] Stage 1 无 P0/P1 后才逐步扩展到最多 10 部剧本和其他授权资料。
- [ ] 至少执行 20 道质量题：精确事实不少于 8、跨文档比较不少于 4、来源核验不少于 4、负面边界不少于 4。
- [ ] 质量阈值：quality score ≥ 90%、source accuracy ≥ 95%、false positive rate ≤ 5%、Codex MCP 成功率 ≥ 95%。
- [ ] 正式数据丢失、Production 污染、重复正式内容、自动写永久记忆、Token/隐私泄露和主人配置破坏均为 0。

### 主人肉眼确认

- [ ] Checkpoint A：安装和首次打开，无黑窗，首页正常，知道下一步，状态文案可区分。
- [ ] Checkpoint B：Codex 能看到 LingJi 工具、真实调用成功、返回内容正确。
- [ ] Checkpoint C：主人亲自批准一个测试候选、拒绝一个测试候选，页面可理解。
- [ ] Checkpoint D：Windows 重启后无黑窗，灵机恢复且页面可操作。
- [ ] Checkpoint E：主人至少抽查 10 道质量题，确认答案与来源评分。

### 强制回归项

- [ ] Day 0 未 PASS 时禁止导入真实资料。
- [ ] 未经主人授权不得扫描或导入任何真实目录。
- [ ] 剧本人物、剧情和台词不得进入主人个人事实。
- [ ] 不存在的问题必须承认未知，不得拿相似资料冒充。
- [ ] 候选未批准前 Core Memory 不增加，拒绝候选不进入永久记忆。
- [ ] A-01 隔离不得读取或修改主人真实 `CODEX_HOME`。
- [ ] 覆盖安装和连接器回滚不得破坏主人数据或配置。
- [ ] Windows 重启后 Runtime、MCP、Workspace、DataRoot 和 Vault 恢复。

### 清理与回滚

- 临时数据前缀：`PR60_MEMORY_TRIAL_1C514877_`
- 临时根目录：`D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-1c514877`
- 覆盖安装方式：固定安装器直接覆盖，不卸载。
- 临时配置副本：每个客户端最多一个，哈希验证后删除。
- 测试数据清理：删除本轮 fixture、checkpoint、测试候选、普通成功日志、截图、重复安装包、解压内容和 worktree。
- 主人授权的真实资料是否保留由主人选择，Codex不得擅自删除。
- 报告第一次远程确认后清理，更新结果回执，再次 push 和远程复读。

### 不在范围

- 不借试运行新增产品功能。
- 不自动批准永久记忆。
- 不启用远程或公网 MCP。
- 不读取未授权浏览器、整盘或用户目录。
- 不把 Stage 2 扩容视为一次性全量迁移。

### 最终报告

- 专项协议：`docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md`
- 任务单：`docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`
- 报告路径：`docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_1c514877.md`
- 报告分支：`acceptance/pr60-memory-quality-trial-1c514877`
- 产品 PR 必须保持 Draft 且不得合并，直到 Day 0、Stage 1、质量指标、主人检查点、远程提交和清理全部满足 PASS。

---

## 2026-07-30 · 本机任务信箱与结果回执硬门禁

- 产品分支：`master`
- 产品 Commit：`governance-only`
- 影响模块：仓库治理、Codex 本机执行交接、报告提交、远程复读、本地垃圾清理、GitHub Actions
- 风险等级：P1
- 用户可感知变化：用户只需告诉 Codex 去看任务单，或告诉 ChatGPT Codex 已完成；不再复制长指令、解释 Git、上传报告或排查分支。
- 数据或安全边界变化：不改变产品数据；明确禁止清理主人 DataRoot、Vault、正式记忆和用户 AI 配置，只清理本轮临时验收垃圾。

### 新增或修改的自动验收

- [x] `python scripts/check_local_execution_handoff.py`：校验任务单、结果回执、身份一致性、开始/结束清理、远程确认和报告 Commit 字段。
- [x] `python -m pytest -q tests/test_local_execution_handoff.py`：覆盖 PENDING、COMPLETED、远程确认缺失、清理失败、身份不一致和阻塞提交。
- [x] `local-execution-handoff` Workflow：在 `master`、开发分支和 `acceptance/**` 报告分支执行；报告分支结果不是 `COMPLETED` 时失败。

### 新增或修改的真机验收

- [x] Codex 只读取 `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md` 中 `status: ACTIVE` 的任务，不从聊天或本机残留推断。
- [x] 每次开始前整体清理上一轮临时验收目录、Artifact、日志、截图、fixture、checkpoint、临时配置副本和 worktree，再释放 8766/8767。
- [x] 报告 push 后使用 `git ls-remote` 和 GitHub API 重新读取远程分支、Commit、报告、结果回执和 PR 评论。
- [x] 第一次远程确认后清理本轮本地垃圾，更新结果回执，再次 push 和远程复读。

### 主人肉眼确认

- [x] 用户只负责下达“去看任务单干活”或“Codex 已完成”，不负责 Git、上传、报告路径和清理操作。

### 回归项

- [x] 禁止把本机生成报告误写成已经上传。
- [x] 禁止 `git push` 命令执行后未复读远程就宣布完成。
- [x] 禁止长期堆积旧验收目录、重复安装包、日志、截图、fixture、checkpoint、配置副本和 worktree。
- [x] 禁止清理主人正式数据或其他任务数据。

### 清理与回滚

- 临时数据前缀：由 `LOCAL_EXECUTION_TASK.md` 每个任务单独声明。
- 覆盖安装或迁移方式：本次为治理变更，不涉及产品安装。
- 临时备份删除条件：远程报告第一次确认后删除；只保留哈希。
- 测试数据清理方式：本机任务结束时删除任务单指定临时根目录和带任务前缀的数据。

### 不在范围

- 不改变 LingJi 产品 Runtime、UI、数据库、记忆或连接器功能。
- 不代替具体任务的真机验收标准。
- 不要求用户学习 Git 或参与报告提交。

### 最终报告

- 规则权威：`docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md` 与 `docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md`
- 自动门禁：`.github/workflows/local-execution-handoff.yml`

---

## 2026-07-29 · PR #60 · P0-A 与统一 AI 记忆连接器重新真机验收（历史方案，已被 2026-07-30 合并试运行方案取代）

- 产品分支：`feature/unified-ai-memory-connectors`
- 产品 Commit：`1c5148779624910f1c6072d95d6c6f6822f631e6`
- 固定 Artifact：`lingji-windows-0.1.0-1c514877`
- Artifact ID：`8723868744`
- 影响模块：P0-A、连接器、MCP、导入、人工审核和 Windows 生命周期
- 风险等级：P0
- 状态：保留为历史记录；当前执行以 2026-07-30 的 Day 0 + 真实数据试运行条目和任务单为准。

### 已通过的自动验收

- [x] `tests #1081`
- [x] `P0 Windows Gate #240`
- [x] `Windows Desktop Release Baseline #129`
- [x] A-01 修复和回归测试

### 历史最终报告

- 原计划报告：`docs/TEST_REPORTS/PR60_OWNER_CODEX_FULL_REACCEPTANCE_1c514877.md`
- 原计划分支：`acceptance/pr60-owner-1c514877`
- 当前不得再按该旧路径执行。

---

## 2026-07-29 · PR #62 · 建立统一 Codex 验收权威

- 产品分支：`docs/acceptance-governance`
- 治理实现与门禁验证基线：`e43da870bc755321f5bd0db4a40aca31df91124d`
- 影响模块：仓库治理、Codex 执行入口、CI 文档同步门禁
- 风险等级：P1
- 用户可感知变化：Codex 拉取代码后可直接从仓库读取当前验收指令，不再依赖聊天中复制的旧指令。
- 数据或安全边界变化：没有产品数据变更；新增规则要求临时证据和配置副本在报告提交后清理。

### 新增或修改的自动验收

- [x] `python scripts/check_acceptance_sync.py`
- [x] `python -m pytest -q tests/test_acceptance_sync.py`
- [x] GitHub Workflow `acceptance-doc-sync #1`
- [x] GitHub Workflow `tests #1082`
- [x] GitHub Workflow `P0 Windows Gate #241`

### 新增或修改的真机验收

- [x] Codex 从仓库读取验收权威，不依赖聊天历史。
- [x] 代码变化后必须同步验收标准。
- [x] 报告提交后清理临时 Artifact、日志、截图、fixture 和配置副本。

### 主人肉眼确认

- [x] 主人明确要求仓库成为验收指令权威。

### 回归项

- [x] 不允许代码变更后遗漏验收标准更新。
- [x] 不允许为了补报告移动已打包产品 Head。
- [x] 不允许长期堆积重复验收垃圾。

### 清理与回滚

- 临时数据前缀：`ACCEPTANCE_GOVERNANCE_`
- 不涉及产品安装或正式数据。

### 不在范围

- 不改变 LingJi 产品功能。
- 不替代模块测试报告。
- 不自动合并产品 PR。

### 最终报告

- 报告路径：`docs/TEST_REPORTS/ACCEPTANCE_GOVERNANCE_IMPLEMENTATION.md`
- 治理 PR：`#62`
