# LingJi（灵机）仓库执行入口

> 正式主线：`master`  
> 架构权威：`docs/ARCHITECTURE.md`  
> 当前状态：`docs/PROJECT_STATUS.md`  
> 产品进度与用户需求总账：`docs/PROJECT_PROGRESS.md`  
> 代码导航：`docs/MODULES/CODE_MAP.md`  
> 验收权威：`docs/ACCEPTANCE/README.md`  
> 本机任务单：`docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`  
> 本机结果回执：`docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md`  
> 完整治理规则：`docs/DEVELOPMENT_RULES.md`

本文件只负责把开发者和 AI 导向正确的局部上下文。不要把架构、状态、测试历史、验收细节或模块实现复制到这里。

## 1. 每次任务的最小读取顺序

1. 检查当前分支、HEAD、上游和工作区状态。
2. 阅读 `docs/PROJECT_PROGRESS.md`，确认产品核心、当前项目主线、用户需求编号和执行队列；任何新的 LingJi 产品需求必须先登记到该总账。
3. 阅读 `docs/PROJECT_STATUS.md` 中与任务相关的章节。
4. 在 `docs/MODULES/CODE_MAP.md` 定位模块入口、所有权、相关测试和局部验收命令。
5. 任何开发、优化、修复、发布或验收任务都必须阅读 `docs/ACCEPTANCE/README.md`。
6. 本机 Codex 收到“去看任务单干活”时，必须继续读取 `LOCAL_EXECUTION_TASK.md`、`LOCAL_EXECUTION_RESULT.md`、`CODEX_ACCEPTANCE_INSTRUCTIONS.md`、`CHANGE_ACCEPTANCE_LOG.md` 当前条目和 `REPORT_TEMPLATE.md`。
7. 只允许执行 `LOCAL_EXECUTION_TASK.md` 中 `status: ACTIVE` 的任务。聊天记录、旧报告、本机残留目录和口头摘要不能替代任务单。
8. 阅读直接受影响的源代码、直接调用方和对应测试。
9. 只有当任务改变架构边界、数据权威、端口、主线职责或兼容策略时，才阅读 `docs/ARCHITECTURE.md`。
10. 只有当任务涉及治理、发布、跨模块测试或文档职责时，才阅读 `docs/DEVELOPMENT_RULES.md` 的对应章节。
11. 历史模块计划和测试报告只在核对历史结论、回归边界或兼容承诺时读取。

禁止默认通读整个仓库、全部文档或全部历史报告。文档冲突时以当前代码和上述权威文件为准，并修正文档冲突。聊天中的旧验收指令不得覆盖仓库当前验收权威。

## 2. 开发流程

1. 先理解用户需求和现有代码。
2. 用户提出新的 LingJi 产品需求时，先在 `docs/PROJECT_PROGRESS.md` 分配需求编号、关联项目、优先级、状态和可验证验收结果，再开始开发。
3. 外部技术、依赖或规则可能变化时，先查官方文档和可靠实现。
4. 在开发前定义本次自动测试、真机测试、主人观察、回归、清理和回滚要求，并写入 `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`。
5. 需要本机执行时，由 ChatGPT / 主开发代理更新 `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`；不得让用户复制长指令。
6. 给出有边界的落地计划，再修改代码。
7. 使用最少、清晰、可维护的代码完成任务，优先扩展现有模块。
8. 不为“更整齐”做无关的大规模重构，不建立第二套数据库、检索器、队列、API、UI 或配置中心。
9. 每个功能或较大代码修改必须有对应测试，并在现有权威文档或 `docs/TEST_REPORTS/` 留下 Markdown 记录。
10. 代码、运行时、Desktop、连接器、数据链路、脚本、依赖或发布流程变化时，必须在同一 PR 同步更新 `docs/ACCEPTANCE/`；未同步不得宣布完成或请求合并。
11. 每轮开发结束必须回填 `docs/PROJECT_PROGRESS.md`：需求状态、实现 Commit/PR、测试/真机证据、已知限制和下一批执行项。

## 3. 长期架构边界

```text
src/
= 唯一长期平台主线

desktop/lingji-control/
= 唯一正式 Desktop UI

second_brain/
= 兼容、迁移与验收来源
```

- 新正式记忆能力进入 `src/`。
- 新采集进入 `src/extraction/`。
- 新正式 Desktop 功能进入 `desktop/lingji-control/`。
- `second_brain/` 只允许迁移阻塞修复、兼容读取、导出工具和验收测试。
- Desktop 只通过认证的 `127.0.0.1:8766` Local Control API 访问后端。
- MCP 默认使用 stdio；可选 HTTP 使用 8767；8765 仅为迁移期兼容 API。

## 4. 数据权威

```text
Obsidian Vault + Git
= 永久记忆与正式知识正文

storage/raw
= 原始导入材料

lingji_state.db
= 任务、队列、运行状态与审计

lingji_memory.db
= 可重建全文与元数据索引

Qdrant
= 可重建语义索引
```

- 不得新增第二个永久记忆事实源。
- AI 只能提出记忆候选，不能静默修改 Core Memory。
- Qdrant、索引数据库和 Structured Read Model 必须可重建。
- Obsidian 正式知识允许索引，但不得自动蒸馏成个人永久记忆。

## 5. 安全与路径

- 禁止提交 `.env`、API Key、Token、Cookie、真实聊天、真实数据库、模型、日志、缓存和个人隐私数据。
- 不得静默向 C 盘写入数据库、向量、模型、日志、缓存、上传或生成资产。
- 不得硬编码开发者绝对路径。
- Production 与 Acceptance 必须物理隔离 Vault、raw、数据库、Qdrant、日志、设置和备份。
- 未经明确批准，不得批量删除、覆盖、移动正式知识或修改真实 Vault。
- 停止服务时按 PID、实例或明确端口处理，禁止结束全部 Python 进程。
- 验收默认直接覆盖安装，不卸载和删除主人数据。
- 每次本机任务开始前必须删除上一轮临时验收目录和垃圾，清理残留进程并释放 8766/8767。
- 每次报告远程确认后必须删除临时 Artifact、日志、截图、fixture、checkpoint、临时配置副本、worktree 和本轮测试数据。

## 6. 测试与验收

优先运行 `CODE_MAP.md` 对应模块的局部测试。统一入口：

```powershell
.\scripts\validate.ps1 -Mode focused -Area <area>
.\scripts\validate.ps1 -Mode full
.\scripts\validate.ps1 -Mode release
python scripts/check_acceptance_sync.py
python scripts/check_local_execution_handoff.py
```

- `focused`：开发过程中运行模块测试。
- `full`：最终合并前在最终树上执行一次完整本机门禁。
- `release`：自身已经包含 `full`，再构建 Windows Sidecar/Tauri/NSIS；同一代码树禁止先跑 `full` 再跑 `release`。
- 成功时只读取 `output/validation/latest-summary.json` 或 `latest-summary.md`，禁止把完整成功日志送入模型上下文。
- 失败时先读取摘要和失败日志尾部；仍无法定位时才按关键词扩展，禁止一次加载全部日志。
- 每次新验收自动清理旧验证目录，本地不堆叠旧输出。
- 不得删除测试、降低断言、把失败改成 skip、隐藏失败或把未执行测试写成通过。
- 未完成真实本机验证时，只能标记为“代码完成，待本机验收”。
- 所有 UI 项目必须先由代理启动真实发布版，自行遍历页面并点击每个可见控件，验证其后端、文件、数据或进程逻辑；死按钮、假成功、占位页和纯外观空壳均判定失败。
- 代理自验通过后必须保持真实 UI 打开，等待主人最终确认；主人明确确认前不得宣布验收完成、关闭 UI、合并最终版本或清理主人要求保留的失败证据。
- 产品相关文件变化而 `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md` 未同步时，验收同步门禁必须失败。
- `acceptance/**` 报告分支上的 `LOCAL_EXECUTION_RESULT.md` 不是 `COMPLETED`，或缺少远程确认、开始/结束清理、报告 Commit 时，本机交接门禁必须失败。

## 7. 文档职责

- `docs/ARCHITECTURE.md`：稳定架构与边界。
- `docs/PROJECT_STATUS.md`：当前阶段、风险、阻塞和下一步。
- `docs/PROJECT_PROGRESS.md`：长期产品项目、用户需求、优先级、执行队列和每轮开发回填。
- `docs/MODULES/CODE_MAP.md`：代码入口、所有权、相关测试和局部验收。
- `docs/DEVELOPMENT_RULES.md`：完整长期治理规则。
- `docs/ACCEPTANCE/README.md`：当前验收与本机交接总规则。
- `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`：唯一当前本机任务单。
- `docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md`：唯一当前本机结果回执。
- `docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md`：通用 Codex 真机验收基线。
- `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`：每次变更的增量验收要求。
- `docs/ACCEPTANCE/REPORT_TEMPLATE.md`：最终报告结构。
- `docs/CHANGELOG.md`：用户可感知或发布相关变化。
- `docs/TEST_REPORTS/`：测试命令、环境、结果、限制和验证提交。

一个事实只保留一个详细权威。优先更新现有文档，禁止创建“最终总结”“补充说明”或同义副本。

## 8. Git 与交付

- 一个提交只处理一个清晰任务，只提交相关文件。
- 提交前确认工作区状态可解释，不覆盖其他未提交修改。
- 提交信息使用 `feat:`、`fix:`、`docs:`、`test:`、`refactor:`、`chore:`。
- 最终报告必须区分：已实现并测试、已实现未本机测试、仅规划、兼容行为、已知阻塞。
- 报告分支、commit SHA、测试结果、修改文件和未解决问题。
- 产品 Artifact 对应的 Head 固定后，验收报告使用独立分支提交；禁止为了补报告移动产品 Head。
- `git push` 不等于提交成功。Codex 必须通过 `git ls-remote` 和 GitHub API 重新读取远程分支、Commit、报告、结果回执和 PR 评论。
- 远程复读失败时必须写 `BLOCKED_REPORT_NOT_VISIBLE_ON_GITHUB`，不得告诉用户已经完成。
- 远程第一次确认后执行本地清理，更新结果回执，再次 push 和远程复读。
- 用户只负责告诉 Codex 去看任务单，或告诉 ChatGPT Codex 已完成；用户不负责 Git 和上传操作。
- PR 模板中的验收同步清单未完成时不得标记 Ready 或合并。

## 9. Windows 约束

- 兼容 Windows PowerShell 5.1。
- 不使用 Bash heredoc，不依赖 `&&`。
- 含空格路径必须正确引用。
- Python 文件使用 UTF-8 无 BOM；读取旧文本时可兼容 `utf-8-sig`。