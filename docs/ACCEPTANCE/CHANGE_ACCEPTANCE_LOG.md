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

## 2026-08-22 · SB-0 · Work Fact 合同与 8766 正式链路修复

- 产品分支：`feat/sb0-work-fact-contract`
- 产品 Commit：`pending`
- 影响模块：`src/work/`、`src/control/`、Capture→Work bridge、8766 Local Control API、Desktop Work Fact DTO、Work Fact focused tests
- 风险等级：P0
- 用户可感知变化：首页/工作/需要我不再依赖拼凑状态；同一个真实 `work_id` 可从正式 8766 API 查询当前工作、最近工作、事件时间线、结果、下一执行者和主人待办。
- 数据或安全边界变化：Work Fact 继续写入正式 runtime state SQLite 边界，不新增第二数据库；Desktop 仍只访问认证的 `127.0.0.1:8766`；不修改永久记忆权威，不直接写 Production Vault/Qdrant。

### 新增或修改的自动验收

- [ ] `tests/test_work_store.py`：验证 WorkItem/Event/Outcome/NextAction/PendingAction 持久化、状态更新、时间排序、重开数据库后读取和稳定 action id。
- [ ] `tests/test_work_projector.py`：验证 current/recent/timeline/pending 投影只来自真实 WorkStore，空状态与失败状态不伪造成功。
- [ ] `tests/test_work_control_api.py`：验证 `/api/work/current`、`/api/work/recent`、`/api/work/{work_id}`、`/api/work/timeline/{work_id}`、`/api/work/pending-actions` 已注册到正式 `create_control_app()` 且字段合同稳定。
- [ ] `tests/test_capture_work_bridge.py`：验证 Capture bridge 使用正式 `WorkStore.create_work()`，同一 Capture 产生稳定可查询 `work_id`，失败路径写真实事件而不是静默丢失。
- [ ] `desktop/lingji-control/scripts/work-fact-smoke.mjs`：验证 TypeScript Work Fact DTO 与正式 API 字段、状态、nullable 语义一致，API unavailable 不被当成“0 条/没有待办”。
- [ ] `python -m pytest -q --tb=short -k "work or capture_work"`：Work Fact focused 回归。
- [ ] `.\scripts\validate.ps1 -Mode focused -Area control`：正式 8766 与 Control 回归。
- [ ] `.\scripts\validate.ps1 -Mode focused -Area capture`：Capture 既有合同回归。
- [ ] `.\scripts\validate.ps1 -Mode focused -Area desktop`：Desktop contract/smoke 回归。
- [ ] `python scripts/check_acceptance_sync.py`：产品变更与本记录同步。

### 新增或修改的真机验收

- [ ] 使用 Acceptance workspace 启动真实 packaged Desktop/Sidecar，8766 可用时首页能读取真实 current work；8766 不可用时必须显示不可用/错误，不得显示“当前无工作”冒充成功。
- [ ] 创建一个隔离测试 WorkItem，重启 Runtime 后仍能通过同一 `work_id` 查询 WorkItem 和 timeline。
- [ ] 构造一个真实 PendingAction，Home 与“需要我”数量和对象一致；不存在 PendingAction 时两处均为 0/空状态。
- [ ] 构造 failed WorkItem，Activity/Work 显示真实失败，不得被空状态或成功 Outcome 覆盖。

### 主人肉眼确认

- [ ] SB-0 不要求主人判断最终视觉设计；只需在后续 Phase 1 M5 中确认“当前工作/工作履历/需要我”三处不再互相矛盾。SB-0 本身不得宣称第二大脑 UI 已最终验收。

### 回归项

- [ ] Tauri 不直连 SQLite、Qdrant、Ollama 或 8765。
- [ ] 没有真实 WorkItem 时不得宣称灵机正在工作或已完成工作。
- [ ] 没有真实 PendingAction 时不得宣称需要主人处理。
- [ ] API 不可用与真实空列表严格区分。
- [ ] Python/TypeScript 状态枚举统一为 `pending | accepted | running | completed | failed | skipped`。
- [ ] `second_brain/` 不新增 Work Fact 正式实现。
- [ ] Production/Acceptance storage 物理隔离不退化。

### 清理与回滚

- 临时数据前缀：`SB0_WORK_FACT_`
- 覆盖安装或迁移方式：本轮代码开发不触碰主人 Production；真机验收沿用正式 Acceptance workspace 和覆盖安装规则。
- 临时备份删除条件：仅在对应验收报告首次远程确认后删除任务专用临时数据；Production 数据永不由本任务清理。
- 测试数据清理方式：测试使用临时 SQLite/Acceptance workspace，结束后删除任务前缀数据；不得清理未知数据库或 Vault。
- 回滚：以产品分支提交为单位回退 Work Fact schema/service/API/DTO 变更；若需要 schema 兼容迁移，回滚必须保留旧列/数据可读，不允许 destructive reset。

### 不在范围

- 不完成 SB-1 Capture→Work→Outcome 全输入类型闭环。
- 不完成 SB-2 Work→Memory/Evidence 产品闭环。
- 不重做 Home/Work/Attention 视觉设计。
- 不启动机会面板、Opportunity Score 或机会数据模型扩展。
- 不删除 `second_brain/` compatibility runtime。

### 最终报告

- 报告路径：`docs/TEST_REPORTS/SB0_WORK_FACT_CONTRACT.md`
- 报告分支：后续本机验收时按精确产品 Head 创建 `acceptance/sb0-work-fact-<short-sha>`。

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
