# LingJi（灵机）仓库执行入口

> 正式主线：`master`  
> 架构权威：`docs/ARCHITECTURE.md`  
> 当前状态：`docs/PROJECT_STATUS.md`  
> 代码导航：`docs/MODULES/CODE_MAP.md`  
> 完整治理规则：`docs/DEVELOPMENT_RULES.md`

本文件只负责把开发者和 AI 导向正确的局部上下文。不要把架构、状态、测试历史或模块实现复制到这里。

## 1. 每次任务的最小读取顺序

1. 检查当前分支、HEAD、上游和工作区状态。
2. 阅读 `docs/PROJECT_STATUS.md` 中与任务相关的章节。
3. 在 `docs/MODULES/CODE_MAP.md` 定位模块入口、所有权、相关测试和局部验收命令。
4. 阅读直接受影响的源代码、直接调用方和对应测试。
5. 只有当任务改变架构边界、数据权威、端口、主线职责或兼容策略时，才阅读 `docs/ARCHITECTURE.md`。
6. 只有当任务涉及治理、发布、跨模块测试或文档职责时，才阅读 `docs/DEVELOPMENT_RULES.md` 的对应章节。
7. 历史模块计划和测试报告只在核对历史结论、回归边界或兼容承诺时读取。

禁止默认通读整个仓库、全部文档或全部历史报告。文档冲突时以当前代码和上述权威文件为准，并修正文档冲突。

## 2. 开发流程

1. 先理解用户需求和现有代码。
2. 外部技术、依赖或规则可能变化时，先查官方文档和可靠实现。
3. 给出有边界的落地计划，再修改代码。
4. 使用最少、清晰、可维护的代码完成任务，优先扩展现有模块。
5. 不为“更整齐”做无关的大规模重构，不建立第二套数据库、检索器、队列、API、UI 或配置中心。
6. 每个功能或较大代码修改必须有对应测试，并在现有权威文档或 `docs/TEST_REPORTS/` 留下 Markdown 记录。

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

## 6. 测试与验收

优先运行 `CODE_MAP.md` 对应模块的局部测试。统一入口：

```powershell
.\scripts\validate.ps1 -Mode focused -Area <area>
.\scripts\validate.ps1 -Mode full
.\scripts\validate.ps1 -Mode release
```

- `focused`：开发过程中运行模块测试。
- `full`：最终合并前在最终树上执行一次完整本机门禁。
- `release`：在 `full` 基础上构建并整理 Windows Sidecar/Tauri/NSIS 发布产物；正式发布仍以 GitHub Windows release workflow 和真机安装验收为准。
- 成功时只读取摘要；失败时读取失败项和对应日志，不把完整成功日志送入模型上下文。
- 不得删除测试、降低断言、把失败改成 skip、隐藏失败或把未执行测试写成通过。
- 未完成真实本机验证时，只能标记为“代码完成，待本机验收”。

## 7. 文档职责

- `docs/ARCHITECTURE.md`：稳定架构与边界。
- `docs/PROJECT_STATUS.md`：当前阶段、风险、阻塞和下一步。
- `docs/MODULES/CODE_MAP.md`：代码入口、所有权、相关测试和局部验收。
- `docs/DEVELOPMENT_RULES.md`：完整长期治理规则。
- `docs/CHANGELOG.md`：用户可感知或发布相关变化。
- `docs/TEST_REPORTS/`：测试命令、环境、结果、限制和验证提交。

一个事实只保留一个详细权威。优先更新现有文档，禁止创建“最终总结”“补充说明”或同义副本。

## 8. Git 与交付

- 一个提交只处理一个清晰任务，只提交相关文件。
- 提交前确认工作区状态可解释，不覆盖其他未提交修改。
- 提交信息使用 `feat:`、`fix:`、`docs:`、`test:`、`refactor:`、`chore:`。
- 最终报告必须区分：已实现并测试、已实现未本机测试、仅规划、兼容行为、已知阻塞。
- 报告分支、commit SHA、测试结果、修改文件和未解决问题。

## 9. Windows 约束

- 兼容 Windows PowerShell 5.1。
- 不使用 Bash heredoc，不依赖 `&&`。
- 含空格路径必须正确引用。
- Python 文件使用 UTF-8 无 BOM；读取旧文本时可兼容 `utf-8-sig`。
