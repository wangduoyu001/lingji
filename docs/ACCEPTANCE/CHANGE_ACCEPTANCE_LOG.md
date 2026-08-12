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

## 2026-08-12 · PR #88 Phase 4 · 安全认证状态同步

- 产品分支：`feature/owner-autopilot-ui-codexpp`
- 产品 Commit：`pending unified closeout head`
- 影响模块：macOS Keychain、Windows Credential Manager、`lingji_state.db`、8766 Local Control API、Desktop Overview、Autopilot、验收证据导出。
- 风险等级：P0（认证秘密与状态边界）。
- 用户可感知变化：首页只显示连接结论；凭据内容、长度、路径和请求头不会显示或同步。

### 新增或修改的自动验收

- [ ] fake CredentialStore 的 get/set/delete/exists 与错误映射；CI 不触碰真实系统凭据。
- [ ] AuthStatus 的 verifying、verified、expired、invalid、permission_insufficient 状态及重启恢复。
- [ ] 8766 `/api/auth/status`、Overview 和 Autopilot 只消费非敏感结论。
- [ ] `LOCAL_AUTH_STATUS_PR88.json` 仅由 allowlist 导出，伪造 Token/Cookie/Authorization Header 必须无法进入；仓库 secret scan PASS，`secret_export_count=0`。
- [ ] macOS / Windows 使用相同状态模型；真实 Keychain / Credential Manager 只在对应真机验收验证。

### 清理与回滚

- 不创建凭据文件、SQLite Secret 或 Git Secret。回滚仅移除状态层代码；不得删除主人已有系统凭据。
- 最终报告：`docs/TEST_REPORTS/PR88_M5_PHASE4_FAILURE_REPAIR.md`；状态快照：`docs/TEST_REPORTS/evidence/LOCAL_AUTH_STATUS_PR88.json`。

### Isolation guard follow-up

- [ ] 当 acceptance task root 与传入 root 不一致时，必须先报告 `LINGJI_ACCEPTANCE_DATA_ROOT` 合同错误，再执行 Windows C: 盘拒绝；Windows 回归与最终 DMG 首启/二启 Gate 必须 PASS。
- 回滚：仅恢复既有 validation order；不得放宽 task-scoped acceptance root 的精确匹配。

---

## 2026-08-11 · PR #88 Phase 3 · Autopilot 启动架构与真机阻断修复

- 产品分支：`feature/owner-autopilot-ui-codexpp`
- 产品 Commit：`pending`
- 来源真机报告：`acceptance/macos-m5-ux-reacceptance-bf9da9ff` / `26946c58cd96158c6318d5f9b5b8f83a91c62aa9`
- 来源结论：`FAIL / DO NOT MERGE`
- 影响模块：macOS/Windows Desktop bootstrap、首次启动、Runtime 数据隔离、首页 Owner Autopilot、AI 来源接管、macOS/Windows Release identity、M5 安装替换协议、Desktop smoke
- 风险等级：P0
- 用户可感知变化：Mac 正常首次启动不再要求主人选择资料目录；灵机自动选择平台安全默认目录、自动启动与恢复。首页不再展示技术 Metric 大面板，AI 来源无授权事项时降为安静的后台接管状态。只有读取真实正文、永久记忆和不可逆操作进入主人决策。
- 数据或安全边界变化：新增 `LINGJI_ACCEPTANCE_DATA_ROOT` 作为仅验收进程使用的 task-scoped 临时根；普通启动不得复用历史 Acceptance workspace；自动化不扩大真实正文读取、永久记忆批准或不可逆重建权限。

### 本轮必须关闭的真机缺陷

- [ ] `M5-IDENTITY-001`：PR Artifact 内嵌 Commit 必须精确等于产品 Head，不得使用 PR merge commit。
- [ ] `M5-UX-002`：Mac 首次启动必须自动确定安全资料目录并继续，手动路径只能作为自动准备失败后的兜底。
- [ ] `M5-ISOLATION-001`：验收 Runtime 所有写入必须在任务单指定 `LINGJI_ACCEPTANCE_DATA_ROOT` 下，`~/Documents/acceptance` 等任务根外新增目录数量必须为 0。
- [ ] `M5-INSTALL-001`：禁止 overlay 写入旧 `.app`；必须整体备份旧 App、完整替换新 App、签名复验失败时整体回滚。

### 新增或修改的自动验收

- [ ] `desktop/lingji-control/scripts/assistant-autopilot-smoke.mjs`：验证自动 bootstrap、AI 元数据被动接管、正文授权边界、永久记忆边界和 acceptance override。
- [ ] `desktop/lingji-control/scripts/observation-first-ui-smoke.mjs`：禁止手选目录重新成为正常首次启动主流程；禁止首页恢复技术 Metric 大面板。
- [ ] `desktop/lingji-control/scripts/macos-release-smoke.mjs`：验证 macOS 自动默认目录、task-scoped acceptance override 与 Release exact-head identity 配置。
- [ ] Rust unit tests：验证 `auto_selected` bootstrap 合同、workspace/path 合同与 acceptance 隔离规则。
- [ ] GitHub `tests`：Python 3.11/3.12、Windows Python、MCP、Desktop smoke、React build、Tauri 配置全部 PASS。
- [ ] GitHub `P0 Windows Gate`：同一产品代码不得破坏 Windows Runtime、首次配置和 Rust/Tauri 基线。
- [ ] GitHub `Windows Desktop Release Baseline`：checkout 与 release metadata 必须使用同一精确 PR Head。
- [ ] GitHub `macOS Desktop Gate`：显式 checkout PR Head；`.app` 与最终 DMG 主二进制必须嵌入该精确 SHA；Sidecar、API boot、DMG mount 全部 PASS。
- [ ] `acceptance-doc-sync` / `local-execution-handoff`：治理门禁必须 PASS。

### 新增或修改的真机验收

- [ ] 使用新精确 Artifact，验收前通过任务单设置 `LINGJI_ACCEPTANCE_DATA_ROOT="$ACCEPTANCE_ROOT/runtime-data"`，并在 Runtime 启动前注入。
- [ ] 旧 `/Applications/灵机.app` 必须整体移入任务临时备份；完整复制新 App；`codesign --verify --deep --strict` PASS 后才启动，禁止 overlay copy。
- [ ] Release Metadata / App 内嵌 commit 与任务单产品 Head 完全一致。
- [ ] 首次打开不手动选择 DataRoot 即可自动准备并进入首页；若自动准备失败，才允许出现手动路径兜底。
- [ ] 所有 SQLite、Qdrant、token、logs、raw、vault、backup 写入只出现在 task-scoped runtime-data；`~/Documents/acceptance` 不得因本轮创建。
- [ ] 首页无主人事项时明确“无需操作”；技术异常显示为后台自动处理中，不进入主人决策数。
- [ ] AI 来源识别不把“2 个工具 / 4400 条工作记录元数据”作为主要任务卡；无授权事项时只以被动状态显示。
- [ ] 合成导出候选只展示一次清晰授权；未授权真实正文读取次数为 0，永久记忆自动批准为 0。
- [ ] 生命周期完成启动 → healthy → 退出 → Core/8766 释放 → 同任务根再次启动 → healthy。

### 主人肉眼确认

- [ ] 第一次打开无需理解 DataRoot、Workspace、Qdrant、Embedding、端口即可进入可用状态。
- [ ] 首页首先告诉主人“有没有必须由我决定的事”，而不是展示后台技术指标或大量扫描计数。
- [ ] 没有主人事项时界面足够安静，不需要为了确认系统正常而点按钮。
- [ ] 真正权限边界出现时，动作清晰且只有一个主要选择。
- [ ] 主人明确确认相比 bf9da9ff 已达到可接受的智能化/自动化主流程；未确认前 PR #88 保持 Draft。

### 回归项

- [ ] 未经主人授权不得读取真实 AI 对话/导出正文。
- [ ] 不允许自动批准永久记忆。
- [ ] 不允许自动删除或重建 Production Qdrant。
- [ ] 不允许自动修改外部 AI 客户端配置。
- [ ] Windows 与 macOS 必须保持同一核心代码，不创建 Mac 特供业务实现。
- [ ] 自动准备失败必须真实降级到手动兜底，不能伪造成功。
- [ ] Production DataRoot / Vault 污染为 0。

### 清理与回滚

- 临时数据前缀：`MACOS-M5-AUTOPILOT-PHASE3-<short-sha>`。
- 安装方式：`whole_bundle_replace`，禁止 overlay。
- 临时 App 备份：仅存于 `$ACCEPTANCE_ROOT/app-backup`；新版本 PASS 后随任务根删除；新版本 FAIL 时先恢复旧 App 并验证签名。
- Runtime 测试根：`$ACCEPTANCE_ROOT/runtime-data`，结束后整体删除。
- 失败证据仅保留最小必要内容；成功日志、截图、DMG、重复 ZIP、临时 Qdrant/SQLite 全部按 M5 协议清理。

### 不在范围

- 未授权静默导入 AI 正文。
- 自动批准永久记忆。
- 无备份执行破坏性 Repair。
- 自动修改第三方 AI 客户端配置。
- 本轮不把所有高级工具页面重做一遍；目标是启动主链和日常首页智能化。

### 最终报告

- 实施报告：`docs/TEST_REPORTS/OWNER_AUTOPILOT_PHASE3_IMPLEMENTATION.md`
- M5 报告：`docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_<short-sha>.md`
- M5 报告分支：`acceptance/macos-m5-autopilot-phase3-<short-sha>`
- PR #88：保持 Draft，直到精确 Artifact、M5 真机和主人体验全部 PASS。

---

## 2026-08-11 · PR #88 · Owner Autopilot UI 与本机 AI 自动发现

- 产品分支：`feature/owner-autopilot-ui-codexpp`
- 产品 Commit：`b34a8752507c99ef929e98769fe37276166aa98d`
- 影响模块：桌面首页、首次启动引导、Codex 工作记录、AI 工具元数据发现、ChatGPT/Codex 导出候选规划与授权导入、Desktop smoke
- 风险等级：P1
- 用户可感知变化：首页优先解释“发现了什么、正在做什么、需要主人决定什么”；Codex 的 Session 计数改为“工作记录”并解释来源；首次启动不再要求主人先理解 DataRoot、Qdrant 或 Windows 专属非 C 盘术语。
- 数据或安全边界变化：自动发现只读取已知位置和文件元数据；不读取真实对话正文、不跟随符号链接、不修改外部 AI 客户端、不自动批准永久记忆；读取发现的导出包前仍需要主人一次明确授权。

### 新增或修改的自动验收

- [x] `python -m pytest -q tests/test_assistant_hub_discovery.py tests/test_assistant_hub_imports.py`：本地 `9 passed`，验证只读发现、路径脱敏、候选白名单、候选失效重验与非相关文件排除。
- [x] `node desktop/lingji-control/scripts/assistant-autopilot-smoke.mjs`：验证首页自动发现、15 秒轮询、授权边界、Codex 工作记录解释与高级技术信息折叠合同。
- [x] Python `py_compile` 与 TypeScript `transpileModule`：验证新增 Python 与 TS/TSX 可解析。
- [ ] GitHub `tests`：Python 3.11/3.12、Windows Python、Desktop UI smoke/build、MCP 与其他仓库回归必须 PASS。
- [ ] GitHub `P0 Windows Gate`：不得破坏已验收的 Windows Runtime、路径、安装和 UI 基线。
- [ ] GitHub `macOS Desktop Gate`：Apple Silicon 构建、Tauri、Sidecar 与 DMG 门禁必须 PASS。
- [ ] `acceptance-doc-sync` 与 `local-execution-handoff`：本条记录与后续真机任务必须通过治理门禁。

### 新增或修改的真机验收

- [ ] 使用 PR #88 精确 Head 生成的新 macOS arm64 Artifact 覆盖安装；首次打开必须只给出一个可理解的主要动作“选择存放位置 / 开始使用灵机”，DataRoot、acceptance 等技术细节默认折叠。
- [ ] Mac 首次使用页面不得出现要求主人理解“非 C 盘”的 Windows 专属主文案；目录选择、保存配置、启动 Core 和重新打开必须可完成。
- [ ] 首页启动后无需点击“扫描”即可自动识别本机 Codex；若存在 Claude Code / WorkBuddy，也应只读显示其真实识别状态。
- [ ] 自动发现阶段检查日志/API/测试资料，确认真实对话正文读取次数为 0，Core Memory 自动新增为 0。
- [ ] 准备一个任务专用的合成 ChatGPT/Codex 导出候选：UI 应先显示文件名/大小等元数据，主人一次授权后立即进入正式处理队列，不再要求输入路径或二次提交。
- [ ] 打开 Codex 工作记录页：若显示 `2`，页面必须明确说明这是 2 条本机识别到的 Codex Session 工作记录，不是灵机新建的 2 个聊天窗口；列表应自动刷新。
- [ ] Windows 使用同一代码基线复验首次配置、自动发现、首页、Codex 工作记录和授权导入，不得因 Mac 文案优化破坏 Windows 路径选择或 Runtime 启动。

### 主人肉眼确认

- [ ] 主人首次打开后不看技术文档，能够直接理解灵机下一步会自己做什么以及自己只需要决定什么。
- [ ] 主人在首页能快速回答四个问题：`发现了什么`、`正在做什么`、`已经自动处理了什么`、`现在有什么必须由我决定`。
- [ ] 主人看到 Codex 工作记录数量时不再把它理解为灵机莫名创建的聊天窗口。
- [ ] Qdrant、Embedding、DataRoot、端口、MCP 等技术信息不会占据日常主流程，需要时仍能从“系统健康细节 / 高级工具”查看。

### 回归项

- [ ] 未经主人授权不得读取任何真实 ChatGPT/Codex 导出正文。
- [ ] 自动扫描不得递归全盘、不得跟随符号链接、不得向前端暴露本机绝对路径。
- [ ] 不允许自动批准永久记忆；现有人工记忆审核链保持有效。
- [ ] Runtime、Qdrant、SQLite、MCP、Sidecar 所有权与生命周期合同不得因本轮 UI/发现优化改变。
- [ ] Windows 与 macOS 使用同一产品代码；不得为 Mac 创建独立业务分支或复制核心逻辑。
- [ ] 自动发现失败时 UI 必须说明会继续重试，不得把未知/失败显示为“全部正常”。

### 清理与回滚

- 临时数据前缀：后续 M5 / Windows 真机任务使用任务 ID 独立前缀，不使用主人 Production 根目录。
- 覆盖安装或迁移方式：使用精确 PR #88 Artifact 覆盖当前验收版本；不卸载主人正式数据。
- 临时备份删除条件：真机报告和远程回执确认后按现有任务清理合同删除。
- 测试数据清理方式：只删除本轮任务创建的合成导出包、临时 DataRoot、日志和安装验证残留；不得删除主人真实 Vault、Production 数据或 AI 客户端配置。
- 回滚：回退 PR #88 的 Owner Autopilot UI / assistant_hub 变更；不得通过关闭 acceptance 门禁或放宽内容授权边界回滚。

### 不在范围

- Codex 原始 Session / JSONL 的静默正文自动导入。
- Claude Code / WorkBuddy 对话正文导入。
- 自动下载或安装 Ollama / Embedding 模型。
- 自动重建 Production Qdrant。
- 自动批准永久记忆。
- 修改外部 AI 客户端配置而不经主人授权。

### 最终报告

- 实施与自动测试报告：`docs/TEST_REPORTS/OWNER_AUTOPILOT_UI_CODEXPP_IMPLEMENTATION.md`
- 真机报告：在精确 CI / Artifact 通过后创建 `docs/TEST_REPORTS/MACOS_M5_OWNER_AUTOPILOT_ACCEPTANCE_<short-sha>.md`
- 真机报告分支：`acceptance/macos-m5-owner-autopilot-<short-sha>`
- PR #88 保持 Draft，直到 CI、Mac/Windows 回归与主人可理解性检查完成。

---

## 2026-08-01 · PR #60 后续 · 代码发布验证临时目录安全清理修复

- 产品分支：`fix/cleanup-code-validation-workspace`
- 产品 Commit：`pending`
- 来源阻塞：`PR60-CODE-RELEASE-VALIDATION-A90A18A6 / BLOCKED_POST_CLEANUP`
- 影响模块：本机任务治理、安全清理工具、代码发布链结果回执
- 风险等级：P1
- 用户可感知变化：不需要重跑已通过的 15 套 release 验证；修复后只补做安全清理、最终回执和远程复读。
- 数据或安全边界变化：不触碰产品 Runtime、UI、Vault、数据库、Qdrant、真实资料或用户 AI 配置；仍只允许删除任务 ID 推导出的精确临时目录。

### 新增或修改的自动验收

- [x] `python -m pytest -q tests/test_cleanup_acceptance_workspace.py`：本地隔离验证 `10 passed`。
- [ ] GitHub `tests`：验证 Python 3.11、3.12、Windows 和完整仓库回归。
- [ ] `acceptance-doc-sync`：验证脚本变化已同步本记录。

### 新增或修改的真机验收

- [ ] 使用 `PR60-CODE-RELEASE-VALIDATION-A90A18A6` 对 `D:\codex\LingJiValidation\PR60-CODE-a90a18a6` 先 dry-run。
- [ ] dry-run 清单必须只包含该任务创建的 product、report、release、日志、缓存和证据目录。
- [ ] 显式 `--execute` 后目标目录必须不存在，相邻目录和主人数据保持不变。
- [ ] 更新原报告与结果回执为最终 `PASS`，再次 push 并远程复读。

### 主人肉眼确认

- [x] 不需要主人参与；本任务不安装、不启动 UI、不读取真实数据。

### 回归项

- [ ] 不允许通配符删除。
- [ ] 不允许删除清理根目录本身。
- [ ] 不允许删除根目录外或非直接子目录。
- [ ] 任务类型、PR号和 8 位 Commit 身份必须与目录名精确匹配。
- [ ] 旧 `D69874AF` 记忆质量任务仍能清理两个明确登记的 `1c514877` 历史目录。
- [ ] 不跟随符号链接或 Windows reparse point。

### 清理与回滚

- 当前清理根：`D:\codex\LingJiValidation`
- 当前目标：`PR60-CODE-a90a18a6`
- 安全入口：`scripts/cleanup_acceptance_workspace.py`
- 回滚：回退本次策略和测试；不得恢复宽泛白名单或手工强删。

### 不在范围

- 不重跑产品代码、Desktop、Rust/Tauri 或 Windows release 验证。
- 不生成或安装正式 GitHub Artifact。
- 不解决 PR #60 与 master 的后续合并冲突。
- 不进入 Day 0、UI 或真实数据验收。

### 最终报告

- 修复报告：`docs/TEST_REPORTS/PR60_CODE_VALIDATION_CLEANUP_POLICY_FIX.md`
- 原验证报告：`docs/TEST_REPORTS/PR60_CODE_RELEASE_VALIDATION_a90a18a6.md`
- 原报告分支：`acceptance/pr60-code-release-validation-a90a18a6`

---

## 2026-07-31 · PR #60 · d69874af 引导修复复验与真实数据记忆质量试运行

- 产品分支：`feature/unified-ai-memory-connectors`
- 产品 Commit：`d69874afd8def42a40c4a5cc5e678a71921d44b5`
- 固定 Artifact：`lingji-windows-0.1.0-d69874af`
- Artifact ID：`8762312712`
- Artifact ZIP SHA256：`6bf1f591502617c400ce482f6beb0d5e430a172cd036137bb4a39cae2cbf4cb4`
- 安装器 SHA256：`d62867b7b7c90bee8273b3cf5720f53099c266897ce95d0e42224deae31bf262`
- 影响模块：首次使用引导、AI 软件与历史目录发现、Codex 连接状态机、Embedding/Qdrant 诊断、Day 0、真实数据试运行、报告提交和本地清理
- 风险等级：P0
- 用户可感知变化：页面必须给出唯一当前动作，主动解释扫描结果和可导入范围，不再同时显示“配置正常”和“命令不存在”，向量问题必须展示具体原因与处理入口。
- 数据或安全边界变化：Day 0 未 PASS 禁止读取真实资料；历史目录只读取元数据，读取内容前必须获得主人授权；Production 保持只读和物理隔离。

### 已通过的自动验收

- [x] `acceptance-doc-sync #43`
- [x] `local-execution-handoff #35`
- [x] `tests #1138`
- [x] `P0 Windows Gate #258`
- [x] `Windows Desktop Release Baseline #142`
- [x] 旧模糊文案“已设置，等待测试”回归断言。
- [x] 配置文件、客户端命令和真实连接三个状态分离。

### 新增或修改的真机验收

- [ ] 开始前使用 `scripts/cleanup_acceptance_workspace.py` 清理旧任务专用临时目录；脚本必须先 dry-run，再显式 `--execute`，且只能操作任务单允许的精确目录。
- [ ] Day 0 在任何真实数据导入前完成：固定 Artifact、覆盖安装、Runtime、8766/8767、MCP 鉴权、真实 Codex 调用、候选边界、A-01、三轮 Core 重启和 Windows 重启。
- [ ] 页面始终只有一个明确主要动作；扫描完成后主动说明发现的软件和历史目录元数据。
- [ ] 发现历史目录后主动询问是否查看或导入，明确说明当前支持与不支持的格式。
- [ ] 配置文件存在、`codex` 命令可用和真实 MCP 连接必须分别显示；缺少命令时不得显示 ready。
- [ ] Embedding/Qdrant 必须显示配置模型、激活模型、缺失模型、最近错误、Qdrant 状态、是否需要重建和当前可执行入口。
- [ ] 主人明确授权后，Stage 1 只导入 1 部剧本、1 份 Codex 报告、少量 ChatGPT 历史和 1 个明确 Obsidian 目录。
- [ ] Stage 1 无 P0/P1 后才逐步扩展到最多 10 部授权剧本和其他授权资料。
- [ ] 至少执行 20 道质量题：精确事实不少于 8、跨文档比较不少于 4、来源核验不少于 4、负面边界不少于 4。

### 主人肉眼确认

- [ ] Checkpoint A：安装和首次打开，无黑窗，首页正常，唯一下一步清楚，状态文案能区分。
- [ ] Checkpoint B：Codex 能看到 LingJi 工具、真实调用成功、返回内容正确。
- [ ] Checkpoint C：主人亲自批准一个测试候选、拒绝一个测试候选，页面可理解。
- [ ] Checkpoint D：Windows 重启后无黑窗，灵机恢复且页面可操作。
- [ ] Checkpoint E：主人至少抽查 10 道质量题，确认答案与来源评分。

### 强制回归项

- [ ] Day 0 未 PASS 时禁止导入真实资料。
- [ ] 未经主人授权不得读取或导入任何真实目录内容。
- [ ] 剧本人物、剧情和台词不得进入主人个人事实。
- [ ] 不存在的问题必须承认未知，不得拿相似资料冒充。
- [ ] 候选未批准前 Core Memory 不增加，拒绝候选不进入永久记忆。
- [ ] A-01 隔离不得读取或修改主人真实 `CODEX_HOME`。
- [ ] 覆盖安装和连接器回滚不得破坏主人数据或配置。
- [ ] Windows 重启后 Runtime、MCP、Workspace、DataRoot 和 Vault 恢复。
- [ ] 开始前和结束后临时目录必须清理；清理失败时只能 BLOCKED，不得绕过安全策略。

### 质量阈值

```text
quality_score >= 90%
source_accuracy >= 95%
false_positive_rate <= 5%
Codex MCP 真实调用成功率 >= 95%
重复正式内容 = 0
Production 污染 = 0
人工审核链成功率 = 100%
Windows 重启后恢复 = 100%
```

### 清理与回滚

- 当前临时数据前缀：`PR60_MEMORY_TRIAL_D69874AF_`
- 当前临时根目录：`D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-d69874af`
- 必须清理的历史临时目录：`D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-1c514877`、`D:\codex\LingJiAcceptance\PR60-1c514877`
- 安全清理入口：`python scripts/cleanup_acceptance_workspace.py --task-id PR60-MEMORY-QUALITY-TRIAL-D69874AF --target <精确目录>`；确认 dry-run 后追加 `--execute`。
- 清理工具拒绝验收根目录本身、根目录外路径、非白名单目录和不匹配任务身份；不跟随符号链接或 Windows reparse point。
- 覆盖安装方式：固定安装器直接覆盖，不卸载。
- 临时配置副本：每个客户端最多一个，哈希验证后删除。
- 主人授权的真实资料是否保留由主人选择，Codex不得擅自删除。
- 报告第一次远程确认后清理，更新结果回执，再次 push 和远程复读。

### 不在范围

- Codex 原始 Session / JSONL 自动导入。
- Claude Code 和 WorkBuddy 历史导入。
- 自动下载 Embedding 模型。
- 自动重建 Production Qdrant。
- 自动批准永久记忆。
- 远程或公网 MCP。

### 最终报告

- 专项协议：`docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md`
- 任务单：`docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`
- 报告路径：`docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_d69874af.md`
- 报告分支：`acceptance/pr60-memory-quality-trial-d69874af`
- 产品 PR 必须保持 Draft 且不得合并，直到 Day 0、Stage 1、质量指标、主人检查点、远程提交和清理全部满足 PASS。

---

## 2026-07-30 · PR #60 · 1c514877 首轮试运行（历史失败，禁止重跑）

- 产品分支：`feature/unified-ai-memory-connectors`
- 产品 Commit：`1c5148779624910f1c6072d95d6c6f6822f631e6`
- 固定 Artifact：`lingji-windows-0.1.0-1c514877`
- Artifact ID：`8723868744`
- 状态：历史 `FAIL / BLOCKED_SUBMISSION`，已被 2026-07-31 的 d69874af 条目取代。
- 已知缺陷：`D0-UX-001` 页面缺少统一引导；`D0-CODEX-002` 配置状态和命令状态矛盾；`BLOCKED_POST_CLEANUP` 旧临时目录未清理。
- 历史报告：`docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_1c514877.md`
- 历史报告分支：`acceptance/pr60-memory-quality-trial-1c514877`
- 当前不得再按该产品 Commit、Artifact 或报告路径执行。

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

## 2026-07-29 · PR #60 · P0-A 与统一 AI 记忆连接器重新真机验收（历史方案）

- 产品分支：`feature/unified-ai-memory-connectors`
- 产品 Commit：`1c5148779624910f1c6072d95d6c6f6822f631e6`
- 固定 Artifact：`lingji-windows-0.1.0-1c514877`
- Artifact ID：`8723868744`
- 状态：被后续真实数据试运行方案取代，保留为历史记录。
- 已通过自动验收：`tests #1081`、`P0 Windows Gate #240`、`Windows Desktop Release Baseline #129`、A-01 回归。
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
