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

## 2026-07-30 · 本机任务信箱与结果回执硬门禁

- 产品分支：`master`
- 产品 Commit：`governance-only`
- 影响模块：仓库治理、Codex 本机执行交接、报告提交、远程复读、本地垃圾清理、GitHub Actions
- 风险等级：P1
- 用户可感知变化：用户只需告诉 Codex 去看任务单，或告诉 ChatGPT Codex 已完成；不再复制长指令、解释 Git、上传报告或排查分支。
- 数据或安全边界变化：不改变产品数据；明确禁止清理主人 DataRoot、Vault、正式记忆和用户 AI 配置，只清理本轮临时验收垃圾。

### 新增或修改的自动验收

- [ ] `python scripts/check_local_execution_handoff.py`：校验任务单、结果回执、身份一致性、开始/结束清理、远程确认和报告 Commit 字段。
- [ ] `python -m pytest -q tests/test_local_execution_handoff.py`：覆盖 PENDING、COMPLETED、远程确认缺失、清理失败、身份不一致和阻塞提交。
- [ ] `local-execution-handoff` Workflow：在 `master`、开发分支和 `acceptance/**` 报告分支执行；报告分支结果不是 `COMPLETED` 时失败。

### 新增或修改的真机验收

- [ ] Codex 只读取 `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md` 中 `status: ACTIVE` 的任务，不从聊天或本机残留推断。
- [ ] 每次开始前整体清理上一轮临时验收目录、Artifact、日志、截图、fixture、checkpoint、临时配置副本和 worktree，再释放 8766/8767。
- [ ] 报告 push 后使用 `git ls-remote` 和 GitHub API 重新读取远程分支、Commit、报告、结果回执和 PR 评论。
- [ ] 第一次远程确认后清理本轮本地垃圾，更新结果回执，再次 push 和远程复读。

### 主人肉眼确认

- [x] 用户只负责下达“去看任务单干活”或“Codex 已完成”，不负责 Git、上传、报告路径和清理操作。

### 回归项

- [ ] 禁止把本机生成报告误写成已经上传。
- [ ] 禁止 `git push` 命令执行后未复读远程就宣布完成。
- [ ] 禁止长期堆积旧验收目录、重复安装包、日志、截图、fixture、checkpoint、配置副本和 worktree。
- [ ] 禁止清理主人正式数据或其他任务数据。

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

## 2026-07-29 · PR #60 · P0-A 与统一 AI 记忆连接器重新真机验收

- 产品分支：`feature/unified-ai-memory-connectors`
- 产品 Commit：`1c5148779624910f1c6072d95d6c6f6822f631e6`
- 固定 Artifact：`lingji-windows-0.1.0-1c514877`
- Artifact ID：`8723868744`
- Artifact ZIP SHA256：`de895289aa8cbef65c27bdf5c298c7f105b8037e34a1e2167208a9e85ab16538`
- 安装器 SHA256：`21ef1825f58845e246695c966032ef9326ba5de8bde4a55e4efe8ec516b7b3a3`
- 影响模块：P0-A 开始中心、AI 助手扫描、Codex/Claude/WorkBuddy 连接器、MCP HTTP、ChatGPT/Codex Report 导入、人工记忆审核、Windows Sidecar 打包与生命周期
- 风险等级：P0
- 用户可感知变化：第一次打开可按唯一下一步完成扫描、连接、导入和审核；本机 AI 可通过受认证的 8767 MCP 使用主人批准的记忆并提交候选。
- 数据或安全边界变化：MCP Token、Production/Acceptance 隔离、第三方 AI 配置写入与回滚、候选记忆人工批准边界。

### 已通过的自动验收

- [x] `tests #1081`：Python 3.11 / 3.12 / Windows、Desktop Smoke、MCP、Obsidian Plugin 和 Browser Capture。
- [x] `P0 Windows Gate #240`：完整 Python、Desktop、Rust 和 clean-install 合同。
- [x] `Windows Desktop Release Baseline #129`：Sidecar、Tauri、NSIS、哈希和 Artifact 合同。
- [x] `tests/test_ai_memory_connectors.py`：连接器写入、冲突、备份、回滚和显式空环境隔离。
- [x] `tests/test_assistant_hub_api.py`、`tests/test_mcp_http_auth.py`、`tests/test_packaged_mcp_runtime.py`。
- [x] A-01 回归：`env={}` 不再继承机器 `CODEX_HOME`，不得触碰主人真实 Codex 配置。

### 必须完成的真机重新验收

- [ ] 清理旧验收目录、旧 Artifact、旧日志、旧测试 fixture 和旧 LingJi 残留进程；不得删除主人 DataRoot、Vault、正式记忆和用户 AI 配置。
- [ ] 只使用 Artifact ID `8723868744`，核验 ZIP、安装器、Desktop、Sidecar 和 Manifest 哈希。
- [ ] 直接覆盖安装，不卸载，不删除用户数据，不把 DataRoot 迁回 C 盘。
- [ ] 首次打开确认 Workspace、Vault、记忆层数量、AI 状态和唯一推荐下一步真实可理解。
- [ ] 8766 与 8767 只监听 `127.0.0.1`；Runtime healthy/managed；无重复 Core 和孤儿 MCP。
- [ ] Codex 预览、精确确认、临时备份、配置写入、新会话真实 MCP 调用、候选提交、回滚和重新连接全部通过。
- [ ] Codex 真实调用 `get_core_memory`、`search_memory`、`build_context_pack`、`memory_health` 和 `propose_memory`。
- [ ] Claude Code 已安装时使用官方 `claude mcp` 完成同类测试；未安装标记 `SKIPPED_NOT_INSTALLED`。
- [ ] WorkBuddy / CodeBuddy 已安装时在官方 UI 粘贴脱敏后受控复制的配置并真实调用；未安装标记 `SKIPPED_NOT_INSTALLED`。
- [ ] 使用无隐私 fixture 完成 ChatGPT Export 或 Codex Report 至少一种真实 UI 导入，并验证队列、幂等、来源和失败路径。
- [ ] `propose_memory` 和导入只生成候选；未批准前 Core Memory 不增加；主人可批准或拒绝 Acceptance 测试候选。
- [ ] 连续三轮 Core 重启后 Runtime、MCP、Workspace、DataRoot、Vault 和客户端调用恢复。
- [ ] Windows 重启后恢复，并再执行一轮 Core 重启。
- [ ] Production/Acceptance DataRoot、Token、候选、导入和正式记忆不串用；Production 不写测试内容。
- [ ] 验收报告提交后删除临时 Artifact、普通成功日志、截图、fixture 和配置临时副本。

### 主人肉眼确认

- [ ] 安装、启动、三轮 Core 重启和 Windows 重启期间没有 PowerShell、CMD 或黑色控制台窗口。
- [ ] 第一次打开无需开发者口头解释即可知道下一步。
- [ ] 能明确区分“检测到”“已配置”“连接测试通过”“历史已导入”。
- [ ] Production、Acceptance、Vault、记忆数量和 Embedding 限制文案可理解。
- [ ] WorkBuddy / CodeBuddy 等真实客户端 GUI 结果由主人确认，不由 Codex 自我推断。

### 强制回归项

- [ ] A-01：隔离验收不得读取或修改主人真实 `CODEX_HOME`。
- [ ] 覆盖安装不破坏主人数据。
- [ ] 连接器回滚不破坏其他 Codex/Claude 设置。
- [ ] Token 不出现在预览、公开日志、截图、Git 或报告。
- [ ] inactive Embedding 不把整个系统伪装成崩溃，lexical 检索仍可用。
- [ ] 不出现死按钮、假成功、未知值伪造、重复 Core、孤儿 MCP、C 盘运行数据写入或自动 Core Memory 写入。

### 清理与回滚

- 临时数据前缀：`PR60_ACCEPTANCE_1C514877_`
- 覆盖安装方式：固定安装器直接覆盖，不卸载。
- 临时配置副本：每个客户端最多一个，回滚哈希确认后立即删除。
- 测试数据清理：只处理带本轮前缀的 Acceptance fixture、候选和测试正式记忆。
- 本地保留：最终报告、脱敏公开证据、哈希清单和主人明确要求保留的失败证据。

### 不在范围

- Claude Code 历史导入。
- WorkBuddy / CodeBuddy 历史导入。
- ChatGPT 实时本地 MCP。
- 远程或公网 MCP。
- 每个 AI 独立 Agent Scope 与隐私矩阵。
- 自动批准永久记忆。
- Embedding 激活完成。

### 最终报告

- 报告路径：`docs/TEST_REPORTS/PR60_OWNER_CODEX_FULL_REACCEPTANCE_1c514877.md`
- 报告分支：`acceptance/pr60-owner-1c514877`
- 产品 PR 必须保持 Draft 且不得合并，直到该报告为 PASS 并由主人确认。

---

## 2026-07-29 · PR #62 · 建立统一 Codex 验收权威

- 产品分支：`docs/acceptance-governance`
- 治理实现与门禁验证基线：`e43da870bc755321f5bd0db4a40aca31df91124d`
- 影响模块：仓库治理、Codex 执行入口、CI 文档同步门禁
- 风险等级：P1
- 用户可感知变化：Codex 拉取代码后可直接从仓库读取当前验收指令，不再依赖聊天中复制的旧指令。
- 数据或安全边界变化：没有产品数据变更；新增规则要求临时证据和配置副本在报告提交后清理。

### 新增或修改的自动验收

- [x] `python scripts/check_acceptance_sync.py`：产品相关文件变化时必须同步修改 `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`。
- [x] `python -m pytest -q tests/test_acceptance_sync.py`：覆盖无代码变化、代码未同步文档、代码已同步文档、隐藏 GitHub 路径、Windows 路径和依赖/Workflow 变化。
- [x] GitHub Workflow `acceptance-doc-sync #1`：精确基线成功。
- [x] GitHub Workflow `tests #1082`：精确基线成功。
- [x] GitHub Workflow `P0 Windows Gate #241`：精确基线成功。

### 新增或修改的真机验收

- [x] Codex 拉取仓库后读取 `AGENTS.md`，能够定位本目录和通用验收指令。
- [x] 使用当前变更记录生成对应验收清单，不依赖聊天历史。
- [x] 验收规则明确要求报告提交后删除临时 Artifact、日志、截图、fixture 和配置临时副本。

### 主人肉眼确认

- [x] 主人明确要求仓库成为验收指令权威，并要求 Codex 拉取后直接读取。

### 回归项

- [x] 不允许代码变更后遗漏验收标准更新。
- [x] 不允许为了补报告移动已打包的产品 Head。
- [x] 不允许长期堆积重复安装包、日志、截图和配置备份。

### 清理与回滚

- 临时数据前缀：`ACCEPTANCE_GOVERNANCE_`
- 覆盖安装或迁移方式：不涉及产品安装。
- 临时备份删除条件：测试完成立即删除。
- 测试数据清理方式：删除测试临时 Git 仓库和输出目录。

### 不在范围

- 不改变 LingJi 产品功能。
- 不替代模块测试报告。
- 不自动合并任何产品 PR。

### 最终报告

- 报告路径：`docs/TEST_REPORTS/ACCEPTANCE_GOVERNANCE_IMPLEMENTATION.md`
- 治理 PR：`#62`
